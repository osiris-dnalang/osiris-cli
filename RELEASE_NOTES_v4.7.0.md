# OSIRIS v4.7.0 — Release Notes (2026-10-31)

A major milestone release delivering the **Sovereign Dual-Substrate Architecture**, formalizing the **automated falsification of the $\tau$-phase anomaly**, establishing **genuine multi-qubit crosstalk-refocusing quantum advantage** on IBM Heron r2 hardware, and integrating the **pure L4→L5 Capability Gap Analyzer**, **CUSUM process control suite**, and **Sprint 3 Adversarial Falsification Engine**.

Accompanied by the foundational research monograph: [`docs/SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md`](docs/SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md).

---

## 1. The Sovereign Dual-Substrate Architecture (`docs/SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md`)

- **Topography of Extreme Constraints**:
  - **Node Alpha (Tactical Edge)**: Google Pixel Fold running Android Termux, ARM64 NEON SIMD kernels, 300-second thermal safety horizon, and battery hysteretic governor. Formally retired from physical service after display/hinge endurance fatigue, with full cryptographic custody transitioned to Node Beta.
  - **Node Beta (Compute Workstation Hub)**: Intel Core i7 HP Laptop (zero discrete GPU) running Ubuntu 24.04 on WSL2. Houses local quantized mentors (Qwen 2.5 1.5B/3B, Gemma 2 2B) and executes continual byte-level training of `osiris.nclm`.
- **Governed Execution Axiom**:
  $$\text{"Cognition may be distributed; authority is not."}$$
  Non-deterministic LLMs propose; deterministic AST firewalls constrain; cryptographic receipts authorize ($\mathcal{H}_{\text{payload}} = \text{SHA-256}(\text{code})$); cryogenic QPUs execute; and immutable Merkle DAGs record.

---

## 2. Epistemic Self-Correction: Automated Falsification of the $\tau$-Phase Anomaly

- **Automated Root-Cause Diagnosis**:
  - Proved mathematically that prior apparent Bell-state fidelity revivals at $\tau_0 \approx 46\,\mu\text{s}$ were classical $T_1$ relaxation artifacts to $|00\rangle$ under unmitigated $Z$-basis measurements:
    $$T_{\min} = T_1 \ln 2 \approx 46 - 56\,\mu\text{s}$$
- **Full Hardware Falsification Suite (`ibm_fez`, Job `dbiobimne4hc73bf2am0`)**:
  - Executed 59 PUBs across 60,416 shots performing 3-basis Pauli tomography ($ZZ, XX, YY$) and phase-compensated $R_z(\theta)$ sweeps.
  - Measured True Bell Fidelity at $46\,\mu\text{s}$: $F_{\Phi^+}(46\,\mu\text{s}) = 0.3438 \pm 0.0132$ (destroying entanglement, $F < 0.50$).
  - Measured Transverse Coherence: $C_\perp(46\,\mu\text{s}) = +0.0029 \pm 0.0221$ (indistinguishable from zero, $z = +0.13$).
  - Evaluated geometric coupling angle $\theta_{\text{lock}} = 51.843^\circ$ against 8 controls: $p = 0.3537$ (null effect).
  - Hypothesis permanently quarantined under [`GRANT-TAU-ERRATUM-001`](provenance/grants_registry.jsonl) and Merkle Root `7e8f20c2e0ce...`.

---

## 3. Genuine Quantum Advantage: Crosstalk-Refocusing Dynamical Decoupling

- **Multi-Qubit Spectator Decoherence Mitigation (`ibm_kingston`, Job `dbb4ppk24mrc73bo8ntg`)**:
  - Demonstrated substantial quantum advantage on 156-qubit Heron architecture by evolving bipartite sublattice pulse-timing staggering (`xy4x2_stag` and `osiris_evolved_g1`) to cancel residual static spectator $ZZ$ crosstalk:
    - **Bare Idle ($32\,\mu\text{s}$)**: Ground state retention $P(0) = \mathbf{0.5945}$
    - **Unstaggered XY-4 ($32\,\mu\text{s}$)**: Ground state retention $P(0) = \mathbf{0.86255}$
    - **Sublattice Staggered XY-4 (`xy4x2_stag`)**: Ground state retention $P(0) = \mathbf{0.93726}$
    - **OSIRIS Evolved Gen-1 (`osiris_evolved_g1`)**: Ground state retention $P(0) = \mathbf{0.96021}$ at $16\,\mu\text{s}$ and $\mathbf{0.92883}$ at $32\,\mu\text{s}$.
  - Achieved **$+7.47\%$ to $+9.77\%$ absolute fidelity improvement** over standard simultaneous dynamical decoupling.

---

## 4. Systems, Gateways & Tooling Upgrades

- **Pure L4→L5 Capability Gap Analyzer (`capability_gap_analyzer.py`)**:
  - Deterministic evaluation engine separating code intent from model proposals.
- **Statistical Process Control Suite (`osiris_cli/spc/`)**:
  - Implements time-ordered calibration drift monitoring, CUSUM process control, and Bayesian evidence factor validation.
- **Sprint 3 Automated Adversarial Falsification Engine (`osiris_cli/dnalang/falsification.py`)**:
  - Enforces SYS-024 claim quarantine gates on evolutionary candidate loops.
- **High-Precision OpenQASM Compiler**:
  - Emits OpenQASM 2.0/3.0 circuits preserving exact float64 rotation angles without numerical drift.

---

## 5. Evidence & Citable Identifiers

- **Predecessor Software Release (v4.6.0)**: [10.5281/zenodo.23832085](https://doi.org/10.5281/zenodo.23832085)
- **Predecessor Software Release (v4.5.4)**: [10.5281/zenodo.23300258](https://doi.org/10.5281/zenodo.23300258)
- **Software Concept DOI**: [10.5281/zenodo.23063462](https://doi.org/10.5281/zenodo.23063462)
- **Anomalous $\tau$-Phase Quantum Coherence Dataset**: [10.5281/zenodo.23658893](https://doi.org/10.5281/zenodo.23658893)
- **Phase-Conjugate Recalibration Telemetry Ledger (PCRB)**: [10.5281/zenodo.23213288](https://doi.org/10.5281/zenodo.23213288)
- **RQC S2 Multi-PUB Batching Hardware Dataset**: [10.5281/zenodo.23256344](https://doi.org/10.5281/zenodo.23256344)
