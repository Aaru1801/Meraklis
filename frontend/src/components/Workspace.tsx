import { useState } from "react";
import type {
  AddressResolution, AdvocacyReport, AuditStep, ComplaintDraft, EdgeRuntimeStatus,
  NeighbourhoodSafety, OperatorPortfolioReport, PIO, PipelineStage, RightsGroundingReport,
  RiskReport, ValueForRisk,
} from "../api";
import { Icon } from "../lib/icons";
import { gradeMeta, Logo } from "../lib/ui";
import { NAV } from "../lib/agents";
import { Trace } from "./Trace";
import { RuntimePanel } from "./RuntimePanel";
import {
  ReportOverview, RedFlags, Intelligence, OperatorPanel, RightsPanel, AdvocateSection,
  DraftPanel, AuditPanel, ValuePanel, SafetyPanel,
} from "./sections";

export interface LiveData {
  resolved?: AddressResolution; pio?: PIO; risk?: RiskReport; value?: ValueForRisk;
  safety?: NeighbourhoodSafety; operator?: OperatorPortfolioReport;
  rights?: RightsGroundingReport; advocacy?: AdvocacyReport; draft_311?: ComplaintDraft; audit_trail: AuditStep[];
}

function Waiting({ label }: { label: string }) {
  return (
    <div className="col" style={{ height: "100%", placeItems: "center", justifyContent: "center", color: "var(--faint)", gap: 12 }}>
      <Icon name="loader" size={24} className="spin" />
      <span className="mono" style={{ fontSize: 12 }}>{label}</span>
    </div>
  );
}

function NavBtn({ n, active, running, onClick }: { n: typeof NAV[number]; active: boolean; running: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="row gap10" style={{
      padding: "8px 10px", borderRadius: 7, width: "100%",
      background: active ? "var(--green-bg)" : "transparent", color: active ? "var(--green)" : "var(--dim)",
      border: "1px solid " + (active ? "color-mix(in oklch,var(--green) 25%, transparent)" : "transparent"),
      fontSize: 12.5, fontWeight: active ? 600 : 500, whiteSpace: "nowrap", transition: "all .12s" }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "var(--surface-2)"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}>
      <Icon name={n.icon} size={15} />
      <span className="grow" style={{ textAlign: "left" }}>{n.label}</span>
      {n.live && running && <span className="dot dot-live" />}
    </button>
  );
}

export function Workspace({
  address, data, stages, traceByIndex, runningIndex, runtime, online, setOnline,
  section, setSection, approval, setApproval, onHome, onRerun,
}: {
  address: string;
  data: LiveData;
  stages: PipelineStage[];
  traceByIndex: Record<number, AuditStep>;
  runningIndex: number | null;
  runtime: EdgeRuntimeStatus | null;
  online: boolean;
  setOnline: (fn: (v: boolean) => boolean) => void;
  section: string;
  setSection: (s: string) => void;
  approval: string;
  setApproval: (s: string) => void;
  onHome: () => void;
  onRerun: () => void;
}) {
  const [railOpen, setRailOpen] = useState(true);
  const running = runningIndex !== null;
  const risk = data.risk;
  const g = gradeMeta(risk?.grade);
  const modelName = runtime?.model_name ?? "nemotron";
  const fallbacks = data.audit_trail.reduce((n, s) => n + s.model_calls.filter((m) => m.fallback_used).length, 0);

  const body = (() => {
    switch (section) {
      case "trace": return <Trace stages={stages} trace={traceByIndex} running={runningIndex} modelName={modelName} />;
      case "report": return risk ? <ReportOverview risk={risk} /> : <Waiting label="scoring risk…" />;
      case "value": return data.value && risk ? <ValuePanel value={data.value} risk={risk} /> : <Waiting label="valuing rent vs. condition…" />;
      case "flags": return risk ? <RedFlags risk={risk} /> : <Waiting label="scoring risk…" />;
      case "pio": return data.pio && risk ? <Intelligence pio={data.pio} risk={risk} resolved={data.resolved} /> : <Waiting label="building PIO…" />;
      case "operator": return data.operator ? <OperatorPanel operator={data.operator} /> : <Waiting label="checking operator…" />;
      case "safety": return data.safety ? <SafetyPanel safety={data.safety} /> : <Waiting label="reading neighbourhood safety…" />;
      case "rights": return data.rights ? <RightsPanel rights={data.rights} /> : <Waiting label="grounding rights…" />;
      case "advocate": return data.advocacy ? <AdvocateSection advocacy={data.advocacy} /> : <Waiting label="drafting guidance…" />;
      case "draft": return data.draft_311 ? <DraftPanel draft={data.draft_311} approval={approval} onApprove={() => setApproval("approved")} onRequestChanges={() => setApproval("pending")} /> : <Waiting label="preparing 311 draft…" />;
      case "audit": return <AuditPanel audit={data.audit_trail} approval={approval} />;
      default: return null;
    }
  })();

  return (
    <div className="col" style={{ height: "100%", overflow: "hidden" }}>
      {/* header */}
      <header className="row gap16" style={{ padding: "11px 20px", borderBottom: "1px solid var(--border)", flexShrink: 0, background: "var(--surface)" }}>
        <button onClick={onHome} style={{ background: "none" }}><Logo size={24} /></button>
        <div style={{ height: 22, width: 1, background: "var(--border-2)" }} />
        <div className="row gap10 grow" style={{ minWidth: 0 }}>
          <Icon name="map-pin" size={15} color="var(--green)" />
          <div className="col" style={{ minWidth: 0 }}>
            <span style={{ fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{risk?.address || address}</span>
            <span className="faint" style={{ fontSize: 10.5 }}>{risk ? (risk.ward_name ?? "Toronto") + " · RSN " + risk.rsn : "resolving…"}</span>
          </div>
          {risk && <span className="row gap6" style={{ padding: "3px 9px", borderRadius: 99, background: g.bg, marginLeft: 4, whiteSpace: "nowrap" }}><span style={{ fontWeight: 800, color: g.color, fontSize: 12 }}>{risk.grade}</span><span className="mono" style={{ fontSize: 10, color: g.color }}>{risk.risk_level}</span></span>}
        </div>
        <span className="row gap6"><span className={online ? "dot dot-live" : "dot"} style={{ background: online ? undefined : "var(--r-elev)" }} /><span className="mono" style={{ fontSize: 10.5, whiteSpace: "nowrap", color: online ? "var(--green)" : "var(--r-elev)" }}>{online ? "EDGE ONLINE" : "FALLBACK"}</span></span>
        <button className="btn btn-ghost btn-sm" onClick={onRerun}><Icon name="rotate-cw" size={13} /> Re-run</button>
        <button className="btn btn-ghost btn-sm" onClick={onHome}><Icon name="search" size={13} /> New</button>
      </header>

      {/* body */}
      <div className="row grow" style={{ overflow: "hidden", alignItems: "stretch" }}>
        <nav className="col" style={{ width: 180, flexShrink: 0, borderRight: "1px solid var(--border)", padding: "14px 11px", background: "var(--surface)", overflow: "auto", gap: 2 }}>
          <div className="eyebrow" style={{ padding: "4px 8px 8px" }}>Workspace</div>
          {NAV.map((n) => <NavBtn key={n.id} n={n} active={section === n.id} running={running} onClick={() => setSection(n.id)} />)}
          <div style={{ flex: 1 }} />
          <div className="panel-2" style={{ padding: 10, marginTop: 10 }}>
            <div className="row gap6" style={{ marginBottom: 4 }}><Icon name="lock" size={12} color="var(--green)" /><span className="mono" style={{ fontSize: 9.5, color: "var(--green)", whiteSpace: "nowrap" }}>LOCAL · NO EGRESS</span></div>
            <p className="faint" style={{ fontSize: 10, lineHeight: 1.4 }}>All inference on the Spark node.</p>
          </div>
        </nav>

        <main className="grow" style={{ overflow: "hidden", background: "var(--bg)", padding: section === "trace" ? 18 : 0 }}>{body}</main>

        {/* collapsible runtime rail */}
        <aside style={{ width: railOpen ? 300 : 48, flexShrink: 0, borderLeft: "1px solid var(--border)", background: "var(--surface)", overflow: railOpen ? "auto" : "hidden", transition: "width .2s var(--ease)" }}>
          {railOpen ? (
            <div style={{ padding: 16 }}>
              <div className="row" style={{ justifyContent: "flex-end", marginBottom: 8 }}>
                <button className="btn-quiet btn btn-sm" onClick={() => setRailOpen(false)} title="Collapse runtime panel"><Icon name="panel-right-close" size={15} /></button>
              </div>
              {runtime ? <RuntimePanel runtime={runtime} online={online} running={running} fallbacks={fallbacks} onToggleOnline={() => setOnline((v) => !v)} /> : <Waiting label="probing runtime…" />}
            </div>
          ) : (
            <button onClick={() => setRailOpen(true)} title="Show NVIDIA Edge Runtime" className="col" style={{ width: "100%", alignItems: "center", gap: 12, padding: "12px 0", height: "100%" }}>
              <Icon name="chevron-left" size={16} color="var(--dim)" />
              <span style={{ width: 26, height: 26, borderRadius: 7, background: "var(--green)", display: "grid", placeItems: "center", color: "var(--green-ink)" }}><Icon name="cpu" size={15} /></span>
              <span className={online ? "dot dot-live" : "dot"} style={{ background: online ? undefined : "var(--r-elev)" }} />
              <span className="mono" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", fontSize: 10, letterSpacing: ".14em", color: "var(--faint)", textTransform: "uppercase", marginTop: 4 }}>NVIDIA Edge Runtime</span>
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}
