"""Reliability primitives for model execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
import time


@dataclass
class RetryPolicy:
    """Simple exponential backoff retry policy."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.4
    max_delay_seconds: float = 4.0
    jitter_seconds: float = 0.2

    def backoff(self, attempt_number: int) -> float:
        """Return delay for zero-based attempt index."""
        exp = self.base_delay_seconds * (2 ** attempt_number)
        bounded = min(exp, self.max_delay_seconds)
        jitter = random.uniform(0.0, self.jitter_seconds)
        return bounded + jitter


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0


@dataclass
class CircuitBreakerRegistry:
    """Per-provider circuit breaker state."""

    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    states: dict[str, CircuitState] = field(default_factory=dict)

    def is_open(self, provider_key: str, now: float | None = None) -> bool:
        now_ts = now if now is not None else time.time()
        state = self.states.get(provider_key)
        return bool(state and state.opened_until > now_ts)

    def record_success(self, provider_key: str) -> None:
        state = self.states.setdefault(provider_key, CircuitState())
        state.failures = 0
        state.opened_until = 0.0

    def record_failure(self, provider_key: str, now: float | None = None) -> None:
        now_ts = now if now is not None else time.time()
        state = self.states.setdefault(provider_key, CircuitState())
        state.failures += 1
        if state.failures >= self.failure_threshold:
            state.opened_until = now_ts + self.cooldown_seconds


def is_transient_error(exc: Exception) -> bool:
    text = str(exc).lower()
    transient_markers = (
        "timeout",
        "temporarily unavailable",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "504",
        "connection reset",
        "connection aborted",
        "network",
    )
    return any(marker in text for marker in transient_markers)
