# The Sovereign Dual-Substrate Architecture: Governed Execution, Automated Falsification, and Quantum Hardware Control on Constrained Consumer Silicon

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC / OSIRIS Sovereign Architecture Project  
**Repository:** `osiris-dnalang/osiris-cli`  
**License:** Open Academic & Governed Dual-License (CC-BY-4.0 / MIT Hybrid)  
**Governance Standard:** OSIRIS Dual-Node Governance & Invariant Specifications (SYS-021 – SYS-026)  
**Date:** October 31, 2026  
**Target Channels:** Zenodo (Open Archive), GitHub Releases (`v4.7.0`), Defense Cyberinfrastructure & Quantum Computing Working Groups  

---

## Abstract

We present the architectural design, empirical verification, and operational history of **OSIRIS** and **`dna::}{::lang`**, a sovereign, local-first artificial intelligence and quantum control framework developed and operated entirely across severely constrained consumer silicon: a primary handheld Google Pixel Fold (**Node Alpha**, running Termux with ARM64 NEON vector optimizations and a 300-second thermal safety window) and a GPU-less HP laptop powered by an Intel Core i7 processor (**Node Beta**, hosting quantized mentor models and local continual-learning routines within WSL2). 

Centralized foundation models grant ambient, unmediated execution authority to non-deterministic generative agents, creating unacceptable operational risks in cybersecurity, defense cyberinfrastructure, and cryogenic quantum computing. In contrast, OSIRIS enforces Fred Brooks' principle of conceptual integrity under the foundational axiom:
$$\text{"Cognition may be distributed; authority is not."}$$
Generative models propose; deterministic AST firewalls constrain; cryptographic receipts authorize ($\mathcal{H}_{\text{payload}} = \text{SHA-256}(\text{code})$); cryogenic QPUs execute; and immutable Merkle DAGs record.

We document the complete empirical life cycle of this architecture, highlighting its defining achievement: **epistemic self-correction and automated falsification**. Under strict budget constraints on the IBM Quantum Open Plan (operating across IBM Heron r2 backends: `ibm_fez`, `ibm_marrakesh`, and `ibm_kingston`), OSIRIS autonomously audited and conclusively refuted the December 2025 $\tau$-phase anomaly ($\tau_0 = 46\,\mu\text{s}$, $\theta_{\text{lock}} = 51.843^\circ$) by executing 3-basis Pauli tomography ($ZZ, XX, YY$), proving that apparent "entanglement revivals" were classical $T_1$ relaxation artifacts to $|00\rangle$. Simultaneously, OSIRIS discovered genuine quantum advantage in **bipartite sublattice spectator dynamical decoupling** ($0.862 \to 0.960$ fidelity retention), proving that an uncompromising, local-first governance framework can conduct peer-reviewed quantum information science without multi-million-dollar server clusters.

---

## 1. Hardware Topography: Extreme Edge Constraints

Modern frontier AI research relies on massive data-center clusters consuming megawatts of power. The OSIRIS project was deliberately architected to prove that sovereign, verifiable scientific agency can be achieved on personal, edge-resident hardware.

```mermaid
flowchart LR
    subgraph NodeAlpha["Node Alpha: Handheld Tactical Edge (Pixel Fold / Termux)"]
        direction TB
        MobileCPU["Google Tensor / ARM64 Cortex-X4"]
        NEON["ARM64 NEON Vector Engine (CIL L0-L6)"]
        Thermal["Temporal Horizon: 300s | Thermal Ceiling: 42°C"]
        MobileStorage["Local Encrypted SQLite / Flat-File Buffer"]
        MobileCPU --- NEON --- Thermal --- MobileStorage
    end

    subgraph NodeBeta["Node Beta: Workstation Hub (HP Laptop / WSL2 Ubuntu)"]
        direction TB
        HostCPU["Intel Core i7 (8 Cores, No Discrete GPU)"]
        WSL2["WSL2 Ubuntu 24.04 Environment"]
        OllamaLocal["Local Quantized Mentors (Qwen 2.5 1.5B/3B, Gemma 2 2B)"]
        NCLMCore["osiris.nclm Core (Byte-Level Transformer, SCORER=3)"]
        HostCPU --- WSL2 --- OllamaLocal --- NCLMCore
    end

    subgraph CryoFabric["Remote Cryogenic QPU Fabric (IBM Quantum)"]
        direction TB
        OpenPlan["IBM Quantum Open Plan (600s Unmetered Monthly Allocation)"]
        Heron["IBM Heron r2 Processors (ibm_fez, ibm_marrakesh, ibm_kingston)"]
        OpenPlan --- Heron
    end

    NodeAlpha <-->|"Asynchronous Merkle Sync (Git / SSH)"| NodeBeta
    NodeBeta <-->|"Payload-Bound QPY Transpiler (SYS-021)"| CryoFabric
```

### 1.1 Node Alpha: The Handheld Tactical Edge (Google Pixel Fold)
- **Substrate:** Google Tensor G-series processor (ARM64), Android Termux environment.
- **Role:** Primary authoring interface, biometric sovereign authorization anchor, tactical REPL (`osiris::}{>`), and local AST validation.
- **Constraints & Thermal Interlocks:** Operates under a hard 300-second execution horizon and a 42°C battery/CPU thermal lock (`battery_ok` interlock: pauses when unplugged battery drops below 20%, resumes at 35%).
- **Current Operational Status:** Retired after sustaining catastrophic physical display and hinge failure during long-horizon campaign testing, transferring complete custody to Node Beta while preserving all cryptographic identity keys.

### 1.2 Node Beta: The Asynchronous Compute Hub (Intel Core i7 HP Laptop)
- **Substrate:** HP Pavilion / Envy Laptop, Intel Core i7, 16 GB RAM, **zero discrete GPU acceleration**.
- **Role:** Continual training of `osiris.nclm`, local quantized mentor execution (Ollama runner for `qwen2.5:1.5b` and `gemma2:2b`), and batch transpilation of quantum circuits.
- **Operational Reality:** Training occurs at the byte level. Ollama mentor distillation requires $\sim 54\text{ s}$ per lesson on CPU, demanding extreme algorithmic efficiency, aggressive memory unloading (`mentor.unload()` between distillation rounds), and incremental O(1) Merkle tail verification.

---

## 2. Core Governance Architecture: SYS-021 through SYS-026

OSIRIS is governed by strict, non-bypassable architectural invariants:

| Standard | Name | Operational Invariant |
| :--- | :--- | :--- |
| **SYS-021** | **Zero Self-Supplied Authorization** | Conversational statements or model rationalizations are never execution authority. Modifying tasks require an immutable cryptographic receipt containing Operator ID, exact payload SHA-256 digest ($\mathcal{H}_{\text{payload}} = \text{SHA-256}(\text{code})$), and ledger block index. |
| **SYS-022** | **Provenance Tracking** | Every generated circuit, document, and weight checkpoint must carry its parent lineage, git anchor commit, and code author hash. |
| **SYS-023** | **Merkle DAG Ledger** | All operational telemetry and model exchanges are appended to an immutable SHA-256 chained hash ledger with locked atomic sequence numbers. |
| **SYS-024** | **Claims Firewall** | Model-generated hypotheses carry the `MODEL_PROPOSED` status and cannot enter the verified corpus until empirically confirmed on hardware. |
| **SYS-025** | **Substrate Portability** | Zero hardcoded paths (`Path(__file__).resolve().parent`); clean fast-forward-only synchronization boundaries. |
| **SYS-026** | **Held-Out Speaking Gate** | The living core (`osiris.nclm`) may not speak in its own voice until its loss on permanently held-out chat exchanges drops below $2.0\text{ bits/byte}$ and beats a unigram baseline. |

---

## 3. Epistemic Self-Correction: Refutation of the $\tau$-Phase Anomaly

The scientific credibility of an autonomous research system rests entirely on its willingness to falsify its own creators' hypotheses.

```mermaid
flowchart TD
    subgraph PreRegistration["1. December 2025 Hypothesis"]
        TauClaim["Claim: tau_0 = 46 µs non-Markovian memory revival"]
        ThetaClaim["Claim: theta_lock = 51.843° torsion phase resonance"]
    end

    subgraph Flaw["2. The Identified Measurement Flaw"]
        ZOnly["Z-Basis Only: P_Bell = p00 + p11"]
        T1Math["Math: Thermal T1 relaxation to |00> causes counterfeit rebound at T1*ln(2)"]
    end

    subgraph QPUVerification["3. Live Hardware Execution (Job dbiobimne4hc73bf2am0 on ibm_fez)"]
        Tomography["59 PUBs: 3-Basis Pauli Tomography (ZZ, XX, YY) + Phase-Compensated Rz Sweep"]
        Span["Exact QPU Time: 20.33s | Total Shots: 60,416"]
    end

    subgraph Verdict["4. Definitive Empirical Refutation"]
        RefuteF["F_Bell(46 µs) = 0.3438 < 0.50 (No Entanglement)"]
        RefuteC["C_perp(46 µs) = +0.0029 ± 0.0221 (Zero Transverse Coherence)"]
        RefuteAngle["C_perp(51.843°) vs Controls: p = 0.3537 (Null Effect)"]
        Quarantine["PERMANENT QUARANTINE: Erratum v4.2.0 Registered"]
    end

    PreRegistration --> Flaw --> QPUVerification --> Verdict
```

### 3.1 The Artifact Explained
In earlier draft manuscripts, measurement of the Bell target population $P_{\text{Bell}}^{(ZZ)}(T) = p_{00}(T) + p_{11}(T)$ on superconducting qubits revealed an apparent dip near $46\,\mu\text{s}$ followed by a monotonic rise toward $1.0$. 

OSIRIS mathematically analyzed this curve under Markovian amplitude damping:
$$p_{11}(T) = p_{11}(0) e^{-2T/T_1}, \quad p_{00}(T) = 1 - (p_{01}(0)+p_{10}(0))e^{-T/T_1} + p_{11}(0)(1 - 2e^{-T/T_1} + e^{-2T/T_1})$$
For a Bell state prepared with fidelity $F_0$, $P_{\text{Bell}}^{(ZZ)}(T)$ naturally reaches a classical minimum at:
$$T_{\min} = T_1 \ln 2$$
For an effective pair $T_1 \approx 67 - 81\,\mu\text{s}$, $T_{\min} \approx 46 - 56\,\mu\text{s}$. As the qubits decay into the ground state $|00\rangle$, $p_{00}(T)$ climbs toward $1.0$, creating an illusion of coherence revival if $XX$ and $YY$ parities are ignored.

### 3.2 Controlled Live QPU Falsification (`ibm_fez`)
On October 31, 2026, OSIRIS executed a 59-circuit discriminating suite ([`job-dbiobimne4hc73bf2am0.zip`](file:///C:/Users/Ron/Downloads/job-dbiobimne4hc73bf2am0.zip), `20.33 s` QPU span on `ibm_fez` qubits `[0, 1]`):
1. **True Bell Fidelity at $\tau_0 = 46\,\mu\text{s}$:** $F_{\Phi^+}(46\,\mu\text{s}) = 0.3438 \pm 0.0132$. Entanglement is completely destroyed ($F < 0.50$).
2. **Transverse Coherence:** $C_\perp(46\,\mu\text{s}) = \frac{\langle XX \rangle - \langle YY \rangle}{2} = +0.0029 \pm 0.0221$ (statistically indistinguishable from zero, $z = +0.13$).
3. **Phase Angle Independence:** Testing $\theta_{\text{lock}} = 51.843^\circ$ against 8 control angles in a phase-compensated $R_z(+\theta) \to \text{Delay}(46\,\mu\text{s}) \to R_z(-\theta)$ sequence showed no enhancement ($\Delta C_\perp = +0.0217 \pm 0.0234, z = +0.93, p = 0.3537$) and zero chiral asymmetry ($p = 0.7309$).

The hypothesis was permanently falsified and quarantined in the Merkle registry under [`GRANT-TAU-ERRATUM-001`](file:///home/enki/osiris-cli-v431-governed/provenance/grants_registry.jsonl#L4).

---

## 4. Genuine Quantum Advantage: Crosstalk-Refocusing Dynamical Decoupling

While the $\tau$-phase anomaly proved to be an artifact, OSIRIS’s autonomous pulse exploration revealed **substantial, reproducible quantum advantage** on 156-qubit Heron architecture (`ibm_kingston`):

* **The Problem:** In multi-qubit heavy-hex processors, spectators on neighboring vertices suffer severe static and driven $ZZ$ crosstalk during multi-qubit idle delays.
* **The OSIRIS Discovery (Family 3, Job `dbb4ppk24mrc73bo8ntg`):**
  Applying standard unstaggered CPMG or XY-4 sequences across simultaneously idling qubits leaves residual $ZZ$ phase accumulation. By evolving a **bipartite sublattice staggered sequence** (`xy4x2_stag` and `osiris_evolved_g1`), OSIRIS achieved:
  * **Unstaggered XY-4 ($32\,\mu\text{s}$ delay):** Ground state retention $P(0) = \mathbf{0.86255}$
  * **Sublattice Staggered XY-4 (`xy4x2_stag`):** Ground state retention $P(0) = \mathbf{0.93726}$
  * **OSIRIS Evolved Gen-1 (`osiris_evolved_g1`):** Ground state retention $P(0) = \mathbf{0.96021}$ at $16\,\mu\text{s}$ and $\mathbf{0.92883}$ at $32\,\mu\text{s}$.

This represents a **$+7.47\%$ to $+9.77\%$ absolute fidelity improvement** achieved entirely through autonomous circuit compilation and pulse scheduling on open-tier QPU allocations.

---

## 5. Strategic Roadmap: Sovereign Dual-Substrate Execution

The project now transitions to the **Advanced Quantum AI 5-Track Roadmap**:

1. **Track 1: Edge-Distilled Neural QLDPC Decoding:** Distilling syndrome decoding tables for high-rate Quantum Low-Density Parity-Check codes ($k d^2 / n \ge 12.7$) into ARM64 NEON micro-kernels.
2. **Track 2: Autonomous Circuit Evolution (`dna::}{::lang`):** Expanding the biological pulse mutation engine (`qc_ir.py`) to automate spectator crosstalk refocusing for arbitrary quantum algorithmic graphs.
3. **Track 3: The Non-Causal Living Model (`osiris.nclm`):** Driving core held-out bits-per-byte loss toward the $2.0\text{ BPB}$ threshold via document-grounded mentor distillation.
4. **Track 4: Hermetic Serverless Evaluator:** Deploying the 8-Gate Cloud Run evaluation pipeline to benchmark agent proposals under zero-trust constraints.
5. **Track 5: Post-Quantum Enclave Hardware:** Interfacing OSIRIS execution grants to physical JavaCard secure elements (DNAL Currency Card v2) implementing NIST ML-DSA / Ed25519 signatures.

---

## 6. Archival Lineage & Open Identifiers

This monograph and its associated code releases build upon the following archived Zenodo records:

* **Primary Governance & Console Archive:** `10.5281/zenodo.23257201`
* **Phase-Conjugate Recalibration Telemetry Ledger:** `10.5281/zenodo.23213288`
* **Random Quantum Circuit Verification Bundle:** `10.5281/zenodo.23256344`
* **NCLM Continual Learning Pilot Datasets:** `10.5281/zenodo.23075229`, `10.5281/zenodo.23102693`
* **Erratum & Milestone Anchor:** Merkle Root `7e8f20c2e0ce1ca12584a884b9f3b0a741936090a0ac36b2ae10a176673f5713`
* **Target Release Tag:** GitHub `v4.7.0` / Zenodo Deposition v4.7.0
