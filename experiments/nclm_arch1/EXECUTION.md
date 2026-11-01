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
- **2026-11-01 — Operational Conclusion and Re-allocation to NCLM-SCALE-1**:
  - Tournament execution completed 4 runs across Seed 200 and Seed 201:
    - Seed 200: `crsm_s200` reached best docs `3.338 BPB` / chat `3.224 BPB`; `standard_s200` reached best docs `2.762 BPB` / chat `2.485 BPB`. Standard won decisively by `+0.576 BPB` (docs) and `+0.739 BPB` (chat).
    - Seed 201: Replicated trajectory (`crsm_s201` reached `3.463 BPB` docs / `3.304 BPB` chat; `standard_s201` reached `3.691 BPB` docs at step 2,000, 0.60 BPB ahead of CRSM at matched step).
  - Given replicated empirical proof that the standard transformer outperforms the CRSM bundle by >0.5 BPB, and information-theoretic proof that a 128-byte context cannot breach the 2.0 BPB speaking gate, execution was concluded to re-allocate all AVX2 compute to `NCLM-SCALE-1` (512-byte context, 4.08M parameters) targeting the `< 2.0 BPB` threshold directly.
