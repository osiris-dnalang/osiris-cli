"""S2 hardware tooling: backend and qubit selection by the registered rules, a Sampler that writes evidence for
every job, and a hard stop at the registered QPU budget. Requires qiskit and qiskit-ibm-runtime (optional extras).

Nothing here decides anything about the experiment: rqc.experiment drives the arms and writes the ledger row before
each sampler call; this module only turns a circuit into counts on hardware, records the job, and refuses to go on
once the budget is spent.
"""
import hashlib
import json
import os
import time

import numpy as np

from .circuits import to_qiskit
from .samplers import calibration_record, counts_to_indices


class BudgetExhausted(RuntimeError):
    """Raised before a job when the registered QPU budget has been used."""


def choose_backend(backends):
    """Registered rule: the first, in ascending alphabetical order, operational Heron-family backend."""
    heron = []
    for b in backends:
        fam = (getattr(b.configuration(), "processor_type", None) or {}).get("family")
        status = b.status()
        if fam == "Heron" and getattr(status, "operational", True):
            heron.append(b)
    if not heron:
        raise RuntimeError("no operational Heron-family backend")
    return sorted(heron, key=lambda b: b.name)[0]


def best_path(backend, n):
    """Registered rule: among all simple paths of n connected qubits, the one with the lowest sum of CZ errors in the
    current calibration; ties broken by the lexicographically smallest qubit list. Exhaustive search."""
    target = backend.target
    err = {}
    for qargs, props in target["cz"].items():
        if props is not None and props.error is not None:
            err[frozenset(qargs)] = props.error
    adj = {}
    for a, b in (tuple(e) for e in err):
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    best = [None, None]                                      # (cost, path)

    def dfs(path, cost):
        if best[0] is not None and cost > best[0]:
            return
        if len(path) == n:
            key = (cost, path)
            if best[0] is None or key < (best[0], best[1]):
                best[0], best[1] = cost, list(path)
            return
        for nb in sorted(adj.get(path[-1], ())):
            if nb not in path:
                dfs(path + [nb], cost + err[frozenset((path[-1], nb))])

    for start in sorted(adj):
        dfs([start], 0.0)
    if best[1] is None:
        raise RuntimeError(f"no path of {n} connected qubits with calibrated CZ errors")
    # a path and its reverse are the same qubits; report the lexicographically smaller orientation
    path = min(best[1], best[1][::-1])
    return path, best[0]


class HardwareSampler:
    """sampler(circuit, shots) -> indices. Each call runs one job, stores its raw counts and job id under
    evidence_dir, and adds the job's billed quantum seconds to the budget. Raises BudgetExhausted before a job
    when the spent seconds have reached the budget."""

    def __init__(self, backend, layout, evidence_dir, budget_seconds, sampler_factory=None, usage_of=None):
        self.backend, self.layout = backend, list(layout)
        self.evidence_dir, self.budget = evidence_dir, float(budget_seconds)
        self.spent, self.jobs = 0.0, 0
        os.makedirs(evidence_dir, exist_ok=True)
        if sampler_factory is None:
            from qiskit_ibm_runtime import SamplerV2
            sampler_factory = lambda: SamplerV2(mode=backend)
        self._sampler = sampler_factory()
        self._usage_of = usage_of or _quantum_seconds
        self.calibration = calibration_record(backend)

    def __call__(self, circuit, shots):
        from qiskit import transpile
        if self.spent >= self.budget:
            raise BudgetExhausted(f"QPU budget {self.budget:.0f}s used ({self.spent:.1f}s); no further jobs")
        tqc = transpile(to_qiskit(circuit), backend=self.backend, initial_layout=self.layout,
                        optimization_level=1, seed_transpiler=0)
        job = self._sampler.run([tqc], shots=shots)
        result = job.result()
        counts = result[0].data.meas.get_counts()
        used = self._usage_of(job)
        self.spent += used
        self.jobs += 1
        rec = {"job_id": job.job_id(), "backend": self.backend.name, "layout": self.layout,
               "circuit_sha256": circuit.digest(), "shots": shots, "quantum_seconds": used,
               "spent_total": self.spent, "calibration": self.calibration,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "counts": counts}
        body = json.dumps(rec, sort_keys=True).encode()
        name = f"{self.jobs:04d}_{circuit.digest()[:12]}_{hashlib.sha256(body).hexdigest()[:8]}.json"
        with open(os.path.join(self.evidence_dir, name), "wb") as f:
            f.write(body)
        return counts_to_indices(counts)


def _quantum_seconds(job):
    """Billed quantum seconds of a finished runtime job (0.0 when the mode has no billing, e.g. local testing)."""
    try:
        usage = job.usage()
        return float(usage if not isinstance(usage, dict) else usage.get("quantum_seconds", 0.0))
    except Exception:  # noqa: BLE001 - local/fake modes have no usage
        try:
            return float(job.metrics().get("usage", {}).get("quantum_seconds", 0.0))
        except Exception:  # noqa: BLE001
            return 0.0
