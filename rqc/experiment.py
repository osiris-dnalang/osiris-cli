"""The two arms, with equal shots, equal structure and a write-ahead ledger.

`sampler(circuit, shots) -> sequence of basis indices` is supplied by the caller: a local noise model for S0/S1,
an IBM backend wrapper for S3. Before every sampler call a ledger row (circuit digest, arm, round, shots) is written
and flushed, so a run that dies mid-way still shows what was attempted.

Random arm (RCS): k fresh random circuits with the same (n, depth).
Adaptive arm (RQC): start from one random circuit; each round perturb its angles, measure, and keep the candidate
if its normalized XEB is higher.
Both arms then re-measure their selected circuit (highest measured normalized XEB) on fresh shots: round "final".
Selecting the best of k noisy estimates inflates that estimate (winner's curse) in both arms; the fresh
re-measurement is unbiased, so the arms' "final" values compare feedback-driven local search with random search
at equal cost: k + 1 sampler calls and (k + 1) * shots per arm.
"""
import hashlib
import json
import os
import time

from .circuits import perturbed, random_circuit
from .sim import probabilities
from .xeb import collision_probability, linear_xeb, normalized_xeb

GENESIS = "0" * 64


class Ledger:
    """Append-only, hash-chained JSONL; each row is fsynced before the sampler runs."""

    def __init__(self, path):
        self.path = path

    def _tip(self):
        tip = GENESIS
        if os.path.exists(self.path):
            for line in open(self.path, encoding="utf-8"):
                if line.strip():
                    tip = json.loads(line)["hash"]
        return tip

    def append(self, kind, payload):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        row = {"kind": kind, "payload": payload, "prev": self._tip(), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        row["hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return row

    def verify(self):
        prev = GENESIS
        for i, line in enumerate(open(self.path, encoding="utf-8")):
            row = json.loads(line)
            body = {k: row[k] for k in ("kind", "payload", "prev", "ts")}
            if row["prev"] != prev or row["hash"] != hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
                return False, f"row {i}: chain broken"
            prev = row["hash"]
        return True, "ok"


def _measure(circuit, sampler, shots, ledger, arm, rnd):
    ledger.append("RQC_SUBMIT", {"arm": arm, "round": rnd, "circuit_sha256": circuit.digest(), "n": circuit.n,
                                 "depth": circuit.depth, "two_qubit_gates": circuit.two_qubit_gates, "shots": shots})
    samples = sampler(circuit, shots)
    p = probabilities(circuit)
    result = {"arm": arm, "round": rnd, "circuit_sha256": circuit.digest(), "shots": len(samples),
              "xeb_normalized": normalized_xeb(p, samples), "xeb_linear": linear_xeb(p, samples),
              "collision_probability": collision_probability(p)}
    ledger.append("RQC_RESULT", result)
    return result


def _remeasure_best(arm, circuits, results, sampler, shots, ledger):
    i = max(range(len(results)), key=lambda j: results[j]["xeb_normalized"])
    final = _measure(circuits[i], sampler, shots, ledger, arm, "final")
    final["selected_round"] = results[i]["round"]
    final["selected_estimate"] = results[i]["xeb_normalized"]
    return final


def run_random(n, depth, k, shots, sampler, ledger, seed):
    circuits = [random_circuit(n, depth, seed * 1000 + r) for r in range(k)]
    results = [_measure(c, sampler, shots, ledger, "random", r) for r, c in enumerate(circuits)]
    return results + [_remeasure_best("random", circuits, results, sampler, shots, ledger)]


def run_adaptive(n, depth, k, shots, sampler, ledger, seed, sigma=0.2):
    best = random_circuit(n, depth, seed * 1000)       # the same starting circuit as the random arm's round 0
    best_res = _measure(best, sampler, shots, ledger, "adaptive", 0)
    circuits, results = [best], [best_res]
    for r in range(1, k):
        cand = perturbed(best, sigma, seed * 1000 + 500 + r)
        res = _measure(cand, sampler, shots, ledger, "adaptive", r)
        circuits.append(cand)
        results.append(res)
        if res["xeb_normalized"] > best_res["xeb_normalized"]:
            best, best_res = cand, res
    return results + [_remeasure_best("adaptive", circuits, results, sampler, shots, ledger)]
