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
