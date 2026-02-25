"""Evaluation Harness — measure agent quality systematically.

Three pillars of agent evaluation:

1. **Correctness** — Does the agent produce the right answer?
   - Deterministic: compare output to expected value
   - LLM-as-judge: have a second LLM grade the response

2. **Safety** — Does the agent avoid dangerous behavior?
   - No harmful code patterns
   - No data exfiltration attempts
   - Stays within tool call budget

3. **Cost efficiency** — How many tokens/dollars per query?
   - Token usage tracking
   - Tool call count
   - Latency
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    """A single evaluation test case."""
    question: str
    expected_answer: str  # What the correct answer contains (substring match)
    expected_keywords: list[str] = field(default_factory=list)  # Must appear in answer
    difficulty: str = "medium"  # easy, medium, hard
    category: str = "general"  # general, aggregation, comparison, trend, etc.
    max_tool_calls: int = 10


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""
    case: EvalCase
    agent_answer: str
    correct: bool
    keyword_matches: dict[str, bool] = field(default_factory=dict)
    tool_calls: int = 0
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: str | None = None
    llm_judge_score: float | None = None  # 0-1 from LLM judge


class EvalSummary(BaseModel):
    """Summary of an evaluation run."""
    total_cases: int
    passed: int
    failed: int
    errors: int
    accuracy: float = Field(description="Fraction of correct answers")
    avg_latency_ms: float
    avg_tokens: float
    avg_tool_calls: float
    total_cost_usd: float
    by_category: dict[str, dict] = Field(default_factory=dict)
    by_difficulty: dict[str, dict] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


class EvalHarness:
    """Runs evaluation suites and tracks results."""

    def __init__(self, model_pricing: dict[str, tuple[float, float]] | None = None):
        self.results: list[EvalResult] = []
        self.model_pricing = model_pricing or {
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4o": (2.50, 10.00),
            "claude-3-5-haiku-latest": (0.80, 4.00),
        }

    def run_case(
        self,
        case: EvalCase,
        agent_fn: Callable[[str], tuple[str, int, int]],
    ) -> EvalResult:
        """Run a single eval case.

        agent_fn should accept a question string and return:
            (answer: str, tool_calls: int, tokens: int)
        """
        start = time.time()
        try:
            answer, tool_calls, tokens = agent_fn(case.question)
            latency = (time.time() - start) * 1000

            # Check correctness: expected answer substring match
            correct = case.expected_answer.lower() in answer.lower()

            # Check keyword matches
            keyword_matches = {
                kw: kw.lower() in answer.lower()
                for kw in case.expected_keywords
            }
            # All keywords must match for the case to pass
            if case.expected_keywords and not all(keyword_matches.values()):
                correct = False

            result = EvalResult(
                case=case,
                agent_answer=answer,
                correct=correct,
                keyword_matches=keyword_matches,
                tool_calls=tool_calls,
                tokens_used=tokens,
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            result = EvalResult(
                case=case,
                agent_answer="",
                correct=False,
                latency_ms=latency,
                error=str(e),
            )

        self.results.append(result)
        return result

    def run_suite(
        self,
        cases: list[EvalCase],
        agent_fn: Callable[[str], tuple[str, int, int]],
        verbose: bool = True,
        reset: bool = True,
    ) -> EvalSummary:
        """Run all cases and produce a summary."""
        if reset:
            self.results = []

        for i, case in enumerate(cases, 1):
            if verbose:
                print(f"  [{i}/{len(cases)}] {case.question[:60]}...", end=" ")
            result = self.run_case(case, agent_fn)
            if verbose:
                status = "PASS" if result.correct else ("ERROR" if result.error else "FAIL")
                print(f"[{status}] {result.latency_ms:.0f}ms")

        return self.summarize()

    def summarize(self, model_name: str = "gpt-4o-mini") -> EvalSummary:
        """Produce a summary of all results."""
        if not self.results:
            return EvalSummary(
                total_cases=0, passed=0, failed=0, errors=0,
                accuracy=0, avg_latency_ms=0, avg_tokens=0,
                avg_tool_calls=0, total_cost_usd=0,
            )

        passed = sum(1 for r in self.results if r.correct)
        errors = sum(1 for r in self.results if r.error)
        failed = len(self.results) - passed - errors

        # Cost calculation
        input_price, output_price = self.model_pricing.get(model_name, (0, 0))
        total_tokens = sum(r.tokens_used for r in self.results)
        # Rough split: 70% input, 30% output
        est_cost = (total_tokens * 0.7 / 1e6 * input_price +
                    total_tokens * 0.3 / 1e6 * output_price)

        # Group by category
        by_category: dict[str, dict] = {}
        for r in self.results:
            cat = r.case.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if r.correct:
                by_category[cat]["passed"] += 1

        # Group by difficulty
        by_difficulty: dict[str, dict] = {}
        for r in self.results:
            diff = r.case.difficulty
            if diff not in by_difficulty:
                by_difficulty[diff] = {"total": 0, "passed": 0}
            by_difficulty[diff]["total"] += 1
            if r.correct:
                by_difficulty[diff]["passed"] += 1

        return EvalSummary(
            total_cases=len(self.results),
            passed=passed,
            failed=failed,
            errors=errors,
            accuracy=passed / len(self.results),
            avg_latency_ms=sum(r.latency_ms for r in self.results) / len(self.results),
            avg_tokens=total_tokens / len(self.results),
            avg_tool_calls=sum(r.tool_calls for r in self.results) / len(self.results),
            total_cost_usd=round(est_cost, 6),
            by_category=by_category,
            by_difficulty=by_difficulty,
        )

    @staticmethod
    def load_cases(path: str | Path) -> list[EvalCase]:
        """Load evaluation cases from a JSON file."""
        payload = json.loads(Path(path).read_text())
        if not isinstance(payload, list):
            raise ValueError("Evaluation dataset must be a JSON list")
        return [EvalCase(**item) for item in payload]

    def save_results(self, path: str | Path) -> None:
        """Save results to JSON for analysis."""
        data = []
        for r in self.results:
            data.append({
                "question": r.case.question,
                "expected": r.case.expected_answer,
                "agent_answer": r.agent_answer[:500],
                "correct": r.correct,
                "tool_calls": r.tool_calls,
                "tokens": r.tokens_used,
                "latency_ms": r.latency_ms,
                "category": r.case.category,
                "difficulty": r.case.difficulty,
                "error": r.error,
            })
        Path(path).write_text(json.dumps(data, indent=2))
