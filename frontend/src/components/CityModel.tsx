import { memo, useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { BASEMAP } from "../lib/basemap";
import type { CityBuilding } from "../api";

// ---- projection: WGS84 → local scene metres, centred on Toronto ----
const LAT0 = 43.705;
const LNG0 = -79.38;
const SCALE = 26;
function project(lat: number, lng: number): [number, number] {
  const x = ((lng - LNG0) * Math.cos((LAT0 * Math.PI) / 180) * 111320) / SCALE;
  const z = (-(lat - LAT0) * 110540) / SCALE;
  return [x, z];
}

export const BAND_COLOR: Record<string, string> = {
  Low: "#76b900", Moderate: "#d6c12a", Elevated: "#e08a2e",
  High: "#e2563a", Severe: "#bf2e1a", Unknown: "#39432d",
};

interface RB { i: number; x: number; z: number; h: number; color: THREE.Color; b: CityBuilding }
interface Scene3D { mesh: THREE.InstancedMesh; data: RB[]; dummy: THREE.Object3D }

// Vanilla three.js (not react-three-fiber): initialises in a useEffect regardless
// of tab visibility, with a manual render loop + a hidden-tab fallback tick.
export const CityModel = memo(function CityModel({ buildings, minScore, includeUnknown, demoRsns, onPick, onHover }: {
  buildings: CityBuilding[];
  minScore: number;
  includeUnknown: boolean;
  demoRsns: Set<string>;
  onPick: (b: CityBuilding) => void;
  onHover: (b: CityBuilding | null) => void;
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<Scene3D | null>(null);
  const cbRef = useRef({ onPick, onHover });
  cbRef.current = { onPick, onHover };

  // ---- build the scene once (when buildings arrive) ----
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || buildings.length === 0) return;
    const W = mount.clientWidth || window.innerWidth;
    const H = mount.clientHeight || window.innerHeight;

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.setSize(W, H);
    renderer.setClearColor(0x05070a, 1);
    renderer.domElement.style.cursor = "grab";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x05070a, 1500, 3600);
    const camera = new THREE.PerspectiveCamera(48, W / H, 1, 7000);
    camera.position.set(300, 330, 520);

    scene.add(new THREE.AmbientLight(0xffffff, 0.78));
    const d1 = new THREE.DirectionalLight(0xffffff, 1.2); d1.position.set(300, 600, 250); scene.add(d1);
    const d2 = new THREE.DirectionalLight(0x5bb3c9, 0.35); d2.position.set(-300, 300, -200); scene.add(d2);

    // real dark Toronto basemap (OSM/CARTO) as the ground — geo-aligned so towers
    // sit on their actual streets and Lake Ontario reads to the south.
    const tex = new THREE.TextureLoader().load(BASEMAP.src);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy ? renderer.capabilities.getMaxAnisotropy() : 4;
    const [xW, zN] = project(BASEMAP.maxLat, BASEMAP.minLng);
    const [xE, zS] = project(BASEMAP.minLat, BASEMAP.maxLng);
    const basemap = new THREE.Mesh(
      new THREE.PlaneGeometry(xE - xW, zS - zN),
      new THREE.MeshBasicMaterial({ map: tex }),
    );
    basemap.rotation.x = -Math.PI / 2;
    basemap.position.set((xW + xE) / 2, -0.5, (zN + zS) / 2);
    scene.add(basemap);
    // a vast black skirt beneath so the horizon reads black, never green
    const skirt = new THREE.Mesh(new THREE.PlaneGeometry(16000, 16000), new THREE.MeshBasicMaterial({ color: 0x05070a }));
    skirt.rotation.x = -Math.PI / 2; skirt.position.set((xW + xE) / 2, -1.2, (zN + zS) / 2); scene.add(skirt);

    // buildings → instanced mesh
    const data: RB[] = buildings.filter((b) => b.lat != null && b.lng != null).map((b, i) => {
      const [x, z] = project(b.lat as number, b.lng as number);
      const storeys = b.storeys || 2;
      return { i, x, z, h: Math.max(8, storeys * 4.5), color: new THREE.Color(BAND_COLOR[b.risk_level || "Unknown"] || BAND_COLOR.Unknown), b };
    });
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.05, transparent: true, opacity: 0.75 });
    const mesh = new THREE.InstancedMesh(geo, mat, data.length);
    mesh.frustumCulled = false;
    const dummy = new THREE.Object3D();
    data.forEach((d) => {
      dummy.position.set(d.x, d.h / 2, d.z);
      dummy.scale.set(6, d.h, 6);
      dummy.updateMatrix();
      mesh.setMatrixAt(d.i, dummy.matrix);
      mesh.setColorAt(d.i, d.color);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    scene.add(mesh);
    sceneRef.current = { mesh, data, dummy };

    // demo markers (pulsing cones)
    const demoGroup = new THREE.Group();
    data.filter((d) => demoRsns.has(d.b.rsn)).forEach((d) => {
      const m = new THREE.Mesh(new THREE.ConeGeometry(5, 11, 4), new THREE.MeshBasicMaterial({ color: 0x8ed600 }));
      m.position.set(d.x, d.h + 16, d.z); m.rotation.x = Math.PI; demoGroup.add(m);
    });
    scene.add(demoGroup);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(50, 10, -10);
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.autoRotate = true; controls.autoRotateSpeed = 0.3;
    controls.minDistance = 90; controls.maxDistance = 1700; controls.maxPolarAngle = Math.PI / 2.12;
    controls.update();

    // raycasting for hover + click
    const raycaster = new THREE.Raycaster();
    const ptr = new THREE.Vector2();
    let hoverRsn = "";
    const hit = (e: PointerEvent | MouseEvent): CityBuilding | null => {
      const r = renderer.domElement.getBoundingClientRect();
      ptr.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      ptr.y = -((e.clientY - r.top) / r.height) * 2 + 1;
      raycaster.setFromCamera(ptr, camera);
      const x = raycaster.intersectObject(mesh)[0];
      return x && x.instanceId != null ? data[x.instanceId].b : null;
    };
    const onMove = (e: PointerEvent) => {
      const b = hit(e);
      const rsn = b ? b.rsn : "";
      if (rsn !== hoverRsn) { hoverRsn = rsn; cbRef.current.onHover(b); renderer.domElement.style.cursor = b ? "pointer" : "grab"; }
    };
    const onClick = (e: MouseEvent) => { const b = hit(e); if (b) cbRef.current.onPick(b); };
    renderer.domElement.addEventListener("pointermove", onMove);
    renderer.domElement.addEventListener("click", onClick);

    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      if (w && h) { camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h); }
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(mount);

    // render loop (rAF) + hidden-tab fallback so the city never goes black
    let raf = 0;
    const animate = () => { controls.update(); renderer.render(scene, camera); raf = requestAnimationFrame(animate); };
    animate();
    let hiddenTimer: ReturnType<typeof setInterval> | null = null;
    const onVis = () => {
      if (document.hidden && !hiddenTimer) hiddenTimer = setInterval(() => { controls.update(); renderer.render(scene, camera); }, 200);
      else if (!document.hidden && hiddenTimer) { clearInterval(hiddenTimer); hiddenTimer = null; }
    };
    document.addEventListener("visibilitychange", onVis);
    onVis();

    return () => {
      cancelAnimationFrame(raf);
      if (hiddenTimer) clearInterval(hiddenTimer);
      document.removeEventListener("visibilitychange", onVis);
      ro.disconnect();
      renderer.domElement.removeEventListener("pointermove", onMove);
      renderer.domElement.removeEventListener("click", onClick);
      controls.dispose();
      mesh.dispose(); geo.dispose(); mat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
      sceneRef.current = null;
    };
  }, [buildings, demoRsns]);

  // ---- apply the risk filter (visibility) without rebuilding ----
  useEffect(() => {
    const s = sceneRef.current;
    if (!s) return;
    const { mesh, data, dummy } = s;
    data.forEach((d) => {
      const vis = d.b.score != null ? d.b.score >= minScore : includeUnknown;
      dummy.position.set(d.x, vis ? d.h / 2 : -99999, d.z);
      dummy.scale.set(6, vis ? d.h : 0.001, 6);
      dummy.updateMatrix();
      mesh.setMatrixAt(d.i, dummy.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
  }, [minScore, includeUnknown, buildings]);

  return <div ref={mountRef} style={{ position: "absolute", inset: 0 }} />;
});
