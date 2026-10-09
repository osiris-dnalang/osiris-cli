# OSIRIS v4.5.3 — release notes (2026-10-09)

A repair release: the exchange ledger's writer and checker, and the Gemini gateway after a merge regressed it. No
change to the core, its scorer, the speaking gate or the benchmark.

Verified on the release tree: the full test suite on Python 3.11 and 3.12 with the home directory hidden, and a
wheel-install smoke test (`scripts/ci_local.sh`): 761 passed, 2 skipped. Not run: GitHub Actions (billing) and Cloud
Build.

## Fixed — exchange ledger (`osiris_cli/living.py`, `osiris_cli/probes.py`, `osiris_cli/architecture.py`)

- **Two consoles could fork the hash chain.** Each new entry took its `prev` hash from the console's in-memory
  `stats.json` (`last_head`). On 2026-10-07 two consoles appended alternately and the chain forked seven times; the
  check then reported "exchange log BROKEN at entry 14". Every entry still hashed to its own content and every link
  named a real earlier entry. The writer now takes `prev` from the ledger file's last entry, read backwards in blocks
  under an exclusive lock, so concurrent writers keep one chain.
- **The check now tells forks from damage.** `verify_chain` still breaks on an altered entry or on a `prev` that names
  no entry (an inserted or removed one). A `prev` naming an earlier entry other than the one just before is reported
  under `forks`, and the console's architecture view says "no entry altered; N fork(s) from concurrent writers". The
  author's ledger now reads: 123 entries intact, forks at 14, 16, 20, 22, 23, 26, 27. No ledger was rewritten.

## Fixed — Gemini gateway (`osiris_cli/gemini_gateway.py`, `tests/test_gemini_gateway.py`)

- Merging the superseded PR #4 (2026-10-07 gateway) into `main` on 2026-10-09 left the module with a SyntaxError (two
  module docstrings spliced), removed the `BACKENDS` table (including the `vertex-project` backend) and duplicated
  tests, so every Gemini feature failed and pytest aborted at collection. Both files are restored to v4.5.2. The
  merge's other content is kept: `UPGRADE_v4.5.1_to_v4.5.2_CHECKLIST.md` and the revision of
  `theoretical/falsifiable_predictions.md` (the `theoretical/` folder stays outside the release archive).

## Repository

Branches whose commits are all in `main` were deleted on GitHub (the source of the stale PR #4 code). `facts` and the
S2 branch `feat/rqc-s0` remain.

## Known issues (unchanged from v4.5.1/v4.5.2)

- Importing `osiris_cli` reads Google Secret Manager at import when `OSIRIS_SECRETS_SOURCE=gcp` is set.
- The Gemini gateway does not return `finishReason`; thinking tokens count toward the output cap (use ≥ 1,024 for
  structured answers).
- The mentor's instructions say OSIRIS learns only from approved material, while typed exchanges train by default.
