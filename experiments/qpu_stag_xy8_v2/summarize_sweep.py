import json

with open("/mnt/c/Users/Ron/osiris-cli/experiments/qpu_stag_xy8_v2/analysis_sweep.json") as f:
    d = json.load(f)

print("Offsets:", d.get("offsets_ns"))
print("Summary keys:", list(d.keys()))
if "summaries" in d:
    for edge, vals in d["summaries"].items():
        print(f"Edge {edge}:")
        for off, metrics in vals.items():
            print(f"  {off}ns -> XX: {metrics.get('XX', {}).get('mean', 0):.4f}, YY: {metrics.get('YY', {}).get('mean', 0):.4f}")
