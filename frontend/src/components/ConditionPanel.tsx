import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ConditionSummary, type ConditionUploadResult } from "../api";
import { Icon } from "../lib/icons";
import { Card, Pill, ScoreGauge, SectionHeader } from "../lib/ui";

const SCROLL = { height: "100%", overflowY: "auto", padding: 22 } as const;

const KIND_META: Record<string, { color: string; bg: string; label: string }> = {
  issue: { color: "var(--r-high)", bg: "var(--r-high-bg)", label: "ISSUE" },
  fix: { color: "var(--green)", bg: "var(--green-bg)", label: "FIX" },
  none: { color: "var(--faint)", bg: "var(--surface-2)", label: "NONE" },
};

// Tenant condition verification, scoped to one building's profile. Photos are
// analyzed locally by NVIDIA Nemotron Nano VL and adjust a SEPARATE "live" score;
// the official City score is never changed.
export function ConditionPanel({ rsn, baseScore }: { rsn: string; baseScore: number | null }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [summary, setSummary] = useState<ConditionSummary | null>(null);
  const [result, setResult] = useState<ConditionUploadResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.buildingConditions(rsn).then(setSummary).catch(() => {});
  }, [rsn]);
  useEffect(() => { refresh(); }, [refresh]);

  const onFile = async (file: File) => {
    setErr(null); setResult(null); setLoading(true);
    try {
      const r = await api.submitCondition(rsn, file);
      if (r.ok) { setResult(r); if (r.summary) setSummary(r.summary); }
      else setErr(r.error || "Could not analyze the photo.");
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const base = summary?.base_score ?? baseScore;
  const live = summary?.live_score ?? base;
  const delta = summary?.delta_total ?? 0;
  const n = summary?.n_reports ?? 0;
  const liveColor = delta < 0 ? "var(--r-high)" : delta > 0 ? "var(--green)" : "var(--text)";

  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="image" eyebrow="Tenant-reported · NVIDIA Nemotron Nano VL"
          title="Live condition"
          sub="Upload a photo of a problem (or a repair). The local vision model verifies it and updates a live score — the official City of Toronto score stays unchanged."
          right={<Pill color="var(--green)"><Icon name="lock" size={11} /> local · no egress</Pill>} />

        <Card style={{ display: "flex", gap: 22, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
          <div className="col" style={{ alignItems: "center", gap: 4 }}>
            <ScoreGauge value={base ?? 0} max={100} size={120} label={base ?? "—"} sub="City score" />
            <span className="faint" style={{ fontSize: 10.5 }}>official · RentSafeTO</span>
          </div>
          <Icon name="arrow-right" size={20} color="var(--faint)" />
          <div className="col" style={{ alignItems: "center", gap: 4 }}>
            <ScoreGauge value={live ?? 0} max={100} color={liveColor} size={120} label={live ?? "—"} sub="live score" />
            <span className="mono" style={{ fontSize: 11, color: liveColor }}>
              {delta === 0 ? "no reports yet" : `${delta > 0 ? "+" : ""}${delta} · ${n} report${n === 1 ? "" : "s"}`}
            </span>
          </div>
        </Card>

        <Card>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <div className="col" style={{ gap: 3 }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>Verify a condition</span>
              <span className="faint" style={{ fontSize: 11.5 }}>A leak, mould, pests, or damage — or a photo showing it's now fixed.</span>
            </div>
            <button className="btn btn-pri btn-sm" disabled={loading} onClick={() => fileRef.current?.click()} style={{ flexShrink: 0 }}>
              <Icon name={loading ? "loader" : "image"} size={14} className={loading ? "spin" : ""} /> {loading ? "Analyzing…" : "Upload photo"}
            </button>
          </div>
          {err && (
            <div style={{ marginTop: 11, padding: "9px 11px", borderRadius: 8, border: "1px solid color-mix(in oklch, var(--r-high) 35%, transparent)", background: "var(--r-high-bg)", fontSize: 12, color: "var(--r-high)" }}>{err}</div>
          )}
          {result?.analysis && (
            <div style={{ marginTop: 12, padding: 12, borderRadius: 8, border: "1px solid var(--border-2)", background: "var(--surface-2)" }}>
              <div className="row gap8" style={{ marginBottom: 6, alignItems: "center" }}>
                {(() => { const m = KIND_META[result.analysis!.kind] ?? KIND_META.none; return <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: ".06em", padding: "2px 7px", borderRadius: 5, color: m.color, background: m.bg }}>{m.label}</span>; })()}
                <span style={{ fontSize: 13, fontWeight: 700 }}>{result.analysis.label || "Assessed"}</span>
                {result.analysis.severity !== "none" && <span className="faint mono" style={{ fontSize: 10.5 }}>{result.analysis.severity}</span>}
                <span style={{ flex: 1 }} />
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: result.delta < 0 ? "var(--r-high)" : result.delta > 0 ? "var(--green)" : "var(--faint)" }}>
                  {result.delta === 0 ? "no change" : `${result.delta > 0 ? "+" : ""}${result.delta}`}
                </span>
              </div>
              <p style={{ fontSize: 12.5, lineHeight: 1.5 }}>{result.analysis.explanation}</p>
              {!result.recorded && <p className="faint" style={{ fontSize: 10.5, marginTop: 5 }}>No clear housing condition detected — the live score was not changed.</p>}
            </div>
          )}
        </Card>

        {summary && summary.reports.length > 0 && (
          <Card>
            <div className="eyebrow" style={{ marginBottom: 10 }}>Reported conditions ({summary.reports.length})</div>
            <div className="col" style={{ gap: 9 }}>
              {summary.reports.map((r) => {
                const m = KIND_META[r.kind] ?? KIND_META.none;
                return (
                  <div key={r.id} className="row gap10" style={{ alignItems: "flex-start", paddingBottom: 9, borderBottom: "1px solid var(--border)" }}>
                    <span className="mono" style={{ fontSize: 9, fontWeight: 700, letterSpacing: ".06em", padding: "2px 6px", borderRadius: 4, color: m.color, background: m.bg, flexShrink: 0, marginTop: 1 }}>{m.label}</span>
                    <div className="grow">
                      <div style={{ fontSize: 12.5, fontWeight: 600 }}>{r.label || r.kind}</div>
                      <div className="faint" style={{ fontSize: 11, lineHeight: 1.4 }}>{r.explanation}</div>
                      <div className="faint mono" style={{ fontSize: 9.5, marginTop: 2 }}>{r.created_at.replace("T", " ").replace("+00:00", "")}</div>
                    </div>
                    <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: r.delta < 0 ? "var(--r-high)" : "var(--green)", flexShrink: 0 }}>{r.delta > 0 ? "+" : ""}{r.delta}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        <p className="faint" style={{ fontSize: 10.5, lineHeight: 1.45, maxWidth: 640 }}>
          Tenant-reported conditions are community signals analyzed locally by an NVIDIA vision model. They adjust a separate live estimate and never change the official City of Toronto inspection score. Not legal advice.
        </p>
      </div>
    </div>
  );
}
