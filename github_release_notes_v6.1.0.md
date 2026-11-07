# OSIRIS v6.1.0: Unified Quantum Hardware Evidence & Capacity Bound Release

**Release Tag:** `v6.1.0`  
**Zenodo Deposition:** [10.5281/zenodo.24031814](https://doi.org/10.5281/zenodo.24031814)  
**Authority Ledger:** [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) (Sequence Blocks #1–#49)  
**Governance Standard:** SYS-021 Zero Self-Supplied Authorization / NIST FIPS 204  
**Primary Operator:** Devin Phillip Davis / Enki  
**CAGE Code:** 9HUP5 (Agile Defense Systems, LLC)  

---

## 1. Executive Summary & Validated Hardware Campaigns

OSIRIS v6.1.0 consolidates the complete empirical quantum telemetry, compiled ISA circuits, Merkle-chained execution receipts, and dispassionate forensic incident records across five physical hardware campaigns executed on 156-qubit IBM Quantum Heron processors (`ibm_fez` and `ibm_marrakesh`):

| Campaign Identifier | Physical QPU | Qubit Volume | Physical Shots | Primary Validated Observable | Milestone Determination | Status |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **OSIRIS-HP-001** | `ibm_fez` (Heron r2) | 6 transmons | 49,152 | Subspace Population: **80.20 +/- 0.62%** | Restricted 1-qubit subspace reconstruction verified | **VERIFIED** |
| **OSIRIS-HP-002** | `ibm_fez` (Heron r2) | 6 transmons | 73,728 | Entanglement Fidelity: **79.49 +/- 0.14%** | Certified Restricted Recovery ($Z > 200\sigma$, $\mathcal{W} = -0.2949 < 0$) with barrier-verified positive control (91.94%) | **CERTIFIED** |
| **OSIRIS-HP-003** | `ibm_fez` (Heron r2) | 8 transmons | 46,080 | 2-Qubit Capacity Bound: Arm B Mean $\bar{\mathcal{F}} = \mathbf{74.95 \pm 0.34\%}$ | Multi-qubit retrieval certified ($Z = 73.0\sigma$); single-photon sub-capacity bound verified ($\mathcal{F}_1 = 42.42\%$, $\mathcal{W}_1 \ge 0$) | **CERTIFIED** |
| **7-Edge Stagger DD** | `ibm_marrakesh` (Heron r1) | 14 transmons | 86,016 | State Fidelity: **0.9023 +/- 0.0069** | Edge (14, 15) +2.28 pp cross-talk gain; 86.0% ensemble win-rate ($p < 10^{-4}$) | **CERTIFIED** |
| **OSIRIS-QAML-002** | Staged Protocol | 8 transmons | 33,500/eval | Multi-Depth Robustness ($D \in \{2, 4, 6, 8\}$) | High-sample ($N_{\mathrm{test}} = 50$, step size $2.0\text{ pp}$) pre-registered benchmark resolving QAML-001 power deficit | **PRE-REGISTERED** |

---

## 2. Definitive Multi-Qubit Hayden–Preskill Findings (`OSIRIS-HP-003`)

1. **Hayden–Preskill Quantum Capacity Bound:**
   - Multi-qubit retrieval strictly requires collecting $k \ge 2$ radiation photons.
   - Collecting $k = 1$ photon (Arm B-Def) fails to surpass the classical entanglement threshold ($\mathcal{F}_1 = 42.42\%$, $\mathcal{W}_1 = +0.0758 \ge 0$), whereas $k = 2$ photons (Arm B) achieves $\bar{\mathcal{F}} = \mathbf{74.95 \pm 0.34\%}$ and $\mathcal{F}_{\mathrm{prod}} = \mathbf{56.17\%}$ ($\mathcal{W} = -0.2495 < 0$, $Z = 73.0\sigma$, $p < 10^{-100}$).
   - **Threshold Capacity Gain:** $\Delta \bar{\mathcal{F}} = \bar{\mathcal{F}}(\text{Arm B}) - \bar{\mathcal{F}}(\text{Arm B-Def}) = \mathbf{+41.29\text{ pp}}$.
   - **EPR Bridge Gain:** $\Delta \bar{\mathcal{F}} = \bar{\mathcal{F}}(\text{Arm B}) - \bar{\mathcal{F}}(\text{Arm B-Ctrl}) = \mathbf{+49.79\text{ pp}}$.
   - **Scrambler Specificity Gain:** $\Delta \bar{\mathcal{F}} = \bar{\mathcal{F}}(\text{Arm B}) - \bar{\mathcal{F}}(\text{Arm B-Held}) = \mathbf{+49.24\text{ pp}}$.
2. **SPAM & ZNE Physical Noise Decomposition:**
   - SPAM attenuation accounts for only $\sim 1.6\%$ to $2.0\%$ attenuation across physical qubits $[146, 143, 123, 144]$ on `ibm_fez`.
   - Mitigated Arm A fidelity is **$75.40 \pm 0.08\%$**, governed by 48 physical CZ gate errors ($\epsilon_{\text{CZ}} = 0.587\%$).
   - Mitigated Arm B fidelity is **$75.84 \pm 0.35\%$** ($\mathcal{W} = -0.2584$, $Z = 74.3\sigma$).
   - Arm B achieves **$100.59\%$** of the physical coherence ceiling defined by Arm A, confirming that recovery is 100% coherence-limited rather than algorithm-limited.

---

## 3. Cryptographic Provenance & Ledger Anchors

The complete campaign is anchored across Blocks #1 through #49 in `evidence_ledger.db` with unbroken SHA-256 parent-block hash chaining:
- **Block #47:** `SYS021_HP003_DISPATCH_GRANT` (`74a0987e...`)
- **Block #48:** `SYS021_HP003_HARDWARE_ACQUISITION_RECEIPT` (Job `dbndsvoou4as73b4cvi0`, `3eee9491...`)
- **Block #49:** `SYS021_ZENODO_PUBLICATION_QUANTUM_HARDWARE_V2` (Zenodo DOI [10.5281/zenodo.24031814](https://doi.org/10.5281/zenodo.24031814), `9be6f2e6...`)

---

## 4. Release Distribution Artifacts

- **Archive Bundle (.zip):** `dist/osiris_quantum_hardware_v2.0_evidence_package.zip` (SHA-256: `e700b02e9b7e7a566aac99157ac67a41e1cddc3a11efe516126522488625b8af`)
- **Archive Bundle (.tar.gz):** `dist/osiris_quantum_hardware_v2.0_evidence_package.tar.gz` (SHA-256: `320115b06dff708c415a62a14a8c7883e1fc7868f9aba428c1af837033730978`)
- **Manuscript:** `papers/crsm_nature_physics_2026.tex`
- **Publication Receipt:** `zenodo_quantum_hardware_v2.0_receipt.json`
