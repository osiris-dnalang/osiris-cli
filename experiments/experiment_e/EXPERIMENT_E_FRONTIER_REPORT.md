# OSIRIS Frontier Campaign (Experiments E0–E2): Coupler-Aware Dynamical Decoupling & Prospective Held-Out Validation on `ibm_marrakesh`

**Backend:** `ibm_marrakesh` (156-qubit IBM Heron r2, $dt = 4.0\text{ ns}$)  
**Authority Chain:** [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) (Blocks #6–#11)  
**Total Campaign Compute:** $485\text{ s}$ across 8 IBM Quantum Runtime jobs ($115\text{ s}$ remaining of $600\text{ s}$ allocation)

---

## 1. Executive Summary of the E0–E2 Progression

1. **Experiment E Pilot (`dblujopkbkrc73coem40`, $63\text{ s}$) & Forensic Post-Mortem:**
   - Revealed that the initial `BELL_PHI_PLUS` helper (`qc.h(u); qc.cz(u,v); qc.h(v)`) lacked the prerequisite `qc.h(v)` prior to `cz(u,v)`, preparing $|++\rangle$ ($\mathcal{F}_{\text{Bell}} \approx 0.465$).
   - Fixed by enforcing `qc.h(u); qc.h(v); qc.cz(u,v); qc.h(v)` and a mandatory pre-flight `Statevector` verification gate (`run_preflight_statevector_gate()`).
2. **Experiment E0: Bell-State Entanglement Certification (`dblup49kbkrc73cof20g`, $62\text{ s}$, 108 circuits, 221,184 shots):**
   - Certified true two-qubit entanglement ($\mathcal{F}_{\text{Bell}} = \frac{1}{4}(1 + \langle XX \rangle - \langle YY \rangle + \langle ZZ \rangle) > 0.50$) on `ibm_marrakesh`:
     - At $0\,\mu\mathrm{s}$: $\mathbf{97.30\%}$ on `(14,15)`, $\mathbf{93.55\%}$ on `(19,35)`, $\mathbf{94.07\%}$ on `(33,32)`.
     - At $4\,\mu\mathrm{s}$ idle: $\mathbf{87.81\%}$ on `(14,15)`, $\mathbf{86.08\%}$ on `(19,35)`, $\mathbf{80.57\%}$ on `(33,32)`.
     - All 12 separable product-state controls (`|00⟩`, `|++⟩`) satisfied $\mathcal{F}_{\text{Bell}} \le 0.50$.
3. **Experiment E1: Multi-Duration Stagger Response Landscape (`dblutq9kbkrc73cofcg0`, $79\text{ s}$, 270 circuits, 276,480 shots):**
   - Mapped antisymmetric bilateral staggered XY8 ($\delta_u = -\Delta/2, \delta_v = +\Delta/2$, offsets $\Delta \in \{80, 160, 240\}\text{ ns}$) vs synchronous XY8 at $4\,\mu\mathrm{s}$ and $8\,\mu\mathrm{s}$ across 3 edges and 3 randomized blocks.
   - Demonstrated that staggered XY8 is **coupler- and duration-dependent**, governed by the dimensionless **Single-Qubit Dephasing Saturation Ratio**:
     $$\eta_\phi(e, T) = T \cdot \max\big(\Gamma_\phi(u),\, \Gamma_\phi(v)\big), \qquad \Gamma_\phi(q) = \max\!\left(0,\, \frac{1}{T_2(q)} - \frac{1}{2T_1(q)}\right)$$
4. **Experiment E2: Prospective Held-Out Scheduler Validation (`dblv7sm74qds73dr8ho0`, $84\text{ s}$, 288 circuits, 294,912 shots):**
   - Evaluated the frozen [`osiris_adaptive_scheduler_v1.py`](file:///C:/Users/Ron/experiments/experiment_e/osiris_adaptive_scheduler_v1.py) (`1f6e55f500e7e0f5ffc38bd3786a278da83450d715eef2bfa2290aa75852980d`) and pre-registered predictions [`preregistered_predictions_exp_e2.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e2.json) (`ddcbeda3a1d6d752c68cd5e9f6fd21bf4eeab9782660df834e4ffe268e0e206e`) across **4 unseen heavy-hex couplers** (`(15,19)`, `(32,31)`, `(34,33)`, `(35,34)`) and $K = 4$ randomized blocks ($df = 3$).

---

## 2. Experiment E2 Prospective Held-Out Results (`dblv7sm74qds73dr8ho0`)

| Held-Out Edge | Duration $T$ | $\eta_\phi(e, T)$ | Pre-Registered Regime & Policy | $\mathcal{F}_{\text{Bell}}(\text{IDLE})$ | $\mathcal{F}_{\text{Bell}}(\text{SYNC})$ | $\mathcal{F}_{\text{Bell}}(\text{STAG}_{80})$ | $\Delta \mathcal{F}_{\text{Bell}} \pm \text{SE}_{\text{blk}}$ (pp) | Exact $df=3$ 95% CI (pp) | $t_3$ ($p_{\text{1s}}$) | Positive Blocks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`(15,19)`** | $4\,\mu\mathrm{s}$ | $0.1072$ | Regime I (`SYNC_XY8`, $\|\Delta\| \le 0.5\text{ pp}$) | $82.42\%$ | $91.72\%$ | $92.09\%$ | **$+0.37 \pm 0.14$** | $[-0.09, +0.83]$ | $+2.54$ ($0.0425$) | $4 / 4$ |
| **`(15,19)`** | $8\,\mu\mathrm{s}$ | **$0.2145$** | **Regime II (`STAG_XY8_80`, $\Delta > 0$)** | $66.63\%$ | $87.22\%$ | **$87.78\%$** | **$+0.56 \pm 0.20$** | $[-0.08, +1.20]$ | **$+2.78$ ($0.0344$)** | **$4 / 4$** |
| **`(32,31)`** | $4\,\mu\mathrm{s}$ | $0.0840$ | Regime I (`SYNC_XY8`, $\|\Delta\| \le 0.5\text{ pp}$) | $77.48\%$ | $85.80\%$ | $86.79\%$ | $+0.99 \pm 0.96$ | $[-2.07, +4.04]$ | $+1.03$ ($0.1894$) | $3 / 4$ |
| **`(32,31)`** | $8\,\mu\mathrm{s}$ | $0.1680$ | Regime II (`STAG_XY8_80`, borderline $\eta_\phi$) | $57.35\%$ | $78.22\%$ | $77.69\%$ | $-0.54 \pm 0.83$ | $[-3.19, +2.11]$ | $-0.65$ ($0.7177$) | $2 / 4$ |
| **`(34,33)`** | $4\,\mu\mathrm{s}$ | **$0.2600$** | **Regime II (`STAG_XY8_80`, $\Delta > 0$)** | $76.70\%$ | $84.78\%$ | **$86.11\%$** | **$+1.33 \pm 0.90$** | $[-1.54, +4.21]$ | $+1.47$ ($0.1186$) | $2 / 4$ |
| **`(34,33)`** | $8\,\mu\mathrm{s}$ | **$0.5199$** | **Regime III (`SYNC_XY8`, CPMG breakdown)** | $52.67\%$ | $77.94\%$ | $78.11\%$ | **$+0.17 \pm 0.55$** | $[-1.59, +1.93]$ | $+0.31$ ($0.3887$) | $2 / 4$ |
| **`(35,34)`** | $4\,\mu\mathrm{s}$ | $0.0160$ | Regime I (`SYNC_XY8`, $\|\Delta\| \le 0.5\text{ pp}$) | $77.99\%$ | $86.58\%$ | $86.71\%$ | **$+0.12 \pm 0.41$** | $[-1.18, +1.42]$ | $+0.30$ ($0.3924$) | $2 / 4$ |
| **`(35,34)`** | $8\,\mu\mathrm{s}$ | $0.0319$ | Regime I (`SYNC_XY8`, $\|\Delta\| \le 0.5\text{ pp}$) | $57.21\%$ | $80.57\%$ | $81.13\%$ | $+0.56 \pm 0.81$ | $[-2.03, +3.15]$ | $+0.69$ ($0.2701$) | $2 / 4$ |

### Portfolio Policy Comparison Across All 8 Held-Out Cells (32 Paired Block Evaluations)

| Control Policy | Mean Held-Out $\mathcal{F}_{\text{Bell}}$ | Gain vs `IDLE` | Gain vs Universal `SYNC_XY8` | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **1. Unprotected `IDLE`** | $68.556\%$ | — | $-15.549\text{ pp}$ | Severe dephasing at $8\,\mu\mathrm{s}$ ($52.67\%$ on `(34,33)`) |
| **2. Fixed Universal `SYNC_XY8`** | $84.105\%$ | $+15.549\text{ pp}$ | $0.000\text{ pp}$ | Standard hardware-agnostic dynamical decoupling |
| **3. Frozen `OSIRIS Adaptive Scheduler v1.0`** | **$84.274\%$** | **$+15.718\text{ pp}$** | **$+0.169\text{ pp}$** | Pre-registered policy (`STAG_XY8_80` on Regime II, `SYNC_XY8` elsewhere) |
| **4. Fixed Universal `STAG_XY8_80`** | **$84.550\%$** | **$+15.994\text{ pp}$** | **$+0.446\text{ pp}$** | Global $t_{31} = 1.935$, $p_{\text{2s}} = 0.0621$, $p_{\text{1s}} = 0.0310$ |
| **5. Post-Hoc Cell Oracle** | $84.618\%$ | $+16.062\text{ pp}$ | $+0.513\text{ pp}$ | Upper bound selecting $\max(\text{SYNC}, \text{STAG}_{80})$ per cell |

---

## 3. Immutable Cryptographic Artifact Manifest (`experiments/experiment_e/`)

| Artifact Path | SHA-256 Digest | Description |
| :--- | :--- | :--- |
| [`execute_experiment_e0.py`](file:///C:/Users/Ron/experiments/experiment_e/execute_experiment_e0.py) | `a55449ad9c59c604dd67c17022a0ef01175efb04f5134d46943cbbad14ba4e28` | E0 Bell-state certification script (Job `dblup49kbkrc73cof20g`) |
| [`submitted_circuits_exp_e0.qpy`](file:///C:/Users/Ron/experiments/experiment_e/submitted_circuits_exp_e0.qpy) | `34d60377a3e4d936d76089da88cb5710a2ce1dd14faeca8e3559c9a2b993c792` | Frozen server-verified QPY archive for E0 (108 circuits) |
| [`execute_experiment_e1.py`](file:///C:/Users/Ron/experiments/experiment_e/execute_experiment_e1.py) | `8563ffe56bef4e23e9688091b81796ed0e26d6d272443ecd676656fa97620e50` | E1 multi-duration stagger response script (Job `dblutq9kbkrc73cofcg0`) |
| [`submitted_circuits_exp_e1.qpy`](file:///C:/Users/Ron/experiments/experiment_e/submitted_circuits_exp_e1.qpy) | `58b82b4f63c4ebe548f2ef0fc518289da9f5d4e3651313f6ae7d6acc95532cfb` | Frozen QPY archive for E1 (270 circuits) |
| [`marrakesh_edge_calibration_features.json`](file:///C:/Users/Ron/experiments/experiment_e/marrakesh_edge_calibration_features.json) | `327b5ff25c836e7eae75579f88f21c210049482b7cc97b2e77acf34ed2957c50` | E1 18-comparison multiplicity audit & backend calibration telemetry |
| [`osiris_adaptive_scheduler_v1.py`](file:///C:/Users/Ron/experiments/experiment_e/osiris_adaptive_scheduler_v1.py) | `1f6e55f500e7e0f5ffc38bd3786a278da83450d715eef2bfa2290aa75852980d` | Frozen prospective scheduler model ($\eta_\phi(e, T)$ regime classifier) |
| [`preregistered_predictions_exp_e2.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e2.json) | `ddcbeda3a1d6d752c68cd5e9f6fd21bf4eeab9782660df834e4ffe268e0e206e` | Pre-registered held-out predictions frozen prior to E2 dispatch |
| [`execute_experiment_e2_heldout.py`](file:///C:/Users/Ron/experiments/experiment_e/execute_experiment_e2_heldout.py) | `87476a255fd579012f29cfa8edf8b3f358273e813003ae790a1914526ab683c0` | E2 held-out execution script (Job `dblv7sm74qds73dr8ho0`) |
| [`submitted_circuits_exp_e2.qpy`](file:///C:/Users/Ron/experiments/experiment_e/submitted_circuits_exp_e2.qpy) | `e8e8f896f7dd5bcceded6a637b9711eb54bdc0f35a0c48489ab369d2d85bbc7e` | Frozen QPY archive for E2 (288 circuits) |
| [`raw_results_exp_e2.json`](file:///C:/Users/Ron/experiments/experiment_e/raw_results_exp_e2.json) | `952fd75b9f3bc97aa8e295765b38cddd572e7c77471ff513c0fc5f6cc25a0408` | Raw bitstring count dictionaries for E2 (288 circuits, 294,912 shots) |
| [`analysis_exp_e2.json`](file:///C:/Users/Ron/experiments/experiment_e/analysis_exp_e2.json) | `cc7d2369cd223862f0934595b29bb09bd6ad6f8616e84314137d3659508596a3` | Prospective evaluation summary for E2 |
| [`osiris_adaptive_scheduler_v2.py`](file:///C:/Users/Ron/experiments/experiment_e/osiris_adaptive_scheduler_v2.py) | `a2f260b074f02fa5143ec35a423b7cef5300462a1df43ad2944aeec44253b4ca` | Cost-sensitive uncertainty-gated Adaptive Scheduler v2.0 & E2 cluster reanalysis |
| [`analysis_exp_e2_clustered.json`](file:///C:/Users/Ron/experiments/experiment_e/analysis_exp_e2_clustered.json) | `ce26e234c36c9c651b23f05275881c5984244cb0ed1a15a353f83f24b5b803e7` | Cluster-robust statistical reanalysis of E2 (coupler $df=3$ & block $df=3$) |
| [`preregistered_predictions_exp_e3.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e3.json) | `1890ed5d8185195ff554962a94d6b7f1e70571f784bc7f10fcc0c0c04e301c6f` | Frozen pre-registered predictions for Experiment E3 (7 unseen heavy-hex couplers) |

---

## 4. Cluster-Robust Statistical Reanalysis & Forensic Post-Mortem of Experiment E2

### 4.1 Why `OSIRIS Adaptive Scheduler v1.0` Underperformed `Fixed STAG_XY8_80` ($-0.28\text{ pp}$)
In Experiment E2 (`dblv7sm74qds73dr8ho0`), `Fixed STAG_XY8_80` achieved the highest mean held-out Bell-state fidelity (`84.550%`, **$+0.446\text{ pp}$** over `SYNC_XY8`), whereas frozen `OSIRIS Adaptive Scheduler v1.0` achieved `84.274%` (**$+0.169\text{ pp}$** over `SYNC_XY8`, trailing `Fixed STAG_XY8_80` by **$-0.276\text{ pp}$**).

Forensic inspection of the E1+E2 calibration and outcome matrix (7 couplers, 14 `(edge, duration)` cells, 50 paired blocks) identifies two structural root causes in `v1.0`:
1. **Defaulting to `SYNC_XY8` in Regime I ($\eta_{\phi,\max} < 0.15$):** `v1.0` assumed that low-dephasing couplers have negligible $ZZ$ crosstalk benefit and defaulted to `SYNC_XY8` on 4 of the 8 held-out E2 cells (`(15,19)@4us`, `(32,31)@4us`, `(35,34)@4us`, `(35,34)@8us`). On fast heavy-hex couplers ($\tau_{CZ} = 68\text{ ns}$), all four of those Regime I cells actually benefited from `STAG_XY8_80` (`+0.37 pp`, `+0.99 pp`, `+0.12 pp`, `+0.56 pp`), costing `v1.0` $-0.255\text{ pp}$ across the 8-cell portfolio.
2. **Single-Qubit Maximum vs. Bilateral Partner Dephasing ($\eta_{\phi,\max}$ vs. $\eta_{\phi,\min}$):** `v1.0` triggered CPMG breakdown using the noisier qubit alone ($\eta_{\phi,\max}(e, T) = T \cdot \max(\Gamma_\phi(u), \Gamma_\phi(v))$). However, under antisymmetric bilateral stagger ($\delta_u = -40\text{ ns}, \delta_v = +40\text{ ns}$), if one qubit is noisy while its partner has long $T_2$ (e.g., `(34,33)@8us` where $\eta_{\phi,\max} = 0.5199$ on Q33 but $\eta_{\phi,\min} = 0.0319$ on Q34), shifting the clean partner incurs negligible echo penalty (`STAG_80 - SYNC = +0.17 pp`). Conversely, when **both** partner qubits simultaneously exceed the bilateral dephasing threshold $\eta_{\phi,\min}(e, T) = T \cdot \min(\Gamma_\phi(u), \Gamma_\phi(v)) > 0.075$—as on `(32,31)@8us` ($\eta_{\phi,\min} = 0.0847$, $\Delta = -0.54\text{ pp}$) and E1's `(33,32)@8us` ($\eta_{\phi,\min} = 0.1680$, $\Delta = -0.90\text{ pp}$)—bilateral staggered timing degrades both echoes simultaneously.

### 4.2 Cluster-Robust Portfolio Inference (Replacing Naive $N=32$ Pooling)
Pooling all 32 block differences as independent observations ($df = 31$) ignores within-coupler and within-acquisition-block correlation. Below is the cluster-robust reanalysis from [`analysis_exp_e2_clustered.json`](file:///C:/Users/Ron/experiments/experiment_e/analysis_exp_e2_clustered.json):

| Portfolio Comparison | Clustering Unit | Clusters ($df$) | Mean Difference (pp) | Cluster-Robust SE (pp) | Exact 95% CI (pp) | $t$-stat | $p_{\text{2-sided}}$ ($p_{\text{1-sided}}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Fixed STAG_XY8_80 - SYNC_XY8`** | **Physical Coupler (Edge)** | $G = 4$ ($df = 3$) | **$+0.446\text{ pp}$** | $0.113\text{ pp}$ | **`[+0.087, +0.804]`** | $+3.952$ | **$0.0289$** ($0.0145$) |
| **`Fixed STAG_XY8_80 - SYNC_XY8`** | **Acquisition Block** | $K = 4$ ($df = 3$) | **$+0.446\text{ pp}$** | $0.090\text{ pp}$ | **`[+0.161, +0.730]`** | $+4.977$ | **$0.0156$** ($0.0078$) |
| **`Fixed STAG_XY8_80 - SYNC_XY8`** | Naive Pooled Cell-Blocks | $N = 32$ ($df = 31$) | $+0.446\text{ pp}$ | $0.230\text{ pp}$ | `[-0.024, +0.915]` | $+1.935$ | $0.0621$ ($0.0310$) |
| **`Adaptive v1.0 - SYNC_XY8`** | **Physical Coupler (Edge)** | $G = 4$ ($df = 3$) | $+0.169\text{ pp}$ | $0.129\text{ pp}$ | `[-0.241, +0.580]` | $+1.312$ | $0.2810$ ($0.1405$) |
| **`Adaptive v1.0 - Fixed STAG_XY8_80`** | **Physical Coupler (Edge)** | $G = 4$ ($df = 3$) | **$-0.276\text{ pp}$** | $0.090\text{ pp}$ | `[-0.562, +0.010]` | $-3.073$ | $0.0545$ ($0.9728$) |
| **`Adaptive v1.0 - Fixed STAG_XY8_80`** | **Acquisition Block** | $K = 4$ ($df = 3$) | **$-0.276\text{ pp}$** | $0.087\text{ pp}$ | `[-0.554, +0.001]` | $-3.166$ | $0.0506$ ($0.9747$) |

#### Edge-Specific Cluster Summaries in E2 (Averaged Across $4\,\mu\mathrm{s}$ and $8\,\mu\mathrm{s}$)
- **`(15,19)`**: `STAG_80 - SYNC = +0.464 pp`, `v1.0 - SYNC = +0.280 pp`, `v1.0 - STAG_80 = -0.183 pp`
- **`(32,31)`**: `STAG_80 - SYNC = +0.226 pp`, `v1.0 - SYNC = -0.268 pp`, `v1.0 - STAG_80 = -0.494 pp`
- **`(34,33)`**: `STAG_80 - SYNC = +0.751 pp`, `v1.0 - SYNC = +0.666 pp`, `v1.0 - STAG_80 = -0.085 pp`
- **`(35,34)`**: `STAG_80 - SYNC = +0.342 pp`, `v1.0 - SYNC = 0.000 pp`, `v1.0 - STAG_80 = -0.342 pp`

---

## 5. OSIRIS Adaptive Scheduler v2.0 & Pre-Registered Experiment E3 Protocol

To address the E2 findings, [`osiris_adaptive_scheduler_v2.py`](file:///C:/Users/Ron/experiments/experiment_e/osiris_adaptive_scheduler_v2.py) (`a2f260b074f02fa5143ec35a423b7cef5300462a1df43ad2944aeec44253b4ca`) replaces the `v1.0` heuristic with a **cost-sensitive, uncertainty-gated physical linear predictor** trained strictly on E1 + E2 ($N = 14$ cells across 7 couplers):

$$\widehat{\Delta\mathcal{F}}_{\text{STAG80}-\text{SYNC}}(e, T) = \beta_{\text{fast}} \cdot \mathbb{I}(\tau_{CZ} < 74\text{ ns}) + \beta_{\text{slow}} \cdot \mathbb{I}(\tau_{CZ} \ge 74\text{ ns}) + \beta_{\text{bilat}} \cdot \max\!\big(0,\, \eta_{\phi,\min}(e, T) - 0.075\big)$$

with fitted E1+E2 parameters $\beta_{\text{fast}} = +0.5823\text{ pp}$, $\beta_{\text{slow}} = -0.3498\text{ pp}$, $\beta_{\text{bilat}} = -16.007\text{ pp}$, and residual standard error $\hat{\sigma}_{\varepsilon} = 0.527\text{ pp}$.

### 5.1 Cost-Sensitive Uncertainty Gate (Defaulting to `STAG_XY8_80`)
Rather than defaulting to `SYNC_XY8`, `OSIRIS_ADAPTIVE_V2` treats `STAG_XY8_80` as the default baseline and switches to `SYNC_XY8` **if and only if** the predicted advantage of `SYNC_XY8` exceeds the predictive standard error margin ($\kappa = 0.50$):

$$\pi_{\text{v2}}(e, T) = \begin{cases} \texttt{SYNC\_XY8}, & \text{if } \widehat{\Delta\mathcal{F}}_{\text{STAG80}-\text{SYNC}}(e, T) + 0.50 \cdot \hat{\sigma}_{\text{pred}}(e, T) < 0 \\ \texttt{STAG\_XY8\_80}, & \text{otherwise.} \end{cases}$$

Across Leave-One-Edge-Out Cross-Validation (LOEO-CV) over all 7 couplers (14 cells) in E1 + E2:
- **LOEO-CV Mean Gain vs. `Fixed STAG_XY8_80`**: **$+0.114\text{ pp}$** (`0 / 14` negative-regret cells; positive gains on slow coupler `(19,35)` at $4, 8\,\mu\mathrm{s}$ and bilateral-dephasing cell `(33,32)@8us`).
- **LOEO-CV Mean Gain vs. `Fixed SYNC_XY8`**: **$+0.435\text{ pp}$** (compared to $+0.321\text{ pp}$ for `Fixed STAG_XY8_80`).

### 5.2 Frozen Pre-Registered Predictions for Experiment E3 (7 Unseen Heavy-Hex Couplers)
Frozen in [`preregistered_predictions_exp_e3.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e3.json) (`1890ed5d8185195ff554962a94d6b7f1e70571f784bc7f10fcc0c0c04e301c6f`), Experiment E3 evaluates **three frozen policies** (`SYNC_XY8`, `STAG_XY8_80`, `OSIRIS_ADAPTIVE_V2`) across the 7 remaining unseen couplers on `ibm_marrakesh`, with primary endpoint $\Delta\mathcal{F}_{\text{primary}} = \mathcal{F}_{\text{Bell}}(\text{OSIRIS\_ADAPTIVE\_V2}) - \mathcal{F}_{\text{Bell}}(\text{STAG\_XY8\_80})$:

| Unseen E3 Edge | Duration $T$ | $\tau_{CZ}$ (ns) | $\eta_{\phi,\min}(e,T)$ | $\eta_{\phi,\max}(e,T)$ | Predicted $\widehat{\Delta\mathcal{F}}_{\text{STAG80}-\text{SYNC}} \pm \hat{\sigma}_{\text{pred}}$ (pp) | Upper Gate Bound $\widehat{\Delta} + 0.5\hat{\sigma}_{\text{pred}}$ (pp) | Frozen `OSIRIS_ADAPTIVE_V2` Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`(12,13)`** | $4\,\mu\mathrm{s}$ | $84.0$ (Slow) | $0.0642$ | $0.0725$ | **$-0.35 \pm 0.65$** | **$-0.026 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(12,13)`** | $8\,\mu\mathrm{s}$ | $84.0$ (Slow) | $0.1285$ | $0.1449$ | **$-1.21 \pm 0.77$** | **$-0.822 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(13,14)`** | $4\,\mu\mathrm{s}$ | $76.0$ (Slow) | $0.0715$ | $0.0725$ | **$-0.35 \pm 0.65$** | **$-0.026 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(13,14)`** | $8\,\mu\mathrm{s}$ | $76.0$ (Slow) | $0.1430$ | $0.1449$ | **$-1.44 \pm 0.83$** | **$-1.023 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(24,25)`** | $4\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.1030$ | $0.1062$ | $+0.13 \pm 0.57$ | $+0.421 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(24,25)`** | $8\,\mu\mathrm{s}$ | $68.0$ (Fast) | **$0.2060$** | $0.2124$ | **$-1.51 \pm 0.91$** | **$-1.061 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(25,26)`** | $4\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.1062$ | $0.1322$ | $+0.08 \pm 0.58$ | $+0.371 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(25,26)`** | $8\,\mu\mathrm{s}$ | $68.0$ (Fast) | **$0.2124$** | $0.2643$ | **$-1.62 \pm 0.94$** | **$-1.145 < 0$** | **`SYNC_XY8` (Switch)** |
| **`(44,45)`** | $4\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.0566$ | $0.0717$ | $+0.58 \pm 0.56$ | $+0.861 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(44,45)`** | $8\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.1131$ | $0.1434$ | $-0.03 \pm 0.59$ | $+0.266 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(45,46)`** | $4\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.0566$ | $0.0825$ | $+0.58 \pm 0.56$ | $+0.861 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(45,46)`** | $8\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.1131$ | $0.1651$ | $-0.03 \pm 0.59$ | $+0.266 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(52,53)`** | $4\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.0434$ | $0.1235$ | $+0.58 \pm 0.56$ | $+0.861 \ge 0$ | `STAG_XY8_80` (Retain) |
| **`(52,53)`** | $8\,\mu\mathrm{s}$ | $68.0$ (Fast) | $0.0868$ | $0.2470$ | $+0.39 \pm 0.56$ | $+0.674 \ge 0$ | `STAG_XY8_80` (Retain) |
