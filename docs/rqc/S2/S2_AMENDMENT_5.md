# RQC S2 — amendment 5 (DRAFT, not deposited)

**Status:** draft of 2026-10-08. Not binding until deposited on Zenodo as a new version alongside
`S2_PREREGISTRATION.md`, which is unchanged. No S2 data exists: no S2 job has been submitted (the account's job list
for the preceding 28 days ends 2026-09-29 and contains no S2 circuits), so this amendment is made before any data.

## Why

§8 sized the run by execution time only (80 seeds × 24,000 shots ≈ 9.3 min). IBM bills each job in whole seconds
with a fixed per-job overhead. Measured on this account's own billed jobs:

| Job (2026-09-25/29) | Execution | Billed |
|---|---|---|
| 1 pub × 2,048 shots, ~45 CZ | 0.537 s | 3 s |
| 1 pub × 4,096 shots | 1.08 s | 3 s |
| 20 pubs × 512 shots | 2.95 s | 5 s |

The frozen driver (`docs/rqc/S2/s2_run.py`) runs one job per sampler call: 80 seeds × 12 calls = 960 jobs, about
2,900–3,800 billed seconds. Under the registered 600 s ceiling it would stop after about 16 seeds (roughly 25%
power for β₀ = 0.012 instead of the registered 75%). In addition, the account is on IBM's Open plan: 600 s per
**rolling** 28-day window, so the ceiling equals the entire allocation.

## What changes

Only how sampler calls are grouped into jobs, and the budget rule that follows from it.

1. **Blocks and lockstep.** Seeds run in two blocks, 1000–1039 then 1040–1079. Within a block the 80 participants
   (seed × arm) run the frozen `run_random` / `run_adaptive` in lockstep: each round of all participants is one
   multi-pub job. 6 jobs per block, 12 jobs in all, each 80 pubs × 2,000 shots.
2. **Arm order** (replaces "within a seed the arm that runs first alternates with seed parity"): within a job, pubs
   are ordered by seed; within a seed the arm whose pub comes first alternates with seed parity (even seed: random
   first). Both arms of a seed are measured in the same job.
3. **Budget** (replaces the stop rule in §8):
   - Before the first job, the account must report at least 600 s of its rolling allocation remaining
     (`QiskitRuntimeService().usage()["usage_remaining_seconds"]`); otherwise the run does not start.
   - Before every job, its billed cost is projected as ⌈3.0 s + 0.015 s × pubs + 0.27 ms × shots⌉ (constants from the
     table above, rounded up). If spent billed seconds plus the projection would exceed 600 s, the job is not
     submitted and the run stops. Projected whole run: 12 × 48 s = 576 s. Expected from measured rates: about 545 s.
   - A block stopped by the budget contributes no seeds (no seed in it has a final re-measurement); completed blocks
     stand. If the run stops in block 2, the analysis uses the 40 seeds of block 1, and the report states that the
     registered size was not reached and gives the achieved power, as §8 already requires.
4. **Ledger.** Each participant's RQC_SUBMIT / RQC_RESULT rows are written in the same order as in a sequential run;
   rows of a round are written in participant order, all before the job that measures them, followed by one
   RQC_BATCH_SUBMIT row (pub order, circuit digests, shots). After the job: RQC_BATCH_DONE (job id, billed seconds).
   A job refused by the budget writes RQC_BATCH_REFUSED and no RQC_SUBMIT rows. A job that fails after submission
   writes RQC_BATCH_FAILED; its RQC_SUBMIT rows stand, since it may have run.
5. **Code.** `rqc/batch.py` (`GatheringSampler`, `BatchHardwareSampler`, `projected_seconds`) and the driver
   `docs/rqc/S2/s2_run_batched.py`, frozen at commit **`<to be filled at commit>`**. The driver refuses hardware
   without the DOIs of both the pre-registration and this amendment. `rqc/experiment.py` (06761071),
   `choose_backend` and `best_path` (86e3a3f4) are used unchanged. `s2_run.py` is superseded and not run.

## What does not change

Question (§1); k, σ, n, depth, circuits, 2,000 shots, seeds 1000–1079 (§2); backend and qubit rules (§3); primary
estimand, test and decision (§4); secondary analyses (§5); power statement (§6); no interim analysis; analysis by
`docs/rqc/s1_adjusted.py` unchanged on the results file.

## Consequences to disclose

- Rounds, not seeds, are now sequential in time. Each round of a block runs within minutes, which removes any
  between-arm calibration drift within a seed (both arms share a job). Drift between rounds and between blocks
  affects both arms equally.
- The cost constants come from circuits with ~45 CZ routed on a 156-qubit device. S2 circuits (21 CZ on a line of 8)
  are assumed to have similar per-shot time. This is an assumption: the per-job budget check is what enforces the
  ceiling if it is wrong.
- Margin: 24 s against the conservative projection, ~55 s against the measured rates. A deviation of more than about
  9% per job stops the run in block 2 (40 seeds), not mid-seed.

## Open decision before deposit (author)

Keep 2,000 shots (registered power, thin margin) or register a lower shot count (e.g. 1,500: projected ≈ 432 s)?
A lower count changes the per-seed noise. Its power must be re-derived from S1 in simulation before deposit, and
that has not been done. This draft keeps 2,000.

## Unverified before launch

- That Batch execution mode is available on the Open plan for this account. If it is not, jobs run in job mode.
  The job count and order are unchanged.
- The backend that the rule selects on the run date. On 2026-10-08 it was `ibm_fez` (operational Herons:
  ibm_fez, ibm_kingston, ibm_marrakesh).

## Run window

The rolling window frees about 570 s by 2026-10-19 08:30Z and the full 600 s by about **2026-10-27**. The run
needs 600 s, so the earliest start is ~2026-10-27, with no other jobs on this IBM account until then.
