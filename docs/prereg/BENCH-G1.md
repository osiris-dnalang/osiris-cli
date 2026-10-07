# BENCH-G1 — does Gemini write better Synthesizer candidates than the local mentor?

Pre-registered 2026-10-07, before either arm is run. Results are recorded below this line in a
later commit, whichever way they fall; nothing here is changed after the first arm starts.

## Question
On OSIRIS's frozen benchmark, are candidates written by Gemini (Vertex AI `gemini-2.5-flash`,
reached through `osiris_cli.gemini_gateway`, exactly as the console's Synthesizer calls it) delivered
— accepted by the hidden acceptance tests — for more tasks than candidates written by the local
mentor `qwen2.5-coder:7b` (Ollama)?

## Fixed conditions
- Code: osiris-cli v4.4.0 (commit db371b66), `osiris_bench.py` unmodified.
- Suite: all 9 tasks, `suite_sha256` 09037df636145b1e…; runner `runner_sha256` f70c781f199f6a1c….
  A run whose recorded hashes differ is invalid for this comparison.
- k = 3 candidates per task, the bench's own verify loop; same prompts by construction.
- Arm G: `osiris_bench.py --backend gemini --k 3`. Arm Q: `osiris_bench.py --backend ollama
  --model qwen2.5-coder:7b --k 3`. One run per arm, on this machine, results in ~/.osiris/bench.
- Arm G first; arm Q only when no other process is using Ollama. Model sampling settings are each
  backend's defaults as OSIRIS uses them; nothing is tuned.
- A backend error or timeout on a task counts as not delivered for that task. Arm G is capped at
  400,000 Gemini tokens for this round; if the cap stops it, the round is reported incomplete.

## Primary outcome and decision rule
Per task, `delivered` (bench ledger field). Paired by task, let G+ = tasks delivered by G and not Q,
Q+ = delivered by Q and not G. Exact one-sided sign test on the discordant tasks, α = 0.05:
- **G better** if G+ ≥ Q+ + 3 and the sign test gives p < 0.05 (with 9 tasks this needs at least 5
  discordant tasks all favouring G, or 6 of 7, …);
- **Q better** by the mirror rule;
- otherwise **no detectable difference at this size** (n = 9 tasks is small; this is a pilot).

## Secondary (reported, not judged)
`pass_at_1` and `oracle_at_k` counts, `false_confidence` totals, wall-clock seconds per arm,
Gemini tokens used (gateway ledger), per-task outcomes.

## Results

### Protocol deviation (recorded before any valid result was read)
Run `bench-20261007T160505Z-dbefc4` (backend gemini, k=3, 2026-10-07T16:05:05Z) was launched by
mistake from v4.3.2 code, which predates the gateway: every Gemini request was refused (HTTP 401,
AQ-type key sent to the Developer API) and all 9 tasks recorded as not delivered. It is invalid for
this comparison (wrong code; the bench ledger records `commit: null`, so it is identified by run id
and its 401 errors). It used no Gemini tokens. It stays in the append-only bench ledger.

### Arm G — `bench-20261007T160545Z-6656f3` (v4.4.0, Vertex gemini-2.5-flash, k=3), complete
suite 09037df6…, runner f70c781f… (as registered).

| task | delivered | pass@1 | oracle@k | false confidence | seconds |
|---|---|---|---|---|---|
| backend_breaker | yes | yes | yes | 0 | 34 |
| backlog | no | no | no | 0 | 33 |
| claims | no | yes | yes | 0 | 213 |
| gaps | no | no | no | 0 | 314 |
| genome_ledger | no | no | no | 1 | 320 |
| nclm_corpus | no | yes | yes | 0 | 270 |
| nclm_eval | yes | yes | yes | 0 | 130 |
| repl_commands | no | yes | yes | 0 | 350 |
| stub_detector | no | yes | yes | 0 | 261 |
| **total** | **2 / 9** | **6 / 9** | **6 / 9** | **1** | **1,924** |

Gemini tokens used by arm G: 103,415 (gateway budget file, 13,023 → 116,438).

### Arm Q
(not yet run: Ollama is in use by another benchmark process)
