---
name: guardrail-setup
description: Add a defense-in-depth guardrail pipeline with input/output validation and tests.
---

# Guardrail Setup

Generate a complete guardrail pipeline for an agent, covering all 6 defense layers
from the production blueprint. Includes implementation code and test suite.

## When to Use

- Setting up guardrails for a new agent.
- Adding missing guardrail layers to an existing agent.
- Hardening an agent after a security review or incident.

## Inputs

Provide:
- **Agent description**: What the agent does.
- **Tool list**: Tools the agent uses (especially any that execute code or SQL).
- **Data sensitivity**: What kind of data flows through (PII, financial, medical, etc.).
- **Existing guardrails** (optional): What's already in place.

## The 6-Layer Pipeline

### Layer 1: Schema Validation

**Purpose**: Reject malformed input before any processing.

```python
from pydantic import BaseModel, Field, field_validator

class AgentInput(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    conversation_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("query")
    @classmethod
    def no_null_bytes(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("Null bytes not allowed")
        return v
```

**Tests**: Empty input, oversized input, null bytes, invalid characters.

### Layer 2: Content Filtering

**Purpose**: Detect known injection patterns via regex.

Patterns to detect and block:
- `ignore previous instructions` (case-insensitive).
- `system:`, `<|im_start|>`, `[INST]` — role injection.
- Base64-encoded payloads longer than 100 chars.
- HTML/script tags: `<script>`, `javascript:`, `on\w+=`.
- URL-based exfiltration: `fetch(`, `curl `, `wget `.

```python
import re

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"(system|assistant)\s*:", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"\bon\w+\s*=", re.IGNORECASE),
    re.compile(r"(fetch|curl|wget)\s*\(", re.IGNORECASE),
]

def check_injection(text: str) -> list[str]:
    return [p.pattern for p in INJECTION_PATTERNS if p.search(text)]
```

**Tests**: Each pattern with positive and negative examples.

### Layer 3: ML Classification (Optional)

**Purpose**: Catch sophisticated injection and toxic content.

Integration points:
- **Prompt injection classifier**: Hugging Face `protectai/deberta-v3-base-prompt-injection-v2`.
- **Toxicity filter**: Meta LlamaGuard or OpenAI moderation endpoint.

```python
async def classify_input(text: str) -> dict:
    injection_score = await injection_classifier.predict(text)
    toxicity_score = await toxicity_classifier.predict(text)
    return {
        "injection_risk": injection_score > 0.85,
        "toxicity_risk": toxicity_score > 0.80,
    }
```

**Tests**: Known injection corpus, benign queries that should pass.

### Layer 4: Semantic Analysis

**Purpose**: Detect intent-level threats that bypass pattern matching.

Checks:
- Data exfiltration intent: asking to send data to external URLs.
- Privilege escalation: asking to modify permissions or access controls.
- System prompt extraction: asking to repeat or reveal instructions.

```python
EXFIL_KEYWORDS = ["send to", "post to", "email to", "upload to", "webhook"]
ESCALATION_KEYWORDS = ["admin", "root", "sudo", "bypass", "override"]
EXTRACTION_KEYWORDS = ["system prompt", "instructions", "repeat your", "what are your rules"]

def semantic_check(text: str) -> list[str]:
    text_lower = text.lower()
    flags = []
    if any(kw in text_lower for kw in EXFIL_KEYWORDS):
        flags.append("potential_exfiltration")
    if any(kw in text_lower for kw in ESCALATION_KEYWORDS):
        flags.append("potential_escalation")
    if any(kw in text_lower for kw in EXTRACTION_KEYWORDS):
        flags.append("potential_extraction")
    return flags
```

**Tests**: Known attack phrases, benign queries with similar words.

### Layer 5: Tool Guardrails

**Purpose**: Validate and constrain tool execution.

Per-tool rules:
- **SQL tools**: Allow only SELECT/WITH. Block mutation keywords.
- **Code execution**: Sandbox with network=none, memory limit, timeout.
- **File access**: No path traversal (`..`), whitelist allowed directories.
- **API calls**: Rate limit per tool, per user.

```python
SQL_BLOCKED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

def validate_sql(query: str) -> bool:
    if SQL_BLOCKED.search(query):
        raise ValueError(f"Mutation SQL blocked: {query[:100]}")
    if not query.strip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("Query must start with SELECT or WITH")
    return True
```

**Tests**: All blocked keywords, valid SELECT queries, edge cases (comments, subqueries).

### Layer 6: Output Guardrails

**Purpose**: Sanitize agent output before returning to user.

Checks:
- **PII scrubbing**: Detect and mask emails, phone numbers, SSNs, credit cards.
- **Schema validation**: Output matches expected response model.
- **System prompt leak**: Output doesn't contain system prompt fragments.
- **Grounding check**: Claims are supported by tool results.

```python
import re

PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
}

def scrub_pii(text: str) -> str:
    for name, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[{name.upper()}_REDACTED]", text)
    return text
```

**Tests**: Strings with PII, clean strings, edge cases (partial matches).

## Generated File Structure

```
guardrails/
├── __init__.py
├── input.py          # Layers 1-4: schema, content filter, ML, semantic
├── output.py         # Layer 6: PII, schema, grounding
├── tool_guards.py    # Layer 5: per-tool validation
└── tests/
    ├── test_input.py
    ├── test_output.py
    └── test_tool_guards.py
```

## Integration Pattern

Wire the pipeline into the agent loop:

```python
async def handle_request(query: str) -> str:
    # Input pipeline (layers 1-4)
    validated = AgentInput(query=query)           # Layer 1
    injections = check_injection(validated.query)  # Layer 2
    if injections:
        return "Request blocked: suspicious content detected."
    flags = semantic_check(validated.query)         # Layer 4
    if "potential_exfiltration" in flags:
        return "Request blocked: data exfiltration attempt."

    # Agent processing with tool guardrails (layer 5)
    result = await agent.run(validated.query)

    # Output pipeline (layer 6)
    result.answer = scrub_pii(result.answer)
    return result.answer
```

## Test Coverage Requirements

Each guardrail layer must have:
- At least 5 positive tests (should block).
- At least 5 negative tests (should pass).
- Edge case tests (unicode, empty strings, max-length inputs).
- Performance test (< 10ms per check for layers 1-2, < 100ms for layer 3).
