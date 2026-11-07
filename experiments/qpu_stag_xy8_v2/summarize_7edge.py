import json

with open("/mnt/c/Users/Ron/osiris-cli/experiments/qpu_stag_xy8_v2/analysis_7edge.json") as f:
    d = json.load(f)

summaries = d["edge_summaries"]
print(f"{'Edge':<10} | {'IDLE XX':<10} | {'SYNC XX':<10} | {'STAG XX':<10} | {'Delta':<10}")
print("-" * 55)
for edge in ["(14,15)", "(15,19)", "(19,35)", "(35,34)", "(34,33)", "(33,32)", "(32,31)"]:
    s = summaries[edge]
    idle_xx = s["IDLE"]["XX"]["mean"]
    sync_xx = s["SYNC_XY8"]["XX"]["mean"]
    stag_xx = s["STAG_XY8"]["XX"]["mean"]
    delta = stag_xx - sync_xx
    print(f"{edge:<10} | {idle_xx:8.4f}   | {sync_xx:8.4f}   | {stag_xx:8.4f}   | {delta:+8.4f}")
