# OSIRIS v4.5.0 — release notes (2026-10-08)

Google Cloud integration: Gemini through Vertex AI in your own project, keys in Secret Manager, CI on Cloud Build.
Also includes seven NCLM-1 workflow and verification commits made since v4.4.0 (listed below).

Verified on the release tree: the test suite on Python 3.11 and 3.12 in a local `git archive` tree with the home
directory hidden, and on Google Cloud Build (`cloudbuild.yaml`), which also installs the built wheel into a clean
environment and loads the console and the benchmark tasks. Live: Gemini answered through the new backend, and the
console loaded its keys from Secret Manager.

## New

- **`vertex-project` Gemini backend.** With `OSIRIS_GCP_PROJECT` set, every Gemini request goes to Vertex AI in that
  project, authenticated with an OAuth token from your gcloud login (no API key). `OSIRIS_GCP_LOCATION` (default
  `global`) and `OSIRIS_GCP_MODEL` (default `gemini-3.6-flash`) choose region and model; `/gemini --pro` uses
  `gemini-3.1-pro-preview`. The token is sent only in the Authorization header and never reaches the ledger. Without
  `OSIRIS_GCP_PROJECT` the key-based backends work as in v4.4.0.
- **Keys from Google Secret Manager** (opt-in, `OSIRIS_SECRETS_SOURCE=gcp`). At startup the console reads secrets
  labelled `osiris=env` and named `OSIRIS_<VAR>` with your gcloud login and exports them as `<VAR>`, unless `<VAR>` is
  already set. Read-only, 5-second timeout, never blocks startup; `/status` shows how many were loaded.
- **CI on Google Cloud Build.** `gcloud builds submit --config cloudbuild.yaml .` runs the suite on Python 3.11 and
  3.12 in parallel and a wheel-install smoke test; `.gcloudignore` keeps large legacy bundles out of the upload.

## Included NCLM-1 commits (since v4.4.0)

`2a1f8c0b` NCLM-1 manual collection workflow, analysis pipeline and monitoring scripts · `1b2951d6`, `1d959242`
adjudicated `verified_first_passing` loop with hermetic isolation · `38162bc7`, `54ed2b9a` research evidence receipts
and messages · `e5fae9be` bench results written to `~/.osiris/bench` · `193f77cc` NCLM analysis rows labelled by
ledger index, verdict deferred to the registered evaluator.

**Benchmark comparability:** these change `osiris_bench.py` and `verify_loop.py`, so the bench `runner_sha256` is now
`d18f87f4…` (v4.4.0: `f70c781f…`); the suite hash is unchanged (`09037df6…`). Bench results recorded under the old
runner hash, including BENCH-G1, are not comparable with new runs.

## Fixed

- `tests/test_verified_first_passing.py` (added since v4.4.0) imported `osiris_governance`, a separate repository, at
  module level, so on any install without it pytest aborted the whole suite at collection. It now skips without it;
  with osiris-governance `main` installed its 9 tests pass.
- `tests/test_sovereign_transformer.py::TestAutograd::test_div` drew unseeded inputs that could land near the pole of
  t/(t+1), where a float32 finite difference cannot meet the tolerance (it failed once on Cloud Build). Inputs now
  keep t + 1 ≥ 1.5.

## Claims register

NEGENTROPY_136 cites the erratum and re-analysis record 10.5281/zenodo.23213023; THETA_LOCK and RZ_CORRECTION name the
ibm_fez job behind dataset 22855102. No verdict changed.

## Release archive

The repository's `main` also holds the τ–Φ preregistration packet merged from pull request #3 (`theoretical/`,
`manifests/`, `metadata/`, `provenance/`). The release archive leaves those directories out: the packet is not
part of the tested console, and its targets (τ₀ = φ⁸, Φ_c = 0.7734, F_max = 1 − φ⁻⁸) are marked refuted or artifacts
in this release's claims register (`/legit`). They remain on GitHub.

## Known issues

BENCH-G1 (branch `prereg/bench-g1`) found no detectable difference in delivered tasks between Gemini and local
qwen2.5-coder:7b at n = 9; Gemini's first candidates passed the hidden tests on 6 of 9 tasks against 1 of 9, but most
were discarded because the candidate's own test failed. `start_nclm_workflow.sh` assumes the Termux path
`/root/osiris-cli`. Otherwise unchanged from v4.4.0.
