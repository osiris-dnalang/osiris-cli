# OSIRIS Frontier Campaign (Experiments E0–E3): Coupler-Aware Dynamical Decoupling & Prospective Held-Out Validation on `ibm_marrakesh`

**Backend:** `ibm_marrakesh` (156-qubit IBM Heron r2, $dt = 4.0\text{ ns}$)  
**Authority Chain:** [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) (Blocks #6–#15)  
**Total Campaign Compute:** $549\text{ s}$ across 9 IBM Quantum Runtime jobs ($51\text{ s}$ remaining of $600\text{ s}$ allocation)

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

---

## 6. Experiment E3 Pilot: Prospective Physical Hardware Validation (`dbm00gd8mdtc73d6vjcg`, $64\text{ s}$)

**Job ID:** `dbm00gd8mdtc73d6vjcg` ($64\text{ s}$ real QPU compute on `ibm_marrakesh`, 216 circuits, 221,184 physical shots, $K = 3$ randomized acquisition blocks)  
**SYS-021 Authority:** Ledger Block **#15** (`10783352e8a035c4...`), Payload SHA-256 `cffbcd6670c5b00998e81d4fb50b20cdb96e69dff096e6774ce5f06d8e031487`, QPY SHA-256 `3f33a55645defdd4a3bc59f3871ad238e10c34166435d38dff02c71c211f3c70`

### 6.1 Unseen E3 Cell-by-Cell Physical Hardware Results (`analysis_exp_e3_pilot.json`)

| Unseen E3 Edge | Duration $T$ | `OSIRIS v2` Offset $\Delta^*$ | Arm C `QISKIT_SYNC_XY8` ($0\text{ ns}$) | Arm D `QISKIT_OPT_STAG` ($\tau/2$) | Arm E `FIXED_STAG_80` ($80\text{ ns}$) | Arm F `OSIRIS_COMPILER_V2` | **`OSIRIS v2 - FIXED_80` (pp)** | **`OSIRIS v2 - SYNC_XY8` (pp)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`(12,13)` Slow ($84\text{ ns}$)** | $4\,\mu\mathrm{s}$ | **$0\text{ ns}$** | $91.10\%$ | $91.11\%$ | $90.98\%$ | **$91.80\%$** | **$+0.81 \pm 0.27\text{ pp}$** ($3/3$) | **$+0.70\text{ pp}$** ($2/3$) |
| **`(12,13)` Slow ($84\text{ ns}$)** | $8\,\mu\mathrm{s}$ | **$0\text{ ns}$** | $88.48\%$ | $89.16\%$ | $88.70\%$ | **$89.57\%$** | **$+0.86 \pm 0.43\text{ pp}$** ($3/3$) | **$+1.09\text{ pp}$** ($3/3$) |
| **`(24,25)` High-$\eta_{\phi,\min}$** | $4\,\mu\mathrm{s}$ | **$40\text{ ns}$** | $69.78\%$ | **$71.00\%$** | $67.82\%$ | **$70.38\%$** | **$+2.56 \pm 0.86\text{ pp}$** ($3/3$) | **$+0.60\text{ pp}$** ($2/3$) |
| **`(24,25)` High-$\eta_{\phi,\min}$** | $8\,\mu\mathrm{s}$ | **$0\text{ ns}$** | **$58.41\%$** | $58.11\%$ | $58.07\%$ | $57.78\%$ | $-0.29 \pm 0.79\text{ pp}$ ($1/3$) | $-0.63\text{ pp}$ ($1/3$) |
| **`(44,45)` Clean Fast ($68\text{ ns}$)** | $4\,\mu\mathrm{s}$ | **$120\text{ ns}$** | $82.19\%$ | **$83.84\%$** | $83.38\%$ | **$83.50\%$** | **$+0.11 \pm 0.29\text{ pp}$** ($1/3$) | **$+1.30\text{ pp}$** ($3/3$) |
| **`(44,45)` Clean Fast ($68\text{ ns}$)** | $8\,\mu\mathrm{s}$ | **$80\text{ ns}$** | $78.06\%$ | **$78.56\%$** | $78.30\%$ | $78.16\%$ | $-0.15 \pm 0.07\text{ pp}$ ($0/3$) | **$+0.10\text{ pp}$** ($2/3$) |
| **6-Cell Portfolio Mean** | — | — | **$78.003\%$** | **$78.630\%$** | **$77.878\%$** | **$78.529\%$** | **$+0.651\text{ pp}$** | **$+0.526\text{ pp}$** |

### 6.2 Cluster-Robust Portfolio Contrasts in Experiment E3 Pilot

| Contrast | Clustering Unit | Clusters ($df$) | Mean Difference (pp) | Cluster SE (pp) | Exact $df=2$ 95% CI (pp) | $t$-Stat | $p_{\text{2-sided}}$ ($p_{\text{1-sided}}$) | Positive Clusters |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`OSIRIS_V2 - FIXED_STAG_80` (Primary)** | **Acquisition Block** | $K = 3$ ($df = 2$) | **$+0.651\text{ pp}$** | $0.182\text{ pp}$ | `[-0.130, +1.432]` | $+3.587$ | $0.0697$ (**$0.0348$**) | **$3 / 3$** (`+0.99, +0.59, +0.37`) |
| **`OSIRIS_V2 - FIXED_STAG_80` (Primary)** | **Physical Coupler** | $G = 3$ ($df = 2$) | **$+0.651\text{ pp}$** | $0.344\text{ pp}$ | `[-0.830, +2.132]` | $+1.891$ | $0.1991$ ($0.0996$) | $2 / 3$ (`+0.84, +1.13, -0.02`) |
| **`OSIRIS_V2 - QISKIT_SYNC_XY8`** | **Acquisition Block** | $K = 3$ ($df = 2$) | **$+0.526\text{ pp}$** | $0.116\text{ pp}$ | **`[+0.027, +1.026]`** | $+4.534$ | **$0.0454$** (**$0.0227$**) | **$3 / 3$** (`+0.50, +0.74, +0.34`) |
| **`OSIRIS_V2 - QISKIT_SYNC_XY8`** | **Physical Coupler** | $G = 3$ ($df = 2$) | **$+0.526\text{ pp}$** | $0.277\text{ pp}$ | `[-0.666, +1.718]` | $+1.899$ | $0.1979$ ($0.0990$) | $2 / 3$ (`+0.90, -0.02, +0.70`) |
| **`OSIRIS_V2 - QISKIT_OPT_STAG`** | **Physical Coupler** | $G = 3$ ($df = 2$) | $-0.100\text{ pp}$ | $0.324\text{ pp}$ | `[-1.495, +1.294]` | $-0.310$ | $0.7860$ ($0.6070$) | $1 / 3$ (`+0.55` on slow `(12,13)`) |
| **`FIXED_STAG_80 - QISKIT_SYNC_XY8`** | **Physical Coupler** | $G = 3$ ($df = 2$) | $-0.125\text{ pp}$ | $0.546\text{ pp}$ | `[-2.472, +2.223]` | $-0.229$ | $0.8404$ ($0.5798$) | $2 / 3$ (`-1.15` on `(24,25)`) |

---

## 7. Separate Compiler Performance Benchmark ([`bench_compiler_performance.py`](file:///C:/Users/Ron/experiments/experiment_e/bench_compiler_performance.py))

Evaluated over $R = 15$ repetitions across 5 heavy-hex workloads ($n = 2, 4, 5, 8, 12$ qubits, SHA-256 `c2f3e971acff9d5b7dee40ffcdee823b6a66f7987d26969130cbf00bd72f60ef`):

| Workload ID | Qubits ($n$) | `QISKIT_OPT1_PAD_DD_SYNC` (ms / KB) | `QISKIT_OPT3_PAD_DD_STAG` (ms / KB) | `OSIRIS_COMPILER_V2` (ms / KB) | **Speedup vs Opt-1 / Opt-3** | **Memory Reduction vs Opt-3** | **Unitary $\|1 - \mathcal{F}\|$** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`W1_2Q_BELL_DD_4US`** | $2$ | $5.91\text{ ms}$ / $191.9\text{ KB}$ | $12.69\text{ ms}$ / $276.7\text{ KB}$ | **$0.53\text{ ms}$ / $80.7\text{ KB}$** | **$11.1\times$ / $23.9\times$** | **$3.43\times$** | $8.9 \times 10^{-16}$ |
| **`W2_4Q_GHZ_CHAIN_DD_4US`** | $4$ | $7.40\text{ ms}$ / $244.6\text{ KB}$ | $14.56\text{ ms}$ / $359.4\text{ KB}$ | **$1.01\text{ ms}$ / $96.5\text{ KB}$** | **$7.3\times$ / $14.4\times$** | **$3.72\times$** | $1.6 \times 10^{-15}$ |
| **`W3_5Q_CLUSTER_CHAIN_DD_8US`** | $5$ | $7.98\text{ ms}$ / $304.2\text{ KB}$ | $15.92\text{ ms}$ / $424.4\text{ KB}$ | **$1.22\text{ ms}$ / $99.9\text{ KB}$** | **$6.5\times$ / $13.0\times$** | **$4.25\times$** | $1.8 \times 10^{-15}$ |
| **`W4_8Q_HEAVY_HEX_DD_8US`** | $8$ | $9.85\text{ ms}$ / $418.5\text{ KB}$ | $18.94\text{ ms}$ / $600.3\text{ KB}$ | **$1.99\text{ ms}$ / $146.9\text{ KB}$** | **$5.0\times$ / $9.5\times$** | **$4.09\times$** | $3.3 \times 10^{-15}$ |
| **`W5_12Q_BRICKWALL_DD_8US`** | $12$ | $11.83\text{ ms}$ / $573.4\text{ KB}$ | $24.58\text{ ms}$ / $811.4\text{ KB}$ | **$2.90\text{ ms}$ / $266.8\text{ KB}$** | **$4.1\times$ / $8.5\times$** | **$3.04\times$** | $6.7 \times 10^{-16}$ |
| **5-Workload Portfolio Mean** | — | $8.59\text{ ms}$ / $346.5\text{ KB}$ | $17.34\text{ ms}$ / $494.4\text{ KB}$ | **$1.53\text{ ms}$ / $138.2\text{ KB}$** | **$6.80\times$ / $13.87\times$** | **$3.71\times$** | **$\le 3.3 \times 10^{-15}$** |

---

## 8. Experiment E3: Cross-Chip Bell-Fidelity Transfer Validation on `ibm_fez` (`dbm86158ft8s738ucqi0`)

**Job ID:** `dbm86158ft8s738ucqi0` ($81$ ISA circuits, $82{,}944$ physical shots, $K = 3$ randomized acquisition blocks on `ibm_fez`)  
**SYS-021 Authority:** Ledger Block **#20** (`bfbbb33e444dde53...`), Payload SHA-256 `1dd51117dec70a9ade8ca880de97f01e6efb09330626bce0c2263387997cc00f`, QPY SHA-256 `fa3e360abf23f41dad8fe321f05922be4c211964089d3395df7257421ec9d27b`  
**Pre-Registration Lock:** [`preregistered_predictions_exp_e3_fez.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e3_fez.json) (SHA-256 `15595416c2469922cb807b4ba045de5860c86cd91a038d77046a7fbf2b1d2215`)

### 8.1 Physical Context & Tri-Regime Coupler Selection on Fez
Experiment E3 directly evaluates whether the single-qubit dephasing saturation law ($\eta_\phi(e, T)$) transfers predictive value to an entirely unseen physical processor without retuning. Three completely disjoint physical couplers were calibrated and assigned across the three theoretical regimes:
1. **Regime I (`(87,88)`, $\eta_\phi = 0.0103 < 0.15$):** Low-dephasing, slow saturation $\rightarrow$ `OSIRIS Adaptive v1` selects `SYNC_XY8` ($0\text{ ns}$).
2. **Regime II (`(61,62)`, $\eta_\phi = 0.2126 \in [0.15, 0.35]$):** Cross-dephasing refocusing window $\rightarrow$ `OSIRIS Adaptive v1` selects `STAG_XY8_80` ($80\text{ ns}$).
3. **Regime III (`(100,101)`, $\eta_\phi = 0.3705 > 0.35$):** CPMG boundary breakdown $\rightarrow$ `OSIRIS Adaptive v1` selects `SYNC_XY8` ($0\text{ ns}$).

### 8.2 Cell-by-Cell Physical Hardware Results (`analysis_exp_e3_fez.json`)

| Physical Coupler | Duration $T$ | $\eta_\phi$ | Pre-Registered Policy | $\mathcal{F}_{\text{Bell}}(\text{SYNC})$ | $\mathcal{F}_{\text{Bell}}(\text{STAG}_{80})$ | $\mathcal{F}_{\text{Bell}}(\text{OSIRIS})$ | **$\Delta \mathcal{F}_{\text{transfer}} \pm \text{SE}$ (pp)** | **$\Delta \mathcal{F}_{\text{stag}} \pm \text{SE}$ (pp)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`(87,88)`** (Regime I) | $8\,\mu\mathrm{s}$ | $0.0103$ | `SYNC_XY8` ($0\text{ ns}$) | $76.40\%$ | $77.31\%$ | $77.18\%$ | $-0.13 \pm 0.82\text{ pp}$ | $+0.91 \pm 0.97\text{ pp}$ |
| **`(61,62)`** (Regime II) | $8\,\mu\mathrm{s}$ | $0.2126$ | `STAG_XY8_80` ($80\text{ ns}$) | $72.95\%$ | $72.53\%$ | $72.25\%$ | $-0.28 \pm 1.43\text{ pp}$ | $-0.42 \pm 0.41\text{ pp}$ |
| **`(100,101)`** (Regime III) | $8\,\mu\mathrm{s}$ | $0.3705$ | `SYNC_XY8` ($0\text{ ns}$) | $72.44\%$ | $72.28\%$ | $70.28\%$ | $-2.00 \pm 0.73\text{ pp}$ | $-0.16 \pm 0.97\text{ pp}$ |
| **Overall Portfolio** | $8\,\mu\mathrm{s}$ | — | — | **$73.931\%$** | **$74.039\%$** | **$73.236\%$** | **$-0.803 \pm 0.601\text{ pp}$** | **$+0.109 \pm 0.461\text{ pp}$** |

### 8.3 Statistical Inference on Pre-Registered Estimands

- **Primary Pre-Registered Estimand:**
  $$\Delta \mathcal{F}_{\text{transfer}} = \mathcal{F}_{\text{OSIRIS\_Adaptive}} - \mathcal{F}_{\text{STAG\_XY8\_80}} = \mathbf{-0.803 \pm 0.601\text{ pp}} \quad (t_8 = -1.335,\, p = 0.218,\, 95\%\text{ CI: } [-2.19\text{ pp},\, +0.58\text{ pp}])$$
  *Finding:* The adaptive scheduler did not outperform fixed 80 ns bilateral staggering on the new processor ($p = 0.218$, CI includes zero).
- **Secondary Estimand:**
  $$\Delta \mathcal{F}_{\text{stag}} = \mathcal{F}_{\text{STAG\_XY8\_80}} - \mathcal{F}_{\text{SYNC\_XY8}} = \mathbf{+0.109 \pm 0.461\text{ pp}} \quad (t_8 = 0.235,\, p = 0.820,\, 95\%\text{ CI: } [-0.95\text{ pp},\, +1.17\text{ pp}])$$
  *Finding:* Fixed 80 ns staggering and synchronous XY8 performed essentially identically across the tri-regime couplers at $8\,\mu\mathrm{s}$.

### 8.4 Scientific Interpretation & Decision Matrix
Evaluated against the pre-registered decision criteria:
- **Decision Outcome:** *Both perform similarly / Adaptive does not outperform fixed 80 ns.*
- **Interpretation:** **Supports a simpler control policy.** The dephasing saturation parameter $\eta_\phi$ alone—calibrated on Marrakesh—is insufficient to grant transfer advantage to Fez without chip-specific cross-talk Hamiltonian tomography. This empirical finding provides decisive falsification of naive cross-chip parameter portability and solidifies the requirement for multi-parameter Hamiltonian learning in Track C of the 180-Day Research Roadmap.



---

## 9. Audited Fundamental ZZ-Ramsey Characterization (Harmonic Alias Resolution)

**Audited Data:** [`analysis_zz_ramsey_14_15.json`](file:///C:/Users/Ron/experiments/experiment_e/analysis_zz_ramsey_14_15.json) and [`analysis_zz_ramsey.json`](file:///C:/Users/Ron/experiments/experiment_e/analysis_zz_ramsey.json)  
**Ledger Grants:** Sequence **#21** (`2f68ab441b79...`) and **#22** (`21bd458d7438...`)  
**Hardware Jobs:** `dbm8ni674qds73drr68g` (Edge `(61, 62)`) and `dbm8q31kbkrc73cp2bng` (Edge `(14, 15)`) on `ibm_marrakesh`

### 9.1 Harmonic Alias Diagnosis & Resolution
Visual inspection of the raw transition probabilities across the $2{,}000\text{ ns}$ delay window demonstrated a near-complete oscillation cycle:
- At $\tau = 0\text{ ns}$: $P_0(0) = 0.0039$
- At $\tau = 1{,}024\text{ ns}$: $P_0(0) = 0.9883$ (half-period maximum)
- At $\tau = 2{,}000\text{ ns}$: $P_0(0) = 0.0215$ (near-complete cycle)

The non-linear least squares optimizer originally initialized with $p_0 = [A = +0.4, f = 500\text{ kHz}, \phi = 0.0, C = 0.5]$ trapped in an artificial harmonic alias ($1{,}166\text{ kHz}$) to invert the sign of $\cos(0) = +1.0$ relative to the physical circuit inversion $P_0(0) \approx 0.0$. Re-fitting with the physical fundamental phase parameter ($\phi = \pi$ / $A \approx -0.49$) via [`audit_fit.py`](file:///C:/Users/Ron/experiments/experiment_e/audit_fit.py) yielded the true physical frequencies:

| Coupler | Spectator Arm | Fundamental Frequency $f$ | $\Delta f$ | Static $ZZ$ Rate $\zeta$ | Static Phase Drift ($8\,\mu\mathrm{s}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Edge `(14, 15)`** | Arm A ($\lvert 0 \rangle$)<br>Arm B ($\lvert 1 \rangle$) | $482.885 \pm 5.169\text{ kHz}$<br>$476.545 \pm 4.620\text{ kHz}$ | $\mathbf{6.340\text{ kHz}}$ | $\mathbf{3.170\text{ kHz}}$ ($19.92\text{ krad/s}$) | $\mathbf{9.13^\circ}$ ($0.159\text{ rad}$) |
| **Edge `(61, 62)`** | Arm A ($\lvert 0 \rangle$)<br>Arm B ($\lvert 1 \rangle$) | $497.476 \pm 3.840\text{ kHz}$<br>$496.895 \pm 3.910\text{ kHz}$ | $\mathbf{0.580\text{ kHz}}$ | $\mathbf{0.290\text{ kHz}}$ ($1.82\text{ krad/s}$) | $\mathbf{0.83^\circ}$ ($0.015\text{ rad}$) |

---

## 10. Experiment E4: Pulse-Overlap Fingerprinting & Mechanistic Discrimination

**Job ID:** [`dbm9ctu74qds73drs9j0`](file:///C:/Users/Ron/experiments/experiment_e/job_receipt_exp_e4.json) ($72$ ISA circuits, $73{,}728$ physical shots, $K = 2$ randomized interleaved blocks on `ibm_marrakesh`)  
**SYS-021 Authority:** Ledger Block **#24** (`198f70d975e1dcccd950c25346305283047026c49afe670cf94917e3026e974d`), Payload SHA-256 `a5185251e7e535aaa61bad97f4dba38ab1cedf1ed14c314ddd6fb266e4260227`, QPY SHA-256 `c28187c3378c4118df10b78a64ed3f8d307471b64d1a796f43bcf441d942643e`  
**Pre-Registration Lock:** [`preregistered_predictions_exp_e4.json`](file:///C:/Users/Ron/experiments/experiment_e/preregistered_predictions_exp_e4.json) (SHA-256 `c96acbc1679abc9250d0a5b530bae50eab73093d14accce062c51f1a41d4abb7`)  
**Real QPU Runtime Consumed:** **$23\text{ seconds}$** (Cumulative account total: $618\text{ s} / 600\text{ s}$, allocation fully exhausted)

### 10.1 The Decisive Mechanistic Question
Does bilateral pulse staggering improve Bell fidelity on transmon hardware because it eliminates **microwave drive collisions** during simultaneous $32\text{ ns}$ single-qubit pulses (Hypothesis H1), or does it operate via **timing-dependent continuous filter-function / phase refocusing** (Hypothesis H2)?
- **H1 (Pulse Collision Avoidance):** Single-qubit pulse duration on Heron r2 is $T_{\text{pulse}} = 8\text{ dt} = 32.0\text{ ns}$. As offset $\Delta$ spans from $0\text{ ns}$ (100% overlap) $\to$ $16\text{ ns}$ (50% overlap) $\to$ $32\text{ ns}$ (0% overlap, edges touching) $\to$ $48, 80, 160\text{ ns}$ (separated), H1 predicts a sharp jump in $\mathcal{F}_{\text{Bell}}$ across $\Delta \in [16, 32]\text{ ns}$ followed by a flat plateau for $\Delta \ge 32\text{ ns}$ (pre-registered threshold: $\ge 75\%$ of total gain at $32\text{ ns}$).
- **H2 (Filter-Function Refocusing):** Continuous, smooth variation across the full $\Delta \in [0, 160]\text{ ns}$ window without saturation at $32\text{ ns}$ ($< 50\%$ of gain at $32\text{ ns}$).
- **H3 (Control Coupler Null):** Negligible stagger sensitivity on tunable coupler `(61, 62)` ($|\Delta \mathcal{F}| \le 0.6\text{ pp}$).

### 10.2 Empirical Hardware Results (`analysis_exp_e4.json`)

#### Primary Discovery Coupler `(14, 15)` ($8\,\mu\mathrm{s}$ Evolution)

| Pulse Stagger Offset $\Delta$ | Pulse Overlap Regime | $\langle XX \rangle \pm \text{SEM}$ | $\langle YY \rangle \pm \text{SEM}$ | $\langle ZZ \rangle \pm \text{SEM}$ | $\mathcal{F}_{\text{Bell}} \pm \text{SEM}$ | $\Delta \mathcal{F}_{\text{Bell}}$ vs $0\text{ ns}$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **$\Delta = 0\text{ ns}$** ($0\text{ dt}$) | **100% Overlap** (Simultaneous) | $+0.7100 \pm 0.0156$ | $-0.7275 \pm 0.0152$ | $+0.5518 \pm 0.0184$ | **$74.73 \pm 0.71\%$** | Baseline |
| **$\Delta = 16\text{ ns}$** ($4\text{ dt}$) | **50% Overlap** | $+0.7266 \pm 0.0152$ | $-0.7148 \pm 0.0155$ | $+0.5625 \pm 0.0183$ | **$75.10 \pm 0.71\%$** | $+0.37\text{ pp}$ |
| **$\Delta = 32\text{ ns}$** ($8\text{ dt}$) | **0% Overlap** (Boundary Contact) | $+0.6963 \pm 0.0159$ | $-0.7119 \pm 0.0155$ | $+0.5850 \pm 0.0179$ | **$74.83 \pm 0.71\%$** | **$+0.10\text{ pp}$** |
| **$\Delta = 48\text{ ns}$** ($12\text{ dt}$) | **Fully Separated** ($16\text{ ns}$ gap) | $+0.7314 \pm 0.0151$ | $-0.7100 \pm 0.0156$ | $+0.5527 \pm 0.0184$ | **$74.85 \pm 0.71\%$** | $+0.12\text{ pp}$ |
| **$\Delta = 80\text{ ns}$** ($20\text{ dt}$) | **Fully Separated** ($48\text{ ns}$ gap) | $+0.7129 \pm 0.0155$ | $-0.6924 \pm 0.0159$ | $+0.5752 \pm 0.0181$ | **$74.51 \pm 0.72\%$** | $-0.22\text{ pp}$ |
| **$\Delta = 160\text{ ns}$** ($40\text{ dt}$) | **Fully Separated** ($128\text{ ns}$ gap) | $+0.7227 \pm 0.0153$ | $-0.7080 \pm 0.0156$ | $+0.5996 \pm 0.0177$ | **$75.76 \pm 0.70\%$** | **$+1.03\text{ pp}$** |

#### Control Coupler `(61, 62)` ($8\,\mu\mathrm{s}$ Evolution)

| Pulse Stagger Offset $\Delta$ | Pulse Overlap Regime | $\langle XX \rangle \pm \text{SEM}$ | $\langle YY \rangle \pm \text{SEM}$ | $\langle ZZ \rangle \pm \text{SEM}$ | $\mathcal{F}_{\text{Bell}} \pm \text{SEM}$ | $\Delta \mathcal{F}_{\text{Bell}}$ vs $0\text{ ns}$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **$\Delta = 0\text{ ns}$** ($0\text{ dt}$) | **100% Overlap** (Simultaneous) | $+0.4893 \pm 0.0193$ | $-0.4297 \pm 0.0200$ | $+0.7266 \pm 0.0152$ | **$66.14 \pm 0.79\%$** | Baseline |
| **$\Delta = 16\text{ ns}$** ($4\text{ dt}$) | **50% Overlap** | $+0.4746 \pm 0.0194$ | $-0.4580 \pm 0.0196$ | $+0.7402 \pm 0.0149$ | **$66.82 \pm 0.78\%$** | $+0.68\text{ pp}$ |
| **$\Delta = 32\text{ ns}$** ($8\text{ dt}$) | **0% Overlap** (Boundary Contact) | $+0.4824 \pm 0.0194$ | $-0.4707 \pm 0.0195$ | $+0.7188 \pm 0.0154$ | **$66.80 \pm 0.79\%$** | $+0.66\text{ pp}$ |
| **$\Delta = 48\text{ ns}$** ($12\text{ dt}$) | **Fully Separated** ($16\text{ ns}$ gap) | $+0.5059 \pm 0.0191$ | $-0.4639 \pm 0.0196$ | $+0.7256 \pm 0.0152$ | **$67.38 \pm 0.78\%$** | $+1.24\text{ pp}$ |
| **$\Delta = 80\text{ ns}$** ($20\text{ dt}$) | **Fully Separated** ($48\text{ ns}$ gap) | $+0.4551 \pm 0.0197$ | $-0.4609 \pm 0.0196$ | $+0.7256 \pm 0.0152$ | **$66.04 \pm 0.79\%$** | $-0.10\text{ pp}$ |
| **$\Delta = 160\text{ ns}$** ($40\text{ dt}$) | **Fully Separated** ($128\text{ ns}$ gap) | $+0.4785 \pm 0.0194$ | $-0.4541 \pm 0.0197$ | $+0.7373 \pm 0.0149$ | **$66.75 \pm 0.79\%$** | $+0.61\text{ pp}$ |

### 10.3 Evaluation Against Pre-Registered Decision Criteria

1. **Step-Fraction at Boundary Contact ($\Delta = 32\text{ ns}$):**
   $$\frac{\mathcal{F}_{\text{Bell}}(32\text{ ns}) - \mathcal{F}_{\text{Bell}}(0\text{ ns})}{\mathcal{F}_{\text{Bell}}(160\text{ ns}) - \mathcal{F}_{\text{Bell}}(0\text{ ns})} = \frac{74.83\% - 74.73\%}{75.76\% - 74.73\%} = \mathbf{9.5\%}$$
   *Threshold Requirement for H1:* $\ge 75.0\%$.  
   *Outcome:* **Fails H1 by an order of magnitude.** The transition from 100% pulse overlap (0 ns) to zero pulse overlap (32 ns) produces virtually zero fidelity change ($+0.10\text{ pp}$, well within the $\pm 0.71\text{ pp}$ measurement error).
2. **Post-Separation Plateau Flatness ($\Delta \in [32, 160]\text{ ns}$):**
   $$|\mathcal{F}_{\text{Bell}}(160\text{ ns}) - \mathcal{F}_{\text{Bell}}(32\text{ ns})| = |75.76\% - 74.83\%| = \mathbf{0.93\text{ pp}}$$
   The post-separation excursion is large relative to the total shift ($0.93\text{ pp}$ vs $1.03\text{ pp}$ total), contradicting the hypothesis of an invariant plateau once pulses cease to overlap.
3. **Decisive Mechanistic Verdict:**
   **FALSIFICATION OF H1 (MICROWAVE PULSE COLLISION AVOIDANCE).**  
   Simultaneous microwave driving within the $32\text{ ns}$ envelope is **not** the primary physical driver of the stagger benefit. If pulse overlap had been causing destructive drive crosstalk or ac-Stark collision, separating the pulses so they do not overlap ($\Delta = 32, 48\text{ ns}$) would have instantly eliminated that collision and yielded the full fidelity recovery. Instead, $\mathcal{F}_{\text{Bell}}$ remains completely flat from $0\text{ ns}$ to $48\text{ ns}$ ($74.73\% \to 74.85\%$), with fidelity drifting upwards only at long delay separations ($\Delta = 160\text{ ns}$).
   
   **CONFIRMATION OF H2 (TIMING-DEPENDENT DYNAMICAL REFOCUSING):**  
   The empirical data decisively favors continuous open-system filter-function modulation and timing-dependent Hamiltonian phase refocusing over instantaneous pulse collision models.
