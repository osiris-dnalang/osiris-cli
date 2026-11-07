"""Offline tests for the execution policy: classification, normalization and environment scrubbing.

Nothing here spawns a process. Every case classifies inside a temporary root.
"""

import json
import os
from pathlib import Path

import pytest

from osiris_cli import exec_policy
from osiris_cli.exec_policy import (
    CommandRequest,
    PolicyError,
    classify,
    is_sensitive_argv,
    scrubbed_env,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "exec_policy_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _req(argv, origin, root, cwd=None, **kw):
    return CommandRequest(argv=tuple(argv), cwd=str(cwd or root), origin=origin, root=str(root), **kw)


def test_fixture_has_at_least_eighty_cases_and_covers_every_bypass():
    assert len(CASES) >= 80
    ids = {case["id"] for case in CASES}
    for required in ("bypass-bash-c-model", "bypass-sh-c-model", "shell-env-assign-model",
                     "bypass-nohup-rm-model", "bypass-timeout-rm-model", "bypass-dotdot-rm-model",
                     "shell-find-exec-semicolon-model", "mutate-find-delete-model",
                     "shell-git-c-alias-model", "shell-git-c-pager-model", "mutate-git-quoted-push-model",
                     "shell-git-dir-env-push-model", "secret-cat-env-model", "secret-rg-env-local-model",
                     "forbid-sudo-model", "net-curl-model", "net-pip-install-model",
                     "net-run-ibm-model", "bypass-python-I-c-model", "forbid-xargs-model"):
        assert required in ids, required


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_fixture_case(case, tmp_path):
    cls = classify(_req(case["argv"], case["origin"], tmp_path))
    assert cls.tier == case["tier"], cls.reasons
    assert cls.decision == case["decision"], cls.reasons


def test_policy_hash_is_recorded_and_stable():
    first = classify(_req(["ls"], "model", Path.cwd()))
    second = classify(_req(["ls"], "model", Path.cwd()))
    assert len(first.policy_sha256) == 64
    assert first.policy_sha256 == second.policy_sha256


def test_unknown_origin_is_denied(tmp_path):
    cls = classify(_req(["ls"], "stranger", tmp_path))
    assert cls.decision == "DENY"


def test_empty_or_non_string_argv_is_denied(tmp_path):
    assert classify(CommandRequest(argv=(), cwd=str(tmp_path), origin="human", root=str(tmp_path))).decision == "DENY"
    assert classify(CommandRequest(argv=("ls", 3), cwd=str(tmp_path), origin="human", root=str(tmp_path))).decision == "DENY"


def test_nul_and_control_characters_are_denied(tmp_path):
    assert classify(_req(["l\x01s"], "human", tmp_path)).decision == "DENY"
    assert classify(_req(["ls", "a\x00b"], "human", tmp_path)).decision == "DENY"


def test_symlink_named_ls_pointing_at_rm_is_treated_as_rm(tmp_path):
    rm_path = None
    for candidate in ("/usr/bin/rm", "/bin/rm"):
        if os.path.exists(candidate):
            rm_path = candidate
            break
    if rm_path is None:
        pytest.skip("no rm binary on this system")
    link = tmp_path / "ls"
    link.symlink_to(rm_path)
    cls = classify(_req(["./ls", "-rf", "x"], "model", tmp_path))
    assert cls.decision == "DENY"
    assert cls.tier == "MUTATE"


def test_cwd_outside_root_is_denied(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    cls = classify(_req(["ls"], "human", root, cwd=outside))
    assert cls.decision == "DENY"


def test_symlink_inside_root_that_points_outside_is_denied(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside)
    cls = classify(_req(["ls"], "human", root, cwd=root / "escape"))
    assert cls.decision == "DENY"


def test_cwd_that_is_not_a_directory_is_denied(tmp_path):
    cls = classify(_req(["ls"], "human", tmp_path, cwd=tmp_path / "missing"))
    assert cls.decision == "DENY"


def test_secret_path_is_denied_even_for_human(tmp_path):
    assert classify(_req(["cat", ".env"], "human", tmp_path)).decision == "DENY"
    assert classify(_req(["cat", "~/.ssh/id_rsa"], "human", tmp_path)).decision == "DENY"


def test_publish_flag_is_denied_for_agents(tmp_path):
    cls = classify(_req(["python", "-m", "pytest", "--publish"], "model", tmp_path))
    assert cls.decision == "DENY"
    cls = classify(_req(["python", "-m", "pytest", "--publish"], "human", tmp_path))
    assert cls.decision == "ASK"


def test_unwrapped_command_is_recorded_in_normalized_argv(tmp_path):
    cls = classify(_req(["timeout", "5", "rm", "-rf", "x"], "human", tmp_path))
    assert os.path.basename(cls.normalized_argv[0]) == "rm"
    assert cls.normalized_argv[1:] == ("-rf", "x")


def test_normalized_argv_keeps_the_path_not_the_realpath_for_venv_interpreters(tmp_path):
    # The venv path must survive normalization; realpath would drop pyvenv.cfg discovery when exec'd.
    import sys

    cls = classify(_req([sys.executable, "--version"], "model", tmp_path))
    assert cls.normalized_argv[0] == os.path.abspath(sys.executable)
    assert cls.tier == "READ"


def test_classify_is_pure_apart_from_reads(tmp_path):
    before = set(os.listdir(tmp_path))
    classify(_req(["rm", "-rf", "x"], "human", tmp_path))
    classify(_req(["git", "commit", "-m", "m"], "model", tmp_path))
    assert set(os.listdir(tmp_path)) == before


def test_missing_policy_file_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(exec_policy, "_POLICY_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)
    with pytest.raises(PolicyError):
        classify(_req(["ls"], "human", tmp_path))
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)


def test_malformed_policy_fails_closed(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text('{"tiers": {"READ": {"human": "ALLOW", "agent": "ALLOW"}}}', encoding="utf-8")
    monkeypatch.setattr(exec_policy, "_POLICY_PATH", bad)
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)
    with pytest.raises(PolicyError):
        exec_policy.load_policy()
    monkeypatch.setattr(exec_policy, "_POLICY_CACHE", None)


def test_scrubbed_env_drops_secret_names_even_when_allowlisted():
    parent = {
        "PATH": "/usr/bin",
        "HOME": "/home/x",
        "LC_ALL": "C",
        "OSIRIS_MODEL": "qwen",
        "QISKIT_IBM_TOKEN": "t",
        "OSIRIS_PG_URL": "postgres://u:p@h/db",
        "GITHUB_TOKEN": "g",
        "AWS_SECRET_ACCESS_KEY": "a",
        "MY_API_KEY": "k",
        "IBM_QUANTUM_KEY": "q",
        "SSH_AUTH_SOCK": "/tmp/agent",
        "RANDOM_VAR": "r",
    }
    env = scrubbed_env(parent)
    assert set(env) == {"PATH", "HOME", "LC_ALL", "OSIRIS_MODEL"}


def test_is_sensitive_argv_flags_only_the_token_command():
    assert is_sensitive_argv(("/usr/bin/gcloud", "auth", "print-access-token"))
    assert not is_sensitive_argv(("/usr/bin/gcloud", "compute", "instances", "list"))
    assert not is_sensitive_argv(("/bin/echo", "print-access-token"))
