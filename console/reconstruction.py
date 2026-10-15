"""KEYSTONE 3D Reconstruction Engine (PyCOLMAP CPU & Memory Optimized).

Provides safe, memory-aware Structure-from-Motion (SfM) for 8 GB RAM machines.
Key features:
1. Thread limiting (default 2 CPU threads) across feature extraction, matching, and incremental mapping.
2. Image size management (max dimension default 1600px) with aspect ratio preservation and non-destructive working copies.
3. Preflight image validation: format, decoding, duplicate hashing, dimension, and blur heuristic.
4. Clean staged execution with progress callbacks and cancellation support.
5. Point cloud and camera pose extraction without coordinate fabrication.
"""
from __future__ import annotations

import gc
import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("keystone.reconstruction")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIN_IMAGE_DIM = 240
DEFAULT_MAX_DIM = 1600
DEFAULT_THREADS = 2
MIN_RECOMMENDED_PHOTOS = 6


@dataclass
class ImageValidationItem:
    filename: str
    valid: bool
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    blur_score: float = 0.0
    sha256: str = ""
    warning: str | None = None
    error: str | None = None


@dataclass
class ValidationSummary:
    status: str  # "READY", "WARNING", "NEEDS ATTENTION"
    total_count: int
    valid_count: int
    invalid_count: int
    items: list[ImageValidationItem] = field(default_factory=list)
    duplicates: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    can_proceed: bool = False


@dataclass
class CameraPose:
    id: int
    name: str
    center: list[float]  # [x, y, z]
    direction: list[float]  # [dx, dy, dz]


@dataclass
class ReconstructionResult:
    success: bool
    points: np.ndarray  # (N, 3)
    colors: np.ndarray  # (N, 3)
    cameras: list[CameraPose]
    num_input_images: int
    num_reg_images: int
    num_points: int
    mean_reprojection_error: float
    ply_path: str | None
    cameras_json_path: str | None
    duration_sec: float
    log: str
    error_message: str | None = None
    warning_messages: list[str] = field(default_factory=list)
    effective_max_dim: int = DEFAULT_MAX_DIM
    num_threads_used: int = DEFAULT_THREADS


def compute_blur_score(image_path: Path) -> float:
    """Calculates image sharpness variance using the Laplacian operator.

    Note: This is an advisory heuristic. A low score on smooth or uniform
    surfaces (e.g. whitewashed lime plaster) does not definitively prove
    an image is unmatchable.
    """
    try:
        data = np.fromfile(str(image_path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        # Resize if huge just for blur computation to save memory
        h, w = img.shape[:2]
        if max(h, w) > 1024:
            scale = 1024.0 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        var = float(cv2.Laplacian(img, cv2.CV_64F).var())
        return var
    except Exception as exc:
        logger.debug(f"Blur calculation exception for {image_path}: {exc}")
        return 0.0


def validate_image_files(image_paths: list[Path]) -> ValidationSummary:
    """Performs rigorous preflight validation on an uploaded list of image files."""
    items: list[ImageValidationItem] = []
    seen_hashes: dict[str, str] = {}
    duplicates: list[tuple[str, str]] = []
    warnings: list[str] = []
    errors: list[str] = []

    if not image_paths:
        return ValidationSummary(
            status="NEEDS ATTENTION",
            total_count=0,
            valid_count=0,
            invalid_count=0,
            errors=["No photographs uploaded. Please select at least 6 overlapping photographs."],
            can_proceed=False,
        )

    for p in image_paths:
        fname = p.name
        ext = p.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            err = f"Unsupported file extension '{ext}'. Only JPG, JPEG, and PNG are supported."
            items.append(ImageValidationItem(filename=fname, valid=False, error=err))
            continue

        size = p.stat().st_size
        if size == 0:
            err = "File is empty (0 bytes)."
            items.append(ImageValidationItem(filename=fname, valid=False, error=err))
            continue

        # Check hash for duplicates
        try:
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        except Exception as e:
            items.append(ImageValidationItem(filename=fname, valid=False, error=f"Read error: {e}"))
            continue

        if digest in seen_hashes:
            dup_orig = seen_hashes[digest]
            duplicates.append((fname, dup_orig))
            warn = f"Duplicate of {dup_orig} (identical content)."
        else:
            seen_hashes[digest] = fname
            warn = None

        # Verify readability and dimensions via PIL
        try:
            with Image.open(p) as im:
                w, h = im.size
        except Exception as e:
            items.append(ImageValidationItem(filename=fname, valid=False, error=f"Cannot decode image: {e}"))
            continue

        if w < MIN_IMAGE_DIM or h < MIN_IMAGE_DIM:
            err = f"Image too small ({w}x{h} px). Minimum required dimension is {MIN_IMAGE_DIM} px."
            items.append(ImageValidationItem(filename=fname, valid=False, width=w, height=h, size_bytes=size, error=err))
            continue

        blur = compute_blur_score(p)
        if blur < 20.0 and warn is None:
            warn = f"Low sharpness heuristic ({blur:.1f}). Check focus if this is not a smooth featureless surface."

        items.append(ImageValidationItem(
            filename=fname,
            valid=True,
            width=w,
            height=h,
            size_bytes=size,
            blur_score=blur,
            sha256=digest,
            warning=warn,
        ))

    valid_count = sum(1 for item in items if item.valid)
    invalid_count = len(items) - valid_count

    if duplicates:
        warnings.append(f"Detected {len(duplicates)} duplicate image(s). Duplicate views waste processing time.")

    low_sharpness = [item.filename for item in items if item.valid and item.blur_score < 15.0]
    if low_sharpness:
        warnings.append(f"{len(low_sharpness)} photograph(s) have low sharpness scores. Verify they are in focus.")

    if valid_count < 3:
        errors.append(f"Only {valid_count} usable photograph(s) available. Structure-from-motion requires at least 3 photos (6+ recommended).")
        status = "NEEDS ATTENTION"
        can_proceed = False
    elif valid_count < MIN_RECOMMENDED_PHOTOS:
        warnings.append(f"Only {valid_count} photos provided. Minimum recommended is 6-15 for stable camera triangulation.")
        status = "WARNING"
        can_proceed = True
    elif invalid_count > 0 or duplicates:
        status = "WARNING"
        can_proceed = True
    else:
        status = "READY"
        can_proceed = True

    return ValidationSummary(
        status=status,
        total_count=len(image_paths),
        valid_count=valid_count,
        invalid_count=invalid_count,
        items=items,
        duplicates=duplicates,
        warnings=warnings,
        errors=errors,
        can_proceed=can_proceed,
    )


def prepare_working_copies(
    source_paths: list[Path],
    working_dir: Path,
    max_dim: int = DEFAULT_MAX_DIM,
) -> tuple[list[Path], list[str]]:
    """Creates resized working copies of images for SfM without modifying originals.

    Downsamples high-resolution images so the largest dimension <= max_dim.
    Preserves aspect ratio, avoids upscaling smaller images, and maintains high quality.
    """
    working_dir.mkdir(parents=True, exist_ok=True)
    prepared_paths: list[Path] = []
    notes: list[str] = []

    for src in source_paths:
        dst = working_dir / src.name
        try:
            with Image.open(src) as im:
                w, h = im.size
                if max_dim > 0 and max(w, h) > max_dim:
                    scale = float(max_dim) / max(w, h)
                    nw, nh = int(round(w * scale)), int(round(h * scale))
                    resized = im.resize((nw, nh), resample=Image.Resampling.LANCZOS)
                    if src.suffix.lower() in {".jpg", ".jpeg"} and resized.mode != "RGB":
                        resized = resized.convert("RGB")
                    resized.save(dst, quality=95, optimize=True)
                    notes.append(f"{src.name}: scaled from {w}x{h} to {nw}x{nh} px (ratio {scale:.2f})")
                else:
                    shutil.copy2(src, dst)
                    notes.append(f"{src.name}: kept native {w}x{h} px")
            prepared_paths.append(dst)
        except Exception as exc:
            logger.error(f"Failed to prepare {src.name}: {exc}")
            shutil.copy2(src, dst)
            prepared_paths.append(dst)

    return prepared_paths, notes


def run_pycolmap_reconstruction(
    image_dir: Path,
    output_dir: Path,
    max_threads: int = DEFAULT_THREADS,
    max_image_dim: int = DEFAULT_MAX_DIM,
    tries: int = 3,
    status_callback: Callable[[str, float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> ReconstructionResult:
    """Executes the complete, memory-optimized PyCOLMAP Structure-from-Motion pipeline.

    - Feature extraction uses max_threads CPU threads and max_image_size limit.
    - Feature matching uses max_threads CPU threads.
    - Incremental mapping uses max_threads and loads images on-demand.
    - Multiple mapping attempts are performed; the most comprehensive model is retained.
    """
    t0 = time.time()
    log_lines: list[str] = []
    warnings: list[str] = []

    def log(msg: str):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        log_lines.append(line)
        logger.info(line)

    def report_stage(stage_name: str, pct: float):
        log(f"Stage: {stage_name}")
        if status_callback:
            status_callback(stage_name, pct)

    log(f"Starting KEYSTONE SfM Pipeline (threads={max_threads}, max_dim={max_image_dim}, tries={tries})")

    try:
        import pycolmap
    except ImportError as e:
        err = "PyCOLMAP is not installed in the active environment. Run `pip install pycolmap`."
        log(f"FATAL: {err}")
        return ReconstructionResult(
            success=False,
            points=np.zeros((0, 3), dtype=np.float32),
            colors=np.zeros((0, 3), dtype=np.uint8),
            cameras=[],
            num_input_images=0,
            num_reg_images=0,
            num_points=0,
            mean_reprojection_error=0.0,
            ply_path=None,
            cameras_json_path=None,
            duration_sec=time.time() - t0,
            log="\n".join(log_lines),
            error_message=err,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "database.db"
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(exist_ok=True)
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    all_imgs = [p for p in image_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    n_photos = len(all_imgs)
    if n_photos < 3:
        err = f"Insufficient photos ({n_photos}). Need at least 3 photos."
        log(f"ERROR: {err}")
        return ReconstructionResult(
            success=False,
            points=np.zeros((0, 3), dtype=np.float32),
            colors=np.zeros((0, 3), dtype=np.uint8),
            cameras=[],
            num_input_images=n_photos,
            num_reg_images=0,
            num_points=0,
            mean_reprojection_error=0.0,
            ply_path=None,
            cameras_json_path=None,
            duration_sec=time.time() - t0,
            log="\n".join(log_lines),
            error_message=err,
        )

    # STAGE 1: Feature Extraction
    if cancel_check and cancel_check():
        log("Reconstruction cancelled by user before feature extraction.")
        return _make_cancelled_result(log_lines, t0, n_photos)

    report_stage("Extracting SIFT Features", 0.20)
    log(f"Extracting features across {n_photos} photographs with {max_threads} CPU thread(s)...")

    feo = pycolmap.FeatureExtractionOptions()
    feo.num_threads = int(max_threads)
    if max_image_dim > 0:
        feo.max_image_size = int(max_image_dim)

    device = pycolmap.Device.cpu
    cancellation_token = pycolmap.CancellationToken()

    try:
        pycolmap.extract_features(
            database_path=db_path,
            image_path=image_dir,
            extraction_options=feo,
            device=device,
            cancellation_token=cancellation_token,
        )
        log("Feature extraction completed successfully.")
    except Exception as e:
        err = f"Feature extraction failed: {e}"
        log(f"ERROR: {err}")
        return _make_error_result(log_lines, t0, n_photos, err)

    gc.collect()

    # STAGE 2: Feature Matching
    if cancel_check and cancel_check():
        log("Reconstruction cancelled by user before matching.")
        return _make_cancelled_result(log_lines, t0, n_photos)

    report_stage("Matching Features (Exhaustive)", 0.45)
    log(f"Exhaustive two-view matching using {max_threads} CPU thread(s)...")

    fmo = pycolmap.FeatureMatchingOptions()
    fmo.num_threads = int(max_threads)

    try:
        pycolmap.match_exhaustive(
            database_path=db_path,
            matching_options=fmo,
            device=device,
            cancellation_token=cancellation_token,
        )
        log("Feature matching completed successfully.")
    except Exception as e:
        err = f"Feature matching failed: {e}"
        log(f"ERROR: {err}")
        return _make_error_result(log_lines, t0, n_photos, err)

    gc.collect()

    # STAGE 3: Incremental Mapping
    if cancel_check and cancel_check():
        log("Reconstruction cancelled by user before mapping.")
        return _make_cancelled_result(log_lines, t0, n_photos)

    report_stage("Solving Cameras & Triangulating 3D Points", 0.70)
    log(f"Beginning incremental bundle adjustment ({tries} mapping attempts)...")

    ipo = pycolmap.IncrementalPipelineOptions()
    ipo.num_threads = int(max_threads)
    ipo.load_all_images = False  # Keep RAM low!

    candidates = []
    for attempt in range(max(1, tries)):
        if cancel_check and cancel_check():
            log("Reconstruction cancelled by user during mapping.")
            return _make_cancelled_result(log_lines, t0, n_photos)

        tdir = sparse_dir / f"attempt_{attempt}"
        tdir.mkdir(exist_ok=True)
        try:
            maps = pycolmap.incremental_mapping(
                database_path=db_path,
                image_path=image_dir,
                output_path=tdir,
                options=ipo,
            )
            for r in maps.values():
                candidates.append(r)
            best_attempt = max(((r.num_reg_images(), r.num_points3D()) for r in maps.values()), default=(0, 0))
            log(f"   Attempt {attempt + 1}/{tries}: registered {best_attempt[0]} cameras, {best_attempt[1]} 3D points.")
        except Exception as e:
            log(f"   Attempt {attempt + 1}/{tries} encountered error: {e}")

    if not candidates:
        err = (
            "No cameras could be registered. None of the photographs could be mutually triangulated. "
            "Please ensure the photographs have 60-80% visual overlap, sufficient surface texture, "
            "and were captured from varying camera positions rather than rotating on the spot."
        )
        log(f"ERROR: {err}")
        return _make_error_result(log_lines, t0, n_photos, err)

    rec = max(candidates, key=lambda r: (r.num_reg_images(), r.num_points3D()))
    n_reg = rec.num_reg_images()
    n_pts = rec.num_points3D()
    log(f"Selected best reconstruction: {n_reg}/{n_photos} photos registered, {n_pts} 3D points triangulated.")

    if n_reg < 3 or n_pts < 10:
        err = f"Degenerate reconstruction: only {n_reg} photos registered and {n_pts} points found."
        log(f"ERROR: {err}")
        return _make_error_result(log_lines, t0, n_photos, err)

    # STAGE 4: Exporting PLY and Camera Poses
    report_stage("Exporting Point Cloud & Camera Geometry", 0.90)

    ply_path = output_dir / "sparse_points.ply"
    try:
        rec.export_PLY(str(ply_path))
        log(f"Exported PLY to {ply_path.name}")
    except Exception as e:
        log(f"Warning: export_PLY failed: {e}. Triangulating directly from memory.")

    pts_list = []
    clr_list = []
    for pt in rec.points3D.values():
        pts_list.append(pt.xyz)
        clr_list.append(pt.color)

    if pts_list:
        points_np = np.asarray(pts_list, dtype=np.float32)
        colors_np = np.asarray(clr_list, dtype=np.uint8)
    else:
        points_np = np.zeros((0, 3), dtype=np.float32)
        colors_np = np.zeros((0, 3), dtype=np.uint8)

    cameras: list[CameraPose] = []
    for img_id, img in rec.images.items():
        try:
            if img.has_pose:
                center = list(map(float, img.projection_center()))
                direction = list(map(float, img.viewing_direction()))
                cameras.append(CameraPose(
                    id=int(img_id),
                    name=str(img.name),
                    center=center,
                    direction=direction,
                ))
        except Exception:
            pass

    cameras_json_path = output_dir / "cameras.json"
    with open(cameras_json_path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in cameras], f, indent=2)

    mean_reproj = 0.0
    try:
        mean_reproj = float(rec.compute_mean_reprojection_error())
        log(f"Mean reprojection error: {mean_reproj:.2f} px")
    except Exception:
        pass

    if n_reg < n_photos:
        warnings.append(f"{n_photos - n_reg} of {n_photos} photographs could not be registered due to insufficient feature matches.")

    duration = time.time() - t0
    log(f"Reconstruction completed in {duration:.1f}s.")
    report_stage("Completed", 1.0)

    return ReconstructionResult(
        success=True,
        points=points_np,
        colors=colors_np,
        cameras=cameras,
        num_input_images=n_photos,
        num_reg_images=n_reg,
        num_points=len(points_np),
        mean_reprojection_error=mean_reproj,
        ply_path=str(ply_path),
        cameras_json_path=str(cameras_json_path),
        duration_sec=duration,
        log="\n".join(log_lines),
        warning_messages=warnings,
        effective_max_dim=max_image_dim,
        num_threads_used=max_threads,
    )


def _make_error_result(log_lines: list[str], t0: float, n_photos: int, err: str) -> ReconstructionResult:
    return ReconstructionResult(
        success=False,
        points=np.zeros((0, 3), dtype=np.float32),
        colors=np.zeros((0, 3), dtype=np.uint8),
        cameras=[],
        num_input_images=n_photos,
        num_reg_images=0,
        num_points=0,
        mean_reprojection_error=0.0,
        ply_path=None,
        cameras_json_path=None,
        duration_sec=time.time() - t0,
        log="\n".join(log_lines),
        error_message=err,
    )


def _make_cancelled_result(log_lines: list[str], t0: float, n_photos: int) -> ReconstructionResult:
    return ReconstructionResult(
        success=False,
        points=np.zeros((0, 3), dtype=np.float32),
        colors=np.zeros((0, 3), dtype=np.uint8),
        cameras=[],
        num_input_images=n_photos,
        num_reg_images=0,
        num_points=0,
        mean_reprojection_error=0.0,
        ply_path=None,
        cameras_json_path=None,
        duration_sec=time.time() - t0,
        log="\n".join(log_lines),
        error_message="Reconstruction was cancelled by the user.",
    )
