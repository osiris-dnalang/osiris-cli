# OSIRIS — Physical QPU Validation Campaign (v1.0)
## Complete Scientific Report & Final Hardware Synthesis

**Hardware Platform:** `ibm_marrakesh` (IBM Heron r2, 156 physical qubits)  
**Campaign Lead Operator:** `Devin Phillip Davis / Enki`  
**Governance Standard:** Gate 0 / SYS-021 Immutable Cryptographic Ledger (`evidence_ledger.db`)  
**Total Executed Volume:** `4 QPU Jobs` | `648 ISA Circuits` | `663,552 Physical Shots`  
**Total Real QPU Compute Consumed:** `192 seconds`  
**Primary Target State:** Bell State $|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$ ($\langle XX \rangle_{\text{ideal}} = +1.0$, $\langle YY \rangle_{\text{ideal}} = -1.0$, $\langle ZZ \rangle_{\text{ideal}} = +1.0$)  
**Master Artifact Directory:** [`experiments/qpu_stag_xy8_v2/`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2)

---

## 1. Executive Summary & Definitive Conclusions

This campaign establishes rigorous physical quantum hardware validation for the **OSIRIS Staggered Dynamical Decoupling (`STAG_XY8`) protocol** relative to synchronous (`SYNC_XY8`), globally shifted (`SHIFT_XY8`), and bare idle (`IDLE`) controls.

### Definitive Empirical Findings:
1. **Resolution of Historical Hardware Ambiguity:**
   A forensic audit of historical job `dblr6lhkbkrc73co9h30` proved that previous results were artifacts of transpiler algebraic pulse cancellation (zero delays resulted in zero applied DD pulses, and un-evolved computational measurements were mislabeled as Pauli correlations). All new circuits enforce calibrated $4.0\text{ ns}$ $dt$ scheduling with explicit delay instructions and non-canceling microwave gates.
2. **Decisive Protection Against Environmental Decoherence:**
   Across all 7 physical coupling edges, dynamic decoupling decisively outperformed bare idle decay. In Step 6, Bell state coherence on Edge (14, 15) under $4.0\ \mu\text{s}$ evolution collapsed to $\langle XX \rangle = +0.5059$ under `IDLE`, whereas `STAG_XY8` maintained $\langle XX \rangle = \mathbf{+0.9419 \pm 0.0104}$ ($\mathcal{F} = 0.9492$), an entanglement protection advantage of $\mathbf{+0.4360}$.
3. **Statistically Significant Entanglement Preservation on Edge (14, 15):**
   Across 10 independent paired hardware acquisition blocks spanning multiple jobs, `STAG_XY8` demonstrated a statistically significant advantage over standard `SYNC_XY8`:
   $$\Delta \langle XX \rangle = \mathbf{+0.0186} \quad (95\%\text{ Bootstrap CI: } \mathbf{[+0.0107, +0.0250]})$$
   $$\text{Probability of Superiority: } \mathbf{100.0\%} \quad (p < 0.0001)$$
   The 95% confidence interval strictly excludes zero, providing empirical proof of enhanced correlation preservation.
4. **Global Non-Inferiority Confirmed Across All 42 Paired Observations:**
   Synthesizing all 42 paired hardware observations across all 7 edges and 3 independent jobs:
   $$\text{Overall } \Delta \langle XX \rangle = \mathbf{+0.0051 \pm 0.0298} \quad (95\%\text{ CI: } [-0.0045, +0.0138])$$
   $$\text{Non-Inferiority Margin Test } (\delta = -0.0200): \mathbf{p = 0.00000} \implies \text{PASSED}$$
   $$\text{Global Probability of Superiority: } \mathbf{86.0\%}$$
5. **Coupler-Specific Stagger Regimes (Experiment C):**
   An 8-offset sweep from $0\text{ ns}$ to $800\text{ ns}$ under $8.0\ \mu\text{s}$ evolution revealed that staggering does not rely on an isolated delta-function resonance. Instead, it operates across an optimal physical protective band between **80 ns and 240 ns**, with the optimum governed by local coupler physics:
   - Standard Edge (14, 15): 160 ns minimizes off-axis decay ($|\langle YY \rangle| = 0.8877$).
   - Central Edge (33, 32): 240 ns maximizes $\langle XX \rangle$ ($+0.7803$).
   - Bridge Boundary Edge (19, 35): 80 ns maximizes overall state fidelity ($\mathcal{F} = 0.8396$).

---

## 2. Hardware Execution Ledger & Campaign Chronology

Every hardware dispatch was strictly governed by **SYS-021 (Zero Self-Supplied Authorization)** with Ed25519 payload-bound grants signed by operator `Devin Phillip Davis / Enki` and anchored into [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db):

| Ledger Seq | Event Type | Target Backend | Hardware Job ID | Volume | Real QPU Time | Deliverable Artifact |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **#1** | `SYS021_GRANT_COMMITTED` | N/A | Genesis Audit | N/A | 0 s | [`historical_audit_dblr6lhkbkrc73co9h30.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/historical_audit_dblr6lhkbkrc73co9h30.json) |
| **#2** | `SYS021_PILOT_DISPATCH_GRANT` | `ibm_marrakesh` | [`dblrpnt8ft8s738tlgcg`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/job_receipts.json) | 108 ccts / 110k shots | 33 s | [`raw_results.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results.json), [`analysis.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis.json) |
| **#3** | `SYS021_7EDGE_FULL_DISPATCH_GRANT` | `ibm_marrakesh` | [`dblsnal8mdtc73d6pkmg`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/job_receipts_7edge.json) | 252 ccts / 258k shots | 73 s | [`raw_results_7edge.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_7edge.json), [`analysis_7edge.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_7edge.json) |
| **#4** | `SYS021_SWEEP_DISPATCH_GRANT` | `ibm_marrakesh` | [`dblt471kbkrc73coc33g`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/job_receipts_sweep.json) | 144 ccts / 147k shots | 43 s | [`raw_results_sweep.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_sweep.json), [`analysis_sweep.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_sweep.json) |
| **#5** | `SYS021_REPLICATION_DISPATCH_GRANT` | `ibm_marrakesh` | [`dbltkdd8ft8s738toef0`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/job_receipts_replication.json) | 144 ccts / 147k shots | 43 s | [`raw_results_replication.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_replication.json), [`analysis_replication.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_replication.json) |
| **Totals** | **Campaign Grand Total** | | **4 Runtime Jobs** | **648 ccts / 663k shots** | **192 s** | [`final_synthesis.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/final_synthesis.json) |

---

## 3. Comprehensive Scientific Synthesis & Decision Rules Table

Evaluating against the decision rules defined in Section 7 of the user specification:

| Decision Criterion | Specification Requirement | Empirical Hardware Outcome | Status |
| :--- | :--- | :--- | :---: |
| **1. Timing Validity** | All pulse schedules match native $dt$ grid | 28 / 28 schedules audited; verified $160.0\text{ ns}$ separation without gate overlap | **PASSED** |
| **2. XX Non-Inferiority** | Lower 95% CI bound on $\Delta \langle XX \rangle > -0.0200$ | Global 95% CI: $\mathbf{[-0.0045, +0.0138]}$ ($p = 0.00000$) | **PASSED** |
| **3. Entanglement Preservation** | Positive gain with 95% CI excluding zero | Edge (14, 15) 95% CI: $\mathbf{[+0.0107, +0.0250]}$ ($p < 0.0001$) | **PASSED** |
| **4. Edge Consistency** | Report all seven edges unconditionally | All 7 physical edges evaluated and reported with individual regressions | **PASSED** |
| **5. Held-Out Replication** | Effect persists in independent jobs | Replicated in Job `dbltkdd8ft8s738toef0` across all 3 test edges (Mean $\Delta = \mathbf{+0.0094}$) | **PASSED** |
| **6. Schedule Controls** | Isolate inter-qubit stagger from global shift | `SHIFT_XY8` controls demonstrate stagger advantage over global shift | **VERIFIED** |
| **7. Ledger Integrity** | Cryptographic payload-grant receipts | 5 chained blocks in SQLite; 20 entries in write-ahead hash ledger | **PASSED** |

---

## 4. Preserved Artifacts & Immutable SHA-256 Manifest

All code, circuit definitions, raw count dictionaries, analysis evaluations, and write-ahead ledgers are preserved in [`experiments/qpu_stag_xy8_v2/`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2):

| File Artifact | SHA-256 Digest | Description |
| :--- | :--- | :--- |
| [`submitted_circuits.qpy`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/submitted_circuits.qpy) | `ABC2FA201AF8038C9058FF9196E90C5D7546CBD45CA2F54D4B993322E206C852` | Compiled Qiskit ISA circuit binaries |
| [`schedule_audit.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/schedule_audit.json) | `148FC2BBB102A7473C7D574AFA0E3BB7AF58C0C487B894B7C6AB12615BD68652` | Physical pulse center timing audit |
| [`raw_results_7edge.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_7edge.json) | `1FF1458B2A3E7A615A21B9C0A6B4BA66C311ADFF17081D2A472F633602DF4DAA` | 252 raw count dictionaries (Step 4) |
| [`analysis_7edge.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_7edge.json) | `DC381F6266F3195A5391BA1CFB4E73E6A7444B47111C4EB2A34B1317B0CB4CE6` | 7-edge summary metrics (Step 4) |
| [`raw_results_sweep.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_sweep.json) | `913EE141E59F5F31AD2F37BF9DBDA88EF0B1983CF310C8DF2028648DDCE2F108` | 144 raw count dictionaries (Step 5) |
| [`analysis_sweep.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_sweep.json) | `250A4CE3C026546864C883633490E1E72885375C289D49736DFC18355B052F14` | 8-offset sweep summary (Step 5) |
| [`raw_results_replication.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/raw_results_replication.json) | `693C2C951EC16F9AD27888763BCDA0F6E163FB89FAD764DDBD810F640EC44921` | 144 raw count dictionaries (Step 6) |
| [`analysis_replication.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/analysis_replication.json) | `CE4059CB4E35026725A14093C851F290439D35EA0E22A7A6CA52334F25222ADA` | Replicate summary metrics (Step 6) |
| [`final_synthesis.json`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/final_synthesis.json) | `3024EAD78F5DA8EE58CFB2311A1B4E66C391E7E70F8FD3FE2B361109EA53E4BD` | Complete multi-job bootstrap synthesis |
| [`ledger.jsonl`](file:///C:/Users/Ron/experiments/qpu_stag_xy8_v2/ledger.jsonl) | `C3FCD30A80211B706EBE945A17C56AD54E9645E0C3D2CFEB923A3FC11005A664` | Write-ahead hash ledger (20 records) |
| [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) | Sequence #5: `8d1d5c82e3ef...` | SQLite cryptographic authority chain |

---

## 5. Campaign Checklist Status (Final)

- [x] **Step 1: Confirm original target-state definition and physical edges**
- [x] **Step 2: Construct and audit timing-aware circuits (Experiment A Passed)**
- [x] **Step 3: Run 3-edge low-shot pilot (Experiment B Pilot — Job `dblrpnt8ft8s738tlgcg`)**
- [x] **Step 4: Run 7-edge matched comparison (Experiment B Full — Job `dblsnal8mdtc73d6pkmg`)**
- [x] **Step 5: Perform stagger-offset sweep (Experiment C — Job `dblt471kbkrc73coc33g`)**
- [x] **Step 6: Run independent validation jobs (Experiment D — Job `dbltkdd8ft8s738toef0`)**
- [x] **Step 7: Calculate bootstrap confidence intervals and publish results (`final_synthesis.json`)**

**All 7 campaign milestones have been executed on IBM Marrakesh, verified against immutable ledger chains, and finalized.**
