# Learning Log — Agentic AI Deep Concepts

This file captures the core concepts, patterns, and mental models
from building the Data Analyst Agent across 8 lessons.

## The Agent Equation

```
Agent = LLM + Tools + Memory + Loop + Guardrails
```

An LLM alone is stateless, tool-less, and uncontrolled.
Each component adds a capability:

| Component | Without It | With It |
|-----------|-----------|---------|
| Tools | Can only generate text | Can query databases, run code, create charts |
| Memory | Forgets everything between messages | Maintains conversation context |
| Loop | Single-shot answer | Multi-step reasoning (ReAct) |
| Guardrails | Unbounded cost, unsafe code | Controlled execution |

## Key Insights by Lesson

### 1. Foundations
- **Structured output is the foundation** — Without it, you're parsing strings. With Pydantic models, the LLM's output is validated, typed, and parseable.
- **Provider switching should be one line** — PydanticAI's model string (`"openai:gpt-4o"` vs `"anthropic:claude-3-5-haiku-latest"`) makes this trivial.
- **Dependency injection > globals** — Pass runtime data through `RunContext[Deps]`, not module-level variables.

### 2. Tool Calling
- **Tools are JSON schemas** — The LLM sees the function signature and docstring as a schema, then decides to call it. Good docstrings = better tool selection.
- **2 API calls minimum** — When a tool is called: (1) LLM decides to call tool, (2) Tool executes and returns result, (3) LLM synthesizes final answer. That's 2 LLM calls.
- **ModelRetry is self-correction** — When a tool raises `ModelRetry(error_message)`, PydanticAI sends the error back to the LLM, which can fix its approach.

### 3. Code Execution
- **Never run LLM code on the host** — Always use a sandbox (Docker, E2B, or at minimum subprocess with timeout).
- **Defense in depth** — AST static analysis catches obvious issues (dangerous imports), sandbox catches everything else.
- **Error-feedback loops work** — When code fails, sending the traceback back to the LLM lets it self-correct. 3 retries is usually enough.

### 4. ReAct Loop
- **Implicit vs explicit planning** — Simple questions don't need a plan. Complex ones benefit from an explicit `AnalysisPlan` with structured steps.
- **Guardrails prevent runaway agents** — Max iterations, token budgets, cost limits, and output truncation are all necessary.
- **The loop is: Think -> Act -> Observe -> Repeat** — PydanticAI handles this automatically when tools are configured.

### 5. Memory
- **Agents are stateless by default** — Every `agent.run_sync()` starts fresh. Memory must be explicitly managed.
- **Three types of memory**: Chat history (what was said), Schema cache (what was learned), Context window (how much fits).
- **Token-aware trimming** — Old messages get dropped when approaching the context limit. Always keep at least the last exchange.

### 6. Evaluation
- **Eval-driven development** — Write eval cases first, then improve the agent. This is the only scalable way to improve reliability.
- **Layer your metrics** — Deterministic (free, fast) first, then heuristic (free, approximate), then LLM-as-Judge (costs money) only when needed.
- **A/B testing is data-driven model selection** — Same eval suite, different providers, objective comparison.

### 7. Observability
- **You can't debug what you can't see** — Every tool call, LLM interaction, and error should be traced.
- **P50 vs P95** — Track both. A fast median with terrible tail latency means some users have a bad experience.
- **Cost tracking prevents surprises** — A single agent query can make 2-5 LLM calls. At scale, this adds up fast.

### 8. Full Assembly
- **Reliability = retry + fallback + circuit breaker** — Retry transient errors, fall back to another model, skip models that keep failing.
- **The adapter pattern decouples eval from implementation** — The eval harness only needs `fn(question) -> (answer, tool_calls, tokens)`.
- **Always eval the production agent** — The simple prototype and the full agent with guardrails/memory/tracing can behave differently.

## Production Patterns Learned

1. **Cost budget enforcement** — Set `max_cost_usd` to prevent runaway spending
2. **Input guardrails** — Block prompt injection and exfiltration before reaching the LLM
3. **Code guardrails** — AST analysis + sandbox isolation for generated code
4. **Circuit breaker** — Skip failing providers to save time and money
5. **Idempotency** — Same request = same response (no duplicate LLM calls)
6. **Rate limiting** — Prevent abuse and control costs at the API layer
7. **Session management** — LRU cache of agent instances for multi-turn conversations

## What to Build Next

- Richer deterministic eval sets (`src/analyst/evaluation/datasets/`)
- API auth and tenant-aware quotas
- Regression tests around fallback and retry paths
- First-class Logfire/Langfuse exporters
- Streaming responses via `agent.run_stream()`
- Interactive Plotly charts
