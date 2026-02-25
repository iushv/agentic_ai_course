"""Sandbox exports."""

from analyst.sandbox.docker_sandbox import SandboxResult, run_in_sandbox
from analyst.sandbox.e2b_sandbox import E2BSandboxResult, run_in_e2b

__all__ = [
    "SandboxResult",
    "run_in_sandbox",
    "E2BSandboxResult",
    "run_in_e2b",
]
