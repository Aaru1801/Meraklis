import { useCallback, useMemo, useState, type CSSProperties, type UIEvent } from "react";
import type { CityBuilding, EdgeRuntimeStatus, UserProfile } from "../api";
import { Icon } from "../lib/icons";
import { Logo, Switch } from "../lib/ui";
import { BAND_COLOR } from "./MapCity";
import { MapView } from "./MapView";
import { BASEMAP } from "../lib/basemap";
import type { DemoCard } from "./SearchScreen";
import { nearest, nearestFlagged } from "../lib/geo";

const PRESETS: { label: string; min: number }[] = [
  { label: "All buildings", min: 0 },
  { label: "Lower risk (75+)", min: 75 },
  { label: "Lowest risk (85+)", min: 85 },
];
const LEGEND: { band: string; label: string }[] = [
  { band: "Low", label: "Low" }, { band: "Moderate", label: "Moderate" },
  { band: "Elevated", label: "Elevated" }, { band: "High", label: "High" }, { band: "Severe", label: "Severe" },
];

// Scroll-driven landing: search-bar hero up front, the 2D map blurred behind it.
// Scrolling zooms the hero, fades it out, and un-blurs the map into an interactive
// view. `p` is scroll progress 0..1.
export function CityLanding({ buildings, demos, runtime, onPick, profile, setProfile }: {
  buildings: CityBuilding[];
  demos: DemoCard[];
  runtime: EdgeRuntimeStatus | null;
  onPick: (input: { address?: string; rsn?: string | null }) => void;
  profile: UserProfile;
  setProfile: (p: UserProfile) => void;
}) {
  const [q, setQ] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [includeUnknown, setIncludeUnknown] = useState(true);
  const [me, setMe] = useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [geoErr, setGeoErr] = useState(false);
  const [p, setP] = useState(0);

  const onScroll = useCallback((e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const max = el.clientHeight * 0.85; // reveal the map over ~0.85 viewport-heights of scroll
    setP(Math.min(1, Math.max(0, el.scrollTop / max)));
  }, []);

  const demoRsns = useMemo(() => new Set(demos.map((d) => d.rsn)), [demos]);
  const visibleCount = useMemo(
    () => buildings.filter((b) => (b.score != null ? b.score >= minScore : includeUnknown)).length,
    [buildings, minScore, includeUnknown],
  );
  const mostSevere = useMemo(() => {
    const scored = buildings.filter((b) => b.score != null);
    return scored.length ? scored.reduce((a, b) => ((b.score as number) < (a.score as number) ? b : a)) : null;
  }, [buildings]);

  const near = useMemo(() => (me ? nearest(buildings, me.lat, me.lng, 8) : []), [me, buildings]);
  const nearRsns = useMemo(() => new Set(near.map((x) => x.b.rsn)), [near]);
  const flaggedNear = useMemo(() => nearestFlagged(near), [near]);
  const locate = useCallback(() => {
    if (!navigator.geolocation) { setGeoErr(true); return; }
    setLocating(true); setGeoErr(false);
    navigator.geolocation.getCurrentPosition(
      (pos) => { setMe({ lat: pos.coords.latitude, lng: pos.coords.longitude }); setLocating(false); },
      () => { setGeoErr(true); setLocating(false); },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
    );
  }, []);

  // scroll-derived transforms
  const heroScale = 1 + p * 0.55;
  const heroOpacity = p < 0.5 ? 1 : Math.max(0, 1 - (p - 0.5) / 0.35);
  const overlayOpacity = Math.max(0, Math.min(1, (p - 0.5) / 0.4));
  const blur = (1 - p) * 12;
  const mapLive = p > 0.88;
  const heroLive = heroOpacity > 0.25;
  const chipStyle = (color: string, bg: string): CSSProperties => ({
    padding: "5px 11px", borderRadius: 6, fontSize: 11.5, fontWeight: 700, color, background: bg,
  });

  return (
    <div onScroll={onScroll} style={{ position: "relative", height: "100%", overflowY: "auto", overflowX: "hidden", background: "var(--bg)" }}>
      {/* fixed blurred 2D map background */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0, filter: `blur(${blur}px)`, opacity: 0.5 + p * 0.5, transition: "filter .12s linear, opacity .12s linear", pointerEvents: mapLive ? "auto" : "none" }}>
        {buildings.length === 0 ? (
          <div className="col" style={{ height: "100%", placeItems: "center", justifyContent: "center", color: "var(--faint)", gap: 10 }}>
            <Icon name="loader" size={26} className="spin" /><span className="mono" style={{ fontSize: 12 }}>loading the city…</span>
          </div>
        ) : (
          <MapView buildings={buildings} minScore={minScore} includeUnknown={includeUnknown} demoRsns={demoRsns} mostSevereRsn={mostSevere?.rsn ?? null} me={me} nearRsns={nearRsns} onPick={onPick} />
        )}
      </div>

      {/* top bar — always */}
      <div className="row" style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 6, justifyContent: "space-between", padding: "16px 22px", gap: 16, pointerEvents: "none" }}>
        <div style={{ pointerEvents: "auto" }}><Logo /></div>
        <div className="row gap10" style={{ pointerEvents: "auto" }}>
          <span className="row gap6"><span className="dot dot-live" /><span className="mono" style={{ fontSize: 11, color: "var(--green)" }}>{runtime?.model_name ?? "local model"}</span></span>
        </div>
      </div>

      {/* hero search — zooms + fades on scroll */}
      <div style={{ position: "fixed", inset: 0, zIndex: 5, display: "grid", placeItems: "center", padding: 24, pointerEvents: "none", opacity: heroOpacity, transform: `scale(${heroScale})`, transformOrigin: "center 44%", transition: "opacity .12s linear, transform .08s linear" }}>
        <div className="col" style={{ alignItems: "center", gap: 18, width: "min(640px, 92vw)", pointerEvents: heroLive ? "auto" : "none" }}>
          <div className="col" style={{ alignItems: "center", gap: 8, textAlign: "center" }}>
            <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.02em", lineHeight: 1.15 }}>Check any Toronto building before you sign</h1>
            <p className="dim" style={{ fontSize: 14 }}>Real City inspection data, scored locally on your NVIDIA edge.</p>
          </div>
          <div className="panel row gap10" style={{ width: "100%", padding: "6px 6px 6px 16px", borderColor: "var(--border-2)", boxShadow: "var(--shadow-lg)", background: "var(--surface)" }}>
            <Icon name="search" size={18} color="var(--faint)" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a Toronto building address…"
              onKeyDown={(e) => { if (e.key === "Enter" && q.trim()) onPick({ address: q.trim() }); }}
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 16, padding: "11px 0" }} />
            <button className="btn btn-pri" onClick={() => q.trim() && onPick({ address: q.trim() })}><Icon name="scan-search" size={15} /> Investigate</button>
          </div>
          <div className="row gap6 wrap" style={{ justifyContent: "center" }}>
            {demos.slice(0, 4).map((d) => (
              <button key={d.rsn} onClick={() => onPick({ address: d.address, rsn: d.rsn })} className="row gap6" style={chipStyle("var(--dim)", "var(--surface-2)")}>
                <span style={{ width: 7, height: 7, borderRadius: 99, background: "var(--green)" }} /> {d.address}
              </button>
            ))}
          </div>
          <div className="col gap4" style={{ alignItems: "center", marginTop: 4, opacity: Math.max(0, 1 - p * 3) }}>
            <span className="mono faint" style={{ fontSize: 10.5 }}>scroll to explore the map</span>
            <Icon name="chevron-right" size={16} color="var(--faint)" style={{ transform: "rotate(90deg)" }} />
          </div>
        </div>
      </div>

      {/* map overlays — fade in as the hero fades out */}
      <div style={{ position: "fixed", inset: 0, zIndex: 3, pointerEvents: "none", opacity: overlayOpacity, transition: "opacity .12s linear" }}>
        {/* quick shortcuts (top center) */}
        <div className="row gap6 wrap" style={{ position: "absolute", top: 66, left: "50%", transform: "translateX(-50%)", justifyContent: "center", maxWidth: "92vw", pointerEvents: mapLive ? "auto" : "none" }}>
          <button onClick={locate} className="row gap6" title="Center the map on your location (needs HTTPS or localhost)"
            style={chipStyle(me ? "#2f6db0" : "var(--dim)", me ? "#e3edf8" : "var(--surface-2)")}>
            <Icon name={locating ? "loader" : "crosshair"} size={11} className={locating ? "spin" : ""} /> {me ? "Located" : "Near me"}
          </button>
          {flaggedNear && (
            <button onClick={() => onPick({ address: flaggedNear.address, rsn: flaggedNear.rsn })} className="row gap6" title={`Nearest flagged building near you: ${flaggedNear.address}`} style={chipStyle("var(--r-high)", "var(--r-high-bg)")}>
              <Icon name="map-pin" size={11} /> Nearest flagged
            </button>
          )}
          {mostSevere && (
            <button onClick={() => onPick({ address: mostSevere.address, rsn: mostSevere.rsn })} className="row gap6" title={`Most severe city-wide: ${mostSevere.address} · City score ${mostSevere.score}`} style={chipStyle("var(--r-high)", "var(--r-high-bg)")}>
              <Icon name="alert-triangle" size={11} /> Most severe
            </button>
          )}
          {geoErr && <span className="mono" style={{ fontSize: 10, color: "var(--faint)", alignSelf: "center" }}>location needs HTTPS or localhost</span>}
        </div>

        {/* filter + personalize panel (bottom-left) */}
        <div className="panel" style={{ position: "absolute", left: 22, bottom: 22, width: 290, padding: 16, maxHeight: "calc(100vh - 110px)", overflowY: "auto", background: "var(--surface)", pointerEvents: mapLive ? "auto" : "none" }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <div className="row gap6"><Icon name="function-square" size={14} color="var(--green)" /><span style={{ fontSize: 13, fontWeight: 700 }}>Filter by risk</span></div>
            <span className="mono faint" style={{ fontSize: 10.5 }}>{visibleCount.toLocaleString()} / {buildings.length.toLocaleString()}</span>
          </div>
          <div className="row gap8" style={{ marginBottom: 4 }}>
            <span className="eyebrow">Min City score</span>
            <span className="mono" style={{ fontSize: 11, color: minScore >= 85 ? "var(--green)" : minScore >= 75 ? "var(--r-mod)" : "var(--dim)", marginLeft: "auto" }}>{minScore === 0 ? "any" : minScore + "+"}</span>
          </div>
          <input type="range" min={0} max={100} value={minScore} onChange={(e) => setMinScore(+e.target.value)} style={{ width: "100%", accentColor: "var(--green)" }} />
          <div className="faint" style={{ fontSize: 10.5, marginTop: 2 }}>Higher City score = lower risk. Drag right to surface the safest buildings.</div>
          <div className="row gap6 wrap" style={{ marginTop: 10 }}>
            {PRESETS.map((pr) => (
              <button key={pr.label} onClick={() => setMinScore(pr.min)} className="mono"
                style={{ fontSize: 10, padding: "5px 9px", borderRadius: 6, color: minScore === pr.min ? "var(--green)" : "var(--dim)", background: minScore === pr.min ? "var(--green-bg)" : "var(--surface-2)" }}>
                {pr.label}
              </button>
            ))}
          </div>
          <div style={{ height: 1, background: "var(--border)", margin: "12px 0 10px" }} />
          <div className="row gap10 wrap">
            {LEGEND.map((l) => (
              <span key={l.band} className="row gap6"><span style={{ width: 9, height: 9, borderRadius: 2, background: BAND_COLOR[l.band] }} /><span className="faint" style={{ fontSize: 10.5 }}>{l.label}</span></span>
            ))}
            <button onClick={() => setIncludeUnknown((v) => !v)} className="row gap6" title="Toggle buildings with no City score" style={{ opacity: includeUnknown ? 1 : 0.45 }}>
              <span style={{ width: 9, height: 9, borderRadius: 2, background: BAND_COLOR.Unknown }} /><span className="faint" style={{ fontSize: 10.5 }}>No score</span>
            </button>
          </div>

          {/* personalize — tailors the building report by household (language switcher lives in the guidance widget) */}
          <div style={{ height: 1, background: "var(--border)", margin: "12px 0 10px" }} />
          <div className="row gap6" style={{ marginBottom: 9 }}>
            <Icon name="user-check" size={13} color="var(--green)" />
            <span style={{ fontSize: 12.5, fontWeight: 700 }}>Personalize report</span>
          </div>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <span className="faint" style={{ fontSize: 11.5 }}>Household size</span>
            <div className="row gap8">
              <button className="mono" onClick={() => setProfile({ ...profile, household_size: Math.max(1, (profile.household_size ?? 1) - 1) })} style={{ width: 20, height: 20, borderRadius: 5, background: "var(--surface-2)", color: "var(--dim)" }}>−</button>
              <span className="mono" style={{ fontSize: 12.5, minWidth: 14, textAlign: "center" }}>{profile.household_size ?? "—"}</span>
              <button className="mono" onClick={() => setProfile({ ...profile, household_size: Math.min(12, (profile.household_size ?? 0) + 1) })} style={{ width: 20, height: 20, borderRadius: 5, background: "var(--surface-2)", color: "var(--dim)" }}>+</button>
            </div>
          </div>
          {([["has_children", "Children at home"], ["has_seniors", "Seniors at home"], ["has_mobility_needs", "Mobility needs"]] as const).map(([key, label]) => (
            <div key={key} className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <span className="faint" style={{ fontSize: 11.5 }}>{label}</span>
              <Switch on={!!profile[key]} onChange={(v) => setProfile({ ...profile, [key]: v })} />
            </div>
          ))}
        </div>

        {/* hint + attribution */}
        <div className="mono" style={{ position: "absolute", bottom: 26, left: "50%", transform: "translateX(-50%)", fontSize: 10.5, color: "var(--ghost)" }}>click a building to investigate · scroll up for search</div>
        <div className="mono" style={{ position: "absolute", bottom: 6, right: 12, fontSize: 9.5, color: "var(--ghost)" }}>{BASEMAP.attribution} · buildings: City of Toronto RentSafeTO</div>
      </div>

      {/* scroll spacer — creates the scroll distance the effects ride on */}
      <div style={{ height: "185vh", pointerEvents: "none" }} />
    </div>
  );
}
