from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from generate_circuits import generate_batch
from qiskit import transpile
import json

service = QiskitRuntimeService()
backend = service.backend("ibm_fez")

circuits, meta = generate_batch()

# Transpile circuits
transpiled_circuits = transpile(circuits, backend)

sampler = Sampler(backend)

jobs = []
for circuit in transpiled_circuits:
    job = sampler.run([circuit], shots=10000)
    jobs.append(job)

results = []
for job in jobs:
    result = job.result()
    results.append(result)

data = []
for i, result in enumerate(results):
    counts = result.quasi_dists[0]  # For Sampler, it's quasi_dists
    # Convert to dict
    counts_dict = {format(k, '08b')[::-1]: int(v * 10000) for k, v in counts.items()}  # Approximate
    data.append({
        "counts": counts_dict,
        "depth": meta[i]["depth"]
    })

with open("results.json", "w") as f:
    json.dump(data, f)