// Meraklis — agent + nav metadata, keyed by the backend agent names.
export interface AgentMeta { icon: string; short: string; blurb: string }

export const AGENTS: Record<string, AgentMeta> = {
  "Address Resolver Agent": { icon: "map-pin", short: "resolver", blurb: "Normalize input and match a Toronto building" },
  "PIO Builder Agent": { icon: "boxes", short: "pio", blurb: "Assemble the Property Intelligence Object" },
  "Risk Analyst Agent": { icon: "gauge", short: "risk", blurb: "Run the deterministic risk engine" },
  "Operator / Portfolio Agent": { icon: "building-2", short: "operator", blurb: "Operator & portfolio patterns" },
  "Rights Grounding Agent": { icon: "scale", short: "rights", blurb: "Map issues to verified tenant rights" },
  "Advocate Agent": { icon: "megaphone", short: "advocate", blurb: "Plain-language renter guidance" },
  "311 Draft Agent": { icon: "file-text", short: "draft", blurb: "Draft the 311 complaint" },
  "Audit Agent": { icon: "list-checks", short: "audit", blurb: "Seal the audit trail" },
};

export function agentMeta(name: string): AgentMeta {
  return AGENTS[name] ?? { icon: "circle", short: name.slice(0, 8), blurb: "" };
}

// Workspace navigation (section id → label/icon). `live` marks the trace.
export interface NavItem { id: string; label: string; icon: string; live?: boolean }
export const NAV: NavItem[] = [
  { id: "trace", label: "Investigation", icon: "activity", live: true },
  { id: "report", label: "Risk Report", icon: "gauge" },
  { id: "value", label: "Value-for-Risk", icon: "circle-dollar-sign" },
  { id: "flags", label: "Red Flags", icon: "flag" },
  { id: "pio", label: "Intelligence", icon: "boxes" },
  { id: "operator", label: "Operator", icon: "building-2" },
  { id: "rights", label: "Rights", icon: "scale" },
  { id: "advocate", label: "Guidance", icon: "megaphone" },
  { id: "draft", label: "311 Draft", icon: "file-text" },
  { id: "audit", label: "Audit Trail", icon: "list-checks" },
];
