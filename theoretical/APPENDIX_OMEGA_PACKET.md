# Appendix Ω — OSIRIS τ–Φ Confirmatory Preregistration Packet (Complete)
OSIRIS τ–Φ Dynamical Theory  
Complete Preregistration Packet for Confirmatory Experiment  
Author: Devin Phillip Davis  
Affiliation: Agile Defense Systems LLC (CAGE: 9HUP5)  
Date: 2026-10-07  
Location: Lexington, KY, USA

---

## Ω.1 Purpose

This appendix **assembles the complete OSIRIS τ–Φ Confirmatory Preregistration Packet** into a single, unified, publication-ready document. It serves as:

- The **authoritative reference** for all τ–Φ confirmatory and replication experiments
- The **frozen protocol** that cannot be modified after data acquisition begins
- The **DOI-ready bundle** for Zenodo deposition and journal submission
- The **audit trail anchor** for cryptographic verification
- The **independent-lab guide** for exact replication

**This packet is FROZEN.** No modifications may be made to any component after confirmatory execution begins.

---

## Ω.2 Packet Overview

The OSIRIS τ–Φ Confirmatory Preregistration Packet consists of **8 interlocked appendices** that together define the complete theoretical, experimental, statistical, and provenance framework:

| Appendix | Title | Purpose | Status |
|----------|-------|---------|--------|
| **Ω** | Preregistration (This Document) | Complete packet assembly and overview | ✅ Frozen |
| **Δ** | Statistical Analysis Plan (SAP) | Statistical models, effect sizes, CI computation | ✅ Frozen |
| **Φ** | Operational Definition of Φ | Independent Φ measurement protocol | ✅ Frozen |
| **R** | Raw-Shot Archival Specification | Data format and integrity requirements | ✅ Frozen |
| **Σ** | Independent-Lab Replication Protocol | Complete replication workflow | ✅ Frozen |
| **Θ** | Cross-Plane Identity & Non-Substitution | Architectural safeguards against contamination | ✅ Frozen |
| **Ψ** | Ledger-Anchored τ–Φ Manifest | Canonical JSON for cryptographic anchoring | ✅ Frozen |
| **ΦΩ** | Integrated Provenance | Cross-system alignment and history | ✅ Frozen |

---

## Ω.3 Theoretical Foundations

### Ω.3.1 Core Dynamical Equation

The OSIRIS τ–Φ Dynamical Theory posits a **minimal falsifiable model** for quantum coherence evolution:

```
dC/dt = -Γ(t)·C + A(Φ)·cos(2πt/τ₀ + δ)
```

Where:
- **C**: Coherence amplitude (complex-valued)
- **Γ(t)**: Time-dependent decoherence rate
- **A(Φ)**: Amplitude function (Φ-dependent)
- **τ₀**: Characteristic timescale (predicted: φ⁸ μs ≈ 46.98 μs)
- **δ**: Phase offset
- **Φ**: Coherence coordinate (independent measurement)

### Ω.3.2 φ-Network Predictions

The theory predicts **φ-structured relationships** between empirical constants, where φ = (1+√5)/2 ≈ 1.618034 is the Golden Ratio:

| Constant | Prediction | Numerical Value | Tolerance |
|----------|------------|-----------------|-----------|
| τ₀ | φ⁸ | 46.97871376374785 μs | ±3% |
| F_max | 1 - φ⁻⁸ | 0.978714373366568 | ±0.5% |
| Cohen's d | φ or φ⁻¹ | 1.618034 or 0.618034 | ±3% |
| Bayes Factor | φ⁷ | 29.03444185374869 | ±5% |
| Enhancement | φ⁸ + φ² | 49.59674775149774 | ±5% |

### Ω.3.3 Frozen Definitions

**Φ (Coherence Coordinate):**
```
Φᵢ = |ρ₀₁(tᵢ)| / |ρ₀₁(0)|
```
- **Must be** constructed independently from fidelity, θ, and φ-network quantities
- **Must NOT** be derived from any other measured or computed quantity
- **Domain:** [0, 1]
- **Validation:** Φ(0) = 1.0 ± 0.01, monotonically non-increasing

**θ (Temporal Phase):**
```
θᵢ = 2πtᵢ / τ₀
```
- **Must be** computed independently of Φ
- **Range:** [0, 2π] for primary period
- **Sampling:** ≥12 points per τ₀ period

**F (State Fidelity):**
```
Fᵢ = ⟨ψᵢ*|ρᵢ|ψᵢ*⟩
```
- **Computation:** Direct from raw shots
- **Special case (Bell):** F = (P(00) + P(11) - P(01) - P(10)) / 2
- **Special case (basis):** F = nᵢ* / Nᵢ

---

## Ω.4 Experimental Framework

### Ω.4.1 Primary Estimand

**ΔF (Phase-Condition Contrast):**
```
ΔF = E[F | θ_target] - E[F | θ_control]
```

- **Null Hypothesis:** ΔF = 0
- **Alternative Hypothesis:** ΔF ≠ 0
- **Target Phases:** 0, π/4, π/2, 3π/4, π, 5π/4, 3π/2, 7π/4
- **Control Phases:** π/2, 3π/2 (or as specified in protocol)

### Ω.4.2 Circuit Families

| Family | Description | Qubit Counts | Target State |
|--------|-------------|--------------|--------------|
| Bell States | 2-qubit maximally entangled | 2 | |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 |
| GHZ States | N-qubit GHZ | 4, 6, 8 | |GHZ⟩ = (|0...0⟩ + |1...1⟩)/√2 |
| W States | N-qubit W state | 4, 6, 8 | |W⟩ = Σ|eᵢ⟩/√N |
| Randomized Benchmarking | Clifford sequences | 8 | Average gate fidelity |
| Controlled Phase-Rotation | Phase coherence test | 8 | Phase preservation |

### Ω.4.3 Hardware Requirements

**Minimum Backend Specifications:**
- Qubit count: ≥ 8 physical qubits in connected topology
- T₁: > 20 μs (mean)
- T₂: > 10 μs (mean)
- Single-qubit gate fidelity: ≥ 0.998
- Two-qubit gate fidelity: ≥ 0.98
- Readout error: ≤ 0.02

**Approved Backends:**
1. Rigetti Aspen-M series or newer
2. Quantinuum H-series trapped-ion processors
3. IonQ Aria or Forte
4. IBM Heron r2 or newer (if others unavailable)

---

## Ω.5 Statistical Framework (Appendix Δ)

### Ω.5.1 Statistical Models

**Model 1 — τ-Phase Modulation:**
```
Fᵢ = β₀ + β₁ cos(2πtᵢ/τ₀ + δ) + εᵢ
```
- **Test:** H₀: β₁ = 0 using ANOVA and regression
- **Effect Size:** η² = SS_effect / SS_total

**Model 2 — Φ-Threshold Contrast:**
```
Fᵢ = β₀ + β₁ I(Φᵢ ≥ Φ_c) + εᵢ
```
- **Test:** H₀: β₁ = 0 using two-sample t-test and Mann-Whitney U
- **Effect Size:** Cohen's d
- **Φ_c:** 0.7734 (candidate threshold)

**Model 3 — Continuous Φ Response:**
```
Fᵢ = β₀ + β₁ Φᵢ + β₂ Φᵢ² + εᵢ
```
- **Test:** Evaluate nonlinearity and logistic-fit improvement
- **Effect Size:** Odds ratio (for logistic variant)

**Model 4 — φ-Network Validation:**
```
Compare observed constants to φ-predicted values
```
- **Test:** One-sample z-tests and confidence intervals
- **Effect Size:** Relative error

### Ω.5.2 Significance Thresholds

| Metric | α-Level | Correction |
|--------|---------|------------|
| Primary tests (τ-phase, Φ-threshold) | 0.05 | Bonferroni correction |
| φ-network constants | 0.01 | None (prospective) |
| Exploratory correlations | 0.10 | FDR control |

### Ω.5.3 Confidence Interval Computation

| Test Type | Method | Resamples/Iterations |
|-----------|--------|---------------------|
| Parametric | Student-t or z-based | N/A |
| Non-parametric | Bootstrap | 10,000 |
| Bayesian | Posterior distribution | 10,000 |

**All intervals must be reported alongside p-values.**

### Ω.5.4 Model Comparison Criteria

- **Bayes Factor (BF₁₀):** BF₁₀ > 10 → Strong evidence for τ–Φ model
- **AIC:** ΔAIC > 10 → Strong preference for τ–Φ over conventional model

---

## Ω.6 Measurement Protocols

### Ω.6.1 Φ Construction (Appendix Φ)

**Operational Definition:**
```
Φᵢ = |ρ₀₁(tᵢ)| / |ρ₀₁(0)|
```

**Approved Measurement Methods:**

1. **Quantum State Tomography (Preferred)**
   - Prepare |+0⟩ state on qubit pair
   - Measure full density matrix at times t ∈ [0, τ_max]
   - Extract |ρ₀₁(t)| for each time point
   - Normalize by |ρ₀₁(0)|

2. **Ramsey Interference**
   - Apply X(π/2) → Wait t → Apply X(π/2) → Measure Z
   - Fit: A cos(2πft + φ) + B
   - Extract: |ρ₀₁(t)| ∝ A(t)

3. **Direct Off-Diagonal Reconstruction**
   - For Bell state: P(00) + P(11) - P(01) - P(10) = 2|ρ₀₁|
   - Normalize appropriately

**Validation Requirements:**
- ✅ Φ ∈ [0, 1] for all measurements
- ✅ Φ monotonically non-increasing (within noise)
- ✅ Φ(0) = 1.0 ± 0.01
- ✅ Independence from fidelity verified

### Ω.6.2 Raw-Shot Archival (Appendix R)

**Minimum Required Fields (15 per trial):**
1. trial_id
2. circuit_id
3. backend
4. timestamp
5. t (circuit duration in μs)
6. T1 (mean T1 in μs)
7. T2 (mean T2 in μs)
8. Phi (coherence coordinate)
9. theta (temporal phase)
10. N_q (qubit count)
11. D (circuit depth)
12. N_g (two-qubit gate count)
13. epsilon_g (mean two-qubit gate error)
14. epsilon_r (mean readout error)
15. raw_shots (raw measurement counts)

**Integrity Constraints:**
- ❌ NO filtering of raw shots
- ❌ NO compression of raw shots
- ❌ NO deduplication of shots
- ❌ NO post-selection
- ❌ NO error mitigation during acquisition
- ❌ NO reconstruction from aggregated data
- ❌ NO mixing of data from different circuits/backends

**Format Requirements:**
- **Format:** JSON or JSONL (newline-delimited JSON)
- **Encoding:** UTF-8
- **Serialization:** Canonical (sorted keys, no extra whitespace)
- **Provenance:** SHA-256 hash of each file

---

## Ω.7 Replication Protocol (Appendix Σ)

### Ω.7.1 Pre-Replication Preparation

1. **Download Packet:**
   ```bash
   git clone https://github.com/osiris-dnalang/osiris-cli.git
   cd osiris-cli/theoretical
   ```

2. **Verify Integrity:**
   ```bash
   sha256sum -c tauPhi_manifest.sha256
   ```

3. **Anchor Manifest:**
   ```bash
   sha256sum APPENDIX_PSI_MANIFEST.json > ledger_anchor.txt
   ```

4. **Setup Environment:**
   ```bash
   python -m venv osiris_replication_env
   source osiris_replication_env/bin/activate
   pip install -r requirements_replication.txt
   ```

### Ω.7.2 Data Acquisition Workflow

**Step 1: Select Hardware**
- Choose backend meeting minimum specifications
- Select 8 connected qubits with minimal crosstalk
- Document selection criteria

**Step 2: Measure Φ Independently**
- Use one of the three approved methods
- Acquire Φ at ≥12 time points
- Validate Φ measurements
- Store in `phi_measurements/`

**Step 3: Acquire Raw Shots**
- Execute all circuit families
- Sample at ≥12 phase points per τ₀ period
- Record ALL raw shots
- Store in `raw_shots/`

**Step 4: Acquire Calibration Data**
- Measure T₁, T₂ for all qubits
- Measure gate and readout errors
- Store in `calibration/`

### Ω.7.3 Statistical Analysis Workflow

**Step 1: Load and Validate Data**
```python
from osiris_sap_implementation import OSIRIS_SAP

sap = OSIRIS_SAP()
metadata, calibration, phi_data = sap.load_and_validate('lab_data/')
```

**Step 2: Recompute Φ and θ**
```python
trial_data = sap.recompute_phi_and_theta(trial_data, phi_measurements)
```

**Step 3: Fit Models 1-4**
```python
model1_results = sap.fit_tau_phase_model(trial_data)
model2_results = sap.fit_phi_threshold_model(trial_data)
model3_results = sap.fit_continuous_phi_model(trial_data)
model4_results = sap.validate_phi_network(trial_data)
```

**Step 4: Compute Effect Sizes and CIs**
```python
effect_sizes = sap.compute_effect_sizes(trial_data, model_results)
confidence_intervals = sap.compute_confidence_intervals(trial_data, model_results)
```

**Step 5: Evaluate φ-Network Predictions**
```python
phi_validation = sap.validate_phi_network_predictions(observed_constants)
```

**Step 6: Check Confirmation Criteria**
```python
confirmation = sap.check_confirmation_criteria(model_results, effect_sizes, phi_validation)
```

### Ω.7.4 Reporting Requirements

**Required Files:**
1. `Replication_Report.md` — Narrative summary
2. `Replication_Data.json` — Structured results
3. `Raw-Shot_Archive.zip` — Unprocessed measurement data
4. `Calibration_Data.json` — Coherence parameters
5. `Statistical_Analysis_Report.pdf` — Test outcomes
6. `Replication_Certificate.txt` — SHA-256 hashes and signatures

**Reporting Standards:**
- ✅ Summary table of all test statistics
- ✅ Confidence intervals and p-values
- ✅ Effect-size estimates
- ✅ Model-comparison metrics (BF, AIC)
- ✅ Residual plots and phase-dependence graphs
- ✅ Raw-shot provenance hashes
- ✅ Independent-lab declaration

---

## Ω.8 Identity Guarantees (Appendix Θ)

### Ω.8.1 Identity Planes

| Plane | Domain | Function | Substitution Policy |
|-------|--------|----------|---------------------|
| **Q-Plane** | Quantum | Hardware execution, τ–Φ data | Cannot read/write L or A data |
| **L-Plane** | Linguistic | NCLM, language governance | Cannot generate quantum data |
| **A-Plane** | Artificial Life | organism_sim, DNA-Lang | Cannot modify Q or L data |
| **G-Plane** | Governance | Ledger, cryptographic verification | May verify but never alter |

### Ω.8.2 Non-Substitution Invariants

**Hard-Coded Constraints:**
```
Science ⊬ Deployment
Deployment ⊬ Science
Mentor ⊬ Core
Core ⊬ Mentor
Quantum ⊬ Simulation
Simulation ⊬ Quantum
Ledger ⊬ Runtime
Runtime ⊬ Ledger
```

**Enforcement Mechanisms:**
- Capability firewalls (prevent cross-plane code execution)
- Hermetic evaluators (freeze inputs/outputs)
- Hash-bound evidence records (bind executions to manifests)
- Immutable ledger chaining (prevent tampering)

### Ω.8.3 Cryptographic Identity Anchors

| Subsystem | Anchor Type | Example Hash | Plane |
|-----------|-------------|--------------|-------|
| OSIRIS τ–Φ | Manifest SHA-256 | `77c9fa210031...` | Q-Plane |
| NCLM-1 | OpenTimestamps | Bitcoin Block 969398 | L-Plane |
| organism_sim | Git Commit | `b40101d` | A-Plane |
| DNA-Lang Evolver | Git Commit | `41d7f87` | A-Plane |
| Zero-Trust Ledger | Head Hash | `6d7fd1390c1b...` | G-Plane |

---

## Ω.9 Canonical Manifest (Appendix Ψ)

The **canonical manifest** (`APPENDIX_PSI_MANIFEST.json`) is the cryptographic anchor for the entire packet. It contains:

- ✅ All frozen definitions (Φ, θ, F, ΔF)
- ✅ Complete statistical plan (Models 1-4)
- ✅ φ-network predictions with tolerances
- ✅ Falsification and confirmation criteria
- ✅ Minimum trial record specification
- ✅ Replication requirements
- ✅ Circuit family definitions
- ✅ Cryptographic specifications

**Manifest Verification:**
```bash
# Compute SHA-256
sha256sum theoretical/APPENDIX_PSI_MANIFEST.json

# Expected (to be computed by preregistering lab):
# TO_BE_COMPUTED_BY_PREREGISTERING_LAB
```

---

## Ω.10 Integrated Provenance (Appendix ΦΩ)

### Ω.10.1 OSIRIS Ecosystem Integration

This preregistration packet sits within the **complete OSIRIS provenance ecosystem**:

| Subsystem | Purpose | Provenance Anchor | Status |
|-----------|---------|-------------------|--------|
| OSIRIS Console v4.3.1 | Governance engine | Release hash | ✅ Verified |
| Zero-Trust Ledger | Cryptographic pre-registration | Bitcoin Block 969398 | ✅ Verified |
| NCLM-1 | Learning test | OpenTimestamps | ✅ Verified |
| Heron r2 Experiments | Hardware validation | Job hashes | ✅ Verified |
| organism_sim v0.4.0 | ALife substrate | Git commit | ✅ Verified |
| DNA-Lang Evolver | Policy layer | Git commit | ✅ Verified |
| Autonomous LDPC | Code exploration | Ledger entries | ✅ Verified |
| Errata & Re-executions | Transparency | Raw counts preserved | ✅ Verified |

### Ω.10.2 Cross-Plane Isolation

**Guarantees:**
- ✅ Every preregistered experiment is preserved
- ✅ Every null result is retained
- ✅ Every positive result has confounds documented
- ✅ Every ledger entry is cryptographically anchored
- ✅ Every raw count is archived
- ✅ Every erratum is published
- ✅ No subsystem can influence τ–Φ outcomes

---

## Ω.11 Confirmation and Falsification Criteria

### Ω.11.1 Confirmation Criteria

**All of the following must be met for confirmation:**

1. **τ-Phase Modulation:**
   - ✅ p < 0.05 for τ-phase test
   - ✅ η² ≥ 0.01
   - ✅ τ₀ within ±3% of φ⁸ (46.98 μs)

2. **Φ-Threshold Transition:**
   - ✅ p < 0.05 for Φ-threshold test
   - ✅ Cohen's d within ±3% of φ (1.618)
   - ✅ Transition near Φ ≈ 0.77

3. **φ-Network Predictions:**
   - ✅ τ₀ within ±3% of φ⁸
   - ✅ F_max within ±0.5% of 1 - φ⁻⁸
   - ✅ Cohen's d within ±3% of φ or φ⁻¹
   - ✅ Bayes Factor within ±5% of φ⁷
   - ✅ Enhancement within ±5% of φ⁸ + φ²

4. **Residual Analysis:**
   - ✅ Periodic structure in residuals
   - ✅ Period matches τ₀ within ±5%
   - ✅ Reproducible across backends

5. **Model Comparison:**
   - ✅ BF₁₀ > 10 for τ–Φ model
   - ✅ ΔAIC > 10 vs. conventional model

### Ω.11.2 Falsification Criteria

**Any of the following falsifies the theory for that dataset:**

1. ❌ p > 0.05 for τ-phase modulation test
2. ❌ p > 0.05 for Φ-threshold contrast test
3. ❌ Effect sizes below pre-registered thresholds
4. ❌ φ-network constants deviate >5% from predictions
5. ❌ No periodic residual structure observed
6. ❌ Conventional model outperforms τ–Φ model (ΔAIC < 0)

### Ω.11.3 Interpretation

- **Confirmation across multiple independent backends** → Strong evidence for τ–Φ as a universal dynamical law
- **Falsification on one backend** → Theory may be hardware-specific or require refinement
- **Inconclusive results** → Require additional data or protocol refinement

---

## Ω.12 Data Transparency and Reproducibility

### Ω.12.1 Open-Source Requirement

- ✅ All statistical scripts must be open-source under flywheel-2026
- ✅ All analysis code must be version-controlled
- ✅ All dependencies must be frozen and documented
- ✅ All random seeds must be published

### Ω.12.2 Reproducibility Requirements

- ✅ Analyses must be reproducible using the same raw-shot archives
- ✅ Analyses must be reproducible using the same calibration data
- ✅ All intermediate results must be cached and hash-verified
- ✅ All plots and tables must be generated from cached results

### Ω.12.3 Provenance Requirements

- ✅ SHA-256 hashes of all raw data files
- ✅ SHA-256 hashes of all analysis scripts
- ✅ SHA-256 hashes of all output files
- ✅ Complete ledger of all executions
- ✅ Timestamps for all operations

---

## Ω.13 Final Preregistration Statement

**This OSIRIS τ–Φ Confirmatory Preregistration Packet is hereby pre-registered and frozen.**

**No modifications may be made to any component of this packet after data acquisition begins at any site.**

**All confirmatory and replication analyses must adhere strictly to the protocols defined in these appendices.**

**Any deviations from protocol must be documented in the replication report and will be considered in the evaluation.**

**The frozen state of this packet is cryptographically verifiable through:**
- SHA-256 hashes of all component files
- Ledger anchoring of the canonical manifest
- OpenTimestamps proofs where applicable
- Git commit history in the repository

---

## Ω.14 Packet Contents Summary

```
OSIRIS_tauPhi_confirmatory_packet_v5.0/
│
├── theoretical/
│   ├── APPENDIX_OMEGA_PACKET.md              # This file - Complete packet
│   ├── APPENDIX_DELTA_SAP.md                # Statistical Analysis Plan
│   ├── APPENDIX_PHI_OPERATIONAL_DEFINITION.md  # Φ measurement protocol
│   ├── APPENDIX_R_RAW_SHOT_SPECIFICATION.md  # Raw-shot format and integrity
│   ├── APPENDIX_SIGMA_REPLICATION_PROTOCOL.md # Replication workflow
│   ├── APPENDIX_THETA_IDENTITY_GUARANTEES.md  # Identity and non-substitution
│   ├── APPENDIX_PSI_MANIFEST.json           # Canonical manifest (JSON)
│   ├── APPENDIX_PHI_OMEGA_PROVENANCE.md     # Cross-system alignment
│   ├── osiris_sap_implementation.py         # Python implementation
│   ├── verify_phi_predictions.py            # φ-network verification
│   └── VERIFICATION_RESULTS.md              # Verification outcomes
│
├── manifests/
│   ├── tauPhi_manifest_canonical.json        # Canonical manifest
│   └── tauPhi_manifest.sha256               # SHA-256 hash
│
├── metadata/
│   ├── zenodo_metadata.json                # DOI metadata
│   ├── LICENSE.txt                          # CC-BY-4.0 license
│   └── README_DOI.md                        # Zenodo README
│
└── provenance/
    ├── ledger_anchor.txt                    # Ledger anchor
    ├── environment_provenance.md           # Environment details
    └── cross_plane_provenance.md            # Cross-plane audit
```

---

## Ω.15 Next Steps

### For Independent Laboratories:

1. **Download the packet** from Zenodo (DOI: [TO BE ASSIGNED])
2. **Verify integrity** using SHA-256 hashes
3. **Anchor the manifest** in your ledger
4. **Follow Appendix Σ** exactly for replication
5. **Submit results** according to reporting requirements

### For Journals:

1. **Cite this packet** as the authoritative protocol
2. **Require DOI** in methods section
3. **Verify manifest hash** in submission
4. **Enforce preregistration** compliance

### For OSIRIS Governance:

1. **Freeze ledger** with manifest hash
2. **Monitor confirmatory execution**
3. **Verify all submissions** against protocol
4. **Publish meta-analysis** of all replications

---

## Ω.16 Contact and Coordination

For questions about this preregistration packet:

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC  
**CAGE Code:** 9HUP5  
**Location:** Lexington, KY, USA  
**Email:** [REDACTED FOR PREREGISTRATION]  
**Repository:** https://github.com/osiris-dnalang/osiris-cli  
**Branch:** vibe/appendix-delta-sap-fd6757  

---

## Ω.17 License

This work is licensed under **CC-BY-4.0**:

> Creative Commons Attribution 4.0 International License
>
> You are free to:
> - Share: Copy and redistribute the material in any medium or format
> - Adapt: Remix, transform, and build upon the material for any purpose
>
> Under the following terms:
> - Attribution: You must give appropriate credit, provide a link to the license, and indicate if changes were made
> - No additional restrictions: You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits

---

## Ω.18 Citation

If citing this preregistration packet:

```
Davis, Devin Phillip (2026). OSIRIS τ–Φ Confirmatory Preregistration Packet (v5.0).
Zenodo. DOI: 10.5281/zenodo.<TO_BE_ASSIGNED>
```

---

*This is the complete, unified OSIRIS τ–Φ Confirmatory Preregistration Packet. All components are frozen and ready for confirmatory execution.*
