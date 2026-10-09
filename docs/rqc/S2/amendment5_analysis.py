#!/usr/bin/env python3
"""Amendment 5 (draft): offline budget sensitivity and power, from local files only (no network).

Inputs: docs/rqc/S2/budget_audit.json; S1 simulation results docs/rqc/S1/results.json (ibm_fez noise model, Aer) and
docs/rqc/S1_willow/results.json (Willow model, Cirq QVM). Output: docs/rqc/S2/amendment5_analysis.json.

Power is for the registered test (one-sided t-test of b0 in d_s = b0 + b1 dc_s + e_s, alpha 0.05, n - 2 df):
  1. analytic: noncentral t with the residual SD and design inflation estimated from each S1 file;
  2. Monte Carlo: bootstrap S1 seeds (d_s, dc_s), recentre b0 at the target effect, refit, test;
  3. 1,500 shots: per-seed shot-noise variance of the final estimates at 2,000 shots is computed from the ideal
     distributions of the reconstructed final circuits under a depolarizing approximation (q = F p + (1 - F)/D with
     F the measured final normalized XEB); extra noise of variance v (2000/1500 - 1) is added to d_s;
  4. block clustering: a shared block effect u_b ~ N(0, tau^2) added to d_s of the 40 seeds of each block.
All random draws use numpy default_rng(20261008). Nothing here was tuned on these outputs.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from rqc.circuits import perturbed, random_circuit  # noqa: E402
from rqc.sim import probabilities  # noqa: E402

N, DEPTH, K, SIGMA = 8, 6, 5, 0.2
RNG_SEED, REPS = 20261008, 20000


# ---- budget ------------------------------------------------------------------------------------------------

def billed(shots, pubs, rate, per_pub, c):
    return math.ceil(rate * shots + per_pub * pubs + c)


def budget():
    audit = json.load(open(os.path.join(HERE, "budget_audit.json")))
    fit = []
    for j in audit["jobs_with_execution_time"]:
        fit.append((j["execution_s"], j["billed_s"]))
    scen = []
    for rate in (0.262e-3, 0.27e-3, 0.30e-3, 0.35e-3, 0.40e-3):
        for per_pub in (0.0135, 0.03, 0.06):
            for c in (1.73, 3.0, 5.0):
                job = billed(160000, 80, rate, per_pub, c)
                scen.append({"rate_ms_per_shot": rate * 1e3, "per_pub_s": per_pub, "per_job_c_s": c,
                             "billed_per_job_s": job, "total_12_jobs_s": 12 * job,
                             "seeds_completed_under_600": _completed(job, 48)})
    frozen = billed(2000, 1, 0.262e-3, 0.0, 1.73)
    return {"model": "billed = ceil(rate x shots + per_pub x pubs + c), whole seconds",
            "fit_points_execution_vs_billed": fit,
            "central_case": {"billed_per_job_s": billed(160000, 80, 0.262e-3, 0.0135, 1.73),
                             "total_s": 12 * billed(160000, 80, 0.262e-3, 0.0135, 1.73)},
            "registered_projection": {"per_job_s": 48, "total_s": 576},
            "frozen_960_job_schedule_central_s": 960 * frozen,
            "break_even_rate_ms_per_shot_at_c1.73_pp0.0135": round((50 - 1.73 - 80 * 0.0135) / 160000 * 1e3, 4),
            "scenarios": scen,
            "not_modelled": ["queue time (not billed in observed jobs)", "provider behaviour when the account limit "
                             "is reached mid-job (unknown)", "per-pub overhead at 80 pubs (only a 20-pub job observed)",
                             "different per-shot time of 8-qubit 21-CZ circuits vs the observed 156-qubit ones"]}


def _completed(actual_job_s, projected_job_s, budget_s=600, jobs_per_block=6, blocks=2):
    spent, seeds = 0, 0
    for _ in range(blocks):
        ok = True
        for _ in range(jobs_per_block):
            if spent + max(actual_job_s, 0) > budget_s and spent + projected_job_s > budget_s:
                ok = False
                break
            if spent + projected_job_s > budget_s:
                ok = False
                break
            spent += max(actual_job_s, projected_job_s)       # rqc.control counts max(reported, reserved)
        if not ok:
            break
        seeds += 40
    return seeds


# ---- S1 data -------------------------------------------------------------------------------------------------

def load(path):
    rows = json.load(open(path))["rows"]
    d = np.array([r["adaptive"][-1]["xeb_normalized"] - r["random"][-1]["xeb_normalized"] for r in rows])
    dc = np.array([r["adaptive"][-1]["collision_probability"] - r["random"][-1]["collision_probability"]
                   for r in rows])
    return rows, d, dc


def fit(d, dc):
    X = np.column_stack([np.ones_like(dc), dc])
    beta, *_ = np.linalg.lstsq(X, d, rcond=None)
    resid = d - X @ beta
    n = len(d)
    s2 = resid @ resid / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta, math.sqrt(s2), cov, resid


def p_one_sided(d, dc):
    beta, s, cov, _ = fit(d, dc)
    t = beta[0] / math.sqrt(cov[0, 0])
    return stats.t.sf(t, len(d) - 2)


def final_circuits(row, seed):
    """Rebuild each arm's final circuit from the seed and the recorded per-round results; checked by digest."""
    out = {}
    rnd = row["random"]
    sel = rnd[-1]["selected_round"]
    c = random_circuit(N, DEPTH, seed * 1000 + sel)
    assert c.digest() == rnd[-1]["circuit_sha256"]
    out["random"] = c
    ada = row["adaptive"]
    best = random_circuit(N, DEPTH, seed * 1000)
    best_x = ada[0]["xeb_normalized"]
    circs = [best]
    for r in range(1, K):
        cand = perturbed(best, SIGMA, seed * 1000 + 500 + r)
        circs.append(cand)
        if ada[r]["xeb_normalized"] > best_x:
            best, best_x = cand, ada[r]["xeb_normalized"]
    c = circs[ada[-1]["selected_round"]]
    assert c.digest() == ada[-1]["circuit_sha256"]
    out["adaptive"] = c
    return out


def shot_var(circuit, F, shots):
    p = probabilities(circuit)
    D = len(p)
    f = (D * p - 1) / (D * np.sum(p ** 2) - 1)
    F = min(max(F, 0.0), 1.0)
    q = F * p + (1 - F) / D
    return float((q @ f ** 2 - (q @ f) ** 2) / shots)


def power_block(name, path):
    rows, d, dc = load(path)
    beta, s, cov, resid = fit(d, dc)
    n0 = len(d)
    infl = cov[0, 0] / (s ** 2 / n0)
    seeds = [r["seed"] for r in rows]
    v = []
    for r, sd in zip(rows, seeds):
        fc = final_circuits(r, sd)
        v.append(shot_var(fc["random"], r["random"][-1]["xeb_normalized"], 2000)
                 + shot_var(fc["adaptive"], r["adaptive"][-1]["xeb_normalized"], 2000))
    v = np.array(v)
    out = {"file": os.path.relpath(path, ROOT), "seeds": n0, "b0_hat": float(beta[0]),
           "b0_se": math.sqrt(cov[0, 0]), "residual_sd": s, "design_inflation": infl,
           "shot_noise_sd_of_d_at_2000": float(math.sqrt(v.mean())),
           "shot_noise_share_of_residual_variance": float(v.mean() / s ** 2)}
    an = {}
    for n in (16, 40, 80):
        for delta in (0.012, 0.02):
            se = s * math.sqrt(infl / n)
            tc = stats.t.ppf(0.95, n - 2)
            an[f"n={n},b0={delta}"] = float(stats.nct.sf(tc, n - 2, delta / se))
    out["analytic_power"] = an
    rng = np.random.default_rng(RNG_SEED)
    mc = {}
    extra_1500 = v * (2000 / 1500 - 1)
    for shots in (2000, 1500):
        for n in (40, 80):
            for delta in (0.0, 0.012, 0.02):
                for tau in ((0.0, 0.005, 0.01) if shots == 2000 and n == 80 else (0.0,)):
                    rej = 0
                    for _ in range(REPS // 4):
                        idx = rng.integers(0, n0, size=n)
                        dd = d[idx] - beta[0] + delta
                        if shots == 1500:
                            dd = dd + rng.normal(0, np.sqrt(extra_1500[idx]))
                        if tau:
                            blocks = np.repeat(rng.normal(0, tau, size=math.ceil(n / 40)), 40)[:n]
                            dd = dd + blocks
                        if p_one_sided(dd, dc[idx]) < 0.05:
                            rej += 1
                    k = REPS // 4
                    mc[f"shots={shots},n={n},b0={delta},tau={tau}"] = {
                        "rate": rej / k, "mc_se": math.sqrt((rej / k) * (1 - rej / k) / k), "reps": k}
    out["monte_carlo"] = mc
    return out


def main():
    res = {"budget": budget(),
           "power": [power_block("ibm_fez", os.path.join(ROOT, "docs/rqc/S1/results.json")),
                     power_block("willow", os.path.join(ROOT, "docs/rqc/S1_willow/results.json"))],
           "rng_seed": RNG_SEED,
           "limitations": [
               "S1 is simulation (two noise models that disagree on the sign of b0); hardware variance is unknown",
               "bootstrap from 30 seeds understates tail behaviour and reuses each S1 seed many times",
               "1,500-shot model adds only final-estimate shot noise; fewer shots also change which circuits are "
               "selected during search (accept/reject and best-of-k), which can change the effect itself - not "
               "assessable from S1 without re-simulating at 1,500 shots",
               "the depolarizing approximation for shot-noise variance is an assumption",
               "tau is a hypothesised arm-by-job interaction; its size on hardware is unknown"]}
    with open(os.path.join(HERE, "amendment5_analysis.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"central_budget": res["budget"]["central_case"],
                      "power": [{k: p[k] for k in ("file", "residual_sd", "shot_noise_share_of_residual_variance",
                                                   "analytic_power")} for p in res["power"]]}, indent=1))


if __name__ == "__main__":
    main()
