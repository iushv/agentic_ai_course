"""Optional E2B-backed sandbox adapter.

This file keeps the same input/output style as the local sandbox so the agent
can switch execution backends with minimal orchestration changes.
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class E2BSandboxResult:
    """Result object for E2B sandbox execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    generated_files: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


def run_in_e2b(
    code: str,
    timeout_seconds: int = 60,
) -> E2BSandboxResult:
    """Run code in E2B's cloud sandbox.

    Requires:
    - `e2b-code-interpreter` installed (`uv sync --extra cloud`)
    - `E2B_API_KEY` set in environment
    """
    if not os.getenv("E2B_API_KEY"):
        return E2BSandboxResult(
            success=False,
            stderr="E2B_API_KEY is not set. Configure it in your environment first.",
        )

    try:
        from e2b_code_interpreter import Sandbox  # type: ignore
    except Exception as exc:  # pragma: no cover - environment-dependent
        return E2BSandboxResult(
            success=False,
            stderr=(
                "e2b-code-interpreter is not installed. "
                "Install with: uv sync --extra cloud"
                f" ({exc})"
            ),
        )

    start = time.time()
    sandbox = None
    try:
        sandbox = Sandbox(timeout=timeout_seconds)
        execution = sandbox.run_code(code)
        generated_files = _download_files_if_any(sandbox)

        elapsed = (time.time() - start) * 1000
        return E2BSandboxResult(
            success=execution.error is None,
            stdout=(execution.stdout or "").strip(),
            stderr=(execution.error or "").strip(),
            generated_files=generated_files,
            execution_time_ms=round(elapsed, 2),
        )
    except Exception as exc:  # pragma: no cover - environment-dependent
        elapsed = (time.time() - start) * 1000
        return E2BSandboxResult(
            success=False,
            stderr=f"E2B execution error: {exc}",
            execution_time_ms=round(elapsed, 2),
        )
    finally:
        if sandbox is not None:
            try:
                sandbox.kill()
            except Exception:
                pass


def _download_files_if_any(sandbox) -> list[str]:
    """Best-effort artifact collection from `/home/user` in E2B."""
    output_dir = Path(tempfile.gettempdir()) / "analyst_e2b_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []

    try:
        files = sandbox.files.list("/home/user")
    except Exception:
        return downloaded

    for file_entry in files:
        name = getattr(file_entry, "name", "")
        if not name.endswith((".png", ".jpg", ".jpeg", ".svg", ".csv", ".html")):
            continue

        local_path = output_dir / name
        try:
            content = sandbox.files.read(f"/home/user/{name}", format="bytes")
            local_path.write_bytes(content)
            downloaded.append(str(local_path))
        except Exception:
            continue

    return downloaded
