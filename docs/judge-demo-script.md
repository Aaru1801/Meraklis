# Meraklis — 3-minute judge demo script

> *"Your agents. Your models. Your edge."*
> Local-first, NVIDIA-powered civic AI for Toronto renters and housing advocates.

**Before you start:** `http://localhost:8088` is open on the **3D city landing**.
No internet is required for the demo.

---

## 0:00 – 0:30 · Frame it on the city

The landing is a **3D model of Toronto** — every RentSafeTO building, coloured by
risk, drifting in a slow orbit.

> "Meraklis is a local-first civic AI copilot for Toronto renters. This is every
> apartment building the City inspects, coloured by risk — green is low, red is
> severe. It all runs on a local NVIDIA model; nothing leaves the device."

Drag **Filter by risk → "Lowest risk (85+)"**: the skyline thins to only the
safest buildings.

> "A renter looking for somewhere safe filters to the green. But we're here for a
> high-risk one —" (click the **500 Dawes Rd** chip, or any red tower).

Point to the **NVIDIA Edge Runtime** panel:

- Model: `nvidia/nemotron-3-nano-30b` · Endpoint: `http://localhost:8000/v1`
- GPU mode (auto-detected via `nvidia-smi`, or "Mocked Spark target" off-Spark)
- Trust cue: **"No sensitive data leaves this device."**
- "If the model server is down, the deterministic fallback keeps the demo working."

## 0:25 – 1:00 · Run the live investigation

Click the **500 Dawes Rd** demo chip (or any address). Narrate the **live agent
trace** as each row lights up in real time:

> "Watch the agents act. Address Resolver matches the building in local SQLite.
> PIO Builder fuses sources with provenance and confidence. The **Risk Analyst
> runs deterministic scoring first** — no LLM. Then Operator, Rights, Advocate
> and the 311 drafter run, each logging its latency, confidence, tool calls and
> whether it used a model or a deterministic fallback."

## 1:00 – 1:40 · Evidence-backed risk

Scroll to **Building risk report**:

- City score, Grade, composite risk, last-inspection date — all from RentSafeTO.
- Red flags grouped by safety, pests, essential services, integrity — flagged
  for **newcomer** relevance — each with its raw evidence line.
- The trend chart shows the score **declining**.

> "No generated claim floats free. Every red flag ties back to a structured
> evidence ID — see the **Evidence ledger** on the right."

Scroll to **3D building massing**:

> "This is a *second* City dataset — the 3D Massing model. We extrude the
> building's real Lidar footprint to its measured height, and cross-check it: here
> RentSafeTO's storey count and the City's 3D model **agree** — or, for 1182 Queen
> St W, they **disagree**, which we flag. It's visualization plus an independent
> check — it never touches the risk score."

## 1:40 – 2:05 · Why it matters for a newcomer

Scroll to **Advocate guidance**:

> "For a newcomer renter, the system explains what's easy to miss before signing,
> and maps issues only to **verified Ontario / Toronto tenant-rights** facts —
> with the legal basis cited. It's legal *information*, not legal advice, and it
> pauses for human verification on high-stakes findings."

Point to the amber **human-verification** checkpoint.

## 2:05 – 2:35 · 311 draft + human approval gate

Scroll to **311 complaint draft**:

> "The draft uses **only cited evidence** and says plainly it's based on the last
> RentSafeTO inspection. It is **not submitted** to any city service. A human has
> to approve it first."

Tick the approval checkbox → **Mark reviewed locally** (don't imply submission).

## 2:35 – 3:00 · Auditability + Spark alignment

Scroll to **Audit trail**:

> "Every step is recorded — tool calls, model calls, latency, fallback status,
> confidence, citations, and human checkpoints. That's why this runs **offline**,
> and why it fits Spark: your agents, your models, your edge."

Finish back on the **NVIDIA Edge Runtime** panel.

---

### If a judge asks "what if the model server is up?"

Start NIM/vLLM/Ollama on `:8000`, re-run. The Advocate and 311 agents flip from
`deterministic` to `local model` (the trace badges change), inference calls and
average latency tick up in the runtime panel — and the deterministic fallback is
still one failed validation away, always armed.
