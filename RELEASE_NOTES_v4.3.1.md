# OSIRIS v4.3.1 — release notes (2026-10-07)

A packaging and repository-hygiene release. **v4.3.0 could not run its console from a clean
install**: the console imported ten modules (and ran five scripts) that existed only in the
author's working copy, so a fresh checkout reported "bench evidence unreadable
(ModuleNotFoundError)". The entry point also put one machine's home directory at the front of
`sys.path`, which hid the gap locally and let stale copies shadow the installed package.

Verified in a `git archive` tree with core dependencies only, no Ollama, and the home directory
hidden: 529 passed, 1 skipped on Python 3.11 and 3.12. A wheel built from the tree and
installed into a fresh environment imports every console module from the installed package.

## Fixed

- Packaging: `capabilities`, `dd_sim`, `discover`, `dna_lang`, `evolve`, `osiris_bench`,
  `paste_digest`, `prompt_strategies`, `protege`, `trials` (imported by the console),
  `algorithmic_dd_generator`, `bench_trial`, `nclm_aer_evaluator`, `pretrain_nclm`,
  `verify_ledger` (run by the console as scripts) and `osiris_local_qvm` (re-exported by
  `osiris.quantum`) are now in the repository and in `py-modules`. `bench_tasks/` (the benchmark
  task definitions) is in the repository.
- No hard-coded home-directory paths: `osiris_cli/paths.py` appends — never prepends — the
  source checkout, `OSIRIS_EXTRA_PATHS` entries and sibling checkouts that exist under the home
  directory (`~/bridge`, `~/dnalang-core`, …), so installed packages keep precedence. Results go
  under the checkout's `results/`, or `~/.osiris/results/` outside a checkout. Used by the
  REPL, `osiris_unified_livlm` and `osiris_comparative_benchmark`.
- dnalang-core's `ledger.py` is found from `$OSIRIS_DNALANG_LEDGER`, the existing source-checkout
  locations, or an installed `dnalang` package (`genome_ledger`, `osiris_bench`).
- The genome-ledger supersession tests run everywhere (a pinned copy of dnalang-core v0.2.0's
  `ledger.py` is a test fixture) instead of being skipped without dnalang-core.

## New

- `tests/test_packaging.py`: every repository module the console or `osiris_cli` imports, and
  every script the console runs by path, must be listed in `py-modules`; no home-directory
  literals in that code.

## Repository hygiene

- Private conversation transcripts, interaction history, outreach drafts containing third-party
  contact details and captured shell output were removed from the repository tree;
  `SETUP_CREDENTIALS.md` uses placeholders; `.osiris_history.jsonl` is ignored. The files of the
  v4.2.1 and v4.3.0 Zenodo records are restricted for this reason; their metadata and DOIs remain
  public.

## Also since v4.3.0

- Claims register: an untested brief registered as UNTESTED; the core-learning entry carries the
  NCLM-GATE-PILOT-1 result. The core still has not passed its speaking gate.
- Genome ledger: the verifier honours an attested supersession of an earlier entry.

## Known issues

- Wheel installs do not include `bench_tasks/`; `/bench` task listing needs a source checkout.
- Six phone-layout test files for the console modules are not part of this release: they
  assume the Termux `bin/` layout (a launcher script beside the modules). Run against this
  release in isolation, five of them pass 28 of 33 cases (the failures drive that launcher);
  the sixth needs example data that is not in the repository.
- Legacy code outside the console and `osiris_cli` still contains old absolute paths, and the
  CI lint selection reports 323 pre-existing findings. GitHub Actions was unavailable; all
  verification is local.
