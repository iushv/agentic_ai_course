# Data Analyst Agent (SOTA Learn-Along)

Build a production-style data analyst agent with typed outputs, tool calling, sandboxed code execution, evaluation, and observability.

## Start Here

1. Install and bootstrap:
   ```bash
   uv sync --extra api --extra eval
   cp .env.example .env
   ```
2. Set local model config in `.env` (recommended):
   - `LMSTUDIO_BASE_URL=http://127.0.0.1:1234`
   - `LMSTUDIO_MODEL=local-model`
3. Run quality gate:
   ```bash
   ./scripts/preflight_checks.sh
   ```
4. Start learning sequence:
   - `LEARNING_PATH_14_DAYS.md`
   - `LEARNING_DAILY_TEMPLATE.md`

## Learning Flow

- **Phase 1: Core agent patterns**
  - `notebooks/01_foundations.ipynb`
  - `notebooks/02_tool_calling.ipynb`
  - `notebooks/03_code_gen_exec.ipynb`
- **Phase 2: Production controls**
  - `notebooks/04_react_loop.ipynb`
  - `notebooks/05_memory_context.ipynb`
  - `notebooks/06_evaluation.ipynb`
  - `notebooks/07_observability.ipynb`
- **Phase 3: Integration and publish**
  - `notebooks/08_full_agent.ipynb`
  - `notebooks/09_sota_masterclass.ipynb`
  - public docs in `docs/`

## Run Paths

- **Notebook-first path**: follow `LEARNING_PATH_14_DAYS.md`
- **API-first path**:
  ```bash
  uv run uvicorn analyst.api:app --host 0.0.0.0 --port 8000 --reload
  ```
- **API smoke request**:
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

## Safety and Runtime Controls

- Default execution backend is Docker (`ANALYST_EXECUTION_BACKEND=docker`).
- Local fallback mode is available for learning only:
  - `ANALYST_ALLOW_UNSAFE_SUBPROCESS=1`
- Guardrails are on by default; disable only for controlled experiments:
  - `ANALYST_DISABLE_GUARDRAILS=1`

## Where to Read Next

- Industry pattern mapping: `INDUSTRY_AGENT_DETAILS.md`
- Public learn-along hub: `docs/index.md`
- LinkedIn series + tracker + Colab guide: `docs/linkedin/`

## Project Structure

- `src/analyst/agent.py`: orchestration, fallback, memory, tracing hooks
- `src/analyst/tools/`: loader, schema inspector, SQL/code/chart tools
- `src/analyst/sandbox/`: Docker and E2B execution adapters
- `src/analyst/evaluation/`: eval harness and metrics
- `src/analyst/observability/`: tracing and dashboard summaries
- `tests/`: deterministic project checks
