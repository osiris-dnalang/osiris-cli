# osiris_ibm_runtime.py

import numpy as np
import time
from dataclasses import dataclass
from typing import List, Dict

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

# =========================
# CONFIG
# =========================
MAX_CIRCUITS_PER_JOB = 50
SHOTS = 4000


# =========================
# BACKEND SCORING
# =========================
@dataclass
class BackendScore:
    name: str
    score: float
    queue: int
    qubits: int
    error: float


def score_backend(backend) -> BackendScore:
    status = backend.status()
    config = backend.configuration()
    props = backend.properties()

    queue = status.pending_jobs
    qubits = config.n_qubits

    # estimate avg error
    error = 0
    if props:
        errors = []
        for g in props.gates:
            if hasattr(g, "parameters"):
                for p in g.parameters:
                    if p.name == "gate_error":
                        errors.append(p.value)
        error = np.mean(errors) if errors else 0.01

    # scoring formula (tunable)
    score = (
        qubits * 2
        - queue * 1.5
        - error * 1000
    )

    return BackendScore(
        backend.name,
        score,
        queue,
        qubits,
        error
    )


# =========================
# SELECT BEST BACKENDS
# =========================
def select_backends(service, min_qubits=8, top_k=3):
    backends = service.backends(simulator=False, operational=True)

    scored = []
    for b in backends:
        if b.configuration().n_qubits >= min_qubits:
            scored.append(score_backend(b))

    scored.sort(key=lambda x: x.score, reverse=True)

    print("\n=== BACKEND SELECTION ===")
    for s in scored[:top_k]:
        print(f"{s.name} | score={s.score:.2f} | q={s.qubits} | queue={s.queue}")

    return [service.backend(s.name) for s in scored[:top_k]]


# =========================
# BATCH CIRCUITS
# =========================
def chunk_circuits(circuits, size):
    for i in range(0, len(circuits), size):
        yield circuits[i:i + size]


# =========================
# SUBMIT JOBS (PARALLEL)
# =========================
def submit_batches(backends, circuits):
    jobs = []

    for i, batch in enumerate(chunk_circuits(circuits, MAX_CIRCUITS_PER_JOB)):
        backend = backends[i % len(backends)]

        print(f"\nSubmitting batch {i} → {backend.name} ({len(batch)} circuits)")

        transpiled = transpile(batch, backend)

        sampler = Sampler(backend)
        job = sampler.run(transpiled, shots=SHOTS)

        jobs.append((job, backend.name))

    return jobs


# =========================
# MONITOR JOBS
# =========================
def monitor_jobs(jobs):
    results = []

    print("\n=== MONITORING JOBS ===")

    for job, backend_name in jobs:
        print(f"Waiting for job on {backend_name}...")

        result = job.result()
        quasi_dists = result.quasi_dists

        results.append((backend_name, quasi_dists))

        print(f"✓ Completed on {backend_name}")

    return results


# =========================
# MAIN EXECUTION PIPELINE
# =========================
def run_ibm_pipeline(circuits):

    service = QiskitRuntimeService()  # uses your exported token

    # 1. select best backends
    backends = select_backends(service, min_qubits=circuits[0].num_qubits)

    # 2. submit batched jobs
    jobs = submit_batches(backends, circuits)

    # 3. monitor + collect
    results = monitor_jobs(jobs)

    return results
