---
name: agent-scaffold
description: Generate a production-ready agent skeleton with tools, guardrails, and tests.
---

# Agent Scaffold

Generate a complete, production-ready agent project structure from a task description.
Output includes the agent loop, tool schemas, guardrail pipeline, config, and test stubs.

## When to Use

- Starting a new agent project from scratch.
- Adding a new agent to an existing multi-agent system.
- Prototyping an agent to validate tool design before full implementation.

## Inputs

Provide:
- **Task description**: What the agent should accomplish.
- **Tool list**: Names and brief descriptions of tools the agent needs.
- **Architecture level** (optional): Override auto-detection. Default: auto-select.
- **Model** (optional): Primary model to use. Default: claude-sonnet-4-6.

## Architecture Level Selection

Auto-select based on inputs:
- No tools mentioned → Level 0 (single call) or Level 1 (chain).
- Fixed tool sequence → Level 1 (chain) or Level 2 (router).
- Dynamic tool use → Level 3 (ReAct).
- Different permissions needed → Level 4 (multi-agent). Requires justification.

## Generated Structure

```
{agent_name}/
├── agent.py           # Main agent loop (ReAct or chain)
├── config.py          # AgentConfig with all budget limits
├── tools/
│   ├── __init__.py
│   └── {tool_name}.py # One file per tool with Pydantic schema
├── guardrails/
│   ├── __init__.py
│   ├── input.py       # Input validation pipeline (layers 1-4)
│   └── output.py      # Output validation pipeline (layer 6)
├── models.py          # Shared data models (AgentStep, AgentRun)
├── tracing.py         # Observability setup (Langfuse/LangSmith)
├── tests/
│   ├── test_tools.py      # Unit tests for each tool
│   ├── test_guardrails.py # Unit tests for guardrails
│   ├── test_agent.py      # Integration tests with mock LLM
│   └── evals/
│       └── golden.yaml    # Golden trajectory test cases
└── pyproject.toml     # Dependencies
```

## Config Template

Every generated agent includes these enforced limits:

```python
class AgentConfig(BaseModel):
    max_iterations: int = Field(default=10, le=50)
    max_tool_calls: int = Field(default=25, le=100)
    max_tokens: int = Field(default=100_000)
    max_cost_usd: float = Field(default=0.50)
    timeout_seconds: int = Field(default=120, le=600)
    model: str = "claude-sonnet-4-6"
    fallback_models: list[str] = ["claude-haiku-4-5-20251001"]
```

## Tool Template

Each tool follows the six design principles:

```python
class {ToolName}Tool(BaseModel):
    """{Rich description with WHEN/WHAT/edge cases.}"""
    {param}: {type} = Field(
        description="{Clear description}",
        # Constrained: enum, min/max, pattern
    )
```

## ReAct Loop Template

The generated loop includes:
1. Budget checks before every LLM call (cost, tokens, iterations, timeout).
2. Tool call execution through guardrail pipeline.
3. Output truncation for large tool results (10,000 char limit).
4. Structured tracing for every step.
5. Circuit breaker and model fallback.
6. Graceful degradation on repeated failures.

## Guardrail Pipeline Template

**Input pipeline:**
1. Pydantic schema validation with length limits.
2. Regex filtering for injection patterns.
3. Optional ML classifier integration point.
4. Semantic analysis hook.

**Output pipeline:**
1. PII scrubbing (regex-based, configurable patterns).
2. Schema validation against expected output type.
3. Grounding check stub (verify claims against tool results).

## Test Stubs

**Unit tests**: One test per tool verifying:
- Valid input produces expected output.
- Invalid input raises appropriate error.
- Edge cases are handled (empty input, max-length input).

**Guardrail tests**: Verify:
- SQL injection attempts are blocked.
- Prompt injection attempts are blocked.
- PII is scrubbed from outputs.
- Schema violations are caught.

**Integration tests**: Verify:
- Mock LLM → agent calls correct tools → produces answer.
- Agent stops at max_iterations.
- Fallback activates when primary model fails.

**Eval template**: YAML format with fields:
- `question`, `expected_tools`, `expected_keywords`, `max_tool_calls`, `max_cost`.
