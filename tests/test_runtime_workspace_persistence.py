from pathlib import Path

import pytest

from osiris.runtime.persistence import SessionStore
from osiris.runtime.workspace import Workspace, WorkspaceError


def test_workspace_rejects_traversal_and_absolute_paths(tmp_path):
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path).resolve_relative("../outside")
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path).resolve_relative(str(Path("/tmp/outside")))


def test_workspace_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / "osiris-runtime-outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "input.txt"
    link.symlink_to(outside)
    workspace = Workspace(tmp_path, require_git=False)

    with pytest.raises(WorkspaceError):
        workspace.read_bytes("input.txt")


def test_workspace_writes_atomically_and_reads_content(tmp_path):
    workspace = Workspace(tmp_path, require_git=False)
    digest = workspace.write_bytes("src/input.txt", b"hello")

    assert workspace.read_bytes("src/input.txt") == b"hello"
    assert len(digest) == 64


def test_session_store_deduplicates_and_verifies_artifacts():
    store = SessionStore()
    store.start_session("session-1", "/workspace")
    first = store.put_artifact(b"payload")
    second = store.put_artifact(b"payload")

    assert first == second
    assert store.get_artifact(first) == b"payload"
    store.record("receipt-1", "session-1", "test", {"status": "ok"})
    store.checkpoint("checkpoint-1", "session-1", None, "artifact://" + first)
    store.close()
