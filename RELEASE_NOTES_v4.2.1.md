# OSIRIS v4.2.1 — release notes (2026-09-30)

A correction release. **v4.2.0 did not pass its tests in a clean environment**: it passed on
the author's machine only because fixes there had never been committed. v4.2.1 commits them
and was verified in a `git archive` tree with core dependencies only and no Ollama:
472 passed on Python 3.11 and 3.12 (`scripts/local_ci.py`).

## Fixed

- Test collection in clean installs: `human_eval` (not a dependency) was imported at module
  level by `osiris_benchmark`; `dnalang_sdk` (not a dependency) by `osiris_agents`.
- `osiris_health.py` IndentationError; `QuantumCircuit` annotations evaluated without Qiskit
  (`qiskit_adapter`, `osiris_auto_discovery`); `RuntimeConfig(allow_mock=...)`.
- `POLICY.md`, protected by the status-recovery test, is now in the repository.
- `osiris_cli.py` is a shim to `osiris_cli.osiris_repl` (the old module was shadowed by the
  `osiris_cli/` package).

## New

- `scripts/local_ci.py`: the checks of `.github/workflows/ci.yml` run locally on the committed
  tree (GitHub Actions is unavailable while the account is billing-locked); each run is
  hash-chained in `~/.osiris/ci/runs.jsonl` and recorded in a dedicated Neon project
  (`osiris_ci_runs`) when `NEON_DATABASE_URL` is set.

## Known issues

- Lint over CI's paths: 323 findings (pre-existing; mostly unused imports, many of them
  deliberate optional-dependency probes). Not fixed by autofix on purpose.

Everything else is as in `RELEASE_NOTES_v4.2.0.md`.
