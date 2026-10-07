#!/usr/bin/env python3
"""
evolve.py -- a bounded autonomous organism: it evolves a dynamical-decoupling
pulse sequence by calling ONLY capabilities.invoke("simulate_dd_v2", ...),
within a budget it cannot change, recording every generation in a
hash-chained ledger, then is judged against fixed sequences and random
search on HELD-OUT seeds it never saw.

  genome     LENGTH letters from I / X / Y (idle, pi-X, pi-Y)
  loop       fixed code, not a model: tournament selection (3), one-point
             crossover, per-letter mutation (1/LENGTH), one elite. Fitness =
             mean simulated fidelity on TRAIN_SEEDS.
  budget     max_evaluations (capability calls in the search) and
             max_seconds; when either runs out the search stops and says why.
  baselines  idle (no pulses), CPMG (all X), XY4 (XYXY...), and the best of a
             random search given the SAME evaluation budget.
  held-out   the organism's best genome and every baseline re-evaluated on
             HOLDOUT_SEEDS with more shots. Verdict on held-out mean fidelity
             versus the best baseline: better / worse / no difference
             (MARGIN); always preliminary -- one simulator, one noise model.
  ledger     ~/.osiris/evolve/runs.ledger.jsonl (dnalang Ledger):
             evolve_start (parameters, capability code hash), one
             evolve_generation per generation, evolve_end (held-out table,
             verdict, stop reason). Nothing else is written.
"""
import os
import random
import time

import capabilities
import genome_ledger

CAPABILITY = "simulate_dd_v2"
LENGTH = 8
POPULATION = 12
TRAIN_SEEDS = (1, 2)
HOLDOUT_SEEDS = (101, 102, 103, 104, 105)
TRAIN_SHOTS, HOLDOUT_SHOTS = 80, 200
MARGIN = 0.01
BASELINES = {"idle": "I" * LENGTH, "CPMG": "X" * LENGTH, "XY4": "XY" * (LENGTH // 2)}
LEDGER_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "evolve", "runs.ledger.jsonl")


class Budget:
    def __init__(self, max_evaluations, max_seconds):
        self.max_evaluations, self.max_seconds = max_evaluations, max_seconds
        self.used, self.start = 0, time.monotonic()

    def exhausted(self):
        if self.used >= self.max_evaluations:
            return f"evaluation budget ({self.max_evaluations}) used"
        if time.monotonic() - self.start >= self.max_seconds:
            return f"time budget ({self.max_seconds}s) used"
        return None


def _call(genome, noise, seed, shots, budget=None):
    """One capability call -- the only way the organism touches the simulator."""
    if budget is not None:
        budget.used += 1
    ok, out = capabilities.invoke(CAPABILITY, {"sequence": list(genome), "noise": noise, "seed": seed,
                                               "shots": shots})
    if not ok:
        raise RuntimeError(f"capability refused or failed: {out}")
    return out


def _fitness(genome, noise, budget):
    return sum(_call(genome, noise, s, TRAIN_SHOTS, budget) for s in TRAIN_SEEDS) / len(TRAIN_SEEDS)


def _holdout(genome, noise):
    return sum(_call(genome, noise, s, HOLDOUT_SHOTS) for s in HOLDOUT_SEEDS) / len(HOLDOUT_SEEDS)


def _ledger():
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    return genome_ledger._dnalang_ledger().Ledger(LEDGER_PATH)


def _append(led, kind, payload):
    entry = led.append(kind, payload)
    with open(LEDGER_PATH, "rb") as f:
        os.fsync(f.fileno())
    return entry


def evolve(noise="ou_slow", max_evaluations=400, max_seconds=300, seed=0, on_generation=None):
    """Runs one bounded search and its held-out judgement; returns the end payload."""
    if noise not in capabilities.REGISTRY[CAPABILITY].params["noise"][1]:
        raise ValueError(f"unknown noise model {noise!r}")
    rng = random.Random(f"evolve:{seed}")
    run_id = "evo-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + os.urandom(3).hex()
    led = _ledger()
    _append(led, "evolve_start", {"run_id": run_id, "capability": CAPABILITY,
                                  "capability_code_sha256": capabilities.code_sha256(), "noise": noise,
                                  "length": LENGTH, "population": POPULATION, "train_seeds": list(TRAIN_SEEDS),
                                  "holdout_seeds": list(HOLDOUT_SEEDS), "max_evaluations": max_evaluations,
                                  "max_seconds": max_seconds, "seed": seed})
    budget = Budget(max_evaluations, max_seconds)
    evals_per = len(TRAIN_SEEDS)

    def room():
        return budget.used + evals_per <= budget.max_evaluations and not budget.exhausted()

    pop = []
    while len(pop) < POPULATION and room():
        g = "".join(rng.choice("IXY") for _ in range(LENGTH))
        pop.append((_fitness(g, noise, budget), g))
    gen = 0
    while room() and pop:
        pop.sort(reverse=True)
        best_f, best_g = pop[0]
        _append(led, "evolve_generation", {"run_id": run_id, "generation": gen, "best": best_g,
                                           "fitness": round(best_f, 5), "evaluations": budget.used})
        if on_generation:
            on_generation(gen, best_g, best_f, budget.used)
        nxt = [pop[0]]
        while len(nxt) < POPULATION and room():
            p1 = max(rng.sample(pop, min(3, len(pop))))[1]
            p2 = max(rng.sample(pop, min(3, len(pop))))[1]
            cut = rng.randrange(1, LENGTH)
            child = "".join(c if rng.random() >= 1 / LENGTH else rng.choice("IXY") for c in p1[:cut] + p2[cut:])
            nxt.append((_fitness(child, noise, budget), child))
        pop, gen = nxt, gen + 1
    stop = budget.exhausted() or ("evaluation budget used" if not room() else "search finished")
    organism = max(pop)[1] if pop else BASELINES["idle"]

    random_budget = Budget(budget.used, max_seconds)  # random search gets the same evaluations
    rand = []
    while random_budget.used + evals_per <= random_budget.max_evaluations:
        g = "".join(rng.choice("IXY") for _ in range(LENGTH))
        rand.append((_fitness(g, noise, random_budget), g))
    candidates = dict(BASELINES)
    if rand:
        candidates["random search"] = max(rand)[1]
    table = {"organism": {"genome": organism, "fidelity": round(_holdout(organism, noise), 5)}}
    for name, g in candidates.items():
        table[name] = {"genome": g, "fidelity": round(_holdout(g, noise), 5)}
    best_name = max((k for k in table if k != "organism"), key=lambda k: table[k]["fidelity"])
    diff = table["organism"]["fidelity"] - table[best_name]["fidelity"]
    verdict = "better" if diff > MARGIN else "worse" if diff < -MARGIN else "no difference"
    end = {"run_id": run_id, "status": "complete", "stop_reason": stop, "generations": gen,
           "evaluations": budget.used, "holdout": table, "best_baseline": best_name,
           "difference": round(diff, 5), "verdict": verdict}
    entry = _append(led, "evolve_end", end)
    return dict(end, hash=entry["hash"])


def runs():
    """[(start, end-or-None)] per run, oldest first, from an intact ledger; raises ValueError if broken."""
    if not os.path.exists(LEDGER_PATH):
        return []
    led = _ledger()
    problem = led.verify()
    if problem:
        raise ValueError(f"evolve ledger broken: {problem}")
    starts, ends = {}, {}
    for e in led:
        if e.get("kind") == "evolve_start":
            starts[e["run_id"]] = e
        elif e.get("kind") == "evolve_end":
            ends[e["run_id"]] = e
    return [(s, ends.get(rid)) for rid, s in starts.items()]


def describe(end):
    t = end["holdout"]
    return (f"evolve run {end['run_id']}: organism {t['organism']['genome']} held-out fidelity "
            f"{t['organism']['fidelity']:.3f} vs best baseline {end['best_baseline']} "
            f"{t[end['best_baseline']]['fidelity']:.3f} ({end['verdict']}, preliminary: one simulator, "
            f"one noise model)")
