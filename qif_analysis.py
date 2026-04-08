import json
import math
from collections import Counter
from itertools import combinations

def shannon_entropy(counts):
    total = sum(counts.values())
    return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)

def kl_divergence_uniform(counts):
    total = sum(counts.values())
    n = len(next(iter(counts)))
    uniform_p = 1 / (2 ** n)
    kl = 0.0
    for bitstring, c in counts.items():
        p = c / total
        if p > 0:
            kl += p * math.log2(p / uniform_p)
    return kl

def mutual_information(counts, i, j):
    joint = Counter()
    xi = Counter()
    xj = Counter()
    total = sum(counts.values())

    for bitstring, c in counts.items():
        a = bitstring[i]
        b = bitstring[j]
        joint[(a,b)] += c
        xi[a] += c
        xj[b] += c

    mi = 0.0
    for (a,b), c in joint.items():
        p_ab = c / total
        p_a = xi[a] / total
        p_b = xj[b] / total
        mi += p_ab * math.log2(p_ab / (p_a * p_b))
    return mi

def extract_qbyte(counts):
    n = len(next(iter(counts)))
    
    mi_values = []
    for i, j in combinations(range(n), 2):
        mi_values.append(mutual_information(counts, i, j))

    return {
        "entropy": shannon_entropy(counts),
        "kl_divergence": kl_divergence_uniform(counts),
        "mi_mean": sum(mi_values)/len(mi_values) if mi_values else 0,
        "mi_max": max(mi_values) if mi_values else 0
    }

def load_results(path):
    with open(path, 'r') as f:
        return json.load(f)

def run_analysis(path):
    data = load_results(path)
    
    if isinstance(data, list):
        results = data
    else:
        results = [data]

    qbytes = []
    for r in results:
        counts = r.get("counts", {})
        if counts:
            qbytes.append(extract_qbyte(counts))

    print(json.dumps(qbytes, indent=2))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python qif_analysis.py results.json")
    else:
        run_analysis(sys.argv[1])
