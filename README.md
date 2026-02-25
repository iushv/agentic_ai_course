# Data Analyst Agent (Agentic AI Learning Project)

Production-style learning project for building a provider-agnostic data analyst
agent with PydanticAI, sandboxed code execution, evaluations, and tracing.

## What It Does

- Accepts dataset-driven natural language questions
- Uses tool calling (schema inspection, SQL, Python execution, chart generation)
- Returns structured answers via `AnalysisResult`
- Supports model fallback across OpenAI, Anthropic, and Ollama
- Tracks traces/cost signals with a local tracer

## Quickstart

```bash
uv sync --extra api --extra eval
cp .env.example .env
```

Set provider config in `.env`:

- Local LM Studio (recommended for this learning track):
  - `LMSTUDIO_BASE_URL=http://127.0.0.1:1234`
  - `LMSTUDIO_MODEL=local-model` (replace with your loaded model ID)
  - Optional override: `ANALYST_PRIMARY_MODEL=openai:local-model`
- OpenAI/Anthropic keys are optional unless you explicitly use those providers.

Run tests:

```bash
uv run python -m pytest tests/
```

Run API:

```bash
uv run uvicorn analyst.api:app --host 0.0.0.0 --port 8000 --reload
```

Execution backend defaults to Docker sandbox:

```bash
export ANALYST_EXECUTION_BACKEND=docker
```

For local debugging only (unsafe):

```bash
export ANALYST_ALLOW_UNSAFE_SUBPROCESS=1
```

Guardrails are enabled by default. To disable for controlled experiments:

```bash
export ANALYST_DISABLE_GUARDRAILS=1
```

API reliability controls:

```bash
export ANALYST_RATE_LIMIT_MAX_REQUESTS=30
export ANALYST_RATE_LIMIT_WINDOW_SECONDS=60
export ANALYST_IDEMPOTENCY_TTL_SECONDS=600
```

## API Example

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "content-type: application/json" \
  -H "Idempotency-Key: demo-1" \
  -d '{
    "question": "Which region has the highest total revenue in sample_sales?",
    "data_dir": "data",
    "models": ["openai:local-model"],
    "session_id": "demo-session"
  }'
```

## Project Layout

- `src/analyst/agent.py`: main orchestration + fallback + memory wiring
- `src/analyst/tools/`: data loader, schema inspector, code executor, visualizer
- `src/analyst/safety/`: input and code guardrails
- `src/analyst/reliability/`: retry/backoff and circuit breaker policies
- `src/analyst/prompting/`: dynamic few-shot example retrieval
- `src/analyst/sandbox/`: Docker and E2B execution backends
- `src/analyst/evaluation/`: eval harness and metrics
- `src/analyst/observability/`: tracing and dashboard stats
- `tests/`: local deterministic test coverage

## Lessons

- `notebooks/01_foundations.ipynb` through `notebooks/07_observability.ipynb`
- continue assembling full production pipeline in `notebooks/08_full_agent.ipynb`

## Industry Patterns

- Source-backed blueprint of cutting-edge lab practices:
  `INDUSTRY_AGENT_DETAILS.md`
