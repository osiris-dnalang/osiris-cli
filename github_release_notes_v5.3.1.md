# OSIRIS v5.3.1: Referee-Audited Rescoring, Held-Out Nulls, and Inter-Arm Noise Floor Bounds on 156-Qubit IBM Heron r2

**Release Tag:** `v5.3.1`  
**Zenodo Deposition:** Continuance of [10.5281/zenodo.23983003](https://doi.org/10.5281/zenodo.23983003)  
**Authority Ledger:** [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) (Sequence Blocks #1–#26)  
**Backends Audited:** `ibm_marrakesh` & `ibm_fez` (156-qubit Heron r2, $dt = 4.0\text{ ns}$)

---

## 1. Executive Summary & Erratum / Rescoring Disclosures

OSIRIS v5.3.1 incorporates a rigorous peer-review statistical audit across all prospective physical hardware experiments (E0–E4) executed on IBM Heron r2 processors. Following independent review against analytical shot-noise lower bounds ($\sigma_{\mathcal{F}} \approx 1.01\text{–}1.03\text{ pp}$ per arm per block) and empirical background drift, this release formally updates all headline claims and replaces initial heuristic assertions with verified statistical boundaries:

### Rescored Estimands Matrix

| Target Claim | Initial Reported | Rescored Value | Forensic Audit Explanation |
| :--- | :---: | :---: | :--- |
| **E3 Pilot Primary (`v2 - Fixed80`)** | $+0.651\text{ pp}$ | **$+0.038\text{ pp}$** | Arm F executed continuous non-preregistered offsets ($40\text{ ns}$ and $120\text{ ns}$). Evaluating strictly the pre-registered binary policy using Arms C ($0\text{ ns}$) and E ($80\text{ ns}$) yields $+0.04\text{ pp}$. |
| **E2 Stagger Benefit (`Fixed80 - SYNC`)** | $+0.446\text{ pp}$ ($p < 0.03$) | **$+0.446 \pm \ge 0.206\text{ pp}$** | Sample cluster SEs ($0.090\text{–}0.113\text{ pp}$) with $df = 3$ swung below the physical shot-noise floor ($0.206\text{ pp}$). Bonferroni threshold ($\alpha = 0.006$) clears nothing. |
| **Fez Cross-Chip Transfer (`Adaptive - Fixed80`)** | $-0.803\text{ pp}$ | **$-0.25\text{ pp}$** | The reported $-2.00\text{ pp}$ on `(100,101)` was an arm-to-arm drift between identical $0\text{ ns}$ schedules (accidental A/A test). Transfer is decisively null. |
| **E4 Mechanistic Discrimination (H1 vs H2)** | "Decisive Falsification of H1" | **Neither Resolved** | Both couplers fit a flat response ($\chi^2$ $p = 0.866$ on `(14,15)` and $p = 0.854$ on `(61,62)`). Step fraction ($9.5\%$) is a ratio of noise-sized values. |
| **Static $ZZ$ Rate $\zeta$ on `(14, 15)`** | $3.170\text{ kHz}$ | **$0.91\sigma$ from zero** | $\Delta f = 6.34 \pm 6.93\text{ kHz}$ ($p = 0.36$). Bounding static coupling to $\le 10\text{ kHz}$ over a $2\,\mu\mathrm{s}$ window, without resolving non-zero rate. |

---

## 2. Key Empirical Findings & Methodological Contributions

1. **The Accidental A/A Inter-Arm Noise Floor ($1.03\text{ pp}$ RMS):**
   Across 7 cell pairs where identical pulse timing was dispatched in separate execution arms, the empirical RMS difference was **$1.03\text{ to }1.11\text{ pp}$** ($\chi^2 = 11.09, df = 6, p = 0.086$). This demonstrates that inter-arm calibration drift on commercial hardware equals or exceeds published sub-percentage DD gains.
2. **Cross-Chip Scalar Transfer Falsification:**
   Calibrations based purely on single-qubit dephasing metrics ($\eta_\phi$) failed to produce an advantage when transferred to `ibm_fez` ($\Delta \mathcal{F}_{\text{transfer}} = -0.80 \pm 0.60\text{ pp}$), falsifying naive parameter portability.
3. **Pooled Fixed 80 ns Stagger Hint:**
   Across all 17 evaluated coupler-duration cells on Heron r2, uniform $80\text{ ns}$ staggering shows an inverse-variance pooled advantage of **$+0.22 \pm 0.18\text{ pp}$** ($1.19\sigma$) and unweighted mean of **$+0.25 \pm 0.16\text{ pp}$** ($1.6\sigma$).
4. **Sample Size Power Law for Quantum Error Mitigation:**
   Resolving a $0.50\text{ pp}$ fidelity difference at $2\sigma$ significance requires **$\ge 33,500\text{ shots per basis per arm}$**, establishing the quantitative benchmark for future experimental campaigns.

---

## 3. Cryptographic Governance & Ledger Receipts

Every circuit execution, analysis script, raw bitstring count, and release manifest is anchored in [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) across 26 sequential cryptographic blocks under operator identity `Devin Phillip Davis / Enki`.
