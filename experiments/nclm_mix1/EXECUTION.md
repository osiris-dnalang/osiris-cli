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
- **2026-10-01 00:38 — second launch stopped by me after 29 steps, no results used.** Another
  session's job (`nclm_gate_pilot0` replay, ~470 % CPU) started alongside it, cutting throughput
  ~20×; with a fixed 3-hour cap, contention would decide how far each arm trains. The run also
  saw 4 chat lessons where earlier runs saw 3: inputs were being read live.
- **Fix before the third launch:** (a) inputs frozen once — `corpus.json`, `exchanges.jsonl`,
  `distill.jsonl` and the built corpus (`frozen_corpus.json`, via `train.freeze_corpus`) under
  `~/.osiris/experiments/nclm_mix1/inputs/`, hashes printed in `driver.log`; every run reads that
  snapshot (`--living-home`, `--frozen-corpus`), so the documents, held-out split and lessons are
  identical across arms even while `$HOME` changes; (b) each run starts only when the 1-minute
  load average is ≤ 3; (c) any run that ends on the time cap instead of early stopping is flagged
  in `RESULT.md`. Arms, seeds, mix, stopping rule and criterion unchanged.
