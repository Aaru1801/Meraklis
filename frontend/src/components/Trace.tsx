import { useEffect, useRef } from "react";
import type { AuditStep, PipelineStage } from "../api";
import { Icon } from "../lib/icons";
import { Confidence, Cite } from "../lib/ui";
import { agentMeta } from "../lib/agents";

const TYPE_META: Record<string, { tag: string; color: string }> = {
  tool: { tag: "TOOL", color: "var(--c-tool)" },
  model: { tag: "MODEL", color: "var(--c-model)" },
  fallback: { tag: "FALLBACK", color: "var(--c-fall)" },
  checkpoint: { tag: "CHECKPOINT", color: "var(--c-check)" },
  result: { tag: "RESULT", color: "var(--green)" },
};

interface LogEvt {
  type: string; agent: string; label: string; tool?: string; model?: string;
  ms?: number; conf?: number; cites?: string[]; note?: string; human?: boolean; start?: boolean;
}

/* Derive a Meraklis-style log feed from real audit steps. */
function deriveLog(stages: PipelineStage[], trace: Record<number, AuditStep>, running: number | null): LogEvt[] {
  const out: LogEvt[] = [];
  stages.forEach((stage) => {
    const step = trace[stage.index];
    const isRunning = running === stage.index;
    if (!step && !isRunning) return;
    out.push({ type: "agent-start", agent: stage.agent, label: "engaged", start: true });
    if (!step) return;
    step.tool_calls.forEach((tc) =>
      out.push({ type: "tool", agent: stage.agent, label: tc.output_summary || tc.tool, tool: tc.tool, ms: tc.latency_ms || undefined }));
    step.model_calls.forEach((mc) =>
      out.push({
        type: mc.fallback_used ? "fallback" : "model", agent: stage.agent,
        label: mc.fallback_used ? "deterministic template used" : "generated plain-language framing",
        model: mc.model, ms: mc.latency_ms || undefined,
        note: mc.fallback_used ? (mc.error ? "model offline — " + mc.error : "model offline — deterministic fallback") : undefined,
      }));
    out.push({ type: "result", agent: stage.agent, label: step.output_summary || stage.label, conf: step.confidence, cites: step.citations.map((c) => c.id) });
    if (step.human_checkpoint)
      out.push({ type: "checkpoint", agent: stage.agent, label: step.human_checkpoint, human: true });
  });
  return out;
}

function agentStatus(stages: PipelineStage[], trace: Record<number, AuditStep>, running: number | null) {
  return stages.map((s) => (trace[s.index] ? "done" : running === s.index ? "working" : "idle"));
}

/* =================== PIPELINE RAIL =================== */
function PipelineRail({ stages, trace, running, compact }: {
  stages: PipelineStage[]; trace: Record<number, AuditStep>; running: number | null; compact?: boolean;
}) {
  const status = agentStatus(stages, trace, running);
  return (
    <div className="col" style={{ gap: 0 }}>
      {stages.map((s, i) => {
        const st = status[i];
        const meta = agentMeta(s.agent);
        const active = st === "working", done = st === "done";
        const step = trace[s.index];
        const nTool = step?.tool_calls.length || 0;
        const nModel = step?.model_calls.length || 0;
        const nFall = step?.model_calls.filter((m) => m.fallback_used).length || 0;
        return (
          <div key={s.index} className="row" style={{ gap: 11, alignItems: "stretch", opacity: st === "idle" ? 0.5 : 1, transition: "opacity .3s" }}>
            <div className="col" style={{ alignItems: "center", width: 24 }}>
              <span style={{ position: "relative", width: 24, height: 24, borderRadius: 7, background: active ? "var(--green)" : done ? "var(--green-bg)" : "var(--surface-2)", border: "1px solid " + (active || done ? "transparent" : "var(--border-2)"), display: "grid", placeItems: "center", color: active ? "var(--green-ink)" : done ? "var(--green)" : "var(--faint)", flexShrink: 0 }}>
                <Icon name={done ? "check" : meta.icon} size={13} />
                {active && <span style={{ position: "absolute", inset: -3, borderRadius: 9, border: "1.5px solid var(--green)" }} className="blink" />}
              </span>
              {i < stages.length - 1 && <span style={{ flex: 1, width: 2, background: done ? "var(--green-deep)" : "var(--border)", minHeight: compact ? 14 : 20 }} />}
            </div>
            <div style={{ flex: 1, padding: compact ? "1px 0 14px" : "2px 0 20px" }}>
              <div className="row gap8" style={{ justifyContent: "space-between" }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: active ? "var(--green)" : "var(--text)" }}>{s.agent.replace(" Agent", "")}</span>
                {active ? <span className="mono blink" style={{ fontSize: 9.5, color: "var(--green)" }}>● WORKING</span>
                  : done ? <span className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}>DONE</span>
                  : <span className="mono" style={{ fontSize: 9.5, color: "var(--ghost)" }}>IDLE</span>}
              </div>
              {!compact && <p className="faint" style={{ fontSize: 11.5, marginTop: 2 }}>{meta.blurb}</p>}
              {step && (nTool || nModel || step.confidence != null) && (
                <div className="row gap8 wrap" style={{ marginTop: 6 }}>
                  {nTool > 0 && <span className="mono" style={{ fontSize: 9.5, color: "var(--c-tool)" }}>{nTool} tool</span>}
                  {nModel > 0 && <span className="mono" style={{ fontSize: 9.5, color: "var(--c-model)" }}>{nModel} model</span>}
                  {nFall > 0 && <span className="mono" style={{ fontSize: 9.5, color: "var(--c-fall)" }}>{nFall} fallback</span>}
                  {step.deterministic_fallback && nModel === 0 && <span className="mono" style={{ fontSize: 9.5, color: "var(--green)" }}>deterministic</span>}
                  <span className="mono" style={{ fontSize: 9.5, color: "var(--dim)" }}>conf {Math.round(step.confidence * 100)}%</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* =================== LOG ROW =================== */
function LogRow({ e, modelName }: { e: LogEvt; modelName: string }) {
  const meta = agentMeta(e.agent);
  if (e.type === "agent-start") {
    return (
      <div className="fade-in row gap10" style={{ padding: "10px 0 4px" }}>
        <span style={{ width: 22, height: 22, borderRadius: 6, background: "var(--green-bg)", border: "1px solid var(--border-2)", display: "grid", placeItems: "center", color: "var(--green)" }}><Icon name={meta.icon} size={12} /></span>
        <span style={{ fontWeight: 700, fontSize: 12.5 }}>{e.agent.replace(" Agent", "")}</span>
        <span className="eyebrow">engaged</span>
        <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
      </div>
    );
  }
  const m = TYPE_META[e.type] || TYPE_META.tool;
  return (
    <div className="fade-in row" style={{ gap: 8, alignItems: "flex-start", padding: "5px 0 5px 18px" }}>
      <span className="mono" style={{ fontSize: 9, fontWeight: 600, letterSpacing: ".04em", color: e.human ? "var(--c-human)" : m.color, background: "color-mix(in oklch," + (e.human ? "var(--c-human)" : m.color) + " 11%, transparent)", border: "1px solid color-mix(in oklch," + (e.human ? "var(--c-human)" : m.color) + " 28%, transparent)", padding: "2px 5px", borderRadius: 4, flexShrink: 0, minWidth: 70, textAlign: "center" }}>
        {e.human ? "HUMAN GATE" : m.tag}
      </span>
      <div className="grow">
        <div className="row gap8 wrap" style={{ alignItems: "baseline" }}>
          <span style={{ fontSize: 12.5, color: e.human ? "var(--c-human)" : "var(--text)", fontWeight: e.human ? 600 : 400 }}>{e.label}</span>
          {e.tool && <span className="mono faint" style={{ fontSize: 10 }}>· {e.tool}</span>}
        </div>
        {e.note && <div className="faint" style={{ fontSize: 11, marginTop: 2, fontStyle: "italic" }}>{e.note}</div>}
        <div className="row gap10 wrap" style={{ marginTop: 4 }}>
          {e.type === "model" && <span className="mono" style={{ fontSize: 10, color: "var(--green)" }}>{e.model || modelName}</span>}
          {e.ms != null && <span className="mono faint" style={{ fontSize: 10 }}>{e.ms}ms</span>}
          {e.conf != null && <Confidence value={e.conf} />}
          {e.cites && e.cites.length > 0 && <Cite ids={e.cites} />}
        </div>
      </div>
    </div>
  );
}

/* =================== TRACE =================== */
export function Trace({ stages, trace, running, modelName }: {
  stages: PipelineStage[]; trace: Record<number, AuditStep>; running: number | null; modelName: string;
}) {
  const events = deriveLog(stages, trace, running);
  const isRunning = running !== null;
  const done = stages.length ? Object.keys(trace).length : 0;
  const progress = stages.length ? Math.round((done / stages.length) * 100) : 0;
  const feedRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight; }, [events.length]);

  return (
    <div className="panel" style={{ overflow: "hidden", height: "100%", display: "grid", gridTemplateRows: "auto 1fr" }}>
      {/* trace bar */}
      <div className="row gap12" style={{ padding: "12px 18px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <span className="row gap8">
          <span className={isRunning ? "dot dot-live" : "dot"} style={{ background: isRunning ? undefined : progress >= 100 ? "var(--green)" : "var(--ghost)" }} />
          <span className="eyebrow" style={{ color: isRunning ? "var(--green)" : "var(--dim)" }}>{isRunning ? "Investigation live" : progress >= 100 ? "Investigation complete" : "Idle"}</span>
        </span>
        <span style={{ flex: 1 }} />
        <div className="track" style={{ width: 160 }}><i style={{ width: progress + "%" }} /></div>
        <span className="mono tabnum faint" style={{ fontSize: 11, minWidth: 32, textAlign: "right" }}>{progress}%</span>
      </div>

      {/* split body */}
      <div style={{ display: "grid", gridTemplateColumns: "208px 1fr", overflow: "hidden" }}>
        <div style={{ borderRight: "1px solid var(--border)", overflow: "auto", padding: "18px 14px", background: "var(--surface-2)" }}>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Agent pipeline</div>
          <PipelineRail stages={stages} trace={trace} running={running} compact />
        </div>
        <div ref={feedRef} style={{ overflow: "auto", height: "100%", padding: "4px 16px 28px" }}>
          {events.length === 0 && (
            <div className="col" style={{ height: "100%", placeItems: "center", justifyContent: "center", color: "var(--faint)", gap: 10 }}>
              <Icon name="radio" size={26} />
              <span className="mono" style={{ fontSize: 12 }}>Awaiting investigation…</span>
            </div>
          )}
          {events.map((e, i) => <LogRow key={i} e={e} modelName={modelName} />)}
          {isRunning && (
            <div className="row gap8" style={{ paddingLeft: 18, marginTop: 6 }}>
              <span className="dot dot-live" />
              <span className="mono blink" style={{ fontSize: 11, color: "var(--green)" }}>thinking…</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
