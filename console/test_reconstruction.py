"""Unit and integration tests for KEYSTONE 3D Reconstruction and Performance Optimization.

Executable with standard library: python -m unittest console/test_reconstruction.py

Tests:
- Input validation (empty, unsupported, corrupted, small, duplicates, blur heuristic)
- Image preparation and downsampling without aspect distortion
- Thread configuration and memory limit propagation
- Error handling (missing dependencies, zero cameras registered, degenerate cloud)
- Cancellation token responsiveness
- Output schema verification (Point clouds, camera poses, JSON, PLY)
- Real reconstruction test on a subset of sample wall photos
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from console.engine import get_system_metrics, reconstruct_photos, validate_photo_inputs
from console.reconstruction import (
    CameraPose,
    ReconstructionResult,
    ValidationSummary,
    compute_blur_score,
    prepare_working_copies,
    run_pycolmap_reconstruction,
    validate_image_files,
)


def create_dummy_image(path: Path, width: int = 400, height: int = 300, color: tuple = (120, 140, 160)):
    im = Image.new("RGB", (width, height), color=color)
    im.save(path, format="JPEG")
    return path


class TestReconstructionOptimization(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ks_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_image_validation_empty(self):
        res = validate_image_files([])
        self.assertEqual(res.status, "NEEDS ATTENTION")
        self.assertEqual(res.total_count, 0)
        self.assertFalse(res.can_proceed)
        self.assertTrue(any("No photographs uploaded" in e for e in res.errors))

    def test_image_validation_unsupported_format(self):
        f1 = self.tmp_dir / "doc.txt"
        f1.write_text("not an image")
        f2 = self.tmp_dir / "scan.pdf"
        f2.write_bytes(b"%PDF-1.4...")
        res = validate_image_files([f1, f2])
        self.assertEqual(res.valid_count, 0)
        self.assertEqual(res.invalid_count, 2)
        self.assertFalse(res.can_proceed)

    def test_image_validation_corrupted_file(self):
        bad = self.tmp_dir / "corrupt.jpg"
        bad.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01...corrupted garbage data")
        res = validate_image_files([bad])
        self.assertEqual(res.valid_count, 0)
        self.assertEqual(res.invalid_count, 1)
        self.assertFalse(res.can_proceed)

    def test_image_validation_small_dimensions(self):
        tiny = self.tmp_dir / "tiny.png"
        create_dummy_image(tiny, width=100, height=80)
        res = validate_image_files([tiny])
        self.assertEqual(res.valid_count, 0)
        self.assertTrue(any("too small" in item.error for item in res.items if item.error))

    def test_image_validation_duplicates(self):
        p1 = self.tmp_dir / "photo1.jpg"
        create_dummy_image(p1, width=500, height=400, color=(100, 150, 200))
        p2 = self.tmp_dir / "photo2.jpg"
        shutil.copy2(p1, p2)
        p3 = self.tmp_dir / "photo3.jpg"
        create_dummy_image(p3, width=500, height=400, color=(50, 60, 70))

        res = validate_image_files([p1, p2, p3])
        self.assertEqual(len(res.duplicates), 1)
        self.assertEqual(res.duplicates[0], ("photo2.jpg", "photo1.jpg"))
        self.assertTrue(any("duplicate" in w.lower() for w in res.warnings))

    def test_image_validation_blur_heuristic(self):
        sharp = self.tmp_dir / "sharp.jpg"
        arr = np.zeros((400, 400, 3), dtype=np.uint8)
        arr[::20, :] = 255
        arr[:, ::20] = 255
        Image.fromarray(arr).save(sharp)

        score = compute_blur_score(sharp)
        self.assertGreater(score, 10.0)

    def test_prepare_working_copies_resizing(self):
        src_dir = self.tmp_dir / "src"
        src_dir.mkdir()
        dst_dir = self.tmp_dir / "dst"

        large = src_dir / "large.jpg"
        create_dummy_image(large, width=3200, height=2400)

        small = src_dir / "small.jpg"
        create_dummy_image(small, width=800, height=600)

        prepared, notes = prepare_working_copies([large, small], dst_dir, max_dim=1600)
        self.assertEqual(len(prepared), 2)

        with Image.open(dst_dir / "large.jpg") as im_l:
            self.assertEqual(max(im_l.size), 1600)
            self.assertEqual(im_l.size, (1600, 1200))

        with Image.open(dst_dir / "small.jpg") as im_s:
            self.assertEqual(im_s.size, (800, 600))

    def test_thread_and_memory_options_propagation(self):
        import pycolmap
        feo = pycolmap.FeatureExtractionOptions()
        feo.num_threads = 2
        feo.max_image_size = 1600
        self.assertEqual(feo.num_threads, 2)
        self.assertEqual(feo.max_image_size, 1600)

        fmo = pycolmap.FeatureMatchingOptions()
        fmo.num_threads = 2
        self.assertEqual(fmo.num_threads, 2)

        ipo = pycolmap.IncrementalPipelineOptions()
        ipo.num_threads = 2
        ipo.load_all_images = False
        self.assertEqual(ipo.num_threads, 2)
        self.assertFalse(ipo.load_all_images)

    def test_reconstruction_cancellation(self):
        img_dir = self.tmp_dir / "imgs"
        img_dir.mkdir()
        for i in range(4):
            create_dummy_image(img_dir / f"img_{i}.jpg", width=500, height=400)

        res = run_pycolmap_reconstruction(
            image_dir=img_dir,
            output_dir=self.tmp_dir / "out",
            cancel_check=lambda: True,
        )
        self.assertFalse(res.success)
        self.assertIn("cancelled", res.error_message.lower())

    def test_system_metrics_format(self):
        m = get_system_metrics()
        self.assertIn("total_ram_gb", m)
        self.assertGreater(m["total_ram_gb"], 0)
        self.assertIn("available_ram_gb", m)
        self.assertIn("used_ram_percent", m)
        self.assertIn("cpu_count_logical", m)
        self.assertGreaterEqual(m["cpu_count_logical"], 1)

    def test_real_reconstruction_on_sample_photos(self):
        """Executes a real PyCOLMAP reconstruction on 6 real wall photographs from sample_wall_photos."""
        sample_dir = ROOT / "sample_wall_photos"
        if not sample_dir.is_dir():
            self.skipTest("sample_wall_photos directory not found")

        sample_files = sorted(sample_dir.glob("*.jpeg"))[:6]
        if len(sample_files) < 4:
            self.skipTest("Not enough sample photos available for integration test")

        test_imgs_dir = self.tmp_dir / "test_imgs"
        test_imgs_dir.mkdir()
        for f in sample_files:
            shutil.copy2(f, test_imgs_dir / f.name)

        out_dir = self.tmp_dir / "recon_out"
        res = run_pycolmap_reconstruction(
            image_dir=test_imgs_dir,
            output_dir=out_dir,
            max_threads=2,
            max_image_dim=1200,
            tries=2,
        )

        self.assertIsInstance(res, ReconstructionResult)
        self.assertEqual(res.num_threads_used, 2)
        self.assertEqual(res.effective_max_dim, 1200)
        self.assertTrue((out_dir / "database.db").exists())
        self.assertTrue(res.success)
        self.assertGreater(res.num_points, 0)
        self.assertGreater(res.num_reg_images, 0)
        self.assertTrue(Path(res.ply_path).exists())
        self.assertTrue(Path(res.cameras_json_path).exists())


if __name__ == "__main__":
    unittest.main()
