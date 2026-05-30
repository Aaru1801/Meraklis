# Meraklis

**A local-first, NVIDIA-powered civic AI for Toronto renters and housing advocates.**

> *Your agents. Your models. Your edge.*

`Local inference` · `NVIDIA Spark / GB10` · `City of Toronto open data` · `Offline-ready` · `No cloud AI`

Meraklis investigates any Toronto apartment building with a pipeline of
**8 cooperating agents**, grounded in the City's **RentSafeTO** inspection data.
It scores risk deterministically, grounds tenant rights in verified Ontario law,
and drafts a 311 complaint — streaming every model call, tool call, deterministic
fallback, confidence score and human-verification checkpoint as it works.

It is built for **NVIDIA DGX Spark / ASUS GX10 (GB10 Grace Blackwell)**: the LLM
runs **locally** behind an OpenAI-compatible endpoint (NVIDIA NIM, vLLM,
TensorRT-LLM, llama.cpp, Ollama). **No data leaves the device, and no cloud AI
provider is used.** If the model server is down, the system falls back to
fully-deterministic reports — so the demo always works, even offline.

**Demo at a glance** — a dark, green-tinted "operator console" (Public Sans /
IBM Plex Mono):

- **Landing — every building on a real Toronto map, two ways** (Map ⇄ 3D toggle):
  - **Map** (default) — a zoomable/pannable **dark slippy map with street names**
    (CARTO `dark_all` / OpenStreetMap) and **translucent risk-coloured markers** for
    each of ~3,500 buildings at its **real lat/long**.
  - **3D** — the same buildings as **translucent towers** (height by storeys) on a
    dark Toronto basemap, orbitable.
  - Shared across both: a **risk filter** (min City-score slider + "Lowest risk"
    presets) to surface the safest buildings, a **Most severe** shortcut to the
    worst building city-wide, address search, and click-any-building-to-investigate.
- **Workspace** — a three-pane command center: a **left sidebar** navigates the
  nine sections; the **center** shows the active section; a **collapsible right rail**
  holds the always-on NVIDIA Edge Runtime panel; the header carries the address,
  grade and edge/fallback status.
- **Investigation** (default) — a split **live agent trace**: a pipeline rail of
  the 8 agents (status + tool/model/fallback/confidence counts) beside a streaming
  log feed of `TOOL` / `MODEL` / `FALLBACK` / `RESULT` / `HUMAN GATE` rows with
  confidence bars and clickable citation chips.
- **Risk Report** — a radial risk-index gauge, grade, declining-score sparkline,
  building facts, and risk-driver bars by inspection-category group.
- **Intelligence** — address resolution + candidates, confidence/completeness, the
  real **3D building massing** (footprint extruded to Lidar height) with the
  storeys-vs-height cross-check, newcomer context, and the provenance ledger.
- **Operator**, **Rights** (legal citations), **Guidance**, **311 Draft** (human
  approval gate), **Audit Trail** — and a **provenance drawer** opens from any
  citation chip.

Clicking a citation opens a provenance record; the runtime panel has a *Simulate
model online* toggle to demo the served-model state vs. the deterministic fallback.

See [`docs/judge-demo-script.md`](docs/judge-demo-script.md) for the 3-minute walkthrough.

---

## Why it fits NVIDIA Spark

| Requirement | How Meraklis meets it |
|---|---|
| **City of Toronto open data** | Two City datasets: RentSafeTO Apartment Building Evaluations (3,649 buildings, 17,100 evaluations) for risk, plus the City **3D Massing** model (428k Lidar footprints) for building form + a height cross-check. Both cached locally. |
| **Agentic application** | An 8-agent investigation pipeline that streams its reasoning live. |
| **Local inference on NVIDIA HW** | OpenAI-compatible adapter → NIM / vLLM / TensorRT-LLM / llama.cpp / Ollama on the GPU. |
| **Open / Nemotron models** | Defaults to `nvidia/nemotron-3-nano-30b`; any local OpenAI-compatible model works. |
| **No cloud-only AI** | Zero OpenAI / Anthropic / Gemini. The model endpoint is `localhost` by default. |
| **Works offline** | Deterministic risk engine, rights grounding and 311 drafting need no network and no model. |
| **DGX Spark / GX10 target** | `nvidia-smi` GPU detection; "Mocked Spark target" label off-Spark; runtime panel proves local-first posture. |

---

## The 8-agent pipeline

Each agent records a structured audit step (tool calls, model calls, latency,
confidence, citations, fallback flag, human checkpoint). The pipeline streams
over Server-Sent Events so the UI shows the system *thinking and acting*.

| # | Agent | What it does | LLM? |
|---|-------|--------------|------|
| 1 | **Address Resolver** | Normalizes input, fuzzy-matches a RentSafeTO building in local SQLite. | No |
| 2 | **PIO Builder** | Fuses sources (RentSafeTO + City 3D Massing footprint/height) into a Property Intelligence Object with per-source provenance, confidence, completeness, an independent height cross-check, and surfaced uncertainties. | No |
| 3 | **Risk Analyst** | Deterministic risk engine: grade, composite risk, red flags (by group + newcomer relevance), trend, strengths. | No |
| 4 | **Operator / Portfolio** | Identifies the operator *if data allows* — honestly reports it is absent from the local schema, and instead provides factual ward-peer context. | No |
| 5 | **Rights Grounding** | Maps issues to **verified** Ontario/Toronto tenant-rights facts (RTA 2006, City bylaws, LTB). Never invents law. | No |
| 6 | **Advocate** | Plain-language guidance tailored to the renter profile, grounded strictly in cited evidence. | **Yes** (det. fallback) |
| 7 | **311 Draft** | Drafts a complaint summary from cited evidence only; never submitted. | **Yes** (det. fallback) |
| 8 | **Audit** | Records every step, fallback, confidence and human checkpoint. | No |

**Every generated claim ties back to a structured evidence ID.** No hallucinated
citations: the model's output is validated, and any cited ID not present in the
evidence ledger causes the agent to drop to its deterministic output.

---

## Architecture

```
                         ┌──────────────────────────────────────────────┐
   City of Toronto       │              Meraklis (this device)      │
   Open Data (CKAN) ──▶  │                                                │
   RentSafeTO            │   data/rentsafeto.sqlite3   (local cache)      │
   (ingest, one-time)    │            │                                   │
                         │            ▼                                   │
                         │   Deterministic core  (pure Python, no LLM)    │
                         │   • risk engine • red-flag taxonomy            │
                         │   • tenant-rights KB • PIO + provenance        │
                         │            │                                   │
                         │            ▼                                   │
                         │   8-agent pipeline ──SSE──▶ React command center│
                         │            │                                   │
                         │            ▼ (optional)                        │
                         │   Local model adapter (OpenAI-compatible)      │
                         │            │                                   │
                         └────────────┼───────────────────────────────────┘
                                      ▼
                         NVIDIA NIM / vLLM / TensorRT-LLM / llama.cpp / Ollama
                         on GB10  ·  http://localhost:8000/v1  ·  on-device
```

**Design principles**

- **Deterministic-first.** The City's audited 0–100 score anchors every verdict;
  the LLM only *explains* — it never invents the underlying facts.
- **Evidence grounding.** Claims carry evidence IDs; unverifiable model output is
  discarded in favour of the deterministic fallback.
- **Human-in-the-loop.** High-stakes / low-confidence findings pause for review;
  the 311 draft has a hard human approval gate and is never submitted.
- **Provenance & uncertainty.** Sources report status + confidence; obstructed
  inspection areas and stale data are surfaced, never hidden.

---

## Quick start (local machine)

**Prerequisites:** Python ≥ 3.11 and Node ≥ 18. The RentSafeTO SQLite cache is
already included — no internet needed.

```bash
# 1. Backend deps (a venv is recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the frontend (the API serves it)
cd frontend && npm install && npm run build && cd ..

# 3. Run — the app binds :8088; the model server (if any) owns :8000
uvicorn --app-dir backend openhouse.api.main:app --host 127.0.0.1 --port 8088
```

Open **http://localhost:8088** and click a demo address. That's the whole demo —
it works with **no model server running** (deterministic fallback).

<details>
<summary><b>Dev mode (hot-reload frontend)</b></summary>

```bash
# terminal 1 — backend with reload
uvicorn --app-dir backend openhouse.api.main:app --port 8088 --reload

# terminal 2 — Vite dev server (proxies /api → :8088)
cd frontend && npm run dev   # http://localhost:5173
```
</details>

> **Note on `pip install -e backend`:** an editable install also works, but on some
> macOS + Python 3.13 setups the editable `.pth` can be flagged hidden and skipped.
> The `--app-dir backend` form above sidesteps that entirely and is the recommended
> way to run.

---

## Running on DGX Spark / ASUS GX10 (GB10 Grace Blackwell)

The app is identical; you simply point it at a **local** model server on the GPU.
Pick one backend, then set `.env` and run.

```bash
cp .env.example .env        # MODEL_BASE_URL defaults to http://localhost:8000/v1
```

**Option A — NVIDIA NIM (recommended on Spark)**
```bash
docker run --rm --gpus all -p 8000:8000 \
  nvcr.io/nim/nvidia/nemotron-3-nano-30b:latest        # serves /v1 on :8000
```

**Option B — vLLM on the GPU**
```bash
pip install vllm
vllm serve nvidia/nemotron-3-nano-30b --port 8000      # OpenAI-compatible /v1
```

**Option C — TensorRT-LLM** — launch the OpenAI-compatible server on `:8000`.

**Option D — llama.cpp (CUDA)**
```bash
./llama-server -m model.gguf --port 8000 -ngl 99       # exposes /v1
```

**Option E — Ollama** (serving a local/open model)
```bash
ollama serve                                            # /v1 on :11434
# then set MODEL_BASE_URL=http://localhost:11434/v1 and MODEL_NAME=<your model>
```

Then run the app on its own port and open it:
```bash
uvicorn --app-dir backend openhouse.api.main:app --host 0.0.0.0 --port 8088
```

The **NVIDIA Edge Runtime** panel auto-detects the GPU via `nvidia-smi` and shows
live inference calls and average latency. When the model is reachable, the
Advocate and 311 agents switch from `deterministic` to `local model` (visible in
the trace and audit badges). The deterministic fallback stays armed throughout.

---

## Offline & deterministic-fallback guarantee

Run the included smoke test — it proves the **entire pipeline works with no model
server**, and that every citation resolves to real evidence:

```bash
PYTHONPATH=backend python -m openhouse.scripts.smoke_test
```

```
✓ 8 audited steps · advocacy is deterministic fallback (no model server)
✓ all step citations resolve to evidence · 311 cites only real evidence
✓ pipeline streams: pipeline → 8×agent_done → runtime → result
✓ All checks passed — Meraklis runs fully offline.
```

---

## Data

- **Source:** City of Toronto Open Data — *Apartment Building Evaluation*
  (RentSafeTO). Buildings of 3+ storeys / 10+ units, scored 0–100 across ~50
  inspection categories. https://open.toronto.ca/dataset/apartment-building-evaluation/
- **Cache:** `data/rentsafeto.sqlite3` (committed; 3,649 buildings).
- **Refresh from the live City API** (optional, needs internet):
  ```bash
  PYTHONPATH=backend python -m openhouse.scripts.ingest            # full dataset
  PYTHONPATH=backend python -m openhouse.scripts.ingest --limit 500 # quick sample
  ```

Meraklis **never invents inspection data** — the LLM only explains the
deterministic facts already present in the dataset.

### Second dataset — City of Toronto 3D Massing (building form + height)

A second City open dataset (**[3D Massing](https://open.toronto.ca/dataset/3d-massing/)**:
~428k Lidar-derived building footprints with heights) adds the building's real 3D
form and an **independent height cross-check** (RentSafeTO storeys vs. measured
roof height). It is **enrichment / visualization only — it never affects the risk
score.** The dataset ships as large zipped shapefiles (no query API), so the heavy
work happens once at ingest; the runtime reads only a tiny committed cache
(`data/massing_cache.json`) and stays offline + dependency-free.

```bash
# one-time: download a 3DMassingShapefile_<year>_WGS84.zip from the link above,
# unzip it (e.g. into data/_massing_src/), then:
pip install pyshp      # pure-Python shapefile reader (ingest-only dependency)
PYTHONPATH=backend python -m openhouse.scripts.ingest_massing \
    --shapefile data/_massing_src/3DMassingShapefile_2025_WGS84
# caches the demo buildings; add --rsn <RSN> (repeatable) for more.
```

The committed `data/massing_cache.json` already covers the three demo buildings,
so this step is optional unless you add new addresses.

### City basemap (3D landing ground)

The 3D city landing renders the buildings on a **dark Toronto street map** (Lake
Ontario and all). It's a committed image (`frontend/public/toronto-basemap.jpg`)
stitched from CARTO `dark_nolabels` / OpenStreetMap tiles over the building
extent — regenerate it (optional, needs internet + `pip install Pillow`) with:

```bash
PYTHONPATH=backend python -m openhouse.scripts.ingest_basemap
```

Map © OpenStreetMap contributors © CARTO; building positions are the City's real
RentSafeTO coordinates.

---

## Project layout

```
openhouse-edge/
├── backend/openhouse/
│   ├── data/            # models, RentSafeTO client, SQLite store, address
│   │   │                #   normalizer, rent model, PIO + source adapters
│   │   └── categories.py# red-flag taxonomy (safety/pests/essential/integrity/…)
│   ├── risk/            # deterministic risk engine + report schema
│   ├── knowledge/       # verified Ontario/Toronto tenant-rights base
│   ├── agents/
│   │   ├── edge.py          # the 8-agent streaming pipeline
│   │   ├── edge_runtime.py  # local OpenAI-compatible model adapter + GPU probe
│   │   ├── service.py       # LLM-free data service
│   │   ├── continuum_modes.py # human-in-the-loop decision matrix
│   │   └── schemas.py       # UserProfile, AdvocacyReport (typed contracts)
│   └── api/main.py      # FastAPI: SSE stream + batch + data endpoints, SPA
├── frontend/src/        # React + TypeScript + lucide-react + three.js (Meraklis design system)
│   ├── index.css        # Meraklis design tokens (green-tinted console, Public Sans)
│   ├── App.tsx          # search ↔ workspace; SSE wiring; evidence context
│   ├── lib/             # icons, ui primitives, agent/nav metadata, evidence ctx
│   └── components/      # CityLanding + CityModel (3D Toronto, three.js), Workspace,
│                        #   Trace, RuntimePanel, sections, Massing3D, SourceDrawer
├── data/                # rentsafeto.sqlite3 + massing_cache.json + demo_seeds.json
├── docs/                # 3-minute judge demo script
├── .env.example
└── requirements.txt
```

---

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Runtime status + dataset stats + offline flag. |
| `GET/POST` | `/api/edge/stream` | **SSE** — streams one event per agent (the live trace). |
| `POST` | `/api/edge/investigate` | One-shot batch investigation (same result, no stream). |
| `GET` | `/api/edge/runtime?probe=true` | NVIDIA Edge Runtime status (probes the model endpoint). |
| `GET` | `/api/buildings/{rsn}` · `/pio` · `/rights` | Deterministic report / PIO / rights for a building. |
| `GET` | `/api/continuum/decision-matrix` | The human-in-the-loop decision matrix. |

Interactive API docs at `/docs` when the server is running.

---

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `MODEL_BASE_URL` | `http://localhost:8000/v1` | Local OpenAI-compatible endpoint. |
| `MODEL_NAME` | `nvidia/nemotron-3-nano-30b` | Any local/open model. |
| `MODEL_API_KEY` | *(empty)* | Usually unset for local servers. |
| `OPENHOUSE_API_PORT` | `8088` | App/API port (kept off `:8000`). |
| `OPENHOUSE_DB_PATH` | *(bundled)* | Override the SQLite cache path. |
| `OPENHOUSE_MASSING_CACHE` | *(bundled)* | Override the 3D Massing cache path. |
| `EDGE_STREAM_DELAY_MS` | `420` | Per-step display pacing for the live trace (0 = instant). |

---

## Safety & scope

- **Legal information, not legal advice.** Tenant-rights content cites primary
  sources and is framed for verification with a clinic / hotline / paralegal.
- **Never submits.** The 311 draft is prepared for the user to review and copy;
  it is never sent to any real city service.
- **No hallucinated data.** Risk and rights are deterministic; model output is
  validated against evidence IDs and discarded if it can't be grounded.
- **On-device.** With a local `MODEL_BASE_URL`, no sensitive data leaves the
  machine and no cloud AI is involved.

## License

MIT — see [LICENSE](LICENSE). RentSafeTO data © City of Toronto, used under the
Open Government Licence – Toronto.
