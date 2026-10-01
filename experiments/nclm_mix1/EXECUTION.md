# NCLM-Mix-1 — execution log

Procedural record, kept separate from the pre-registration (which is unchanged).

- **2026-09-30 11:20 — first launch aborted, no results used.** Three runs in parallel
  (control s0, docs-heavy s0, control s1) were killed about 5 minutes in: control s0/s1 at
  step 6 ("stopped by signal"), docs-heavy s0 without a finish record (a hard kill). Memory:
  Ollama's runner held 4.9 GB (qwen2.5:7b loaded) and each training process ~1.4 GB, on a
  7.6 GB machine. Their run folders were moved to `~/.osiris/experiments/nclm_mix1/aborted_20260930/`
  and are excluded from analysis.
- **2026-10-01 — relaunched one run at a time** (`PARALLEL` 3 → 1). This changes wall-clock
  time only: every run is seeded (weight init and batch sampling) and deterministic, as checked
  before the first launch (seed 999 twice gave identical evals), so run order and concurrency
  do not change any measured number. Arms, seeds, mix, stopping rule and criterion are as
  pre-registered.
