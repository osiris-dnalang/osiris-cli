from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from generate_circuits import generate_batch
from qiskit import transpile
import json
import os

# Token must be set via environment variable — never hardcode credentials
if not os.environ.get("IBM_QUANTUM_TOKEN"):
    raise EnvironmentError(
        "IBM_QUANTUM_TOKEN not set. Export it:\n"
        "  export IBM_QUANTUM_TOKEN='your_token_from_quantum.ibm.com'"
    )

service = QiskitRuntimeService()
backend = service.backend("ibm_fez")

circuits, meta = generate_batch()

# Transpile circuits
transpiled_circuits = transpile(circuits, backend)

sampler = Sampler(backend)

jobs = []
for circuit in transpiled_circuits:
    job = sampler.run([circuit], shots=32000)  # Changed to 32000
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