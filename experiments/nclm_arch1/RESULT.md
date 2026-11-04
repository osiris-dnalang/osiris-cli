# NCLM-ARCH-1 result: **FAIL** — the standard arm predicts held-out documents better

Mean paired gain (standard − crsm, best held-out documents) -0.595 bits/byte, SD 0.026, n = 2; one-sided 95 % bounds [-0.712, -0.478] (minimum effect ±0.05). Wins: crsm 0, standard 2 of 2 (need 2). Held-out chat guard: +0.728 bpb (crsm − standard; PASS needs ≤ +0.1, FAIL ≥ −0.1).

| seed | crsm best @ step | standard best @ step | gain | chat change | crsm steps | standard steps |
|---|---|---|---|---|---|---|
| 200 | 3.338 @ 11800 | 2.762 @ 11800 | -0.576 | +0.737 | 12000 | 12000 |
| 201 | 3.463 @ 12000 | 2.849 @ 11400 | -0.613 | +0.719 | 12000 | 12000 |

**Caveat:** these runs hit the 12,000-step cap before early stopping, so their best may be understated: crsm s200, crsm s201, standard s200, standard s201.

Reported, not judged (Amendment 1, item 5): held-out documents at the last eval both runs of a seed reached -- s200 step 12000: crsm 3.340, standard 2.771; s201 step 12000: crsm 3.463, standard 2.850.

Unigram baseline (train split) 5.221 bpb on held-out documents; runs below it: crsm s200, crsm s201, standard s200, standard s201.
Parameters: crsm 726,304, standard 725,760. Code ba56ca0cb40295e857b240476f1cac22c1dd428e.

Per-run detail, manifests, final-eval scores and stop reasons: `results.json`.
