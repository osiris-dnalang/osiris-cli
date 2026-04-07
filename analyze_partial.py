import json
import numpy as np
from qiskit import qpy
import os

def decode_qpy_circuits(qpy_dir):
    """Decode QPY circuit files to extract metadata like depth."""
    circuits = []
    for file in os.listdir(qpy_dir):
        if file.endswith('.qpy'):
            with open(os.path.join(qpy_dir, file), 'rb') as f:
                qc = qpy.load(f)[0]  # Assume one circuit per file
                # Extract depth from circuit name or metadata
                depth = int(file.split('_')[-1].split('.')[0]) if '_' in file else 1
                circuits.append({'circuit': qc, 'depth': depth, 'file': file})
    return circuits

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

def analyze_partial_results(results_dir, qpy_dir):
    """Analyze partial results from completed jobs."""
    circuits = decode_qpy_circuits(qpy_dir)
    results = {}

    for file in os.listdir(results_dir):
        if file.endswith('.json'):
            with open(os.path.join(results_dir, file)) as f:
                data = json.load(f)
                # Assume data has counts and metadata
                depth = data.get('depth', 1)
                counts = data['counts']

                if depth not in results:
                    results[depth] = []

                row = [compute_C(counts, 0, k) for k in range(1, 8)]
                results[depth].append(row)

    # Aggregate
    final = {}
    for depth, vals in results.items():
        arr = np.array(vals)
        mean = np.mean(arr, axis=0)
        std = np.std(arr, axis=0)
        Z = mean / std

        final[depth] = {
            "mean": mean.tolist(),
            "std": std.tolist(),
            "Z": Z.tolist()
        }

    with open("partial_analysis.json", "w") as f:
        json.dump(final, f, indent=2)

    return final

# Example usage
if __name__ == "__main__":
    results = analyze_partial_results("results", "circuits")
    print("Partial analysis complete. Check partial_analysis.json")