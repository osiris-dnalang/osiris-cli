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
- **2026-10-01 00:46 — third launch stopped by me at step 737 of control s0, no results used.**
  The driver inherited `PYTHONPATH=/home/enki:…` from the launching shell, so the runs imported a
  stale copy of the model code (`/home/enki/osiris/nclm`, dated 05-01, without the matmul
  gradient fix) instead of this repository's. That copy's gradients accumulate (tracemalloc:
  +313 MB in 40 steps; the run's RSS rose ~40 MB/min to 4.8 GB). The repository's copy holds
  steady (~1.9–2.6 GB). The 2-thread BLAS cap from the parallel design was also still set,
  slowing the run ~5×.
- **Fix before the fourth launch:** runs get `PYTHONPATH` = this repository only and no thread
  caps; every run's manifest now records the imported `osiris.nclm` path and git commit
  (`code`), and the analysis carries it into `results.json`. Arms, seeds, mix, stopping rule,
  criterion and frozen inputs unchanged.
- **2026-10-08 — scoring defect found (osiris-cli v4.5.2), recorded before any Mix-1 result is read in
  this repository.** Every held-out score this experiment uses -- the primary (`heldout_docs_bpb`), the
  guard (`heldout_chat_bpb`), early stopping and the best checkpoint it keeps -- came from a forward pass
  under `no_grad`. Before v4.5.2 that pass skipped the phase-conjugate corrector, which training applies
  in every block (`osiris/nclm/sovereign_mechanics.py`; Γ is 0.6-0.99, far above its 0.3 threshold).
  Runs on v4.5.1 or earlier code therefore selected and scored a different network from the one they
  trained, and a result from them does not answer the registered question. Arms, seeds, mix, stopping
  rule and criterion are unchanged by this note. Whether to set those runs aside and re-run all six on
  v4.5.2 (manifests record the code commit) is decided and recorded here before any result is opened.
