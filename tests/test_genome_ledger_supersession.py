"""Genome ledger: an entry hashed in a foreign format is accepted only through an attested correction,
and only if its content is exactly what its writer hashed. Everything else still fails closed."""
import json
import os
import shutil

import pytest

import genome_ledger as gl

# dnalang-core is a separate package; without it, use the pinned copy of its ledger.py
# (v0.2.0) so these cases run everywhere instead of being skipped.
FIXTURE_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "dnalang_ledger_v0_2_0.py")


@pytest.fixture(autouse=True)
def _dnalang_ledger_source(monkeypatch):
    if not os.path.exists(gl.LEDGER_SRC):
        monkeypatch.setattr(gl, "LEDGER_SRC", FIXTURE_LEDGER)
        monkeypatch.setattr(gl, "_ledger_mod", None)


def _foreign_append(path, payload):
    """Append the way the 2026-10-01 Antigravity script did (prev inside the body, default separators)."""
    entries = [json.loads(line) for line in open(path) if line.strip()]
    prev = entries[-1]["hash"] if entries else gl.GENESIS
    entry = {"kind": "ZENODO_DRAFT_DEPOSITED", "prev": prev, "payload": payload, "ts": "2026-10-01T11:08:52Z"}
    entry["hash"] = gl._antigravity_inline_hash(entry)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _correction(index, entry):
    canonical = gl._dnalang_hash(entry["prev"], entry)
    return {"action": "RECORD_SUPERSEDED", "superseded_block_index": index,
            "superseded_observed_hash": entry["hash"], "corrected_canonical_hash": canonical,
            "resolution_policy": "supersede_and_attest", "reason": "test"}


@pytest.fixture
def broken(tmp_path):
    path = str(tmp_path / "genome_ledger.jsonl")
    led = gl.GenomeLedger(path)
    led.append("A", {"n": 1})
    led.append("B", {"n": 2})
    bad = _foreign_append(path, {"deposition_id": 1, "title": "x"})
    return path, led, bad


def test_foreign_entry_breaks_the_chain(broken):
    _, led, _ = broken
    assert not led.verify() and led.problem() == "entry 2: hash mismatch"


def test_attested_correction_restores_the_chain(broken):
    _, led, bad = broken
    led.append(gl.SUPERSESSION_KIND, _correction(2, bad))
    assert led.verify(), led.problem()
    assert any("antigravity-inline-2026-10-01" in n and "superseded by entry 3" in n for n in led.notes())
    led.append("C", {"n": 3})                       # the chain keeps growing from the correction
    assert led.verify()


def test_entry_edited_after_hashing_still_fails(broken):
    path, led, bad = broken
    lines = open(path).read().splitlines()
    rec = json.loads(lines[2])
    rec["payload"]["title"] = "edited"               # content no longer what its writer hashed
    lines[2] = json.dumps(rec)
    open(path, "w").write("\n".join(lines) + "\n")
    # a correction computed for the edited content does not rescue it: the stored hash no longer
    # reproduces under the foreign formula
    led.append(gl.SUPERSESSION_KIND, _correction(2, rec))
    assert led.problem() == "entry 2: hash mismatch"


@pytest.mark.parametrize("field,value", [("superseded_observed_hash", "0" * 64),
                                         ("corrected_canonical_hash", "1" * 64),
                                         ("superseded_block_index", 1)])
def test_correction_must_name_the_exact_entry_and_hash(broken, field, value):
    _, led, bad = broken
    corr = _correction(2, bad)
    corr[field] = value
    led.append(gl.SUPERSESSION_KIND, corr)
    assert led.problem() == "entry 2: hash mismatch"


def test_tampered_correction_fails(broken):
    path, led, bad = broken
    led.append(gl.SUPERSESSION_KIND, _correction(2, bad))
    lines = open(path).read().splitlines()
    rec = json.loads(lines[3])
    rec["payload"]["reason"] = "rewritten"
    lines[3] = json.dumps(rec)
    open(path, "w").write("\n".join(lines) + "\n")
    assert led.problem() == "entry 3: hash mismatch"


def test_correction_cannot_precede_the_entry(tmp_path):
    path = str(tmp_path / "l.jsonl")
    led = gl.GenomeLedger(path)
    led.append("A", {"n": 1})
    probe = {"kind": "ZENODO_DRAFT_DEPOSITED", "prev": "x", "payload": {}, "ts": "t"}
    led.append(gl.SUPERSESSION_KIND, {"superseded_block_index": 2, "superseded_observed_hash": "h",
                                      "corrected_canonical_hash": gl._dnalang_hash("x", probe)})
    _foreign_append(path, {})
    assert led.problem() == "entry 2: hash mismatch"


def test_real_ledger_copy_verifies_with_notes(tmp_path):
    if not os.path.exists(gl.DEFAULT_PATH):
        pytest.skip("no ~/.osiris/genome_ledger.jsonl on this machine")
    copy = str(tmp_path / "copy.jsonl")
    shutil.copyfile(gl.DEFAULT_PATH, copy)
    led = gl.GenomeLedger(copy)
    if not any(e.get("kind") == gl.SUPERSESSION_KIND for e in led.chain):
        pytest.skip("this machine's ledger has no correction record")
    assert led.verify(), led.problem()
    assert led.notes()
