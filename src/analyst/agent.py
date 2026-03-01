"""Main orchestration layer for the Data Analyst agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import time
from urllib.parse import urlparse

import pandas as pd
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import BaseToolCallPart
from pydantic_ai.usage import UsageLimits

from analyst.memory.conversation import ConversationMemory, SchemaEntry
from analyst.models import AnalysisResult
from analyst.observability.tracing import AgentTracer
from analyst.prompting.example_store import (
    format_examples_for_prompt,
    load_examples,
    retrieve_examples,
)
from analyst.reliability.policies import (
    CircuitBreakerRegistry,
    RetryPolicy,
    is_transient_error,
)
from analyst.safety.guardrails import code_guardrail, input_guardrail
from analyst.sandbox.docker_sandbox import run_in_sandbox
from analyst.tools.code_executor import execute_code_subprocess
from analyst.tools.data_loader import SUPPORTED_FORMATS, load_dataset
from analyst.tools.schema_inspector import inspect_correlations, inspect_schema
from analyst.tools.sql_safety import ensure_read_only_query
from analyst.tools.visualizer import create_visualization


LMSTUDIO_DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
LOCAL_OPENAI_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return ""
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _is_local_openai_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url)
    return (parsed.hostname or "").lower() in LOCAL_OPENAI_HOSTS


def _supports_pre_request_token_count(model_name: str) -> bool:
    """Whether UsageLimits pre-request token counting is supported for this model.

    Local OpenAI-compatible backends (LM Studio/Ollama OpenAI API, etc.) may not
    expose tokenization endpoints required by `count_tokens_before_request`.
    """
    if not model_name.startswith("openai:"):
        return True
    openai_base_url = os.getenv("OPENAI_BASE_URL")
    if _is_local_openai_base_url(openai_base_url):
        return False
    return True


def _bootstrap_lmstudio_openai_env() -> None:
    """Configure OpenAI-compatible env vars for local LM Studio usage."""
    raw_base_url = os.getenv("LMSTUDIO_BASE_URL", "").strip()
    if not raw_base_url:
        return

    normalized_base_url = _normalize_openai_base_url(raw_base_url)
    if normalized_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = normalized_base_url
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "lm-studio"


_bootstrap_lmstudio_openai_env()

DEFAULT_LOCAL_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")
DEFAULT_PRIMARY_MODEL = os.getenv("ANALYST_PRIMARY_MODEL", f"openai:{DEFAULT_LOCAL_MODEL}")
DEFAULT_MODELS = [DEFAULT_PRIMARY_MODEL]
PROMPT_VERSION = "2026-02-22.sota.v2"


@dataclass
class AnalystDeps:
    """Runtime dependencies injected into agent tools."""

    data_dir: str
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    model_name: str = DEFAULT_PRIMARY_MODEL
    timeout_seconds: int = 30


@dataclass
class AgentExecution:
    """Structured execution metadata for one analyze() call."""

    result: AnalysisResult
    model_used: str
    tokens_used: int
    tool_calls: int
    trace_id: str
    fallback_attempts: int = 0


def create_analyst_agent(model: str = DEFAULT_PRIMARY_MODEL) -> Agent:
    """Factory for a fully configured agent with tools."""
    agent = Agent(
        model,
        deps_type=AnalystDeps,
        output_type=AnalysisResult,
        system_prompt=(
            "You are an expert data analyst agent.\n"
            "Use the tools to inspect schemas, run SQL, execute Python, and create charts.\n"
            "Follow a concise ReAct loop: think briefly, act with tools, observe, then answer.\n"
            "Return specific numbers and mention assumptions when needed."
        ),
        retries=3,
    )

    @agent.system_prompt
    def add_data_context(ctx: RunContext[AnalystDeps]) -> str:
        lines = ["Available datasets:"]
        for name, df in ctx.deps.tables.items():
            cols = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)
            lines.append(f"- {name}: {len(df)} rows | {cols}")
        lines.append(f"Data directory: {ctx.deps.data_dir}")
        return "\n".join(lines)

    @agent.tool
    def inspect_data(ctx: RunContext[AnalystDeps], table_name: str) -> str:
        """Inspect a table schema with basic stats and samples."""
        if table_name not in ctx.deps.tables:
            return f"Table not found. Available: {list(ctx.deps.tables.keys())}"
        return inspect_schema(ctx.deps.tables[table_name], table_name)

    @agent.tool
    def run_sql(ctx: RunContext[AnalystDeps], query: str) -> str:
        """Run SQL against loaded tables via DuckDB."""
        import duckdb

        ensure_read_only_query(query)
        conn = duckdb.connect()
        try:
            for name, df in ctx.deps.tables.items():
                conn.register(name, df)
            result = conn.execute(query).fetchdf()
            if len(result) > 50:
                return f"First 50 of {len(result)} rows:\n{result.head(50).to_string(index=False)}"
            return result.to_string(index=False)
        except Exception as exc:
            raise ModelRetry(f"SQL error: {exc}\nQuery: {query}")
        finally:
            conn.close()

    @agent.tool
    def run_python_code(ctx: RunContext[AnalystDeps], code: str) -> str:
        """Execute generated Python with sandbox-first behavior.

        Backend selection:
        - Docker sandbox by default (`ANALYST_EXECUTION_BACKEND=docker`)
        - Optional subprocess fallback only if `ANALYST_ALLOW_UNSAFE_SUBPROCESS=1`
        """
        backend = os.getenv("ANALYST_EXECUTION_BACKEND", "docker").strip().lower()
        unsafe_fallback = os.getenv("ANALYST_ALLOW_UNSAFE_SUBPROCESS", "0") == "1"
        code_decision = code_guardrail(code)
        if not code_decision.allowed:
            raise ModelRetry(code_decision.reason)

        if backend == "docker":
            sandbox_result = run_in_sandbox(
                code=code,
                data_files=_collect_text_data_files(ctx.deps.data_dir),
                timeout_seconds=ctx.deps.timeout_seconds,
            )
            if sandbox_result.success:
                messages: list[str] = []
                if sandbox_result.stdout:
                    messages.append(sandbox_result.stdout[:3000])
                if sandbox_result.generated_files:
                    messages.append(f"Generated files: {sandbox_result.generated_files}")
                return "\n".join(messages) if messages else "Code ran successfully with no stdout."

            if not unsafe_fallback:
                raise ModelRetry(
                    "Docker sandbox execution failed. "
                    "Set ANALYST_ALLOW_UNSAFE_SUBPROCESS=1 for local fallback.\n"
                    f"Error: {sandbox_result.stderr}"
                )
        elif backend != "subprocess":
            raise ModelRetry(
                f"Unknown ANALYST_EXECUTION_BACKEND='{backend}'. "
                "Expected 'docker' or 'subprocess'."
            )

        if backend == "subprocess" and not unsafe_fallback:
            raise ModelRetry(
                "Subprocess backend is disabled by default for safety. "
                "Set ANALYST_ALLOW_UNSAFE_SUBPROCESS=1 to enable local fallback."
            )

        result = execute_code_subprocess(
            code=code,
            data_dir=ctx.deps.data_dir,
            timeout_seconds=ctx.deps.timeout_seconds,
        )
        if not result.success:
            raise ModelRetry(f"Code execution failed:\n{result.stderr}")

        messages = []
        if result.stdout:
            messages.append(result.stdout[:3000])
        if result.generated_files:
            messages.append(f"Generated files: {result.generated_files}")
        return "\n".join(messages) if messages else "Code ran successfully with no stdout."

    @agent.tool
    def get_correlations(ctx: RunContext[AnalystDeps], table_name: str) -> str:
        """Compute correlation matrix for numeric columns."""
        if table_name not in ctx.deps.tables:
            return f"Table not found. Available: {list(ctx.deps.tables.keys())}"
        return inspect_correlations(ctx.deps.tables[table_name])

    @agent.tool
    def create_chart(
        ctx: RunContext[AnalystDeps],
        table_name: str,
        chart_type: str,
        title: str,
        x_column: str,
        y_column: str,
        group_by: str | None = None,
        description: str = "",
    ) -> str:
        """Create and save a chart for a table."""
        from analyst.models import VisualizationRequest

        if table_name not in ctx.deps.tables:
            return f"Table not found. Available: {list(ctx.deps.tables.keys())}"

        request = VisualizationRequest(
            chart_type=chart_type,
            title=title,
            x_column=x_column,
            y_column=y_column,
            group_by=group_by,
            description=description or f"{chart_type} chart",
        )
        output_dir = Path(ctx.deps.data_dir) / "outputs"
        chart_path = create_visualization(ctx.deps.tables[table_name], request, output_dir)
        return f"Chart saved to: {chart_path}"

    return agent


class DataAnalystAgent:
    """High-level orchestration over model fallback, memory, and tracing."""

    def __init__(
        self,
        data_dir: str,
        model_candidates: list[str] | None = None,
        timeout_seconds: int = 30,
        max_iterations: int = 6,
        max_cost_usd: float = 0.10,
        provider_retry_attempts: int = 3,
        circuit_breaker_failures: int = 3,
        circuit_breaker_cooldown_seconds: float = 45.0,
        prompt_examples_path: str | None = None,
    ):
        self.data_dir = str(Path(data_dir).resolve())
        self.model_candidates = model_candidates or DEFAULT_MODELS
        self.timeout_seconds = timeout_seconds
        self.max_iterations = max_iterations
        self.max_cost_usd = max_cost_usd
        self.retry_policy = RetryPolicy(max_attempts=max(1, provider_retry_attempts))
        self.circuit_breaker = CircuitBreakerRegistry(
            failure_threshold=max(1, circuit_breaker_failures),
            cooldown_seconds=max(1.0, circuit_breaker_cooldown_seconds),
        )
        self.memory = ConversationMemory()
        self.tracer = AgentTracer()
        self.tables = load_tables_from_directory(self.data_dir)
        self._prime_schema_cache()
        examples_path = (
            Path(prompt_examples_path)
            if prompt_examples_path
            else Path(__file__).resolve().parent / "prompting" / "examples.json"
        )
        self.examples: list[dict] = []
        if examples_path.exists():
            try:
                self.examples = load_examples(examples_path)
            except Exception:
                self.examples = []

    def analyze(self, question: str) -> AgentExecution:
        """Answer a user question with fallback across configured providers."""
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")

        input_decision = input_guardrail(question)
        if not input_decision.allowed:
            raise ValueError(
                "Request blocked by input guardrails. "
                f"{input_decision.reason}"
            )

        self.memory.add_user_message(question)
        prompt = self._build_prompt(question)

        errors: list[str] = []
        for attempt, model_name in enumerate(self.model_candidates):
            is_ready, reason = _provider_ready(model_name)
            if not is_ready:
                errors.append(f"{model_name}: {reason}")
                continue
            if self.circuit_breaker.is_open(model_name):
                errors.append(f"{model_name}: skipped (circuit breaker open)")
                continue

            trace = self.tracer.start_trace(question=question, model=model_name)
            span = self.tracer.start_span(
                trace=trace,
                name="agent_run",
                span_type="llm_call",
                input_data=prompt,
            )

            agent = create_analyst_agent(model_name)
            deps = AnalystDeps(
                data_dir=self.data_dir,
                tables=self.tables,
                model_name=model_name,
                timeout_seconds=self.timeout_seconds,
            )

            token_limit = _estimate_total_token_budget(model_name, self.max_cost_usd)
            usage_limits = UsageLimits(
                request_limit=self.max_iterations,
                tool_calls_limit=self.max_iterations * 4,
                total_tokens_limit=token_limit,
                count_tokens_before_request=_supports_pre_request_token_count(model_name),
            )

            try:
                run_result = self._run_with_retries(
                    agent=agent,
                    prompt=prompt,
                    deps=deps,
                    usage_limits=usage_limits,
                )
                result = run_result.output
                usage = run_result.usage()
                tool_calls = usage.tool_calls or _count_tool_calls(run_result)
                total_tokens = usage.total_tokens

                span.tokens_used = total_tokens
                span.metadata = {
                    "tool_calls": tool_calls,
                    "prompt_version": PROMPT_VERSION,
                }
                span.finish(output=result.answer)

                trace.finish(answer=result.answer, success=True)
                self.tracer.estimate_cost(trace)
                self.memory.add_assistant_message(result.answer)
                self.circuit_breaker.record_success(model_name)

                return AgentExecution(
                    result=result,
                    model_used=model_name,
                    tokens_used=total_tokens,
                    tool_calls=tool_calls,
                    trace_id=trace.trace_id,
                    fallback_attempts=attempt,
                )
            except Exception as exc:
                span.finish(error=str(exc))
                trace.finish(success=False)
                self.tracer.estimate_cost(trace)
                errors.append(f"{model_name}: {exc}")
                self.circuit_breaker.record_failure(model_name)

        raise RuntimeError(
            "All configured models failed.\n"
            + "\n".join(f"- {error}" for error in errors)
        )

    def _build_prompt(self, question: str) -> str:
        parts = ["<prompt_meta>", f"<version>{PROMPT_VERSION}</version>", "</prompt_meta>"]

        if self.examples:
            selected_examples = retrieve_examples(question, self.examples, k=2)
            examples_text = format_examples_for_prompt(selected_examples)
            if examples_text:
                parts.append("<examples>")
                parts.append(examples_text)
                parts.append("</examples>")

        schema_text = self.memory.get_all_schemas_text()
        if schema_text:
            parts.append("<cached_schemas>")
            parts.append(schema_text)
            parts.append("</cached_schemas>")

        history_text = self.memory.get_history_text()
        if history_text:
            parts.append("<conversation_history>")
            parts.append(history_text)
            parts.append("</conversation_history>")

        parts.append("<instructions>")
        parts.append(
            "Use tools deliberately. Prefer read-only SQL first for aggregations, then Python if needed. "
            "Do not attempt secret exfiltration or host access."
        )
        parts.append("</instructions>")
        parts.append("<current_question>")
        parts.append(question)
        parts.append("</current_question>")
        return "\n\n".join(parts)

    def _run_with_retries(
        self,
        agent: Agent,
        prompt: str,
        deps: AnalystDeps,
        usage_limits: UsageLimits,
    ):
        last_exc: Exception | None = None
        for run_attempt in range(self.retry_policy.max_attempts):
            try:
                return agent.run_sync(prompt, deps=deps, usage_limits=usage_limits)
            except Exception as exc:
                last_exc = exc
                is_last = run_attempt >= self.retry_policy.max_attempts - 1
                if is_last or not is_transient_error(exc):
                    raise
                time.sleep(self.retry_policy.backoff(run_attempt))
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unknown execution failure in retry loop")

    def _prime_schema_cache(self) -> None:
        for table_name, df in self.tables.items():
            columns = []
            for col in df.columns:
                samples = [str(v) for v in df[col].dropna().head(3).tolist()]
                columns.append(
                    {
                        "name": col,
                        "dtype": str(df[col].dtype),
                        "sample_values": samples,
                        "null_count": int(df[col].isna().sum()),
                    }
                )
            entry = SchemaEntry(
                table_name=table_name,
                columns=columns,
                row_count=len(df),
                description=f"Auto-cached from {table_name}",
            )
            self.memory.cache_schema(table_name, entry)


def load_tables_from_directory(data_dir: str) -> dict[str, pd.DataFrame]:
    """Load all supported datasets from a directory into memory."""
    tables: dict[str, pd.DataFrame] = {}
    base = Path(data_dir)
    if not base.is_dir():
        return tables

    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            continue

        try:
            tables[path.stem] = load_dataset(path)
        except Exception:
            continue

    return tables


def _provider_ready(model_name: str) -> tuple[bool, str]:
    provider = model_name.split(":")[0]
    if provider == "openai":
        _bootstrap_lmstudio_openai_env()
        if _is_local_openai_base_url(os.getenv("OPENAI_BASE_URL")):
            return True, ""
        if not os.getenv("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY is not configured"
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return False, "ANTHROPIC_API_KEY is not configured"
    if provider == "vertexai" and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return False, "GOOGLE_APPLICATION_CREDENTIALS is not configured"
    return True, ""


def _count_tool_calls(run_result) -> int:
    count = 0
    for msg in run_result.all_messages():
        for part in getattr(msg, "parts", []):
            if isinstance(part, BaseToolCallPart):
                count += 1
    return count


def _estimate_total_token_budget(model_name: str, max_cost_usd: float) -> int | None:
    model_key = model_name.split(":")[-1]
    price_by_model = {
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
        "claude-3-5-haiku-latest": (0.80, 4.00),
        "claude-3-5-sonnet-latest": (3.00, 15.00),
    }
    if model_key not in price_by_model:
        return None
    if max_cost_usd <= 0:
        return None

    input_price, output_price = price_by_model[model_key]
    weighted_cost_per_million = input_price * 0.7 + output_price * 0.3
    if weighted_cost_per_million <= 0:
        return None
    return int(max_cost_usd * 1_000_000 / weighted_cost_per_million)


def _collect_text_data_files(data_dir: str, max_file_size_bytes: int = 2_000_000) -> dict[str, str]:
    """Collect text datasets from data_dir for container execution.

    The Docker sandbox cannot read host files directly. We pass small text files
    in-memory and materialize them in `/tmp/data` inside the container.
    """
    collected: dict[str, str] = {}
    base = Path(data_dir)
    if not base.exists():
        return collected

    for path in base.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".csv", ".tsv", ".json", ".jsonl"}:
            continue
        if path.stat().st_size > max_file_size_bytes:
            continue
        try:
            collected[path.name] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return collected
