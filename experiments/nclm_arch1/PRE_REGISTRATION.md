# NCLM-ARCH-1 — do the CRSM components make the core a better byte model? (pre-registered 2026-10-08)

Written and committed **before any run**, in the release (v4.5.2) that makes the phase-conjugate corrector act
the same way in training and in scoring. The result goes into `RESULT.md` in this folder as PASS, FAIL or
NO-DIFFERENCE against the criterion below, whichever it is. Nothing here is re-tuned after the runs.

## Why

The core (`osiris.nclm.SovereignTransformerV2`, 726,304 parameters, byte-level, built by
`osiris_termux_console._organism_build`) is not a standard transformer. Five components carry the CRSM
framework's constants:

| component | what it computes | code |
|---|---|---|
| torsion-locked attention | scores × α + β·diag(scores); α, β learnable per head, initialised at sin 51.843° = 0.787 and 0.946·cos 51.843° = 0.584; the diagonal is taken from the scores' values (no gradient to q, k through it) | `osiris/nclm/sovereign_mechanics.py`, `TorsionLockedAttention` |
| pilot-wave modulation | scores × (1 + exp(−\|i−j\|/T)), a fixed factor in [1, 2] — a per-distance temperature | same, `_pilot_wave_factor` |
| phase-conjugate corrector | after the attention residual, when Γ = v/(v+1) > 0.3 (v = mean variance of the residual stream): x ← g ⊙ Θ(x with odd dimensions negated) + (1 − g) ⊙ x, with a learned gate g and projection Θ | same, `PhaseConjugateCorrector` |
| golden-ratio FFN scale | FFN output × 1/φ = 0.618 | same, `_SovereignFFN` |
| φ position table | frequencies 1/φ^(2i/d) ∈ [0.39, 1] rad/byte times the θ-lock factors; longest wavelength ≈ 21 bytes (even dimensions), ≈ 28 (odd), inside a 128-byte context | `osiris/nclm/positions.py` |

The claims register already says what the constants are not (THETA_LOCK and CHI_PC: REFUTED as physical
constants). Whether the components help *as architecture* — whether a byte model with them predicts held-out
text better than one without — has never been measured. Two facts make it worth measuring now:

1. Until v4.5.2 the corrector ran in training but was skipped whenever gradients were off: in every held-out
   score, in early stopping and in generation. No held-out number on record measures the network that was
   trained.
2. As scored before v4.5.2, the core never got below its unigram baseline (best held-out documents 5.923 vs
   5.026 bits/byte on 2026-09-30; NCLM_CORE: 5.56 vs 4.68 on held-out replies). If the architecture is part of
   the reason, a standard transformer of the same size should do better.

## The one change

| arm | blocks | attention | FFN | positions | parameters |
|---|---|---|---|---|---|
| `crsm` | `SovereignBlock` — exactly the live core | T-lock + pilot wave | 256, × 1/φ | φ table | 726,304 |
| `standard` | `TransformerBlock` (pre-norm) | scaled dot-product (`pilot_wave=False`) | **384**, unscaled (`golden_scale=False`) | sinusoidal, base 10,000 | 725,760 |

These are `ORGANISM_ARCHES["crsm"]` and `ORGANISM_ARCHES["standard"]` in `osiris_termux_console.py`.

**The same in both arms:**
- dim 128, 4 layers, 4 heads, context 128, byte vocabulary, dropout 0, no fractal embedding;
- AdamW (lr 3·10⁻⁴, weight decay 0.01), gradient clip 1.0, 50-step warm-up and cosine decay (the trainer's
  schedule).

These settings were chosen for the CRSM core and are not tuned for either arm.

**Parameter count is matched** by widening the standard arm's FFN from 256 to 384:
- The CRSM components add 33,032 parameters per block (132,128 in all). With an FFN of 256 the standard arm
  would have 594,176 (−18 %), and a CRSM win could be bought by size alone.
- At 384 the difference is 544 (0.075 %).
- 512 of the CRSM arm's parameters (the corrector's `zero_point`, 128 per block) are never used in the forward
  pass and get no gradient, so the counts that train differ by 32.
- Compute is matched too: the corrector's two 128×128 projections and the 128 extra FFN units each cost 32,768
  multiply-adds per byte per block.

This is a **bundle** comparison. The two arms differ in five components at once, and the code cannot separate
them: either `torsion_lock` or `phase_conjugate` selects `SovereignBlock`, which always applies T-lock, the
corrector, the pilot wave and the 1/φ scale. A PASS or FAIL says which architecture is better here, not which
component. Attributing it needs a leave-one-out follow-up, pre-registered separately.

## Fixed conditions

- **Code:** osiris-cli v4.5.2. The runs use the model and trainer code of the commit that adds this file.
  `run.py --check` refuses to launch if any of these hold:
  - `osiris/nclm`, `osiris_termux_console.py`, `osiris_cli/train.py` or `osiris_cli/living.py` differ from
    that commit;
  - `osiris.nclm` is imported from anywhere but this repository;
  - either arm's parameter count differs from the table;
  - a training-mode and a scoring-mode forward pass give different losses (the v4.5.2 corrector fix);
  - a seed below is found in any run manifest under `~/.osiris`.

  Run it from a checkout of the registration commit (for example `git worktree add ../osiris-arch1 <commit>`),
  so that later releases do not block it.
- **Architecture:** `arch.json` (`{"arch": "crsm" | "standard"}`) sits in each run's `OSIRIS_ORGANISM_HOME`.
  Each run's manifest records the architecture it built and its parameter count (`model`). The live core
  (`~/.osiris/nclm_organism`, which has no `arch.json`) builds `crsm` and is not touched.
- **Inputs:** frozen once at the first launch, as in NCLM-Mix-1.
  - `corpus.json`, `exchanges.jsonl`, `distill.jsonl` and the built corpus (`train.freeze_corpus`, archive
    roots `.`) are copied to `~/.osiris/experiments/nclm_arch1/inputs/`.
  - The SHA-256 of each is recorded in `inputs.sha256.json` and checked at every later launch.
  - Every run reads only that snapshot (`--living-home`, `--frozen-corpus`): identical documents, held-out
    split (`sha256(path) % 10 == 0`), lessons and evaluation windows.
- **Training:**
  - fresh weights; `--all`; `--distill 0`;
  - mix docs / lessons / archive **0.5 / 0.3 / 0.2** — the default, set explicitly and not revised, whatever
    NCLM-Mix-1 finds;
  - batch 8; 12,000-step cap with no wall-clock limit; `--no-rescore`.
- **Evaluation:**
  - at the start, every 200 steps and at the end;
  - on the same 48 held-out-document windows and up to 48 held-out-chat windows (127 predicted bytes each);
  - early stopping after 5 evals without a gain of at least 0.01 bits/byte on held-out documents;
  - the best checkpoint is kept.
- **Order:**
  - one run at a time, each started when the 1-minute load average is ≤ 3;
  - both arms of a seed run back to back, never alongside other NCLM training;
  - runs are seeded (weight init through numpy; batches through `random.Random(seed)`) and deterministic, so
    the two arms of a seed see the same batches in the same order.

## Seeds

**200–207**: eight per arm, paired by seed. No NCLM run on record in this repository uses them:

| source | seeds |
|---|---|
| NCLM-Mix-1 | 0, 1, 2 and 999 |
| organism_sim | 0–4, 30–34, 50–54, 60–64, 70–74, 80–84 |
| the in-memory checks below | 0, 3, 4, 5, 7, 9, 10, 11, 12, 101, 20261008 |

The replay seeds of NCLM-GATE-PILOT-0/1 are recorded only in `~/experiments/nclm_gate_pilot1/`, so they are
checked there before launch. On a collision the block moves to the next eight unused seeds ≥ 200; that is
recorded in `EXECUTION.md` before the first run.

## Measurements (per run, from its `progress.jsonl` and `manifest.json`)

- **primary:** best held-out-documents bits/byte, the minimum `heldout_docs_bpb` over all evals. It can differ
  by less than 0.01 from the checkpoint early stopping keeps, which moves only on gains of 0.01 or more.
- **guard:** held-out-chat bits/byte at that same eval.
- **reported, not judged:**
  - step of the best eval;
  - final-eval held-out-documents score (unselected);
  - stop reason, steps and hours;
  - whether the best is below the run's unigram baseline;
  - runs that hit the step cap.

Per seed:
- **gain = standard − crsm** on the primary (positive = the CRSM arm is better);
- **chat change = crsm − standard** on the guard (positive = the CRSM arm is worse on chat).

## Criterion (stated before the runs)

The minimum effect is δ = **0.05 bits/byte**. Over the 8 seeds, compute the mean gain ḡ, its SD, and the
one-sided 95 % bounds ḡ ± 1.895·SD/√8 (t with 7 degrees of freedom).

**PASS** (the CRSM arm is better) if all of these hold:
1. ḡ ≥ +0.05;
2. the lower bound is > 0;
3. the CRSM arm wins at least 6 of 8 seeds;
4. guard: the mean chat change is ≤ +0.10 (no buying document scores with conversation).

**FAIL** (the standard arm is better) is the mirror: ḡ ≤ −0.05, upper bound < 0, standard wins at least 6 of
8, and the mean chat change is ≥ −0.10.

**NO-DIFFERENCE** otherwise, with one label:
- *equivalent within ±0.05* if both bounds lie inside (−0.05, +0.05) (two one-sided tests at 5 %);
- *mixed* if conditions 1–3 hold for one arm but the guard fails;
- *inconclusive at this size* otherwise.

Edge cases:
- **Guard size.** The guard is judged only if every run has at least 8 held-out-chat windows (about 1,000
  predicted bytes). Otherwise it is reported, not judged, and RESULT.md says so.
- **Divergence.** A run whose training loss or held-out score becomes non-finite is *diverged*. Its seed
  counts as a win for the other arm in condition 3 and is left out of ḡ and the bounds (n = 7, t = 1.943).
  With more than one such seed the verdict is NO-DIFFERENCE (inconclusive).
- **No added seeds.** No seeds are added after any result is seen.

This rule is `decide()` in `run.py`.

## Power (why 8 seeds per arm)

- **Run-to-run variance on record.** The only figure is NCLM-GATE-PILOT-1 (NCLM_CORE): seed means of
  0.030–0.101 bits/byte over 5 replay seeds, ≈ 86 % of the variance. Range / 2.33 gives σ_run ≈ 0.03.
- **One arm vs two.** The register's "about 4 runs for 0.05" is for one arm. A paired difference of two arms
  has σ_d = √2·σ_run ≈ 0.043 if a seed's two runs are uncorrelated. That needs about 6 pairs to reject zero at
  a true 0.05, and more to tell "no difference" from "too noisy to say".

The rule above with 8 pairs, applied by `run.py`'s own `decide()` to 20,000 simulated experiments per row
(normal errors, uncorrelated arms):

| σ_run | true gain | PASS | FAIL | NO-DIFF equivalent | NO-DIFF other |
|---|---|---|---|---|---|
| 0.03 | 0 | 0.00 | 0.00 | 0.82 | 0.18 |
| 0.03 | +0.05 | 0.50 | 0.00 | 0.05 | 0.45 |
| 0.03 | +0.08 | 0.98 | 0.00 | 0.00 | 0.02 |
| 0.03 | −0.08 | 0.00 | 0.98 | 0.00 | 0.02 |
| 0.05 | 0 | 0.02 | 0.02 | 0.22 | 0.75 |
| 0.05 | +0.08 | 0.84 | 0.00 | 0.00 | 0.16 |

- **If runs vary more.** Fresh-initialised runs may vary more than the pilot's replay seeds. The bounds widen
  with the observed SD, so extra noise moves the result toward "inconclusive", not toward a false PASS or FAIL.
- **Cost.** At ≈ 0.6 s/step (the 2026-09-30 rate on the author's machine) a run takes at most 2 h, and all 16
  at most 32 h.

## Validity

A run counts only if its manifest shows all of the following:
- the registered architecture and parameter count;
- the frozen inputs (identical `bytes`, `chat_train`, `chat_heldout`, `distill_lessons` in all 16 runs);
- pool weights 0.5 / 0.3 / 0.2;
- the same commit as every other run;
- an end record.

An invalid run is set aside unread, logged in `EXECUTION.md`, and re-run with the same seed. `--analyse`
gives no verdict until all 16 runs are valid.

## Caveats stated in advance

1. **Bundle, not components** (above).
2. **Hyperparameters were set for the CRSM core**, and neither arm is tuned. An untuned arm can lose for reasons
   that are not architectural, in either direction.
3. **The position tables differ a lot.** The φ table has no wavelength longer than ≈ 28 bytes, so absolute
   positions alias inside the 128-byte context. The standard table spans 6 to ≈ 54,000 positions. A
   difference could come from this alone.
4. **The corrector is a threshold switch** on Γ, which is computed over the whole batch (8 windows in
   training, 1 in evaluation), so whether it fires can depend on batch composition. Measured Γ was 0.57–0.99
   in every block, far above 0.3. v4.5.2 makes training and scoring apply the same rule but does not change
   the rule.
5. **Selection on the test windows.** "Best over evals" is a minimum over ~30–60 evals on the same held-out
   windows. Both arms get the same advantage, and the unselected final-eval score is reported.
6. **Small and specific.** The test is 48 windows × 127 bytes ≈ 6,100 predicted bytes from ~22 held-out
   documents: one corpus, ≈ 0.73 M parameters, at most 12,000 × 8 × 127 ≈ 12 M training bytes.
7. **Not comparable with earlier numbers.** Held-out scores of the CRSM core before v4.5.2 (NCLM-Mix-1, the
   2026-09-30 run, the pilots, live speaking-gate scores) were computed without the corrector, which is a
   different function from the one trained. ARCH-1's CRSM numbers are not compared with them.
8. **A PASS would not validate CRSM physics.** It would say these operations help a small byte model on this
   corpus. θ_lock, χ_PC and Γ as physical quantities are untouched (THETA_LOCK and CHI_PC stay REFUTED).

## What was seen before registration

These runs were made on 2026-10-08, before this file was written, while finding and fixing the corrector
defect and checking that the standard arm builds. All were in memory, on this repository's own docs (not the
frozen inputs), with one seed per configuration.

- **One memorised 127-byte window, 150 steps (the check that led to v4.5.2).**
  - The live configuration scored 0.002 bits/byte with gradients on and 8.04 with them off.
- **Up to 1,000 steps, seed 20261008, held-out repository files (22,225 bytes, unigram 5.31).**
  - The live configuration scored **4.79** at step 1,000 with the corrector applied (v4.5.2 scoring) and 6.35
    with it skipped (v4.5.1 scoring).
  - The same configuration with the corrector disabled scored **4.49** at step 1,000 (5.31 at step 300).
  - The V1 block (no T-lock or corrector, pilot wave and 1/φ scale kept, FFN 256, φ table) scored 5.29 at
    step 300 and was not run further.
- **40 steps, seed 101 (the standard-arm build check).**
  - The standard arm's training loss fell faster (6.61 → 3.93 nats/byte vs 6.46 → 4.80).

These hint that the corrector may not help. They are one seed, short runs and a different corpus, and they are
exactly why the question is registered rather than answered from them. The arms, metric, seeds and criterion
come from the NCLM_CORE power figures above, not from these numbers.

## How it runs

1. `python experiments/nclm_arch1/run.py --check` runs the preflight only.
2. `python experiments/nclm_arch1/run.py` runs the 16 runs:
   - one at a time;
   - each with its own checkpoint folder (`OSIRIS_ORGANISM_HOME` + `arch.json`) and runs folder;
   - `PYTHONPATH` = this repository only, no thread caps, `--no-rescore`.

   The driver can be relaunched. Finished runs are skipped; unfinished ones must be set aside first.
3. `python experiments/nclm_arch1/run.py --analyse` checks validity, computes the verdict and writes
   `results.json` and `RESULT.md`.

Procedural events go to `EXECUTION.md`.

## What each outcome changes

The CRSM_ARCH entry in the claims register is updated as follows:

| outcome | register entry |
|---|---|
| PASS | SUPPORTED within this scope |
| FAIL | REFUTED, which points at the standard architecture for the next core |
| NO-DIFFERENCE (equivalent) | NULL |
| NO-DIFFERENCE (mixed or inconclusive) | stays UNTESTED, with the numbers; any follow-up is pre-registered anew using the observed SD |
