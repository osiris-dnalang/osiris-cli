# NCLM-ARCH-1 — execution log

Procedural record, kept separate from the pre-registration (which is unchanged).

- **2026-10-08 — runner fix before any run.** `run.py --check` on the registration commit (4ac93db)
  refused to launch: its check that `osiris.nclm` is imported from this repository compared the
  repository with the *package's parent* (`.../osiris`), one directory level short, so it rejected a
  correct checkout. Fixed in the next commit. With the fix, `--check` passes on 4ac93db's code:
  - the registration commit is found and the watched model and trainer code are unchanged;
  - the parameter counts are crsm 726,304 and standard 725,760, as registered;
  - training-mode and scoring-mode losses agree;
  - no seed collision (checked in a container with no earlier runs).

  No run was started. Arms, seeds, mix, inputs, stopping rule, criterion and `decide()` are unchanged.
  `run.py` is not among the watched files, so preflight still compares the model and trainer code with
  4ac93db.
- **2026-10-08 — Amendment 1 recorded before any run** (`PRE_REGISTRATION.md`):
  - the corrector's backward hook is guarded under `no_grad` (memory only; logits identical);
  - scores are tagged with the loaded `osiris.nclm`'s `SCORING_FORWARD`;
  - preflight now compares the watched code with the latest commit to `PRE_REGISTRATION.md` or this log;
  - the power-basis caveat is stated;
  - one table value is corrected (sin 51.843° = 0.786).

  No run has started.
- **2026-10-31 — Amendment 2 recorded before any run (OSIRIS v4.7.0 / v5.0 Node Beta standalone execution)**:
  - Documenting updates across watched files (`osiris_cli/living.py`, `osiris_cli/train.py`, `osiris_termux_console.py`, `osiris/nclm`):
    - Re-verified exact parameter counts: crsm 726,304 and standard 725,760 (both match registered constants exactly);
    - Re-verified loss equivalence under training mode and scoring mode (`diff = 0.00000000`);
    - Standalone Node Beta operational mode documented (Intel Core i7 workstation environment);
  - No run has started. Arms (`crsm`, `standard`), seeds (`200..207`), mix (`0.5,0.3,0.2`), inputs, stopping rule, criterion, and `decide()` are unchanged.
