# RQC on Google Cloud — scope (2026-10-08)

Status: scope only. No cloud resources created, no QPU time used, no code deployed.

## 1. What exists today

| Item | State |
|---|---|
| Claim `RQC_ADVANTAGE` ("recursive circuits with feedback beat random circuit sampling, p < 0.05") | **UNTESTED** in the claims register. `RQC_RESEARCH_METHODOLOGY.md` lists its p-values (0.024, 0.018, 0.009) under *expected* results; no RQC hardware result exists. |
| Comparison in the methodology | **Not fair as written.** The RQC arm's depth grows "+1 per iteration" while the random-circuit (RCS) arm's is static, although the same document says depth is matched. |
| `osiris_ibm_execution.py` / `osiris_orchestrator.py` | **Must not be deployed.** `_submit_job` does not run a circuit: it sets `result_xeb = 0.90 − noise + random.uniform(−0.03, 0.03)`. Any pipeline built on it would publish fabricated XEB values. |
| The pasted Cloud Run / Pub/Sub guide | Targets a project `dnalang` that does not exist on this account, and container images (`osiris-rqc-orchestrator`, `osiris-job-launcher`) that were never built; every command failed and nothing was created. |
| Backends named in the methodology | `ibm_brisbane` is retired; current Heron backends would replace it. |
| Cloud pieces already in place | Project `living-language-model` (billing on); IBM key in Secret Manager as `OSIRIS_IBM_QUANTUM_TOKEN`; private versioned bucket `gs://living-language-model-osiris-evidence`; Cloud Build CI. |

## 2. A testable question

> On one Heron backend, with qubits, depth, two-qubit gate count, shots and job held equal, does closed-loop angle
> adaptation (k feedback rounds, depth fixed) raise the circuit-normalized XEB fidelity estimate compared with
> fresh random circuits of the same structure?

Two traps the design must close before any hardware run:

1. **Depth and gate count.** Both arms use the same layer structure and the same number of two-qubit gates; only
   single-qubit rotation angles differ. Anything else is a different experiment.
2. **XEB can be gamed by choosing easier circuits.** The plain linear XEB, 2ⁿ·⟨p_ideal(x)⟩ − 1, assumes Porter–Thomas
   output distributions. An adaptive loop that keeps whatever raised XEB drifts toward circuits whose ideal
   distributions are concentrated, which raises XEB without any gain in fidelity. Use the per-circuit normalized
   estimator F = (2ⁿ·Σᵢ p_ideal(xᵢ)/N − 1) / (2ⁿ·Σₓ p_ideal(x)² − 1) and report the ideal distribution's collision
   probability Σ p_ideal² for both arms. If the adaptive arm's collision probability rises, the "gain" is the
   circuits, not the hardware.

Ideal probabilities come from exact statevector simulation (feasible to ~24 qubits locally; 8–16 qubits as in the
methodology are cheap).

## 3. Stages

| Stage | What | Gate to the next stage |
|---|---|---|
| **S0 — code, local** | New `rqc/` package: circuit families (shared layer structure, seeded), exact ideal probabilities, the normalized XEB estimator, the adaptive loop, a write-ahead ledger row before every backend call; tests including a known-answer XEB check and a "concentrated circuits inflate plain XEB" test. Delete or quarantine the mock in `osiris_ibm_execution.py`. | Tests pass locally and on Cloud Build. |
| **S1 — simulation** | Run both arms on Aer with a noise model from a current Heron calibration snapshot; power analysis for the effect size worth detecting; fix trials and k. | A power estimate; the S2 criterion written. |
| **S2 — pre-registration** | Hypothesis, primary metric (normalized XEB difference, paired by seed), test, α, n, k, backend-selection rule, QPU budget, decision rules, and the collision-probability control — deposited on Zenodo before any hardware job. | DOI exists. |
| **S3 — hardware, small** | Stage-1 size (8 qubits): one Heron backend, both arms interleaved in the same jobs, ledger rows before submission, raw counts to the evidence bucket. | Result recorded PASS / FAIL / null against S2, whichever way it falls; claims register updated. |
| **S4 — cloud runner (optional)** | Only if runs become long or scheduled: see section 4. | — |

## 4. Cloud design, when S4 is wanted

Smaller than the pasted guide; everything in `living-language-model`:

- **Container:** built by Cloud Build from the repository's `rqc/` package and pushed to Artifact Registry (not
  `gcr.io`, which is deprecated).
- **Cloud Run Job** (`osiris-rqc`), started by hand with `gcloud run jobs execute` or by Cloud Scheduler. No HTTP
  launcher service and no Pub/Sub until there is a queue of work that needs one.
- **Identity:** a dedicated service account with only `secretmanager.secretAccessor` on `OSIRIS_IBM_QUANTUM_TOKEN` and
  `storage.objectCreator` on the evidence bucket. The key is mounted with
  `--set-secrets IBM_QUANTUM_TOKEN=OSIRIS_IBM_QUANTUM_TOKEN:latest`; no new secret.
- **Evidence:** the job writes the ledger row before each IBM submission, then raw counts, job IDs and calibration
  hashes to `gs://living-language-model-osiris-evidence/rqc/<run-id>/`.
- **Spend guard:** the job refuses to start without a pre-registration DOI in its configuration and stops at the
  registered QPU-second budget.

## 5. Costs (estimates)

- S0–S2: local CPU and Cloud Build minutes (within the free tier at the current suite size).
- S3 at 8 qubits, 2,000 shots, 5 seeds × 2 arms × k = 5 rounds ≈ 50 circuits ≈ 100k shots: on the order of one
  minute of Heron QPU time (the 2026-09-20 rate was ≈ 0.3 s per 1,024 shots).
- S4: Cloud Run Job seconds per run, negligible next to QPU time.

## 6. Decisions needed

1. Start S0 (write the `rqc/` package and tests, and quarantine the mock XEB)?
2. Is the question in section 2 the one you want answered, or a different RQC hypothesis?
3. QPU budget ceiling for S3.
