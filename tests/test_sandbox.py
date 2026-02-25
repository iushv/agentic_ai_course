from __future__ import annotations

from analyst.tools.code_executor import execute_code_subprocess


def test_execute_code_subprocess_success() -> None:
    code = """
import matplotlib.pyplot as plt
print("hello from sandbox")
plt.plot([1, 2, 3], [1, 4, 9])
"""

    result = execute_code_subprocess(code, timeout_seconds=10)

    assert result.success is True
    assert "hello from sandbox" in result.stdout
    assert len(result.generated_files) >= 1


def test_execute_code_subprocess_timeout() -> None:
    code = """
import time
while True:
    time.sleep(0.2)
"""

    result = execute_code_subprocess(code, timeout_seconds=1)

    assert result.success is False
    assert "timed out" in result.stderr.lower()
