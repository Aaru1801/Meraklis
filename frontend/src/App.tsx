import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api, streamInvestigation, type EdgeEvent, type EdgeRuntimeStatus, type EvidenceRef,
} from "./api";
import { EvidenceCtx } from "./lib/evidence";
import { type DemoCard } from "./components/SearchScreen";
import { CityLanding } from "./components/CityLanding";
import { Workspace, type LiveData } from "./components/Workspace";
import { SourceDrawer } from "./components/SourceDrawer";
import { Team } from "./components/Team";
import type { AuditStep, CityBuilding, PipelineStage, UserProfile } from "./api";

const EMPTY: LiveData = { audit_trail: [] };
const PROFILE_KEY = "meraklis.profile";
const DEFAULT_PROFILE: UserProfile = { is_newcomer: true, priorities: ["safety", "pests", "heat"] };
function loadProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (raw) return { ...DEFAULT_PROFILE, ...(JSON.parse(raw) as UserProfile) };
  } catch { /* ignore corrupt storage */ }
  return DEFAULT_PROFILE;
}

export default function App() {
  const [view, setView] = useState<"search" | "workspace">("search");
  const [runtime, setRuntime] = useState<EdgeRuntimeStatus | null>(null);
  const [demos, setDemos] = useState<DemoCard[]>([]);
  const [city, setCity] = useState<CityBuilding[]>([]);
  const [address, setAddress] = useState("");

  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [traceByIndex, setTraceByIndex] = useState<Record<number, AuditStep>>({});
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const [data, setData] = useState<LiveData>(EMPTY);
  const [evidence, setEvidence] = useState<EvidenceRef[]>([]);

  const [section, setSection] = useState("trace");
  const [approval, setApproval] = useState("pending");
  const [online, setOnline] = useState(false);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile>(loadProfile);
  const profileRef = useRef(profile);
  const [route, setRoute] = useState(() => window.location.hash);

  useEffect(() => {
    profileRef.current = profile;
    try { localStorage.setItem(PROFILE_KEY, JSON.stringify(profile)); } catch { /* ignore */ }
  }, [profile]);

  const abortRef = useRef<AbortController | null>(null);
  const lastInput = useRef<{ address?: string; rsn?: string | null }>({});

  // bootstrap: runtime + demo buildings (enriched with real grade/score)
  useEffect(() => {
    api.health().then((h) => { setRuntime(h.runtime); setOnline(h.runtime.endpoint_available); }).catch(() => {});
    api.demoAddresses().then(async (list) => {
      const enriched = await Promise.all(list.map(async (d, i): Promise<DemoCard> => {
        try {
          const b = await api.building(d.rsn);
          return { ...d, grade: b.grade, score: b.overall_score, units: b.units, ward: b.ward_name, hero: i === 0 };
        } catch { return { ...d, hero: i === 0 }; }
      }));
      setDemos(enriched);
    }).catch(() => {});
    api.city().then(setCity).catch(() => {});
  }, []);

  const onEvent = useCallback((ev: EdgeEvent) => {
    switch (ev.type) {
      case "pipeline": setStages(ev.stages); break;
      case "agent_start": setRunningIndex(ev.index); break;
      case "agent_done": {
        setTraceByIndex((p) => ({ ...p, [ev.index]: ev.step }));
        setRunningIndex(null);
        const { evidence: ptEv, ...rest } = ev.patch;
        setData((p) => ({ ...p, ...rest }));
        if (ptEv) setEvidence(ptEv);
        break;
      }
      case "runtime": setRuntime(ev.data); break;
      case "result":
        setRuntime(ev.data.runtime);
        setEvidence(ev.data.evidence);
        setData({
          resolved: ev.data.resolved, pio: ev.data.pio ?? undefined, risk: ev.data.risk ?? undefined,
          value: ev.data.value ?? undefined, safety: ev.data.safety ?? undefined,
          operator: ev.data.operator, rights: ev.data.rights, advocacy: ev.data.advocacy ?? undefined,
          draft_311: ev.data.draft_311 ?? undefined, audit_trail: ev.data.audit_trail,
        });
        break;
    }
  }, []);

  const investigate = useCallback(async (input: { address?: string; rsn?: string | null }, opts?: { keepSection?: boolean }) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    lastInput.current = input;
    setAddress(input.address ?? "");
    setStages([]); setTraceByIndex({}); setRunningIndex(null); setData(EMPTY); setEvidence([]);
    setApproval("pending");
    if (!opts?.keepSection) setSection("trace");
    setView("workspace");
    try {
      await streamInvestigation({ address: input.address, rsn: input.rsn, profile: profileRef.current }, onEvent, controller.signal);
      setRunningIndex(null);
    } catch (err) {
      if (!controller.signal.aborted) setRunningIndex(null);
    }
  }, [onEvent]);

  // Switch the report language in place: update the profile and re-generate the
  // current building's guidance in the new language, staying on the same tab.
  const changeLanguage = useCallback((lang: string) => {
    const next: UserProfile = { ...profileRef.current, respond_language: lang === "English" ? null : lang };
    profileRef.current = next;
    setProfile(next);
    if (lastInput.current.address || lastInput.current.rsn) investigate(lastInput.current, { keepSection: true });
  }, [investigate]);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const evidenceMap = useMemo(() => {
    const m = new Map<string, EvidenceRef>();
    evidence.forEach((e) => m.set(e.id, e));
    return m;
  }, [evidence]);

  const ctxValue = useMemo(() => ({ map: evidenceMap, open: (id: string) => setSourceId(id) }), [evidenceMap]);

  if (route === "#team") return <Team />;

  return (
    <EvidenceCtx.Provider value={ctxValue}>
      {view === "search" ? (
        <CityLanding buildings={city} demos={demos} runtime={runtime} onPick={investigate} profile={profile} setProfile={setProfile} />
      ) : (
        <Workspace
          address={address}
          data={data}
          stages={stages}
          traceByIndex={traceByIndex}
          runningIndex={runningIndex}
          runtime={runtime}
          online={online}
          section={section}
          setSection={setSection}
          approval={approval}
          setApproval={setApproval}
          onHome={() => { abortRef.current?.abort(); setView("search"); }}
          onRerun={() => investigate(lastInput.current)}
          language={profile.respond_language ?? "English"}
          onLanguage={changeLanguage}
        />
      )}
      <SourceDrawer ev={sourceId ? evidenceMap.get(sourceId) ?? null : null} onClose={() => setSourceId(null)} />
    </EvidenceCtx.Provider>
  );
}
