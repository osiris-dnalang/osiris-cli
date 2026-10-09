# OSIRIS v4.3.2 — release notes (2026-10-07)

A fix release. In v4.3.1 several console menu entries ended the session with a traceback,
and `/bench` failed after a pip install.

Verified in a `git archive` tree with core dependencies only, the home directory hidden and
no reachable Ollama: 593 passed, 1 skipped on Python 3.11 and 3.12. A wheel built from the
tree and installed into a fresh environment imports the console and loads all 9 benchmark tasks.

## Fixed

- **Menu letters B, C, F (and `/runs`, `/apply`, `/discard`, `/sprint`, `/nclm`, `/facts`)
  crashed the REPL.** The REPL kept its own copy of the console's command table and it had
  drifted: nine handlers it called were missing or took different arguments, and `/gaps`
  opened a new draft instead of listing drafts. The REPL now routes through the console's
  `run_command()`; `tests/test_repl_dispatch.py` checks that every console call in the REPL
  exists and binds. (This is the author's 2026-10-03/04 working-tree fix, which had not been
  committed; it also adds the architecture panel and paste learning.)
- **A failing command ended the session.** A command that raises now reports which command
  failed, keeps the traceback in `~/.osiris/logs/repl_errors.log`, and returns to the prompt.
- **`/bench` and `/check` failed after `pip install`** (`FileNotFoundError: .../bench_tasks`).
  The benchmark tasks now ship in the wheel. They ship without an `__init__.py`, and
  `osiris_bench.py` is unchanged, so the benchmark's suite and runner hashes are identical to
  v4.3.1 (`09037df6…`, `f70c781f…`) and earlier results stay comparable.
- **`/status` called the historical CRSM constants "invariants"** (and gave Λ_Φ a unit of kg).
  It now shows θ_lock, Λ_Φ and F_max as historical parameters with their claims-register
  verdicts (REFUTED, NOT_MEASURED).

## Tests and CI

- Tests point `OLLAMA_HOST` at an address nothing listens on (`OSIRIS_TEST_LIVE_OLLAMA=1` opts
  in): a busy local Ollama made `tests/test_integration.py` hang. `test_architecture` uses the
  pinned dnalang-core ledger when dnalang-core is absent.
- The CI workflow builds the wheel, installs it in a clean environment and imports the console
  from it. `scripts/ci_local.sh` runs the suite with the home directory hidden plus the same
  wheel check, for when GitHub Actions is unavailable (it still is; all verification is local).

## Upgrading

`/update` installs from GitHub `main`; from this release on it delivers the fixed console.
An editable install: `git pull && pip install -e .` in your checkout.

## Known issues

Unchanged from v4.3.1: legacy code outside the console and `osiris_cli` still contains old
absolute paths; the CI lint selection reports pre-existing findings; Python 3.9 and 3.10 were
not tested locally.
