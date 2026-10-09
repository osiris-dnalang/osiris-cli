#!/usr/bin/env python3
"""RQC stage S1: both arms on Aer with a noise model from a live IBM Heron calibration (read-only; nothing is
submitted to hardware), then the paired comparison and a power analysis for the S2 pre-registration.

Usage: PYTHONPATH=~/osiris-cli-wt/rqc ~/osiris_env/bin/python s1_simulate.py --seeds 30
"""
import argparse
import json
import math
import os
import statistics
import time

import numpy as np

from rqc import Ledger
from rqc.experiment import run_adaptive, run_random
from rqc.samplers import aer_sampler_from_backend

HERE = os.path.dirname(os.path.abspath(__file__))
FEZ_CHAIN = [89, 90, 91, 98, 111, 110, 109, 118]     # the ibm_fez 8-qubit chain of the 2026-09 GHZ and DD runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--first-seed", type=int, default=100)     # simulation seeds 100+; hardware will use fresh ones
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--shots", type=int, default=2000)
    ap.add_argument("--sigma", type=float, default=0.2)
    ap.add_argument("--out", default=os.path.join(HERE, "s1"))
    a = ap.parse_args()

    from qiskit_ibm_runtime import QiskitRuntimeService
    backend = QiskitRuntimeService().backend(a.backend)
    edges = {tuple(e) for e in backend.coupling_map.get_edges()}
    layout = FEZ_CHAIN[:a.n]
    missing = [(x, y) for x, y in zip(layout, layout[1:]) if (x, y) not in edges and (y, x) not in edges]
    if missing:
        raise SystemExit(f"chain not connected on {a.backend}: {missing}")
    sampler, cal = aer_sampler_from_backend(backend, layout, seed=a.first_seed)
    os.makedirs(a.out, exist_ok=True)
    ledger = Ledger(os.path.join(a.out, "ledger.jsonl"))
    cfg = {k: v for k, v in vars(a).items() if k != "out"}
    ledger.append("RQC_RUN_START", {"stage": "S1-simulation", "sampler": "aer_from_backend", "layout": layout,
                                    "config": cfg, "calibration": cal})
    rows, t0 = [], time.time()
    for s in range(a.first_seed, a.first_seed + a.seeds):
        r = run_random(a.n, a.depth, a.k, a.shots, sampler, ledger, seed=s)
        q = run_adaptive(a.n, a.depth, a.k, a.shots, sampler, ledger, seed=s, sigma=a.sigma)
        rows.append({"seed": s, "random": r, "adaptive": q})
        print(f"seed {s}: final random {r[-1]['xeb_normalized']:.4f}  adaptive {q[-1]['xeb_normalized']:.4f}  "
              f"({time.time() - t0:.0f}s)", flush=True)
    json.dump({"config": cfg, "layout": layout, "calibration": cal, "rows": rows},
              open(os.path.join(a.out, "results.json"), "w"), indent=1)

    d = [x["adaptive"][-1]["xeb_normalized"] - x["random"][-1]["xeb_normalized"] for x in rows]
    n = len(d); m = statistics.mean(d); sd = statistics.stdev(d) if n > 1 else float("nan")
    se = sd / math.sqrt(n); tcrit = 2.045 if n == 30 else 1.96             # two-sided 95% (t, 29 df) / normal
    pos = sum(x > 0 for x in d); neg = sum(x < 0 for x in d)
    p_sign = sum(math.comb(pos + neg, i) for i in range(pos, pos + neg + 1)) / 2 ** (pos + neg) if pos + neg else 1.0
    fin = lambda arm, key: statistics.mean(x[arm][-1][key] for x in rows)
    infl = lambda arm: statistics.mean(x[arm][-1]["selected_estimate"] - x[arm][-1]["xeb_normalized"] for x in rows)
    z = 1.645 + 0.842                                                    # one-sided alpha 0.05, power 0.8
    need = lambda delta: math.ceil((z * sd / delta) ** 2) if delta > 0 and sd == sd else None
    summary = {
        "seeds": n, "mean_final_random": fin("random", "xeb_normalized"), "mean_final_adaptive": fin("adaptive", "xeb_normalized"),
        "paired_diff_mean": m, "paired_diff_sd": sd, "paired_diff_ci95": [m - tcrit * se, m + tcrit * se],
        "sign_test": {"adaptive_higher": pos, "random_higher": neg, "p_one_sided_adaptive_better": p_sign},
        "collision_prob_final": {"random": fin("random", "collision_probability"), "adaptive": fin("adaptive", "collision_probability")},
        "linear_xeb_final": {"random": fin("random", "xeb_linear"), "adaptive": fin("adaptive", "xeb_linear")},
        "winners_curse_inflation": {"random": infl("random"), "adaptive": infl("adaptive")},
        "seeds_needed_power80": {f"delta={dl}": need(dl) for dl in (0.01, 0.02, 0.05)},
        "qpu_estimate": {"shots_per_seed": 2 * (a.k + 1) * a.shots,
                         "seconds_per_seed_at_0.3s_per_1024_shots": round(2 * (a.k + 1) * a.shots / 1024 * 0.3, 1)},
        "wall_seconds": round(time.time() - t0, 1),
    }
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print("ledger:", ledger.verify())


if __name__ == "__main__":
    main()
