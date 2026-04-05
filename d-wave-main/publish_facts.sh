#!/usr/bin/env bash
# Usage: bash publish_facts.sh
#        ./publish_facts.sh
set -euo pipefail

REPO_URL="https://github.com/dnalang-ip-theft-expose/d-wave.git"
BRANCH="facts"
DIR="$(pwd)"

if [ ! -d "$DIR/.git" ]; then
  echo "ERROR: This script must be run from the root of the d-wave repo."
  exit 1
fi

git fetch origin --prune

git checkout -B "$BRANCH"
mkdir -p docs

cat > docs/FACTS_TIMELINE.md <<'EOF'
# Facts-Only Timeline

Author: Devin Phillip Davis
Repository: dnalang-ip-theft-expose/d-wave
Purpose: Public, facts-only timeline assembled from local logs and public artifact metadata.

## Summary
- Owner / Author: Devin Phillip Davis (Agile Defense Systems, LLC / ENKI-420)
- Key immutable constants recorded in DNALang artifacts and project metadata:
  - `LAMBDA_PHI = 2.176435e-8` (s^-1)
  - `THETA_LOCK = 51.843`
  - `PHI_THRESHOLD = 0.7734`
  - `GAMMA_CRITICAL = 0.3`
  - `CHI_PC = 0.946`
- Core fact: these constants appear repeatedly in the author’s published artifacts and project metadata.
- Local OSIRIS sentinel logs show blocked outbound network activity on `2026-04-01` to two external IP addresses.

## Timeline

### 2025-12-08
- Multiple datasets and code packages published by Devin Phillip Davis (ENKI-420) on Zenodo and GitHub.
- Examples include the Omega-11 Wheeler-DeWitt package, Tau-Phase Anomaly evidence packages, and 6dCRSM theoretical materials.
- The published records include experiment job IDs and analysis scripts; metadata and files reference the constants above.

### 2025-12-10 → 2026-02-26
- Multiple software releases and dataset publications from the same author are recorded in public metadata.
- These artifacts include the DNA-Lang ecosystem, Cockpit AI Platform, and DNA::}{::lang validation packages.
- Project README and Zenodo metadata cite hardware validation and the same constants.

### 2026-02-26
- Public project metadata claims validation against IBM Quantum backends and lists job counts and shot counts.

### 2026-03-01
- Public annotations and metadata reference a "Quantum Forensic Audit" and explicitly note constants such as `51.843°` and `0.092`.

### 2026-03-31
- Evidence package records and supporting files were uploaded to public archives by the same author.

### 2026-04-01 13:11:52 → 13:12:09
- Local OSIRIS sentinel session observed repeated blocked outbound connections.
- Observed alert targets:
  - `38.146.195.203:443`
  - `16.148.51.142:443`
- The logs show repeated blocked connection attempts by local processes over a 17-second window.

## Included files in this branch
- `docs/FACTS_TIMELINE.md`
- `docs/EVIDENCE_SUMMARY.md`
- `docs/FULL_INTEGRATION_GUIDE.md`

## Verification notes
- Use the Zenodo API to fetch public metadata for cited DOIs.
- Use Git to snapshot the referenced repositories and compute SHA-256 hashes for key files.
- If IBM job IDs are present in datasets, use IBM/Qiskit job metadata to confirm timestamps.
EOF

cat > docs/EVIDENCE_SUMMARY.md <<'EOF'
# Evidence Summary (facts only)

Author: Devin Phillip Davis
Repository: dnalang-ip-theft-expose/d-wave
Purpose: Documentation of public artifacts, metadata references, and local forensic observations.

## Public references mentioned in source materials
- Example Zenodo DOIs mentioned in metadata and logs:
  - `10.5281/zenodo.17858632`
  - `10.5281/zenodo.17859207`
  - `10.5281/zenodo.17859845`
- Example IBM job IDs reported in project materials:
  - `job-d5h6rospe0pc73am1l00`
  - `job-d5h725kpe0pc73am1vfg`
- Public claim in project metadata: validation across IBM backends such as `ibm_fez` and `ibm_torino` with job counts and shot counts.

## Key constants and hardware values
- `LAMBDA_PHI = 2.176435e-8` (s^-1)
- `THETA_LOCK = 51.843°`
- `PHI_THRESHOLD = 0.7734`
- `GAMMA_CRITICAL = 0.3`
- `CHI_PC = 0.946`

## Observed OSIRIS sentinel logs
These log excerpts were supplied by the author and are reproduced here verbatim in a compact format.
- `[04/01/2026 13:11:52] ALERT: System.Diagnostics.Process (BASupSrvc) ... attempting exfiltration ... 38.146.195.203 ... TERMINATED & BLOCKED`
- `[04/01/2026 13:11:53] ALERT: System.Diagnostics.Process (NetworkManagement) ... attempting exfiltration ... 16.148.51.142 ... TERMINATED & BLOCKED`
- `[04/01/2026 13:11:56] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:11:56] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:11:58] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:11:58] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:01] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:01] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:03] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:03] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:06] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:06] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:09] ALERT: System.Diagnostics.Process (BASupSrvc) ... TERMINATED & BLOCKED`
- `[04/01/2026 13:12:09] ALERT: System.Diagnostics.Process (NetworkManagement) ... TERMINATED & BLOCKED`

## Observed network connections
These connection records were captured during the same OSIRIS session.
- `10.1.2.52:55361 → 38.146.195.203:443` (Established)
- `10.1.2.52:52372 → 16.148.51.42:443` (Established)

## Public comparison references
- Andrew D. King (D-Wave) arXiv author page: http://arxiv.org/a/king_a_1
- Public GitHub reference: quantum-advantage/copilot-sdk-dnalang
- Public Zenodo records for Devin Phillip Davis: search by creator name and DOI.

## Suggested factual verification steps
- Use the Zenodo API to fetch metadata for the DOIs listed above and compute SHA-256 for downloaded records.
- Use Git to snapshot the cited repos and compute SHA-256 for key files.
- If IBM job IDs are available, use IBM/Qiskit APIs to verify job metadata and timestamps.
- Archive the OSIRIS sentinel log and any exported CSV evidence into a timestamped zip and compute SHA-256.
EOF

cat > docs/FULL_INTEGRATION_GUIDE.md <<'EOF'
# Full Integration Guide

This document records the integration of the DNALang SDK and OSIRIS platform into a single facts-oriented repository structure.

## Included capabilities
- DNALang NCLM integration
- Gemini model support
- Intent deduction and semantic planning
- Quantum circuit execution and verification
- Local OSIRIS CLI packaging

## Installation notes
- Create and activate a Python virtual environment
- Install the DNALang SDK and optional Gemini support
- Set API keys via environment variables for Gemini or IBM Quantum if needed

## Notes
This file is added to the facts branch as a companion integration reference.
EOF

cat > /tmp/publish_facts_commit.log <<'EOF'
Published facts-only documentation and prepared branch for push.
EOF

git add docs/FACTS_TIMELINE.md docs/EVIDENCE_SUMMARY.md docs/FULL_INTEGRATION_GUIDE.md

git -c commit.gpgsign=false -c user.name='Devin Phillip Davis' -c user.email='devin.dnalang@outlook.com' commit -m 'Add facts-only timeline, evidence summary, and full integration guide'

git push -u origin "$BRANCH"

echo "DONE: docs/FACTS_TIMELINE.md and docs/EVIDENCE_SUMMARY.md committed and pushed to branch '$BRANCH'."
