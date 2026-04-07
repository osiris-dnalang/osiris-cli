from qiskit_ibm_runtime import QiskitRuntimeService
from generate_circuits import generate_batch
import json

service = QiskitRuntimeService()
backend = service.backend("ibm_torino")

circuits, meta = generate_batch()

job = backend.run(circuits, shots=10000)
result = job.result()

data = []
for i, counts in enumerate(result.get_counts()):
    data.append({
        "counts": counts,
        "depth": meta[i]["depth"]
    })

with open("results.json", "w") as f:
    json.dump(data, f)