from __future__ import annotations

from analyst.reliability.policies import CircuitBreakerRegistry, RetryPolicy, is_transient_error


def test_retry_policy_backoff_increases() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=1.0, jitter_seconds=0.0)
    d0 = policy.backoff(0)
    d1 = policy.backoff(1)
    d2 = policy.backoff(2)
    assert d0 < d1 <= d2


def test_circuit_breaker_opens_after_failures() -> None:
    breaker = CircuitBreakerRegistry(failure_threshold=2, cooldown_seconds=100)
    key = "openai:gpt-4o-mini"
    assert breaker.is_open(key) is False
    breaker.record_failure(key, now=1000.0)
    assert breaker.is_open(key, now=1000.1) is False
    breaker.record_failure(key, now=1001.0)
    assert breaker.is_open(key, now=1001.1) is True


def test_is_transient_error() -> None:
    assert is_transient_error(Exception("429 rate limit exceeded")) is True
    assert is_transient_error(Exception("Timeout while calling provider")) is True
    assert is_transient_error(Exception("validation failed")) is False
