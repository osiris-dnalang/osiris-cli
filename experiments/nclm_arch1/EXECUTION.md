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
