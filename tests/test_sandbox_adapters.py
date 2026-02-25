from __future__ import annotations

import base64

from analyst.sandbox import docker_sandbox, e2b_sandbox


def test_docker_wrap_code_includes_data_files() -> None:
    wrapped = docker_sandbox._wrap_code("print('ok')", data_files={"a.csv": "x,y\n1,2\n"})
    assert "a.csv" in wrapped
    assert "DATA_DIR = \"/tmp/data\"" in wrapped
    assert "print('ok')" in wrapped


def test_docker_extract_files_parses_markers() -> None:
    payload = base64.b64encode(b"hello").decode("utf-8")
    stdout = (
        "line before\n"
        f"__FILE_OUTPUT__:chart_0.png:{payload}:__END_FILE__\n"
        "line after"
    )
    files, clean = docker_sandbox._extract_files(stdout)

    assert len(files) == 1
    assert files[0].endswith("chart_0.png")
    assert "line before" in clean
    assert "line after" in clean


def test_docker_run_in_sandbox_handles_unavailable_client(monkeypatch) -> None:
    def _boom():
        raise RuntimeError("docker unavailable")

    monkeypatch.setattr("analyst.sandbox.docker_sandbox.docker.from_env", _boom)
    result = docker_sandbox.run_in_sandbox("print('x')", timeout_seconds=1)

    assert result.success is False
    assert "docker unavailable" in result.stderr.lower()


def test_e2b_run_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    result = e2b_sandbox.run_in_e2b("print('x')")
    assert result.success is False
    assert "E2B_API_KEY" in result.stderr


def test_e2b_run_missing_package(monkeypatch) -> None:
    monkeypatch.setenv("E2B_API_KEY", "dummy")
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "e2b_code_interpreter":
            raise ImportError("module missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    result = e2b_sandbox.run_in_e2b("print('x')")

    assert result.success is False
    assert "e2b-code-interpreter is not installed" in result.stderr
