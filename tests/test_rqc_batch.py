"""rqc.batch (S2 amendment 5 draft): lockstep gathering of many seeds' sampler calls into multi-pub jobs, with the
frozen search code unchanged, a deterministic write-ahead ledger, and a projected-cost budget stop."""
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np
import pytest

from rqc import Ledger, probabilities
from rqc.batch import GatheringSampler, projected_seconds
from rqc.experiment import run_adaptive, run_random
from rqc.hardware import BudgetExhausted

N, DEPTH, K, SHOTS = 5, 4, 3, 400
DRIVER = os.path.join(os.path.dirname(__file__), "..", "docs", "rqc", "S2", "s2_run_batched.py")


def keyed_sample(circuit, shots, eps=0.3):
    """Depolarized ideal distribution, sampled with an RNG seeded by the circuit digest: the outcome depends only
    on (circuit, shots), never on call order, so sequential and gathered runs must agree exactly."""
    rng = np.random.default_rng(int(hashlib.sha256(circuit.digest().encode()).hexdigest()[:15], 16) + shots)
    p = probabilities(circuit)
    return rng.choice(len(p), size=shots, p=(1 - eps) * p + eps / len(p))


def batch_of(fn=keyed_sample, calls=None):
    def run_batch(reqs):
        if calls is not None:
            calls.append([(c.digest(), s) for c, s in reqs])
        return [fn(c, s) for c, s in reqs], {"job_id": f"mock-{len(calls or [])}"}
    return run_batch


def tasks(seeds):
    out = []
    for s in seeds:
        order = ("random", "adaptive") if s % 2 == 0 else ("adaptive", "random")
        for rank, arm in enumerate(order):
            if arm == "random":
                fn = (lambda s: lambda smp, led: run_random(N, DEPTH, K, SHOTS, smp, led, seed=s))(s)
            else:
                fn = (lambda s: lambda smp, led: run_adaptive(N, DEPTH, K, SHOTS, smp, led, seed=s))(s)
            out.append(((s, rank, arm), fn))
    return out


def rows(path):
    return [json.loads(x) for x in open(path, encoding="utf-8").read().splitlines()]


def test_gathered_run_equals_sequential_run(tmp_path):
    seeds = [10, 11, 12, 13]
    led = Ledger(str(tmp_path / "g.jsonl"))
    out = GatheringSampler(batch_of(), led).run(tasks(seeds))
    for s in seeds:
        sl = Ledger(str(tmp_path / f"s{s}.jsonl"))
        for arm, fn in (("random", run_random), ("adaptive", run_adaptive)):
            ref = fn(N, DEPTH, K, SHOTS, keyed_sample, sl, seed=s)
            got = [v for (ks, _, a), v in out.items() if ks == s and a == arm][0]
            assert got == ref                                   # identical selections and XEB values
    # every participant's own ledger rows appear in the same order as in its sequential run
    g = [r for r in rows(led.path) if r["kind"] in ("RQC_SUBMIT", "RQC_RESULT")]
    for s in seeds:
        seq = [r for r in rows(str(tmp_path / f"s{s}.jsonl"))]
        for arm in ("random", "adaptive"):
            mine = [r["payload"] for r in seq if r["payload"]["arm"] == arm]
            digests = {p["circuit_sha256"] for p in mine}
            theirs = [r["payload"] for r in g if r["payload"]["arm"] == arm and r["payload"]["circuit_sha256"] in digests]
            assert theirs == mine
    assert led.verify() == (True, "ok")


def test_one_job_per_round_with_parity_ordered_pubs(tmp_path):
    calls = []
    g = GatheringSampler(batch_of(calls=calls), Ledger(str(tmp_path / "l.jsonl")))
    g.run(tasks([20, 21, 22]))
    assert len(calls) == K + 1 and all(len(c) == 6 for c in calls)
    expect = [(20, 0, "random"), (20, 1, "adaptive"), (21, 0, "adaptive"), (21, 1, "random"),
              (22, 0, "random"), (22, 1, "adaptive")]
    assert all(b == expect for b in g.batches)
    batch_rows = [r for r in rows(str(tmp_path / "l.jsonl")) if r["kind"] == "RQC_BATCH_SUBMIT"]
    assert [r["payload"]["pubs"] for r in batch_rows] == [[list(k) for k in expect]] * (K + 1)


def test_every_submit_row_is_on_disk_before_its_job(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))

    def run_batch(reqs):
        on_disk = rows(led.path)
        assert on_disk[-1]["kind"] == "RQC_BATCH_SUBMIT"
        assert on_disk[-1]["payload"]["circuit_sha256"] == [c.digest() for c, _ in reqs]
        submitted = [r["payload"]["circuit_sha256"] for r in on_disk if r["kind"] == "RQC_SUBMIT"]
        for c, _ in reqs:
            assert c.digest() in submitted
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
    assert kinds.count("RQC_SUBMIT") == sent == 8                    # the refused third job left no SUBMIT rows
    assert kinds.count("RQC_RESULT") == 8 and kinds[-1] == "RQC_BATCH_REFUSED"
    assert led.verify() == (True, "ok")


def test_job_failure_is_recorded_and_aborts_the_gather(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    n = []

    def run_batch(reqs):
        n.append(1)
        if len(n) == 2:
            raise ConnectionError("lost")
        return [keyed_sample(c, s) for c, s in reqs], {}

    g = GatheringSampler(run_batch, led)
    out = g.run(tasks([1, 2]))
    assert isinstance(g.aborted, ConnectionError)
    assert all(isinstance(v, Exception) for v in out.values())
    kinds = [x["kind"] for x in rows(led.path)]
    assert kinds[-1] == "RQC_BATCH_FAILED" and kinds.count("RQC_SUBMIT") == 8   # second job's rows stand: it may have run
    assert led.verify() == (True, "ok")


def test_participant_error_does_not_hang_the_others(tmp_path):
    def broken(smp, led):
        raise ValueError("bug")
    g = GatheringSampler(batch_of(), Ledger(str(tmp_path / "l.jsonl")))
    out = g.run(tasks([1]) + [((0, 0, "broken"), broken)])
    assert isinstance(g.aborted, ValueError) and isinstance(out[(0, 0, "broken")], ValueError)


def _driver():
    spec = importlib.util.spec_from_file_location("s2_run_batched", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registered_run_fits_the_budget_and_the_frozen_design_does_not():
    d = _driver()
    assert projected_seconds([(None, 2000)] * 80) == 48
    assert d.projected_total(80, 40) == 12 * 48 == 576 <= d.BUDGET_SECONDS
    assert 960 * projected_seconds([(None, 2000)]) == 3840 > d.BUDGET_SECONDS  # one job per call: 6x over


def test_hardware_mode_refuses_without_both_dois(monkeypatch):
    d = _driver()
    for argv in (["--prereg-doi", "10.5281/zenodo.1", "--amendment-doi", "TEST", "--out", "x"],
                 ["--prereg-doi", "10.5281/zenodo.1", "--amendment-doi", "10.5281/zenodo.2", "--seeds", "4",
                  "--out", "x"]):
        monkeypatch.setattr(sys, "argv", ["s2_run_batched.py"] + argv)
        with pytest.raises(SystemExit, match="Zenodo DOIs"):
            d.main()                                              # refused before any IBM service is created


def test_batched_driver_on_a_fake_heron(tmp_path, monkeypatch):
    pytest.importorskip("qiskit_aer")
    pytest.importorskip("qiskit_ibm_runtime.fake_provider")
    d = _driver()
    monkeypatch.setattr(d, "SHOTS", 200)
    out = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["s2_run_batched.py", "--prereg-doi", "TEST", "--amendment-doi", "TEST",
                                      "--fake", "--seeds", "4", "--block", "2", "--out", str(out)])
    d.main()
    res = json.loads((out / "results.json").read_text())
    assert res["backend"] == "fake_fez" and res["stopped"] is None
    assert [r["seed"] for r in res["rows"]] == [1000, 1001, 1002, 1003]
    for r in res["rows"]:
        assert len(r["random"]) == len(r["adaptive"]) == d.K + 1 and r["random"][-1]["round"] == "final"
    ev = sorted((out / "evidence").iterdir())
    assert len(ev) == 2 * (d.K + 1)                                # 2 blocks x 6 jobs
    rec = json.loads(ev[0].read_text())
    assert len(rec["pubs"]) == 4 and all(sum(p["counts"].values()) == 200 for p in rec["pubs"])
    assert Ledger(str(out / "ledger.jsonl")).verify() == (True, "ok")
