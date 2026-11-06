# CRSM manuscript claim audit

**Status:** Draft; evidence review only  
**Repository:** `osiris-dnalang/osiris-cli`  
**Review base:** `main` at `6bfcf12a9f9b26675e3dd253e9bc1893cf640ea7`  
**Related existing artifact:** `papers/crsm_nature_physics_2026.tex`, blob SHA `1ee0256fa480f92179d53585b4081c63a2d36cc1`  
**Governance:** No canonical claim verdicts, genome ledger entries, grants, or release records are changed by this draft.

## Scope and provenance

This audit concerns a CRSM manuscript supplied in a conversation, titled *Tetrahedral Dielectric Lattice Resonances and Anomalous Vacuum Energy Density: Computational Evidence from the CRSM Framework*. The conversation text itself has not been committed as an immutable source artifact and has no independently verified content hash in this repository. The existing paper at `papers/crsm_nature_physics_2026.tex` is a separate, pre-existing artifact and must not be silently replaced or treated as byte-identical to the supplied manuscript.

This document is a proposed evidence map, not a physics result, peer review, or statement that the proposed computations have run.

## Claim disposition

| Manuscript claim | Current OSIRIS status / treatment | Evidence gap before any upgrade |
|---|---|---|
| `theta_lock = 51.843 degrees` is a physical resonance or lock angle | Existing register entry `THETA_LOCK` is `REFUTED`; preserve that verdict. Treat new physical interpretations as unsupported. | Independent, pre-registered measurement that distinguishes a physical resonance from the geometric value `arctan(14/11)`; calibrated controls and replication. |
| `Lambda_Phi = 2.176435e-8 s^-1` is a universal coupling | Existing `LAMBDA_PHI` entry is `NOT_MEASURED`; preserve that verdict. | Derivation with consistent dimensions and a traceable measurement protocol. The numerical value matches the Planck mass in kg, not by itself a rate in s^-1. |
| Shannon entropy suppression `Z ~= 29.83`, `p < 1e-6` across 1,430 IBM Quantum circuits | Not verified by this audit; classify as `NOT_MEASURED` here until raw artifacts and analysis reproduce it. Do not infer independent sample size from job count. | Raw counts/results, job identifiers, backend calibration and dates, circuit-family mapping, exclusion log, baseline definition, effect size, confidence interval, pre-registered test, dependence/pseudoreplication analysis, multiplicity correction, and independent reproduction. |
| Casimir correction / anomalous vacuum energy | Hypothesis only. | Correct observable and units, geometry-specific mode spectrum and boundary conditions, uncertainty budget, conventional-model comparison, raw calculations, and independent validation. |
| Integrated Poynting flux implies propulsion, mass reduction, or metric perturbation | Hypothesis only; flux alone does not establish net force, energy creation, or spacetime curvature. | Defined control volume and surface orientation, time-averaged vector flux (not only magnitude), energy balance, force/thrust measurement, momentum accounting, systematic controls, and a dimensionally consistent relativistic derivation. |
| CRSM explains galaxy rotation curves better than established models | Hypothesis only. | Public, traceable dataset; fixed fitting protocol; uncertainties/covariance; same data splits and likelihood assumptions for baryonic, NFW/CDM, MOND, and CRSM comparisons; model-complexity accounting and held-out evaluation. |
| Proposed microwave, optical, and astrophysical experiments | Proposed protocols, not results. | Pre-registration, apparatus specification, calibrated controls, sample-size/power plan, exclusion rules, and reporting of nulls. |

## Equation and geometry review flags

1. **Tetrahedral geometry:** the supplied manuscript's geometry and angle definition need a consistent three-dimensional construction. The equation `arccos(1/3)` is approximately 70.53 degrees, not 51.843 degrees. A regular tetrahedron's dihedral angle and other common tetrahedral angles are distinct; identify the intended angle and derive it from explicit vertices.
2. **Casimir dimensions:** `-pi^2 hbar c/(720 d^4)` is the ideal parallel-plate Casimir energy per unit area. If the manuscript calls this energy density, it needs a volume normalization and stated geometry; otherwise relabel the quantity.
3. **Dimensional consistency:** a coefficient with units `s^-1` cannot be added directly to a dimensionless correction factor without a defined timescale or reformulation.
4. **Poynting integral:** `integral |E x B|/mu_0 dA` is not a signed net power flux. Define the oriented surface integral and appropriate time average, and show units.
5. **Metric / mass inference:** any mapping from an electromagnetic flux to `h_tt`, mass reduction, or propulsion needs a derivation from a stated stress-energy tensor and field equations; a dimensional placeholder is not a derivation.
6. **Statistical inference:** a very small p-value is interpretable only with a defined estimand, valid sampling unit, fixed analysis, dependence treatment, multiplicity plan, and transparent raw data.

## Required evidence bundle

Before any result is promoted, attach stable paths/identifiers for:

- Immutable raw job metadata and results, including job IDs, backend, timestamps, circuit source hashes, shot counts, calibration context, and retrieval provenance.
- Exact analysis code commit, dependency/environment lock, deterministic command line, output hashes, and full stdout/stderr.
- Pre-registration timestamp and frozen primary/secondary hypotheses; all deviations and exclusions.
- Null and negative-control results, effect sizes and confidence intervals, not p-values alone.
- Independent replication report and reviewer notes.
- Claim ID and proposed verdict transition, with a human-reviewed rationale. This draft does not authorize a verdict transition.

## Decision rule

No numerical result in the supplied manuscript is upgraded by this audit. Keep the manuscript as a hypothesis/protocol draft until every claim has a source artifact and an independently reproducible analysis. A test passing establishes only the property that test checks; it does not establish a physical interpretation by itself.

## Provenance log

- Existing repository base: `main` at `6bfcf12a9f9b26675e3dd253e9bc1893cf640ea7`.
- Existing claim register inspected: `osiris_cli/claims.py`, blob SHA `4f41ae59940317d7436c61e57f61fa44804c9a95`.
- Existing tests inspected: `tests/test_claims.py`, blob SHA `0495c0473129d7b21bdb23f2b191b513deb5c7da`.
- Existing manuscript inspected: `papers/crsm_nature_physics_2026.tex`, blob SHA `1ee0256fa480f92179d53585b4081c63a2d36cc1`.
- Conversation-supplied manuscript: source text provided by user; immutable repository artifact/hash not yet established.
- This audit is an additive draft. No tests, experiments, QPU jobs, or independent replications are claimed as run.
