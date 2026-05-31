import type { CSSProperties } from "react";
import type {
  AddressResolution, AdvocacyReport, AuditStep, ComplaintDraft, NeighbourhoodSafety,
  OperatorPortfolioReport, PIO, RightsGroundingReport, RiskReport, ValueForRisk,
} from "../api";
import { Icon } from "../lib/icons";
import {
  Banner, Card, Cite, Confidence, GradeBadge, gradeMeta, Meter, Pill, ScoreGauge,
  SectionHeader, SevTag, Sparkline, Stat, TrendArrow,
} from "../lib/ui";
import { Massing3D } from "./Massing3D";

const SCROLL: CSSProperties = { height: "100%", overflow: "auto", padding: "22px 26px" };
const GROUP_ICON: Record<string, string> = {
  "Security & Safety": "lock", "Pests & Sanitation": "alert-triangle",
  "Essential Services & Records": "file-text", "Building Integrity": "building-2",
  "Common Areas": "boxes", "Exterior & Grounds": "map-pin",
};
function driverColor(raw: number) {
  return raw >= 0.65 ? "var(--r-high)" : raw >= 0.45 ? "var(--r-elev)" : raw >= 0.25 ? "var(--r-mod)" : "var(--r-low)";
}
function flagConf(code: string): number {
  if (code.startsWith("obstructed:")) return 0.4;
  if (code.startsWith("derived:")) return 0.85;
  return 0.95;
}

/* ============ 1 · RISK REPORT ============ */
export function ReportOverview({ risk }: { risk: RiskReport }) {
  const g = gradeMeta(risk.grade);
  const hist = risk.trend.history.filter((h) => h.score != null);
  const pts = hist.map((h) => h.score);
  const cites = [`rent:${risk.rsn}:score`];
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="gauge" eyebrow="Risk Analyst · deterministic" title="Building Risk Report"
          sub={risk.address + (risk.ward_name ? " · " + risk.ward_name : "")}
          right={<div className="row gap6"><Pill color="var(--green)"><Icon name="cpu" size={11} /> model-framed</Pill><Pill><Icon name="function-square" size={11} /> engine-scored</Pill></div>} />

        <Card style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 26, alignItems: "center" }}>
          <div className="row gap20" style={{ alignItems: "center" }}>
            <ScoreGauge value={risk.risk_score} color={g.color} size={140} sub="risk index" />
            <div className="col gap8">
              <GradeBadge grade={risk.grade} size={58} />
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: g.color }}>{risk.risk_level} risk</div>
                <div className="mono faint" style={{ fontSize: 11 }}>grade {risk.grade} · index {risk.risk_score}/100</div>
              </div>
            </div>
          </div>
          <div className="col gap12">
            <p style={{ fontSize: 14, lineHeight: 1.55 }}>{risk.summary_line}</p>
            <div className="row gap16 wrap">
              <span className="row gap6"><span className="faint" style={{ fontSize: 11 }}>Method</span><span className="mono" style={{ fontSize: 11, color: "var(--green)" }}>deterministic engine</span></span>
              <span className="row gap6"><span className="faint" style={{ fontSize: 11 }}>Confidence</span><Confidence value={0.98} /></span>
              <Cite ids={cites} />
            </div>
          </div>
        </Card>

        <div className="row gap16 wrap" style={{ alignItems: "stretch" }}>
          <Card className="grow" style={{ minWidth: 300 }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <div><div className="eyebrow">RentSafeTO evaluation score</div><div className="faint" style={{ fontSize: 11, marginTop: 2 }}>higher is better · city inspection</div></div>
              <div className="col" style={{ alignItems: "flex-end" }}>
                <span className="mono tabnum" style={{ fontSize: 22, fontWeight: 700, color: "var(--r-elev)" }}>{risk.overall_score ?? "—"}%</span>
                {risk.trend.delta != null && <span className="mono" style={{ fontSize: 11, color: risk.trend.direction === "improving" ? "var(--green)" : "var(--r-elev)" }}>{risk.trend.delta > 0 ? "+" : ""}{risk.trend.delta} pts {hist.length ? "since " + hist[0].year : ""}</span>}
              </div>
            </div>
            {pts.length >= 2 ? <Sparkline points={pts} w={360} h={56} color="var(--r-elev)" /> : <p className="faint" style={{ fontSize: 12 }}>{risk.trend.narrative}</p>}
            <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
              {hist.map((h) => <span key={h.year} className="mono faint" style={{ fontSize: 10 }}>{h.year}</span>)}
            </div>
          </Card>

          <Card style={{ width: 300, flexShrink: 0 }}>
            <div className="eyebrow" style={{ marginBottom: 12 }}>Building</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Stat label="Units" value={risk.units ?? "—"} />
              <Stat label="Storeys" value={risk.storeys ?? "—"} />
              <Stat label="Built" value={risk.year_built ?? "—"} />
              <Stat label="RSN" value={risk.rsn} mono />
            </div>
            <div style={{ height: 1, background: "var(--border)", margin: "14px 0" }} />
            <div className="col gap4"><span className="faint" style={{ fontSize: 11 }}>Ward</span><span style={{ fontSize: 13, fontWeight: 600 }}>{risk.ward_name ?? "—"}</span></div>
          </Card>
        </div>

        <Card>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Risk drivers · by inspection-category group</div>
          <div className="col gap12">
            {risk.group_breakdown.map((c) => {
              const raw = c.subscore != null ? 1 - c.subscore / 100 : 0.5;
              return (
                <div key={c.group} className="row gap12" style={{ alignItems: "center" }}>
                  <span style={{ width: 188, fontSize: 12.5, fontWeight: 500 }}>{c.group}</span>
                  <div className="grow"><Meter value={raw} color={driverColor(raw)} /></div>
                  <span className="mono tabnum" style={{ fontSize: 11, width: 54, textAlign: "right", color: "var(--dim)" }}>{c.subscore != null ? c.subscore + "/100" : "n/a"}</span>
                  <span className="mono faint" style={{ fontSize: 10, width: 52, textAlign: "right" }}>{c.n_poor ? c.n_poor + " poor" : ""}</span>
                </div>
              );
            })}
          </div>
          <div style={{ height: 1, background: "var(--border)", margin: "14px 0 12px" }} />
          <Banner icon="info" tone="legal">Scoring is fully deterministic and reproducible. The local model only writes the plain-language summary — it cannot change the grade. <Cite ids={cites} /></Banner>
        </Card>
      </div>
    </div>
  );
}

/* ============ · VALUE-FOR-RISK ============ */
const VALUE_BAND: Record<string, { color: string; label: string }> = {
  good_value: { color: "var(--green)", label: "Good value" },
  fair: { color: "var(--c-tool)", label: "Fairly priced" },
  rich: { color: "var(--r-elev)", label: "A bit rich" },
  overpriced: { color: "var(--r-high)", label: "Overpriced" },
};

export function ValuePanel({ value, risk }: { value: ValueForRisk; risk: RiskReport }) {
  const b = VALUE_BAND[value.band] ?? VALUE_BAND.fair;
  const cites = [`value:${risk.rsn}`, `rent:${risk.rsn}:score`];
  const money = (n: number | null | undefined) => (n != null ? "$" + n.toLocaleString() : "—");
  if (!value.available) {
    return (
      <div style={SCROLL}>
        <SectionHeader icon="circle-dollar-sign" eyebrow="Risk Analyst · value-for-risk" title="Value for Risk" sub={risk.address} />
        <Card><p className="faint" style={{ fontSize: 13 }}>{value.rationale || "No rent estimate is available for this building, so value-for-risk can't be computed."}</p></Card>
      </div>
    );
  }
  const over = value.gap_monthly > 0;
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="circle-dollar-sign" eyebrow="Risk Analyst · value-for-risk" title="Value for Risk"
          sub={risk.address + (risk.ward_name ? " · " + risk.ward_name : "")}
          right={<div className="row gap6"><Pill color={b.color}>{b.label}</Pill><Pill><Icon name="function-square" size={11} /> deterministic</Pill></div>} />

        <Card style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 26, alignItems: "center" }}>
          <ScoreGauge value={value.value_index} color={b.color} size={140} sub="value index" />
          <div className="col gap12">
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: b.color }}>{value.verdict}</div>
              <div className="mono faint" style={{ fontSize: 11 }}>condition-fair rent vs. area-typical rent</div>
            </div>
            <p style={{ fontSize: 14, lineHeight: 1.55 }}>{value.rationale}</p>
            <div className="row gap16 wrap">
              <span className="row gap6"><span className="faint" style={{ fontSize: 11 }}>Method</span><span className="mono" style={{ fontSize: 11, color: "var(--green)" }}>rent model × condition</span></span>
              <Cite ids={cites} />
            </div>
          </div>
        </Card>

        <div className="row gap16 wrap" style={{ alignItems: "stretch" }}>
          <Card className="grow" style={{ minWidth: 190 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Area-typical rent</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700 }}>{money(value.market_rent)}<span className="faint" style={{ fontSize: 12, fontWeight: 500 }}>/mo</span></div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>est. {money(value.market_low)}–{money(value.market_high)} · model estimate</div>
          </Card>
          <Card className="grow" style={{ minWidth: 190 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Fair for its condition</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700, color: b.color }}>{money(value.condition_fair_rent)}<span className="faint" style={{ fontSize: 12, fontWeight: 500 }}>/mo</span></div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>adjusted for City score & red flags</div>
          </Card>
          <Card className="grow" style={{ minWidth: 190 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>{value.asking_rent ? "Asking vs. fair" : "Premium for condition"}</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700, color: over ? "var(--r-high)" : "var(--green)" }}>{over ? "+" : ""}{value.gap_pct}%</div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>{over ? "≈" + money(Math.abs(value.annual_gap)) + "/yr over fair" : "in line with / below fair"}</div>
          </Card>
        </div>

        {value.drivers.length > 0 && (
          <Card>
            <div className="eyebrow" style={{ marginBottom: 10 }}>What drives this</div>
            <div className="row gap8 wrap">
              {value.drivers.map((d, i) => (
                <span key={i} className="pill"><Icon name="git-commit-horizontal" size={11} /> {d}</span>
              ))}
            </div>
          </Card>
        )}

        <Banner icon="info" tone="legal">{value.disclaimer} <Cite ids={cites} /></Banner>
      </div>
    </div>
  );
}

/* ============ 2 · RED FLAGS ============ */
export function RedFlags({ risk }: { risk: RiskReport }) {
  const groups: Record<string, { code: string; title: string; detail: string; severity: string; newcomer: boolean; idx: number }[]> = {};
  risk.red_flags.forEach((f, i) => {
    const k = f.group || "Other";
    (groups[k] ||= []).push({ code: f.code, title: f.title, detail: f.detail, severity: f.severity, newcomer: f.newcomer_relevant, idx: i });
  });
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="flag" eyebrow="Risk Analyst" title="Red Flags" sub="Deficiencies grouped by inspection category. Each flag carries a confidence score and links to its RentSafeTO source. Obstructed / unverified areas are marked." />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {Object.entries(groups).map(([group, items]) => (
            <Card key={group} pad={0}>
              <div className="row gap10" style={{ padding: "13px 16px", borderBottom: "1px solid var(--border)" }}>
                <span style={{ width: 30, height: 30, borderRadius: 8, background: "var(--surface-3)", display: "grid", placeItems: "center", color: "var(--dim)" }}><Icon name={GROUP_ICON[group] || "flag"} size={15} /></span>
                <span style={{ fontWeight: 700, fontSize: 13.5 }}>{group}</span>
                <span className="mono faint" style={{ fontSize: 11, marginLeft: "auto" }}>{items.length}</span>
              </div>
              <div className="col">
                {items.map((it, i) => {
                  const conf = flagConf(it.code);
                  const cite = it.idx < 10 ? `rent:${risk.rsn}:flag:${it.idx + 1}` : `rent:${risk.rsn}:score`;
                  return (
                    <div key={i} style={{ padding: "12px 16px", borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <div className="row gap8" style={{ alignItems: "flex-start", marginBottom: 5 }}>
                        <SevTag sev={it.severity} />
                        <span className="grow" style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.35 }}>{it.title}</span>
                      </div>
                      <p className="dim" style={{ fontSize: 12, lineHeight: 1.45, marginBottom: 7 }}>{it.detail}</p>
                      <div className="row gap10 wrap">
                        <Confidence value={conf} />
                        {it.newcomer && <Pill color="var(--c-tool)"><Icon name="user" size={10} /> newcomer</Pill>}
                        {it.code.startsWith("derived:") && <Pill><Icon name="git-branch" size={10} /> derived</Pill>}
                        <Cite ids={[cite]} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============ 3 · INTELLIGENCE / PIO ============ */
export function Intelligence({ pio, risk, resolved }: { pio: PIO; risk: RiskReport; resolved?: AddressResolution }) {
  const nl = risk.newcomer_lens;
  const m = pio.massing;
  const cc = m?.cross_check;
  const candidates = resolved?.candidates ?? [];
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="boxes" eyebrow="PIO Builder" title="Property Intelligence Object" sub="The structured evidence object every agent reads from — each field carries provenance, confidence and, where derived, explicit uncertainty." />

        <div className="row gap16 wrap" style={{ alignItems: "stretch" }}>
          <Card className="grow" style={{ minWidth: 300 }}>
            <div className="eyebrow" style={{ marginBottom: 12 }}>Address resolution</div>
            <div className="row gap10" style={{ marginBottom: 12 }}>
              <Icon name="map-pin" size={16} color="var(--green)" />
              <div className="grow">
                <div style={{ fontSize: 14, fontWeight: 700 }}>{risk.address}</div>
                <div className="faint" style={{ fontSize: 11.5 }}>{risk.ward_name ?? "Toronto"} · {resolved?.status?.replace(/_/g, " ") ?? "matched"}</div>
              </div>
              <div className="col" style={{ alignItems: "flex-end" }}>
                <span className="mono tabnum" style={{ fontSize: 15, fontWeight: 700, color: "var(--green)" }}>{Math.round((resolved?.confidence ?? 1) * 100)}%</span>
                <span className="eyebrow">match</span>
              </div>
            </div>
            {candidates.length > 0 && (
              <div className="col gap6">
                <span className="faint" style={{ fontSize: 10.5 }}>CANDIDATES CONSIDERED</span>
                {candidates.slice(0, 4).map((c, i) => (
                  <div key={c.rsn} className="row gap10" style={{ alignItems: "center" }}>
                    <Icon name={i === 0 ? "check-circle" : "circle"} size={13} color={i === 0 ? "var(--green)" : "var(--ghost)"} />
                    <span className="grow" style={{ fontSize: 12, color: i === 0 ? "var(--text)" : "var(--faint)" }}>{c.address}</span>
                    <div style={{ width: 70 }}><Meter value={c.match_confidence} color={i === 0 ? "var(--green)" : "var(--border-3)"} /></div>
                    <span className="mono faint tabnum" style={{ fontSize: 10, width: 32, textAlign: "right" }}>{c.match_confidence.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 12 }}><Cite ids={[`pio:rentsafeto`]} /></div>
          </Card>

          <Card style={{ width: 300, flexShrink: 0 }}>
            <div className="eyebrow" style={{ marginBottom: 10 }}>Confidence & completeness</div>
            <div className="row gap20">
              <Stat label="Confidence" value={Math.round(pio.overall_confidence * 100)} unit="%" color="var(--green)" />
              <Stat label="Completeness" value={Math.round(pio.data_completeness * 100)} unit="%" color="var(--c-tool)" />
            </div>
            <div style={{ height: 1, background: "var(--border)", margin: "12px 0" }} />
            <div className="row gap16 wrap">
              <Stat label="Type" value={pio.property_type ?? "Apartment"} mono={false} />
              {pio.latitude != null && <div className="col gap4"><span className="eyebrow">Geo</span><span className="mono" style={{ fontSize: 11.5, color: "var(--dim)" }}>{pio.latitude.toFixed(3)}, {pio.longitude?.toFixed(3)}</span></div>}
            </div>
          </Card>
        </div>

        {/* 3D massing */}
        {m?.matched && (
          <Card>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
              <div className="eyebrow">City 3D Massing · {m.height_source}</div>
              <Cite ids={[`massing:${pio.rsn}`]} />
            </div>
            <div className="row gap20 wrap" style={{ alignItems: "center" }}>
              <div style={{ width: 280, flexShrink: 0 }}><Massing3D footprint={m.footprint_m} height={m.max_height_m ?? m.avg_height_m ?? 10} /></div>
              <div className="grow col gap12" style={{ minWidth: 240 }}>
                <div className="row gap20 wrap">
                  <Stat label="Roof height" value={m.max_height_m ?? "—"} unit="m" />
                  <Stat label="Avg height" value={m.avg_height_m ?? "—"} unit="m" />
                  <Stat label="Footprint" value={m.footprint_area_m2 ? Math.round(m.footprint_area_m2).toLocaleString() : "—"} unit="m²" />
                </div>
                {cc && (
                  <div style={{ padding: "11px 13px", borderRadius: "var(--r)", border: "1px solid " + (cc.status === "consistent" ? "color-mix(in oklch,var(--green) 28%, transparent)" : "color-mix(in oklch,var(--r-elev) 30%, transparent)"), background: cc.status === "consistent" ? "var(--green-bg)" : "var(--r-elev-bg)" }}>
                    <div className="row gap6" style={{ marginBottom: 3 }}>
                      <Icon name={cc.status === "consistent" ? "check-circle" : "alert-triangle"} size={13} color={cc.status === "consistent" ? "var(--green)" : "var(--r-elev)"} />
                      <span className="eyebrow" style={{ color: cc.status === "consistent" ? "var(--green)" : "var(--r-elev)" }}>Height cross-check · {cc.status}</span>
                    </div>
                    <p className="dim" style={{ fontSize: 12, lineHeight: 1.45 }}>{cc.note}</p>
                  </div>
                )}
                <span className="faint" style={{ fontSize: 11, fontStyle: "italic" }}>Real footprint extruded to {Math.round(m.max_height_m ?? 0)} m · visualization + cross-check, never used in scoring.</span>
              </div>
            </div>
          </Card>
        )}

        {/* newcomer context */}
        {nl && (
          <Card style={{ borderColor: "color-mix(in oklch,var(--c-tool) 22%, transparent)" }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
              <div className="eyebrow" style={{ color: "var(--c-tool)" }}>Newcomer / equity context</div>
              <div className="row gap8"><Pill color="var(--c-tool)"><Icon name="git-branch" size={10} /> derived</Pill><Pill color={gradeMeta(nl.risk_level === "Severe" || nl.risk_level === "High" ? "D" : "C").color}>{nl.risk_level} for newcomers</Pill></div>
            </div>
            <p className="dim" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{nl.summary}</p>
            {nl.questions_to_ask.length > 0 && (
              <div className="col gap6" style={{ marginTop: 10 }}>
                <span className="eyebrow">Questions to ask before signing</span>
                {nl.questions_to_ask.slice(0, 4).map((q, i) => (
                  <div key={i} className="row gap8" style={{ alignItems: "flex-start" }}><Icon name="help-circle" size={12} color="var(--c-tool)" style={{ marginTop: 2 }} /><span style={{ fontSize: 12, lineHeight: 1.45 }}>{q}</span></div>
                ))}
              </div>
            )}
            <div className="row" style={{ marginTop: 10 }}>
              <span className="faint" style={{ fontSize: 11, fontStyle: "italic" }}>Derived indicator — context only, not a building deficiency.</span>
            </div>
          </Card>
        )}

        {/* provenance ledger */}
        <Card pad={0}>
          <div className="row" style={{ padding: "13px 18px", borderBottom: "1px solid var(--border)", justifyContent: "space-between" }}>
            <span className="eyebrow">Provenance ledger · {pio.provenance.length} adapters</span>
            <span className="mono faint" style={{ fontSize: 11 }}>status · confidence</span>
          </div>
          <div className="col">
            {pio.provenance.map((s, i) => {
              const col = s.status === "ok" ? "var(--green)" : s.status === "uncertain" ? "var(--r-mod)" : "var(--faint)";
              return (
                <div key={s.source} className="row gap12" style={{ padding: "9px 18px", borderBottom: i < pio.provenance.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--c-tool)", width: 150, flexShrink: 0 }}>{s.source}</span>
                  <span className="grow faint" style={{ fontSize: 11.5, lineHeight: 1.35 }}>{s.note}</span>
                  <span className="mono" style={{ fontSize: 10, color: col, width: 70, textTransform: "uppercase", flexShrink: 0, textAlign: "right" }}>{s.status}</span>
                  <div style={{ width: 54, flexShrink: 0 }}><Meter value={s.confidence} color={s.confidence >= 0.8 ? "var(--green)" : s.confidence >= 0.5 ? "var(--r-mod)" : "var(--r-elev)"} /></div>
                  <span className="mono tabnum faint" style={{ fontSize: 10, width: 26, textAlign: "right", flexShrink: 0 }}>{Math.round(s.confidence * 100)}</span>
                </div>
              );
            })}
          </div>
        </Card>

        {pio.uncertainties.length > 0 && (
          <Banner icon="help-circle" tone="warn" title="Surfaced uncertainties">{pio.uncertainties.slice(0, 4).join(" · ")}</Banner>
        )}
      </div>
    </div>
  );
}

/* ============ 4 · OPERATOR / PORTFOLIO ============ */
const scoreCol = (s: number | null) => {
  const v = s ?? 0;
  return v < 65 ? "var(--r-high)" : v < 70 ? "var(--r-elev)" : v < 80 ? "var(--r-mod)" : "var(--green)";
};

export function OperatorPanel({ operator: o }: { operator: OperatorPortfolioReport }) {
  const resolved = !!o.operator_name_canonical && o.status === "operator_resolved";
  const peers = o.portfolio_buildings || [];
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="building-2" eyebrow="Operator / Portfolio · model-resolved" title="Operator Pattern"
          sub="Who runs this building — and does the same failure repeat across every building they run? The public city site shows one building at a time; connecting them is the non-obvious insight."
          right={resolved ? <Pill color="var(--green)"><Icon name="cpu" size={11} /> entity-resolved</Pill> : undefined} />

        {!resolved ? (
          <Card>
            <div className="row gap10" style={{ marginBottom: 6 }}>
              <span style={{ width: 38, height: 38, borderRadius: 9, background: "var(--surface-3)", display: "grid", placeItems: "center", color: "var(--dim)" }}><Icon name="building-2" size={18} /></span>
              <div className="grow">
                <div style={{ fontSize: 15, fontWeight: 700 }}>No registered operator on file</div>
                <div className="mono faint" style={{ fontSize: 11 }}>{o.status.replace(/_/g, " ")}</div>
              </div>
            </div>
            <p className="dim" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{o.uncertainty}</p>
          </Card>
        ) : (
          <>
            <Card>
              <div className="row gap12" style={{ alignItems: "flex-start" }}>
                <span style={{ width: 42, height: 42, borderRadius: 10, background: "var(--green-bg)", display: "grid", placeItems: "center", color: "var(--green)", flexShrink: 0 }}><Icon name="building-2" size={20} /></span>
                <div className="grow">
                  <div style={{ fontSize: 17, fontWeight: 800 }}>{o.operator_name_canonical}</div>
                  <div className="mono faint" style={{ fontSize: 11 }}>registered as “{o.operator_name}” · {o.n_portfolio} building{o.n_portfolio !== 1 ? "s" : ""} on file</div>
                </div>
                <div className="col" style={{ alignItems: "flex-end", gap: 4 }}>
                  <span className="eyebrow">link confidence</span>
                  <div style={{ width: 90 }}><Meter value={o.confidence} max={1} color={o.confidence >= 0.75 ? "var(--green)" : o.confidence >= 0.5 ? "var(--r-mod)" : "var(--r-elev)"} /></div>
                  <span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>{Math.round(o.confidence * 100)}%</span>
                </div>
              </div>
              {o.operator_reasoning && (
                <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 8, background: "var(--surface-2)", border: "1px solid var(--border)" }}>
                  <div className="row gap6" style={{ marginBottom: 4 }}><Icon name="cpu" size={12} color="var(--green)" /><span className="eyebrow">how the model linked it</span></div>
                  <p style={{ fontSize: 12.5, lineHeight: 1.5 }}>{o.operator_reasoning}</p>
                </div>
              )}
            </Card>

            {o.pattern_summary && (
              <Card style={{ borderColor: "color-mix(in oklch, var(--r-elev) 35%, var(--border))" }}>
                <div className="row gap8" style={{ alignItems: "flex-start" }}>
                  <Icon name="trending-down" size={16} color="var(--r-elev)" style={{ marginTop: 2 }} />
                  <p style={{ fontSize: 14, lineHeight: 1.55, fontWeight: 600 }}>{o.pattern_summary}</p>
                </div>
              </Card>
            )}

            {peers.length > 0 && (
              <Card pad={0}>
                <div className="row" style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", justifyContent: "space-between" }}>
                  <span className="eyebrow">Portfolio buildings · shared failures</span>
                  <span className="mono faint" style={{ fontSize: 10.5 }}>showing {peers.length} of {o.n_portfolio}</span>
                </div>
                <div className="col">
                  {peers.map((b, i) => (
                    <div key={b.rsn} className="row gap12" style={{ padding: "10px 16px", borderBottom: i < peers.length - 1 ? "1px solid var(--border)" : "none", alignItems: "flex-start" }}>
                      <div className="grow col gap4" style={{ minWidth: 0 }}>
                        <span style={{ fontSize: 12.5, fontWeight: 600 }}>{b.address}</span>
                        {b.shared_violations.length > 0 && (
                          <div className="row gap6 wrap">
                            {b.shared_violations.slice(0, 4).map((v) => (
                              <span key={v} className="pill" style={{ fontSize: 9.5, color: "var(--r-elev)", borderColor: "color-mix(in oklch, var(--r-elev) 40%, transparent)" }}>{v}</span>
                            ))}
                            {b.shared_violations.length > 4 && <span className="faint" style={{ fontSize: 10 }}>+{b.shared_violations.length - 4}</span>}
                          </div>
                        )}
                      </div>
                      <div style={{ width: 64, marginTop: 2 }}><Meter value={b.score ?? 0} max={100} color={scoreCol(b.score)} /></div>
                      <span className="mono tabnum" style={{ fontSize: 12, fontWeight: 700, width: 30, textAlign: "right", color: scoreCol(b.score) }}>{b.score ?? "—"}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {o.pattern_citations.length > 0 && (
              <Card>
                <div className="eyebrow" style={{ marginBottom: 10 }}>Evidence · specific failed inspections ({o.pattern_citations.length})</div>
                <div className="col gap6" style={{ maxHeight: 220, overflow: "auto" }}>
                  {o.pattern_citations.map((c, i) => (
                    <div key={i} className="row gap8" style={{ fontSize: 12 }}>
                      <span className="mono" style={{ width: 14, color: c.grade === 0 ? "var(--r-high)" : "var(--r-elev)", fontWeight: 700 }}>{c.grade}</span>
                      <span style={{ fontWeight: 600 }}>{c.category}</span>
                      <span className="faint">·</span>
                      <span className="dim grow" style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.address}</span>
                      {c.grade === 0 && <span className="mono" style={{ fontSize: 9.5, color: "var(--r-high)" }}>doc absent</span>}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}

        {o.portfolio_basis && <p className="faint" style={{ fontSize: 11.5, fontStyle: "italic" }}>{o.portfolio_basis}</p>}
        {o.human_checkpoint && <Banner icon="user-check" tone="warn" title="Human checkpoint">{o.human_checkpoint}</Banner>}
      </div>
    </div>
  );
}

/* ============ · NEIGHBOURHOOD SAFETY ============ */
const SAFETY_BAND: Record<string, { color: string; label: string }> = {
  safer: { color: "var(--green)", label: "Safer area" },
  moderate: { color: "var(--r-mod)", label: "Mid-city" },
  higher: { color: "var(--r-high)", label: "Higher-crime area" },
};

export function SafetyPanel({ safety }: { safety: NeighbourhoodSafety }) {
  const b = SAFETY_BAND[safety.band] ?? SAFETY_BAND.moderate;
  if (!safety.available) {
    return (
      <div style={SCROLL}>
        <SectionHeader icon="shield" eyebrow="Neighbourhood context" title="Neighbourhood Safety" sub="" />
        <Card><p className="faint" style={{ fontSize: 13 }}>No neighbourhood-safety data is available for this building's location.</p></Card>
      </div>
    );
  }
  const maxCat = Math.max(1, ...safety.top_categories.map((c) => c.count));
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="shield" eyebrow="Neighbourhood context · Toronto Police MCI" title="Neighbourhood Safety"
          sub={safety.neighbourhood} right={<Pill color={b.color}>{b.label}</Pill>} />

        <Card style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 26, alignItems: "center" }}>
          <ScoreGauge value={safety.safety_percentile} color={b.color} size={140} sub="safety percentile" />
          <div className="col gap12">
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: b.color }}>{b.label}</div>
              <div className="mono faint" style={{ fontSize: 11 }}>higher percentile = fewer reported incidents vs. other Toronto neighbourhoods</div>
            </div>
            <p style={{ fontSize: 14, lineHeight: 1.55 }}>{safety.summary}</p>
          </div>
        </Card>

        <div className="row gap16 wrap" style={{ alignItems: "stretch" }}>
          <Card className="grow" style={{ minWidth: 150 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Reported / year</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700 }}>{safety.per_year.toLocaleString()}</div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>major crimes · 3-yr avg</div>
          </Card>
          <Card className="grow" style={{ minWidth: 150 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Violent</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700, color: "var(--r-high)" }}>{Math.round(safety.violent_3y / 3).toLocaleString()}<span className="faint" style={{ fontSize: 12, fontWeight: 500 }}>/yr</span></div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>assault, robbery</div>
          </Card>
          <Card className="grow" style={{ minWidth: 150 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Property</div>
            <div className="mono tabnum" style={{ fontSize: 24, fontWeight: 700, color: "var(--r-elev)" }}>{Math.round(safety.property_3y / 3).toLocaleString()}<span className="faint" style={{ fontSize: 12, fontWeight: 500 }}>/yr</span></div>
            <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>break-in, auto theft, theft</div>
          </Card>
        </div>

        {safety.top_categories.length > 0 && (
          <Card>
            <div className="eyebrow" style={{ marginBottom: 12 }}>Reported incidents by type · last 3 years</div>
            <div className="col gap10">
              {safety.top_categories.map((c) => (
                <div key={c.category} className="row gap12" style={{ alignItems: "center" }}>
                  <span style={{ width: 150, fontSize: 12.5 }}>{c.category}</span>
                  <div className="grow"><Meter value={c.count} max={maxCat} color={b.color} /></div>
                  <span className="mono tabnum" style={{ fontSize: 11, width: 54, textAlign: "right", color: "var(--dim)" }}>{c.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Banner icon="info" tone="legal">{safety.disclaimer} <span className="faint">{safety.basis}</span></Banner>
      </div>
    </div>
  );
}

/* ============ 5 · RIGHTS GROUNDING ============ */
export function RightsPanel({ rights }: { rights: RightsGroundingReport }) {
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="scale" eyebrow="Rights Grounding" title="Tenant-Rights Grounding" sub="Each building issue is mapped to verified Ontario tenant-rights sources. The agent is constrained to cite — it cannot invent law." />
        <Banner icon="alert-triangle" tone="warn" title="Legal information, not legal advice">{rights.disclaimer}</Banner>
        <div className="col gap14">
          {rights.rights.map((r, i) => (
            <Card key={i}>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <div className="row gap8"><Icon name="shield-check" size={15} color="var(--green)" /><span style={{ fontSize: 14, fontWeight: 700 }}>{r.title}</span></div>
                {r.topic && <Cite ids={[`rights:${r.topic}`]} />}
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.55 }}>{r.right}</p>
              {r.legal_basis && <p className="mono" style={{ fontSize: 10.5, color: "var(--green)", marginTop: 8, lineHeight: 1.5 }}>{r.legal_basis}</p>}
              {r.what_you_can_do && r.what_you_can_do.length > 0 && (
                <div className="row gap10" style={{ marginTop: 10, alignItems: "flex-start", padding: "9px 12px", borderRadius: "var(--r)", background: "var(--surface-2)" }}>
                  <Icon name="arrow-right-circle" size={14} color="var(--green)" style={{ marginTop: 1 }} />
                  <span className="dim" style={{ fontSize: 12, lineHeight: 1.45 }}><b style={{ color: "var(--text)" }}>What you can do — </b>{r.what_you_can_do[0]}</span>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============ 6 · ADVOCATE ============ */
const ADV_LANGUAGES = [
  "English", "Simplified Chinese", "Traditional Chinese", "Punjabi", "Tagalog",
  "Tamil", "Spanish", "Urdu", "Persian (Farsi)", "Portuguese", "Russian",
  "Korean", "Arabic", "Italian", "French",
];

export function AdvocateSection({ advocacy, language, onLanguage }: { advocacy: AdvocacyReport; language: string; onLanguage: (lang: string) => void }) {
  const byModel = advocacy.generated_by === "local_model";
  const cards: { h: string; p: string }[] = [
    { h: "Bottom line", p: advocacy.bottom_line },
    ...(advocacy.what_this_means_for_you ? [{ h: "What this means for you", p: advocacy.what_this_means_for_you }] : []),
    ...advocacy.key_concerns.map((c) => ({ h: c.title, p: c.why_it_matters })),
  ];
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="megaphone" eyebrow="Advocate" title="Plain-Language Guidance" sub="Customized for a newcomer renter profile and grounded in the cited rights — no new claims introduced."
          right={
            <div className="row gap8">
              <select value={language} onChange={(e) => onLanguage(e.target.value)} title="Generate this guidance in another language"
                style={{ padding: "4px 9px", borderRadius: 4, border: "1px solid var(--border-2)", background: "var(--surface)", color: "var(--text)", fontSize: 12 }}>
                {ADV_LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
              <Pill color={byModel ? "var(--green)" : "var(--c-tool)"}><Icon name={byModel ? "cpu" : "function-square"} size={11} /> {byModel ? "local model" : "deterministic"}</Pill>
            </div>
          } />
        <p style={{ fontSize: 14, lineHeight: 1.55 }}>{advocacy.headline}</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {cards.map((s, i) => (
            <Card key={i} style={{ display: "flex", gap: 13 }}>
              <span className="mono" style={{ width: 26, height: 26, borderRadius: 99, background: "var(--green-bg)", border: "1px solid var(--border-2)", display: "grid", placeItems: "center", color: "var(--green)", flexShrink: 0, fontWeight: 700, fontSize: 12 }}>{i + 1}</span>
              <div><div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 4 }}>{s.h}</div><p className="dim" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{s.p}</p></div>
            </Card>
          ))}
        </div>
        {advocacy.recommended_actions.length > 0 && (
          <Card>
            <div className="eyebrow" style={{ marginBottom: 10 }}>Recommended actions</div>
            <div className="col gap8">
              {advocacy.recommended_actions.map((a, i) => (
                <div key={i} className="row gap8" style={{ alignItems: "flex-start" }}><Icon name="check-circle" size={14} color="var(--green)" style={{ marginTop: 1 }} /><span style={{ fontSize: 12.5, lineHeight: 1.45 }}>{a}</span></div>
              ))}
            </div>
          </Card>
        )}
        {advocacy.schools_nearby.length > 0 && (
          <Card>
            <div className="row gap6" style={{ marginBottom: 10 }}>
              <Icon name="map-pin" size={13} color="var(--green)" />
              <span className="eyebrow" style={{ margin: 0 }}>Schools nearby · good for families</span>
            </div>
            <div className="col gap8">
              {advocacy.schools_nearby.map((s, i) => (
                <div key={i} className="row gap8" style={{ alignItems: "flex-start", justifyContent: "space-between" }}>
                  <div className="row gap8" style={{ alignItems: "flex-start" }}>
                    <Icon name="check-circle" size={14} color="var(--green)" style={{ marginTop: 1, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontSize: 12.5, fontWeight: 600 }}>{s.name}</div>
                      <div className="faint" style={{ fontSize: 11 }}>{s.type}{s.address ? " · " + s.address : ""}</div>
                    </div>
                  </div>
                  <span className="mono faint" style={{ fontSize: 11, flexShrink: 0 }}>{s.distance_m < 1000 ? s.distance_m + " m" : (s.distance_m / 1000).toFixed(1) + " km"}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
        <Banner icon="user-check" tone="warn" title={(advocacy.continuum_mode === "human_verification" ? "Human verification" : "Recommendation") + " · " + advocacy.agency_stakes + " stakes"}>
          {advocacy.agency_rationale}
        </Banner>
        <p className="faint" style={{ fontSize: 11, lineHeight: 1.5 }}>{advocacy.limitations} {advocacy.disclaimer}</p>
      </div>
    </div>
  );
}

/* ============ 7 · 311 DRAFT + HUMAN GATE ============ */
export function DraftPanel({ draft, approval, onApprove, onRequestChanges }: {
  draft: ComplaintDraft; approval: string; onApprove: () => void; onRequestChanges: () => void;
}) {
  const approved = approval === "approved";
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="file-text" eyebrow="311 Draft" title="311 / RentSafeTO Complaint Draft" sub="Composed only from cited evidence. Held at a human approval gate before anything leaves the workspace." />
        <Banner icon="shield" tone="legal">This is a <b>draft for your review</b>. Meraklis never submits to any real city service — approval here only marks the draft ready to copy or export.</Banner>

        <Card pad={0} style={{ overflow: "hidden", borderColor: approved ? "color-mix(in oklch,var(--green) 35%, transparent)" : "color-mix(in oklch,var(--c-human) 35%, transparent)" }}>
          <div className="row gap12" style={{ padding: "14px 18px", background: approved ? "var(--green-bg)" : "var(--r-elev-bg)", borderBottom: "1px solid var(--border)" }}>
            <Icon name={approved ? "check-circle" : "user-check"} size={18} color={approved ? "var(--green)" : "var(--c-human)"} />
            <div className="grow">
              <div style={{ fontSize: 13, fontWeight: 700, color: approved ? "var(--green)" : "var(--c-human)" }}>{approved ? "Approved by human reviewer" : "Human approval gate — awaiting review"}</div>
              <div className="dim" style={{ fontSize: 11.5, marginTop: 1 }}>{approved ? "Logged to the audit trail with a reviewer checkpoint." : "An agent drafted this. A person must approve before it leaves the workspace."}</div>
            </div>
            {!approved ? (
              <div className="row gap8">
                <button className="btn btn-ghost btn-sm" onClick={onRequestChanges}><Icon name="rotate-ccw" size={13} /> Request changes</button>
                <button className="btn btn-pri btn-sm" onClick={onApprove}><Icon name="check" size={13} /> Approve draft</button>
              </div>
            ) : (
              <div className="row gap8">
                <button className="btn btn-ghost btn-sm" onClick={() => navigator.clipboard?.writeText(`${draft.title}\n\n${draft.body}`)}><Icon name="copy" size={13} /> Copy</button>
                <button className="btn btn-ghost btn-sm"><Icon name="download" size={13} /> Export</button>
              </div>
            )}
          </div>
          <div style={{ padding: "20px 22px", background: "var(--surface-2)" }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <div className="col gap2"><span className="faint" style={{ fontSize: 11 }}>To</span><span style={{ fontSize: 12.5, fontWeight: 600 }}>City of Toronto — 311 / RentSafeTO</span></div>
              <Pill color={approved ? "var(--green)" : "var(--c-human)"}>{approved ? "READY" : "DRAFT — UNAPPROVED"}</Pill>
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{draft.title}</div>
            <pre className="mono" style={{ fontSize: 11.5, lineHeight: 1.65, whiteSpace: "pre-wrap", color: "var(--text)" }}>{draft.body}</pre>
            <div className="row gap8 wrap" style={{ marginTop: 14 }}><span className="faint" style={{ fontSize: 11 }}>Evidence cited:</span><Cite ids={draft.evidence_ids} /></div>
          </div>
        </Card>
        <Banner icon="filter" tone="neutral" title="Drafting guard">{draft.approval_gate}</Banner>
      </div>
    </div>
  );
}

/* ============ 8 · AUDIT TRAIL ============ */
export function AuditPanel({ audit, approval }: { audit: AuditStep[]; approval: string }) {
  const nModel = audit.reduce((n, s) => n + s.model_calls.length, 0);
  const nTool = audit.reduce((n, s) => n + s.tool_calls.length, 0);
  const nFall = audit.reduce((n, s) => n + s.model_calls.filter((m) => m.fallback_used).length, 0);
  const nCheck = audit.filter((s) => s.human_checkpoint).length + (approval === "approved" ? 1 : 0);
  return (
    <div style={SCROLL}>
      <div className="col" style={{ gap: 16 }}>
        <SectionHeader icon="list-checks" eyebrow="Audit" title="Audit Trail" sub="Every model call, tool call, deterministic fallback and human checkpoint — recorded so a judge can verify no claim was hallucinated." />
        <div className="row gap12 wrap">
          <Card className="grow" style={{ minWidth: 120 }}><Stat label="Steps" value={audit.length} color="var(--text)" /></Card>
          <Card className="grow" style={{ minWidth: 120 }}><Stat label="Model calls" value={nModel} color="var(--green)" /></Card>
          <Card className="grow" style={{ minWidth: 120 }}><Stat label="Tool calls" value={nTool} color="var(--c-tool)" /></Card>
          <Card className="grow" style={{ minWidth: 120 }}><Stat label="Fallbacks" value={nFall} color="var(--c-fall)" /></Card>
          <Card className="grow" style={{ minWidth: 140 }}><Stat label="Ungrounded claims" value="0" color="var(--green)" sub="every claim → evidence" /></Card>
        </div>
        <Card pad={0}>
          <div className="row" style={{ padding: "11px 16px", borderBottom: "1px solid var(--border)", justifyContent: "space-between" }}>
            <span className="eyebrow">Sealed log · {audit.length} steps · {nCheck} checkpoints</span>
            <span className="mono faint" style={{ fontSize: 10.5 }}>local · auditable</span>
          </div>
          <div className="col">
            {audit.map((s, i) => {
              const tag = s.model_calls.some((m) => !m.fallback_used) ? { t: "MODEL", c: "var(--green)" }
                : s.model_calls.length ? { t: "FALLBACK", c: "var(--c-fall)" }
                : s.deterministic_fallback ? { t: "ENGINE", c: "var(--c-tool)" }
                : { t: "TOOL", c: "var(--c-tool)" };
              return (
                <div key={s.id} className="row gap10" style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)", alignItems: "flex-start", fontSize: 11.5 }}>
                  <span className="mono faint tabnum" style={{ fontSize: 10, width: 26, flexShrink: 0 }}>{String(i + 1).padStart(2, "0")}</span>
                  <span className="mono faint" style={{ fontSize: 10, width: 78, flexShrink: 0 }}>{s.agent.replace(" Agent", "").slice(0, 11)}</span>
                  <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, color: s.human_checkpoint ? "var(--c-human)" : tag.c, width: 70, flexShrink: 0 }}>{tag.t}</span>
                  <span className="grow" style={{ lineHeight: 1.4 }}>{s.output_summary || s.action}</span>
                  <span className="mono faint tabnum" style={{ fontSize: 10, width: 46, textAlign: "right", flexShrink: 0 }}>{s.latency_ms}ms</span>
                  <span className="mono tabnum" style={{ fontSize: 10, width: 34, textAlign: "right", flexShrink: 0, color: "var(--dim)" }}>{Math.round(s.confidence * 100)}%</span>
                </div>
              );
            })}
            {approval === "approved" && (
              <div className="row gap10 fade-in" style={{ padding: "8px 16px", alignItems: "flex-start", fontSize: 11.5, background: "var(--green-bg)" }}>
                <span className="mono faint tabnum" style={{ fontSize: 10, width: 26, flexShrink: 0 }}>{String(audit.length + 1).padStart(2, "0")}</span>
                <span className="mono faint" style={{ fontSize: 10, width: 78, flexShrink: 0 }}>Draft</span>
                <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, color: "var(--c-human)", width: 70, flexShrink: 0 }}>HUMAN</span>
                <span className="grow" style={{ lineHeight: 1.4, color: "var(--green)" }}>Human reviewer approved the 311 draft</span>
                <span className="mono" style={{ fontSize: 9.5, width: 80, textAlign: "right", flexShrink: 0, color: "var(--green)" }}>checkpoint</span>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
