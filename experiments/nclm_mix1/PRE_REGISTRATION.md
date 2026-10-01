# NCLM-Mix-1 — does training on more of Devin's own text improve held-out text? (pre-registered 2026-09-30)

Written and committed **before any run**. The result goes into `RESULT.md` in this folder as
PASS or FAIL against the criterion below, whichever it is. Nothing here is re-tuned after the
runs.

## Why

The core (`osiris.nclm` SovereignTransformerV2, ~726K parameters, byte-level) trains on three
pools: verified documents (`~/.osiris/living/corpus.json` roots), lessons (chat exchanges +
grounded distillation), and the home-directory archive (`--all`). The first early-stopped run
(2026-09-30, `train_runs/20260930T090152`, mix 0.5 / 0.3 / 0.2) reached a best held-out-documents
score of **5.923 bits/byte** at step 5,600 and stopped at 6,600 — still above the unigram
baseline (5.026). The held-out set is 22 of the verified documents (split by
`sha256(path) % 10 == 0`). The archive is the largest pool and the least like them.

## The one change

| arm | docs | lessons | archive |
|---|---|---|---|
| `control` | 0.50 | 0.30 | 0.20 | (the current default, set explicitly) |
| `docs-heavy` | 0.80 | 0.15 | 0.05 |

Everything else is identical and fixed: fresh weights; `--all` corpus as built at launch;
`--distill 0` (the 82 existing distilled lessons are used, no new ones); batch 8; eval every
200 steps on the same held-out windows; early stopping after 5 evals without a ≥ 0.01 bpb
gain; best checkpoint kept; a 3-hour cap per run; weight init and batch sampling seeded.

**Seeds:** 0, 1, 2 (no NCLM run has used them). There is no tuning phase: the mix was chosen
before any run, from the reasoning above, and is not revised.

## Measurements (per run, from its `progress.jsonl`)

- **primary:** best held-out-documents bits/byte over all evals (the weights early stopping
  keeps)
- **guard:** held-out-chat bits/byte at that same eval
- reported, not judged: step of the best eval, stop reason, whether best < unigram (5.026)

## Criterion (stated before the runs)

**PASS** if all three hold:

1. `docs-heavy` beats `control` on primary for **≥ 2 of 3** seeds (paired by seed);
2. the median paired improvement (control − docs-heavy) is **≥ 0.10 bits/byte**;
3. guard: the median paired change in held-out chat is **not worse than +0.10 bits/byte**
   (docs-heavy must not buy document scores by losing conversation).

Otherwise **FAIL**. A FAIL is a result: it says the data mix is not what limits the core, which
points at capacity (a larger core) next.

## Caveat stated in advance

The held-out set is drawn from the documents pool, so shifting weight toward documents favours
the primary metric by construction; that is why criterion 3 exists and why a PASS here says
"closer to the held-out distribution helps", not "the core got generally better".

## How it runs

`python experiments/nclm_mix1/run.py` — six runs (2 arms × 3 seeds), three at a time, each with
its own checkpoint folder (`OSIRIS_ORGANISM_HOME`) and runs folder, `--no-rescore` so the live
chat's scores are never touched. The live core in `~/.osiris/nclm_organism` is not modified.
`python experiments/nclm_mix1/run.py --analyse` computes the verdict from the run folders and
writes `results.json` and `RESULT.md`.

## Amendment 1 (2026-10-01, before any result was examined)

The 3-hour per-run cap is replaced by a **12,000-step cap** (about twice the 6,600 steps the
reference run needed), with no wall-clock limit. Reason: on this shared machine, other work held
the load at 7–18 for hours; the first valid-procedure run (control s0) reached only 854 steps in
3 hours (~12.6 s/step vs ~0.6 s/step on 2026-09-30), so a time cap would have stopped each run at
an arbitrary, contention-dependent point and confounded the comparison. A step cap makes every
run independent of machine load (runs are seeded and deterministic). That run's score was not
looked at; it and the docs-heavy s0 run in progress were set aside unread
(`aborted_20261001c/`). Arms, seeds, mix, early-stopping rule, inputs and the PASS criterion are
unchanged. Runs that end on the step cap rather than early stopping are flagged in `RESULT.md`.
