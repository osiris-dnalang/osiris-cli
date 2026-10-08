# OSIRIS τ–Φ Confirmatory Preregistration Packet (v5.0)

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC (CAGE: 9HUP5)  
**Date:** 2026-10-07  
**Version:** v5.0-confirmatory  
**License:** CC-BY-4.0  
**DOI:** [To be assigned by Zenodo after upload]

---

## Overview

This archive contains the **complete preregistration packet** for the OSIRIS τ–Φ Dynamical Theory Confirmatory Experiment. It includes all frozen definitions, statistical plans, replication protocols, provenance guarantees, and the canonical manifest intended for cryptographic anchoring.

The packet is designed for:
- ✅ Independent laboratory replication
- ✅ Journal peer-review
- ✅ Long-term archival
- ✅ Zero-trust scientific verification
- ✅ Ledger-anchored preregistration

**All components are frozen prior to confirmatory execution.**

---

## Contents

```
OSIRIS_tauPhi_confirmatory_packet_v5.0/
├── theoretical/                          # Core theory documents
│   ├── APPENDIX_OMEGA_PACKET.md         # Complete packet assembly
│   ├── APPENDIX_DELTA_SAP.md           # Statistical Analysis Plan
│   ├── APPENDIX_PHI_OPERATIONAL_DEFINITION.md  # Φ measurement protocol
│   ├── APPENDIX_R_RAW_SHOT_SPECIFICATION.md  # Raw-shot archival spec
│   ├── APPENDIX_SIGMA_REPLICATION_PROTOCOL.md # Replication workflow
│   ├── APPENDIX_THETA_IDENTITY_GUARANTEES.md  # Identity & non-substitution
│   ├── APPENDIX_PSI_MANIFEST.json       # Canonical manifest (JSON)
│   ├── APPENDIX_PHI_OMEGA_PROVENANCE.md # Cross-system alignment
│   ├── osiris_sap_implementation.py      # Python implementation
│   ├── verify_phi_predictions.py        # φ-network verification
│   └── VERIFICATION_RESULTS.md          # Verification outcomes
│
├── manifests/                          # Manifest files
│   ├── tauPhi_manifest_canonical.json   # Canonical JSON manifest
│   └── tauPhi_manifest.sha256          # SHA-256 hash
│
├── metadata/                           # Metadata files
│   ├── zenodo_metadata.json           # DOI metadata
│   ├── LICENSE.txt                     # CC-BY-4.0 license
│   └── README_DOI.md                   # This file
│
└── provenance/                         # Provenance records
    ├── ledger_anchor.txt               # Ledger anchor
    ├── environment_provenance.md      # Environment details
    └── cross_plane_provenance.md       # Cross-plane audit
```

---

## Purpose of the Packet

This preregistration packet defines the complete framework for the OSIRIS τ–Φ Dynamical Theory:

### 1. The Dynamical Theory (Frozen)
- **Minimal falsifiable model:** dC/dt = -Γ(t)C + A(Φ)cos(2πt/τ₀ + δ)
- **Independently measured Φ:** Coherence coordinate from off-diagonal density matrix elements
- **Independently defined θ:** Temporal phase 2πt/τ₀
- **Candidate φ-structured timescale:** τ₀ ≈ φ⁸ μs ≈ 46.98 μs

### 2. The Confirmatory Experiment
- **Primary endpoint:** State fidelity Fᵢ = ⟨ψᵢ*|ρᵢ|ψᵢ*⟩
- **Primary estimand:** ΔF = E[F | θ_target] - E[F | θ_control]
- **Raw-shot archival:** Complete, unfiltered, uncompressed
- **Statistical analysis:** Pre-registered models and tests
- **Falsification criteria:** Objective, pre-specified thresholds
- **φ-network predictions:** Prospective validation

### 3. Replication Protocol
- **Complete independent-lab protocol** specifying:
  - Hardware requirements (T₁ > 20μs, T₂ > 10μs, gate fidelity ≥ 0.98)
  - Calibration workflow
  - Phase sampling (≥12 points per τ₀ period)
  - Shot counts (≥10,000 per circuit)
  - Statistical tests (ANOVA, t-test, Mann-Whitney U)
  - Reporting format
  - Success/failure criteria

### 4. Provenance & Identity Guarantees
- **Cross-plane identity invariants** (Q, L, A, G planes)
- **Non-substitution guarantees** (Science ⊬ Deployment, etc.)
- **Cryptographic anchoring** (SHA-256, ledger chaining)
- **Ledger-ready manifest** for cryptographic registration

---

## Theoretical Foundations

### Core Equation
```
dC/dt = -Γ(t)·C + A(Φ)·cos(2πt/τ₀ + δ)
```

### φ-Network Predictions
| Constant | Prediction | Value | Tolerance |
|----------|------------|-------|-----------|
| τ₀ | φ⁸ | 46.9787 μs | ±3% |
| F_max | 1 - φ⁻⁸ | 0.978714 | ±0.5% |
| Cohen's d | φ or φ⁻¹ | 1.618034 or 0.618034 | ±3% |
| Bayes Factor | φ⁷ | 29.034442 | ±5% |
| Enhancement | φ⁸ + φ² | 49.596748 | ±5% |

### Frozen Definitions
- **Φᵢ = |ρ₀₁(tᵢ)| / |ρ₀₁(0)|** (independent measurement)
- **θᵢ = 2πtᵢ / τ₀** (independent of Φ)
- **Fᵢ = ⟨ψᵢ*|ρᵢ|ψᵢ*⟩** (direct from raw shots)

---

## Quick Start Guide

### For Independent Laboratories

1. **Download the packet:**
   ```bash
   git clone https://github.com/osiris-dnalang/osiris-cli.git
   cd osiris-cli
   ```

2. **Verify integrity:**
   ```bash
   cd theoretical
   sha256sum -c ../manifests/tauPhi_manifest.sha256
   ```

3. **Anchor the manifest:**
   ```bash
   sha256sum APPENDIX_PSI_MANIFEST.json > ../provenance/ledger_anchor.txt
   ```

4. **Set up environment:**
   ```bash
   python -m venv osiris_replication_env
   source osiris_replication_env/bin/activate
   pip install -r requirements_replication.txt
   ```

5. **Follow the replication protocol:**
   - Read `APPENDIX_SIGMA_REPLICATION_PROTOCOL.md`
   - Implement all procedures exactly as specified
   - Submit results according to reporting requirements

### For Verification

1. **Compute manifest hash:**
   ```bash
   sha256sum theoretical/APPENDIX_PSI_MANIFEST.json
   ```

2. **Verify all component hashes:**
   ```bash
   for file in theoretical/APPENDIX_*.md theoretical/APPENDIX_*.json; do
     sha256sum "$file"
   done
   ```

3. **Check against published hashes** in `manifests/tauPhi_manifest.sha256`

---

## File Descriptions

### Theory Documents (`theoretical/`)

| File | Description | Size | Purpose |
|------|-------------|------|---------|
| `APPENDIX_OMEGA_PACKET.md` | Complete packet assembly | ~22 KB | Master document |
| `APPENDIX_DELTA_SAP.md` | Statistical Analysis Plan | ~17 KB | Models, effect sizes, CIs |
| `APPENDIX_PHI_OPERATIONAL_DEFINITION.md` | Φ measurement protocol | ~18 KB | Independent Φ construction |
| `APPENDIX_R_RAW_SHOT_SPECIFICATION.md` | Raw-shot archival spec | ~26 KB | Data format requirements |
| `APPENDIX_SIGMA_REPLICATION_PROTOCOL.md` | Replication workflow | ~27 KB | Independent-lab protocol |
| `APPENDIX_THETA_IDENTITY_GUARANTEES.md` | Identity & non-substitution | ~32 KB | Architectural safeguards |
| `APPENDIX_PSI_MANIFEST.json` | Canonical manifest | ~21 KB | Cryptographic anchoring |
| `APPENDIX_PHI_OMEGA_PROVENANCE.md` | Cross-system alignment | ~18 KB | OSIRIS ecosystem integration |

### Implementation Files (`theoretical/`)

| File | Description | Size | Purpose |
|------|-------------|------|---------|
| `osiris_sap_implementation.py` | Full Python implementation | ~53 KB | Models 1-4 fitting |
| `verify_phi_predictions.py` | φ-network verification | ~12 KB | Predictions validation |
| `VERIFICATION_RESULTS.md` | Verification outcomes | ~5 KB | φ-network checks |

### Manifest Files (`manifests/`)

| File | Description | Purpose |
|------|-------------|---------|
| `tauPhi_manifest_canonical.json` | Canonical JSON manifest | Cryptographic anchoring |
| `tauPhi_manifest.sha256` | SHA-256 hash | Verification |

### Metadata Files (`metadata/`)

| File | Description | Purpose |
|------|-------------|---------|
| `zenodo_metadata.json` | DOI metadata | Zenodo deposition |
| `LICENSE.txt` | CC-BY-4.0 license | Legal |
| `README_DOI.md` | This file | Documentation |

### Provenance Files (`provenance/`)

| File | Description | Purpose |
|------|-------------|---------|
| `ledger_anchor.txt` | Ledger anchor hash | Cryptographic proof |
| `environment_provenance.md` | Environment details | Reproducibility |
| `cross_plane_provenance.md` | Cross-plane audit | Identity verification |

---

## Statistical Framework

### Models (Appendix Δ)

1. **Model 1 — τ-Phase Modulation:**
   - Fᵢ = β₀ + β₁ cos(2πtᵢ/τ₀ + δ) + εᵢ
   - Test: H₀: β₁ = 0 (ANOVA, regression)
   - Effect size: η²

2. **Model 2 — Φ-Threshold Contrast:**
   - Fᵢ = β₀ + β₁ I(Φᵢ ≥ Φ_c) + εᵢ
   - Test: H₀: β₁ = 0 (t-test, Mann-Whitney U)
   - Effect size: Cohen's d

3. **Model 3 — Continuous Φ Response:**
   - Fᵢ = β₀ + β₁ Φᵢ + β₂ Φᵢ² + εᵢ
   - Test: Nonlinearity evaluation
   - Effect size: Odds ratio

4. **Model 4 — φ-Network Validation:**
   - Compare observed to φ-predicted
   - Test: One-sample z-tests
   - Effect size: Relative error

### Significance Thresholds

| Metric | α-Level | Correction |
|--------|---------|------------|
| Primary tests | 0.05 | Bonferroni |
| φ-network | 0.01 | None |
| Exploratory | 0.10 | FDR |

### Confidence Intervals
- Parametric: Student-t or z-based
- Non-parametric: Bootstrap (10,000 resamples)
- Bayesian: 95% credible intervals

---

## Replication Requirements

### Hardware
- **Backend:** Non-IBM preferred (Rigetti, Quantinuum, IonQ)
- **Qubits:** ≥ 8 connected
- **T₁:** > 20 μs (mean)
- **T₂:** > 10 μs (mean)
- **Gate fidelity (1Q):** ≥ 0.998
- **Gate fidelity (2Q):** ≥ 0.98
- **Readout error:** ≤ 0.02

### Data Acquisition
- **Phase sampling:** ≥ 12 points per τ₀ period
- **Shot count:** ≥ 10,000 per circuit
- **Calibration:** Before each session
- **Ledger anchoring:** Required

### Circuit Families
1. Bell states (2 qubits)
2. GHZ states (4, 6, 8 qubits)
3. W states (4, 6, 8 qubits)
4. Randomized benchmarking (8 qubits)
5. Controlled phase-rotation (8 qubits)

---

## Confirmation and Falsification

### Confirmation Criteria (ALL must be met)
- ✅ p < 0.05 for τ-phase test
- ✅ p < 0.05 for Φ-threshold test
- ✅ τ₀ within ±3% of φ⁸
- ✅ F_max within ±0.5% of 1 - φ⁻⁸
- ✅ Cohen's d within ±3% of φ
- ✅ Bayes Factor within ±5% of φ⁷
- ✅ Periodic residuals
- ✅ BF₁₀ > 10
- ✅ ΔAIC > 10

### Falsification Criteria (ANY one falsifies)
- ❌ p > 0.05 for τ-phase test
- ❌ p > 0.05 for Φ-threshold test
- ❌ Effect sizes below thresholds
- ❌ φ-network constants >5% deviation
- ❌ No periodic residuals
- ❌ Conventional model outperforms (ΔAIC < 0)

---

## Verification

### Compute Packet Hash
```bash
cd OSIRIS_tauPhi_confirmatory_packet_v5.0
find . -type f -exec sha256sum {} \; | sort > complete_packet.sha256
```

### Verify Individual Files
```bash
# Check manifest
sha256sum theoretical/APPENDIX_PSI_MANIFEST.json

# Check all appendices
for f in theoretical/APPENDIX_*.md theoretical/APPENDIX_*.json; do
  echo "$f:"
  sha256sum "$f"
done
```

### Verify Against Published Hashes
```bash
sha256sum -c manifests/tauPhi_manifest.sha256
```

---

## Usage

### For Independent Labs
1. Follow `APPENDIX_SIGMA_REPLICATION_PROTOCOL.md` exactly
2. Use `APPENDIX_R_RAW_SHOT_SPECIFICATION.md` for data archival
3. Use `APPENDIX_DELTA_SAP.md` for statistical analysis
4. Use `APPENDIX_PSI_MANIFEST.json` for manifest anchoring

### For Journals
1. Cite this preregistration packet
2. Include DOI and manifest hash in methods
3. Require adherence to protocol

### For OSIRIS Governance
1. Anchor manifest in write-ahead ledger
2. Freeze preregistration state
3. Begin confirmatory execution only after anchoring

---

## License

**CC-BY-4.0**: Creative Commons Attribution 4.0 International License

You are free to:
- Share: Copy and redistribute in any medium or format
- Adapt: Remix, transform, and build upon for any purpose

Under the following terms:
- Attribution: Give appropriate credit, provide license link, indicate changes
- No additional restrictions: May not apply legal/technological restrictions

---

## Citation

```
Davis, Devin Phillip (2026). OSIRIS τ–Φ Confirmatory Preregistration Packet (v5.0).
Zenodo. DOI: 10.5281/zenodo.<TO_BE_ASSIGNED>
```

---

## Contact

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC  
**CAGE Code:** 9HUP5  
**Location:** Lexington, KY, USA  
**Repository:** https://github.com/osiris-dnalang/osiris-cli  
**Branch:** vibe/appendix-delta-sap-fd6757  

---

## Status

**✅ ALL COMPONENTS FROZEN**  
**✅ READY FOR ZENODO DEPOSITION**  
**✅ READY FOR PEER REVIEW**  
**✅ READY FOR INDEPENDENT REPLICATION**

---

*This README is part of the OSIRIS τ–Φ Confirmatory Preregistration Packet v5.0. For complete details, see `theoretical/APPENDIX_OMEGA_PACKET.md`.*
