"""Meraklis FastAPI application.

A thin, well-typed HTTP surface over the data service, deterministic risk engine,
verified tenant-rights base and the local-first Spark agent pipeline.

The signature route is ``GET/POST /api/edge/stream`` — a Server-Sent Events
stream that emits one event per agent as the investigation runs, so the UI can
show the system *thinking and acting* live. ``/api/edge/investigate`` returns the
same result in one shot for tests and non-streaming clients. Everything works
offline: if the local model endpoint is unavailable, agents fall back to
deterministic output and say so in the audit trail.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..agents.continuum_modes import DECISION_MATRIX, pipeline_modes
from ..agents.edge import (
    DEMO_ADDRESSES,
    NEMOTRON_LANGS,
    PIPELINE_STAGES,
    EdgeInvestigationRequest,
    get_edge_investigator,
)
from ..agents.edge_runtime import SUPPORTED_BACKENDS, get_model_adapter
from ..agents.schemas import UserProfile
from ..agents.service import get_service
from ..data.adapters.base import AddressQuery
from ..data.pio import get_pio_builder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("openhouse.api")

app = FastAPI(
    title="Meraklis API",
    version="1.0.0",
    description=(
        "A local-first NVIDIA Spark civic AI for Toronto renters. Real RentSafeTO "
        "open data, deterministic risk scoring, verified Ontario tenant-rights "
        "grounding, and OpenAI-compatible local model agents with offline fallback."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_svc = get_service()
_edge = get_edge_investigator()


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------
def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _sse(event: dict[str, Any]) -> str:
    """Encode one event as an SSE ``data:`` frame (pydantic-aware)."""
    return f"data: {json.dumps(event, default=_to_jsonable)}\n\n"


# ---------------------------------------------------------------------------
# Health & data
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict:
    runtime = await get_model_adapter().status(probe=False)
    return {
        "status": "ok",
        "runtime": runtime.model_dump(mode="json"),
        "data": _svc.city_stats(),
        "offline_ready": True,
        "supported_backends": list(SUPPORTED_BACKENDS),
    }


@app.get("/api/stats")
def stats() -> dict:
    return _svc.city_stats()


@app.get("/api/wards")
def wards() -> list[dict]:
    return _svc.store.list_wards()


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(15, ge=1, le=50)) -> list[dict]:
    return [b.model_dump(mode="json") for b in _svc.search(q, limit)]


@app.get("/api/city")
def city(limit: int = Query(6000, ge=1, le=8000)) -> list[dict]:
    """Every geolocated RentSafeTO building (lat/lng, storeys, City score, grade,
    risk band) — the data layer for the whole-city 3D model."""
    return [
        {
            "rsn": b.rsn, "address": b.address, "ward": b.ward_name,
            "lat": b.latitude, "lng": b.longitude, "storeys": b.storeys,
            "units": b.units, "year_built": b.year_built,
            "score": b.score, "grade": b.grade, "risk_level": b.risk_level,
            "estimated_rent": b.estimated_rent,
            "value_index": b.value_index, "value_band": b.value_band,
        }
        for b in _svc.map_points(limit=limit)
    ]


@app.get("/api/buildings/{rsn}")
def building(rsn: str) -> dict:
    report = _svc.report(rsn)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No building found for RSN {rsn}")
    return report.model_dump(mode="json")


@app.get("/api/buildings/{rsn}/rights")
def building_rights(rsn: str) -> dict:
    rights = _svc.rights(rsn)
    if not rights:
        raise HTTPException(status_code=404, detail=f"No building found for RSN {rsn}")
    return rights


@app.get("/api/buildings/{rsn}/comparison")
def building_comparison(rsn: str) -> dict:
    return _svc.comparison(rsn)


@app.get("/api/buildings/{rsn}/pio")
async def building_pio(rsn: str) -> dict:
    """The canonical Property Intelligence Object — sources fused, with per-source
    provenance, confidence and surfaced uncertainties."""
    pio = await get_pio_builder().build_async(AddressQuery.make(rsn=rsn))
    if not pio.resolved:
        raise HTTPException(status_code=404, detail=f"No building found for RSN {rsn}")
    return pio.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Agency Continuum (human-in-the-loop transparency)
# ---------------------------------------------------------------------------
@app.get("/api/continuum/decision-matrix")
def continuum_matrix() -> dict:
    return {
        "decision_matrix": DECISION_MATRIX,
        "pipeline_modes": [m.model_dump(mode="json") for m in pipeline_modes()],
        "modes": {
            "autonomous": "The agent acts without asking (data fetch, cleaning, scoring).",
            "automated_recommendation": "The agent recommends; the user reviews.",
            "human_verification": "The agent pauses and asks the user to validate before acting.",
        },
    }


# ---------------------------------------------------------------------------
# NVIDIA Edge runtime
# ---------------------------------------------------------------------------
@app.get("/api/edge/runtime")
async def edge_runtime(probe: bool = False) -> dict:
    return (await get_model_adapter().status(probe=probe)).model_dump(mode="json")


@app.get("/api/edge/demo-addresses")
def edge_demo_addresses() -> list[dict]:
    return [dict(d) for d in DEMO_ADDRESSES]


@app.get("/api/edge/pipeline")
def edge_pipeline() -> list[dict]:
    """The fixed pipeline stage labels (for rendering the trace skeleton)."""
    return [{"index": i, "agent": agent, "label": label}
            for i, (agent, label) in enumerate(PIPELINE_STAGES)]


# ---------------------------------------------------------------------------
# Investigation — batch
# ---------------------------------------------------------------------------
@app.post("/api/edge/investigate")
async def edge_investigate(request: EdgeInvestigationRequest) -> dict:
    result = await _edge.investigate(request)
    return result.model_dump(mode="json")


@app.get("/api/edge/investigate")
async def edge_investigate_get(
    address: str = Query(..., min_length=1),
    asking_rent: int | None = Query(None, ge=0, description="Optional real asking rent to value-check"),
) -> dict:
    result = await _edge.investigate(
        EdgeInvestigationRequest(address=address, asking_rent=asking_rent)
    )
    return result.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Investigation — streaming (Server-Sent Events)
# ---------------------------------------------------------------------------
def _stream_response(request: EdgeInvestigationRequest, http_request: Request) -> StreamingResponse:
    async def gen():
        # Leading comment defeats proxy buffering and signals the stream is open.
        yield ": meraklis stream open\n\n"
        try:
            async for event in _edge.run(request, pace=True):
                if await http_request.is_disconnected():
                    break
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - surface as a stream event, never 500 mid-stream
            log.exception("edge stream failed")
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/edge/stream")
async def edge_stream_post(request: EdgeInvestigationRequest, http_request: Request) -> StreamingResponse:
    """Stream the investigation as Server-Sent Events (full profile via JSON body)."""
    return _stream_response(request, http_request)


@app.get("/api/edge/stream")
async def edge_stream_get(
    http_request: Request,
    address: str = Query("", description="Free-text Toronto address"),
    rsn: str | None = Query(None, description="RentSafeTO building id"),
    is_newcomer: bool = Query(True),
    has_children: bool = Query(False),
    has_seniors: bool = Query(False),
    has_mobility_needs: bool = Query(False),
) -> StreamingResponse:
    """Convenience GET stream (curl / EventSource friendly)."""
    if not address and not rsn:
        raise HTTPException(status_code=422, detail="Provide an address or rsn.")
    request = EdgeInvestigationRequest(
        address=address,
        rsn=rsn,
        profile=UserProfile(
            is_newcomer=is_newcomer,
            has_children=has_children,
            has_seniors=has_seniors,
            has_mobility_needs=has_mobility_needs,
        ),
    )
    return _stream_response(request, http_request)


# ---------------------------------------------------------------------------
# Document vision (NVIDIA Nemotron Parse via vLLM) — read a tenant document
# ---------------------------------------------------------------------------
# NVIDIA Nemotron Parse task prompt — its trained control tokens. The output
# interleaves text with <x_..><y_..> bounding boxes and <class_..> semantic tags,
# which _clean_parse_output strips to leave readable text in reading order.
_PARSE_PROMPT = "</s><s><predict_bbox><predict_classes><output_markdown>"


def _clean_parse_output(text: str) -> str:
    t = re.sub(r"<[xy]_[0-9.]+>", "", text)
    t = re.sub(r"<class_[^>]*>", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


class VisionExplanation(BaseModel):
    explanation: str = ""
    rights_pointers: list[str] = []


class VisionResult(BaseModel):
    ok: bool
    model: str
    extracted_text: str = ""
    explanation: str = ""
    rights_pointers: list[str] = []
    language: str = "English"
    error: str | None = None


def _vision_explain_prompt(extracted: str, doc_hint: str, language: str) -> str:
    hint = f"The user says this is: {doc_hint}.\n" if doc_hint else ""
    lang_rule = (
        f"Write `explanation` and every `rights_pointers` item in {language}.\n" if language else ""
    )
    return (
        "The text below was extracted from a Toronto tenant's document or photo "
        "(e.g. a lease, an N4/N12 notice, or a photo of a housing problem).\n"
        f"{hint}{lang_rule}"
        "Explain in plain language what it is and what it means for the renter, then "
        "list 2-4 relevant Ontario/Toronto tenant-rights pointers. This is general "
        "information, not legal advice; do not invent text that is not present.\n\n"
        f"EXTRACTED TEXT:\n{extracted[:6000]}\n\n"
        'Return JSON: {"explanation": "...", "rights_pointers": ["...", "..."]}'
    )


@app.post("/api/vision")
async def vision(
    file: UploadFile = File(...),
    doc_hint: str = Form(""),
    respond_language: str = Form("English"),
) -> VisionResult:
    """OCR a tenant document with a local vision model, then explain it in plain language."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Empty upload.")
    if len(raw) > 8_000_000:
        raise HTTPException(status_code=413, detail="Image too large (max ~8 MB).")
    mime = file.content_type or "image/png"
    image_b64 = base64.b64encode(raw).decode()
    adapter = get_model_adapter()

    extracted_raw, parse_call = await adapter.parse_document(
        image_b64=image_b64, mime=mime, prompt=_PARSE_PROMPT
    )
    if not extracted_raw:
        return VisionResult(
            ok=False, model=adapter.parse_model, language=respond_language,
            error=(parse_call.error or "Document parser unavailable."),
        )
    extracted = _clean_parse_output(extracted_raw)

    lang = (respond_language or "").strip()
    nonenglish = bool(lang) and lang.lower() != "english"
    model_override = (
        adapter.multilingual_model_name
        if (nonenglish and lang.lower() not in NEMOTRON_LANGS)
        else None
    )
    explanation, _ = await adapter.generate_json(
        agent="Document Explainer",
        response_model=VisionExplanation,
        model=model_override,
        max_tokens=900,
        messages=[
            {
                "role": "system",
                "content": (
                    "You explain tenant documents in plain language. General information "
                    "only, not legal advice. Return valid JSON only."
                ),
            },
            {"role": "user", "content": _vision_explain_prompt(extracted, doc_hint, lang if nonenglish else "")},
        ],
    )
    return VisionResult(
        ok=True, model=adapter.parse_model, language=respond_language,
        extracted_text=extracted,
        explanation=(explanation.explanation if explanation else ""),
        rights_pointers=(explanation.rights_pointers if explanation else []),
    )


# ---------------------------------------------------------------------------
# Static frontend (served if a build exists at <repo>/frontend/dist)
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "name": "Meraklis API",
                "docs": "/docs",
                "health": "/api/health",
                "stream": "/api/edge/stream?address=500 Dawes Rd",
                "note": "Frontend build not found; serving API only. Run `npm run build` in frontend/.",
            }
        )
