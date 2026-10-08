#!/usr/bin/env python3
"""RQC S2 under amendment 5 (DRAFT - not deposited). The frozen s2_run.py is superseded, not edited.

Same search code, parameters, seeds, backend rule, qubit rule and 600 s ceiling as the frozen protocol. What changes
is how sampler calls become jobs: seeds run in blocks of 40; within a block the 80 participants (seed x arm) run in
lockstep and every barrier becomes one multi-pub job (see rqc/batch.py). Within a job, pubs are ordered by seed, and
within a seed the arm that comes first alternates with seed parity (even seed: random first). A block stopped by the
budget or by an error contributes no seeds.

Every job goes through rqc.control: a persisted intent whose payload names the code manifest, parameters, seeds,
DOIs, budget and target; an approval bound to that payload's hash; an outbox row leased and marked 'dispatching'
before the provider is called. The hardware path refuses before touching the network unless an unexpired 'execute'
approval for target 'ibm-quantum' covers exactly this payload. No such approval is created by this script.

  python s2_run_batched.py --fake --seeds 4 --block 2 --out DIR                 # local Aer on a fake Heron
  python s2_run_batched.py --prereg-doi 10.5281/zenodo.23241223 --amendment-doi 10.5281/zenodo.M \\
      --evidence EVDIR --out DIR                                                 # hardware (needs approval)
"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rqc import Ledger  # noqa: E402
from rqc.batch import GatheringSampler, projected_seconds  # noqa: E402
from rqc.control import (Dispatcher, Evidence, NotAuthorized, QiskitBatchAdapter, Telemetry,  # noqa: E402
                         canonical, code_manifest, sha256)
from rqc.experiment import run_adaptive, run_random  # noqa: E402
from rqc.hardware import BudgetExhausted, best_path, choose_backend  # noqa: E402

N, DEPTH, K, SHOTS, SIGMA = 8, 6, 5, 2000, 0.2
SEEDS = range(1000, 1080)
BLOCK = 40
BUDGET_SECONDS = 600
PREREG_DOI = "10.5281/zenodo.23241223"
HARDWARE_TARGET = "ibm-quantum"
PROTOCOL_FILES = ["rqc/__init__.py", "rqc/circuits.py", "rqc/sim.py", "rqc/xeb.py", "rqc/experiment.py",
                  "rqc/samplers.py", "rqc/hardware.py", "rqc/batch.py", "rqc/control.py",
                  "docs/rqc/S2/s2_run_batched.py", "docs/rqc/s1_adjusted.py", "docs/rqc/S2_PREREGISTRATION.md",
                  "docs/rqc/S2_AMENDMENT_5.DRAFT.md"]


def participants(seeds, shots=None):
    """[(key, fn)]; key (seed, rank, arm) sorts by seed, then by the parity-alternated arm order."""
    shots = SHOTS if shots is None else shots
    tasks = []
    for s in seeds:
        order = ("random", "adaptive") if s % 2 == 0 else ("adaptive", "random")
        for rank, arm in enumerate(order):
            if arm == "random":
                fn = (lambda s: lambda smp, led: run_random(N, DEPTH, K, shots, smp, led, seed=s))(s)
            else:
                fn = (lambda s: lambda smp, led: run_adaptive(N, DEPTH, K, shots, smp, led, seed=s, sigma=SIGMA))(s)
            tasks.append(((s, rank, arm), fn))
    return tasks


def projected_total(n_seeds, block, shots=None, **constants):
    """Projected billed seconds of the schedule: (k + 1) jobs per block of 2 x block pubs."""
    shots = SHOTS if shots is None else shots
    total, left = 0, n_seeds
    while left > 0:
        b = min(block, left)
        total += (K + 1) * projected_seconds([(None, shots)] * (2 * b), **constants)
        left -= b
    return total


def intent_payload(prereg_doi, amendment_doi, target, n_seeds=len(SEEDS), block=BLOCK, shots=None):
    shots = SHOTS if shots is None else shots
    return {"schema": "rqc-s2-intent/1", "protocol": "RQC-S2", "amendment": "5-draft",
            "prereg_doi": prereg_doi, "amendment_doi": amendment_doi, "target": target,
            "code_manifest": code_manifest(ROOT, PROTOCOL_FILES),
            "params": {"n": N, "depth": DEPTH, "k": K, "shots": shots, "sigma": SIGMA,
                       "seeds": [SEEDS[0], SEEDS[0] + n_seeds - 1], "block": block},
            "backend_rule": "first in ascending name order of operational Heron-family backends on the UTC date "
                            "of the first job (rqc.hardware.choose_backend)",
            "qubit_rule": "lowest summed CZ error simple 8-qubit path (rqc.hardware.best_path)",
            "budget_seconds": BUDGET_SECONDS}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg-doi", default="TEST")
    ap.add_argument("--amendment-doi", default="TEST")
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", help="evidence root (default: OUT/evidence)")
    ap.add_argument("--fake", action="store_true", help="fake Heron backends, local Aer (testing only)")
    ap.add_argument("--seeds", type=int, default=len(SEEDS), help="testing only; the registered run uses all 80")
    ap.add_argument("--block", type=int, default=BLOCK, help="testing only; the registered run uses 40")
    ap.add_argument("--shots", type=int, default=SHOTS, help="testing only; the registered run uses 2,000")
    a = ap.parse_args(argv)
    hardware = not a.fake
    if hardware and (a.seeds != len(SEEDS) or a.block != BLOCK or a.shots != SHOTS or a.prereg_doi != PREREG_DOI
                     or not a.amendment_doi.startswith("10.5281/zenodo.")):
        raise SystemExit("hardware runs use all 80 seeds in blocks of 40 at 2,000 shots and need the pre-registration "
                         f"DOI {PREREG_DOI} and the Zenodo DOI of amendment 5")
    target = HARDWARE_TARGET if hardware else "local-fake"
    os.makedirs(a.out, exist_ok=True)
    ev = Evidence(a.evidence or os.path.join(a.out, "evidence"))
    tel = Telemetry(os.path.join(a.out, "telemetry.sqlite"))
    payload = intent_payload(a.prereg_doi, a.amendment_doi, target, a.seeds, a.block, a.shots)
    intent_id = ev.create_intent("rqc-s2", payload, target)
    if not hardware:
        ev.approve(intent_id, "execute", BUDGET_SECONDS, ev.clock() + 3600, "policy:local-fake")
    try:
        ev.authorize(intent_id, payload, target)          # before any network access
    except NotAuthorized as e:
        raise SystemExit(f"not authorized: {e}. Intent {intent_id}, payload sha256 {sha256(canonical(payload))}")

    if hardware:                                           # reached only with a recorded execute approval
        from qiskit_ibm_runtime import Batch, QiskitRuntimeService, SamplerV2
        service = QiskitRuntimeService()
        remaining = service.usage().get("usage_remaining_seconds")
        ev.record("account.usage_observed", intent_id, {"usage_remaining_seconds": remaining})
        if remaining is None or remaining < BUDGET_SECONDS:
            raise SystemExit(f"account reports {remaining} s left; the run needs {BUDGET_SECONDS} s first")
        backends = service.backends(simulator=False, operational=True)
    else:
        from qiskit_ibm_runtime import fake_provider as fp
        backends = [fp.FakeFez(), fp.FakeKingston(), fp.FakeMarrakesh(), fp.FakeTorino()]
        remaining = None
    backend = choose_backend(backends)
    path, cost = best_path(backend, N)
    mode_ctx = Batch(backend=backend) if hardware else None
    adapter = QiskitBatchAdapter(backend, path,
                                 sampler_factory=(lambda: SamplerV2(mode=mode_ctx)) if hardware else None)
    disp = Dispatcher(ev, intent_id, payload, target, adapter, worker_id=f"pid-{os.getpid()}",
                      project=projected_seconds)
    recovered = disp.recover()
    ledger = Ledger(os.path.join(a.out, "ledger.jsonl"))
    seeds = list(SEEDS)[:a.seeds]
    protocol_sha = sha256(canonical(payload))
    ledger.append("RQC_RUN_START", {
        "stage": "S2-hardware" if hardware else "S2-fake-test", "amendment": "5-draft", "intent_id": intent_id,
        "protocol_sha256": protocol_sha, "prereg_doi": a.prereg_doi, "amendment_doi": a.amendment_doi,
        "backend": backend.name, "layout": path, "path_cz_error_sum": cost, "calibration": adapter.calibration,
        "n": N, "depth": DEPTH, "k": K, "shots": a.shots, "sigma": SIGMA, "seeds": [seeds[0], seeds[-1]],
        "block": a.block, "budget_seconds": BUDGET_SECONDS, "account_remaining_seconds": remaining,
        "projected_seconds": projected_total(len(seeds), a.block, a.shots), "recovered": recovered})
    rows, stopped = [], None
    try:
        for b0 in range(0, len(seeds), a.block):
            block = seeds[b0:b0 + a.block]
            g = GatheringSampler(disp, ledger, preflight=disp.preflight, max_calls=K + 1,
                                 protocol_sha256=protocol_sha)
            out = g.run(participants(block, a.shots))
            if g.aborted is not None:
                stopped = {"at_block": [block[0], block[-1]], "reason": repr(g.aborted),
                           "budget": isinstance(g.aborted, BudgetExhausted)}
                break
            for s in block:
                first = "random" if s % 2 == 0 else "adaptive"
                rows.append({"seed": s, "random": out[(s, 0 if first == "random" else 1, "random")],
                             "adaptive": out[(s, 0 if first == "adaptive" else 1, "adaptive")], "first": first,
                             "block": b0 // a.block})
            tel.emit("progress", {"seeds": len(rows), "committed_s": disp.committed_seconds()})
            print(f"block {block[0]}-{block[-1]} done; {len(rows)} seeds; committed "
                  f"{disp.committed_seconds():.1f} s", flush=True)
    finally:
        if mode_ctx is not None:
            mode_ctx.close()
    ledger.append("RQC_RUN_END", {"completed_seeds": len(rows), "stopped": stopped,
                                  "committed_seconds": disp.committed_seconds(), "replayed_jobs": disp.replayed})
    ev.record("run.end", intent_id, {"completed_seeds": len(rows), "stopped": stopped})
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump({"config": {"n": N, "depth": DEPTH, "k": K, "shots": a.shots, "sigma": SIGMA, "block": a.block},
                   "amendment": "5-draft", "intent_id": intent_id, "protocol_sha256": protocol_sha,
                   "backend": backend.name, "layout": path, "calibration": adapter.calibration,
                   "prereg_doi": a.prereg_doi, "amendment_doi": a.amendment_doi, "stopped": stopped, "rows": rows},
                  f, indent=1)
    print(f"finished: {len(rows)} seeds; stopped={stopped}; ledger {ledger.verify()}; evidence {ev.verify_chain()}")
    return rows, stopped


if __name__ == "__main__":
    main()
