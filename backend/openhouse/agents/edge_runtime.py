"""Local OpenAI-compatible model runtime for Meraklis.

The Spark build treats the model server as an edge dependency: NVIDIA NIM,
vLLM, TensorRT-LLM, llama.cpp server, LM Studio and Ollama can all work when
they expose an OpenAI-compatible ``/v1/chat/completions`` endpoint.

No cloud model is configured by default. If the local endpoint is down, callers
receive ``None`` and can continue with deterministic reports.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV = _REPO_ROOT / ".env"
if _ENV.exists():
    load_dotenv(_ENV, override=True)

DEFAULT_MODEL_BASE_URL = "http://localhost:8000/v1"
DEFAULT_MODEL_NAME = "nvidia/nemotron-3-nano-30b"
SUPPORTED_BACKENDS = (
    "NVIDIA NIM local container",
    "vLLM on NVIDIA GPU",
    "TensorRT-LLM OpenAI-compatible server",
    "llama.cpp server with CUDA",
    "LM Studio local server",
    "Ollama local OpenAI-compatible endpoint",
)

T = TypeVar("T", bound=BaseModel)


class ModelCallSummary(BaseModel):
    """Audit-safe metadata for one local model attempt."""

    agent: str
    provider: str = "openai-compatible-local"
    model: str
    endpoint: str
    status: str = "skipped"  # ok | validation_error | error | skipped
    latency_ms: int = 0
    retries: int = 0
    fallback_used: bool = False
    error: str | None = None


class EdgeRuntimeStatus(BaseModel):
    """Runtime visibility shown in the NVIDIA Edge panel."""

    model_name: str
    endpoint: str
    local_edge_status: str
    endpoint_available: bool
    inference_calls: int
    average_latency_ms: int | None
    gpu_hardware_mode: str
    gpu_details: str
    fallback_status: str
    supported_backends: list[str]
    trust_cue: str
    last_error: str | None = None


def _is_local_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".local")


def _extract_json(text: str) -> str:
    """Pull a JSON object from a model response that may include fences/prose."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1]
    return t


@lru_cache(maxsize=1)
def _gpu_mode() -> tuple[str, str]:
    """Best-effort NVIDIA hardware detection, with a Spark-target fallback label."""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            first = proc.stdout.strip().splitlines()[0]
            return "NVIDIA GPU detected", first
    except Exception:  # noqa: BLE001 - hardware probing should never break the app
        pass
    return (
        "Mocked Spark target",
        "No local nvidia-smi response. Demo target: DGX Spark / ASUS GX10 with NVIDIA GB10 Grace Blackwell.",
    )


class LocalModelAdapter:
    """Tiny OpenAI-compatible adapter with validation and deterministic fallback hooks."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("MODEL_BASE_URL", DEFAULT_MODEL_BASE_URL).rstrip("/")
        self.model_name = os.environ.get("MODEL_NAME", DEFAULT_MODEL_NAME)
        self.api_key = os.environ.get("MODEL_API_KEY", "")
        self.inference_calls = 0
        self._latencies: list[int] = []
        self.fallback_count = 0
        self.last_error: str | None = None

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    @property
    def models_url(self) -> str:
        return f"{self.base_url}/models"

    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def probe(self) -> bool:
        """Check whether the local endpoint is reachable."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.8)) as client:
                resp = await client.get(self.models_url, headers=self.headers())
            ok = resp.status_code == 200
            if ok:
                self.last_error = None
            else:
                self.last_error = f"model endpoint probe returned HTTP {resp.status_code}"
            return ok
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            return False

    async def status(self, probe: bool = False) -> EdgeRuntimeStatus:
        available = await self.probe() if probe else self.last_error is None and self.inference_calls > 0
        gpu_mode, gpu_details = _gpu_mode()
        avg = int(sum(self._latencies) / len(self._latencies)) if self._latencies else None
        local = _is_local_url(self.base_url)
        if available and local:
            local_status = "local endpoint reachable"
        elif local:
            local_status = "local endpoint not reachable; deterministic fallback ready"
        else:
            local_status = "non-local endpoint configured; verify edge deployment policy"
        return EdgeRuntimeStatus(
            model_name=self.model_name,
            endpoint=self.base_url,
            local_edge_status=local_status,
            endpoint_available=available,
            inference_calls=self.inference_calls,
            average_latency_ms=avg,
            gpu_hardware_mode=gpu_mode,
            gpu_details=gpu_details,
            fallback_status=(
                "deterministic fallback used"
                if self.fallback_count
                else "deterministic fallback armed"
            ),
            supported_backends=list(SUPPORTED_BACKENDS),
            trust_cue="No sensitive data leaves this device when MODEL_BASE_URL points to localhost.",
            last_error=self.last_error,
        )

    async def generate_json(
        self,
        *,
        agent: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float = 0.2,
        max_tokens: int = 700,
        attempts: int = 2,
    ) -> tuple[T | None, ModelCallSummary]:
        """Generate and validate structured JSON, returning ``None`` on failure."""
        call = ModelCallSummary(agent=agent, model=self.model_name, endpoint=self.base_url)
        working_messages = list(messages)
        started = time.perf_counter()
        last_error: str | None = None

        for attempt in range(attempts):
            call.retries = attempt
            payload = {
                "model": self.model_name,
                "messages": working_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            }
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=2.0)) as client:
                    resp = await client.post(self.chat_url, headers=self.headers(), json=payload)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(_extract_json(content))
                result = response_model.model_validate(parsed)
                latency = int((time.perf_counter() - started) * 1000)
                self.inference_calls += 1
                self._latencies.append(latency)
                self.last_error = None
                call.status = "ok"
                call.latency_ms = latency
                return result, call
            except httpx.HTTPStatusError as exc:
                last_error = f"HTTP {exc.response.status_code} from local model endpoint"
                working_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Your previous response failed JSON validation. "
                            "Return only a valid JSON object matching the requested schema."
                        ),
                    },
                ]
            except Exception as exc:  # noqa: BLE001 - validation or endpoint failure
                last_error = f"{type(exc).__name__}: {exc}"
                working_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Your previous response failed JSON validation. "
                            "Return only a valid JSON object matching the requested schema."
                        ),
                    },
                ]

        latency = int((time.perf_counter() - started) * 1000)
        self.fallback_count += 1
        self.last_error = last_error
        call.status = "error"
        call.latency_ms = latency
        call.fallback_used = True
        call.error = last_error
        return None, call


_adapter: LocalModelAdapter | None = None


def get_model_adapter() -> LocalModelAdapter:
    global _adapter
    if _adapter is None:
        _adapter = LocalModelAdapter()
    return _adapter
