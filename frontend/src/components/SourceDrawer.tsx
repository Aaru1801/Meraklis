import type { EvidenceRef } from "../api";
import { Icon } from "../lib/icons";
import { Banner, Confidence, Meter } from "../lib/ui";
import { evidenceKind } from "../lib/evidence";

const KIND_META: Record<string, { c: string; icon: string; t: string }> = {
  law: { c: "var(--green)", icon: "scale", t: "Verified legal source" },
  dataset: { c: "var(--c-tool)", icon: "database", t: "Open dataset" },
  tool: { c: "var(--c-tool)", icon: "terminal", t: "Tool output" },
};

export function SourceDrawer({ ev, onClose }: { ev: EvidenceRef | null; onClose: () => void }) {
  if (!ev) return null;
  const { kind } = evidenceKind(ev.source || ev.id);
  const km = KIND_META[kind] || KIND_META.tool;
  const confColor = ev.confidence >= 0.8 ? "var(--green)" : ev.confidence >= 0.5 ? "var(--r-mod)" : "var(--r-elev)";
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60, display: "flex", justifyContent: "flex-end", animation: "fadeIn .2s" }}>
      <div onClick={(e) => e.stopPropagation()} className="slide-in" style={{ width: 380, maxWidth: "90vw", height: "100%", background: "var(--surface)", borderLeft: "1px solid var(--border-2)", padding: 22, overflow: "auto", boxShadow: "var(--shadow-lg)" }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 18 }}>
          <span className="eyebrow">Provenance record</span>
          <button className="btn-quiet btn btn-sm" onClick={onClose}><Icon name="x" size={15} /></button>
        </div>
        <div className="row gap10" style={{ marginBottom: 16 }}>
          <span style={{ width: 38, height: 38, borderRadius: 9, background: "color-mix(in oklch," + km.c + " 14%, transparent)", display: "grid", placeItems: "center", color: km.c }}><Icon name={km.icon} size={18} /></span>
          <div><div className="mono" style={{ fontSize: 13, color: km.c, fontWeight: 600 }}>{ev.id}</div><div className="faint" style={{ fontSize: 11 }}>{km.t}</div></div>
        </div>
        <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, marginBottom: 6 }}>{ev.title}</div>
        <p className="dim" style={{ fontSize: 12.5, lineHeight: 1.5, marginBottom: 18 }}>{ev.detail}</p>
        <div className="panel-2" style={{ padding: 14 }}>
          <div className="row" style={{ justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
            <span className="faint" style={{ fontSize: 11.5 }}>Source</span>
            <span className="mono" style={{ fontSize: 11.5, color: km.c }}>{ev.source}</span>
          </div>
          <div className="row" style={{ justifyContent: "space-between", padding: "8px 0 4px", alignItems: "center" }}>
            <span className="faint" style={{ fontSize: 11.5 }}>Confidence</span><Confidence value={ev.confidence} />
          </div>
          <Meter value={ev.confidence} color={confColor} />
        </div>
        {kind === "law" && <div style={{ marginTop: 12 }}><Banner icon="alert-triangle" tone="warn" title="">Legal information, not legal advice.</Banner></div>}
        {ev.confidence < 0.5 && <div style={{ marginTop: 12 }}><Banner icon="help-circle" tone="warn" title="Low confidence">This source is uncertain and is excluded from generated complaints.</Banner></div>}
        {ev.url && (
          <a href={ev.url} target="_blank" rel="noreferrer" className="row gap6 mono" style={{ marginTop: 14, fontSize: 11, color: "var(--c-tool)" }}>
            <Icon name="link" size={12} /> {ev.url.replace(/^https?:\/\//, "").slice(0, 46)}
          </a>
        )}
        <p className="faint" style={{ fontSize: 10.5, marginTop: 16, fontFamily: "var(--mono)" }}>Stored in local cache · no network egress</p>
      </div>
    </div>
  );
}
