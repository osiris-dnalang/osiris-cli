# CRSM governance integration proposal

**Status:** Draft proposal; no implementation or canonical register changes authorized by this file.  
**Target:** OSIRIS claims firewall and research workflow.

## Existing mechanisms reviewed

- `osiris_cli/claims.py` is the canonical code-level claim register. Existing entries include `THETA_LOCK` (`REFUTED`) and `LAMBDA_PHI` (`NOT_MEASURED`).
- `tests/test_claims.py` checks register well-formedness, claim matching, and selected computations.
- `GEMINI.md` requires agents to propose rather than commit, prohibits promotion of canonical genome-ledger records, and explicitly treats `theta_lock = 51.843 degrees` as refuted/artifact rather than verified.
- `RESEARCH_INTEGRITY.md` calls for pre-registration, multiple-comparison control, blinding where feasible, and reporting negative results.
- `OSIRIS_PHYSICS_TEST_MATRIX.json` currently includes the interpretation string “Claim: Evidence for exotic physics (publish in Nature Physics)” when multiple exotic predictions are significant. This is a governance hazard: significance across predictions alone does not establish exotic physics or justify publication.

## Proposed changes (not applied)

### A. Replace interpretation language in a future reviewed change

Change the matrix interpretation for multiple significant exotic predictions to wording such as:

> Investigate: candidate anomaly requiring raw-data review, systematic-error analysis, multiplicity correction, comparison with conventional models, and independent replication. No physical interpretation or publication recommendation follows from significance alone.

Do not make this change automatically in this draft branch. It is a proposed future edit to an existing file and requires a separate explicit review because the current task specified additive files.

### B. Add a claim-to-artifact evidence map

Use `docs/research/crsm_claim_audit.md` as a human-readable mapping. If later implemented in code, keep it non-authoritative until a schema, validation rules, and a migration plan are reviewed. Avoid duplicate canonical verdicts that could drift from `osiris_cli/claims.py`.

### C. Regression coverage to add in a future implementation PR

1. A matrix interpretation test rejects unsupported phrases that convert statistical significance directly into an exotic-physics conclusion or publication recommendation.
2. A test confirms `THETA_LOCK` remains `REFUTED` and `LAMBDA_PHI` remains `NOT_MEASURED` unless a reviewed evidence-backed change explicitly alters them.
3. A test checks that manuscript claim language such as “measured,” “confirmed,” or “demonstrated” cannot be inferred merely from a protocol or simulated output.
4. A test checks evidence records carry source identifiers, content hashes where applicable, analysis commit, method, and review status.
5. Tests remain offline and deterministic; no IBM Quantum, cloud model, external network, or QPU calls.

These tests are proposals only. They have not been added or run.

### D. State model and transition control

- `HYPOTHESIS` / `PROPOSED`: testable idea or protocol not yet measured.
- `NOT_MEASURED`: quantity configured or claimed without a traceable measurement.
- `PILOT`: exploratory measurement that is not confirmatory.
- `SUPPORTED` / `REPORTED`: use only according to existing repository definitions and evidence scope.
- `NULL`, `REFUTED`, `ARTIFACT`, `OVERCLAIM`: preserve their existing semantics and negative findings.

Do not add new enum values or change verdicts without reviewing compatibility with `claims.py`, its match/render behavior, tests, and all consumers. A manuscript's wording never changes a register verdict. Models can propose status transitions; deterministic code checks schema and provenance; a human authorizes promotion.

## Proposed integration sequence

1. Review this proposal and the CRSM claim audit.
2. Validate raw-data provenance and math before designing confirmatory tests.
3. Open a separate implementation change for the interpretation-matrix wording and regression tests, after explicit approval.
4. Run the offline test suite and `git diff --check` in a suitable local worktree. This connector-based file creation has not run local tests.
5. Only after review, decide whether to submit a pull request. No PR, merge, release, DOI deposit, or claim promotion is authorized by this file.

## Audit trail

This proposal is additive and non-authoritative. It does not edit `claims.py`, `tests/test_claims.py`, `OSIRIS_PHYSICS_TEST_MATRIX.json`, `GEMINI.md`, the canonical genome ledger, or any grant registry.
