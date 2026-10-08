# OSIRIS v4.5.2 — release notes (2026-10-08)

A correction release with one large consequence: **every held-out score of the core before this release
measured a different network from the one that was trained.** This release fixes that, stops old scores from
counting toward the speaking gate, pre-registers a test of whether the CRSM layers help the core at all
(NCLM-ARCH-1, not run), and adds claims-register verdicts for the premises of a proposed quantum-LLM roadmap.

Verified on the release tree:
- the full test suite on Python 3.11, 3.12 and 3.13, run with the home directory hidden;
- a wheel-install smoke test (`scripts/ci_local.sh`).

Not run for this release: GitHub Actions (billing) and Cloud Build.

## Fixed — the core trained one network and was scored as another (`osiris/nclm/sovereign_mechanics.py`)

**The defect.** `PhaseConjugateCorrector` returned its input unchanged whenever gradients were off
(`... or not _is_grad_enabled()`).
- The live core (`SovereignTransformerV2`, `phase_conjugate=True`) therefore applied the corrector in every
  block during training: its trigger Γ = v/(v+1) was 0.57–0.99 in every check, far above its 0.3 threshold.
- It applied the corrector in no block whenever gradients were off. That covers everything that scores or
  speaks:
  - the speaking gate's held-out scores (`NclmCore.bits_per_byte`);
  - the batch trainer's evaluations, its early stopping and the "best" checkpoint it restores;
  - `prepost` (the NCLM-GATE-PILOT scorer);
  - `rescore_chat`;
  - generation: the core's own voice, `/self`, and `nclm_aer_evaluator` proposals.
- The skipped layers hold 131,584 trained parameters, 18 % of the core's 726,304.
- The condition is in the oldest version of the file checked (2026-04-19), and in every version since.

**The size of the gap**, from in-memory checks on this repository's text (one seed each, not the live core or
your data):

| check | corrector applied (training's network) | corrector skipped (what was scored) |
|---|---|---|
| one 127-byte window memorised for 150 steps | 0.002 bits/byte | 8.04 bits/byte (worse than uniform) |
| fresh core, 1,000 steps, held-out repository files (unigram 5.31) | 4.79 bits/byte | 6.35 bits/byte |
| the new regression test (dim 32, 30 steps) | 0.066 nats/byte | 4.96 nats/byte |

**The fix.** The corrector now follows the same rule with gradients on or off. No parameter changed, and
existing checkpoints load as before.

**Two regression tests pin it** (`tests/test_sovereign_transformer.py`): the same logits with and without
gradients, and the same loss after training. Both fail on v4.5.1.

**No reference cycles without gradients.** The corrector's backward hook is attached only when gradients are on.
The first version of this fix attached it under `no_grad` too. The hook is a closure that refers to its own
tensor, so it kept each scoring or generation graph alive until the cycle collector ran: 191 MB peak for 10
forwards of the live core, against 21 MB now. Logits are unchanged. A test asserts that a no-grad forward
leaves nothing for the collector.

**The early-stopping incident may have been this.** The pattern recorded for 2026-09-30 is: training loss
fell 3.9 → 1.7 nats/byte while held-out rose 7.2 → 9.9 bits/byte, worse than uniform. That incident is why
early stopping exists (RELEASE_NOTES_v4.2.0.md), and it was put down to overfitting. It is what this defect
produces by itself: the more the weights rely on the corrector, the worse the network without it scores. This
has not been re-measured on the original run.

## Benchmark comparability

Not comparable with anything from v4.5.2 on (they scored the network without the corrector):
- live speaking-gate scores in `~/.osiris/living/stats.json`;
- `heldout_*_bpb` in every `train_runs/*/progress.jsonl`, and which checkpoint early stopping kept;
- NCLM-GATE-PILOT-0 and PILOT-1 (+0.043 and +0.067 bits/byte; the core at 5.56 vs a unigram's 4.68);
- NCLM-Mix-1 (see `experiments/nclm_mix1/EXECUTION.md`, 2026-10-08);
- the README's 7.60 vs 5.03;
- `nclm_final_report.csv`;
- the DD sublattices `nclm_aer_evaluator` proposed.

None of these has been re-scored. The claims register (NCLM_CORE, NCLM_PC_CORRECTOR), the README, the mentor's
system prompt and `.zenodo.json` now say so.

Unchanged and still comparable:
- training losses (`nclm_loss.log`, organism history, the "train" rows of progress.jsonl);
- unigram baselines;
- the exchange hash chain;
- checkpoints;
- the benchmark: suite `09037df6…` and runner `d18f87f4…` are as in v4.5.0 and v4.5.1 (the runner does not
  import `osiris.nclm`).

## New — scores carry their scorer; old ones do not count (`osiris_cli/living.py`, `osiris_cli/train.py`)

- **Scores carry their scorer.** Each held-out score now has a 5th field, `SCORER = 2`. Scores without it
  were written before this release.
  - The tag comes from the `osiris.nclm` package actually loaded (`SCORING_FORWARD`), not from the console.
  - An older copy of the model code on `PYTHONPATH`, or the phone's fallback checkout, therefore writes scores
    tagged 1, and they never count.
  - `--rescore-only` refuses to run on such a copy and names its path.
- **The gate counts only current scores.** Older scores are counted as `stale` and shown in `/osiris`, in the
  gate note and in the mentor's state line, with how to replace them.
- **Merging prefers the newer scorer.** When stats are merged, a score from the newer scorer wins over an
  older one at the same step. A console that is still open therefore cannot write a pre-fix score back over a
  rescored one, provided that console runs v4.5.2.
- **Rescoring without training.** `osiris train --rescore-only` (in the console: `/train rescore`) rescores
  every held-out exchange with the current weights and prints the gate before and after.
- **Run manifests record more.** They now include:
  - the architecture, configuration, parameter count and scorer (`model`);
  - the number of evaluation windows;
  - the package version (`code.git_head` is empty on a wheel install).

### Upgrading

1. Check that no trainer is running: `osiris train --status`. If one is, run `osiris train --stop`.
2. Quit every OSIRIS console from v4.5.1 or earlier. An old console merges by step only and can write old
   scores back.
3. Optionally, keep the old scores: `cp ~/.osiris/living/stats.json ~/.osiris/living/stats.v4.5.1.json`.
4. Run `osiris train --rescore-only`. This scores the same weights with the fixed scorer, and refuses if the
   loaded model code is older than v4.5.2. Its message also counts any old scores that have no exchange left in
   the ledger to rescore; those stay uncounted. The next
   `osiris train` run would also rescore, but only after training has changed the weights, mixing the fix's
   effect with training's.

Expect the gate figures to change, possibly a lot. If 30 rescored held-out exchanges average ≤ 2.0 bits/byte
and beat the unigram baseline, the gate opens and the core starts answering in its own voice, recorded as
`voice: "core"` in the exchange ledger. That is the gate working as designed, on scores that now measure the
trained network.

The phone harness (osiris-mobile-termux) shares this checkpoint format:
- Checkpoints move between versions in both directions unchanged.
- Any score or generated text from a pre-4.5.2 harness measures the network without the corrector, so don't copy
  its stats into a v4.5.2 `stats.json`.
- Update `~/crsm/osiris-cli` on the phone too: the console falls back to it for `osiris.nclm`.
- To check which model code is loaded:
  `python -c "import osiris.nclm as n; print(n.__file__, getattr(n, 'SCORING_FORWARD', 1))"`. It must print 2.

## New — NCLM-ARCH-1 pre-registration, and the code it needs (not run)

`experiments/nclm_arch1/PRE_REGISTRATION.md` asks whether the CRSM components help the core as a byte model:
- **The two arms.** The live core is compared with a standard pre-norm transformer of the same size.
  - Same size means 726,304 vs 725,760 parameters; the standard arm's FFN is widened to 384.
  - The standard arm uses base-10000 positions.
- **Design.** 8 paired seeds (200–207) on frozen inputs. The primary outcome is the best held-out-documents
  bits/byte, with a minimum effect of 0.05.
- **Outcomes, fixed in advance.** PASS, FAIL or NO-DIFFERENCE. `decide()` in `run.py` implements the rule, and
  20,000 simulated experiments per scenario reproduce the power table.
- **What was seen first.** One-seed checks made before registration hint that the corrector may not help. The
  pre-registration lists them.
- **Amendment 1, before any run.** It records:
  - the memory fix above;
  - scorer tagging;
  - a preflight that compares the watched code with the latest commit to the pre-registration or its execution
    log;
  - that the power basis (pilot replay seeds, scored before the fix) may understate run-to-run variance;
  - a held-out score at the last step both runs of a seed reached, reported but not judged.

`python experiments/nclm_arch1/run.py --check` runs the preflight, then `run.py` runs the experiment and
`--analyse` writes the result.

What it needed:
- **`SovereignConfig.positional`**: `"phi"` (the default, so every existing checkpoint is unchanged) or
  `"standard"`, the base-10000 table (`standard_sinusoidal_positional_encoding`).
- **`ORGANISM_ARCHES`, and `arch.json` in a checkpoint folder**, select the architecture
  (`osiris_termux_console._organism_arch`). The live folder has none and is `crsm`, built exactly as before.
  An unknown `arch.json` is an error, not a fallback.
- **`_organism_load` checks every tensor's shape before copying.** Loading a checkpoint of another
  architecture used to overwrite the leading tensors before failing, and then report "starting fresh" with a
  half-loaded model. `prepost` builds a snapshot's own architecture.
- **SovereignConfig's flags are not independent.** `torsion_lock` or `phase_conjugate` selects `SovereignBlock`,
  which always applies T-lock, the corrector, the pilot-wave factor and the 1/φ scale. `pilot_wave` and
  `golden_scale` act only on the plain block. This is documented in `SovereignTransformerV2`; ARCH-1 is
  therefore a bundle comparison.

## Companion change: dnalang-core 0.3.0

Circuit lineage on the run ledger
([osiris-dnalang/dnalang-core#1](https://github.com/osiris-dnalang/dnalang-core/pull/1)):
- `evolve(..., ledger=...)` and `breed_from_ranking(..., ledger=...)` record each generation's genomes with
  parents, operator, fitness and, optionally, the compiled circuit's hash.
- `dnalang trace-lineage` walks an evolved circuit back to generation 0.
- dnalang's `ledger.py` is unchanged, so this console's genome ledger is unaffected.
- `pyproject.toml` installs dnalang from git `main`, so 0.3.0 arrives when that PR merges.

## Claims register

Seven entries are added; the register now has 40.

| entry | verdict | finding |
|---|---|---|
| F_MAX | REFUTED | "F_max = 1 − φ⁻⁸ ≈ 0.9787 bounds Bell-state fidelity". Published experiments exceed it: 0.993 (Benhelm et al. 2008), and 0.999 / 0.9992 from Bell states (Ballance et al.; Gaebler et al. 2016). "0/189 violations" on hardware that never passed 0.9773 cannot test a ceiling. |
| COHERENCE_QUANTIZATION | OVERCLAIM | Its three "validations" (150, 200, 250 µs) are multiples of 50 µs. With ±15 % bands, every T2 above 117 µs passes. |
| NCLM_MECHANICS | NOT_MEASURED | "Pilot-wave", "torsion-locked" and "phase-conjugate positional" are ordinary transformer parts under physics names, and the core is a causal decoder. |
| NCLM_PC_CORRECTOR | NOT_MEASURED | Γ is a variance ratio; F_purified is never computed; `zero_point` is never used. Records the v4.5.2 fix. |
| QUANTUM_LM | NO_EVIDENCE | Quantum-guided attention, quantum-aided in-context learning, NCQM. Nothing is on record. A gate computed from a simulated state is classical, so a classical control is required. |
| QEC_LLM_SAFETY | RULED_OUT | A 3-qubit GHZ/repetition code flags flips after encoding, not which token was encoded. Both codewords have syndrome 00 (computed). |
| CRSM_ARCH | UNTESTED | Pre-registered as NCLM-ARCH-1. |

Other changes to the register:
- **NCLM_CORE** states that both pilots were scored before the fix.
- **Pattern fixes.** THETA_LOCK now matches "θ-lock", and CHSH_TEST now matches "CHSH_bounds".
- **`/status`** shows F_max with F_MAX's verdict; it showed K8_REVIVAL's.
- **New computed checks:** `1 − φ⁻⁸`, multiple-band coverage, the φ position table's frequency span, and the
  repetition code (`physics_checks.repetition_code`).
- **Tests** now accept journal DOIs as evidence.

## Known issues

- **Nothing has been re-scored.** The fix's effect on the live core, the pilots and Mix-1 is unknown until
  they are re-scored (or re-run). Only the synthetic numbers above are measured.
- **NCLM-1 may use the old scorer.** Its evaluator (`NCLM-1_v1_evaluate.py`, not in this repository) should
  pin v4.5.2's scoring forward before any run, if it uses `NclmCore.bits_per_byte` or `prepost.byte_nats`.
- **The corrector is still batch-dependent.** It is a threshold switch on Γ averaged over the whole window and
  batch.
  - Training and scoring now apply the same rule, but whether it fires can in principle depend on batch
    composition and on later bytes.
  - That is the one exception to "causal decoder" (NCLM_MECHANICS).
  - Γ has never been seen near 0.3: the minimum across checks was 0.57, including single-byte inputs.
- **The pilot-wave factor depends on the window length.** Its decay is λ = 1/T, so a reply shorter than 127
  bytes is scored with attention scaling that the batch trainer, which always uses T = 127, never trains.
  Console `learn()` uses the same variable windows. This was true before this release too.
- **The T-lock diagonal is still detached.** It is read from the scores' values, so no gradient reaches q and
  k through it. Unchanged.
- **The phase-conjugate `zero_point` is still never used.** It is kept so that checkpoint indices do not move.
- **Carried over from v4.5.1:**
  - importing `osiris_cli` reads Google Secret Manager when `OSIRIS_SECRETS_SOURCE=gcp`;
  - the Gemini output cap includes thinking tokens;
  - the mentor prompt's "learns only from material you approve" wording.
