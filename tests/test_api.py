from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from analyst.api import (
    _IDEMPOTENCY_STORE,
    _RATE_LIMIT_BUCKETS,
    _SESSION_AGENTS,
    _SESSION_CONFIG,
    app,
)
from analyst.models import AnalysisResult


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_uses_session_cache(monkeypatch) -> None:
    _SESSION_AGENTS.clear()
    _SESSION_CONFIG.clear()
    _IDEMPOTENCY_STORE.clear()
    _RATE_LIMIT_BUCKETS.clear()

    class FakeExecution:
        result = AnalysisResult(
            answer="ok",
            confidence=0.9,
            assumptions=[],
            code_used="print('ok')",
        )
        model_used = "mock:model"
        tokens_used = 10
        tool_calls = 1
        trace_id = "trace_0001"
        fallback_attempts = 0

    class FakeAgent:
        created_count = 0
        analyze_count = 0

        def __init__(self, *args, **kwargs):
            FakeAgent.created_count += 1

        @staticmethod
        def analyze(_question: str):
            FakeAgent.analyze_count += 1
            return FakeExecution()

    monkeypatch.setattr("analyst.api.DataAnalystAgent", FakeAgent)

    client = TestClient(app)
    payload = {
        "question": "hello",
        "data_dir": "data",
        "models": ["mock:model"],
        "session_id": "s1",
    }

    resp1 = client.post("/analyze", json=payload)
    resp2 = client.post("/analyze", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert FakeAgent.created_count == 1
    assert FakeAgent.analyze_count == 2


def test_analyze_endpoint_idempotency_key(monkeypatch) -> None:
    _SESSION_AGENTS.clear()
    _SESSION_CONFIG.clear()
    _IDEMPOTENCY_STORE.clear()
    _RATE_LIMIT_BUCKETS.clear()

    class FakeExecution:
        result = AnalysisResult(
            answer="cached",
            confidence=0.9,
            assumptions=[],
            code_used="print('cached')",
        )
        model_used = "mock:model"
        tokens_used = 5
        tool_calls = 1
        trace_id = "trace_cached"
        fallback_attempts = 0

    class FakeAgent:
        analyze_count = 0

        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def analyze(_question: str):
            FakeAgent.analyze_count += 1
            return FakeExecution()

    monkeypatch.setattr("analyst.api.DataAnalystAgent", FakeAgent)

    client = TestClient(app)
    payload = {
        "question": "hello",
        "data_dir": "data",
        "models": ["mock:model"],
        "session_id": "idem-session",
    }
    headers = {"Idempotency-Key": "abc-123"}
    resp1 = client.post("/analyze", json=payload, headers=headers)
    resp2 = client.post("/analyze", json=payload, headers=headers)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["answer"] == "cached"
    assert resp2.json()["answer"] == "cached"
    assert FakeAgent.analyze_count == 1


def test_analyze_endpoint_rate_limit(monkeypatch) -> None:
    _SESSION_AGENTS.clear()
    _SESSION_CONFIG.clear()
    _IDEMPOTENCY_STORE.clear()
    _RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr("analyst.api._RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr("analyst.api._RATE_LIMIT_WINDOW_SECONDS", 60)

    class FakeExecution:
        result = AnalysisResult(
            answer="ok",
            confidence=0.9,
            assumptions=[],
            code_used="print('ok')",
        )
        model_used = "mock:model"
        tokens_used = 1
        tool_calls = 1
        trace_id = "trace_1"
        fallback_attempts = 0

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def analyze(_question: str):
            return FakeExecution()

    monkeypatch.setattr("analyst.api.DataAnalystAgent", FakeAgent)

    client = TestClient(app)
    payload = {
        "question": "hello",
        "data_dir": "data",
        "models": ["mock:model"],
    }
    first = client.post("/analyze", json=payload)
    second = client.post("/analyze", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
