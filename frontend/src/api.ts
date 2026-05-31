// API client + types for OpenHouse Edge.
// Same-origin in prod (FastAPI serves the build); Vite proxies /api in dev.

// ---------------------------------------------------------------------------
// Domain types (mirror the backend pydantic contracts)
// ---------------------------------------------------------------------------
export type Severity = "critical" | "high" | "moderate" | "minor" | "info";

export interface RedFlag {
  code: string;
  title: string;
  detail: string;
  severity: Severity;
  group: string | null;
  newcomer_relevant: boolean;
  category_key: string | null;
  score: number | null;
  evidence: string | null;
}

export interface GroupScore {
  group: string;
  subscore: number | null;
  status: string;
  n_categories: number;
  n_poor: number;
  n_not_assessed: number;
}

export interface TrendInfo {
  direction: string;
  delta: number | null;
  from_year: number | null;
  to_year: number | null;
  history: { year: number; score: number }[];
  narrative: string;
}

export interface NewcomerLens {
  risk_score: number;
  risk_level: string;
  summary: string;
  priorities: RedFlag[];
  questions_to_ask: string[];
}

export interface RiskReport {
  rsn: string;
  address: string;
  ward_name: string | null;
  latitude: number | null;
  longitude: number | null;
  units: number | null;
  storeys: number | null;
  year_built: number | null;
  property_type: string | null;
  overall_score: number | null;
  grade: string;
  risk_level: string;
  risk_score: number;
  summary_line: string;
  headline_factors: string[];
  red_flags: RedFlag[];
  not_assessed: RedFlag[];
  strengths: { title: string; group: string | null }[];
  group_breakdown: GroupScore[];
  newcomer_lens: NewcomerLens | null;
  trend: TrendInfo;
  evaluation_date: string | null;
  n_evaluations: number;
  data_source: string;
  disclaimer: string;
}

export type ValueBand = "good_value" | "fair" | "rich" | "overpriced";
export interface ValueForRisk {
  available: boolean;
  market_rent: number | null;
  market_low: number | null;
  market_high: number | null;
  condition_fair_rent: number | null;
  asking_rent: number | null;
  reference_rent: number | null;
  gap_monthly: number;
  gap_pct: number;
  annual_gap: number;
  band: ValueBand;
  verdict: string;
  value_index: number;
  rationale: string;
  drivers: string[];
  basis: string;
  is_estimate: boolean;
  disclaimer: string;
}

export type SafetyBand = "safer" | "moderate" | "higher";
export interface CrimeCategory {
  category: string;
  count: number;
}
export interface NeighbourhoodSafety {
  available: boolean;
  neighbourhood: string;
  crimes_3y: number;
  violent_3y: number;
  property_3y: number;
  per_year: number;
  safety_percentile: number;
  band: SafetyBand;
  top_categories: CrimeCategory[];
  summary: string;
  basis: string;
  disclaimer: string;
}

export interface Concern {
  title: string;
  why_it_matters: string;
  severity: string;
}
export interface RightSummary {
  title: string;
  summary: string;
  action: string;
}
export interface AdvocacyReport {
  rsn: string;
  address: string;
  risk_level: string;
  grade: string;
  overall_score: number | null;
  headline: string;
  bottom_line: string;
  key_concerns: Concern[];
  what_this_means_for_you: string;
  your_rights: RightSummary[];
  recommended_actions: string[];
  questions_before_signing: string[];
  positives: string[];
  generated_by: string;
  limitations: string;
  disclaimer: string;
  continuum_mode: string;
  agency_stakes: string;
  agency_rationale: string;
  verification_checkpoints: string[];
  data_confidence: number;
  data_completeness: number;
  uncertainties: string[];
}

export interface MarketIntel {
  status: string | null;
  monthly_rent: number | null;
  rent_low: number | null;
  rent_high: number | null;
  source: string | null;
  confidence: number;
  is_estimate: boolean;
  basis: string | null;
}

export interface SourceProvenance {
  source: string;
  status: string;
  confidence: number;
  note: string;
  fetched_at: string | null;
}

export interface MassingCrossCheck {
  rentsafeto_storeys: number | null;
  implied_storeys_low: number | null;
  implied_storeys_high: number | null;
  status: "consistent" | "differs" | "unknown";
  note: string;
}
export interface MassingInfo {
  matched: boolean;
  source: string;
  source_url: string;
  massing_year: number | null;
  distance_m: number | null;
  min_height_m: number | null;
  avg_height_m: number | null;
  max_height_m: number | null;
  surface_elev_m: number | null;
  height_source: string | null;
  footprint_area_m2: number | null;
  n_vertices: number | null;
  centroid: { lat: number; lon: number } | null;
  footprint_m: number[][]; // exterior ring, local ground metres
  cross_check: MassingCrossCheck | null;
}

export interface PIO {
  address_raw?: string;
  address_canonical: string;
  rsn: string | null;
  ward_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  units?: number | null;
  storeys?: number | null;
  year_built?: number | null;
  property_type?: string | null;
  overall_confidence: number;
  data_completeness: number;
  uncertainties: string[];
  provenance: SourceProvenance[];
  market: MarketIntel | null;
  massing?: MassingInfo | null;
}

export interface UserProfile {
  household_size?: number | null;
  has_children?: boolean | null;
  has_seniors?: boolean | null;
  has_mobility_needs?: boolean | null;
  budget_max_monthly?: number | null;
  languages?: string[];
  is_newcomer?: boolean;
  priorities?: string[];
  notes?: string | null;
  respond_language?: string | null;
}

export interface EvidenceRef {
  id: string;
  source: string;
  title: string;
  detail: string;
  confidence: number;
  url: string | null;
}

export interface ModelCallSummary {
  agent: string;
  provider: string;
  model: string;
  endpoint: string;
  status: string;
  latency_ms: number;
  retries: number;
  fallback_used: boolean;
  error: string | null;
}

export interface ToolCallSummary {
  tool: string;
  status: string;
  latency_ms: number;
  output_summary: string;
}

export interface AuditStep {
  id: string;
  agent: string;
  action: string;
  status: string;
  started_at: string;
  completed_at: string;
  latency_ms: number;
  tool_calls: ToolCallSummary[];
  model_calls: ModelCallSummary[];
  deterministic_fallback: boolean;
  confidence: number;
  citations: EvidenceRef[];
  human_checkpoint: string | null;
  output_summary: string;
}

export interface AddressCandidate {
  rsn: string;
  address: string;
  ward_name: string | null;
  score: number | null;
  match_confidence: number;
}

export interface AddressResolution {
  input: string;
  normalized: string;
  rsn: string | null;
  address: string | null;
  confidence: number;
  status: string;
  candidates: AddressCandidate[];
  human_checkpoint: string | null;
}

export interface PortfolioBuilding {
  rsn: string;
  address: string;
  score: number | null;
  shared_violations: string[];
}

export interface PatternCitation {
  rsn: string;
  address: string;
  category: string;
  grade: number;
}

export interface OperatorPortfolioReport {
  status: string;
  operator_name: string | null;
  operator_name_canonical: string | null;
  operator_source: string;
  confidence: number;
  operator_reasoning: string;
  n_portfolio: number;
  repeated_patterns: string[];
  portfolio_buildings: PortfolioBuilding[];
  pattern_summary: string;
  pattern_citations: PatternCitation[];
  portfolio_basis: string;
  uncertainty: string;
  human_checkpoint: string | null;
}

export interface RightsGroundingReport {
  topics: string[];
  rights: {
    topic?: string;
    title?: string;
    right?: string;
    legal_basis?: string;
    source?: string;
    what_you_can_do?: string[];
    escalation?: string;
  }[];
  citations: EvidenceRef[];
  disclaimer: string;
}

export interface ComplaintDraft {
  title: string;
  body: string;
  evidence_ids: string[];
  human_approval_required: boolean;
  approval_gate: string;
  submit_status: string;
}

export interface EdgeRuntimeStatus {
  model_name: string;
  endpoint: string;
  local_edge_status: string;
  endpoint_available: boolean;
  inference_calls: number;
  average_latency_ms: number | null;
  gpu_hardware_mode: string;
  gpu_details: string;
  fallback_status: string;
  supported_backends: string[];
  trust_cue: string;
  last_error: string | null;
}

export interface DemoAddress {
  label: string;
  address: string;
  rsn: string;
  why: string;
}

export interface CityBuilding {
  rsn: string;
  address: string;
  ward: string | null;
  lat: number | null;
  lng: number | null;
  storeys: number | null;
  units: number | null;
  year_built: number | null;
  score: number | null;
  grade: string | null;
  risk_level: string | null;
  estimated_rent?: number | null;
  value_index?: number | null;
  value_band?: ValueBand | null;
}

export interface EdgeInvestigationResponse {
  app_name: string;
  tagline: string;
  resolved: AddressResolution;
  pio: PIO | null;
  risk: RiskReport | null;
  value: ValueForRisk | null;
  safety: NeighbourhoodSafety | null;
  operator: OperatorPortfolioReport;
  rights: RightsGroundingReport;
  advocacy: AdvocacyReport | null;
  draft_311: ComplaintDraft | null;
  audit_trail: AuditStep[];
  runtime: EdgeRuntimeStatus;
  evidence: EvidenceRef[];
  demo_addresses: DemoAddress[];
  meta: Record<string, unknown>;
}

export interface VisionResult {
  ok: boolean;
  model: string;
  extracted_text: string;
  explanation: string;
  rights_pointers: string[];
  language: string;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Streaming event union (one per SSE frame)
// ---------------------------------------------------------------------------
export interface PipelineStage {
  index: number;
  agent: string;
  label: string;
}

export interface PartialResult {
  resolved?: AddressResolution;
  pio?: PIO;
  risk?: RiskReport;
  value?: ValueForRisk;
  safety?: NeighbourhoodSafety;
  operator?: OperatorPortfolioReport;
  rights?: RightsGroundingReport;
  advocacy?: AdvocacyReport;
  draft_311?: ComplaintDraft;
  evidence?: EvidenceRef[];
  audit_trail?: AuditStep[];
}

export type EdgeEvent =
  | { type: "pipeline"; stages: PipelineStage[] }
  | { type: "agent_start"; index: number; agent: string; label: string; action: string }
  | { type: "agent_done"; index: number; step: AuditStep; patch: PartialResult }
  | { type: "runtime"; data: EdgeRuntimeStatus }
  | { type: "result"; data: EdgeInvestigationResponse }
  | { type: "error"; message: string };

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------
async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface InvestigateInput {
  address?: string;
  rsn?: string | null;
  profile?: UserProfile;
}

function body(input: InvestigateInput) {
  return JSON.stringify({
    address: input.address ?? "",
    rsn: input.rsn ?? null,
    profile: input.profile ?? { is_newcomer: true, priorities: ["safety", "pests", "heat"] },
    refresh_model: false,
  });
}

/**
 * Stream an investigation as Server-Sent Events. Calls `onEvent` for each agent
 * step as it happens — this is what drives the live trace. Resolves when the
 * stream completes; rejects on transport error or abort.
 */
export async function streamInvestigation(
  input: InvestigateInput,
  onEvent: (event: EdgeEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/edge/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body(input),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let boundary: number;
    // SSE frames are separated by a blank line.
    while ((boundary = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, boundary);
      buf = buf.slice(boundary + 2);
      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("\n");
      if (!data) continue; // comments / heartbeats
      try {
        onEvent(JSON.parse(data) as EdgeEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}

export const api = {
  health: () => get<{ runtime: EdgeRuntimeStatus; data: Record<string, number> }>("/api/health"),
  runtime: (probe = false) => get<EdgeRuntimeStatus>(`/api/edge/runtime?probe=${probe}`),
  demoAddresses: () => get<DemoAddress[]>("/api/edge/demo-addresses"),
  building: (rsn: string) => get<RiskReport>(`/api/buildings/${rsn}`),
  city: () => get<CityBuilding[]>("/api/city"),
  decisionMatrix: () => get<{ decision_matrix: Record<string, string>[] }>("/api/continuum/decision-matrix"),
  investigate: async (input: InvestigateInput): Promise<EdgeInvestigationResponse> => {
    const res = await fetch("/api/edge/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body(input),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
  analyzeImage: async (file: File, docHint: string, respondLanguage: string): Promise<VisionResult> => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_hint", docHint);
    fd.append("respond_language", respondLanguage);
    const res = await fetch("/api/vision", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
  streamInvestigation,
};
