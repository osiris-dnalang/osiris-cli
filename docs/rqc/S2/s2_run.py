#!/usr/bin/env python3
"""RQC S2 hardware run, exactly as pre-registered (docs/rqc/S2_PREREGISTRATION.md).

Refuses to start without the pre-registration DOI. Chooses the backend and qubits by the registered rules, runs seeds
1000-1079 with both arms of a seed in one IBM batch session (the arm that runs first alternates with seed parity),
writes a ledger row before every job and the raw evidence of every job, and stops at the registered QPU budget.
No XEB value is printed while the run is in progress (no interim analysis).

  python s2_run.py --prereg-doi 10.5281/zenodo.NNNNNNN --out DIR            # IBM hardware
  python s2_run.py --prereg-doi TEST --fake --seeds 2 --out DIR             # local test on a fake Heron backend
"""
import argparse
import json
import os
import time

from rqc import Ledger
from rqc.experiment import run_adaptive, run_random
from rqc.hardware import BudgetExhausted, HardwareSampler, best_path, choose_backend

N, DEPTH, K, SHOTS, SIGMA = 8, 6, 5, 2000, 0.2
SEEDS = range(1000, 1080)
BUDGET_SECONDS = 600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg-doi", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fake", action="store_true", help="fake Heron backends, local Aer (testing only)")
    ap.add_argument("--seeds", type=int, default=len(SEEDS), help="testing only; the registered run uses all 80")
    a = ap.parse_args()
    if not a.fake and (a.seeds != len(SEEDS) or not a.prereg_doi.startswith("10.5281/zenodo.")):
        raise SystemExit("hardware runs use all 80 registered seeds and need the Zenodo DOI of the pre-registration")
    if a.fake:
        from qiskit_ibm_runtime import fake_provider as fp
        backends = [fp.FakeFez(), fp.FakeKingston(), fp.FakeMarrakesh(), fp.FakeTorino()]
    else:
        from qiskit_ibm_runtime import QiskitRuntimeService
        backends = QiskitRuntimeService().backends(simulator=False, operational=True)
    backend = choose_backend(backends)
    path, cost = best_path(backend, N)
    os.makedirs(a.out, exist_ok=True)
    ledger = Ledger(os.path.join(a.out, "ledger.jsonl"))

    if a.fake:
        factory = None
        mode_ctx = None
    else:
        from qiskit_ibm_runtime import Batch, SamplerV2
        mode_ctx = Batch(backend=backend)
        factory = lambda: SamplerV2(mode=mode_ctx)
    sampler = HardwareSampler(backend, path, os.path.join(a.out, "evidence"), BUDGET_SECONDS, sampler_factory=factory)
    ledger.append("RQC_RUN_START", {"stage": "S2-hardware" if not a.fake else "S2-fake-test", "prereg_doi": a.prereg_doi,
                                    "backend": backend.name, "layout": path, "path_cz_error_sum": cost,
                                    "calibration": sampler.calibration, "n": N, "depth": DEPTH, "k": K, "shots": SHOTS,
                                    "sigma": SIGMA, "seeds": [SEEDS[0], SEEDS[0] + a.seeds - 1], "budget_seconds": BUDGET_SECONDS})
    rows, stopped = [], None
    try:
        for i, s in enumerate(list(SEEDS)[:a.seeds]):
            first_random = s % 2 == 0
            try:
                if first_random:
                    r = run_random(N, DEPTH, K, SHOTS, sampler, ledger, seed=s)
                    q = run_adaptive(N, DEPTH, K, SHOTS, sampler, ledger, seed=s, sigma=SIGMA)
                else:
                    q = run_adaptive(N, DEPTH, K, SHOTS, sampler, ledger, seed=s, sigma=SIGMA)
                    r = run_random(N, DEPTH, K, SHOTS, sampler, ledger, seed=s)
            except BudgetExhausted as e:
                stopped = {"at_seed": s, "reason": str(e)}
                break
            rows.append({"seed": s, "random": r, "adaptive": q, "first": "random" if first_random else "adaptive"})
            print(f"seed {s} done ({i + 1}/{a.seeds}); {sampler.jobs} jobs, {sampler.spent:.1f} QPU s", flush=True)
    finally:
        if mode_ctx is not None:
            mode_ctx.close()
    ledger.append("RQC_RUN_END", {"completed_seeds": len(rows), "stopped": stopped, "qpu_seconds": sampler.spent, "jobs": sampler.jobs})
    json.dump({"config": {"n": N, "depth": DEPTH, "k": K, "shots": SHOTS, "sigma": SIGMA}, "backend": backend.name,
               "layout": path, "calibration": sampler.calibration, "prereg_doi": a.prereg_doi, "stopped": stopped,
               "rows": rows}, open(os.path.join(a.out, "results.json"), "w"), indent=1)
    print(f"finished: {len(rows)} seeds, {sampler.jobs} jobs, {sampler.spent:.1f} QPU s; stopped={stopped}; ledger {ledger.verify()}")


if __name__ == "__main__":
    main()
