"""Code Executor Tool — runs LLM-generated Python in a sandbox.

This tool bridges the agent and the sandbox. It:
1. Receives generated code from the LLM
2. Injects dataset files into the sandbox
3. Runs the code in isolation
4. Returns results (stdout, errors, generated charts)

Supports two backends:
- Docker (local, free) — default
- subprocess (lightweight, less secure — for learning/dev only)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExecutionResult:
    """Result of code execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    generated_files: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


def execute_code_subprocess(
    code: str,
    data_dir: str | None = None,
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """Execute Python code in a subprocess.

    WARNING: This is NOT fully sandboxed. Use for development/learning only.
    For production, use Docker sandbox (docker_sandbox.py) or E2B.

    The code runs in a separate Python process with a timeout.
    Data files from data_dir are accessible via the injected DATA_DIR variable.
    """
    start_time = time.time()

    # Prepend data directory setup
    preamble = "import os, sys\n"
    if data_dir:
        preamble += f"DATA_DIR = '{data_dir}'\n"
    else:
        preamble += "DATA_DIR = '.'\n"

    # Create temp directory for outputs
    output_dir = Path(tempfile.mkdtemp(prefix="analyst_"))
    preamble += f"OUTPUT_DIR = '{output_dir}'\n"

    # Set matplotlib backend
    preamble += "os.environ['MPLBACKEND'] = 'Agg'\n"

    # Append chart saving
    postamble = """
# Auto-save any matplotlib figures
try:
    import matplotlib.pyplot as plt
    for i, fig_num in enumerate(plt.get_fignums()):
        fig = plt.figure(fig_num)
        save_path = os.path.join(OUTPUT_DIR, f'chart_{i}.png')
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[saved chart: {save_path}]")
    plt.close('all')
except ImportError:
    pass
"""

    full_code = preamble + "\n" + code + "\n" + postamble

    # Write to temp file and execute
    script_path = output_dir / "script.py"
    script_path.write_text(full_code)

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(output_dir),
        )

        elapsed = (time.time() - start_time) * 1000

        # Collect generated files
        generated = _persist_generated_files(output_dir)

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            generated_files=generated,
            execution_time_ms=round(elapsed, 2),
        )

    except subprocess.TimeoutExpired:
        elapsed = (time.time() - start_time) * 1000
        return ExecutionResult(
            success=False,
            stderr=f"Execution timed out after {timeout_seconds}s",
            execution_time_ms=round(elapsed, 2),
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return ExecutionResult(
            success=False,
            stderr=f"Execution error: {e}",
            execution_time_ms=round(elapsed, 2),
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def _persist_generated_files(output_dir: Path) -> list[str]:
    """Copy generated artifacts to a stable temp location before cleanup."""
    persistent_dir = Path(tempfile.gettempdir()) / "analyst_outputs"
    persistent_dir.mkdir(parents=True, exist_ok=True)

    generated_paths: list[str] = []
    for file_path in output_dir.iterdir():
        if file_path.suffix not in {".png", ".jpg", ".svg", ".csv", ".html"}:
            continue
        unique_name = f"{int(time.time() * 1000)}_{file_path.name}"
        target = persistent_dir / unique_name
        shutil.copy2(file_path, target)
        generated_paths.append(str(target))
    return generated_paths
