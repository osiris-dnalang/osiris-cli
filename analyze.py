import json
import numpy as np

def compute_C(counts, i, k):
    shots = sum(counts.values())
    C = 0
    Zi = 0
    Zk = 0

    for bitstring, c in counts.items():
        b = bitstring[::-1]
        zi = 1 if b[i] == '0' else -1
        zk = 1 if b[k] == '0' else -1

        C += zi * zk * c
        Zi += zi * c
        Zk += zk * c

    C /= shots
    Zi /= shots
    Zk /= shots

    return C - Zi * Zk


with open("results.json") as f:
    data = json.load(f)

results = {}

for entry in data:
    depth = entry["depth"]
    counts = entry["counts"]

    if depth not in results:
        results[depth] = []

    row = []
    for k in range(1, 8):
        row.append(compute_C(counts, 0, k))

    results[depth].append(row)

# Aggregate
final = {}

for depth, vals in results.items():
    arr = np.array(vals)
    mean = np.mean(arr, axis=0)
    std = np.std(arr, axis=0)

    final[depth] = {
        "mean": mean.tolist(),
        "std": std.tolist(),
        "Z": (mean / std).tolist()
    }

with open("analysis.json", "w") as f:
    json.dump(final, f, indent=2)