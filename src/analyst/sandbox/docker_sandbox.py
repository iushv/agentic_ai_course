"""Docker-based sandbox for executing LLM-generated Python code.

SECURITY: Never run LLM-generated code on the host machine.
This sandbox runs code in an isolated Docker container with:
- No network access
- Memory and CPU limits
- Timeout enforcement
- Read-only filesystem (except /tmp)
- No access to host filesystem

For production, consider E2B (cloud sandbox) — see e2b_sandbox.py.
"""

from __future__ import annotations

import base64
import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import docker
from docker.errors import ImageNotFound


SANDBOX_IMAGE = "analyst-sandbox"
DOCKERFILE_CONTENT = """\
FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas numpy matplotlib seaborn plotly \
    scipy scikit-learn

# Create non-root user for safety
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox

# Default command: run a Python script
CMD ["python", "/tmp/script.py"]
"""


@dataclass
class SandboxResult:
    """Result of running code in the sandbox."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    generated_files: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    exit_code: int = 0


def ensure_sandbox_image(client: docker.DockerClient) -> None:
    """Build the sandbox Docker image if it doesn't exist."""
    try:
        client.images.get(SANDBOX_IMAGE)
    except ImageNotFound:
        print(f"Building sandbox image '{SANDBOX_IMAGE}'...")
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text(DOCKERFILE_CONTENT)
            client.images.build(
                path=tmpdir,
                tag=SANDBOX_IMAGE,
                rm=True,
            )
        print("Sandbox image built successfully.")


def run_in_sandbox(
    code: str,
    data_files: dict[str, str] | None = None,
    timeout_seconds: int = 30,
    memory_limit: str = "512m",
    cpu_quota: int = 50000,  # 50% of one CPU
) -> SandboxResult:
    """Execute Python code in an isolated Docker container.

    Args:
        code: Python code to execute.
        data_files: Dict of {filename: csv_content} to make available in /tmp/data/.
        timeout_seconds: Max execution time.
        memory_limit: Docker memory limit (e.g., '512m', '1g').
        cpu_quota: CPU quota in microseconds per 100ms period.

    Returns:
        SandboxResult with stdout, stderr, generated files, and timing.
    """
    start_time = time.time()
    try:
        client = docker.from_env()
        ensure_sandbox_image(client)

        # Wrap user code with output capture and file saving
        wrapped_code = _wrap_code(code, data_files=data_files)

        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command=["python", "-c", wrapped_code],
            detach=True,
            mem_limit=memory_limit,
            cpu_quota=cpu_quota,
            network_disabled=True,  # No network access
            read_only=True,
            tmpfs={"/tmp": "size=100m"},
            environment={
                "MPLBACKEND": "Agg",  # Non-interactive matplotlib backend
            },
        )

        # Wait for completion with timeout
        result = container.wait(timeout=timeout_seconds)
        exit_code = result.get("StatusCode", -1)

        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

        # Extract generated files (base64-encoded in stdout markers)
        generated_files, clean_stdout = _extract_files(stdout)

        elapsed = (time.time() - start_time) * 1000

        return SandboxResult(
            success=exit_code == 0,
            stdout=clean_stdout.strip(),
            stderr=stderr.strip(),
            generated_files=generated_files,
            execution_time_ms=round(elapsed, 2),
            exit_code=exit_code,
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return SandboxResult(
            success=False,
            stderr=f"Sandbox error: {e}",
            execution_time_ms=round(elapsed, 2),
            exit_code=-1,
        )

    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass


def _wrap_code(code: str, data_files: dict[str, str] | None = None) -> str:
    """Wrap user code with file output capture.

    Any matplotlib figures are saved and base64-encoded to stdout
    so we can extract them from the container.
    """
    data_files_literal = json.dumps(data_files or {})
    return f"""\
import sys
import os
import base64
import io

# Make /tmp writable for outputs
os.chdir('/tmp')

# Write provided input files to /tmp/data
os.makedirs('/tmp/data', exist_ok=True)
_DATA_FILES = {data_files_literal}
for _name, _content in _DATA_FILES.items():
    with open(f"/tmp/data/{{_name}}", "w", encoding="utf-8") as _fp:
        _fp.write(_content)
DATA_DIR = "/tmp/data"

# --- User code begins ---
{code}
# --- User code ends ---

# Save any open matplotlib figures
try:
    import matplotlib.pyplot as plt
    for i, fig_num in enumerate(plt.get_fignums()):
        fig = plt.figure(fig_num)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        print(f"__FILE_OUTPUT__:chart_{{i}}.png:{{encoded}}:__END_FILE__")
    plt.close('all')
except ImportError:
    pass
"""


def _extract_files(stdout: str) -> tuple[list[str], str]:
    """Extract base64-encoded files from stdout markers."""
    generated_files = []
    clean_lines = []

    for line in stdout.split("\n"):
        if line.startswith("__FILE_OUTPUT__:") and line.endswith(":__END_FILE__"):
            parts = line.split(":")
            if len(parts) >= 3:
                filename = parts[1]
                b64_data = parts[2]
                # Save to a temp location
                output_dir = Path(tempfile.gettempdir()) / "analyst_outputs"
                output_dir.mkdir(exist_ok=True)
                filepath = output_dir / filename
                filepath.write_bytes(base64.b64decode(b64_data))
                generated_files.append(str(filepath))
        else:
            clean_lines.append(line)

    return generated_files, "\n".join(clean_lines)
