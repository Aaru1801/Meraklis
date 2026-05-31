import { useRef, useState } from "react";
import { api, type UserProfile, type VisionResult } from "../api";
import { Icon } from "../lib/icons";
import { Card, Pill } from "../lib/ui";

const DOC_HINTS = [
  { v: "", label: "Auto-detect" },
  { v: "lease", label: "Lease / agreement" },
  { v: "N4", label: "N4 (rent arrears)" },
  { v: "N12", label: "N12 (landlord's own use)" },
  { v: "notice", label: "Other notice / letter" },
  { v: "photo", label: "Photo of a problem" },
];

// Upload a tenant document (lease, N4/N12, or a photo) → local NVIDIA vision model
// (Nemotron Parse via vLLM) extracts the text, then the local LLM explains it.
export function DocAnalyzer({ profile, onClose }: { profile: UserProfile; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [hint, setHint] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VisionResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const onFile = async (file: File) => {
    setErr(null);
    setResult(null);
    setPreview((p) => { if (p) URL.revokeObjectURL(p); return URL.createObjectURL(file); });
    setLoading(true);
    try {
      const r = await api.analyzeImage(file, hint, profile.respond_language ?? "English");
      if (r.ok) setResult(r);
      else setErr(r.error || "Could not read the document.");
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card style={{ position: "absolute", top: 70, right: 22, width: 360, maxHeight: "80vh", overflowY: "auto", zIndex: 7, background: "color-mix(in oklch, var(--surface) 95%, transparent)", backdropFilter: "blur(10px)" }}>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <div className="row gap8"><Icon name="image" size={15} color="var(--green)" /><span style={{ fontSize: 13, fontWeight: 700 }}>Read a document</span></div>
        <button onClick={onClose} title="Close"><Icon name="x" size={14} color="var(--faint)" /></button>
      </div>
      <div className="faint" style={{ fontSize: 11, marginBottom: 11, lineHeight: 1.45 }}>
        Upload a lease, an N4/N12 notice, or a photo of a problem. Read locally on this device — nothing leaves the GX10.
      </div>

      <select value={hint} onChange={(e) => setHint(e.target.value)}
        style={{ width: "100%", padding: "7px 9px", borderRadius: 7, border: "1px solid var(--border-2)", background: "var(--surface-2)", color: "var(--text)", fontSize: 12.5, marginBottom: 9 }}>
        {DOC_HINTS.map((d) => <option key={d.v} value={d.v}>{d.label}</option>)}
      </select>

      <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
      <button className="btn btn-pri btn-sm" style={{ width: "100%", justifyContent: "center" }} disabled={loading}
        onClick={() => fileRef.current?.click()}>
        <Icon name={loading ? "loader" : "image"} size={14} className={loading ? "spin" : ""} /> {loading ? "Reading…" : "Choose an image"}
      </button>

      {preview && <img src={preview} alt="upload preview" style={{ width: "100%", marginTop: 10, borderRadius: 8, border: "1px solid var(--border)" }} />}

      <div className="row gap6" style={{ marginTop: 9 }}>
        <Icon name="lock" size={11} color="var(--green)" />
        <span className="faint" style={{ fontSize: 10 }}>Local · no egress</span>
      </div>

      {err && (
        <div style={{ marginTop: 10, padding: "9px 11px", borderRadius: 8, border: "1px solid color-mix(in oklch, var(--r-high) 35%, transparent)", background: "var(--r-high-bg)", fontSize: 11.5, color: "var(--r-high)" }}>{err}</div>
      )}

      {result && (
        <div style={{ marginTop: 12 }}>
          <Pill color="var(--green)"><Icon name="cpu" size={10} /> {result.model}</Pill>
          {result.explanation && (
            <div style={{ marginTop: 10 }}>
              <div className="eyebrow" style={{ marginBottom: 4 }}>What this means</div>
              <div style={{ fontSize: 12.5, lineHeight: 1.5 }}>{result.explanation}</div>
            </div>
          )}
          {result.rights_pointers?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div className="eyebrow" style={{ marginBottom: 4 }}>Your rights</div>
              {result.rights_pointers.map((r, i) => (
                <div key={i} className="row gap6" style={{ alignItems: "flex-start", marginBottom: 5 }}>
                  <Icon name="check-circle" size={12} color="var(--green)" style={{ marginTop: 2, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, lineHeight: 1.45 }}>{r}</span>
                </div>
              ))}
            </div>
          )}
          {result.extracted_text && (
            <details style={{ marginTop: 10 }}>
              <summary className="eyebrow" style={{ cursor: "pointer" }}>Extracted text</summary>
              <pre className="mono" style={{ fontSize: 10.5, whiteSpace: "pre-wrap", marginTop: 6, padding: 9, borderRadius: 7, background: "var(--surface-2)", border: "1px solid var(--border)", maxHeight: 220, overflowY: "auto" }}>{result.extracted_text}</pre>
            </details>
          )}
          <div className="faint" style={{ fontSize: 10, marginTop: 10, lineHeight: 1.4 }}>
            General information, not legal advice. Verify with a legal clinic or the LTB.
          </div>
        </div>
      )}
    </Card>
  );
}
