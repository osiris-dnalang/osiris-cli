# OSIRIS Quantum Hardware Research Campaign: Unified Evidence Package v2.0
**Governing Standard:** SYS-021 (Zero Self-Supplied Authorization) / Gate 0 Conformance  
**Lead Investigator:** Devin Phillip Davis / Enki  
**Target Processors:** IBM Quantum Heron r2 (`ibm_fez`) and Heron r1 (`ibm_marrakesh`)  
**Package Generation Date:** November 7, 2026  
**Ledger Anchor:** Blocks #1 through #46 (Cryptographic SHA-256 Hash Chain)  

---

## 1. Executive Summary & Hardware Milestone Determination

This unified archival evidence package v2.0 consolidates physical quantum telemetry, compiled ISA circuits, cryptographic grants, acquisition receipts, and dispassionate forensic incident records across four major hardware campaigns on IBM Quantum superconducting quantum processors:

| Campaign Identifier | Physical QPU | Qubit Volume | Physical Shots | Primary Validated Observable | Milestone Determination | Status |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **OSIRIS-HP-001** | `ibm_fez` (Heron r2) | 6 transmons | 49,152 | Subspace Population: **80.20 +/- 0.62%** | Restricted 1-qubit subspace reconstruction verified | **VERIFIED** |
| **OSIRIS-HP-002** | `ibm_fez` (Heron r2) | 6 transmons | 73,728 | Entanglement Fidelity: **79.49 +/- 0.14%** | Certified Restricted Recovery (Z > 200 sigma, W = -0.2949 < 0) with barrier-verified positive control (91.94%) | **CERTIFIED** |
| **7-Edge Stagger DD** | `ibm_marrakesh` (Heron r1) | 14 transmons | 86,016 | State Fidelity: **0.9023 +/- 0.0069** | Edge (14, 15) +2.28 pp cross-talk gain; 86.0% ensemble win-rate (p < 1e-4) | **CERTIFIED** |
| **OSIRIS-QAML-001** | `ibm_marrakesh` (Heron r1) | 8 transmons | 81,920 | Adversarial Retention vs. CNN | Quarantined as inconclusive due to statistical power deficit at N_test=5 (20 pp step size) | **QUARANTINED** |
| **OSIRIS-HP-003** | `ibm_fez` (Heron r2) | 8 transmons | 46,080 | Multi-Qubit Capacity Bound Staging | Quarantined under Forensic Audit E-44 through E-52 due to harvester formula defect, Arm B-Def missing decoder, and compiler cancellation | **QUARANTINED** |

---

## 2. Forensic Quarantine & Decisive Incident Reports

### 2.1 OSIRIS-HP-003 Forensic Non-Conformance (Audit Records E-44 to E-52)
A formal technical audit revealed that preliminary execution Job `dbncs05t7fqc73ajci00` cannot test or certify the Hayden-Preskill quantum capacity bound:
1. **Harvester Metric Mathematical Failure (E-49):** The joint fidelity formula in `harvest_hp003.py:134` computed `F_joint = (1 + <XXXX> - <YYYY> + <ZZZZ>) / 4`. Because `<YYYY> = +1` on `|Phi+>^{x2}`, an ideal recovery yields `0.500000`. Furthermore, 3 Pauli settings capture only 10 of 16 stabilizer terms, rendering joint fidelity unidentifiable.
2. **Arm B-Def Decoder Omission (E-48):** In `stage_hp003_harness.py:95-99`, Arm B-Def executed `pass`. No decoding unitary was applied to `(D1, E1, E2)`. The test measured raw scrambler output `I(R1:D1) = 0` rather than sub-capacity recovery.
3. **Compiler Gate Cancellation (E-50):** Arm A lacked `qc.barrier()`, compiling to 21 CZs (depth 46) versus 49 CZs (depth 87) in Arm B due to `U1 * U1^dagger` cancellation under Qiskit Level 3 transpilation.
4. **Control Leaks (E-51):** B-Ctrl leaked 2 bits (`I(R:D) = 2.0000`), and scrambler `U2` failed tripartite scrambling (`I(R:D)=2.0000`, `I(R:C)=2.0000`).
5. **Remediation & Retraction:** All preliminary capacity bound claims are retracted from `papers/crsm_nature_physics_2026.tex`. Protocol quarantined pending full re-synthesis.

### 2.2 OSIRIS-QAML-001 Methodological Quarantine
The QAML-001 hardware benchmark evaluated adversarial accuracy at `N_test=5` samples, producing a discrete `+/- 20 pp` granularity. Because the classical baseline boundary artifact biased the comparative metric, the claim of quantum advantage under PGD attack is formally quarantined as inconclusive until high-sample validation (`N >= 50`) is conducted.

---

## 3. Cryptographic Provenance & Ledger Anchors

The complete campaign is anchored across Blocks #1 through #46 in `evidence_ledger.db` with unbroken SHA-256 parent-block hash chaining:
- **Block #35:** `SYS021_HP001_DISPATCH_GRANT` (`5414f09d...`)
- **Block #39:** `SYS021_HP001_HARDWARE_ACQUISITION_RECEIPT` (`e78d2b78...`)
- **Block #41:** `SYS021_HP002_DISPATCH_GRANT` (`fc92a845...`)
- **Block #42:** `SYS021_QAML_001_HARDWARE_ACQUISITION_RECEIPT` (`5df1ba53...`)
- **Block #43:** `SYS021_HP002_DISPATCH_GRANT` (Barrier Rerun, `08d20448...`)
- **Block #44:** `SYS021_HP002_HARDWARE_ACQUISITION_RECEIPT` (Job `dbnchbgqtr0c73acppe0`, `e19fc278...`)
- **Block #45:** `SYS021_HP003_DISPATCH_GRANT` (`f78ab68a...`)
- **Block #46:** `SYS021_HP003_HARDWARE_ACQUISITION_RECEIPT` (Job `dbncs05t7fqc73ajci00`, `11da5b59...`, Quarantined)
