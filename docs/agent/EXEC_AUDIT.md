# Execution audit (Phase 0 re-verification and Phase 1 record)

Commit inspected: `97979bdf` (`main` merge), branch `feature/governed-skills`, worktree
`/home/enki/osiris-cli-wt/governed-skills`. The worktree was clean at the start (`git status --short`
printed nothing) and the imported `osiris_cli` resolved inside the worktree.

This file records what the spawn sites do at this commit, what Phase 1 added, and what was left
alone. It is a claim about the code until the tests in section 5 show it.

## 1. Re-verified findings (file:line at 97979bdf)

Line numbers are checked against the file. Where a line has moved, the new number is given with the
handoff's number in brackets.

**E1, `osiris_shell.py`** (legacy shell; live only with `OSIRIS_LEGACY_SHELL=1`, line 820):
- `_exec_shell` at 680; `subprocess.Popen(cmd, shell=True, ...)` at 686–687; `proc.wait(timeout=300)` at 695; `proc.kill()` at 701.
- `run <tool>` passthrough at 735–736; bare system-tool passthrough at 738–739 (`_exec_shell(text)`, the whole line).
- No confirm, grant or receipt anywhere on this path.

**E2, `osiris_cli/code_agent.py`:**
- `_SHELL_ONLY_TOKENS` at 46; `_DANGEROUS` at 47.
- `_run_command` at 340. `shlex.split` at 345; shell-token refusal at 350–352; `_DANGEROUS` refusal at 353–354; `_confine` at 355; digest at 358; y/N confirm at 359; grant at 362–364; timeout from substrate at 365; grant re-check at 371; `subprocess.run(argv, shell=False, ...)` at 374–375.
- No `env=` argument, so the child inherits the full environment. The file never references `AuditReceipt`.
- `_grep` at 316–328: `subprocess.run(argv, shell=False)` at 323, with no confirm.

**E3, `copilot-sdk-dnalang/src/dnalang_sdk/nclm/tools.py`:** the handoff's ranges are one line low for the definitions. Def lines now: `tool_llm` 110 [109], `tool_test` 262, `tool_profile` 274 [273], `tool_github_repos` 289 [288], `tool_consciousness` 453 [452], `tool_shell` 482 [481] with `shell=True` at 487, `tool_git` 504 [503] with the f-string at 507 and `shell=True` at 510. Hard-coded `"coherence": 0.87` at 443 and 473 (matches).

**E4, `copilot-sdk-dnalang/src/dnalang_sdk/sovereign/dev_tools.py`:** `_resolve_path` at 274, `_run_command` at 289, `shell=True` at 294 (all match).

**E5, `osiris_cli/orchestration/controller.py`:** the banned-call check at 51–63 flags `os.system`, `os.popen`, `os.execv`, `os.execve` and `os.spawnl`, and `shell=True` only on calls named `subprocess` or `sp`. Gaps confirmed by reading the code: `os.execvp`, `os.execl`, `os.spawnv`, and `from subprocess import run`.

**Reuse targets:** `osiris/substrate.py` `execution_timeout_s` 78, `interactive_timeout_s` 88 (both match). `osiris_cli/orchestration/schemas.py` `ExecutionGrant` 98 (`is_valid` 107), `AuditReceipt` 117 (both match). `osiris_cli/journal.py` `_canon` 35, `OperationalMerkleLedger` 44 (both match). `osiris_cli/paths.py` `results_dir` 49 (matches).

**Live spawn sites (paths from the inventory, not the handoff's short names):**
- `osiris_cli/osiris_repl.py`: `run <binary>` sensor probe at 183; `/update` git/pip at 1721 (`subprocess.run(cmd, check=True)`); `os.execvp` restart at 1733; `/update` command handler at 2283; `/apply` at 1981.
- `osiris_termux_console.py` (repo root): many sites, including `_propose_write` at 4300 and the test sandbox `Popen` at 4847.
- `osiris_cli/code_agent.py`: 323 (`_grep`) and 374 (`_run_command`).
- `osiris_cli/train.py`: 181, 367, 728 (`Popen` for a training job; no gate checked).
- `osiris_cli/github_bridge.py`: 39–139 (`gh` and git).
- `osiris_cli/sync_bridge.py`: 85–86 (adb).
- `osiris_cli/probes.py`: 43.
- `osiris_cli/gemini_gateway.py`: 203 (`gcloud auth print-access-token`).
- `osiris_bench.py` (repo root): 411 (`git -C`).

**Dead for this CLI:** `osiris_cli/grants.py` (no importers); `osiris_shadow/shadow_pipeline.py:67` (`os.system`, no importers); `copilot-sdk-dnalang/*`; the publish, release and experiment scripts.

**Not traced:** `osiris_agents.py`, and the same-named `client` and `executor` modules.

**`osiris_swarm_governance.py:358`** holds `os.system("rm -rf /")` as text in a self-test payload. The self-test was not run.

**`copilot-sdk-dnalang/src/dnalang_sdk/omega_engine.py:783–784`** runs `git add` and then `git commit` with `check=False`. It is SDK code and dead for this CLI, but it breaks the human-commits rule if reached.

## 2. Spawn-site inventory

Command: the one in the handoff, run from the worktree root. Result: **155 matching lines in 47 files**, matching the handoff. The raw list was saved to the session scratchpad (`inventory.txt`) and is not committed.

## 3. Baseline (before any Phase 1 file was added)

Command: `PYTHONDONTWRITEBYTECODE=1 /home/enki/osiris_env/bin/python -m pytest -o cache_dir=/tmp/osiris_pytest_cache tests/ -q -rfE --tb=line`

```
1385 passed, 3 skipped, 4 warnings in 177.23s (0:02:57)
```

The handoff expected `1384 passed, 4 skipped, 4 warnings in 171.73s`. The pass count is one higher and the skip count one lower. There were no failures, so no pre-existing failure node IDs to record. The 4 warnings are the `test_journal.py::test_concurrent_writers_never_fork_the_journal` fork `DeprecationWarning`, which is already on the open list.

## 4. What Phase 1 adds

| File | Purpose |
|---|---|
| `osiris_cli/exec_policy.py` | Normalization and classification (pure apart from `which`, `realpath` and reading the policy file). `CommandRequest`, `Classification`, `classify`, `load_policy`, `scrubbed_env`. |
| `osiris_cli/exec_kernel.py` | `run`, grants, output capture, process-group kill, the hash-chained receipt journal, and the `--explain` CLI. Re-exports the policy types. |
| `osiris_cli/policy/exec_policy.json` | The tier table, program lists, wrapper rules, secret patterns, env allow and deny lists, and output limits. Its SHA-256 is stamped on every classification and receipt. |
| `tests/test_exec_policy.py` | 167 fixture cases plus the policy-level tests (symlink, cwd escape, missing or malformed policy, env scrubbing). |
| `tests/test_exec_kernel.py` | Environment scrubbing in a child process, timeout kills a grandchild, cwd confinement, grant binding, DENY and declined-ASK never spawn, one receipt per decision, tamper detection, ask-once, streaming, truncation, `--explain`. |
| `tests/fixtures/exec_policy_cases.json` | 167 table-driven cases. Includes every bypass named in the handoff. |
| `docs/agent/EXEC_AUDIT.md` | This file. |

No existing call site was changed. `pyproject.toml` was not changed.

### Tiers and decisions

The tier table is in `exec_policy.json` and follows the handoff's section 6:
READ allowed for everyone. VERIFY allowed for humans, ask-once per session per program for agents. MUTATE asks humans and asks agents every call. NETWORK asks humans and denies agents. FORBIDDEN denies everyone, except that a human may be asked for `gcloud auth print-access-token`, whose output is never stored or echoed.

### Normalization (section 7)

Applied before any decision: argv validation (no NUL, no control or non-ASCII characters in `argv[0]`); shell operators and substitution markers are refused for every origin; a leading `NAME=value` is refused; the cwd must be a directory inside the root (symlinks resolved); any argument that resolves to a secret path is refused; ledger databases are refused. Then wrappers are unwrapped, `argv[0]` is resolved with `shutil.which` against the scrubbed PATH, and the program is classified by both its given basename and its realpath basename (the more restrictive verdict wins).

## 5. Test results

Full offline suite after Phase 1, same command as the baseline:

```
1588 passed, 3 skipped, 4 warnings in 176.04s (0:02:56)
```

That is the baseline's 1385 plus the 203 new tests (167 fixture cases, plus the policy and kernel tests). No failures.

The new tests alone (`tests/test_exec_policy.py tests/test_exec_kernel.py`): `203 passed`.

Lint and syntax: `ruff check --select E,F,W --ignore E501` on the four new Python files: `All checks passed!`. Python 3.9 syntax check (`ast.parse(..., feature_version=(3, 9))`) on the four new Python files: passed.

Bypass matrix: 167 of 167 fixture cases match their expected tier and decision. Every bypass named in the handoff's section 8 has a case.

Review fixes (2026-11-07, uncommitted):
- Rerun after the fixes, same offline command: `1589 passed, 3 skipped, 4 warnings in 177.79s (0:02:57)`. The new kernel test raises the new-test count to 204.
- **One receipt on every path.** The artifact setup in `run()` (the `_ArtifactWriter` mkdir and file open, plus the policy load) is now wrapped. A failure finishes with `ERROR` and a reason, writes exactly one receipt, and never starts the command. Test: `test_unwritable_artifacts_dir_ends_in_one_error_receipt_and_never_spawns` in `tests/test_exec_kernel.py` (artifacts dir under a regular file; asserts ERROR, no marker file, one receipt, `journal.verify()` passes).
- **Packaging.** `pyproject.toml` now has `osiris_cli = ["policy/*.json"]` under `[tool.setuptools.package-data]`. Checked offline: `pip wheel --no-deps --no-build-isolation --no-index` produced `osiris_cli-6.0.0-py3-none-any.whl`, which contains `osiris_cli/policy/exec_policy.json`, byte-identical to the source (sha256 prefix bc476084ef1b). The file is CRLF, so `git diff --check` flags the new line's `\r`; the other lines in the file are CRLF too and were left as they are.

## 6. Decisions and stricter choices

- **Receipts and artifacts live under `~/.osiris`** (`exec_journal.jsonl`, `runs/`), never `results/`. Tests pass temporary paths and never write to the real `~/.osiris`.
- **Receipt chain, not `OperationalMerkleLedger`.** The journal's `_canon` is not RFC 8785 for floats, and its concurrency test emits the fork warning. The kernel uses its own chain with `canon_version: "exec-canon-1"`. Bodies reject floats, so the canonical bytes are stable. Durations are stored as integer milliseconds.
- **`ExecutionGrant` is copied, not imported.** Importing `osiris_cli.orchestration.schemas` runs the orchestration package `__init__`, which pulls in the agent stack. The kernel's grant has the same digest rule (normalized argv, cwd, env key names, policy hash) and a 60 s TTL from the policy.
- **Commands run from the resolved absolute path, not the realpath.** A venv's `python` is a symlink; realpath would drop `pyvenv.cfg` discovery. The realpath is used only for classification.
- **Realpath names are judged too, with one exemption.** A symlink named `ls` pointing at `rm` is judged as `rm`. An unknown realpath name inside a system directory is ignored (e.g. `which` → `which.debianutils`); this is a stated trade-off.
- **`claude_code` is treated as an agent origin**, the stricter column. Unknown origins are denied.
- **`rm`, `rmdir`, `shred`, `dd`, `mkfs*`, `chmod -R` and `chown -R` are DENY for agents outright**, not "outside the scratch directory". The kernel has no scratch-directory concept; the stricter rule is the one written.
- **Git write operations are DENY for agents.** Unknown git subcommands are MUTATE (agents ASK). `git config` counts as a write. `git stash list|show` and `git branch` listings are READ.
- **Publish scripts and `--publish` are DENY for agents** and ASK for humans.
- **`gh` is NETWORK**, with read-only subcommands listed and everything else treated as a write (DENY for agents).
- **Confinement applies to every origin.** A cwd outside the root is DENY, including for humans.
- **Shell operators and `$(`, backticks, `<(`, `>(` are DENY for every origin**, as the handoff's section 7 says. This is stricter for humans than "ASK", and it also refuses `find -exec ... ;` for humans.
- **`find -exec` with a literal `;` is refused by the shell-token rule for every origin**, not by the find rule.
- **`env` as a launcher and bare `env` are DENY for every origin**; `printenv` is FORBIDDEN.
- **`sort -o` and `diff --output` are MUTATE**, because they write files.
- **Ask-once is keyed by program basename**, plus the module for `python -m <module>`. The approval set lives in the process and resets with `reset_session_approvals()`.
- **Grants expire after 60 s** and are re-verified immediately before `Popen`.
- **Timeouts** come from `osiris.substrate.interactive_timeout_s()` (the REPL horizon). A request may lower it; a zero, negative or NaN request falls back to the horizon.
- **Process-group kill** sends SIGTERM, waits the grace period (2 s, policy `kill_grace_s`), sends SIGKILL, and then checks `/proc` for any live member (zombies ignored). If a member survives, the receipt is ERROR.
- **Output** is written as JSON lines to `~/.osiris/runs/run-<id>/output.jsonl` and hashed. The model-facing view is the ANSI-stripped first 4,000 and last 4,000 characters with a truncation marker. A credential-bearing command writes no artifact and its views say so.
- **`CommandResult` has two fields beyond the handoff's list**: `decision` (the receipt's outcome, e.g. `ASK_APPROVED`) and `reasons`. Callers need the outcome, and the handoff's `provenance="COMPUTED"` is kept.
- **Human-origin "add a named key back" is not implemented.** The handoff allows it but does not require it; no Phase 1 caller needs it. Phase 2 can add it with a test.
- **`classify` is re-exported from `exec_kernel`** (the handoff lists it under the kernel API). It is defined in `exec_policy` so the policy module does not import the kernel.

## 7. Open items and blockers

- **Packaging (blocker for non-editable installs).** `osiris_cli/policy/` has no `__init__.py` and `pyproject.toml` does not list it as package data. The editable install used here works. A wheel will not contain `exec_policy.json`, and `load_policy()` then fails closed with `PolicyError`. Shipping it needs a `pyproject.toml` change, which the handoff says to ask about first. **Done** after the human's direct instruction ("suggest and execute"): `osiris_cli = ["policy/*.json"]` under `[tool.setuptools.package-data]`, beside the `bench_tasks` entry, wheel-checked (see section 5). A relayed approval from another session was not what authorized it.
- **Phase 2 items (no code change in Phase 1):**
  - `reset_session_approvals()` has no caller yet.
  - An ask-once approval covers a program with any arguments for the rest of the session.
  - `/code` must pass its own working directory as `root`.
  - The READ and VERIFY lists need a focused security review before model commands use the kernel.
  - `~/.osiris/runs` has no cleanup.
- `/update` is a REPL command, not an argv. It runs git and pip directly at `osiris_repl.py:1721` and restarts through `os.execvp` at 1733. Phase 2 must route it through the kernel as NETWORK (ASK for humans, DENY for models).
- The `OSIRIS_*` allowlist passes every `OSIRIS_` name that does not match the deny regex. A new secret-shaped `OSIRIS_*` variable must match the regex or it will reach the child.
- Secret-pattern hits in tracked files (names only, from the handoff; not opened in this phase): `world-record-quantum-supremacy.md.txt` (one AWS-access-key-ID-shaped line) and `tests/test_paste_learning.py` (one `sk-`-shaped line). The human checks these.
- E5 gaps (`os.execvp`, `os.execl`, `os.spawnv`, `from subprocess import run`) are not closed by this phase; they belong to Phase 2.
- SDK stubs (`tool_test`, `tool_profile`, `tool_github_repos`, `tool_llm`, the hard-coded coherence values, `tool_consciousness`) belong to Phase 3.
- `omega_engine.py:783–784` runs `git add` and `git commit` automatically (see section 1).
- The fork `DeprecationWarning` in `test_journal.py` (4 warnings in the baseline).
- Out of scope, reported only: the claims register lists `HERON_R2_STAG_XY8` as SUPPORTED, while the v5.3.1 record withdrew the "+2.28 pp on (14,15)" claim. Not checked in this phase; `claims.py` not edited.
- `git diff --check` checks tracked changes only. Phase 1 touched no tracked file, so it prints nothing; the new files are checked by ruff and the Python 3.9 syntax check instead.
