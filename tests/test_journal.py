"""The operational journal: entries already on main still verify, appends are locked and numbered,
L8 events carry their payload hash, and tampering, torn tails and reserved keys are refused."""

import json
import multiprocessing
import os
import shutil
from pathlib import Path

import pytest

from osiris_cli import chain_lock
from osiris_cli.gap_analyzer import ProposedStep, compute_action_fingerprint
from osiris_cli.journal import OperationalMerkleLedger, payload_sha256

GENESIS = "0" * 64
MAIN_JOURNAL = Path(__file__).resolve().parents[1] / "provenance" / "osiris_operational_journal.jsonl"


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def test_the_journal_on_main_still_verifies():
    assert MAIN_JOURNAL.exists()
    assert OperationalMerkleLedger(MAIN_JOURNAL).verify() is None


def test_append_chains_and_numbers_entries(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    first = ledger.append("verification_check", {"checker": "osiris_harness", "status": "CONFIRMED"})
    second = ledger.append("verification_check", {"checker": "osiris_harness", "status": "CONFIRMED"})

    assert first["prev"] == GENESIS and first["seq_id"] == 0
    assert second["prev"] == first["hash"] and second["seq_id"] == 1
    assert _lines(ledger.path) == [first, second]
    raw = ledger.path.read_text(encoding="utf-8").splitlines()[0]
    assert raw == json.dumps(first, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert ledger.verify() is None


def test_append_continues_a_journal_written_before_seq_id(tmp_path):
    copy = tmp_path / "journal.jsonl"
    shutil.copy(MAIN_JOURNAL, copy)
    legacy = _lines(copy)
    assert all("seq_id" not in e for e in legacy)

    ledger = OperationalMerkleLedger(copy)
    entry = ledger.append_event("promotion.evaluated", "NODE_BETA_WORKSTATION", {"eligible": False})
    assert entry["seq_id"] == len(legacy)
    assert entry["prev"] == legacy[-1]["hash"]
    assert ledger.append("verification_check", {"status": "CONFIRMED"})["seq_id"] == len(legacy) + 1
    assert ledger.verify() is None


def test_append_event_records_the_l8_fields(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    step = ProposedStep(step_id="s1", capability_id="cap", target_node="NODE_ALPHA_EDGE", workspace_snapshot_id="abc")
    fingerprint = compute_action_fingerprint(step)
    payload = {"disposition": "READY", "gaps": []}

    entry = ledger.append_event("gap.analyzed", "NODE_ALPHA_EDGE", payload, action_fingerprint=fingerprint)
    assert entry["kind"] == "gap.analyzed"
    assert entry["substrate_node"] == "NODE_ALPHA_EDGE"
    assert entry["action_fingerprint"] == fingerprint
    assert entry["payload"] == payload
    assert entry["payload_sha256"] == payload_sha256(payload)
    assert ledger.append_event("note", "NODE_ALPHA_EDGE", {})["action_fingerprint"] is None
    assert ledger.verify() is None


@pytest.mark.parametrize("kwargs", [
    {"event_type": "", "substrate_node": "NODE_ALPHA_EDGE"},
    {"event_type": "note", "substrate_node": "  "},
    {"event_type": "note", "substrate_node": "NODE_ALPHA_EDGE", "action_fingerprint": "abc123"},
    {"event_type": "note", "substrate_node": "NODE_ALPHA_EDGE", "action_fingerprint": "A" * 64},
])
def test_append_event_rejects_malformed_fields(tmp_path, kwargs):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    with pytest.raises(ValueError):
        ledger.append_event(payload={}, **kwargs)
    assert ledger.path.read_bytes() == b""


@pytest.mark.parametrize("key", OperationalMerkleLedger.RESERVED)
def test_payload_cannot_overwrite_chain_fields(tmp_path, key):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    with pytest.raises(ValueError, match="reserved"):
        ledger.append("verification_check", {key: "x"})
    assert ledger.path.read_bytes() == b""


def _rewrite(path, entries):
    Path(path).write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def test_verify_reports_the_first_fault(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    for i in range(3):
        ledger.append_event("note", "NODE_ALPHA_EDGE", {"i": i})
    entries = _lines(ledger.path)

    edited = [dict(entries[0], payload={"i": 99}), *entries[1:]]
    _rewrite(ledger.path, edited)
    assert ledger.verify().startswith("Entry 0: hash mismatch")

    _rewrite(ledger.path, [entries[0], entries[2]])
    assert ledger.verify().startswith("Entry 1: prev-hash mismatch")

    _rewrite(ledger.path, entries)
    with ledger.path.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
    assert ledger.verify() == "Entry 3: not JSON"


def test_verify_checks_the_payload_hash(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    ledger.append("note", {"payload": {"a": 1}, "payload_sha256": payload_sha256({"a": 2})})
    assert ledger.verify() == "Entry 0: payload_sha256 does not match its payload"


def test_a_torn_tail_refuses_the_append(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    ledger.append("note", {"i": 0})
    with ledger.path.open("a", encoding="utf-8") as f:
        f.write('{"prev": "torn')
    before = ledger.path.read_bytes()
    with pytest.raises(chain_lock.ChainTailError):
        ledger.append("note", {"i": 1})
    assert ledger.path.read_bytes() == before


def _writer(path, start, count):
    ledger = OperationalMerkleLedger(path)
    for i in range(start, start + count):
        ledger.append_event("note", "NODE_BETA_WORKSTATION", {"i": i})


def test_concurrent_writers_never_fork_the_journal(tmp_path):
    path = str(tmp_path / "journal.jsonl")
    ctx = multiprocessing.get_context("fork" if hasattr(os, "fork") else "spawn")
    procs = [ctx.Process(target=_writer, args=(path, k * 1000, 25)) for k in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
        assert p.exitcode == 0

    entries = _lines(path)
    assert len(entries) == 100
    assert [e["seq_id"] for e in entries] == list(range(100))
    assert OperationalMerkleLedger(path).verify() is None
