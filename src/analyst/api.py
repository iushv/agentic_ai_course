"""FastAPI entrypoint for the Data Analyst agent."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
from threading import Lock
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from analyst.agent import DEFAULT_MODELS, DataAnalystAgent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = os.getenv("ANALYST_DATA_DIR", str(PROJECT_ROOT / "data"))


class AnalyzeRequest(BaseModel):
    """Request payload for `/analyze`."""

    question: str = Field(min_length=1)
    data_dir: str = Field(default=DEFAULT_DATA_DIR)
    models: list[str] = Field(default_factory=lambda: DEFAULT_MODELS.copy())
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_iterations: int = Field(default=6, ge=1, le=20)
    max_cost_usd: float = Field(default=0.10, ge=0.0)
    session_id: str | None = Field(
        default=None,
        description="Optional conversation session key for memory persistence.",
    )


class AnalyzeResponse(BaseModel):
    """Structured response for `/analyze`."""

    answer: str
    confidence: float
    assumptions: list[str]
    code_used: str
    model_used: str
    tokens_used: int
    tool_calls: int
    trace_id: str
    fallback_attempts: int


app = FastAPI(title="Data Analyst Agent API", version="0.1.0")
_SESSION_AGENTS: OrderedDict[str, DataAnalystAgent] = OrderedDict()
_SESSION_CONFIG: dict[str, tuple] = {}
_MAX_SESSION_AGENTS = 128
_SESSION_LOCK = Lock()
_STATE_LOCK = Lock()
_IDEMPOTENCY_STORE: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_IDEMPOTENCY_TTL_SECONDS = int(os.getenv("ANALYST_IDEMPOTENCY_TTL_SECONDS", "600"))
_MAX_IDEMPOTENCY_KEYS = int(os.getenv("ANALYST_MAX_IDEMPOTENCY_KEYS", "500"))
_RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("ANALYST_RATE_LIMIT_WINDOW_SECONDS", "60"))
_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("ANALYST_RATE_LIMIT_MAX_REQUESTS", "30"))


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    """Basic health endpoint."""
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AnalyzeResponse:
    """Analyze a dataset question using the configured agent."""
    caller_key = request.session_id or (http_request.client.host if http_request.client else "unknown")
    _enforce_rate_limit(caller_key)

    idem_store_key = _build_idempotency_key(idempotency_key, request) if idempotency_key else None
    if idem_store_key:
        cached = _idempotency_get(idem_store_key)
        if cached:
            return AnalyzeResponse(**cached)

    try:
        config = (
            request.data_dir,
            tuple(request.models),
            request.timeout_seconds,
            request.max_iterations,
            request.max_cost_usd,
        )

        if request.session_id:
            with _SESSION_LOCK:
                cached = _SESSION_AGENTS.get(request.session_id)
                if cached is None or _SESSION_CONFIG.get(request.session_id) != config:
                    cached = DataAnalystAgent(
                        data_dir=request.data_dir,
                        model_candidates=request.models,
                        timeout_seconds=request.timeout_seconds,
                        max_iterations=request.max_iterations,
                        max_cost_usd=request.max_cost_usd,
                    )
                    _SESSION_AGENTS[request.session_id] = cached
                    _SESSION_CONFIG[request.session_id] = config
                    _SESSION_AGENTS.move_to_end(request.session_id)
                    while len(_SESSION_AGENTS) > _MAX_SESSION_AGENTS:
                        evicted_id, _ = _SESSION_AGENTS.popitem(last=False)
                        _SESSION_CONFIG.pop(evicted_id, None)
                else:
                    _SESSION_AGENTS.move_to_end(request.session_id)
                agent = cached
        else:
            agent = DataAnalystAgent(
                data_dir=request.data_dir,
                model_candidates=request.models,
                timeout_seconds=request.timeout_seconds,
                max_iterations=request.max_iterations,
                max_cost_usd=request.max_cost_usd,
            )

        execution = agent.analyze(request.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handler
        raise HTTPException(status_code=500, detail=f"Unhandled error: {exc}") from exc

    response = AnalyzeResponse(
        answer=execution.result.answer,
        confidence=execution.result.confidence,
        assumptions=execution.result.assumptions,
        code_used=execution.result.code_used,
        model_used=execution.model_used,
        tokens_used=execution.tokens_used,
        tool_calls=execution.tool_calls,
        trace_id=execution.trace_id,
        fallback_attempts=execution.fallback_attempts,
    )
    if idem_store_key:
        _idempotency_set(idem_store_key, response.model_dump())
    return response


def _build_idempotency_key(idempotency_key: str, request: AnalyzeRequest) -> str:
    payload = {
        "idempotency_key": idempotency_key,
        "question": request.question,
        "data_dir": request.data_dir,
        "models": request.models,
        "timeout_seconds": request.timeout_seconds,
        "max_iterations": request.max_iterations,
        "max_cost_usd": request.max_cost_usd,
        "session_id": request.session_id,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _idempotency_get(key: str) -> dict | None:
    now = time.time()
    with _STATE_LOCK:
        _prune_idempotency(now)
        item = _IDEMPOTENCY_STORE.get(key)
        if item is None:
            return None
        _IDEMPOTENCY_STORE.move_to_end(key)
        return item[1]


def _idempotency_set(key: str, response_payload: dict) -> None:
    now = time.time()
    with _STATE_LOCK:
        _prune_idempotency(now)
        _IDEMPOTENCY_STORE[key] = (now + _IDEMPOTENCY_TTL_SECONDS, response_payload)
        _IDEMPOTENCY_STORE.move_to_end(key)
        while len(_IDEMPOTENCY_STORE) > _MAX_IDEMPOTENCY_KEYS:
            _IDEMPOTENCY_STORE.popitem(last=False)


def _prune_idempotency(now: float) -> None:
    stale_keys = [k for k, (expires_at, _) in _IDEMPOTENCY_STORE.items() if expires_at <= now]
    for key in stale_keys:
        _IDEMPOTENCY_STORE.pop(key, None)


def _enforce_rate_limit(caller_key: str) -> None:
    now = time.time()
    with _STATE_LOCK:
        bucket = _RATE_LIMIT_BUCKETS.setdefault(caller_key, [])
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        bucket[:] = [ts for ts in bucket if ts >= cutoff]
        if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Rate limit exceeded. "
                    f"Max {_RATE_LIMIT_MAX_REQUESTS} requests per {_RATE_LIMIT_WINDOW_SECONDS}s."
                ),
            )
        bucket.append(now)
