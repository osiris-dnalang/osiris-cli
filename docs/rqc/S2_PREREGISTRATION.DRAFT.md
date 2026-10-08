# RQC S2 — pre-registration (DRAFT, not deposited)

**Status:** draft for review, 2026-10-08. It becomes binding when deposited on Zenodo with its SHA-256; no hardware job
runs before that. **Repository:** osiris-dnalang/osiris-cli, branch `feat/rqc-s0`.

## 1. Question

On one IBM Heron backend, with qubits, depth, two-qubit gate count, shots and session held equal, does closed-loop angle
adaptation (feedback-driven local search) raise the **fresh-re-measured, circuit-normalized XEB fidelity** of the selected
circuit compared with random search of the same structure and cost — **at equal output concentration**?

## 2. Frozen code and parameters (amendment 4)

- Search and selection: `rqc/experiment.py` at commit **`06761071`** (`run_random`, `run_adaptive`). Nothing in it is
  changed for S2. Parameters: k = 5 search rounds per arm; adaptive step σ = 0.2 rad (Gaussian, all angles); selection =
  highest measured normalized XEB among the k rounds; then one fresh re-measurement of the selected circuit
  (round `final`). Cost per arm per seed: k + 1 = 6 sampler calls.
- Circuits: n = 8 qubits, depth 6, brickwork CZ on a line (21 CZ per circuit), angles from `rqc/circuits.py` at the same commit.
- Shots: 2,000 per sampler call. Estimator: `rqc/xeb.py` `normalized_xeb`, ideal probabilities from `rqc/sim.py`.
- Seeds: **1000–1079** (80 seeds). Simulation used 100–129; no S2 seed has been run anywhere.
- These were chosen from S1 without tuning on hardware; no parameter may change after deposit.

## 3. Backend and qubits (no discretion)

- Backend: the first, in ascending alphabetical order, of the IBM Heron-family backends reported operational on the UTC
  date of the first job (on 2026-10-08 that would be `ibm_fez`).
- Qubits: among all simple paths of 8 connected qubits on that backend, the one with the lowest sum of CZ errors in the
  calibration snapshot taken immediately before the first job (ties: lexicographically smallest qubit list). The
  snapshot's SHA-256 is written to the ledger before the first job.
- Both arms of a seed run in the same session; the arm that runs first alternates with seed parity.

## 4. Primary estimand and test (amendment 1)

For each seed s: d_s = final normalized XEB (adaptive − random); Δc_s = final collision probability (adaptive − random).
Fit by ordinary least squares d_s = β₀ + β₁·Δc_s + ε_s.

- **Primary estimand: β₀**, the adaptive gain at equal output concentration.
- **Test:** one-sided t-test of H₀: β₀ ≤ 0 against H₁: β₀ > 0, α = 0.05, n − 2 degrees of freedom; report β₀ with its 95%
  confidence interval.
- **Decision:** *feedback helps at this scale* only if the one-sided p < 0.05; otherwise *no detected gain*. Either
  result is published and recorded in the claims register (`RQC_ADVANTAGE`: SUPPORTED at n = 8, depth 6, or NULL).

## 5. Secondary (reported, not used for the decision)

- Raw paired mean difference of final normalized XEB, with 95% CI.
- Sign test on d_s.
- Mean Δc_s (does adaptation select more concentrated circuits?) and β₁.
- Winner's-curse inflation per arm (selected-round estimate minus fresh re-measurement).
- Plain linear XEB, descriptively only; it is not an estimate of fidelity for these circuits.

## 6. Power and what a null means (amendment 2)

Sizing from S1 (simulation only), collision-adjusted, residual SD ≈ 0.047:

| Noise model (S1) | β₀ (adjusted) | 95% CI |
|---|---|---|
| ibm_fez (Aer, live calibration) | +0.010 | −0.007 to +0.028 |
| willow_pink (Cirq QVM) | −0.003 | −0.021 to +0.016 |

With 80 seeds the test has about 75% power for β₀ = 0.012 and above 99% for β₀ = 0.02. **S2 is powered to detect gains
of about 0.012 or larger. A null result does not rule out smaller gains**, and the two noise models already disagree on
whether any gain exists; a null would be reported in exactly those terms.

## 7. Exploratory results already seen (amendment 3)

S1's sign test (20 of 30 seeds favouring adaptation, one-sided p = 0.049, ibm_fez model) was computed on the same
exploratory data as every other S1 number and is not corroboration. On the Willow model the same test gave 15 of 30
(p = 0.57). Neither carries confirmatory weight.

## 8. Budget and stopping

- QPU ceiling: **10 minutes** of billed QPU time. Estimate: 80 seeds × 24,000 shots ≈ 9.3 minutes at the 2026-09 rate of
  about 0.3 s per 1,024 shots.
- The run stops at the ceiling. If it stops early, the analysis uses the completed seeds and the report states that the
  registered size was not reached and gives the achieved power.
- No interim analysis: results are not examined until all seeds finish or the ceiling is reached.

## 9. Provenance

A hash-chained ledger row is written before every sampler call (`rqc.experiment.Ledger`). Raw counts, IBM job IDs and
the calibration snapshot hash go to `gs://living-language-model-osiris-evidence/rqc/S2/`. The analysis script is
`docs/rqc/s1_adjusted.py` applied unchanged to the S2 results file.

## 10. Out of scope

Stim / QEC decoder benchmarking is a separate pre-registration. Larger n, other depths and other backends are later
studies.
