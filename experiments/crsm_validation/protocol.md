# CRSM validation protocol (draft)

**Status:** Proposed protocol only; not pre-registered and not executed.  
**Purpose:** Make CRSM claims testable without treating configured parameters, simulation output, statistical significance, or a passing software test as physical confirmation.

## 1. Governance and provenance

- Keep all work on `research/crsm-evidence-governance-draft` until human review.
- Do not edit the canonical claims register, promote evidence, sign grants, mutate the genome ledger, submit QPU jobs, or publish a DOI as part of this protocol.
- Record repository commit, source-file hashes, environment lock, commands, random seeds, stdout/stderr, and artifact hashes for every later run.
- Preserve raw data immutably. Derived datasets must record their parent hashes and transformations.
- Use claim states conservatively: hypothesis/proposed before measurement; `NOT_MEASURED` where a quantity is configured or no supporting measurement is on record; retain existing `REFUTED`, `ARTIFACT`, and `NULL` verdicts unless new evidence is independently reviewed and the human authorizes a register change.

## 2. Work packages and gates

### WP0 — Freeze definitions (required before execution)

Write down the exact estimand, units, sampling unit, inclusion/exclusion criteria, primary outcome, null hypothesis, alternative hypothesis, statistical test, confidence interval, multiplicity policy, stopping rule, and failure criteria. Timestamp and hash the protocol before examining outcomes.

**Gate:** No confirmatory analysis until definitions are frozen.

### WP1 — Mathematical and dimensional audit

1. Specify a valid 3-D geometry for the claimed tetrahedral lattice; provide vertices and derive the target angle.
2. Verify every equation symbol, SI unit, and unit transformation.
3. Correct the angle identity: `arccos(1/3)` is about 70.53 degrees, not 51.843 degrees. Do not substitute a different angle without an explicit derivation.
4. Distinguish Casimir energy per area from energy density and from total energy.
5. Derive field, flux, and any stress-energy / metric relationship from stated equations and boundary conditions; do not infer propulsion from flux magnitude alone.

**Gate:** Independent reviewer reproduces the algebra and dimensional checks. Failure means the associated claim remains unsupported or is revised as a hypothesis.

### WP2 — Numerical implementation verification

- Pin source commit, dependency versions, configuration, input hashes, random seeds, and numerical tolerances.
- Compare implementation against analytically solvable limiting cases and independent reference calculations.
- Add unit tests for units, geometry, sign conventions, conservation, and limiting behavior.
- Separate code-verification tests from validation against physical observations.

**Gate:** Report tests and logs only after they actually run. A software test does not validate the physical model.

### WP3 — Quantum entropy claim

Required inputs: raw per-job results/counts, backend and calibration metadata, job identifiers, circuit definitions/hashes, shots, run times, data selection history, and exact analysis code.

Pre-specify:
- The experimental unit (job, circuit, calibration window, or independent run) and how dependence is handled.
- Entropy estimator, bias correction if needed, baseline/control families, effect size, uncertainty interval, and test statistic.
- Primary vs secondary comparisons and a multiplicity adjustment.
- Exclusion criteria before unblinding; include all valid conditions and negative/null results.
- A sensitivity analysis for pseudoreplication, backend drift, circuit-family imbalance, and alternative reasonable baselines.

Do not treat 1,430 jobs as 1,430 independent samples unless the design justifies independence. Do not repeat `Z ~= 29.83` or `p < 1e-6` as established results until raw data and a reproducible analysis substantiate the exact claim.

**Gate:** Independent re-run from immutable data, plus a separate replication with frozen analysis.

### WP4 — Electromagnetic / Casimir / propulsion claims

- Define the apparatus, dielectric properties, geometry, boundary conditions, measurement bandwidth, and calibration traceability.
- Distinguish signed net power through an oriented closed surface from an integral of field magnitudes.
- Close the energy and momentum budgets; record electrical input, thermal losses, radiation, mechanical forces, vibration, and environmental effects.
- Blind or randomize control conditions where practical. Include sham, conventional-theory, and sign/random-angle controls.
- Publish uncertainty budgets and all null outcomes.

**Gate:** No claim of propulsion, mass reduction, or anomalous vacuum energy from simulation alone.

### WP5 — Galaxy rotation curves

- Use a named, versioned public dataset and preserve source URLs/version/hash.
- Freeze quality cuts, distance/inclination treatment, baryonic components, likelihood, priors, and train/held-out split.
- Fit CRSM and conventional comparator models using the same observations and uncertainty assumptions.
- Report residual diagnostics, uncertainty intervals, complexity/parameter count, sensitivity to sample selection, and held-out predictive performance.
- Do not claim superiority from a visually flatter curve or selected examples.

**Gate:** Independent analysis and held-out performance that survives sensitivity checks.

## 3. Reporting template

For each claim, report:

| Field | Required content |
|---|---|
| Claim ID | Stable identifier, existing verdict, and proposed status (if any) |
| Hypothesis | Exact falsifiable statement and scope |
| Data | Immutable artifact identifiers and hashes |
| Method | Frozen analysis commit and environment |
| Controls | Null, sham, negative, and conventional baselines |
| Result | Effect size, uncertainty interval, test statistic, corrected p-value where appropriate |
| Deviations | Every deviation, exclusion, and exploratory analysis |
| Replication | Independent operator/environment and result |
| Limitations | Known confounds and what the result does not establish |
| Review | Human decision and evidence-ledger reference, if later authorized |

## 4. Failure and stop conditions

Stop confirmatory interpretation if raw data are missing, units are inconsistent, the sampling unit is unclear, the protocol was changed after outcome inspection, controls fail, the result depends on undocumented exclusions, or independent replication fails. Preserve the failure and record a null/refuted/artifact proposal for human review; do not silently rewrite the hypothesis.

## 5. Execution status

This file is a draft protocol. It has not been timestamped as a pre-registration, executed against hardware or astrophysical data, independently reviewed, or used to promote any claim.
