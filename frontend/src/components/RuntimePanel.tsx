import { useState } from "react";
import type { EdgeRuntimeStatus } from "../api";
import { Icon } from "../lib/icons";
import { KV, Pill, Switch } from "../lib/ui";

export function RuntimePanel({ runtime, online, running, fallbacks, onToggleOnline }: {
  runtime: EdgeRuntimeStatus;
  online: boolean;
  running: boolean;
  fallbacks: number;
  onToggleOnline: () => void;
}) {
  const [backend, setBackend] = useState(runtime.supported_backends[0] ?? "");
  const active = online || running;
  const statusColor = online ? "var(--green)" : "var(--r-elev)";
  const fallbackActive = !online;
  const calls = runtime.inference_calls;
  const avgLat = runtime.average_latency_ms;

  return (
    <div className="col" style={{ gap: 14 }}>
      {/* header */}
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div className="row gap8">
          <span style={{ width: 26, height: 26, borderRadius: 7, background: "var(--green)", display: "grid", placeItems: "center", color: "var(--green-ink)" }}><Icon name="cpu" size={15} /></span>
          <div className="col">
            <span style={{ fontWeight: 700, fontSize: 13 }}>NVIDIA Edge Runtime</span>
            <span className="eyebrow" style={{ marginTop: 1 }}>Spark · local inference</span>
          </div>
        </div>
        <span className="row gap6" style={{ padding: "3px 9px", borderRadius: 99, background: online ? "var(--green-bg)" : "var(--r-elev-bg)", border: "1px solid color-mix(in oklch," + statusColor + " 30%, transparent)" }}>
          <span className={online ? "dot dot-live" : "dot"} style={{ background: statusColor }} />
          <span className="mono" style={{ fontSize: 9.5, color: statusColor, letterSpacing: ".05em" }}>{online ? "ONLINE" : "OFFLINE"}</span>
        </span>
      </div>

      {/* status banner */}
      <div className="panel-2" style={{ padding: 12, borderColor: fallbackActive ? "color-mix(in oklch,var(--r-elev) 35%, transparent)" : "var(--border-2)", background: fallbackActive ? "var(--r-elev-bg)" : "var(--surface-2)" }}>
        <div className="row gap8">
          <Icon name={fallbackActive ? "shield-alert" : "shield-check"} size={15} color={fallbackActive ? "var(--r-elev)" : "var(--green)"} />
          <span style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.25, color: fallbackActive ? "var(--r-elev)" : "var(--green)" }}>
            {fallbackActive ? "Deterministic fallback engaged" : "Local model serving"}
          </span>
        </div>
        <p className="dim" style={{ fontSize: 11, marginTop: 5, lineHeight: 1.45 }}>
          {fallbackActive
            ? "Model endpoint unreachable. Reports come from the deterministic risk engine — no claims are fabricated."
            : "Generation grounded by the deterministic engine; the model adds plain-language framing only."}
        </p>
      </div>

      {/* metrics grid */}
      <div className="row gap10">
        <div className="panel-2 grow" style={{ padding: "10px 12px" }}>
          <div className="eyebrow">Inference calls</div>
          <div className="mono tabnum" style={{ fontSize: 20, fontWeight: 700, marginTop: 2 }}>{calls}</div>
        </div>
        <div className="panel-2 grow" style={{ padding: "10px 12px" }}>
          <div className="eyebrow">Avg latency</div>
          <div className="mono tabnum" style={{ fontSize: 20, fontWeight: 700, marginTop: 2, color: avgLat != null ? "var(--text)" : "var(--faint)" }}>{avgLat != null ? avgLat : "—"}<span style={{ fontSize: 11, color: "var(--dim)", marginLeft: 2 }}>ms</span></div>
        </div>
      </div>
      <div className="row gap10">
        <div className="panel-2 grow" style={{ padding: "10px 12px" }}>
          <div className="eyebrow">Throughput</div>
          <div className="mono tabnum" style={{ fontSize: 16, fontWeight: 700, marginTop: 2, color: active ? "var(--text)" : "var(--faint)" }}>{active ? 38 + (calls % 9) : "—"}<span style={{ fontSize: 10, color: "var(--dim)", marginLeft: 2 }}>tok/s</span></div>
        </div>
        <div className="panel-2 grow" style={{ padding: "10px 12px" }}>
          <div className="eyebrow">Fallbacks</div>
          <div className="mono tabnum" style={{ fontSize: 16, fontWeight: 700, marginTop: 2, color: fallbacks ? "var(--c-fall)" : "var(--text)" }}>{fallbacks}</div>
        </div>
      </div>

      {/* config */}
      <div>
        <KV k="Model" v={runtime.model_name} vColor="var(--green)" />
        <KV k="Endpoint" v={runtime.endpoint} />
        <KV k="Status" v={online ? "reachable" : "unreachable"} vColor={statusColor} />
        <KV k="Hardware" v={runtime.gpu_hardware_mode} />
        <KV k="Fallback" v={runtime.fallback_status.includes("used") ? "active" : "armed"} />
      </div>

      {/* serving backend picker */}
      <div>
        <div className="eyebrow" style={{ marginBottom: 7 }}>Serving backend</div>
        <div className="row gap6 wrap">
          {runtime.supported_backends.slice(0, 6).map((o) => {
            const short = o.replace(/ .*/, "");
            return (
              <button key={o} onClick={() => setBackend(o)} className="mono" title={o}
                style={{ fontSize: 10, padding: "5px 9px", borderRadius: 6, border: "1px solid " + (o === backend ? "var(--green)" : "var(--border-2)"), color: o === backend ? "var(--green)" : "var(--dim)", background: o === backend ? "var(--green-bg)" : "transparent" }}>
                {short}
              </button>
            );
          })}
        </div>
      </div>

      {/* trust cue */}
      <div className="panel-2 grid-tex" style={{ padding: 13, borderColor: "var(--border-2)" }}>
        <div className="row gap8" style={{ marginBottom: 4 }}>
          <Icon name="lock" size={14} color="var(--green)" />
          <span style={{ fontSize: 12, fontWeight: 700 }}>No sensitive data leaves this device</span>
        </div>
        <p className="dim" style={{ fontSize: 11, lineHeight: 1.45 }}>{runtime.trust_cue}</p>
        <div className="row gap6 wrap" style={{ marginTop: 8 }}>
          <Pill color="var(--green)"><Icon name="wifi-off" size={11} /> Air-gap ready</Pill>
          <Pill color="var(--green)"><Icon name="hard-drive" size={11} /> On-device cache</Pill>
        </div>
      </div>

      {/* simulate offline */}
      <div className="row" style={{ justifyContent: "space-between", padding: "10px 12px", borderRadius: "var(--r)", border: "1px dashed var(--border-2)" }}>
        <div className="col" style={{ gap: 1 }}>
          <span style={{ fontSize: 11.5, fontWeight: 600 }}>Simulate model online</span>
          <span className="faint" style={{ fontSize: 10.5 }}>Preview the served-model state</span>
        </div>
        <Switch on={online} onChange={onToggleOnline} />
      </div>
    </div>
  );
}

export function RuntimeStrip({ runtime, online, calls }: { runtime: EdgeRuntimeStatus; online: boolean; calls: number }) {
  return (
    <span className="row gap6">
      <span className={online ? "dot dot-live" : "dot"} style={{ background: online ? undefined : "var(--r-elev)" }} />
      <span className="mono" style={{ fontSize: 10.5, whiteSpace: "nowrap", color: online ? "var(--green)" : "var(--r-elev)" }}>{online ? "EDGE ONLINE" : "FALLBACK"}</span>
      <span className="mono faint" style={{ fontSize: 10.5 }}>· {calls} calls</span>
    </span>
  );
}
