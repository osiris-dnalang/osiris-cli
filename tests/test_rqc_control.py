"""rqc.control: evidence database settings, append-only events and tamper detection, content-addressed artifacts,
approval binding, and the outbox (leases, restart, reconciliation) against mock providers only."""
import json
import os
import socket
import sqlite3
import threading

import numpy as np
import pytest

from rqc import random_circuit
from rqc import control
from rqc.control import (AmbiguousOutcome, ArtifactStore, DefiniteFailure, Dispatcher, DurabilityError, Evidence,
                         IntegrityError, LeaseHeld, MockAdapter, NotAuthorized, ReconciliationRequired, Telemetry,
                         canonical, connect_evidence, sha256)
from rqc.hardware import BudgetExhausted


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted during an offline test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def sample(circuit, shots):
    return np.arange(shots, dtype=np.int64) % 2 ** circuit.n


PAYLOAD = {"schema": "rqc-s2-intent/1", "params": {"shots": 100}, "budget_seconds": 10.0}
REQS = [(random_circuit(3, 2, i), 100) for i in range(3)]
REQS2 = [(random_circuit(3, 2, 10 + i), 100) for i in range(3)]


def setup(tmp_path, clock=None, budget=10.0, target="ibm-quantum", payload=PAYLOAD, adapter=None, worker="w1"):
    ev = Evidence(str(tmp_path / "ev"), clock=clock or Clock())
    iid = ev.create_intent("test", payload, target)
    ev.approve(iid, "execute", budget, ev.clock() + 3600, "operator")
    ad = adapter or MockAdapter(sample, supports_idempotency=False)
    return ev, iid, Dispatcher(ev, iid, payload, target, ad, worker, project=lambda r: 2, lease_s=60), ad


# ---- evidence database ---------------------------------------------------------------------------------------

def test_required_pragmas_on_every_evidence_connection(tmp_path):
    p = str(tmp_path / "e.sqlite")
    for con in (connect_evidence(p), connect_evidence(p), Evidence(str(tmp_path / "x")).con):
        got = {n: con.execute(f"PRAGMA {n}").fetchone()[0] for n, _, _ in control.EVIDENCE_PRAGMAS}
        assert got == {"journal_mode": "wal", "synchronous": 2, "foreign_keys": 1, "busy_timeout": 5000,
                       "temp_store": 2, "trusted_schema": 0}


def test_evidence_fails_closed_instead_of_downgrading(tmp_path, monkeypatch):
    with pytest.raises(DurabilityError):
        connect_evidence(":memory:")
    # if the connection reports anything but the required value, opening fails
    monkeypatch.setattr(control, "EVIDENCE_PRAGMAS", (("synchronous", "NORMAL", 2),))
    with pytest.raises(DurabilityError, match="synchronous"):
        connect_evidence(str(tmp_path / "e.sqlite"))


def test_migrations_are_idempotent_and_tamper_checked(tmp_path, monkeypatch):
    p = str(tmp_path / "e.sqlite")
    connect_evidence(p).close()
    connect_evidence(p).close()
    monkeypatch.setattr(control, "MIGRATIONS", [(control.MIGRATIONS[0][0], control.MIGRATIONS[0][1] + "\n")])
    with pytest.raises(DurabilityError, match="differs"):
        connect_evidence(p)


def test_telemetry_is_separate_and_its_failure_changes_nothing(tmp_path):
    t = Telemetry(str(tmp_path / "no" / "such" / "dir" / "t.sqlite"))
    t.emit("progress", {"x": 1})
    assert t.dropped == 1
    ok = Telemetry(str(tmp_path / "t.sqlite"))
    assert ok._con.execute("PRAGMA synchronous").fetchone()[0] == 1          # NORMAL, non-authoritative only
    ev, iid, disp, _ = setup(tmp_path)
    disp(REQS)
    assert ev.verify_chain() == (True, "ok")


def test_transaction_rollback_leaves_nothing(tmp_path):
    ev = Evidence(str(tmp_path / "ev"))
    n = len(ev.events())
    with pytest.raises(RuntimeError):
        with ev.tx():
            ev._event("x", None, {})
            raise RuntimeError("crash inside the transaction")
    assert len(ev.events()) == n


def test_events_are_append_only_and_tampering_is_detected(tmp_path):
    ev, iid, disp, _ = setup(tmp_path)
    for sql in ("UPDATE events SET body = '{}' WHERE seq = 1", "DELETE FROM events WHERE seq = 1",
                "UPDATE intents SET target = 'x'", "DELETE FROM approvals"):
        with pytest.raises(sqlite3.DatabaseError):
            ev.con.execute(sql)
    assert ev.verify_chain() == (True, "ok")
    # a privileged operator can drop the triggers and edit; the chain then fails and dispatch is refused
    ev.con.execute("DROP TRIGGER events_no_update")
    body = ev.con.execute("SELECT body FROM events WHERE seq = 1").fetchone()[0]
    ev.con.execute("UPDATE events SET body = ? WHERE seq = 1", (body.replace("ibm-quantum", "local-fake"),))
    assert ev.verify_chain()[0] is False
    with pytest.raises(NotAuthorized, match="chain"):
        disp(REQS)
    assert ev.events()[-1]["kind"] == "authorization.denied"                # recorded, history not rewritten


# ---- artifacts ----------------------------------------------------------------------------------------------

def test_artifact_identity_and_corruption(tmp_path):
    st = ArtifactStore(str(tmp_path / "a"))
    d = st.put(b"hello")
    assert d == sha256(b"hello") and st.get(d) == b"hello" and st.put(b"hello") == d
    p = st.path_of(d)
    os.chmod(p, 0o644)
    with open(p, "wb") as f:
        f.write(b"jello")
    with pytest.raises(IntegrityError, match="does not match"):
        st.get(d)
    with pytest.raises(IntegrityError):
        st.put(b"hello")                                                    # never silently replaced
    with pytest.raises(IntegrityError, match="missing"):
        st.get(sha256(b"absent"))


def test_artifact_publication_interrupted_and_staging_sweep(tmp_path):
    st = ArtifactStore(str(tmp_path / "a"))
    part = os.path.join(st.staging, "dead.part")                             # crash after staging, before link
    with open(part, "wb") as f:
        f.write(b"half")
    with pytest.raises(IntegrityError):
        st.get(sha256(b"half"))
    assert st.sweep_staging(older_than_s=0) == ["dead.part"]


def test_artifact_paths_cannot_escape(tmp_path):
    st = ArtifactStore(str(tmp_path / "a"))
    for bad in ("../" + "0" * 61, "A" * 64, "0" * 63, None):
        with pytest.raises(ValueError):
            st.path_of(bad)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(str(outside), os.path.join(st.objects, "ab"))
    with pytest.raises(IntegrityError, match="outside"):
        st.path_of("ab" + "0" * 62)


def test_evidence_detects_missing_referenced_artifact(tmp_path):
    ev = Evidence(str(tmp_path / "ev"))
    d = ev.put_artifact(b"x", "test")
    os.unlink(ev.artifacts.path_of(d))
    assert ev.verify_artifacts() and "missing" in ev.verify_artifacts()[0]


# ---- approvals ------------------------------------------------------------------------------------------------

def test_approval_is_bound_to_payload_target_scope_budget_and_time(tmp_path):
    clock = Clock()
    ev = Evidence(str(tmp_path / "ev"), clock=clock)
    iid = ev.create_intent("t", PAYLOAD, "ibm-quantum")
    with pytest.raises(NotAuthorized):
        ev.authorize(iid, PAYLOAD, "ibm-quantum")                            # nothing approved yet
    ev.approve(iid, "read_only", 10.0, clock() + 100, "operator")
    with pytest.raises(NotAuthorized):
        ev.authorize(iid, PAYLOAD, "ibm-quantum")                            # read-only never authorizes a dispatch
    aid = ev.approve(iid, "execute", 10.0, clock() + 100, "operator")
    assert ev.authorize(iid, PAYLOAD, "ibm-quantum")["approval_id"] == aid
    changed = dict(PAYLOAD, params={"shots": 1500})
    with pytest.raises(NotAuthorized, match="payload"):
        ev.authorize(iid, changed, "ibm-quantum")                            # material change
    with pytest.raises(NotAuthorized, match="intent is for"):
        ev.authorize(iid, PAYLOAD, "local-fake")
    clock.t += 101
    with pytest.raises(NotAuthorized):
        ev.authorize(iid, PAYLOAD, "ibm-quantum")                            # expired
    clock.t -= 101
    ev.revoke(aid, "operator withdrew")
    with pytest.raises(NotAuthorized):
        ev.authorize(iid, PAYLOAD, "ibm-quantum")


def test_budget_mismatch_and_policy_approval_limits(tmp_path):
    ev = Evidence(str(tmp_path / "ev"))
    iid = ev.create_intent("t", PAYLOAD, "ibm-quantum")
    ev.approve(iid, "execute", 999.0, ev.clock() + 100, "operator")          # budget differs from the payload's
    with pytest.raises(NotAuthorized):
        ev.authorize(iid, PAYLOAD, "ibm-quantum")
    with pytest.raises(NotAuthorized, match="local targets"):
        ev.approve(iid, "execute", 10.0, ev.clock() + 100, "policy:auto")
    lid = ev.create_intent("t", PAYLOAD, "local-fake")
    ev.approve(lid, "execute", 10.0, ev.clock() + 100, "policy:local-fake")
    assert ev.authorize(lid, PAYLOAD, "local-fake")


def test_tampered_intent_payload_artifact_blocks_dispatch(tmp_path):
    ev, iid, disp, _ = setup(tmp_path)
    p = ev.artifacts.path_of(sha256(canonical(PAYLOAD)))
    os.chmod(p, 0o644)
    with open(p, "wb") as f:
        f.write(b"{}")
    with pytest.raises(NotAuthorized, match="artifact"):
        disp(REQS)


# ---- outbox ------------------------------------------------------------------------------------------------

def test_receipt_then_restart_replays_without_resubmitting(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    res, meta = disp(REQS)
    assert ad.executions == 1 and meta["job_id"] == "mock-1"
    ev.con.close()
    ev2 = Evidence(str(tmp_path / "ev"))                                     # process restart after the receipt
    disp2 = Dispatcher(ev2, iid, PAYLOAD, "ibm-quantum", ad, "w2", project=lambda r: 2)
    res2, meta2 = disp2(REQS)
    assert ad.executions == 1 and meta2["replayed"] and all((a == b).all() for a, b in zip(res, res2))


def test_crash_before_dispatch_lease_lapses_and_job_runs_once(tmp_path):
    clock = Clock()
    ev, iid, disp, ad = setup(tmp_path, clock=clock)
    disp.lease(REQS)                                                         # worker w1 dies here
    other = Dispatcher(ev, iid, PAYLOAD, "ibm-quantum", ad, "w2", project=lambda r: 2, lease_s=60)
    with pytest.raises(LeaseHeld):
        other(REQS)                                                          # lease still live
    clock.t += 61
    assert other.recover()["lease_expired"]
    other(REQS)
    assert ad.executions == 1


def test_crash_during_dispatch_becomes_outcome_unknown(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    key = disp.lease(REQS)
    disp._set(key, "dispatching", "job.dispatching", {})                     # worker dies inside submit
    rec = Dispatcher(ev, iid, PAYLOAD, "ibm-quantum", ad, "w2", project=lambda r: 2).recover()
    assert rec["outcome_unknown"] == [key]
    with pytest.raises(ReconciliationRequired):
        disp(REQS)
    assert ad.executions == 0


def test_ambiguous_outcome_without_idempotency_blocks_until_reconciled(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    ad.fail_after_execute = 1
    with pytest.raises(AmbiguousOutcome):
        disp(REQS)
    for _ in range(3):
        with pytest.raises(ReconciliationRequired):
            disp(REQS)                                                       # never resubmitted blindly
    assert ad.executions == 1
    key = disp.idem_key(REQS)
    with pytest.raises(NotImplementedError):
        ad.lookup(key)
    disp.reconcile(key, executed=False, evidence_note="provider console shows no job")
    disp(REQS)                                                               # a new, recorded attempt
    assert ad.executions == 2
    kinds = [e["kind"] for e in ev.events(iid)]
    assert kinds.count("job.outcome_unknown") == 1 and "job.reconciled_not_executed" in kinds


def test_ambiguous_outcome_reconciled_as_executed_uses_provider_results(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    ad.fail_after_execute = 1
    with pytest.raises(AmbiguousOutcome):
        disp(REQS)
    key = disp.idem_key(REQS)
    found = [sample(c, s) for c, s in REQS]
    disp.reconcile(key, executed=True, evidence_note="job mock-1 found by tag", results=found, requests=REQS,
                   meta={"job_id": "mock-1", "quantum_seconds": 1.0})
    res, meta = disp(REQS)
    assert meta["replayed"] and ad.executions == 1


def test_native_idempotency_reconciles_by_lookup(tmp_path):
    ev, iid, disp, ad = setup(tmp_path, adapter=MockAdapter(sample, supports_idempotency=True))
    ad.fail_after_execute = 1
    with pytest.raises(AmbiguousOutcome):
        disp(REQS)
    res, meta = disp(REQS)                                                   # lookup finds the executed job
    assert ad.executions == 1 and meta["replayed"]


def test_definite_failure_is_terminal_and_keeps_its_reservation(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    ad.fail_before = 1
    with pytest.raises(DefiniteFailure):
        disp(REQS)
    with pytest.raises(RuntimeError, match="terminally"):
        disp(REQS)
    assert disp.committed_seconds() == 2.0 and ad.executions == 0


def test_budget_reservations_include_unknown_outcomes(tmp_path):
    ev, iid, disp, ad = setup(tmp_path, budget=10.0)
    disp.project = lambda r: 6
    ad.fail_after_execute = 1
    disp.preflight(REQS)
    with pytest.raises(AmbiguousOutcome):
        disp(REQS)
    assert disp.committed_seconds() == 6.0
    with pytest.raises(BudgetExhausted):
        disp.preflight(REQS2)                                                # 6 held + 6 projected > 10
    assert any(e["kind"] == "budget.refused" for e in ev.events(iid))


def test_unreported_usage_never_frees_budget(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    disp.project = lambda r: 4
    real = ad.submit

    def zero_usage(reqs, key):
        res, meta = real(reqs, key)
        return res, dict(meta, quantum_seconds=0.0)                          # usage not yet computed
    ad.submit = zero_usage
    disp(REQS)
    assert disp.committed_seconds() == 4.0                                   # the reservation stands


def _bundle(tmp_path, commit="a" * 40, cite=True, status="draft", doi=None):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "code.py").write_text("x = 1\n")
    (root / "docs" / "prereg.md").write_text("frozen\n")
    (root / "docs" / "amend.md").write_text(f"implementation snapshot {commit if cite else '<none>'}\n")
    m = {"schema": control.BUNDLE_SCHEMA, "status": status, "amendment_doi": doi,
         "implementation": {"commit": commit, "files": control.code_manifest(str(root), ["code.py"])},
         "documents": control.code_manifest(str(root), ["docs/prereg.md", "docs/amend.md"]),
         "amendment_path": "docs/amend.md"}
    (root / "manifest.json").write_text(json.dumps(m))
    return str(root), str(root / "manifest.json")


def test_bundle_verifies_and_detects_changes(tmp_path):
    root, mp = _bundle(tmp_path)
    args = (["code.py"], ["docs/prereg.md", "docs/amend.md"])
    assert control.verify_bundle(root, mp, *args) == []
    with open(os.path.join(root, "code.py"), "a") as f:
        f.write("x = 2\n")
    assert any("code.py" in p for p in control.verify_bundle(root, mp, *args))


def test_bundle_requires_amendment_to_cite_the_snapshot_and_a_full_hash(tmp_path):
    args = (["code.py"], ["docs/prereg.md", "docs/amend.md"])
    root, mp = _bundle(tmp_path / "a", cite=False)
    assert any("does not cite" in p for p in control.verify_bundle(root, mp, *args))
    root, mp = _bundle(tmp_path / "b", commit="abc123")
    assert any("40-hex" in p for p in control.verify_bundle(root, mp, *args))
    assert control.verify_bundle(root, str(tmp_path / "none.json"), *args) == [f"manifest {tmp_path / 'none.json'} missing"]


def test_bundle_for_hardware_needs_deposited_status_and_matching_doi(tmp_path):
    args = (["code.py"], ["docs/prereg.md", "docs/amend.md"])
    root, mp = _bundle(tmp_path / "a")
    probs = control.verify_bundle(root, mp, *args, amendment_doi="10.5281/zenodo.9")
    assert any("not 'deposited'" in p for p in probs) and any("amendment_doi" in p for p in probs)
    root, mp = _bundle(tmp_path / "b", status="deposited", doi="10.5281/zenodo.9")
    assert control.verify_bundle(root, mp, *args, amendment_doi="10.5281/zenodo.9") == []


def test_concurrent_lease_acquisition_has_one_winner(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    wins, losses = [], []

    def grab(i):
        e = Evidence(str(tmp_path / "ev"), clock=ev.clock)                    # own connection per worker
        d = Dispatcher(e, iid, PAYLOAD, "ibm-quantum", ad, f"w{i}", project=lambda r: 2, lease_s=60)
        try:
            d.lease(REQS)
            wins.append(i)
        except LeaseHeld:
            losses.append(i)

    threads = [threading.Thread(target=grab, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1 and len(losses) == 7


def test_approval_revoked_between_lease_and_dispatch_is_caught(tmp_path):
    ev, iid, disp, ad = setup(tmp_path)
    aid = ev.con.execute("SELECT approval_id FROM approvals").fetchone()[0]
    real = ev.authorize
    calls = []

    def revoke_after_first(*a):
        calls.append(1)
        if len(calls) == 1:
            r = real(*a)
            ev.revoke(aid, "revoked mid-flight")
            return r
        return real(*a)
    ev.authorize = revoke_after_first
    disp.preflight(REQS)
    with pytest.raises(NotAuthorized):
        disp(REQS)
    assert ad.executions == 0
