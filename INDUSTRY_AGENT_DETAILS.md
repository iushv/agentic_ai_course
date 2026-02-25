# Industry Agent Details (OpenAI, Anthropic, Google)

As of **February 22, 2026**, this document summarizes the most relevant
production patterns used by top labs and maps them to this repository.

## 1) What Top Labs Are Doing

### A. Tool-first agent architecture

- **OpenAI**: Responses API + built-in tools (Code Interpreter, file search, remote MCP)
  with agentic controls such as background mode and reasoning summaries.
- **Anthropic**: explicit tool-use contracts, server/client tool separation, strict tool mode.
- **Google**: Gemini function calling + Agent Engine tool ecosystem.

Why it matters:
- Deterministic tool schemas reduce hallucinated actions.
- Background/async execution enables long-running tasks.

### B. Structured outputs and schema guarantees

- Labs emphasize schema-constrained outputs and strict argument validation for tools.
- This improves reliability, downstream parsing, and safe automation.

### C. Sandboxed code execution

- Agent platforms now treat code execution as an isolated capability with explicit
  runtime controls, not direct host execution.
- Typical controls: network restrictions, memory/CPU/time limits, artifact boundaries.

### D. Memory + context management

- **Anthropic** and **Google** documentation both emphasize state/session constructs,
  prompt caching, and memory tools.
- Practical pattern: short-term conversation memory + cached static context + retrieval.

### H. Reliability controls around model providers

- SOTA agent services use retry/backoff for transient failures and circuit breakers
  to avoid repeatedly hitting degraded providers.
- They also use idempotency and request IDs at API boundaries to make client retries safe.

### E. Evaluation flywheel and trace grading

- Labs now treat evals as a first-class development loop (dataset-driven tests,
  trace-level grading, regression monitoring).
- Trace-based evaluation is used to catch process failures, not only final-answer failures.

### F. Guardrails and jailbreak resistance

- Modern agent docs emphasize prompt-injection and jailbreak mitigation, especially
  around tool calls and data exfiltration attempts.
- Guardrails are implemented as layered checks:
  input policies, tool policies, output policies, and runtime isolation.

### G. Observability, cost, and latency controls

- Common production controls:
  - trace IDs spanning model + tool calls
  - token/cost accounting
  - bounded loops and call budgets
  - failure mode categorization

## 2) How This Repo Now Reflects Those Patterns

Implemented:
- Tool-first orchestration + structured output:
  `src/analyst/agent.py`
- Sandbox-first code execution with Docker by default:
  `src/analyst/agent.py`, `src/analyst/sandbox/docker_sandbox.py`
- Optional cloud sandbox adapter (E2B):
  `src/analyst/sandbox/e2b_sandbox.py`
- Input + generated-code guardrails:
  `src/analyst/safety/guardrails.py`
- Provider reliability policies (retry/backoff + circuit breaker):
  `src/analyst/reliability/policies.py`
- Structured prompt sections + dynamic few-shot retrieval:
  `src/analyst/prompting/example_store.py`, `src/analyst/agent.py`
- SQL read-only safety policy:
  `src/analyst/tools/sql_safety.py`
- Session-aware API memory (per session_id, LRU bounded):
  `src/analyst/api.py`
- API request IDs, idempotency keys, and rate limiting:
  `src/analyst/api.py`
- Eval harness and metrics:
  `src/analyst/evaluation/harness.py`, `src/analyst/evaluation/metrics.py`
- Trace and cost/latency tracking:
  `src/analyst/observability/tracing.py`

Still to implement next:
- Persistent memory store (Redis/SQLite/Postgres), not just in-process session cache.
- AuthN/AuthZ + per-tenant rate limits for `/analyze`.
- Docker/E2B integration tests in CI (current tests cover subprocess + unit paths).
- First-class Langfuse/Logfire exporters with environment-driven toggles.
- Provider A/B matrix runner (same eval dataset across OpenAI/Anthropic/Ollama/Gemini).

## 3) Source Links (Official)

OpenAI:
- [New tools and features in the Responses API](https://openai.com/index/new-tools-and-features-in-the-responses-api/)
- [New tools for building agents](https://openai.com/index/new-tools-for-building-agents/)
- [Agent evals guide](https://platform.openai.com/docs/guides/agent-evals)
- [Trace grading guide](https://platform.openai.com/docs/guides/trace-grading)
- [Reasoning best practices](https://platform.openai.com/docs/guides/reasoning-best-practices)

Anthropic:
- [Tool use overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview)
- [Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Define success (evals)](https://docs.anthropic.com/en/docs/test-and-evaluate/define-success)
- [Develop tests (eval build workflow)](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests)
- [Mitigate jailbreaks](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks)
- [Multi-shot prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting)

Google:
- [Vertex AI Agent Engine overview](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [Gemini function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling)
- [Example Store in Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/agent-engine/example-store/overview)
