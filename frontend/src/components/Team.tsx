// Team section — built to the "Agentic" design system (typeui.sh): Playfair Display
// display type, #FF5701 primary, #F6F6F1 subtle, #111827 text, 8pt spacing, WCAG 2.2 AA.
// Fully self-contained (scoped `.tm-` styles + its own fonts) so it never collides
// with the Meraklis theme. Preview at /#team.

interface Member {
  name: string;
  role: string;   // role-category shown in the pill badge
  title: string;  // single-line job title
  color: string;  // avatar + badge accent (white-on-color ≥ 3:1 for the large initial)
}

const TEAM: Member[] = [
  { name: "Aarav", role: "Founder", title: "Product & AI Lead", color: "#FF5701" },
  { name: "David", role: "Story", title: "Product Storyteller", color: "#BE123C" },
  { name: "Yixiao", role: "Engineering", title: "Full-Stack Engineer", color: "#2563EB" },
  { name: "Randeep", role: "Design", title: "UI / UX Designer", color: "#7C3AED" },
  { name: "Adarsha", role: "Systems", title: "Scoring & Systems", color: "#15803D" },
  { name: "Keshav", role: "Data", title: "Data & Safety Modeling", color: "#0E7490" },
];

const ArrowRight = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);
const MailIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="m3 7 9 6 9-6" />
  </svg>
);
const Dot = ({ color }: { color: string }) => (
  <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true"><circle cx="4" cy="4" r="4" fill={color} /></svg>
);

const STYLE = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
.tm-root{ --tm-primary:#FF5701; --tm-surface:#FFFFFF; --tm-subtle:#F6F6F1; --tm-text:#111827; --tm-muted:#5B616E; --tm-border:#D9DBE0;
  min-height:100%; background:var(--tm-surface); color:var(--tm-text);
  font-family:'JetBrains Mono',ui-monospace,monospace; -webkit-font-smoothing:antialiased; }
.tm-container{ max-width:1200px; margin:0 auto; padding:72px 40px; }
.tm-header{ display:flex; justify-content:space-between; align-items:baseline; gap:24px 32px; flex-wrap:wrap; }
.tm-head-left{ display:flex; flex-direction:column; gap:12px; max-width:60ch; }
.tm-h1{ font-family:'Playfair Display',Georgia,serif; font-weight:800; font-size:40px; line-height:1.08; letter-spacing:-.01em; margin:0; }
.tm-lead{ font-size:16px; line-height:1.65; color:var(--tm-muted); max-width:56ch; margin:0; }
.tm-btn{ display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; padding:11px 20px;
  border:1.5px solid var(--tm-text); border-radius:999px; background:transparent; color:var(--tm-text);
  font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:500; line-height:1; cursor:pointer; white-space:nowrap;
  transition:border-color .18s ease, background-color .18s ease, color .18s ease, transform .12s ease; }
.tm-btn:hover{ border-color:var(--tm-primary); background:#FFF4EF; color:var(--tm-text); }
.tm-btn:focus-visible{ outline:3px solid color-mix(in srgb, var(--tm-primary) 45%, transparent); outline-offset:2px; }
.tm-btn:active{ transform:translateY(1px); }
.tm-board{ margin-top:48px; background:transparent; border:none; box-shadow:none; }
.tm-grid{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:40px 32px; list-style:none; margin:0; padding:0; }
.tm-block{ display:flex; flex-direction:column; align-items:center; text-align:center; gap:12px; padding:8px; }
.tm-avatar{ width:96px; height:96px; border-radius:999px; display:grid; place-items:center;
  font-family:'Playfair Display',Georgia,serif; font-weight:700; font-size:34px; color:#fff; user-select:none; }
.tm-badge{ display:inline-flex; align-items:center; gap:6px; padding:4px 11px; border-radius:999px;
  background:var(--tm-subtle); color:var(--tm-text); font-size:12px; font-weight:500; line-height:1; }
.tm-name{ font-family:'Playfair Display',Georgia,serif; font-weight:600; font-size:18px; line-height:1.2; }
.tm-title{ font-size:14px; font-weight:400; color:var(--tm-muted); line-height:1.3; }
.tm-contact{ margin-top:4px; padding:10px 16px; font-size:13px; }
@media (max-width:1024px){ .tm-grid{ grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:640px){ .tm-grid{ grid-template-columns:1fr; } .tm-container{ padding:48px 22px; } .tm-h1{ font-size:32px; } }
@media (prefers-reduced-motion:reduce){ .tm-btn{ transition:none; } .tm-btn:active{ transform:none; } }
`;

export function Team() {
  return (
    <section className="tm-root" aria-labelledby="tm-heading">
      <style>{STYLE}</style>
      <div className="tm-container">
        <header className="tm-header">
          <div className="tm-head-left">
            <h1 id="tm-heading" className="tm-h1">Meet the Edge Cases</h1>
            <p className="tm-lead">
              The team behind Meraklis — a local-first, NVIDIA-powered housing copilot that shows
              Toronto renters a building's real credibility, not just its listing.
            </p>
          </div>
          <button type="button" className="tm-btn">Join the team <ArrowRight /></button>
        </header>

        <div className="tm-board">
          <ul className="tm-grid" role="list">
            {TEAM.map((m) => (
              <li key={m.name} className="tm-block">
                <div className="tm-avatar" style={{ background: m.color }} aria-hidden="true">{m.name[0]}</div>
                <span className="tm-badge"><Dot color={m.color} /> {m.role}</span>
                <span className="tm-name">{m.name}</span>
                <span className="tm-title">{m.title}</span>
                <button type="button" className="tm-btn tm-contact" aria-label={`Contact ${m.name}`}>
                  <MailIcon /> Contact me
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
