"""Offline tests for the execution kernel. Child processes are small script files run via sys.executable."""

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

from osiris_cli import exec_kernel
from osiris_cli.exec_kernel import (
    CommandRequest,
    ExecJournal,
    ExecutionGrant,
    main,
    mint_grant,
    reset_session_approvals,
    run,
    verify_grant,
)


@pytest.fixture(autouse=True)
def _fresh_session():
    reset_session_approvals()
    yield
    reset_session_approvals()


def _ask_yes(prompt, cls):
    return True


def _ask_no(prompt, cls):
    return False


def _write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _alive(pid: int) -> bool:
    """True only if the pid is running and not a zombie."""
    try:
        with open(f"/proc/{pid}/stat", "r") as handle:
            state = handle.read().rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return False
    return state != "Z"


def test_child_does_not_receive_secret_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "do-not-leak")
    script = _write_script(tmp_path / "probe.py",
                           "import os\nprint('TOKEN_PRESENT' if 'QISKIT_IBM_TOKEN' in os.environ else 'TOKEN_ABSENT')\n")
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "ASK_APPROVED"
    assert "TOKEN_ABSENT" in res.stdout_view
    assert "do-not-leak" not in res.stdout_view
    assert "QISKIT_IBM_TOKEN" not in json.dumps(json.loads(journal.path.read_text().splitlines()[0])["body"])


def test_timeout_kills_the_grandchild_too(tmp_path):
    pid_file = tmp_path / "grandchild.pid"
    script = _write_script(tmp_path / "spawner.py", (
        "import subprocess, time, sys\n"
        "child = subprocess.Popen(['sleep', '30'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(30)\n"
    ))
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path), timeout_s=2),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.timed_out is True
    assert res.decision == "TIMEOUT"
    deadline = time.monotonic() + 5
    grandchild = int(pid_file.read_text())
    while _alive(grandchild) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(grandchild)
    assert res.duration_s < 10


def test_requested_timeout_can_lower_but_never_raise_the_horizon(tmp_path):
    horizon = float(exec_kernel.time_limit(None))
    assert exec_kernel.time_limit(horizon * 10) == horizon
    assert exec_kernel.time_limit(1.5) == 1.5
    assert exec_kernel.time_limit(-4) == horizon
    assert exec_kernel.time_limit(float("nan")) == horizon


def test_cwd_confinement_refuses_a_symlink_out_of_root(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside)
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, "-V"), cwd=str(root / "escape"), origin="human",
                             root=str(root)),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "DENY"
    assert res.exit_code is None


def test_grant_minted_for_one_argv_is_refused_for_another(tmp_path):
    cwd = str(tmp_path)
    grant = mint_grant(("/bin/ls", "-la"), cwd, ["PATH"], "a" * 64)
    assert verify_grant(grant, ("/bin/ls", "-la"), cwd, ["PATH"], "a" * 64)
    assert not verify_grant(grant, ("/bin/ls", "-l", "/"), cwd, ["PATH"], "a" * 64)
    assert not verify_grant(grant, ("/bin/ls", "-la"), str(tmp_path / "other"), ["PATH"], "a" * 64)
    assert not verify_grant(grant, ("/bin/ls", "-la"), cwd, ["PATH", "HOME"], "a" * 64)
    assert not verify_grant(grant, ("/bin/ls", "-la"), cwd, ["PATH"], "b" * 64)


def test_expired_grant_is_refused(tmp_path):
    expired = ExecutionGrant(grant_id="grant-x", digest="d", expires_ms=int(time.time() * 1000) - 1)
    assert not verify_grant(expired, ("/bin/ls",), str(tmp_path), [], "a" * 64)


def test_deny_never_spawns(tmp_path):
    marker = tmp_path / "marker.txt"
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=("bash", "-c", f"touch {marker}"), cwd=str(tmp_path), origin="model",
                             root=str(tmp_path)),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "DENY"
    assert not marker.exists()


def test_declined_ask_never_spawns(tmp_path):
    marker = tmp_path / "marker.txt"
    script = _write_script(tmp_path / "touch.py", f"open({str(marker)!r}, 'w').write('x')\n")
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              _ask_no, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "ASK_DECLINED"
    assert not marker.exists()


def test_missing_confirm_callback_declines(tmp_path):
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, "-V"), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              None, journal, artifacts_dir=tmp_path / "runs")
    # -V is a READ for humans, so it runs without asking.
    assert res.decision == "ALLOW"
    # An ASK with no callback must decline without spawning.
    script = _write_script(tmp_path / "noop.py", "print('hi')\n")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              None, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "ASK_DECLINED"


def test_allowed_read_runs_and_artifact_hash_matches(tmp_path):
    (tmp_path / "hello.txt").write_text("hello kernel\n", encoding="utf-8")
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=("cat", "hello.txt"), cwd=str(tmp_path), origin="model",
                             root=str(tmp_path)),
              _ask_no, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "ALLOW"
    assert res.exit_code == 0
    assert "hello kernel" in res.stdout_view
    assert res.artifact_path is not None
    artifact = Path(res.artifact_path)
    assert str(artifact).startswith(str(tmp_path / "runs"))
    assert _sha(res.artifact_path) == res.artifact_sha256


def test_long_output_is_truncated_with_a_marker(tmp_path):
    script = _write_script(tmp_path / "loud.py", "print('x' * 20000)\n")
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.truncated is True
    assert "characters truncated" in res.stdout_view
    assert len(res.stdout_view) < 8100


def test_one_receipt_per_decision_and_the_chain_verifies(tmp_path):
    journal = ExecJournal(tmp_path / "j.jsonl")
    run(CommandRequest(argv=("bash", "-c", "ls"), cwd=str(tmp_path), origin="model", root=str(tmp_path)),
        _ask_yes, journal, artifacts_dir=tmp_path / "runs")                     # DENY
    run(CommandRequest(argv=("cat", "hello.txt"), cwd=str(tmp_path), origin="model", root=str(tmp_path)),
        _ask_no, journal, artifacts_dir=tmp_path / "runs")                      # ALLOW (file absent is fine)
    script = _write_script(tmp_path / "noop.py", "print('ok')\n")
    run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                       root=str(tmp_path)),
        _ask_no, journal, artifacts_dir=tmp_path / "runs")                      # ASK_DECLINED
    lines = journal.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    decisions = [json.loads(line)["body"]["decision"] for line in lines]
    assert decisions == ["DENY", "ALLOW", "ASK_DECLINED"]
    ok, count, error = journal.verify()
    assert ok and count == 3 and error == ""


def test_tampering_breaks_the_chain(tmp_path):
    journal = ExecJournal(tmp_path / "j.jsonl")
    run(CommandRequest(argv=("bash", "-c", "ls"), cwd=str(tmp_path), origin="model", root=str(tmp_path)),
        _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    run(CommandRequest(argv=("bash", "-c", "ls"), cwd=str(tmp_path), origin="model", root=str(tmp_path)),
        _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    text = journal.path.read_text(encoding="utf-8")
    journal.path.write_text(text.replace('"decision":"DENY"', '"decision":"ALLOW"', 1), encoding="utf-8")
    ok, count, error = journal.verify()
    assert not ok
    assert "hash mismatch" in error


def test_ask_once_per_session_for_agent_verify(tmp_path):
    journal = ExecJournal(tmp_path / "j.jsonl")
    asked = []

    def confirm(prompt, cls):
        asked.append(prompt)
        return True

    req = CommandRequest(argv=(sys.executable, "-m", "compileall", "-q", "."), cwd=str(tmp_path),
                         origin="model", root=str(tmp_path))
    first = run(req, confirm, journal, artifacts_dir=tmp_path / "runs")
    second = run(req, confirm, journal, artifacts_dir=tmp_path / "runs")
    assert first.decision == "ASK_APPROVED"
    assert second.decision == "ALLOW"
    assert len(asked) == 1


def test_mutate_asks_every_call_for_agents(tmp_path):
    journal = ExecJournal(tmp_path / "j.jsonl")
    asked = []

    def confirm(prompt, cls):
        asked.append(prompt)
        return False

    req = CommandRequest(argv=("frobnicate",), cwd=str(tmp_path), origin="model", root=str(tmp_path))
    run(req, confirm, journal, artifacts_dir=tmp_path / "runs")
    run(req, confirm, journal, artifacts_dir=tmp_path / "runs")
    assert len(asked) == 2


def test_stream_callback_receives_live_output(tmp_path):
    script = _write_script(tmp_path / "say.py", "print('streamed-line')\n")
    seen = []
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=(sys.executable, str(script)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              _ask_yes, journal, stream=lambda kind, text: seen.append((kind, text)),
              artifacts_dir=tmp_path / "runs")
    assert res.decision == "ASK_APPROVED"
    assert any("streamed-line" in text for _, text in seen)


def test_explain_prints_tier_and_decision_without_running(tmp_path, capsys):
    marker = tmp_path / "should-not-exist"
    code = main(["--explain", "--origin", "model", "--cwd", str(tmp_path), "--root", str(tmp_path),
                 "--", "bash", "-c", f"touch {marker}"])
    out = capsys.readouterr().out
    assert code == 0
    assert "decision: DENY" in out
    assert "tier: MUTATE" in out
    assert not marker.exists()


def test_policy_failure_still_writes_one_receipt(tmp_path, monkeypatch):
    from osiris_cli import exec_policy
    monkeypatch.setattr(exec_policy, "_POLICY_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)
    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=("ls",), cwd=str(tmp_path), origin="human", root=str(tmp_path)),
              _ask_yes, journal, artifacts_dir=tmp_path / "runs")
    assert res.decision == "ERROR"
    assert len(journal.path.read_text(encoding="utf-8").splitlines()) == 1
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)


def test_unwritable_artifacts_dir_ends_in_one_error_receipt_and_never_spawns(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("regular file, not a directory\n", encoding="utf-8")
    marker = tmp_path / "ran.marker"
    asked = []

    def _record_yes(prompt, cls):
        asked.append(prompt)
        return True

    journal = ExecJournal(tmp_path / "j.jsonl")
    res = run(CommandRequest(argv=("touch", str(marker)), cwd=str(tmp_path), origin="human",
                             root=str(tmp_path)),
              _record_yes, journal, artifacts_dir=blocker / "runs")
    assert len(asked) == 1  # the command was otherwise cleared to run
    assert res.decision == "ERROR"
    assert any("artifact setup failed" in reason for reason in res.reasons)
    assert not marker.exists()
    assert res.artifact_path is None
    lines = journal.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["body"]["decision"] == "ERROR"
    ok, count, error = journal.verify()
    assert ok and count == 1 and error == ""
