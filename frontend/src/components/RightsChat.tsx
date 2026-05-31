import { useRef, useState } from "react";
import { api, type RightsResponse } from "../api";
import { Icon } from "../lib/icons";
import { Logo } from "../lib/ui";

type Msg = { role: "user" | "assistant"; text: string; res?: RightsResponse };

const STARTERS = [
  "My heat has been off for days — what can I do?",
  "Can my landlord enter my unit without notice?",
  "Who is responsible for getting rid of cockroaches?",
  "My landlord won't fix a leak — what are my options?",
];

// Grounded tenant-rights chat: every answer comes only from Meraklis's verified
// Ontario/Toronto rights knowledge base (POST /api/rights/ask), with the law cited.
export function RightsChat({ onHome }: { onHome: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || loading) return;
    setQ("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await api.askRights(text);
      setMsgs((m) => [...m, { role: "assistant", text: res.ok ? res.answer : (res.error || "Something went wrong."), res }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", text: "Couldn't reach the rights assistant — please try again." }]);
    } finally {
      setLoading(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
    }
  };

  return (
    <div className="col" style={{ height: "100%", background: "var(--bg)" }}>
      <header className="row" style={{ justifyContent: "space-between", padding: "12px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface)", flexShrink: 0 }}>
        <button onClick={onHome} style={{ background: "none" }}><Logo size={22} /></button>
        <div className="row gap8"><Icon name="scale" size={15} color="var(--green)" /><span style={{ fontSize: 13, fontWeight: 700 }}>Know your rights</span></div>
        <button className="btn btn-ghost btn-sm" onClick={onHome}><Icon name="search" size={13} /> Back</button>
      </header>

      <div className="grow" style={{ overflowY: "auto", padding: 22 }}>
        <div className="col" style={{ gap: 16, maxWidth: 760, margin: "0 auto" }}>
          {msgs.length === 0 && (
            <div className="col" style={{ gap: 14, alignItems: "center", textAlign: "center", padding: "44px 0" }}>
              <span style={{ width: 44, height: 44, borderRadius: 12, background: "var(--green-bg)", display: "grid", placeItems: "center", color: "var(--green)" }}><Icon name="scale" size={22} /></span>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>Ask about your tenant rights</div>
                <p className="dim" style={{ fontSize: 13, marginTop: 4, maxWidth: 470 }}>Answers come only from Meraklis's verified Ontario / Toronto tenant-rights knowledge — with the law cited. General information, not legal advice.</p>
              </div>
              <div className="row gap8 wrap" style={{ justifyContent: "center", maxWidth: 580 }}>
                {STARTERS.map((s) => (
                  <button key={s} onClick={() => ask(s)} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-2)", background: "var(--surface)", fontSize: 12.5, color: "var(--dim)", textAlign: "left", maxWidth: 270 }}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {msgs.map((m, i) => m.role === "user" ? (
            <div key={i} className="row" style={{ justifyContent: "flex-end" }}>
              <div style={{ background: "var(--green)", color: "var(--green-ink)", padding: "10px 14px", borderRadius: "12px 12px 2px 12px", fontSize: 13.5, lineHeight: 1.45, maxWidth: "80%" }}>{m.text}</div>
            </div>
          ) : (
            <div key={i} className="col" style={{ alignItems: "flex-start", maxWidth: "90%" }}>
              <div className="panel" style={{ padding: 14, background: "var(--surface)" }}>
                <p style={{ fontSize: 13.5, lineHeight: 1.55 }}>{m.text}</p>
                {m.res?.out_of_scope && (
                  <div className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>This is outside the rights knowledge base — the resources below can help.</div>
                )}
                {m.res?.citations?.length ? (
                  <div style={{ marginTop: 11 }}>
                    <div className="eyebrow" style={{ marginBottom: 6 }}>Based on</div>
                    {m.res.citations.map((c) => (
                      <div key={c.title} className="row gap8" style={{ alignItems: "flex-start", marginBottom: 6 }}>
                        <Icon name="scale" size={12} color="var(--green)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <div><div style={{ fontSize: 12.5, fontWeight: 600 }}>{c.title}</div><div className="faint" style={{ fontSize: 11, lineHeight: 1.35 }}>{c.legal_basis} · {c.source}</div></div>
                      </div>
                    ))}
                  </div>
                ) : null}
                {m.res?.resources?.length ? (
                  <div style={{ marginTop: 10 }}>
                    <div className="eyebrow" style={{ marginBottom: 6 }}>Where to get help</div>
                    {m.res.resources.map((r) => (
                      <a key={r.name} href={r.url} target="_blank" rel="noreferrer" className="row gap8" style={{ alignItems: "flex-start", marginBottom: 5, color: "var(--text)" }}>
                        <Icon name="link" size={12} color="var(--green)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 12 }}><b>{r.name}</b> — {r.contact}</span>
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}

          {loading && <div className="row gap6 faint mono" style={{ fontSize: 12 }}><Icon name="loader" size={13} className="spin" /> consulting the rights knowledge…</div>}
          <div ref={endRef} />
        </div>
      </div>

      <div style={{ flexShrink: 0, borderTop: "1px solid var(--border)", background: "var(--surface)", padding: "12px 20px" }}>
        <div className="row gap10" style={{ maxWidth: 760, margin: "0 auto" }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about heat, repairs, pests, entry, locks…"
            onKeyDown={(e) => { if (e.key === "Enter") ask(q); }}
            style={{ flex: 1, padding: "11px 14px", borderRadius: 8, border: "1px solid var(--border-2)", background: "var(--bg)", color: "var(--text)", fontSize: 14, outline: "none" }} />
          <button className="btn btn-pri" disabled={loading || !q.trim()} onClick={() => ask(q)}><Icon name="arrow-right" size={15} /> Ask</button>
        </div>
        <p className="faint" style={{ fontSize: 10, textAlign: "center", marginTop: 8, maxWidth: 760, marginInline: "auto" }}>
          General information from Ontario / Toronto tenant-rights sources, not legal advice. Answered locally on your NVIDIA edge.
        </p>
      </div>
    </div>
  );
}
