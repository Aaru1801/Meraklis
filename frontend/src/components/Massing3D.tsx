import { useMemo } from "react";

// Isometric extrusion of a real footprint ring (local ground-metres) to height.
const ISO = Math.PI / 6;
const COS = Math.cos(ISO);
const SIN = Math.sin(ISO);

export function Massing3D({ footprint, height, w = 300, h = 210 }: {
  footprint: number[][]; height: number; w?: number; h?: number;
}) {
  const geo = useMemo(() => {
    if (footprint.length < 3) return null;
    const PAD = 22;
    const iso = (x: number, y: number, z: number) => ({ x: (x - y) * COS, y: (x + y) * SIN - z });
    const base = footprint.map((p) => iso(p[0], p[1], 0));
    const roof = footprint.map((p) => iso(p[0], p[1], height));
    const all = [...base, ...roof];
    const minX = Math.min(...all.map((p) => p.x)), maxX = Math.max(...all.map((p) => p.x));
    const minY = Math.min(...all.map((p) => p.y)), maxY = Math.max(...all.map((p) => p.y));
    const scale = Math.min((w - 2 * PAD) / (maxX - minX || 1), (h - 2 * PAD) / (maxY - minY || 1));
    const ox = PAD - minX * scale + (w - 2 * PAD - (maxX - minX) * scale) / 2;
    const oy = PAD - minY * scale + (h - 2 * PAD - (maxY - minY) * scale) / 2;
    const tf = (p: { x: number; y: number }) => ({ x: ox + p.x * scale, y: oy + p.y * scale });
    const B = base.map(tf), R = roof.map(tf);
    const n = footprint.length;
    const walls: { pts: string; depth: number; right: boolean }[] = [];
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      walls.push({
        pts: `${B[i].x},${B[i].y} ${B[j].x},${B[j].y} ${R[j].x},${R[j].y} ${R[i].x},${R[i].y}`,
        depth: footprint[i][0] + footprint[i][1] + footprint[j][0] + footprint[j][1],
        right: R[j].x - R[i].x >= 0,
      });
    }
    walls.sort((a, b) => a.depth - b.depth);
    const rear = footprint.reduce((m, _p, i, a) => (a[i][0] + a[i][1] < a[m][0] + a[m][1] ? i : m), 0);
    return { walls, roof: R.map((p) => `${p.x},${p.y}`).join(" "), base: B.map((p) => `${p.x},${p.y}`).join(" "), dim: { base: B[rear], roof: R[rear] } };
  }, [footprint, height, w, h]);

  if (!geo) return null;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ display: "block", width: "100%", height: "auto" }}>
      <polygon points={geo.base} fill="rgba(118,185,0,.07)" stroke="var(--border-2)" strokeWidth={1} />
      {geo.walls.map((wl, i) => (
        <polygon key={i} points={wl.pts} fill={wl.right ? "var(--green-deep)" : "#3a6206"} stroke="var(--bg)" strokeWidth={0.6} strokeLinejoin="round" />
      ))}
      <polygon points={geo.roof} fill="var(--green-2)" stroke="var(--bg)" strokeWidth={0.8} strokeLinejoin="round" />
      <line x1={geo.dim.base.x} y1={geo.dim.base.y} x2={geo.dim.roof.x} y2={geo.dim.roof.y} stroke="var(--c-tool)" strokeWidth={1} strokeDasharray="3 3" />
      <circle cx={geo.dim.roof.x} cy={geo.dim.roof.y} r={2} fill="var(--c-tool)" />
    </svg>
  );
}
