"""A broken command must not end the REPL session; /bench must work from a wheel install;
/status must not present refuted or unmeasured constants as invariants."""
import os

import pytest

from osiris_cli import osiris_repl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_failing_command_reports_and_session_continues(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))

    def boom(state, line):
        raise AttributeError("module 'osiris_termux_console' has no attribute '_intent'")

    monkeypatch.setattr(osiris_repl, "dispatch_command", boom)
    osiris_repl.safe_dispatch(None, "/intent")          # must not raise
    out = capsys.readouterr().out
    assert "'/intent' failed: AttributeError" in out and "session continues" in out
    log = tmp_path / ".osiris" / "logs" / "repl_errors.log"
    assert "Traceback" in log.read_text()


def test_repl_loop_uses_the_guard():
    src = open(osiris_repl.__file__, encoding="utf-8").read()
    loop = src[src.index("def boot_repl"):]
    assert "dispatch_command(SESSION" not in loop, "the input loop must call safe_dispatch"


def test_bench_tasks_ship_in_the_wheel():
    text = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert '"bench_tasks"' in text and "[tool.setuptools.package-data]" in text
    # no __init__.py: every .py under bench_tasks is hashed into suite_sha256, and adding one
    # would make all earlier bench evidence non-comparable
    assert not os.path.exists(os.path.join(ROOT, "bench_tasks", "__init__.py"))


def test_bench_task_listing_skips_package_files():
    import osiris_bench
    names = [t["id"] if isinstance(t, dict) and "id" in t else t for t in osiris_bench.load_tasks()]
    assert names and not any(str(n).startswith(("_", ".")) for n in names)


def test_console_bench_argv_survives_missing_tasks(monkeypatch, tmp_path):
    otc = osiris_repl.otc
    if otc is None:
        pytest.skip("console not importable")
    monkeypatch.setattr(otc.os.path, "abspath", lambda p: str(tmp_path / "x.py") if p == otc.__file__ else os.path.abspath(p))
    otc._bench_argv("/bench")                     # no FileNotFoundError when bench_tasks is absent


def test_status_does_not_call_crsm_constants_invariants():
    src = open(osiris_repl.__file__, encoding="utf-8").read()
    block = src[src.index("STATUS DASHBOARD"):src.index("Evidence Events")]
    assert "Invariant" not in block and " kg" not in block
    assert "not established" in block
