# Data Analyst Agent — Learn Agentic AI by Building

A production-grade data analyst agent built across 8 progressive lessons. The agent takes datasets + natural language questions, writes and executes Python/SQL code, creates visualizations, and explains findings.

**Provider-agnostic** (OpenAI, Claude, Ollama/LM Studio) using PydanticAI.

## Quick Start

```bash
# 1. Install dependencies
uv sync --extra api --extra eval

# 2. Configure your LLM provider
cp .env.example .env
# Edit .env: set LMSTUDIO_BASE_URL or OPENAI_API_KEY

# 3. Start learning
jupyter lab notebooks/01_foundations.ipynb
```

## The 8-Lesson Curriculum

| Lesson | Notebook | What You Build |
|--------|----------|---------------|
| **1. Foundations** | `01_foundations.ipynb` | LLM calls, structured output, provider switching, dependency injection |
| **2. Tool Calling** | `02_tool_calling.ipynb` | `@agent.tool`, DuckDB SQL, schema inspection, retry/validation |
| **3. Code Execution** | `03_code_gen_exec.ipynb` | Sandboxed Python, AST validation, error-feedback loops |
| **4. ReAct Loop** | `04_react_loop.ipynb` | Multi-step reasoning, planning, guardrails, cost budgets |
| **5. Memory** | `05_memory_context.ipynb` | Chat history, schema cache, context window management |
| **6. Evaluation** | `06_evaluation.ipynb` | Deterministic metrics, LLM-as-Judge, safety eval, A/B testing |
| **7. Observability** | `07_observability.ipynb` | Tracing, cost tracking, performance dashboards, error analysis |
| **8. Full Assembly** | `08_full_agent.ipynb` | Production orchestration, FastAPI endpoint, deployment checklist |

Each notebook is self-contained with detailed explanations, architecture diagrams, and runnable code.

## Run the API

```bash
uv run uvicorn analyst.api:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Analyze a dataset
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total revenue?", "data_dir": "data"}'

# Multi-turn conversation
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Break it down by region", "session_id": "my-session"}'
```

## Project Structure

```
src/analyst/
├── agent.py              # Orchestrator: fallback, memory, tracing
├── api.py                # FastAPI: rate limiting, idempotency, sessions
├── models.py             # Pydantic schemas for all inputs/outputs
├── tools/                # Agent capabilities
│   ├── schema_inspector  # Dataset structure inspection
│   ├── data_loader       # CSV/JSON/Excel ingestion
│   ├── code_executor     # Sandboxed Python execution
│   ├── visualizer        # Chart generation
│   └── sql_safety        # Read-only SQL enforcement
├── sandbox/              # Execution isolation
│   ├── docker_sandbox    # Production (Docker container)
│   └── e2b_sandbox       # Cloud (E2B)
├── memory/               # State management
│   └── conversation      # Chat history + schema cache
├── safety/               # Guardrails
│   └── guardrails        # Input validation, code AST analysis
├── reliability/          # Error handling
│   └── policies          # Retry, circuit breaker
├── evaluation/           # Quality measurement
│   ├── harness           # Test suite runner
│   └── metrics           # Scoring functions
└── observability/        # Monitoring
    └── tracing           # Span/trace recording
```

## Safety and Runtime Controls

| Setting | Default | Purpose |
|---------|---------|---------|
| `ANALYST_EXECUTION_BACKEND` | `docker` | Code execution backend |
| `ANALYST_ALLOW_UNSAFE_SUBPROCESS` | `0` | Enable local subprocess (learning only) |
| `ANALYST_DISABLE_GUARDRAILS` | `0` | Disable input/code guardrails |
| `ANALYST_RATE_LIMIT_MAX_REQUESTS` | `30` | Max API requests per window |

## Technology Stack

| Layer | Choice |
|-------|--------|
| Agent Framework | PydanticAI |
| LLM Providers | OpenAI, Anthropic, Ollama (via LM Studio) |
| Structured Output | Pydantic models |
| Code Sandbox | Docker (prod), subprocess (dev) |
| SQL Engine | DuckDB (in-memory on DataFrames) |
| Observability | Custom tracer + Logfire/Langfuse |
| Evaluation | Custom harness + LLM-as-Judge |
| API | FastAPI |
| Package Manager | uv + pyproject.toml |
