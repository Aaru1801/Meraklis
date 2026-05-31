import { memo, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import * as THREE from "three";
import type { CityBuilding } from "../api";

export const BAND_COLOR: Record<string, string> = {
  Low: "#76b900", Moderate: "#d6c12a", Elevated: "#e08a2e",
  High: "#e2563a", Severe: "#bf2e1a", Unknown: "#5b6b46",
};

const RISK_COLOR: maplibregl.ExpressionSpecification = [
  "match", ["get", "risk"],
  "Low", BAND_COLOR.Low, "Moderate", BAND_COLOR.Moderate, "Elevated", BAND_COLOR.Elevated,
  "High", BAND_COLOR.High, "Severe", BAND_COLOR.Severe, BAND_COLOR.Unknown,
];
const RISK_VE = 1.3;
const DIM_OPACITY = 0.75; // every building 75% opaque; hovered/selected → full

type LandmarkPayload = {
  landmarks: { name: string; anchor: [number, number]; v: number[] }[];
};

const LANDMARK_STYLE: Record<string, { fill: number; edge: number; opacity: number }> = {
  "CN Tower": { fill: 0xd6ded2, edge: 0xf1f6ed, opacity: 0.98 },
  "Rogers Centre": { fill: 0x9aa8a8, edge: 0xd7dfdd, opacity: 0.94 },
  "Old City Hall": { fill: 0xb69c77, edge: 0xead6b2, opacity: 0.95 },
  "Union Station": { fill: 0xb9aa8f, edge: 0xe8dcc6, opacity: 0.94 },
  "Royal Ontario Museum": { fill: 0x92a5b5, edge: 0xdce8ef, opacity: 0.94 },
  "Casa Loma": { fill: 0xa68f6f, edge: 0xe2d0ae, opacity: 0.95 },
};

function createLandmarkLayer(): maplibregl.CustomLayerInterface {
  let map: maplibregl.Map | null = null;
  let renderer: THREE.WebGLRenderer | null = null;
  let scene: THREE.Scene | null = null;
  let camera: THREE.Camera | null = null;
  const resources: { geometry: THREE.BufferGeometry; material: THREE.Material }[] = [];

  const addMesh = (landmark: LandmarkPayload["landmarks"][number]) => {
    if (!scene) return;
    const raw = landmark.v;
    const positions = new Float32Array(raw.length);
    for (let i = 0; i < raw.length; i += 3) {
      const c = maplibregl.MercatorCoordinate.fromLngLat(
        [raw[i], raw[i + 1]],
        Math.max(0, raw[i + 2]) * RISK_VE,
      );
      positions[i] = c.x;
      positions[i + 1] = c.y;
      positions[i + 2] = c.z;
    }

    const style = LANDMARK_STYLE[landmark.name] ?? { fill: 0xb8c6ac, edge: 0xe5f2dc, opacity: 0.95 };
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();

    const material = new THREE.MeshStandardMaterial({
      color: style.fill,
      roughness: 0.62,
      metalness: 0.04,
      transparent: true,
      opacity: style.opacity,
      side: THREE.DoubleSide,
      depthTest: true,
      depthWrite: true,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.frustumCulled = false;
    scene.add(mesh);
    resources.push({ geometry, material });

    const edges = new THREE.EdgesGeometry(geometry, 34);
    const edgeMaterial = new THREE.LineBasicMaterial({
      color: style.edge,
      transparent: true,
      opacity: 0.28,
      depthTest: true,
      depthWrite: false,
    });
    const lines = new THREE.LineSegments(edges, edgeMaterial);
    lines.frustumCulled = false;
    scene.add(lines);
    resources.push({ geometry: edges, material: edgeMaterial });
  };

  return {
    id: "landmarks",
    type: "custom",
    renderingMode: "3d",
    onAdd(nextMap, gl) {
      map = nextMap;
      camera = new THREE.Camera();
      scene = new THREE.Scene();
      scene.add(new THREE.AmbientLight(0xffffff, 1.15));
      const key = new THREE.DirectionalLight(0xffffff, 1.45);
      key.position.set(0.35, -0.45, 0.8);
      scene.add(key);
      const rim = new THREE.DirectionalLight(0x8bb2ff, 0.6);
      rim.position.set(-0.5, 0.35, 0.45);
      scene.add(rim);

      renderer = new THREE.WebGLRenderer({
        canvas: nextMap.getCanvas(),
        context: gl,
      });
      renderer.autoClear = false;
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      void fetch("/landmarks.json")
        .then((r) => {
          if (!r.ok) throw new Error(`landmarks.json ${r.status}`);
          return r.json() as Promise<LandmarkPayload>;
        })
        .then((payload) => {
          payload.landmarks.forEach(addMesh);
          map?.triggerRepaint();
        })
        .catch((err) => console.warn("[maplibre] landmark meshes unavailable", err));
    },
    render(_gl, options) {
      if (!renderer || !scene || !camera) return;
      camera.projectionMatrix.fromArray(options.modelViewProjectionMatrix as ArrayLike<number>);
      camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
      renderer.resetState();
      renderer.render(scene, camera);
      renderer.resetState();
    },
    onRemove() {
      resources.forEach((r) => { r.geometry.dispose(); r.material.dispose(); });
      resources.length = 0;
      renderer?.dispose();
      renderer = null;
      scene = null;
      camera = null;
      map = null;
    },
  };
}

let _pmReady = false;
function ensurePmtiles() {
  if (_pmReady) return;
  maplibregl.addProtocol("pmtiles", new Protocol().tile);
  _pmReady = true;
}

function buildStyle(): maplibregl.StyleSpecification {
  const o = window.location.origin;
  return {
    version: 8,
    name: "Meraklis Toronto",
    glyphs: o + "/fonts/{fontstack}/{range}.pbf",
    sources: { toronto: { type: "vector", url: "pmtiles://" + o + "/toronto.pmtiles" } },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#0a0d07" } },
      {
        id: "road", type: "line", source: "toronto", "source-layer": "road",
        paint: { "line-color": "#283120", "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.3, 13, 1.0, 16, 3.0] },
      },
      {
        // Every ordinary building stays in MapLibre for reliable navigation.
        // Landmark footprints are filtered out and replaced by detailed meshes.
        id: "building", type: "fill-extrusion", source: "toronto", "source-layer": "building", minzoom: 12,
        paint: {
          "fill-extrusion-color": "#2a3320",
          "fill-extrusion-height": ["*", ["coalesce", ["get", "h"], 6], RISK_VE],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": DIM_OPACITY,
        },
        filter: ["!=", ["get", "lm"], 1],
      },
      {
        id: "road-label", type: "symbol", source: "toronto", "source-layer": "road", minzoom: 13.5,
        layout: { "symbol-placement": "line", "text-field": ["get", "name"], "text-font": ["Open Sans Regular"], "text-size": 11, "symbol-spacing": 320 },
        paint: { "text-color": "#91a774", "text-halo-color": "#0a0d07", "text-halo-width": 1.4 },
      },
    ],
  };
}


export const MapCity = memo(function MapCity({ minScore, includeUnknown, onPick, onHover, me }: {
  minScore: number;
  includeUnknown: boolean;
  demoRsns: Set<string>;
  me?: { lat: number; lng: number } | null;
  onPick: (b: CityBuilding) => void;
  onHover: (b: CityBuilding | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const refreshRef = useRef<(() => void) | null>(null);
  const meMarkerRef = useRef<maplibregl.Marker | null>(null);
  const filt = useRef({ minScore, includeUnknown });
  filt.current = { minScore, includeUnknown };
  const [loading, setLoading] = useState(true);
  const cb = useRef({ onPick, onHover });
  cb.current = { onPick, onHover };

  useEffect(() => {
    if (!ref.current) return;
    ensurePmtiles();
    const map = new maplibregl.Map({
      container: ref.current, style: buildStyle(),
      center: [-79.383, 43.652], zoom: 13.2, pitch: 58, bearing: -17, maxPitch: 78, attributionControl: false,
      minZoom: 11.5,
      maxBounds: [[-79.6392, 43.5810], [-79.1152, 43.8554]], // Constrain to Toronto bounds
    });
    mapRef.current = map;
    (window as unknown as { __m: maplibregl.Map }).__m = map;
    map.on("error", (e) => console.error("[maplibre]", (e && e.error && e.error.message) || e));
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "City of Toronto Open Data · RentSafeTO · 3D Massing" }), "bottom-left");
    const spinnerTimeout = setTimeout(() => setLoading(false), 12000);

    const toCity = (p: Record<string, unknown>): CityBuilding => ({
      rsn: String(p.rsn), address: String(p.address ?? ""), ward: (p.ward as string) ?? null,
      lat: null, lng: null, storeys: (p.storeys as number) ?? null, units: (p.units as number) ?? null,
      year_built: null, score: (p.score as number) ?? null, grade: (p.grade as string) ?? null,
      risk_level: (p.risk as string) ?? null,
    });

    let hoverRsn: string | null = null;
    let selectRsn: string | null = null;
    const setState = (rsn: string | null, key: "hover" | "select", on: boolean) => {
      if (rsn != null) map.setFeatureState({ source: "rsto", id: rsn }, { [key]: on });
    };
    // route the active (hover/select) building to the full-opacity layer; others stay 75%
    const refresh = () => {
      if (!map.getLayer("risk")) return;
      const cs: maplibregl.ExpressionSpecification = ["coalesce", ["get", "score"], -1];
      const sf: maplibregl.ExpressionSpecification = filt.current.includeUnknown
        ? ["any", [">=", cs, filt.current.minScore], ["==", cs, -1]]
        : [">=", cs, filt.current.minScore];
      const active = [...new Set([hoverRsn, selectRsn].filter(Boolean) as string[])];
      const inActive: maplibregl.ExpressionSpecification = ["in", ["get", "rsn"], ["literal", active]];
      map.setFilter("risk", active.length ? ["all", sf, ["!", inActive]] : sf);
      map.setFilter("risk-hi", active.length ? (["all", sf, inActive] as maplibregl.FilterSpecification) : ["==", ["get", "rsn"], "__none__"]);
    };
    refreshRef.current = refresh;

    map.on("load", () => {
      map.addLayer(createLandmarkLayer(), "road-label");
      map.addSource("rsto", { type: "geojson", data: "/buildings.geojson", promoteId: "rsn" });
      const heightExpr: maplibregl.ExpressionSpecification = ["*", ["coalesce", ["get", "height"], 9], RISK_VE];
      // base risk buildings at 75%
      map.addLayer({
        id: "risk", type: "fill-extrusion", source: "rsto",
        paint: { "fill-extrusion-color": RISK_COLOR, "fill-extrusion-height": heightExpr, "fill-extrusion-base": 0, "fill-extrusion-opacity": DIM_OPACITY },
      });
      // full-opacity layer for the hovered/selected building (highlight colour)
      map.addLayer({
        id: "risk-hi", type: "fill-extrusion", source: "rsto",
        filter: ["==", ["get", "rsn"], "__none__"],
        paint: {
          "fill-extrusion-color": ["case", ["boolean", ["feature-state", "select"], false], "#ffffff", ["boolean", ["feature-state", "hover"], false], "#b6f00a", RISK_COLOR],
          "fill-extrusion-height": heightExpr, "fill-extrusion-base": 0, "fill-extrusion-opacity": 1.0,
        },
      });
      // All non-landmark city buildings render via the MapLibre "building"
      // fill-extrusion in the style above. Iconic buildings use their detailed
      // City multipatch meshes in the custom layer so their silhouettes read.

      const pick = (e: maplibregl.MapLayerMouseEvent) => e.features?.[0];
      map.on("mousemove", "risk", (e) => {
        const f = pick(e); if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const rsn = (f.id as string) ?? (f.properties as { rsn: string }).rsn;
        if (rsn !== hoverRsn) { setState(hoverRsn, "hover", false); hoverRsn = rsn; setState(hoverRsn, "hover", true); refresh(); }
        cb.current.onHover(toCity(f.properties as Record<string, unknown>));
      });
      map.on("mouseleave", "risk", () => { map.getCanvas().style.cursor = ""; setState(hoverRsn, "hover", false); hoverRsn = null; refresh(); cb.current.onHover(null); });
      map.on("click", "risk", (e) => {
        const f = pick(e); if (!f) return;
        setState(selectRsn, "select", false); selectRsn = (f.id as string) ?? (f.properties as { rsn: string }).rsn; setState(selectRsn, "select", true); refresh();
        cb.current.onPick(toCity(f.properties as Record<string, unknown>));
      });

      readyRef.current = true;
      clearTimeout(spinnerTimeout);
      setLoading(false);
      refresh();
    });

    return () => { clearTimeout(spinnerTimeout); map.remove(); mapRef.current = null; readyRef.current = false; refreshRef.current = null; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (readyRef.current && refreshRef.current) refreshRef.current();
  }, [minScore, includeUnknown, loading]);

  // "Near me": drop a marker at the user and fly there (also stops the idle spin).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !me) return;
    const place = () => {
      map.fire("dragstart"); // triggers the existing stop-spin handler
      meMarkerRef.current?.remove();
      meMarkerRef.current = new maplibregl.Marker({ color: "#4aa3ff" })
        .setLngLat([me.lng, me.lat]).addTo(map);
      map.flyTo({ center: [me.lng, me.lat], zoom: 15, pitch: 55, essential: true });
    };
    if (readyRef.current) place();
    else map.once("load", place);
  }, [me]);

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div ref={ref} style={{ position: "absolute", inset: 0 }} />
      {loading && (
        <div className="col" style={{ position: "absolute", inset: 0, placeItems: "center", justifyContent: "center", gap: 12, background: "#0a0d07", color: "var(--faint)", pointerEvents: "none" }}>
          <div style={{ width: 34, height: 34, borderRadius: "50%", border: "3px solid var(--border-2)", borderTopColor: "var(--green)" }} className="spin" />
          <span className="mono" style={{ fontSize: 12 }}>loading the 3D city…</span>
        </div>
      )}
    </div>
  );
});
