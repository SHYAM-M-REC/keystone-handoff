import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { getMonth, maxPoints } from "../data/loader.js";

// diverging scale: blue (moved one way) - pale stone - vermilion (moved the other way)
const NEG = [48, 120, 190], MID = [214, 222, 222], POS = [232, 84, 36];
const QUIET = [112, 108, 98], VOID = [4, 6, 8];
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

function colourFor(kind, q) {
  if (kind === 2) return VOID;
  if (kind === 0) return QUIET;
  const mm = q / 5;                                   // 0.2 mm units
  const t = Math.max(-1, Math.min(1, mm / 25));
  const s = Math.sign(t) * Math.pow(Math.abs(t), 0.75);
  return s < 0 ? mix(MID, NEG, -s) : mix(MID, POS, s);
}

/** The simulated temple as a point cloud. Imperative three.js inside a React shell. */
export default function Scene({ month, exag, autoRotate = false, interactive = true, ghost = false, pointSize = 0.055, fov = 38, distance = 1, shiftX = 0 }) {
  const mount = useRef(null);
  const api = useRef({});

  useEffect(() => {
    const el = mount.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 200);
    camera.up.set(0, 0, 1);
    camera.position.set(-15 * distance, -19 * distance, 10.5 * distance);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    el.appendChild(renderer.domElement);
    renderer.domElement.style.display = "block";

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.4, 4.4);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.enableZoom = interactive;
    controls.enableRotate = interactive;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.7;
    controls.minDistance = 10;
    controls.maxDistance = 60;
    controls.maxPolarAngle = Math.PI * 0.62;

    const mk = (size, opacity) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(maxPoints * 3), 3));
      g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(maxPoints * 3), 3));
      const m = new THREE.PointsMaterial({ size, vertexColors: true, sizeAttenuation: true, transparent: opacity < 1, opacity, depthWrite: opacity >= 1 });
      const p = new THREE.Points(g, m);
      p.frustumCulled = false;
      scene.add(p);
      return p;
    };
    const main = mk(pointSize, 1);
    const ghostPts = mk(pointSize * 0.8, 0.16);
    ghostPts.visible = false;

    // ground grid, faint, like a survey sheet
    const grid = new THREE.GridHelper(24, 24, 0x3a434a, 0x242b31);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -0.02;
    scene.add(grid);

    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = w / Math.max(h, 1);
      if (shiftX) camera.setViewOffset(w, h, -w * shiftX, 0, w, h);
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    let raf;
    const loop = () => {
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    loop();

    api.current = { main, ghostPts, controls };
    api.current.fill = (pts, m, ex, withColour) => {
      const d = getMonth(m);
      const P = pts.geometry.attributes.position.array;
      const C = pts.geometry.attributes.color.array;
      for (let i = 0; i < d.n; i++) {
        const i3 = i * 3;
        P[i3] = (d.pos[i3] * 0.5 + (ex * d.disp[i3]) / 100) * 0.001;
        P[i3 + 1] = (d.pos[i3 + 1] * 0.5 + (ex * d.disp[i3 + 1]) / 100) * 0.001;
        P[i3 + 2] = (d.pos[i3 + 2] * 0.5 + (ex * d.disp[i3 + 2]) / 100) * 0.001;
        const c = withColour ? colourFor(d.kind[i], d.q[i]) : QUIET;
        C[i3] = c[0] / 255; C[i3 + 1] = c[1] / 255; C[i3 + 2] = c[2] / 255;
      }
      pts.geometry.setDrawRange(0, d.n);
      pts.geometry.attributes.position.needsUpdate = true;
      pts.geometry.attributes.color.needsUpdate = true;
    };
    api.current.fill(ghostPts, 0, 0, false);
    api.current.fill(main, month, exag, true);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      main.geometry.dispose(); ghostPts.geometry.dispose();
      el.removeChild(renderer.domElement);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (api.current.fill) api.current.fill(api.current.main, month, exag, true);
  }, [month, exag]);

  useEffect(() => {
    if (api.current.ghostPts) api.current.ghostPts.visible = ghost;
  }, [ghost]);

  useEffect(() => {
    if (api.current.controls) api.current.controls.autoRotate = autoRotate;
  }, [autoRotate]);

  return <div ref={mount} className="scene" />;
}
