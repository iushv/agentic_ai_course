"""Runtime guardrails for user input and generated code."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import re

from analyst.evaluation.metrics import code_safety_score


MAX_QUESTION_CHARS = 8_000

PROMPT_INJECTION_PATTERNS = [
    r"ignore (?:(?:all|any|the)\s+)?(?:previous|prior) instructions",
    r"reveal (your|the) (system|developer) prompt",
    r"act as (?:jailbreak|dan|root)",
    r"bypass (?:safety|guardrails|policy|restrictions)",
]

SENSITIVE_EXFIL_PATTERNS = [
    r"api[_ -]?key",
    r"secret",
    r"token",
    r"password",
    r"ssh key",
    r"\.env",
]


@dataclass
class GuardrailDecision:
    """Decision from a guardrail check."""

    allowed: bool
    reason: str = ""
    severity: str = "none"
    tags: list[str] = field(default_factory=list)


def input_guardrail(prompt: str) -> GuardrailDecision:
    """Check user input for obvious injection or exfiltration attempts."""
    if guardrails_disabled():
        return GuardrailDecision(allowed=True)

    if len(prompt) > MAX_QUESTION_CHARS:
        return GuardrailDecision(
            allowed=False,
            reason=f"Input too long ({len(prompt)} chars > {MAX_QUESTION_CHARS}).",
            severity="medium",
            tags=["length"],
        )

    lowered = prompt.lower()
    injection_hits = [
        pattern for pattern in PROMPT_INJECTION_PATTERNS if re.search(pattern, lowered)
    ]
    if injection_hits:
        return GuardrailDecision(
            allowed=False,
            reason="Potential prompt-injection attempt detected.",
            severity="high",
            tags=["prompt_injection", *injection_hits],
        )

    exfil_hits = [
        pattern for pattern in SENSITIVE_EXFIL_PATTERNS if re.search(pattern, lowered)
    ]
    if exfil_hits and any(word in lowered for word in ["show", "reveal", "print", "dump"]):
        return GuardrailDecision(
            allowed=False,
            reason="Potential sensitive-data exfiltration request detected.",
            severity="high",
            tags=["exfiltration", *exfil_hits],
        )

    return GuardrailDecision(allowed=True)


def code_guardrail(code: str) -> GuardrailDecision:
    """Check generated code before execution."""
    if guardrails_disabled():
        return GuardrailDecision(allowed=True)

    report = code_safety_score(code)
    if not report["safe"]:
        issues = ", ".join(report["issues"][:3])
        return GuardrailDecision(
            allowed=False,
            reason=f"Generated code failed safety checks: {issues}",
            severity="high",
            tags=["unsafe_code"],
        )

    return GuardrailDecision(allowed=True)


def guardrails_disabled() -> bool:
    return os.getenv("ANALYST_DISABLE_GUARDRAILS", "0") == "1"
