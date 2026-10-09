# RQC S2 — amendment 5

**DEPOSITED 2026-10-09 as 10.5281/zenodo.23256344 — NOT APPROVED FOR EXECUTION.**

**Status:** drafted 2026-10-08; deposited 2026-10-09, before any S2 data, as a new version of the S2 record
(concept 10.5281/zenodo.23241222) next to the unchanged original pre-registration. Not executable until an operator
records an `execute` approval bound to the exact run payload (see `CONTROL_NOTES.md`). The author decisions in §9
were made on 2026-10-09. The original pre-registration and its frozen tooling are unchanged:

| Frozen artifact | Identity |
|---|---|
| `docs/rqc/S2_PREREGISTRATION.md` | sha256 `ee179e8f53b9b81c336db09ff68ff1fd7617edd728000a50f7a34d95cfa00e5d` |
| Search code `rqc/experiment.py` | commit `0676107155d3ca5c5777937f49ce56a99085ca5c`; file sha256 `4f80d891…84af` |
| Tooling `rqc/hardware.py`, `docs/rqc/S2/s2_run.py` | commit `86e3a3f4db6e449044fa0d7c173fc107b1b74452`; sha256 `165221a7…0ee2`, `b7686e00…094f` |
| Pre-registration text commit | `964efe1931ead531ad4408945e03d6f2b2ddf3aa` (branch `feat/rqc-s0`) |
| Pre-registration DOI | `10.5281/zenodo.23241223`: supplied by the operator; **not verifiable from local files** |

**Identifier.** The deposited text carries amendments 1–4 (§2, §4, §6, §7), so this is amendment 5. No other
amendment exists in the repository history.

## 0. Has any S2 outcome been observed?

No, as far as local and account evidence shows. On 2026-10-08 at 15:34Z, the IBM account's job list for the
preceding 28 days held 24 jobs, the last created 2026-09-29. None is an S2 job: the S2 tooling commit
(86e3a3f4) is dated 2026-10-08, and no S2 ledger or evidence directory exists. Seeds 1000–1079 have never been run
anywhere (pre-registration §2). Everything quantitative below comes from S1 *simulation* (seeds 100–129, two noise
models) or from billing metadata of unrelated earlier jobs. None of it is S2 outcome data.

## 1. Reason

Pre-registration §8 sized the run by execution time (80 seeds × 24,000 shots ≈ 9.3 min). The frozen driver submits
one job per sampler call: 80 seeds × 2 arms × 6 calls = 960 jobs. This account's billed jobs show a fixed per-job
charge plus rounding to whole seconds (`budget_audit.json`). For example, 2,048 shots ran for 0.537 s and billed 3 s.
A fit of `billed = ⌈execution + c⌉` with c ≈ 1.5–1.7 s matches all 10 jobs with recorded execution time. Under that
fit the frozen schedule costs about 2,880 s against a 600 s ceiling. It would stop after about 16 seeds (analytic
power 23–25% for β₀ = 0.012). The account is IBM's Open plan: 600 s per rolling 28-day window, so the ceiling is
the whole allocation.

## 2. Original versus amended protocol

| Element | Original (frozen) | Amended |
|---|---|---|
| Question, estimand, test, decision (§1, §4) | as registered | **unchanged** |
| n, depth, k, σ, circuits, estimator (§2) | 8, 6, 5, 0.2 rad | **unchanged** |
| Seeds | 1000–1079 | **unchanged**; no replacement seeds, no extra rounds |
| Shots per sampler call | 2,000 | **unchanged** (1,500 evaluated in §6, *not* adopted) |
| Backend rule, qubit rule (§3) | `choose_backend`, `best_path` @ 86e3a3f4 | **unchanged** (same functions, same file) |
| Search code | `run_random`, `run_adaptive` @ 06761071 | **unchanged**; called as is |
| Analysis script | `docs/rqc/s1_adjusted.py` | **unchanged** for the primary; secondary diagnostics added (§5) |
| Session | one IBM Batch session | unchanged |
| Submission unit | one job per sampler call (960 jobs) | one job per *barrier* (see below) |
| Time order | seed by seed; within a seed, arms in sequence | round by round across a block; both arms of a seed in the same job |
| Arm-order rule | first arm alternates with seed parity (even: random first) | pub order within a job: by seed; within a seed, the first pub alternates with seed parity (even: random first) |
| Budget stop | check spent seconds before each job | reservation-based check before each job (§4) |
| Pre-launch check | none | ≥ 600 s of the rolling allocation must be reported available |
| Ledger | row before each call | same rows, same per-participant order, plus batch rows (§4) |
| Failure handling | not specified | §4: no automatic retry; unknown outcomes need reconciliation |

**Barrier schedule (derived, then tested).** Each arm makes exactly k + 1 = 6 sampler calls. The adaptive arm's call
r depends on its results 0..r−1, and both arms' final call depends on all k earlier results. No call depends on
another seed. So call r of every participant (seed × arm) in a block can share one job. With seeds in blocks of 40
(1000–1039, then 1040–1079), each block needs 6 jobs of 80 pubs: 12 jobs, 960 pubs, 1.92 M shots. This count is
observed in `tests/test_rqc_batch.py::test_registered_schedule_yields_twelve_jobs_of_eighty_pubs`, which runs the
registered parameters through the driver's own participant builder. It is not asserted from the arithmetic alone.

**Why two blocks.** A budget stop then costs at most the second block, leaving 40 complete seeds. With one block of
80 seeds, a stop in the last job would leave no seed with a final re-measurement.

**Drift.** Under the original order, temporal drift was confounded with seed index and with arm order inside a seed.
Under the amendment, both arms of a seed are adjacent pubs in the same job, so drift between jobs cancels in d_s to
first order. Alternating which arm comes first by seed parity balances drift within a job. What the amendment
*adds* is a shared-job component (§5).

## 3. Timing

Earliest start is when the account reports ≥ 600 s available. If the window is rolling as observed, that is after
2026-10-27 15:10Z, with no other jobs on the account until then. The run itself is 12 jobs in one Batch session, as
in the original. Whether IBM's Batch mode is available on this Open-plan account is **unverified**. Changing to
plain job mode would be a protocol change requiring its own decision, not a silent fallback. Queue time is not
billed in any observed job, but that is not guaranteed.

## 4. Stopping, retry and failure rules

Three kinds of stop are kept apart, and only the first two exist:

1. **Budget checks at registered boundaries.** These run before each job, from billing data only.
2. **Operational failure handling.** Errors, unknown outcomes, malformed results, timeouts or cancellation stop the
   run, and nothing is retried automatically.
3. **Statistical stopping on observed outcomes: none.** No rule in this amendment reads an XEB value, a difference
   or a p-value before the run ends. Pre-registration §8's "no interim analysis" stands. Block 1 is a budget and
   failure boundary, **not an interim analysis or an interim stopping rule**. Its results are not examined before
   the run ends, whether or not block 2 completes.

- **Before the first job:** an `execute` approval for target `ibm-quantum` must exist, bound to the SHA-256 of the
  intent payload. The payload covers the code manifest, parameters, seeds, block size, DOIs, budget, and backend and
  qubit rules. The account must also report `usage_remaining_seconds ≥ 600`. Otherwise nothing is submitted.
- **Before every job:** the approval is re-checked, and the evidence hash chain and intent artifact are verified. The
  job's cost is projected as ⌈3.0 + 0.015 × pubs + 0.27 ms × shots⌉ s, which is 48 s for an 80-pub job. If committed
  seconds plus the projection exceed 600, the job is not sent and the run stops. Committed seconds are:
  Σ max(reported, reserved) over finished jobs, plus the reservations of jobs in flight, with unknown outcome, or
  failed. A reported 0 never frees budget, because `job.usage()` returns 0 until the provider has computed usage.
- **Overshoot:** the check uses a projection, so a job that bills more than projected can exceed the ceiling by its
  excess. Provider behaviour at the account limit mid-job is unknown. **This is not a strict billed-time ceiling.**
- **Retries:** none automatic. A job whose submission may have reached the provider (timeout, lost response,
  unclassified error) is recorded `outcome_unknown`. The run stops, and that job is reconciled before anything else:
  either found by its provider job id or tags and its results recorded, or established as not executed. Only a job
  rejected before execution (`DefiniteFailure`) is terminal. It is not resubmitted, and the run stops.
- **Restart:** the search is deterministic given results. A restarted run replays every finished job from its stored
  result artifact, verified by hash, and does not contact the provider for it. It resumes at the first unfinished
  barrier.
- **Malformed results:** a wrong count, wrong order or wrong shot count aborts the block (`RQC_BATCH_FAILED`).
- **Partial run:** a block that does not finish contributes no seeds. If block 2 is lost, the analysis uses block 1
  (seeds 1000–1039) and the report states that the registered size was not reached and gives the achieved power, as
  §8 requires. No seed of an incomplete block is analysed.

## 5. Statistical implications of shared jobs

All 40 seeds of a block share their 6 jobs, so d_s are not independent just because seeds differ. A calibration
shift that affects both arms equally cancels in d_s. A shift that affects the arms *differently* (an arm × job
interaction) adds a common component u_b to every d_s in block b. With two blocks, u_b cannot be estimated
separately from β₀. Offline simulation with u_b ~ N(0, τ²), registered OLS test, bootstrap from S1:

| τ | Type I rate (fez / Willow model) | Power at β₀ = 0.012, n = 80 |
|---|---|---|
| 0 | 0.069 / 0.039 | 0.74 / 0.69 |
| 0.005 | 0.104 / 0.079 | 0.70 / 0.66 |
| 0.01 | 0.173 / 0.146 | 0.65 / 0.62 |

(5,000 replicates each, Monte Carlo SE ≤ 0.007. At τ = 0 the bootstrap's own size is 3.9–6.9% against a nominal 5%,
a limitation of resampling 30 seeds.) The size of τ on hardware is unknown.

Pre-committed handling, decided before any S2 outcome is seen:
- **Primary: unchanged.** The registered OLS t-test on all completed seeds. The report states that its nominal α
  assumes no arm × job interaction, and that the amendment introduced this exposure.
- **Secondary (reported, not used for the decision):** β₀ estimated separately in each block, and their difference
  with its standard error, as a diagnostic for block heterogeneity. Each block's collision-adjusted fit is
  `s1_adjusted.analyse` applied to that block's rows.
- **Not adopted:** cluster-robust standard errors. With two clusters they are not usable.

An alternative with more independent clusters (4 blocks of 20, 24 jobs) costs about 576 s central and projects
above 600 s under the registered constants. It is listed as an author decision, not adopted.

## 6. Power (re-derived offline, `amendment5_analysis.py` → `amendment5_analysis.json`)

The registered test on S1 data (30 seeds per model; residual SD 0.046 fez, 0.049 Willow; design inflation ≈ 1.03–1.05):

| n | β₀ | Analytic (fez / Willow) | Bootstrap MC, 2,000 shots | Bootstrap MC, 1,500 shots |
|---|---|---|---|---|
| 16 | 0.012 | 0.25 / 0.23 | — | — |
| 40 | 0.012 | 0.47 / 0.44 | 0.50 / 0.41 | 0.44 / 0.37 |
| 80 | 0.012 | 0.73 / 0.69 | 0.74 / 0.69 | 0.67 / 0.62 |
| 80 | 0.02 | 0.98 / 0.97 | 0.98 / 0.98 | 0.95 / 0.95 |

- Pre-registration §6's "about 75% for 0.012" is reproduced for the fez model (0.73 analytic, 0.74 MC) and is lower
  on Willow (0.69). Its "above 99% for 0.02" is **not** reproduced: 0.97–0.98.
- Shot noise is 69–79% of the residual variance of d_s at 2,000 shots. This is computed from the reconstructed final
  circuits (every digest matched the S1 ledger) under a depolarizing approximation. Shots are therefore the main
  lever on power.
- **1,500 shots:** costs about 420 s central and loses about 7 points of power at n = 80, β₀ = 0.012. S1 cannot fully
  assess it. Fewer shots also change which circuits the search selects, and that effect is not captured without
  re-simulating at 1,500 shots. **Not adopted, and no automatic fallback.** If the author wants it, it must be chosen
  in this document before deposit, with its own power statement.

## 7. Cost model and margin (`budget_audit.json`, `amendment5_analysis.json`)

| Scenario (per-shot, per-pub, per-job) | Billed per job | 12 jobs | Seeds under 600 s |
|---|---|---|---|
| Observed rates: 0.262 ms, 13.5 ms, 1.73 s | 45 s | 540 s | 80 |
| Registered projection: 0.27 ms, 15 ms, 3 s | 48 s | 576 s | 80 |
| Per-pub cost 4× observed (60 ms) | 49–51 s | 588–612 s | 80 / 40 |
| Per-shot 0.30 ms (+15%) | 51–53 s | 612–636 s | 40 |
| Per-shot 0.35 ms (+34%) | 59–61 s | 708–732 s | 40 |

The break-even per-shot time is 0.295 ms, 12.6% above the observed value. The observed jobs ran 156-qubit-layout
circuits with 33–45 CZ, and only one had more than one pub (20). S2 jobs have 80 pubs of an 8-qubit, 21-CZ circuit.
The margin is real but thin. A deviation of about 13% loses block 2.

## 8. Provenance: three artifacts, no circular hashes

- **A. Implementation snapshot:** the code files the run executes or analyses with (`CODE_FILES` in
  `s2_run_batched.py`: the frozen `rqc` modules, `rqc/batch.py` [`GatheringSampler`, `projected_seconds`],
  `rqc/control.py` [`Evidence`, `Dispatcher`, `QiskitBatchAdapter`, `verify_bundle`], the driver, and
  `docs/rqc/s1_adjusted.py`) at one commit. No file in A names that commit.
- **B. Documents:** the frozen `S2_PREREGISTRATION.md` and this amendment. This amendment cites A's commit (§10).
  It never contains its own hash or the manifest's hash.
- **C. Bundle manifest** `docs/rqc/S2/AMENDMENT_5_MANIFEST.json`: A's commit and file hashes, B's hashes, and
  supporting files. It is written by `make_bundle_manifest.py`, which refuses unless every code file on disk equals
  `git show <A>:<path>`.
- **Binding:** the run's intent payload carries A's and B's file hashes, computed from disk, plus C's hash. An
  `execute` approval binds that payload's hash, so code, amendment and manifest are approved together, and a change
  to any of them voids the approval. The hardware path also requires `verify_bundle` to pass, with C's status
  `deposited` and its `amendment_doi` equal to the DOI given at launch.
- **Superseded procedure:** writing a commit's hash into a file and then `git commit --amend` does not work. The
  amend creates a new hash, so the recorded one names a commit that is no longer on the branch. Commit hashes are
  only ever cited from a later commit.

## 9. Author decisions (made 2026-10-09, before any S2 data)

The author, Devin Phillip Davis, accepted on 2026-10-09 the three options recommended by the assistant that drafted
this amendment. The recommendation and its reasons were presented first; the choice is the author's. No S2 outcome
existed (§0).

1. **Shots: 2,000 per sampler call, as registered.** 1,500 is not adopted: it would lose about 7 points of power at
   n = 80, β₀ = 0.012 (§6), and its effect on circuit selection has not been simulated. There is no shot-count
   fallback.
2. **Blocks: 2 blocks of 40 seeds (1000–1039, 1040–1079), 12 jobs** (§2, §7; projected 576 s, about 540 s expected).
   Four blocks of 20 are not adopted: they project to 624 s, above the 600 s ceiling.
3. **§5 exposure: accepted.** The primary test stays the registered OLS t-test on all completed seeds. The per-block
   β₀ estimates and their difference are reported as a secondary diagnostic, not used for the decision. The report
   states that the primary test's nominal α assumes no arm × job interaction, and that grouping seeds into shared jobs
   introduced this exposure (τ = 0.01 would raise the type I rate to about 0.15–0.17 in the offline model, §5).

These decisions change no code and no registered parameter, so the implementation snapshot (§11) stands.

## 10. Prerequisites (in order; each is a separate approval)

1. ~~The author decisions in §9.~~ Made 2026-10-09 (§9); no code or parameter change, so A stands.
2. ~~Verify DOI 10.5281/zenodo.23241223.~~ Done 2026-10-09: it holds `S2_PREREGISTRATION.md` with sha256
   `ee179e8f53b9b81c336db09ff68ff1fd7617edd728000a50f7a34d95cfa00e5d` and `rqc-s2-frozen-86e3a3f4.zip`.
3. ~~Deposit this amendment.~~ Deposited 2026-10-09 as 10.5281/zenodo.23256344 (DOI reserved first, then recorded
   here and in the manifest, status `deposited`, before the files were uploaded).
4. Record an `execute` approval bound to the final payload hash, with target `ibm-quantum`, budget 600 s and an
   expiry.
5. On launch day: read-only usage check (≥ 600 s), then the run.

## 11. Implementation snapshot cited by this draft

Implementation snapshot (artifact A): commit **`3332e8935ba208dbcdf38e4bdece6a507b5cf089`** on branch `feat/rqc-s0`.
Verified on 2026-10-08: a full `git archive` export of that commit passed `tests/test_rqc.py`,
`tests/test_rqc_batch.py` and `tests/test_rqc_control.py` (61 passed, 0 failed, 0 skipped), with sockets blocked and
PYTHONPATH unset. This amendment is committed **after** A, so the tree that contains this text also contains
documentation changes that are not part of A. The file hashes of A and of this document are in
`docs/rqc/S2/AMENDMENT_5_MANIFEST.json` (artifact C).
