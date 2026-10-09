"""Collision-adjusted paired difference (exploratory sizing for S2): d_s = b0 + b1 * dc_s + e_s, where
d_s = final normalized XEB (adaptive - random) and dc_s = final collision probability (adaptive - random).
b0 is the adaptive gain at equal output concentration."""
import json, math, sys
import numpy as np

def analyse(path):
    rows = json.load(open(path))["rows"]
    d = np.array([r["adaptive"][-1]["xeb_normalized"] - r["random"][-1]["xeb_normalized"] for r in rows])
    dc = np.array([r["adaptive"][-1]["collision_probability"] - r["random"][-1]["collision_probability"] for r in rows])
    X = np.column_stack([np.ones_like(dc), dc]); beta, res, *_ = np.linalg.lstsq(X, d, rcond=None)
    n, p = len(d), 2
    resid = d - X @ beta; s2 = resid @ resid / (n - p); cov = s2 * np.linalg.inv(X.T @ X)
    se0 = math.sqrt(cov[0, 0]); sd_res = math.sqrt(s2)
    z = 1.645 + 0.842
    need = lambda delta: math.ceil((z * sd_res / delta) ** 2 * (cov[0, 0] / (s2 / n)))   # inflate for estimating b1
    return {"n": n, "raw_mean": float(d.mean()), "raw_sd": float(d.std(ddof=1)),
            "b0_adjusted": float(beta[0]), "b0_se": se0, "b0_ci95": [float(beta[0] - 2.048 * se0), float(beta[0] + 2.048 * se0)],
            "b1_per_unit_collision": float(beta[1]), "mean_dc": float(dc.mean()),
            "seeds_for_power80": {f"delta={x}": need(x) for x in (0.012, 0.02, 0.03)}}

for path in sys.argv[1:]:
    print(path, json.dumps(analyse(path), indent=1))
