// Meraklis — UI primitives (TypeScript port of the design handoff).
import type { CSSProperties, ReactNode } from "react";
import { Icon } from "./icons";
import { useEvidence, evidenceKind } from "./evidence";

/* ---------------- risk / severity maps ---------------- */
export interface GradeMeta { color: string; bg: string; band: string }
export const GRADE: Record<string, GradeMeta> = {
  A: { color: "var(--r-low)", bg: "var(--r-low-bg)", band: "Low risk" },
  B: { color: "var(--r-mod)", bg: "var(--r-mod-bg)", band: "Moderate risk" },
  C: { color: "var(--r-elev)", bg: "var(--r-elev-bg)", band: "Elevated risk" },
  D: { color: "var(--r-high)", bg: "var(--r-high-bg)", band: "High risk" },
  F: { color: "var(--r-high)", bg: "var(--r-high-bg)", band: "Severe risk" },
};
export function gradeMeta(grade: string | null | undefined): GradeMeta {
  return GRADE[grade ?? ""] ?? GRADE.C;
}
export const SEV: Record<string, { color: string; bg: string; label: string }> = {
  critical: { color: "var(--r-high)", bg: "var(--r-high-bg)", label: "CRIT" },
  high: { color: "var(--r-high)", bg: "var(--r-high-bg)", label: "HIGH" },
  moderate: { color: "var(--r-elev)", bg: "var(--r-elev-bg)", label: "MED" },
  minor: { color: "var(--r-mod)", bg: "var(--r-mod-bg)", label: "LOW" },
  info: { color: "var(--c-tool)", bg: "rgba(91,179,201,.13)", label: "INFO" },
};

/* ---------------- brand mark ---------------- */
export function Logo({ size = 26 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
      <span style={{ width: size, height: size, borderRadius: 7, background: "var(--green)", display: "grid", placeItems: "center", position: "relative", boxShadow: "0 0 16px -4px rgba(118,185,0,.6)" }}>
        <span style={{ width: size * 0.34, height: size * 0.34, borderRadius: 99, border: "2.4px solid var(--green-ink)" }} />
        <span style={{ position: "absolute", bottom: size * 0.16, width: 2.4, height: size * 0.26, background: "var(--green-ink)" }} />
      </span>
      <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>Meraklis</span>
    </span>
  );
}

/* ---------------- Pill ---------------- */
export function Pill({ children, color, bg, className = "", style }: {
  children: ReactNode; color?: string; bg?: string; className?: string; style?: CSSProperties;
}) {
  return (
    <span className={"pill " + className} style={{ color: color || "var(--dim)", background: bg || "var(--surface-2)", ...style }}>
      {children}
    </span>
  );
}

/* ---------------- Severity tag ---------------- */
export function SevTag({ sev }: { sev: string }) {
  const s = SEV[sev] || SEV.info;
  return <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, letterSpacing: ".08em", padding: "2px 6px", borderRadius: 4, color: s.color, background: s.bg }}>{s.label}</span>;
}

/* ---------------- Grade badge ---------------- */
export function GradeBadge({ grade, size = 64 }: { grade: string; size?: number }) {
  const g = gradeMeta(grade);
  return (
    <div style={{ width: size, height: size, borderRadius: 12, display: "grid", placeItems: "center", color: g.color, background: g.bg, border: "1px solid color-mix(in oklch," + g.color + " 30%, transparent)", fontWeight: 800, fontSize: size * 0.46, lineHeight: 1 }}>
      {grade}
    </div>
  );
}

/* ---------------- Score gauge (radial 270° arc) ---------------- */
export function ScoreGauge({ value, max = 100, color = "var(--green)", size = 132, label, sub }: {
  value: number; max?: number; color?: string; size?: number; label?: ReactNode; sub?: string;
}) {
  const r = (size - 16) / 2, cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  const sweep = 0.75;
  const pct = Math.max(0, Math.min(1, value / max));
  const dash = circ * sweep;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(135deg)" }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--surface-3)" strokeWidth="9" strokeLinecap="round" strokeDasharray={dash + " " + circ} />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={(dash * pct) + " " + circ} style={{ transition: "stroke-dasharray 1s var(--ease)", filter: "drop-shadow(0 0 6px color-mix(in oklch," + color + " 50%, transparent))" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div className="tabnum" style={{ fontSize: size * 0.3, fontWeight: 800, lineHeight: 1, letterSpacing: "-.02em", color: "var(--text)" }}>{label != null ? label : Math.round(value)}</div>
          {sub && <div className="eyebrow" style={{ marginTop: 5 }}>{sub}</div>}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Sparkline ---------------- */
export function Sparkline({ points, w = 200, h = 48, color = "var(--green)" }: {
  points: number[]; w?: number; h?: number; color?: string;
}) {
  if (points.length < 2) return null;
  const min = Math.min(...points), max = Math.max(...points);
  const span = max - min || 1;
  const step = w / (points.length - 1);
  const xy = points.map((p, i) => [i * step, h - ((p - min) / span) * (h - 8) - 4]);
  const d = xy.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + " L" + w + " " + h + " L0 " + h + " Z";
  const gid = "spk" + color.replace(/\W/g, "");
  return (
    <svg width={w} height={h} style={{ display: "block", overflow: "visible", maxWidth: "100%" }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={"url(#" + gid + ")"} />
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {xy.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r={i === xy.length - 1 ? 3.5 : 0} fill={color} />)}
    </svg>
  );
}

/* ---------------- Meter ---------------- */
export function Meter({ value, max = 1, color = "var(--green)", w }: {
  value: number; max?: number; color?: string; w?: number | string;
}) {
  return <div className="meter" style={{ width: w || "100%" }}><i style={{ width: Math.min(100, (value / max) * 100) + "%", background: color }} /></div>;
}

/* ---------------- Confidence (5-bar) ---------------- */
export function Confidence({ value, showLabel = true }: { value: number; showLabel?: boolean }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "var(--green)" : value >= 0.55 ? "var(--r-mod)" : "var(--r-elev)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }} title={"Model/source confidence " + pct + "%"}>
      <span style={{ display: "inline-flex", gap: 2 }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} style={{ width: 3, height: 10, borderRadius: 1, background: i < Math.round(value * 5) ? color : "var(--surface-3)" }} />
        ))}
      </span>
      {showLabel && <span className="mono" style={{ fontSize: 10.5, color }}>{pct}%</span>}
    </span>
  );
}

/* ---------------- Citation chips ---------------- */
export function Cite({ ids = [] }: { ids?: string[] }) {
  const { map, open } = useEvidence();
  if (!ids.length) return null;
  return (
    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap", verticalAlign: "middle" }}>
      {ids.map((id) => {
        const ev = map.get(id);
        const { color: baseCol } = evidenceKind(ev?.source || id);
        const isWeak = ev != null && ev.confidence < 0.5;
        const col = isWeak ? "var(--r-elev)" : baseCol;
        return (
          <button key={id} className="mono" onClick={() => open(id)} title={ev ? ev.title + " — " + ev.detail : id}
            style={{ fontSize: 9.5, letterSpacing: ".02em", padding: "1px 6px", borderRadius: 4, border: "1px solid color-mix(in oklch," + col + " 30%, transparent)", color: col, background: "color-mix(in oklch," + col + " 9%, transparent)", cursor: "pointer" }}>
            {id}
          </button>
        );
      })}
    </span>
  );
}

/* ---------------- Stat tile ---------------- */
export function Stat({ label, value, unit, sub, color, mono = true }: {
  label: string; value: ReactNode; unit?: string; sub?: string; color?: string; mono?: boolean;
}) {
  return (
    <div className="col" style={{ gap: 3 }}>
      <span className="eyebrow">{label}</span>
      <span className={mono ? "mono tabnum" : "tabnum"} style={{ fontSize: 22, fontWeight: 700, color: color || "var(--text)", lineHeight: 1.1, letterSpacing: "-.01em" }}>
        {value}{unit && <span style={{ fontSize: 12, color: "var(--dim)", fontWeight: 500, marginLeft: 3 }}>{unit}</span>}
      </span>
      {sub && <span className="faint" style={{ fontSize: 11.5 }}>{sub}</span>}
    </div>
  );
}

/* ---------------- Section header ---------------- */
export function SectionHeader({ icon, eyebrow, title, sub, right }: {
  icon?: string; eyebrow?: string; title: string; sub?: string; right?: ReactNode;
}) {
  return (
    <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 18 }}>
      <div className="row gap12" style={{ alignItems: "flex-start" }}>
        {icon && <span style={{ width: 34, height: 34, borderRadius: 9, background: "var(--green-bg)", border: "1px solid var(--border-2)", display: "grid", placeItems: "center", color: "var(--green)" }}><Icon name={icon} size={17} /></span>}
        <div>
          {eyebrow && <div className="eyebrow" style={{ marginBottom: 4 }}>{eyebrow}</div>}
          <h2 style={{ fontSize: 19, fontWeight: 700, letterSpacing: "-.015em" }}>{title}</h2>
          {sub && <p className="dim" style={{ fontSize: 13, marginTop: 4, maxWidth: 640 }}>{sub}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

/* ---------------- Card ---------------- */
export function Card({ children, style, className = "", pad = 18 }: {
  children: ReactNode; style?: CSSProperties; className?: string; pad?: number;
}) {
  return <div className={"panel " + className} style={{ padding: pad, ...style }}>{children}</div>;
}

/* ---------------- Banner ---------------- */
export function Banner({ icon, tone = "neutral", title, children }: {
  icon: string; tone?: "neutral" | "green" | "warn" | "legal"; title?: string; children: ReactNode;
}) {
  const tones: Record<string, { c: string; b: string; bg: string }> = {
    neutral: { c: "var(--dim)", b: "var(--border-2)", bg: "var(--surface-2)" },
    green: { c: "var(--green)", b: "color-mix(in oklch,var(--green) 30%, transparent)", bg: "var(--green-bg)" },
    warn: { c: "var(--c-check)", b: "color-mix(in oklch,var(--c-check) 30%, transparent)", bg: "var(--r-mod-bg)" },
    legal: { c: "var(--c-tool)", b: "color-mix(in oklch,var(--c-tool) 30%, transparent)", bg: "rgba(91,179,201,.1)" },
  };
  const t = tones[tone] || tones.neutral;
  return (
    <div className="row" style={{ gap: 11, alignItems: "flex-start", padding: "12px 14px", borderRadius: "var(--r)", border: "1px solid " + t.b, background: t.bg }}>
      <Icon name={icon} size={16} color={t.c} style={{ marginTop: 1 }} />
      <div className="grow">
        {title && <div style={{ fontSize: 12.5, fontWeight: 700, color: t.c, marginBottom: 2 }}>{title}</div>}
        <div className="dim" style={{ fontSize: 12, lineHeight: 1.5 }}>{children}</div>
      </div>
    </div>
  );
}

/* ---------------- Trend arrow ---------------- */
export function TrendArrow({ dir }: { dir: string }) {
  const map: Record<string, { i: string; c: string }> = {
    declining: { i: "trending-down", c: "var(--r-elev)" },
    down: { i: "trending-down", c: "var(--r-elev)" },
    improving: { i: "trending-up", c: "var(--green)" },
    up: { i: "trending-up", c: "var(--green)" },
  };
  const m = map[dir] || { i: "minus", c: "var(--faint)" };
  return <Icon name={m.i} size={14} color={m.c} />;
}

/* ---------------- Toggle switch ---------------- */
export function Switch({ on, onChange, color = "var(--green)" }: {
  on: boolean; onChange: (v: boolean) => void; color?: string;
}) {
  return (
    <button onClick={() => onChange(!on)} style={{ width: 38, height: 22, borderRadius: 99, background: on ? color : "var(--surface-3)", border: "1px solid var(--border-2)", padding: 2, transition: "background .2s", flexShrink: 0 }}>
      <span style={{ display: "block", width: 16, height: 16, borderRadius: 99, background: on ? "var(--green-ink)" : "var(--dim)", transform: on ? "translateX(16px)" : "none", transition: "transform .2s var(--ease)" }} />
    </button>
  );
}

/* ---------------- KV row (runtime config) ---------------- */
export function KV({ k, v, vColor, mono = true }: { k: string; v: ReactNode; vColor?: string; mono?: boolean }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
      <span className="faint" style={{ fontSize: 11.5 }}>{k}</span>
      <span className={mono ? "mono tabnum" : ""} style={{ fontSize: 11.5, color: vColor || "var(--text)", textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>{v}</span>
    </div>
  );
}
