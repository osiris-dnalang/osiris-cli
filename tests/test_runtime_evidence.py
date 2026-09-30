import hashlib
import sqlite3

import pytest

from osiris.runtime.evidence import EvidenceCapsule, EvidenceStore, EvidenceStoreError


def capsule():
    digest = hashlib.sha256(b"source").hexdigest()
    return EvidenceCapsule(
        run_id="run-1",
        task_id="task-1",
        plan_hash=digest,
        circuit_hash=digest,
        backend="local-simulator",
        execution_mode="dry_run",
        counts={"00": 1},
    )


def test_evidence_store_uses_durable_sqlite_settings(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence.sqlite"))
    assert store.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert store.connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert store.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_capsule_round_trip_and_provenance():
    store = EvidenceStore()
    record = capsule()
    store.insert_capsule(record)
    loaded = store.get_capsule(record.capsule_id)
    assert loaded["payload_hash"] == hashlib.sha256(b"{}").hexdigest()
    assert store.connection.execute(
        "SELECT COUNT(*) FROM provenance_events WHERE capsule_id = ?",
        (record.capsule_id,),
    ).fetchone()[0] == 1


def test_duplicate_capsule_is_rejected_without_partial_rows():
    store = EvidenceStore()
    record = capsule()
    store.insert_capsule(record)
    with pytest.raises(EvidenceStoreError):
        store.insert_capsule(record)
    assert store.connection.execute(
        "SELECT COUNT(*) FROM hardware_results WHERE capsule_id = ?",
        (record.capsule_id,),
    ).fetchone()[0] == 1


def test_outbox_is_idempotent():
    store = EvidenceStore()
    assert store.add_outbox("test", "key-1", "artifact://one")
    assert not store.add_outbox("test", "key-1", "artifact://one")


def test_artifact_registration_is_content_addressed_and_idempotent():
    store = EvidenceStore()
    record = capsule()
    store.insert_capsule(record)

    digest = store.register_artifact(record.capsule_id, "artifact://source", b"source")
    assert digest == hashlib.sha256(b"source").hexdigest()
    assert store.register_artifact(
        record.capsule_id, "artifact://source", b"source"
    ) == digest

    with pytest.raises(EvidenceStoreError):
        store.register_artifact(record.capsule_id, "artifact://source", b"tampered")


def test_summary_is_bounded_and_excludes_payload():
    store = EvidenceStore()
    record = capsule()
    store.insert_capsule(record)

    summary = store.summary("run-1")

    assert len(summary) == 1
    assert "payload_json" not in summary[0]
