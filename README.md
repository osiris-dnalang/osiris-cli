# OSIRIS

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23063462.svg)](https://doi.org/10.5281/zenodo.23063462)

A local-first console for testing whether a small language model can learn from
conversation. OSIRIS's own model (`osiris.nclm`, the *core*) trains on every exchange and on your
documents, and may answer in its own voice only after it passes a held-out test; it has not
passed yet. Until then a local Ollama model speaks *for* it, labelled as such, and the core
trains on what it says. Models propose; deterministic code decides, measures and records.

Author: Devin Phillip Davis (Agile Defense Systems LLC). License: OSIRIS Source-Available
Dual License v1.0 (see `LICENSE`) — source-available, not open source.

## What works today (v4.3.1)

| Part | What it does | Where |
|---|---|---|
| Conversation | Plain text talks to OSIRIS. Replies stream; keys typed during a reply are held and sent next, never mixed into the answer. | `osiris_cli/living.py` |
| Grounding | A stable brief of what is on record (pre-registered results, projects) plus per-message retrieval over your notes; answers name the file they used. | `osiris_cli/knowledge.py` |
| Read-only checks | Code, not the model, runs checks before answering — training status, git history, exchange-ledger integrity, system load, a file you name (credential files are never read). `/check` shows them directly. | `osiris_cli/probes.py` |
| Memory | Recent exchanges carry into the next session from the ledger (no model summarises them); `/remember` and `/forget` keep explicit facts. | `osiris_cli/living.py` |
| Speaking gate | The core answers in its own voice only after 30 held-out exchanges at ≤ 2.0 bits/byte and below a unigram baseline. Every 5th exchange is held out and never trained on. | `osiris_cli/living.py` |
| Batch training | `osiris train --hours 8 --detach` trains the core on a configured corpus, chat lessons and grounded distillation; distillation pauses while you chat. | `osiris_cli/train.py` |
| Provenance | Every exchange is appended to a SHA-256 hash chain (`~/.osiris/living/exchanges.jsonl`); `/check ledger` recomputes it. | `osiris_cli/probes.py` |

### Current measured state

The core has **not** earned its voice. After the first training runs it scored 7.60 bits/byte
on held-out documents against 5.03 for a unigram baseline — worse than the baseline. That is
the starting point the gate exists to measure honestly; the pre-registered learning test
(NCLM-1: gain over a memory-only baseline seven days after a restart) has not been run.

## Install and run

```bash
pip install -e .                 # core; Python 3.9+
pip install -e ".[research]"     # optional: dnalang, organism_sim, bridge sibling repos
ollama pull qwen2.5:7b           # a local mentor voice (qwen2.5:1.5b on small machines)
osiris                           # start talking
```

In the console: `/osiris` (core status and gate) · `/check [trainer|git|ledger|system]` ·
`/remember <fact>` · `/forget <words>` · `/train [start H|stop]` · `/mentor [model]` ·
`/self <text>` (the core's raw voice, ungated) · `/help` for everything else.

Optional sibling checkouts (`~/dnalang-core`, `~/bridge`, `~/organism_sim`, …) are found
automatically; other locations can be added with `OSIRIS_EXTRA_PATHS` (path-separated), and
dnalang-core's ledger with `OSIRIS_DNALANG_LEDGER`. Installed packages always take precedence.

## Related, separately published work

- **organism_sim / dnalang-core / bridge** — pre-registered ALife and dynamical-decoupling
  experiments with a checked-in scorecard (PASS and FAIL recorded alike).
  Zenodo [10.5281/zenodo.22862567](https://doi.org/10.5281/zenodo.22862567).
- **Staggered dynamical decoupling on ibm_marrakesh** — a pre-registered run in which
  bipartite-staggered DD kept P(+) = 0.900 at 32 µs versus 0.834 for simultaneous DD and 0.595
  idle (non-overlapping 95 % CIs; job `dau0q3qhcrkc73durtgg`; data in
  `experiments/osiris_advantage_marrakesh/`; Zenodo
  [10.5281/zenodo.23045494](https://doi.org/10.5281/zenodo.23045494)). This is a
  crosstalk-suppression result for a known technique family, not a quantum-advantage claim.

## What this repository also contains

The `osiris/` package and many root-level `osiris_*.py` modules come from earlier phases of the
project (the CRSM framework, qByte simulator, agent constellation, dna::}{::lang compiler v1).
Several of their headline constants and metrics — the τ-phase anomaly, θ_lock = 51.843°, the
CCCE "consciousness" metrics — were tested on hardware by the author and **refuted**; the code
is kept for provenance and still runs, but those quantities are not presented as physics.
The previous README is preserved at `docs/README_v4_legacy.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/
```
