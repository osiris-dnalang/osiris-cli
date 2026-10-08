"""rqc.batch (S2 amendment 5 draft): lockstep gathering of many seeds' sampler calls into multi-pub jobs, with the
frozen search code unchanged, a deterministic write-ahead ledger, validation of what comes back, and no hangs."""
import hashlib
import importlib.util
import json
import os
import socket
import threading
import time

import numpy as np
import pytest

from rqc import Ledger, probabilities
from rqc.batch import GatherAborted, GatheringSampler, GatherTimeout, ResultMismatch, projected_seconds
from rqc.experiment import run_adaptive, run_random
from rqc.hardware import BudgetExhausted

N, DEPTH, K, SHOTS = 5, 4, 3, 400
DRIVER = os.path.join(os.path.dirname(__file__), "..", "docs", "rqc", "S2", "s2_run_batched.py")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted during an offline test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def keyed_sample(circuit, shots, eps=0.3):
    """Depolarized ideal distribution, sampled with an RNG seeded by the circuit digest: the outcome depends only
    on (circuit, shots), never on call order, so sequential and gathered runs must agree exactly."""
    rng = np.random.default_rng(int(hashlib.sha256(circuit.digest().encode()).hexdigest()[:15], 16) + shots)
    p = probabilities(circuit)
    return rng.choice(len(p), size=shots, p=(1 - eps) * p + eps / len(p))


def batch_of(fn=keyed_sample, calls=None, delay=0.0):
    def run_batch(reqs):
        if calls is not None:
            calls.append([(c.digest(), s) for c, s in reqs])
        time.sleep(delay)
        return [fn(c, s) for c, s in reqs], {"job_id": f"mock-{len(calls or [])}",
                                              "circuit_sha256": [c.digest() for c, _ in reqs]}
    return run_batch


def tasks(seeds, n=N, depth=DEPTH, k=K, shots=SHOTS):
    out = []
    for s in seeds:
        order = ("random", "adaptive") if s % 2 == 0 else ("adaptive", "random")
        for rank, arm in enumerate(order):
            if arm == "random":
                fn = (lambda s: lambda smp, led: run_random(n, depth, k, shots, smp, led, seed=s))(s)
            else:
                fn = (lambda s: lambda smp, led: run_adaptive(n, depth, k, shots, smp, led, seed=s))(s)
            out.append(((s, rank, arm), fn))
    return out


def rows(path):
    return [json.loads(x) for x in open(path, encoding="utf-8").read().splitlines()]


def _driver():
    spec = importlib.util.spec_from_file_location("s2_run_batched", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gathered_run_equals_sequential_run(tmp_path):
    seeds = [10, 11, 12, 13]
    led = Ledger(str(tmp_path / "g.jsonl"))
    out = GatheringSampler(batch_of(), led, max_calls=K + 1).run(tasks(seeds))
    for s in seeds:
        sl = Ledger(str(tmp_path / f"s{s}.jsonl"))
        for arm, fn in (("random", run_random), ("adaptive", run_adaptive)):
            ref = fn(N, DEPTH, K, SHOTS, keyed_sample, sl, seed=s)
            got = [v for (ks, _, a), v in out.items() if ks == s and a == arm][0]
            assert got == ref                                   # identical selections and XEB values
    g = [r for r in rows(led.path) if r["kind"] in ("RQC_SUBMIT", "RQC_RESULT")]
    for s in seeds:
        seq = rows(str(tmp_path / f"s{s}.jsonl"))
        for arm in ("random", "adaptive"):
            mine = [r["payload"] for r in seq if r["payload"]["arm"] == arm]
            digests = {p["circuit_sha256"] for p in mine}
            theirs = [r["payload"] for r in g if r["payload"]["arm"] == arm and r["payload"]["circuit_sha256"] in digests]
            assert theirs == mine                               # same rows, same order, same content
    assert led.verify() == (True, "ok")


def test_registered_schedule_yields_twelve_jobs_of_eighty_pubs(tmp_path):
    """The real parameters (n=8, depth 6, k=5, 2,000 shots, seeds 1000-1079, blocks of 40) through the driver's own
    participant builder; the job count is observed, not assumed."""
    d = _driver()
    calls, per_block = [], []
    seeds = list(d.SEEDS)
    for b0 in range(0, len(seeds), d.BLOCK):
        block = seeds[b0:b0 + d.BLOCK]
        before = len(calls)
        g = GatheringSampler(batch_of(calls=calls), Ledger(str(tmp_path / f"l{b0}.jsonl")), max_calls=d.K + 1)
        out = g.run(d.participants(block))
        assert g.aborted is None
        per_block.append(len(calls) - before)
        expect = sorted(k for k, _ in d.participants(block))
        assert all(b == expect for b in g.batches)              # every participant in every job, registered order
        assert all(len(v) == d.K + 1 and v[-1]["round"] == "final" for v in out.values())
    assert per_block == [6, 6] and len(calls) == 12
    assert all(len(c) == 80 and {s for _, s in c} == {2000} for c in calls)
    assert sum(len(c) for c in calls) == 960                    # = 80 seeds x 2 arms x 6 calls, as registered
    assert sorted({s for (s, _, _), _ in d.participants(seeds)}) == seeds


def test_parity_ordered_pubs_and_batch_rows(tmp_path):
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")))
    g.run(tasks([20, 21, 22]))
    expect = [(20, 0, "random"), (20, 1, "adaptive"), (21, 0, "adaptive"), (21, 1, "random"),
              (22, 0, "random"), (22, 1, "adaptive")]
    assert len(g.batches) == K + 1 and all(b == expect for b in g.batches)
    batch_rows = [r for r in rows(str(tmp_path / "l.jsonl")) if r["kind"] == "RQC_BATCH_SUBMIT"]
    assert [r["payload"]["pubs"] for r in batch_rows] == [[list(k) for k in expect]] * (K + 1)


def test_every_submit_row_is_on_disk_before_its_job(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))

    def run_batch(reqs):
        on_disk = rows(led.path)
        assert on_disk[-1]["kind"] == "RQC_BATCH_SUBMIT"
        assert on_disk[-1]["payload"]["circuit_sha256"] == [c.digest() for c, _ in reqs]
        submitted = [r["payload"]["circuit_sha256"] for r in on_disk if r["kind"] == "RQC_SUBMIT"]
        assert all(c.digest() in submitted for c, _ in reqs)
        return [keyed_sample(c, s) for c, s in reqs], {}

    g = GatheringSampler(run_batch, led)
    g.run(tasks([1, 2]))
    assert g.aborted is None
    kinds = [r["kind"] for r in rows(led.path)]
    assert kinds.count("RQC_SUBMIT") == kinds.count("RQC_RESULT") == 4 * (K + 1)
    assert led.verify() == (True, "ok")


def test_budget_refusal_writes_no_submit_for_the_refused_job_and_stops_everyone(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    seen = []

    def preflight(reqs):
        seen.append(len(reqs))
        if len(seen) == 3:
            raise BudgetExhausted("ceiling")

    g = GatheringSampler(batch_of(), led, preflight=preflight)
    out = g.run(tasks([1, 2]))
    assert isinstance(g.aborted, BudgetExhausted) and len(g.batches) == 2
    assert all(isinstance(v, BudgetExhausted) for v in out.values())
    r = rows(led.path)
    kinds = [x["kind"] for x in r]
    sent = sum(len(x["payload"]["pubs"]) for x in r if x["kind"] == "RQC_BATCH_SUBMIT")
    assert kinds.count("RQC_SUBMIT") == sent == 8
    assert kinds.count("RQC_RESULT") == 8 and kinds[-1] == "RQC_BATCH_REFUSED"
    assert led.verify() == (True, "ok")


def test_job_failure_is_recorded_not_retried_and_aborts(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    n = []

    def run_batch(reqs):
        n.append(1)
        if len(n) == 2:
            raise ConnectionError("lost")
        return [keyed_sample(c, s) for c, s in reqs], {}

    g = GatheringSampler(run_batch, led)
    out = g.run(tasks([1, 2]))
    assert isinstance(g.aborted, ConnectionError) and len(n) == 2   # no third attempt
    assert all(isinstance(v, Exception) for v in out.values())
    kinds = [x["kind"] for x in rows(led.path)]
    assert kinds[-1] == "RQC_BATCH_FAILED" and kinds.count("RQC_SUBMIT") == 8


@pytest.mark.parametrize("bad", ["missing", "extra", "shuffled", "duplicate", "short"])
def test_malformed_results_are_rejected(tmp_path, bad):
    def run_batch(reqs):
        res = [keyed_sample(c, s) for c, s in reqs]
        dig = [c.digest() for c, _ in reqs]
        if bad == "missing":
            res = res[:-1]
        elif bad == "extra":
            res = res + res[:1]
        elif bad == "shuffled":
            dig = dig[::-1]
        elif bad == "duplicate":
            dig = [dig[0]] * len(dig)
        elif bad == "short":
            res[0] = res[0][:-1]
        return res, {"circuit_sha256": dig}

    led = Ledger(str(tmp_path / "l.jsonl"))
    g = GatheringSampler(run_batch, led)
    g.run(tasks([1, 2]))
    assert isinstance(g.aborted, ResultMismatch)
    assert rows(led.path)[-1]["kind"] == "RQC_BATCH_FAILED"


def test_slow_job_is_not_a_barrier_timeout(tmp_path):
    g = GatheringSampler(batch_of(delay=0.3), Ledger(str(tmp_path / "l.jsonl")), barrier_timeout_s=0.1)
    g.run(tasks([1]))
    assert g.aborted is None


def test_barrier_timeout_when_a_participant_stalls(tmp_path):
    def stalls(smp, led):
        time.sleep(0.6)
        return smp(None, 1)
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")), barrier_timeout_s=0.1)
    out = g.run(tasks([1]) + [((0, 0, "stall"), stalls)])
    assert isinstance(g.aborted, GatherTimeout) and g.batches == []
    assert all(isinstance(v, GatherAborted) for v in out.values())


def test_cancel_stops_all_participants(tmp_path):
    def stalls(smp, led):
        time.sleep(0.5)
        return smp(None, 1)
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")))
    threading.Timer(0.1, g.cancel, args=("operator cancel",)).start()
    out = g.run(tasks([1]) + [((0, 0, "stall"), stalls)])
    assert isinstance(g.aborted, GatherAborted) and "operator cancel" in str(g.aborted)
    assert all(isinstance(v, GatherAborted) for v in out.values())


def test_participant_error_does_not_hang_the_others(tmp_path):
    def broken(smp, led):
        raise ValueError("bug")
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")))
    out = g.run(tasks([1]) + [((0, 0, "broken"), broken)])
    assert isinstance(g.aborted, ValueError) and isinstance(out[(0, 0, "broken")], ValueError)


def test_unregistered_extra_round_is_refused(tmp_path):
    def greedy(smp, led):
        return [run_random(N, DEPTH, K, SHOTS, smp, led, seed=5), smp(None, 1)]
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")), max_calls=K + 1)
    g.run([((5, 0, "greedy"), greedy)])
    assert isinstance(g.aborted, GatherAborted) and "call 5 of 4" in str(g.aborted)


def test_participant_bound_and_unique_keys(tmp_path):
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")), max_participants=3)
    with pytest.raises(ValueError, match="exceed"):
        g.run(tasks([1, 2]))
    with pytest.raises(ValueError, match="unique"):
        GatheringSampler(batch_of(), Ledger(str(tmp_path / "m.jsonl"))).run(tasks([1]) + tasks([1]))


def test_projection_of_the_registered_schedule():
    d = _driver()
    assert projected_seconds([(None, 2000)] * 80) == 48
    assert d.projected_total(80, 40) == 12 * 48 == 576 <= d.BUDGET_SECONDS
    assert 960 * projected_seconds([(None, 2000)]) == 3840               # one job per call


def test_hardware_mode_refuses_without_dois_bundle_or_approval(tmp_path, monkeypatch):
    d = _driver()
    with pytest.raises(SystemExit, match="DOI"):
        d.main(["--prereg-doi", "10.5281/zenodo.1", "--amendment-doi", "10.5281/zenodo.2", "--out", str(tmp_path)])
    hw = ["--prereg-doi", d.PREREG_DOI, "--amendment-doi", "10.5281/zenodo.2", "--out", str(tmp_path)]
    with pytest.raises(SystemExit, match="bundle verification failed"):   # no deposited, matching bundle
        d.main(hw + ["--manifest", str(tmp_path / "absent.json")])
    monkeypatch.setattr(d, "verify_bundle", lambda *a, **k: [])          # isolate the approval stage
    with pytest.raises(SystemExit, match="not authorized"):              # refused before any network access
        d.main(hw)
    from rqc.control import Evidence
    ev = Evidence(str(tmp_path / "evidence"))
    assert any(e["kind"] == "authorization.denied" for e in ev.events())
    assert ev.verify_chain() == (True, "ok")


def test_batched_driver_on_a_fake_heron_and_restart_replays(tmp_path):
    pytest.importorskip("qiskit_aer")
    pytest.importorskip("qiskit_ibm_runtime.fake_provider")
    d = _driver()
    out = tmp_path / "run"
    argv = ["--fake", "--seeds", "4", "--block", "2", "--shots", "200", "--out", str(out)]
    rows1, stopped = d.main(argv)
    assert stopped is None and [r["seed"] for r in rows1] == [1000, 1001, 1002, 1003]
    for r in rows1:
        assert len(r["random"]) == len(r["adaptive"]) == d.K + 1 and r["random"][-1]["round"] == "final"
    from rqc.control import Evidence
    ev = Evidence(str(out / "evidence"))
    jobs = ev.con.execute("SELECT state FROM outbox").fetchall()
    assert [s for (s,) in jobs] == ["done"] * 12                        # 2 blocks x 6 jobs, all received
    assert ev.verify_chain() == (True, "ok") and ev.verify_artifacts() == []
    ev.con.close()
    # a restart on the same evidence re-runs the deterministic search and replays every job from evidence
    rows2, _ = d.main(argv)
    assert rows2 == rows1
    end = rows(str(out / "ledger.jsonl"))[-1]
    assert end["kind"] == "RQC_RUN_END" and end["payload"]["replayed_jobs"] == 12
    assert Ledger(str(out / "ledger.jsonl")).verify() == (True, "ok")
