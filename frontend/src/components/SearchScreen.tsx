import { useState } from "react";
import type { EdgeRuntimeStatus } from "../api";
import { Icon } from "../lib/icons";
import { GradeBadge, Logo, Pill } from "../lib/ui";

export interface DemoCard {
  label: string; address: string; rsn: string; why: string;
  grade?: string; score?: number | null; units?: number | null; ward?: string | null; hero?: boolean;
}

export function SearchScreen({ demos, runtime, onPick }: {
  demos: DemoCard[];
  runtime: EdgeRuntimeStatus | null;
  onPick: (input: { address?: string; rsn?: string | null }) => void;
}) {
  const [q, setQ] = useState("");
  const submit = () => {
    if (q.trim()) onPick({ address: q.trim() });
    else if (demos[0]) onPick({ address: demos[0].address, rsn: demos[0].rsn });
  };
  return (
    <div className="col" style={{ height: "100%", overflow: "auto" }}>
      <div className="row" style={{ justifyContent: "space-between", padding: "16px 26px", borderBottom: "1px solid var(--border)" }}>
        <Logo />
        <div className="row gap10">
          <span className="row gap6"><span className="dot dot-live" /><span className="mono" style={{ fontSize: 11, color: "var(--green)" }}>{runtime?.model_name ?? "local model"}</span></span>
          <span className="faint">·</span>
          <span className="mono faint" style={{ fontSize: 11 }}>{runtime?.gpu_hardware_mode ?? "NVIDIA Spark"}</span>
        </div>
      </div>

      <div className="col grow" style={{ alignItems: "center", justifyContent: "center", padding: "40px 24px" }}>
        <div style={{ width: "100%", maxWidth: 720 }}>
          <div className="row gap8 wrap" style={{ marginBottom: 16 }}>
            <Pill color="var(--green)"><Icon name="cpu" size={11} /> Your Agents · Your Models · Your Edge</Pill>
            <Pill><Icon name="map-pin" size={11} /> Toronto open data</Pill>
          </div>
          <h1 style={{ fontSize: 34, fontWeight: 800, letterSpacing: "-.025em", lineHeight: 1.08, marginBottom: 10 }}>
            Investigate any Toronto rental,<br /><span style={{ color: "var(--green)" }}>fully on the edge.</span>
          </h1>
          <p className="dim" style={{ fontSize: 15, lineHeight: 1.5, maxWidth: 560, marginBottom: 26 }}>
            Eight local agents read RentSafeTO and city open data, score risk deterministically, ground every claim in tenant-rights law, and draft a 311 complaint — all running on a local NVIDIA model. Nothing leaves the device.
          </p>

          <div className="panel row gap10" style={{ padding: "6px 6px 6px 16px", borderColor: "var(--border-2)" }}>
            <Icon name="search" size={18} color="var(--faint)" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Enter a Toronto building address…"
              onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 15, padding: "10px 0" }} />
            <button className="btn btn-pri" onClick={submit}><Icon name="scan-search" size={15} /> Investigate</button>
          </div>

          <div className="eyebrow" style={{ margin: "26px 0 12px" }}>Demo buildings · click to run a full investigation</div>
          <div className="col gap10">
            {demos.map((b) => (
              <button key={b.rsn} onClick={() => onPick({ address: b.address, rsn: b.rsn })} className="panel row gap14"
                style={{ padding: "13px 16px", textAlign: "left", borderColor: b.hero ? "color-mix(in oklch,var(--green) 30%, transparent)" : "var(--border)", transition: "all .15s" }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-3)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = b.hero ? "color-mix(in oklch,var(--green) 30%, transparent)" : "var(--border)")}>
                <GradeBadge grade={b.grade ?? "C"} size={42} />
                <div className="grow">
                  <div className="row gap8"><span style={{ fontSize: 14, fontWeight: 700 }}>{b.address}</span>{b.hero && <Pill color="var(--green)">featured</Pill>}</div>
                  <div className="faint" style={{ fontSize: 12 }}>{[b.ward, b.units ? b.units + " units" : null, b.score != null ? "RentSafeTO " + b.score + "%" : null].filter(Boolean).join(" · ") || b.why}</div>
                </div>
                <Icon name="arrow-right" size={18} color="var(--faint)" />
              </button>
            ))}
          </div>

          <div className="row gap16 wrap" style={{ marginTop: 28, paddingTop: 20, borderTop: "1px solid var(--border)" }}>
            {[["lock", "No data egress"], ["function-square", "Deterministic scoring"], ["wifi-off", "Offline-capable"], ["git-commit-horizontal", "Human approval gate"]].map(([ic, t]) => (
              <span key={t} className="row gap6"><Icon name={ic} size={13} color="var(--green)" /><span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>{t}</span></span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
