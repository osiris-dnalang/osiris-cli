"""/update moves a git checkout forward with git, never by pip-installing a second copy over it."""
import subprocess

import pytest

from osiris_cli import osiris_repl
from osiris_cli.osiris_repl import update_checkout


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repos(tmp_path):
    origin, local, other = tmp_path / "origin.git", tmp_path / "local", tmp_path / "other"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    for clone in (local, other):
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
        git(clone, "config", "user.email", "t@example.com")
        git(clone, "config", "user.name", "t")
        git(clone, "checkout", "-q", "-B", "main")
    (other / "a.txt").write_text("1\n")
    git(other, "add", "a.txt")
    git(other, "commit", "-qm", "one")
    git(other, "push", "-q", "origin", "main")
    git(local, "pull", "-q", "origin", "main")
    git(local, "branch", "-q", "--set-upstream-to=origin/main", "main")
    return local, other


def upstream_commit(other, text="2\n"):
    (other / "a.txt").write_text(text)
    git(other, "commit", "-qam", "upstream")
    git(other, "push", "-q", "origin", "main")
    return git(other, "rev-parse", "HEAD")


def test_a_checkout_behind_origin_is_fast_forwarded(repos, capsys):
    local, other = repos
    head = upstream_commit(other)
    assert update_checkout(str(local)) is True
    assert git(local, "rev-parse", "HEAD") == head
    assert "fast-forwarded by 1 commit" in capsys.readouterr().out


def test_local_commits_are_never_merged_or_dropped(repos, capsys):
    local, other = repos
    upstream_commit(other)
    (local / "b.txt").write_text("mine\n")
    git(local, "add", "b.txt")
    git(local, "commit", "-qm", "local work")
    mine = git(local, "rev-parse", "HEAD")
    assert update_checkout(str(local)) is False
    assert git(local, "rev-parse", "HEAD") == mine
    assert "1 commit(s) that origin/main does not, and is 1 behind" in capsys.readouterr().out


def test_uncommitted_changes_stop_the_update(repos, capsys):
    local, other = repos
    upstream_commit(other)
    (local / "a.txt").write_text("edited\n")
    before = git(local, "rev-parse", "HEAD")
    assert update_checkout(str(local)) is False
    assert git(local, "rev-parse", "HEAD") == before and "uncommitted changes" in capsys.readouterr().out


def test_an_up_to_date_checkout_does_not_restart(repos, capsys):
    local, _ = repos
    assert update_checkout(str(local)) is False
    assert "already has everything" in capsys.readouterr().out


def test_update_from_a_checkout_never_runs_pip(monkeypatch):
    calls = []
    monkeypatch.setattr(osiris_repl, "update_checkout", lambda repo: calls.append(repo) or False)
    monkeypatch.setattr(osiris_repl.subprocess, "run", lambda *a, **k: pytest.fail("pip must not run"))
    monkeypatch.setattr(osiris_repl.os, "execvp", lambda *a: pytest.fail("nothing to restart for"))
    monkeypatch.setattr(osiris_repl.os.path, "exists",
                        lambda p, real=osiris_repl.os.path.exists: True if p.endswith(".git") else real(p))
    osiris_repl.execute_update()
    assert len(calls) == 1


def fake_probe(file, version="4.6.0", code=0):
    out = '{"file": "%s", "version": "%s"}\n' % (file, version)
    return lambda *a, **k: subprocess.CompletedProcess(a[0], code, out if code == 0 else "", "boom")


def test_a_fresh_interpreter_imports_this_checkout():
    repo = osiris_repl.os.path.dirname(osiris_repl.os.path.dirname(osiris_repl.__file__))
    ok, detail = osiris_repl.verify_upgrade_import(repo)
    assert ok, detail


def test_a_copy_outside_the_checkout_stops_the_restart(tmp_path):
    repo = tmp_path / "osiris-cli"
    for shadow in (tmp_path / "site-packages" / "osiris_cli" / "__init__.py",
                   tmp_path / "osiris-cli-old" / "osiris_cli" / "__init__.py"):    # a sibling sharing the prefix
        ok, detail = osiris_repl.verify_upgrade_import(str(repo), run=fake_probe(shadow))
        assert not ok and "not from the checkout" in detail and str(shadow.parent.parent) in detail
    ok, detail = osiris_repl.verify_upgrade_import(str(repo), run=fake_probe(repo / "osiris_cli" / "__init__.py"))
    assert ok and "4.6.0" in detail


def test_an_install_that_cannot_be_imported_stops_the_restart(tmp_path):
    ok, detail = osiris_repl.verify_upgrade_import(None, run=fake_probe(tmp_path / "x.py", code=1))
    assert not ok and "cannot import osiris_cli (boom)" in detail
    ok, _ = osiris_repl.verify_upgrade_import(None, run=fake_probe(tmp_path / "x.py"))   # pip path: any location
    assert ok


@pytest.mark.parametrize("verified", [False, True])
def test_the_console_restarts_only_after_the_import_check(monkeypatch, capsys, verified):
    restarted = []
    monkeypatch.setattr(osiris_repl, "update_checkout", lambda repo: True)
    monkeypatch.setattr(osiris_repl, "verify_upgrade_import", lambda repo: (verified, "a fresh interpreter says so"))
    monkeypatch.setattr(osiris_repl.time, "sleep", lambda s: None)
    monkeypatch.setattr(osiris_repl.os, "execvp", lambda *a: restarted.append(a))
    monkeypatch.setattr(osiris_repl.os.path, "exists",
                        lambda p, real=osiris_repl.os.path.exists: True if p.endswith(".git") else real(p))
    osiris_repl.execute_update()
    out = capsys.readouterr().out
    assert bool(restarted) is verified
    assert ("Not restarting: a fresh interpreter says so" in out) is not verified
