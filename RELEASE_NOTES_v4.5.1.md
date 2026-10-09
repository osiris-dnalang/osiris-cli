# OSIRIS v4.5.1 — release notes (2026-10-08)

A correction release: the claims register's τ-phase matcher, and five console behaviours that misreported what OSIRIS
did with long or pasted input. No new capability; no change to the speaking gate, the held-out schedule or the
benchmark (suite and runner hashes are as in v4.5.0).

Verified on the release tree: the full test suite on Python 3.11 and 3.12 in a local tree with the home directory
hidden (`scripts/ci_local.sh`), and a wheel-install smoke test. GitHub Actions is unavailable (billing) and Cloud Build
was not run for this release.

## Fixed — claims register (`osiris_cli/claims.py`)

- **TAU_PHASE missed "46.0 µs".** The duration pattern accepted 46 and 46.9… but not 46.0 (the micro sign was never
  the problem: µ and μ are already equivalent under case-insensitive matching). It also matched "4.46 µs",
  "46 users", "46 microphones" and any plain 46 µs delay. It now accepts 46, 46.0… and 46.9… microseconds, not inside
  a larger number, with a real microsecond unit, near a τ/revival/anomaly/oscillation/period/phase/φ word.
- **TAU_PHASE finding wording.** The τ-phase is (unix timestamp mod 46 µs)/46 µs using the job's execution-start time,
  falling back to its creation time — as `calculate_tau_phase` computes it (the entry said "job-creation" only). The
  "580 jobs → 103 runs" figure is attributed to the 2026-09-20 written assessment, and the code file is cited as
  evidence. Verdict unchanged: ARTIFACT.
- `match()` documents that a match identifies a reference to a claim, not an endorsement: criticism matches too.

## Fixed — console (`osiris_cli/living.py`, `osiris_cli/osiris_repl.py`)

- **A paste made while OSIRIS was answering could be trained on.** Messages held during a reply were dispatched with
  the *previous* prompt's input type, so a pasted document could be classed as typed — and typed exchanges train the
  core. Held messages now carry their own transport. *Exchanges recorded before v4.5.1 with `learnable: true` whose
  text was pasted during a reply may have been trained on; the exchange ledger shows which.*
- **"Learning from this" said more than happened.** It appeared on held-out exchanges (scored, never trained) and with
  no core loaded. The footer now states the actual case: trained on, held out, no core loaded, or not learned and why.
- **The excerpt footer gave the whole message's length as the excerpt's.** "An excerpt of 13,024 characters was sent"
  meant a 13,024-character message of which the model read the first 4,000 and the last 2,000. The footer now says
  exactly that, and that the rest was not read.
- **A long paste with no request was restated by a model from an excerpt.** It is now acknowledged by code: its
  sections are listed, nothing is reviewed, summarised, adopted or learned, and OSIRIS asks what to do. A follow-up
  request reaches the model with the document.
- **Cut-off replies looked complete.** A reply stopped at the 700-token limit (Ollama `done_reason: length`) or ending
  inside an open code block is marked incomplete and not learned. Timings now come from the model's own counters
  (load, prompt read, generation).
- **Model-made status labels.** Labels in a reply that nothing sent to the model contains (for example
  `NUMERICAL_OVERLAP = OBSERVED` for a "potential overlap") are flagged as the model's own. This is a flag, not a fact
  check.
- **Bracketed paste.** A paste still arriving when a reply ends is read to its end marker (bounded: 1 s quiet, 15 s
  total). A paste tail arriving alone is held as a paste, never shown as "you were typing '\x1b[201~'". A held
  multi-line paste goes to the conversation, never to the command router (where a first word such as `/apply` ran a
  command and dropped the rest).

Tests: `tests/test_console_paste.py` (27, synthetic fixtures only) and 24 new matcher cases in `tests/test_claims.py`.

## Known issues (not fixed in this release)

- **Importing `osiris_cli` reads Google Secret Manager** when `OSIRIS_SECRETS_SOURCE=gcp` is set: the console module,
  imported by the package, loads secrets at import time. Anything that imports the package — including a test run
  that does not hide the home directory — makes that read-only request. `scripts/ci_local.sh` hides the home
  directory and is unaffected.
- **Gemini output cap includes thinking tokens.** With `gemini-3.6-flash`, a 256-token cap spent 242 tokens thinking
  and returned a JSON answer cut mid-word; `gemini_gateway.generate()` records `finishReason` in its ledger but does
  not return it, so callers cannot see the truncation. A 1,024-token cap answered correctly. Use caps of ≥ 1,024 for
  structured answers until the gateway reports truncation.
- The mentor's system prompt says OSIRIS "learns only from eligible material you explicitly approve", while typed
  exchanges train the core automatically (pasted ones do not). The wording and the default are under review.
