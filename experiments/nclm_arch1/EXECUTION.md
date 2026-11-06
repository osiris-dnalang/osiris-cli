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
- **2026-11-01 — Amendment 3 recorded before completing Seed 201 (Option A Protocol Execution)**:
  - Documenting memory safety & autograd cycle reclamation updates across watched files:
    - In `osiris/nclm/autograd.py`: detach backward function pointers (`t._backward_fn = None`) during `Tensor.backward()` reverse topological pass, releasing closures and breaking circular references.
    - In `osiris_cli/living.py`: invoke `gc.collect()` at the conclusion of `train_batch()` to eliminate RSS growth across multi-hour 12,000-step training cycles.
    - Re-verified parameter counts: crsm 726,304 and standard 725,760 (exact match).
    - Re-verified loss equivalence under training mode and scoring mode (`diff = 0.00000000`).
    - All 127 claims tests and 14 trainer tests pass.
  - Setting aside interrupted partial run:
    - The initial run of `standard_s201` was stopped at step 2,020 during option evaluation. Its partial artifacts were moved to `~/.osiris/experiments/nclm_arch1/aborted_20261101/` and excluded from analysis.
  - Option A Execution Scope:
    - Scope bounded to $N=2$ replicated seed pairs (Seeds 200 & 201; 4 complete runs, 48,000 steps total) via `NCLM_ARCH1_SEEDS=200,201`.
    - `standard_s201` relaunched fresh from step 0 to 12,000 steps to complete Seed 201.
    - Upon completion, `run.py --analyse` runs to compute paired statistics, generate `results.json` and `RESULT.md`, and conclude `NCLM-ARCH-1`.
    - Following conclusion, compute shifts immediately to `NCLM-SCALE-1`.
- **2026-11-04 — Amendment 4 recorded before concluding NCLM-ARCH-1 (OSIRIS v5.0 Milestones 1 & 2)**:
  - Documenting Milestone 1 & 2 upgrades across watched files:
    - Added AVX2 C-SIMD fused kernels (`osiris/nclm/c_simd_ops.c`) and O(1) KV-cache decode engine (`osiris/nclm/fast_inference.py`), lifting generation throughput to 915.4 tok/s (118.9 ms draft latency).
    - Added Bidirectional Attention & Epistemic Introspection Engine (`osiris/nclm/bidirectional.py`), providing dual-stream causal/anti-causal attention, online negentropic tracking $\Xi(l)$, layer decoherence $\Gamma(l)$, and automated early-stopping rollback governor (`IntrospectiveGovernor`) under SYS-021.
    - Sanitized all dynamic script paths in `build_simd.sh` (resolving relative to script root).
    - Re-verified exact parameter counts: crsm 726,304 and standard 725,760 (both match registered constants exactly).
    - Re-verified loss equivalence under training mode and scoring mode (`diff = 0.00000000` for both crsm and standard).
    - All 1,322 test suites pass.
  - Arms (`crsm`, `standard`), seeds (`200..207`), mix (`0.5,0.3,0.2`), inputs, stopping rule, criterion, and `decide()` are unchanged.
