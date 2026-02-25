"""Observability & Tracing — structured logging for agent runs.

Production agents need visibility into:
1. **What happened** — which tools were called, in what order
2. **How long it took** — latency per step and end-to-end
3. **How much it cost** — token usage and dollar cost
4. **What went wrong** — errors, retries, unexpected behavior

This module provides a lightweight tracing system that works without
external dependencies. For production, integrate with Logfire or Langfuse.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Span: a single unit of work (LLM call, tool call, etc.)
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single traced operation."""
    name: str
    span_type: str  # "llm_call", "tool_call", "agent_run", "code_execution"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float = 0.0

    # Metadata
    input_data: str = ""
    output_data: str = ""
    tokens_used: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Hierarchy
    parent_id: str | None = None
    span_id: str = ""

    def finish(self, output: str = "", error: str | None = None) -> None:
        """Mark span as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        if output:
            self.output_data = output[:2000]  # Truncate large outputs
        if error:
            self.error = error

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.span_type,
            "duration_ms": round(self.duration_ms, 1),
            "tokens": self.tokens_used,
            "error": self.error,
            "input": self.input_data[:200],
            "output": self.output_data[:200],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Trace: a collection of spans for one agent run
# ---------------------------------------------------------------------------


@dataclass
class Trace:
    """A complete trace of an agent run."""
    trace_id: str
    question: str
    model: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    spans: list[Span] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    success: bool = True
    final_answer: str = ""

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    def finish(self, answer: str = "", success: bool = True) -> None:
        self.end_time = time.time()
        self.final_answer = answer
        self.success = success
        self.total_tokens = sum(s.tokens_used for s in self.spans)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    @property
    def tool_calls(self) -> list[Span]:
        return [s for s in self.spans if s.span_type == "tool_call"]

    @property
    def llm_calls(self) -> list[Span]:
        return [s for s in self.spans if s.span_type == "llm_call"]

    @property
    def errors(self) -> list[Span]:
        return [s for s in self.spans if s.error]

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "question": self.question,
            "model": self.model,
            "duration_ms": round(self.duration_ms, 1),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "success": self.success,
            "answer": self.final_answer[:300],
            "spans": [s.to_dict() for s in self.spans],
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Trace: {self.trace_id}",
            f"  Question: {self.question[:80]}",
            f"  Model: {self.model}",
            f"  Duration: {self.duration_ms:.0f}ms",
            f"  Tokens: {self.total_tokens}",
            f"  Cost: ${self.total_cost_usd:.4f}",
            f"  Tool calls: {len(self.tool_calls)}",
            f"  LLM calls: {len(self.llm_calls)}",
            f"  Errors: {len(self.errors)}",
            f"  Success: {self.success}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# AgentTracer: collects traces across multiple runs
# ---------------------------------------------------------------------------


# Per-million-token pricing: (input, output)
MODEL_PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
}


class AgentTracer:
    """Collects and analyzes traces from agent runs."""

    def __init__(self, model_pricing: dict[str, tuple[float, float]] | None = None):
        self.traces: list[Trace] = []
        self.model_pricing = model_pricing or MODEL_PRICING
        self._counter = 0

    def start_trace(self, question: str, model: str = "") -> Trace:
        """Begin tracing a new agent run."""
        self._counter += 1
        trace = Trace(
            trace_id=f"trace_{self._counter:04d}",
            question=question,
            model=model,
        )
        self.traces.append(trace)
        return trace

    def start_span(
        self,
        trace: Trace,
        name: str,
        span_type: str,
        input_data: str = "",
    ) -> Span:
        """Start a new span within a trace."""
        span = Span(
            name=name,
            span_type=span_type,
            input_data=input_data[:2000],
            span_id=f"{trace.trace_id}_span_{len(trace.spans):02d}",
        )
        trace.add_span(span)
        return span

    def estimate_cost(self, trace: Trace) -> float:
        """Estimate cost based on token usage and model pricing."""
        model_key = trace.model.split(":")[-1] if ":" in trace.model else trace.model
        input_price, output_price = self.model_pricing.get(model_key, (0, 0))

        total_tokens = trace.total_tokens
        # Rough split: 70% input, 30% output
        cost = (total_tokens * 0.7 / 1e6 * input_price +
                total_tokens * 0.3 / 1e6 * output_price)
        trace.total_cost_usd = cost
        return cost

    # ----- Analytics -----

    def get_stats(self) -> dict:
        """Aggregate statistics across all traces."""
        if not self.traces:
            return {"total_runs": 0}

        durations = [t.duration_ms for t in self.traces]
        tokens = [t.total_tokens for t in self.traces]
        tool_counts = [len(t.tool_calls) for t in self.traces]
        costs = [t.total_cost_usd for t in self.traces]

        return {
            "total_runs": len(self.traces),
            "success_rate": sum(1 for t in self.traces if t.success) / len(self.traces),
            "latency": {
                "p50": sorted(durations)[len(durations) // 2],
                "p95": sorted(durations)[int(len(durations) * 0.95)],
                "mean": sum(durations) / len(durations),
            },
            "tokens": {
                "mean": sum(tokens) / len(tokens),
                "total": sum(tokens),
            },
            "tool_calls": {
                "mean": sum(tool_counts) / len(tool_counts),
            },
            "cost": {
                "total": sum(costs),
                "mean": sum(costs) / len(costs),
            },
        }

    def get_slowest(self, n: int = 5) -> list[Trace]:
        """Get the N slowest traces."""
        return sorted(self.traces, key=lambda t: t.duration_ms, reverse=True)[:n]

    def get_failures(self) -> list[Trace]:
        """Get all failed traces."""
        return [t for t in self.traces if not t.success]

    def get_error_summary(self) -> dict[str, int]:
        """Categorize errors across all traces."""
        errors: dict[str, int] = {}
        for trace in self.traces:
            for span in trace.errors:
                err_type = span.error.split(":")[0] if span.error else "Unknown"
                errors[err_type] = errors.get(err_type, 0) + 1
        return errors

    # ----- Persistence -----

    def save(self, path: str | Path) -> None:
        """Save all traces to JSON."""
        data = [t.to_dict() for t in self.traces]
        Path(path).write_text(json.dumps(data, indent=2))

    def dashboard(self) -> str:
        """Generate a text dashboard of agent performance."""
        stats = self.get_stats()
        if stats["total_runs"] == 0:
            return "No traces recorded."

        lines = [
            "=" * 50,
            "        AGENT PERFORMANCE DASHBOARD",
            "=" * 50,
            f"  Total runs:    {stats['total_runs']}",
            f"  Success rate:  {stats['success_rate']:.0%}",
            "",
            "  Latency:",
            f"    P50:  {stats['latency']['p50']:.0f}ms",
            f"    P95:  {stats['latency']['p95']:.0f}ms",
            f"    Mean: {stats['latency']['mean']:.0f}ms",
            "",
            "  Tokens:",
            f"    Mean per run: {stats['tokens']['mean']:.0f}",
            f"    Total:        {stats['tokens']['total']}",
            "",
            "  Tool calls:",
            f"    Mean per run: {stats['tool_calls']['mean']:.1f}",
            "",
            "  Cost:",
            f"    Total:    ${stats['cost']['total']:.4f}",
            f"    Per run:  ${stats['cost']['mean']:.4f}",
            "=" * 50,
        ]
        return "\n".join(lines)
