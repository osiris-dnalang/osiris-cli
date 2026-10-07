# OSIRIS v4.4.0 — release notes (2026-10-07)

Every request OSIRIS makes to Google's Gemini models now goes through one governed gateway.

Verified in a `git archive` tree with core dependencies only, the home directory hidden and no
reachable Ollama: 604 passed, 1 skipped on Python 3.11 and 3.12. Live: both keys in the author's
`~/.env` answered through the gateway on Vertex AI (`gemini-2.5-flash`), and `/gemini` and
`/status` ran in the installed console.

## New

- **`osiris_cli/gemini_gateway.py`**, the only code that calls Google's model APIs (a test
  fails if any other module does). For every request it:
  - picks the backend by key type: `AIza…` keys use the Gemini Developer API; `AQ.…`
    (Vertex express / agent-platform) keys use Vertex AI, which is the only one that accepts them;
  - redacts every outbound text part: any value held in `~/.env`, and secret-shaped strings
    (Google, GitHub, AWS and `sk-` keys, private keys, database URLs with passwords);
  - enforces a persistent token budget (`OSIRIS_GEMINI_TOKEN_BUDGET`, default 2,000,000),
    refusing a call that would exceed it;
  - writes a hash-chained ledger row (`~/.osiris/gemini_gateway_ledger.jsonl`) before the call
    and after it, with hashes and counts only, never prompt or response text.
- **`/gemini [--dry] <question>`** asks Gemini directly; the answer is labelled advisory.
  `--dry` shows what would be sent and the redactions, and sends nothing.
- **`/status`** shows the Gemini backend, model, budget used and ledger state.

## Changed

- `gemini_bridge` (the Synthesizer, `/lab` discovery, vision) sends through the gateway. Its
  functions and its `GeminiUnavailable` fall back to local Ollama are unchanged.
- Model variables: `GEMINI_MODEL` for the Developer API, `GEMINI_VERTEX_MODEL` for Vertex
  (default `gemini-2.5-flash`); `OSIRIS_GEMINI_BACKEND=developer|vertex` forces one.

## Fixed

- An `AQ.`-type key in `GEMINI_API_KEY` was sent to the Gemini Developer API, which rejects it
  (HTTP 401), so the Synthesizer silently fell back to Ollama. It is now used on Vertex AI.
- An installed (wheel) console did not read `~/.env`, because it looked for `.env` beside
  `site-packages`; it now also reads `~/.env`. Variables already set in the shell still win, and
  `export KEY=…` lines are accepted.

## Known issues

Unchanged from v4.3.2. Whether Gemini-written candidates pass the sandbox more often than the
local mentor's is not yet measured; a pre-registered benchmark round is planned.
