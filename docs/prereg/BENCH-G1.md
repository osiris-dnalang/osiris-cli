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
(not yet run)
