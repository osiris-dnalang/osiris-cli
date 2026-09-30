# OSIRIS v4.2.0 — release notes (2026-09-30)

## What this release is

The first release in which `osiris` is a conversation with a living language model: plain text
talks to OSIRIS; its own core (`osiris.nclm`) learns from every exchange and speaks in its own
voice only after passing a held-out gate; until then a local Ollama model speaks for it,
labelled. What this release does **not** claim: the core has not passed its gate, and the
pre-registered learning test (NCLM-1) has not been run.

## New

- **Conversation loop** (`osiris_cli/living.py`): mentor/core voices, held-out discipline
  (every 5th exchange never trained on), speaking gate (30 held-out exchanges at ≤ 2.0 bpb and
  below unigram), hash-chained exchange log.
- **Grounding** (`osiris_cli/knowledge.py`): a stable brief (pre-registered scorecard verdicts,
  projects) in the system prompt, so Ollama can reuse its cached prefix; per-message BM25
  retrieval over configured notes with file citations in the reply footer.
- **Read-only checks** (`osiris_cli/probes.py`): code-selected, never model-selected — trainer
  status, git history across the research repos, exchange-ledger recomputation, system load,
  named files under `$HOME` (credential files refused). `/check` runs them directly.
- **Memory across sessions**: the last exchanges are recalled from the ledger verbatim;
  `/remember` and `/forget` manage explicit facts.
- **Batch training** (`osiris train`): corpus + chat lessons + grounded distillation;
  distillation pauses while a chat is active; packaging metadata (`*.egg-info`) is excluded
  from the corpus.
- **Console UX**: keys typed while a reply streams are captured instead of echoed into it and
  sent next, labelled (fixes answers appearing one turn late); a thinking indicator names CPU
  contention; replies show their latency.

## Fixed

- `OrganismConverter.translate(..., return_report=True)` ignored the flag for
  sovereign→sovereign and returned a bare circuit.
- Syntax that only parses on Python 3.12 (backslashes inside f-strings) in
  `osiris_cli/osiris_repl.py` and `nclm/enhanced_config.py`; a `X | tuple[...]` annotation
  evaluated at import on 3.9.
- `osiris_publication_zenodo.py` did not import on any Python (orphaned lines of a removed
  placeholder-DOI mock).
- `nclm/enhanced_core.py` referenced undefined names; the methods that depended on code that
  was never written now raise `NotImplementedError` with that explanation.
- Autograd `matmul` backward now un-broadcasts gradients to operand shape.
- Test corrections: finite-difference gradient checks used float32 with eps = 1e-4 (rounding
  error ≈ 3e-3 > rtol 1e-3 against exact analytic gradients); the byte-dataset test located
  windows by their first byte, which is ambiguous; the runtime capability test expected
  "verified" where no verification evidence exists (the conservative label stands).

## Packaging

- The phone console (`osiris_termux_console.py` and its 17 modules) is now committed and
  packaged; a clean wheel install loads the console and the core.
- Sibling research repos moved from `file:///home/…` dependencies to the optional
  `[research]` extra (git URLs).
- `.venv/`, `venv312/` and `osiris_cli.egg-info/` are no longer tracked; `.gitignore` merge
  conflict resolved.
- The banner no longer presents refuted constants as physical invariants.
- README rewritten to describe what works and what is measured; the previous README is kept at
  `docs/README_v4_legacy.md`. `.zenodo.json` and `CITATION.cff` rewritten to match.

## Known issues

- CI lint (`ruff --select E,F,W` over `osiris/ nclm/ qbyte_system/ …`) reports ~320
  pre-existing findings, mostly unused imports — many are deliberate optional-dependency
  probes, so they need a manual pass, not an autofix.
- The repository still carries earlier-phase material (nested project copies, CRSM-era
  documents). See the README section "What this repository also contains".
