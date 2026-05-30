// Shared evidence context — lets Cite chips and the SourceDrawer resolve an
// evidence id to its full record without prop-drilling.
import { createContext, useContext } from "react";
import type { EvidenceRef } from "../api";

export interface EvidenceCtxValue {
  map: Map<string, EvidenceRef>;
  open: (id: string) => void;
}

export const EvidenceCtx = createContext<EvidenceCtxValue>({ map: new Map(), open: () => {} });
export const useEvidence = () => useContext(EvidenceCtx);

/** Kind/colour inferred from an evidence id prefix or source string. */
export function evidenceKind(idOrSource: string): { kind: string; color: string } {
  const s = idOrSource.toLowerCase();
  if (s.startsWith("rights:") || s.includes("tenant_rights")) return { kind: "law", color: "var(--green)" };
  if (s.startsWith("massing:") || s.includes("massing")) return { kind: "dataset", color: "var(--c-tool)" };
  if (s.startsWith("rent:") || s.includes("rentsafeto")) return { kind: "dataset", color: "var(--c-tool)" };
  if (s.startsWith("pio:")) return { kind: "tool", color: "var(--c-tool)" };
  return { kind: "tool", color: "var(--dim)" };
}
