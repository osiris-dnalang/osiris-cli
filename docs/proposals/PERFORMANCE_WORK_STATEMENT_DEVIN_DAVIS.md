# PERFORMANCE WORK STATEMENT (PWS)
## Governed Autonomous Systems Architecture, Quantum Cyberinfrastructure & Edge Compute Engineering
**Document Control Number:** PWS-ADS-2026-02  
**Target Organization / Customer:** Department of the Air Force (DAF) / AFWERX / Defense Industrial Base (DIB) / Enterprise Sovereign Infrastructure  
**Contractor / Principal Investigator:** Devin Phillip Davis, Founder & Lead Systems Architect  
**Entity:** Agile Defense Systems LLC (CAGE / SAM Active)  
**LinkedIn:** [https://www.linkedin.com/in/ξ-devin-phillip-davis-88379b174](https://www.linkedin.com/in/%CE%BE-devin-phillip-davis-88379b174)  
**Effective Date:** November 2026  
**Security Classification:** UNCLASSIFIED // FOR OFFICIAL USE ONLY (FOUO) // CUI-Ready  

---

```
       ==================================================================================
                              PERFORMANCE WORK STATEMENT (PWS)
                       Agile Defense Systems LLC &middot; Devin Phillip Davis
       ==================================================================================

        [ Scope & Governance ]        [ Core Technical Pillars ]        [ Verified Deliverables ]
        +--------------------+        +-------------------------+        +-----------------------+
        | SYS-021 Fail-Closed| -----> | 1. Sovereign AI C-SIMD  | -----> | C-Contiguous Tensor   |
        | Math Determinism   |        | 2. PQC Merkle Ledgers   |        | FIPS 204 ML-DSA-65    |
        | AST Interposition  |        | 3. Physical QPU Control |        | STAG-XY8 663k Shots   |
        | Zero Cloud Reliance|        | 4. Dual-Node Edge Mesh  |        | ARM64 NDK Zero-Copy   |
        | CMMC 2.0 Level 2/3 |        | 5. Fleet CAD Automation |        | 12-Printer AMS Vault  |
        | DAU / OTA / MTA    |        | 6. Evaluative Sandboxes |        | RFC 8785 BEIR SciFact |
        +--------------------+        +-------------------------+        +-----------------------+
       ==================================================================================
```

---

## 1.0 GENERAL INFORMATION & MISSION PURPOSE

### 1.1 Mission & Architectural Ethos
The Department of the Air Force (DAF), Department of Defense (DoD), and enterprise sovereign computing infrastructure require hardened, verifiable systems capable of executing high-consequence computing workloads without reliance on fragile external cloud connections or unverified probabilistic model outputs. Current generative AI systems and autonomous agent frameworks operate with non-deterministic, open-loop execution authority, introducing critical vulnerabilities: hallucinations, prompt-injection exploits, memory-stride corruption, and untracked system state mutations.

This Performance Work Statement (PWS) establishes the technical scope, operational tasks, quality metrics, and performance standards for **Devin Phillip Davis** (Agile Defense Systems LLC). Davis’s architectural ethos enforces mathematical determinism, fail-closed authorization bounds, static Abstract Syntax Tree (AST) interposition, and cryptographic evidence anchoring: **generative models propose actions, while deterministic code strictly decides execution.**

### 1.2 Program Scope
The Contractor shall serve as Principal Systems Architect and Quantum Cyberinfrastructure Engineer, delivering full-stack development, low-level kernel optimization, physical quantum processor validation, post-quantum cryptographic governance, distributed edge IPC bridges, parametric additive manufacturing automation, and rigorous empirical evidence evaluation across six core capability areas:
1. **Sovereign AI & C-SIMD Acceleration:** Dual-voice Non-Causal Language Model (NCLM) architectures decoupled from conversational mentors, accelerated via AVX2/AVX-VNNI C-SIMD kernels, with strict C-contiguous tensor stride alignment.
2. **Cryptographic Governance & Merkle Ledgers (SYS-021):** Zero Self-Supplied Authorization execution enclaves, dual-signed via NIST FIPS 204 ML-DSA-65 and Ed25519, recorded into tamper-evident SQLite block ledgers.
3. **Quantum Information Science & Hardware QPU Telemetry:** OpenQASM 3.0 compilation, staggered dynamical decoupling (STAG-XY8) pulse scheduling, and preregistered Hayden–Preskill scrambling benchmarks on physical IBM Heron r2 hardware.
4. **Distributed Dual-Node Substrate Mesh:** Low-latency IPC bridging pocketable ARM64 edge nodes (Google Pixel 10 Pro Fold / Tensor G5) to x86_64 compute hosts via zero-copy Android NDK JNI and abstract domain sockets.
5. **Parametric Manufacturing & Cloud Infrastructure:** osiris-fabric control plane governing a 12-printer Bambu Lab fleet, Vertex AI supervised fine-tuning (SFT), and headless geometry verification microservices.
6. **Autonomous Evaluation & Evidence Capsules:** Bounded sandbox execution capsules (EXP-OLMO3-BEIR-SCIFACT-001) evaluating MTEB/BEIR benchmarks under RFC 8785 canonical serialization, and the 46-criterion osiris-android-spec-001 platform acceptance specification.

### 1.3 Defense Acquisition & Systems Engineering Credentials
The Contractor brings rigorous institutional grounding certified through the **Defense Acquisition University (DAU)**, holding official completions across:
- **Cybersecurity & Resiliency:** `CYB 5610` (Cybersecurity & Resiliency for Weapons, Control and IT Systems), `WSA 002` (DEVSECOPS for the DoD: Security Focus), `CENG 003A` (AI Foundations for the DoD).
- **Systems Engineering:** `ENG 101` (Fundamentals of Systems Engineering), `ENG 201` (Applied Systems Engineering in Defense Acquisition, Part I).
- **Specialized Contracting & Prototyping:** `CLC 066` (Other Transactions / OTAs), `ACQ 0150` (Middle Tier of Acquisition / Section 804 Rapid Prototyping/Fielding), `CON 0210` (R&D Processes & Programs), `ACQ 1300` (Fundamentals of Technology Security/Transfer), `ACQ 0800` (Federally Funded Research & Development Centers / FFRDCs).
- **Integrated Scheduling & Financial Governance:** `CLM 094` (Integrated Master Scheduling / IMS), Primavera P6, `CLC 056` (Analyzing Contract Costs), `CON 124` (Contract Execution), `CLE 076` (Agile Software Acquisition).

---

## 2.0 APPLICABLE DOCUMENTS & COMPLIANCE MANDATES

The Contractor shall perform all tasks in strict conformance with the following statutory, military, and cryptographic standards:

1. **DoD CMMC 2.0 Level 2 & Level 3:** NIST SP 800-171 Rev 2 / NIST SP 800-53 Rev 5 controls for Controlled Unclassified Information (CUI):
   - `AU-2`, `AU-3`, `AU-4`, `AU-6`, `AU-9`, `AU-10`, `AU-11` (Audit Logging, Integrity, Non-Repudiation, and Retention)
   - `AC-3`, `AC-4`, `AC-6` (Access Enforcement, Information Flow, and Least Privilege)
   - `SI-4`, `SI-7` (Information System Monitoring, Firmware/Software Integrity)
   - `SC-13`, `SC-28` (Cryptographic Protection, Protection at Rest)
2. **Post-Quantum Cryptography Migration:** 
   - National Security Memorandum 10 (NSM-10) and OMB M-23-02
   - NIST FIPS 203 (ML-KEM), NIST FIPS 204 (ML-DSA-65), and NIST FIPS 205 (SLH-DSA)
   - NSA Commercial National Security Algorithm Suite 2.0 (CNSA 2.0)
3. **Quantum Architecture & Intermediate Representation:**
   - OpenQASM 3.0 Language Specification (Live AST Parser & Semantic Validator)
   - IBM Quantum Heavy-Hex Architecture & Heron r2 Native ISA (`cz`, `rz`, `sx`, `x`)
4. **Data Formatting & Schema Compliance:**
   - RFC 8785 (Canonical JSON Serialization Format)
   - Elastic Common Schema (ECS 8.x) Telemetry Ingestion Specification

---

## 3.0 SPECIFIC PERFORMANCE REQUIREMENTS & WORK BREAKDOWN STRUCTURE (WBS)

```
       ==================================================================================
                               WORK BREAKDOWN STRUCTURE (WBS)
       ==================================================================================
       WBS 1.0: Sovereign AI & C-SIMD Acceleration Engine
       WBS 2.0: SYS-021 Cryptographic Governance & Merkle Evidence Ledgers
       WBS 3.0: Quantum Information Science & Physical QPU Validation
       WBS 4.0: Distributed Dual-Node Substrate Mesh & Edge NDK IPC
       WBS 5.0: Parametric Manufacturing Automation & Headless CAD Gates
       WBS 6.0: Autonomous Evaluation Sandboxes & Edge Platform Acceptance
       ==================================================================================
```

### 3.1 WBS Task 1: Sovereign AI & C-SIMD Acceleration Architecture
The Contractor shall design, build, and maintain low-latency, localized neural computing engines that operate completely independent of commercial cloud dependencies:
- **1.1 Living Core Neural Engine:** Maintain and enhance the 4.08M parameter localized living core (`osiris.nclm`) decoupled from conversational mentors (`qwen2.5:1.5b`). The living core shall synthesize internal state representations, phase-conjugate positional encodings, and epistemic confidence metrics.
- **1.2 C-SIMD Vector Kernel Acceleration:** Engineer and benchmark vectorized C kernels (`c_simd_ops.c`, compiled via `build_simd.sh`) utilizing Intel/AMD AVX2 and AVX-VNNI hardware extensions for fused multiply-accumulate and matrix operations.
- **1.3 Tensor Memory Stride Alignment:** Enforce strict C-contiguous float32 memory layout across the autoregressive KV-cache $(B, H, T, HD)$, eliminating memory stride corruption, segment faults, and ensuring numerical equivalence ($< 1.15 \times 10^{-5}$ maximum logit deviation) against baseline `SovereignTransformerV2` forward passes.
- **1.4 Bracketed-Paste Intent Quarantine:** Maintain automated natural language intent routers (`/learn`, `/remember`, `/forget`). Untrusted inputs and code snippets must be quarantined in ephemeral staging cards, preventing untrusted input from mutating weights without explicit cryptographic authority.

### 3.2 WBS Task 2: Cryptographic Governance & Merkle Evidence Ledgers (SYS-021)
The Contractor shall implement and enforce the non-negotiable **SYS-021** operational invariant across all autonomous software components:
- **2.1 Zero Self-Supplied Authorization:** Ensure no autonomous agent, model prompt, or conversational output can self-authorize state mutations, file modifications, background dispatches, or external network calls.
- **2.2 Payload-Bound Authorization Grants:** Every state-modifying action requires a cryptographic grant binding the operator public identity (`Devin Phillip Davis / Enki`) to the exact SHA-256 digest of executable code:
  $$\mathcal{H}_{\text{payload}} = \text{SHA-256}(\text{code})$$
  Any byte modification alters the digest and immediately invalidates authorization.
- **2.3 Hybrid Post-Quantum Enclave:** Maintain an active cryptographic enclave (`osiris_cli/pqc_enclave.py`) enforcing dual-signing with NIST FIPS 204 ML-DSA-65 (lattice-based digital signatures) alongside classical Ed25519.
- **2.4 Tamper-Evident Merkle Ledgers:** Commit all execution events to an append-only SQLite evidence ledger (`evidence_ledger.db`) utilizing RFC 8785 canonical JSON serialization, where each block incorporates the SHA-256 digest of the previous block:
  $$\mathcal{H}_n = \text{SHA-256}(\mathcal{H}_{n-1} \parallel \text{Payload}_n)$$
- **2.5 External State Anchoring:** Periodically commit local ledger chain heads to external, immutable public registries (permanent Zenodo DOIs and signed Git release tags) to mathematically detect and prevent local root ledger rewrites.

### 3.3 WBS Task 3: Quantum Information Science & Physical QPU Validation
The Contractor shall design, execute, and verify quantum optimal control sequences across physical superconducting quantum processors:
- **3.1 Physical QPU Pulse Scheduling:** Transpile and execute calibrated quantum circuit campaigns on IBM Heron r2 heavy-hex processors (`ibm_fez`, `ibm_torino`, `ibm_marrakesh`), accumulating over 660,000 shots.
- **3.2 Staggered Dynamical Decoupling (STAG-XY8):** Formulate and benchmark staggered XY8 and XY4 pulse schedules targeting spectator transmon qubit coupling chains (e.g., edges 14, 15 and 61, 62), measuring residual Hamiltonian ZZ interactions and demonstrating statistically significant fidelity gains over unmitigated baselines.
- **3.3 Hayden–Preskill Information Recovery Protocol (`osiris-hp-001`):** Execute the 3-arm preregistered quantum recovery protocol evaluating state entanglement restoration:
  $$F_{\mathrm{rec}} = \langle\Phi^+|\rho_{RM'}|\Phi^+\rangle$$
  across Identity controls (Arm A), restricted-access scrambling (Arm B), and noise-calibrated controls (Arm C).
- **3.4 In-Memory Deterministic Claims Engine:** Maintain the claims validation firewall (`claims.py`), verifying runtime physical assertions against established theoretical bounds, Bell-CHSH inequalities, and empirical noise floors (1.11 pp RMS), automatically rejecting unphysical claims.

### 3.4 WBS Task 4: Distributed Dual-Node Substrate Mesh & Edge NDK IPC
The Contractor shall architect and maintain low-latency cross-platform edge infrastructure connecting mobile edge nodes with compute hosts:
- **4.1 Dual-Node Mesh Synchronization:** Bridge pocketable ARM64 edge nodes (Node Alpha: Google Pixel 10 Pro Fold / Android 16 / Termux) with workstation hosts (Node Beta: x86_64 WSL2 Ubuntu 24.04 LTS).
- **4.2 Zero-Copy NDK JNI Shared Memory:** Bypass Android runtime (ART) overhead using C++ Android NDK JNI shared memory interfaces (`NativeBleBridge`) utilizing `DirectByteBuffer` pointers.
- **4.3 Abstract UNIX Domain Sockets:** Deploy local abstract domain socket daemons (`\0osiris_bt_bridge` / `\0edge_bt_bridge`), achieving microsecond-level POSIX `epoll` packet streaming between hardware BLE radios and edge Python/C++ CLI runtimes.
- **4.4 Substrate Thermal & Power Governors:** Implement hysteretic hardware telemetry monitors (`osiris_daemon`) on Google Tensor G5 silicon, enforcing dynamic 300-second execution horizons to protect long-running tasks from Android Phantom Process Killers and OOM kernel reapers.

### 3.5 WBS Task 5: Parametric Manufacturing Automation & Headless CAD Gates
The Contractor shall govern and automate cyber-physical additive manufacturing workflows:
- **5.1 12-Printer Fleet Automation (`osiris-fabric`):** Supervise an active 12-printer Bambu Lab manufacturing farm (5x P1S, 1x H2X, 2x A1, 2x A2L, 2x A1 Mini) equipped with multi-material Automatic Material Systems (AMS).
- **5.2 Multi-Material Purge Optimization:** Deploy `AmsFlushOptimizer` and `osiris_filament_vault.py`, tracking digital spool twins and calculating color transition deltas ($\Delta E$), diverting purge waste into interior gyroid infill to reduce material waste by 40% to 70%.
- **5.3 Headless Cloud Run Geometry Validation:** Build and maintain containerized Cloud Run microservices executing headless OpenSCAD and OrcaSlicer CLI binaries. Candidate parametric scripts emitting non-manifold meshes or unprintable overhangs must fail closed before G-code compilation.
- **5.4 Vertex AI Supervised Fine-Tuning (SFT):** Curate and maintain training datasets in Google Cloud Storage (`gs://dnalang-evolver-archive/training/`), executing SFT runs on Google Cloud Vertex AI targeting `gemini-2.5-flash` to synthesize valid OpenSCAD/build123d parametric geometries.

### 3.6 WBS Task 6: Autonomous Evaluation Sandboxes & Edge Platform Acceptance
The Contractor shall design, validate, and maintain automated evaluative test harnesses and normative platform specifications:
- **6.1 Evidence Capsule Benchmarking:** Deploy the `EXP-OLMO3-BEIR-SCIFACT-001` evidence capsule within the `osiris-cybercontext` runtime, executing bounded sandbox retrieval evaluations on SciFact (`NDCG@10 = 0.2658`, `MRR@10 = 0.1139`, `CTC = 0.7646`), diagnosing top-1 rank suppression and providing empirical justification for cross-encoder reranking layers.
- **6.2 Android Platform Specification (`osiris-android-spec-001`):** Maintain and enforce the 46-criterion Android platform specification across 10 modules (`:demo`, `:app`, `:keyboard`, `:governance`, `:evidence`, `:evaluation`, `:execution`, `:runtime-bridge`, `:sdk`), achieving 100% pass rates across 53 unit/mocked/physical tests.
- **6.3 100-Command Advanced Operations Manual:** Implement and verify the complete 100-command diagnostic scorecard spanning cryptographic ledger checks, AVX2 SIMD tensor strides, claims firewalls, OpenQASM parsing, and POSIX packaging.

---

## 4.0 PERFORMANCE STANDARDS & QUALITY ASSURANCE SURVEILLANCE PLAN (QASP)

The Contractor’s performance shall be evaluated against rigorous mathematical and operational Acceptable Quality Levels (AQL):

| Performance Objective | PWS WBS Reference | Performance Standard / Metric | Acceptable Quality Level (AQL) | Method of Surveillance |
|---|---|---|---|---|
| **C-SIMD Numerical Equivalence** | WBS 3.1.3 | Max logit error between C-SIMD AVX2 kernel and `SovereignTransformerV2` forward pass. | Maximum logit deviation $\mathbf{\le 1.15 \times 10^{-5}}$; zero NaN/inf tokens. | Deterministic test suite (`tests/test_fast_inference.py`) executed in CI/CD. |
| **SYS-021 Enclave Inviolability** | WBS 3.2.1 | Pre-execution cryptographic authorization gate for mutating operations. | **Zero (0)** unauthenticated state mutations; 100% rejection of unauthorized payloads. | Boundary fault-injection test suite (`tests/test_grants.py`, `tests/test_p1_adversarial_core.py`). |
| **Merkle Ledger Integrity** | WBS 3.2.4 | Cryptographic continuity across append-only SQLite block records. | **100% hash chain validity**; zero hash pre-image breaks across all production blocks. | Continuous automated verification script (`tests/test_ledger_integrity.py`). |
| **Post-Quantum Signature Verification** | WBS 3.2.3 | Hybrid NIST FIPS 204 ML-DSA-65 and Ed25519 signature validation. | **100% valid dual-signatures**; zero classical algorithm downgrades permitted. | PQC verification gate (`tests/test_p4_adversarial_pqc.py`). |
| **Physical QPU Noise Floor Discipline** | WBS 3.3.4 | Empirical measurement of inter-arm hardware drift across identical pulse schedules. | Measured drift floor $\mathbf{\le 1.11\text{ pp RMS}}$; zero unverified statistical claims. | Matched-pair A/A statistical evaluation script (`claims.py`). |
| **Edge IPC Latency & Stability** | WBS 3.4.2 | Zero-copy NDK JNI and abstract domain socket packet streaming latency. | Packet transfer latency $\mathbf{\le 150\,\mu\text{s}}$; zero ART VM allocation stalls. | End-to-end POSIX socket benchmarking telemetry. |
| **Watertight Mesh Geometry Compile** | WBS 3.5.3 | Headless Cloud Run OpenSCAD verification for autonomous additive manufacturing. | **100% manifold, watertight geometry**; zero slicer parsing exceptions dispatched to fleet. | Automated geometry test harness and slicer exit code evaluation. |
| **Evidence Capsule Reproducibility** | WBS 3.6.1 | Bit-for-bit RFC 8785 canonical JSON serialization of MTEB/BEIR benchmark capsules. | **100% hash matching** against Merkle root `e46e6d92...`; reproducible ranking metrics. | Automated evaluation script and evidence bundle verification. |
| **Android Specification Conformance** | WBS 3.6.2 | 46-criterion `osiris-android-spec-001` test execution across 10 functional modules. | **53/53 tests passing (100%)**; zero build failures; CIL L0-L8 security barriers enforced. | Automated Gradle verification suite (`run_gradle_verification.py`). |

---

## 5.0 DELIVERABLES, MILESTONES & DELIVERY SCHEDULE

| Deliverable ID | Description | Delivery Target | Format / Delivery Mechanism |
|---|---|---|---|
| **DEL-01** | **osiris Living Core & C-SIMD Engine** (`osiris.nclm`, `c_simd_ops.c`) | Continuous / Production | Git repository (`main`), compiled Linux/ARM64 binaries, and test suite. |
| **DEL-02** | **SYS-021 PQC Enclave & Cryptographic Ledger** (`evidence_ledger.db`) | Continuous / Production | SQLite ledger, RFC 8785 JSON receipts, and permanent Zenodo DOI deposit. |
| **DEL-03** | **OpenQASM 3.0 Transpiler & QPU Campaign Telemetry** | Milestone-Based | Calibrated OpenQASM circuits, IBM QPU job receipts, and raw shot telemetry. |
| **DEL-04** | **Dual-Node Substrate Mesh & NDK Native Ble Bridge** | Milestone-Based | C++ NDK shared libraries, Termux environment configs, and daemon services. |
| **DEL-05** | **osiris-fabric Fleet Control Plane & SFT Datasets** | Production Active | JSONL SFT training datasets in GCS, Cloud Run container images, and OrcaSlicer profiles. |
| **DEL-06** | **Elastic Common Schema (ECS 8.x) Telemetry Ingestion Suite** | Ready for Deployment | NDJSON event streams, bulk ingest client, and 6 pre-built Elastic Security detection rules. |
| **DEL-07** | **Permanent Scientific Pre-Registrations & Errata** | Milestone-Based | Permanent Zenodo DOIs, TeX manuscripts, and open replication datasets. |
| **DEL-08** | **MTEB/BEIR Evidence Capsules & Android Acceptance Reports** | Milestone-Based | RFC 8785 evidence bundles, Android 46-criterion audit scorecards, and test logs. |

---

## 6.0 SPECIAL CONTRACT REQUIREMENTS, SECURITY & DATA RIGHTS

### 6.1 Government Data Rights (DFARS Compliance)
All foundational architectures, cryptographic ledgers, and open-source tooling developed by the Contractor prior to contract award remain the intellectual property of **Agile Defense Systems LLC / Devin Phillip Davis**. The Government shall receive **Unlimited Rights** to technical data, telemetry streams, and configuration packages developed specifically under Government-funded task orders, in accordance with DFARS 252.227-7013.

### 6.2 Security, CUI Handling, and Post-Quantum Mandates
All technical deliverables and data handling shall conform to NIST SP 800-171 Rev 2 controls for Controlled Unclassified Information (CUI). In compliance with OMB M-23-02 and CNSA 2.0, all digital audit records intended for multi-year retention shall incorporate NIST FIPS 204 post-quantum cryptographic signatures to guard against future quantum cryptanalysis.

### 6.3 Defense Acquisition Acumen & Middle Tier Authority
The Contractor’s demonstrated completion of DAU curricula across Other Transactions (`CLC 066`), Middle Tier of Acquisition (`ACQ 0150`), R&D Contracting (`CON 0210`), and Cybersecurity for Weapons Systems (`CYB 5610`) ensures seamless alignment with DoD rapid prototyping, commercial dual-use scaling, and OTA vehicle execution.

### 6.4 Principal Investigator Commitment
Devin Phillip Davis shall personally serve as Principal Systems Architect and lead technical contributor for all task areas, dedicating full-time professional labor to ensure adherence to mathematical determinism, quality standards, and delivery milestones.

---
*Agile Defense Systems LLC | Performance-Based Contracting & Sovereign Compute Engineering*
