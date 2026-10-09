# S2 amendment 5: control notes (threat model, decisions, gaps, preflight)

Scope: only the controls the amendment-5 workflow needs: one intent (the S2 run), its approval, 12 jobs through an
outbox, evidence and artifacts. This is not a general OSIRIS control plane. Code: `rqc/control.py`,
`rqc/batch.py`, `docs/rqc/S2/s2_run_batched.py`. Tests: `tests/test_rqc_control.py`, `tests/test_rqc_batch.py`.

## 1. Threat model

**Assets:** the frozen protocol and its hashes; the amended protocol; the 600 s QPU allocation; S2 evidence (ledger,
job results, approvals); the integrity of "no outcome seen before pre-registration".

**Actors and assumptions**

| Actor | Assumed capability | What stops it here | What does not |
|---|---|---|---|
| Buggy or crashing driver process | any Python bug, kill at any point | write-ahead `dispatching` state; outbox; restart replays; no automatic retry | — |
| An agent (LLM or script) running as the operator's user | can run any command the user can: edit files, call the IBM API directly, write to the evidence DB | Nothing *technically*. The approval check binds a dispatch through *this driver* to a recorded approval. | An agent with shell access can bypass the driver entirely (call `qiskit_ibm_runtime` itself), forge an approval row (`approver` is a label, not an authenticated identity), or drop triggers. Detectable afterwards only via the chain hash, the IBM account's job list, and git history. |
| Privileged local operator | full control of disk | hash chain makes edits detectable (`verify_chain`) | Can rewrite the whole chain consistently and re-hash; the chain has no external anchor yet (backlog P1-3). |
| Provider (IBM) | may time out, lose responses, bill differently from the model | `outcome_unknown` + reconciliation; conservative budget accounting | Cannot stop billing beyond the projection; account-limit behaviour unknown. |

**Not claimed:** that anything here is "mathematically unreachable" by an LLM agent. The boundary is OS-user level.
Whoever runs as this user can do everything this code prevents the driver from doing. Real separation would need a
different OS user or service holding the IBM credential and exposing only typed, approval-checked operations
(backlog P1-1).

## 2. Architecture decision records

**ADR-1: Threads with a barrier, not a rewrite of the search code.** `run_random` and `run_adaptive` are frozen
(06761071) and call a blocking `sampler(circuit, shots)`. Suspending them mid-call without editing them requires a
thread (or a coroutine library). One thread per participant (80 per block, bounded by `max_participants=160`). The
threads only wait on one condition variable, and one thread at a time runs a job. Alternative rejected: converting
the arms to generators, which changes frozen code and its hash. Risk: a participant that never calls back. This is
handled by the barrier timeout, `cancel()`, and abort-on-error. Tests: timeout, cancel, error, extra round.

**ADR-2: Deterministic ledger order.** Participants buffer their rows (snapshotted at append, as `Ledger` serializes
at call time). The thread that fires a job writes all buffers in sorted-key order, then `RQC_BATCH_SUBMIT`, then
calls the provider. Each participant's rows are identical in content and order to a sequential run (tested).

**ADR-3: Evidence = SQLite (WAL, synchronous=FULL, foreign_keys, busy_timeout 5000, temp_store MEMORY,
trusted_schema OFF), set and read back on every connection; fail closed.** `connect_evidence` is the only way to
open evidence. `:memory:` is refused. Any PRAGMA reporting another value raises `DurabilityError`. There is no
downgrade to NORMAL. Telemetry is a separate file at NORMAL whose failures are swallowed and counted.
Durability assumption: the OS and storage honour fsync. The tests prove behaviour on process exceptions and
simulated crashes, **not on power loss**.

**ADR-4: Content-addressed artifacts; publish before reference.** Bytes are written to `staging/`, fsynced,
re-read and verified, then hard-linked into `objects/aa/<sha256>`. The link fails if the name exists, so an
existing hash is never replaced. Then the directory is fsynced and the staging name removed. Only then is a DB row
written that refers to it. A crash leaves at most an orphan staging file (`sweep_staging`) or an unreferenced
object. A referenced artifact that is missing or corrupt is reported by `verify_artifacts` and blocks
authorization when it is the intent payload.

**ADR-5: Events are append-only and hash-chained.** Format `rqc-evidence-event/1`, canonical JSON (sorted keys,
no NaN, ASCII), `hash = sha256(prev_hash || body)`. Triggers forbid UPDATE and DELETE on events, intents, approvals
and artifacts. The mutable outbox row is queue state; its every transition is also an event. Limitation: triggers
can be dropped by anyone with file access; tampering is then *detected* (`verify_chain`), and authorization is
refused while the chain fails. Corrupted history is preserved, never re-hashed.

**ADR-6: Approval binds the exact payload.** An approval stores the intent payload's SHA-256, target, scope
(`read_only` | `execute`), budget and expiry. `authorize()` requires an unexpired, unrevoked `execute` approval
whose payload hash equals the hash of the payload being dispatched *and* of the stored payload artifact, with the
same target and budget, and a verified chain. Any change to code (via the manifest), seeds, shots, block size,
DOIs or budget changes the hash and voids the approval. `read_only` never authorizes a dispatch. Automatic
("policy:") approval is accepted only for `local-fake`. Authorization is checked at preflight and again
immediately before the provider call. Denials are recorded; if a denial cannot be recorded the error propagates.

**ADR-7: Outbox semantics; no exactly-once claim.** `idem_key = sha256(intent, pub digests, shots)` names one job.
The sequence is lease (with a reservation) → re-authorize → commit `dispatching` → `adapter.submit` → receipt
(result artifact first, then `done`). An expired lease without `dispatching` lapses safely, because nothing left
the machine. A row found in `dispatching` at restart becomes `outcome_unknown`. With an adapter that supports
native idempotency, `lookup(key)` reconciles automatically. Without it (IBM SamplerV2 has no client idempotency
key, as far as the installed library shows), the job stays blocked until `reconcile(executed=…)` is recorded. The
local key gives exactly-once *recording*, not exactly-once *execution*.

**ADR-8: Budget = reservations.** Committed = Σ max(reported, reserved) over done jobs, plus reservations of leased,
dispatching, outcome-unknown and failed jobs. A reported 0 (usage not yet computed) never frees budget. This is a
projection-based stop, not a guaranteed ceiling.

**ADR-9: Scientific claims stay out.** CRSM constants, CCCE metrics (Φ, Λ, Γ, Ξ) and PCRB "healing" appear nowhere
in `rqc/`. None influences approval, budget, sandboxing or evidence integrity. The pre-existing
`osiris.runtime.evidence.EvidenceStore` stores `gamma`/`phi`/`xi`/`lambda_value` columns. It is not used by this
workflow; its evidence status is recorded in the repository's claims register, not here.

**ADR-10: Provenance as three artifacts with no circular hash.** A = implementation snapshot (code files at one
commit); B = documents (pre-registration, amendment citing A); C = bundle manifest (A's commit and file hashes, B's
hashes), generated by `make_bundle_manifest.py`, which checks the files against `git show A:path`. No artifact
contains its own hash. The run payload carries A, B and hash(C), so one approval binds all three.
`verify_bundle` refuses hardware use unless C verifies against disk, records `deposited`, and carries the launch
DOI. This replaces an earlier procedure ("write the commit hash into the amendment, then `--amend`") that cannot
work. On 2026-10-08 that procedure left the unreachable commit `a99aebc2` and recorded no hash.

## 3. Requirement → code matrix (amendment workflow)

| Requirement | Implementation | Status | Verifying test |
|---|---|---|---|
| Frozen files unchanged | `experiment.py`, `hardware.py`, `s2_run.py`, `S2_PREREGISTRATION.md` untouched | implemented | `git diff 86e3a3f4 -- …` empty (run in this session) |
| Gathered = sequential results | `GatheringSampler` | implemented | `test_gathered_run_equals_sequential_run` |
| 12 jobs from the real schedule | driver `participants` + coordinator | implemented | `test_registered_schedule_yields_twelve_jobs_of_eighty_pubs` |
| Parity pub order, seed order | sorted keys `(seed, rank, arm)` | implemented | `test_parity_ordered_pubs_and_batch_rows` |
| Write-ahead rows | flush before `run_batch` | implemented | `test_every_submit_row_is_on_disk_before_its_job` |
| Missing/extra/shuffled/duplicate/short results | digest echo + counts | implemented (echo is the adapter's own pub list; a provider reordering pubs inside one result object is not detectable) | `test_malformed_results_are_rejected[*]` |
| Timeouts, cancel, error, no deadlock | barrier timeout, `cancel()`, abort | implemented | `test_barrier_timeout…`, `test_cancel…`, `test_participant_error…`, `test_slow_job_is_not_a_barrier_timeout` |
| No extra rounds / seed replacement | `max_calls`, fixed key set | implemented | `test_unregistered_extra_round_is_refused`, `test_participant_bound_and_unique_keys` |
| Evidence PRAGMAs on every connection, fail closed | `connect_evidence` | implemented | `test_required_pragmas…`, `test_evidence_fails_closed…` |
| Migrations | `MIGRATIONS` + checksum | implemented | `test_migrations_are_idempotent_and_tamper_checked` |
| Telemetry separate, failure-independent | `Telemetry` | implemented | `test_telemetry_is_separate…` |
| Transactions roll back | `Evidence.tx` (BEGIN IMMEDIATE) | implemented | `test_transaction_rollback_leaves_nothing` |
| Append-only events, tamper detection | triggers + chain | implemented | `test_events_are_append_only_and_tampering_is_detected` |
| Artifacts: hash identity, corruption, interruption, traversal, symlink | `ArtifactStore` | implemented | four `test_artifact_*` tests + `test_evidence_detects_missing_referenced_artifact` |
| Approval binding, expiry, revocation, scope, target, budget | `Evidence.authorize` | implemented | `test_approval_is_bound…`, `test_budget_mismatch…`, `test_tampered_intent_payload…`, `test_approval_revoked_between_lease_and_dispatch_is_caught` |
| Crash before / during dispatch, after receipt | outbox states, `recover`, replay | implemented (simulated by abandoning objects, not by killing a process) | `test_crash_before_dispatch…`, `test_crash_during_dispatch…`, `test_receipt_then_restart…` |
| Ambiguous outcome, no idempotency | `outcome_unknown` + `reconcile` | implemented | `test_ambiguous_outcome_without_idempotency…`, `…reconciled_as_executed…` |
| Native idempotency | `MockAdapter(supports_idempotency=True)` | implemented (mock only) | `test_native_idempotency_reconciles_by_lookup` |
| Concurrent leases, stale workers | `lease` under BEGIN IMMEDIATE, expiry | implemented | `test_concurrent_lease_acquisition_has_one_winner`, `test_crash_before_dispatch…` |
| Budget reservations incl. unknown outcomes; unreported usage | `committed_seconds` | implemented | `test_budget_reservations…`, `test_unreported_usage_never_frees_budget`, `test_definite_failure…` |
| Hardware refused without approval, before network | driver order: DOIs → `verify_bundle` → authorize → then import service | implemented | `test_hardware_mode_refuses_without_dois_bundle_or_approval` (sockets blocked) |
| Provenance without circular hashes (ADR-10) | `verify_bundle`, `make_bundle_manifest.py` | implemented | `test_bundle_*` (control), `tests/test_rqc_s2_bundle.py` |
| End-to-end fake backend + restart replay | driver `--fake` | implemented | `test_batched_driver_on_a_fake_heron_and_restart_replays` |
| No network in tests | autouse fixture blocks connect/getaddrinfo | implemented for these two files | every test in both files |
| Governed command execution (CIL, `./dna exec`) | **absent** in this worktree | absent | — (this session's shell commands ran through Claude Code's own tool, not an OSIRIS-governed executor; nothing was mediated or audited by OSIRIS) |
| High-assurance bypass disabled | **absent** (no bypass mechanism exists here to disable) | absent | — |
| Worker sandbox (network deny, resource limits) | **absent**; the fake run executes in-process | absent | — |
| External anchor for the evidence chain | none | absent | — |
| IBM reconciliation by job tags | not implemented; `QiskitBatchAdapter.lookup` raises | absent | — |

The console's L0… layers (`osiris_cli/architecture.py`) are a description of the console's governed-learning
pipeline. They are not the CIL L0–L6 in the proposed control-plane design, and nothing here maps onto them.

**Exchange-log failure at entry 14:** that log (`osiris_cli/living.py`, `~/.osiris/…/exchanges.jsonl`) is not part
of this workflow's approval or evidence chain, which is `rqc.control` plus the `rqc` `Ledger`. It was not
investigated here, and it does not gate this workflow.

## 4. Preflight checklist (publication, then execution)

Publication (each step needs approval):
- [x] Author decisions in amendment §9 (shots, blocks, §5 exposure). Made 2026-10-09: 2,000 shots, 2 × 40 blocks,
      exposure accepted with the primary test unchanged.
- [ ] `pytest tests/test_rqc.py tests/test_rqc_batch.py tests/test_rqc_control.py tests/test_rqc_s2_bundle.py`
      green on a full `git archive` export of each commit, with sockets blocked and PYTHONPATH unset.
- [ ] Implementation snapshot (A) committed first. Then, in a **later** commit, the amendment (B) cites A's full
      hash and `make_bundle_manifest.py --implementation-commit A` writes the manifest (C). Never amend to insert a
      hash (ADR-10).
- [ ] `git diff 86e3a3f4 -- rqc/experiment.py rqc/hardware.py docs/rqc/S2/s2_run.py` and
      `git diff 964efe19 -- docs/rqc/S2_PREREGISTRATION.md` both empty.
- [x] Read-only check that DOI 10.5281/zenodo.23241223 is the S2 deposit with sha256 `ee179e8f…e5d` (done 2026-10-09).
- [x] Deposit amendment 5; record its DOI in the amendment and the driver invocation (10.5281/zenodo.23256344, 2026-10-09).

Execution (separate approval):
- [ ] Create the `ibm-quantum` intent with the final DOIs; record an `execute` approval bound to its payload hash
      (target `ibm-quantum`, budget 600, expiry within the run window).
- [ ] Read-only usage check reports ≥ 600 s; no other jobs pending on the account.
- [ ] Launch with `setsid nohup`; evidence directory on local disk (not a network mount).
- [ ] On any `outcome_unknown`: stop and reconcile by job id/tags before anything else.

## 5. Live read-only checks that would need separate approval

- `QiskitRuntimeService().usage()`: current allocation (the 2026-10-08 snapshot is historical).
- `service.backends(operational=True)`: which Heron the rule selects on the run date.
- Whether Batch mode is available on the Open plan for this account.
- A Zenodo lookup of 10.5281/zenodo.23241223 and the file hash of its pre-registration.
- Whether SamplerV2 accepts job tags under the installed version (needed for reconciliation by tag).

## 6. Open local issues outside this workflow

- **Stray `evidence.sqlite`** at the worktree root: 0 bytes, untracked, created 2026-10-08 12:10:57, with no
  `-wal`/`-shm` files. No code refers to that path; `rqc.control.Evidence` opens `<root>/evidence.sqlite` under an
  explicit evidence directory. It matches a diagnostic snippet that ran `sqlite3.connect('evidence.sqlite')` in the
  worktree. That call creates an empty database and reads its defaults, so it verifies nothing about the
  application. It is a candidate accidental artifact; removal awaits approval.
- **NCLM workflow** (`start_nclm_workflow.sh`): ignores all arguments (no `--dry-run`), runs
  `cd /root/osiris-cli` (inaccessible to this user), requires `OSIRIS_PG_URL`, and starts
  `nclm_analysis.py --watch` in the background. It is a separate issue, not part of S2.
- **Branch upstream:** `feat/rqc-s0` tracks `origin/main` (`branch.feat/rqc-s0.merge = refs/heads/main`). Any
  eventual push must name its destination explicitly (`origin`, `refs/heads/feat/rqc-s0`), never rely on the
  upstream, and never target `main`.

## 7. Backlog

**Phase 1:**
1. Move the IBM credential behind a separate OS user or service that exposes only `submit(intent_id, job)`, checking
   approvals itself. This is the only change that makes "an agent cannot submit" true rather than conventional.
2. Reconciliation by provider job tags: tag each job with `idem_key`, and add an adapter `lookup` that searches tags.
3. Anchor the evidence chain head externally (signed commit, or a hash deposited with the run).
4. An approval CLI requiring the operator to type the payload hash; record it as a signed git commit.
5. Measure arm × job interaction: optional reference pubs per job (decide before deposit, or in a later study).

**Phase 2:**
1. Fold `rqc.control` and `osiris.runtime.evidence` into one evidence service. The latter lacks three PRAGMAs and
   read-back, accepts `:memory:`, and has a lease-less outbox.
2. A worker sandbox (network-deny namespace or container) for any execution beyond in-process fake runs.
3. A governed command layer (typed actions, argument vectors, no shell strings) if OSIRIS is to run tools for agents.
4. Real power-loss testing on the target storage, if durability claims beyond process crashes are ever needed.
