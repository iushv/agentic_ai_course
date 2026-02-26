# Navigation Guide

Use this file as the single map for what to run, in what order, and where outputs go.

## 1) First Run (30-45 min)

1. `uv sync --extra api --extra eval`
2. `cp .env.example .env`
3. Set local model in `.env`:
   - `LMSTUDIO_BASE_URL=http://127.0.0.1:1234`
   - `LMSTUDIO_MODEL=local-model`
4. `./scripts/preflight_checks.sh`

Expected:
- tests pass
- import smoke check passes
- executed reference notebook written to `.artifacts/notebooks/09_sota_masterclass.executed.ipynb`

## 2) Core Learning Path (14 days)

1. Follow `LEARNING_PATH_14_DAYS.md` day-by-day.
2. For each day, create `learning_outputs/day-XX.md` using `LEARNING_DAILY_TEMPLATE.md`.
3. Do not advance until that day checklist passes.

Important:
- `Output` bullets in `LEARNING_PATH_14_DAYS.md` are expected deliverables from you.

## 3) Notebook Order

1. `notebooks/01_foundations.ipynb`
2. `notebooks/02_tool_calling.ipynb`
3. `notebooks/03_code_gen_exec.ipynb`
4. `notebooks/04_react_loop.ipynb`
5. `notebooks/05_memory_context.ipynb`
6. `notebooks/06_evaluation.ipynb`
7. `notebooks/07_observability.ipynb`
8. `notebooks/08_full_agent.ipynb`
9. `notebooks/09_sota_masterclass.ipynb`

## 4) Publish / Share Track (Optional)

Use `docs/index.md`, then:
- `docs/linkedin/LINKEDIN_SOTA_AGENTIC_AI_14_DAY_SERIES.md`
- `docs/linkedin/LINKEDIN_14_DAY_TRACKER.csv`
- `docs/linkedin/COLAB_NOTEBOOK_EXECUTION_GUIDE.md`
- `docs/linkedin/PUBLISH_AND_HOST.md`

## 5) If Something Fails

1. Re-run: `uv run python -m pytest tests/ -q`
2. Re-run: `./scripts/preflight_checks.sh`
3. Check `.env` provider variables and local model server availability.
4. In Jupyter, prefer `await agent.run(...)` over `agent.run_sync(...)` if you see `RuntimeError: This event loop is already running`.
5. If local models fail strict output validation, switch to a stronger local model or increase retries.
