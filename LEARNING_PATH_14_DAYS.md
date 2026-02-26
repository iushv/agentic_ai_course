# 14-Day Learning Path: Data Analyst Agent (SOTA + Production)

Start date: **Sunday, February 22, 2026**  
Goal: learn architecture, implementation, testing, safety, reliability, and production operations end-to-end.

## Daily Rule

- Do not move to the next day until validation passes:

```bash
uv run python -m pytest tests/ -q
```

- Capture your daily deliverable using:
  - `LEARNING_DAILY_TEMPLATE.md`
  - each `Output` bullet below is expected from you as learner evidence.

## Day-by-Day Plan

### Day 1 (Sun, Feb 22)

- Setup environment and baseline verification.
- Read:
  - `README.md`
  - `INDUSTRY_AGENT_DETAILS.md`
  - `LEARNING_LOG.md`
- Run:
  - `uv sync --extra api --extra eval`
  - `uv run python -m pytest tests/ -q`
- Output:
  - Baseline notes in `LEARNING_LOG.md`.

Checklist:
- [ ] Dependencies installed
- [ ] Tests pass
- [ ] Baseline notes written

### Day 2 (Mon, Feb 23)

- Run `notebooks/01_foundations.ipynb`.
- Read `src/analyst/models.py`.
- Output:
  - 5-line summary: structured output + provider abstraction.

Checklist:
- [ ] Notebook ran
- [ ] Summary written

### Day 3 (Tue, Feb 24)

- Run `notebooks/02_tool_calling.ipynb`.
- Read `src/analyst/tools/`.
- Output:
  - Explain `inspect_data`, `run_sql`, `run_python_code` flow.

Checklist:
- [ ] Notebook ran
- [ ] Tool flow explained

### Day 4 (Wed, Feb 25)

- Run `notebooks/03_code_gen_exec.ipynb`.
- Read `src/analyst/sandbox/docker_sandbox.py`.
- Output:
  - 1 chart artifact under `data/outputs/`.

Checklist:
- [ ] Notebook ran
- [ ] Chart generated

### Day 5 (Thu, Feb 26)

- Run `notebooks/04_react_loop.ipynb`.
- Read `src/analyst/agent.py`.
- Output:
  - Explain iteration/tool budget controls.

Checklist:
- [ ] Notebook ran
- [ ] Loop limits explained

### Day 6 (Fri, Feb 27)

- Run `notebooks/05_memory_context.ipynb`.
- Read `src/analyst/memory/conversation.py`.
- Output:
  - Demonstrate one follow-up query using session memory.

Checklist:
- [ ] Notebook ran
- [ ] Follow-up demo captured

### Day 7 (Sat, Feb 28)

- Midpoint integration day.
- Run:
  - `notebooks/08_full_agent.ipynb`
  - `uv run python -m pytest tests/ -q`
- Output:
  - “What still breaks/confuses me” note.

Checklist:
- [ ] Full agent notebook ran
- [ ] Midpoint gaps listed

### Day 8 (Sun, Mar 1)

- Run `notebooks/06_evaluation.ipynb`.
- Read `src/analyst/evaluation/harness.py`.
- Expand dataset in `src/analyst/evaluation/datasets/sample_cases.json`.
- Output:
  - Add at least 5 new eval cases.

Checklist:
- [ ] Evaluation notebook ran
- [ ] New eval cases added

### Day 9 (Mon, Mar 2)

- Run `notebooks/07_observability.ipynb`.
- Read `src/analyst/observability/tracing.py`.
- Output:
  - Capture and interpret one trace summary.

Checklist:
- [ ] Observability notebook ran
- [ ] Trace interpretation written

### Day 10 (Tue, Mar 3)

- Reliability deep dive.
- Read:
  - `src/analyst/reliability/policies.py`
  - reliability wiring in `src/analyst/agent.py`
- Output:
  - Simulate transient failures and explain retry vs circuit-breaker behavior.

Checklist:
- [ ] Retry policy understood
- [ ] Circuit breaker understood

### Day 11 (Wed, Mar 4)

- Guardrails + SQL safety day.
- Read:
  - `src/analyst/safety/guardrails.py`
  - `src/analyst/tools/sql_safety.py`
- Output:
  - Add 3 adversarial prompts/tests; verify blocking.

Checklist:
- [ ] Guardrails reviewed
- [ ] Adversarial tests pass

### Day 12 (Thu, Mar 5)

- API production controls day.
- Read `src/analyst/api.py`.
- Test:
  - `/health`
  - `/analyze` with `Idempotency-Key`
  - rate-limit behavior
- Output:
  - One idempotent replay example + one 429 example.

Checklist:
- [ ] API tests done
- [ ] Idempotency demonstrated
- [ ] Rate limit demonstrated

### Day 13 (Fri, Mar 6)

- Run `notebooks/09_sota_masterclass.ipynb` end-to-end.
- Compare with `.artifacts/notebooks/09_sota_masterclass.executed.ipynb` after preflight run.
- Output:
  - 10 key takeaways.

Checklist:
- [ ] Masterclass notebook ran
- [ ] 10 takeaways written

### Day 14 (Sat, Mar 7)

- Capstone demo.
- Run one full pipeline:
  - question -> tool usage -> chart -> eval -> trace -> API response
- Output:
  - Final architecture review in `LEARNING_LOG.md`:
    - strengths
    - weaknesses
    - next 30-day plan

Checklist:
- [ ] End-to-end demo complete
- [ ] Final report written

## Weekly Repeatable Preflight

Use the full verification script before major changes:

```bash
./scripts/preflight_checks.sh
```

## Stretch Goals (Optional)

- Add persistent memory backend (Redis/SQLite/Postgres).
- Add API auth and tenant-aware quotas.
- Add Docker/E2B integration tests in CI.
- Add provider A/B eval matrix (OpenAI/Anthropic/Ollama/Gemini).
