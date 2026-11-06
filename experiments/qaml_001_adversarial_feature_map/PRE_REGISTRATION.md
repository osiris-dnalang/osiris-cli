# OSIRIS-QAML-001: Pre-Registered Hardware Benchmark Specification
**Protocol:** Adversarial Robustness of Staggered-DD Transmon Quantum Feature Maps vs. Classical CNNs  
**Target Hardware:** IBM Quantum Heron r2 (`ibm_marrakesh`, 156-qubit transmon)  
**Execution Authority:** SYS-021 (Operator: `Devin Phillip Davis / Enki`)  
**Statistical Power Floor:** $N \ge 33{,}500$ shots per basis per arm  
**Status:** FROZEN & PRE-REGISTERED

---

## 1. Scientific Objective
This benchmark empirically tests whether mapping high-dimensional data into quantum Hilbert spaces via second-order Pauli feature maps—when protected by bipartite staggered dynamical decoupling (`stag_xy8`)—provides verifiable adversarial robustness against classical norm-bounded gradient attacks (PGD and FGSM), or whether purported quantum advantages collapse into the empirical $1.03\text{ pp}$ transmon calibration noise floor.

---

## 2. Experimental Arms & Conditions

The benchmark evaluates five matched arms across an 8-qubit nearest-neighbor transmon chain ($[1, 2, 3, 4, 5, 6, 7, 8]$):

| Arm ID | Architecture / Policy | Pulse Schedule / Timing | Purpose |
| :--- | :--- | :--- | :--- |
| **Arm 0** | **Classical Baseline** | 4-layer CNN with LeakyReLU | Classical benchmark reference |
| **Arm 1** | **Bare Quantum Feature Map** | Unmitigated idle windows ($0\text{ ns}$) | Baseline environmental decoherence |
| **Arm 2** | **Synchronous XY8 Map** | Simultaneous XY8 ($\Delta = 0\text{ ns}$) | Standard DD baseline control |
| **Arm 3** | **Staggered XY8 Map (OSIRIS)** | Bipartite offset ($\Delta = 80\text{ ns}$) | Test spectator crosstalk suppression |
| **Arm 4** | **Identical A/A Control** | Bipartite offset ($\Delta = 80\text{ ns}$) | **Mandatory real-time drift monitor** |

---

## 3. Quantum Feature Map Specification

Data inputs $x \in [0, \pi]^8$ are encoded using the second-order non-linear Pauli expansion:
$$U_{\Phi}(x) = U_Z(x) \cdot H^{\otimes 8} \cdot U_Z(x) \cdot H^{\otimes 8}$$
where the phase diagonal unitary is:
$$U_Z(x) = \exp\left( -i \sum_{j=1}^8 x_j Z_j - i \sum_{j < k}^8 (\pi - x_j)(\pi - x_k) Z_j Z_k \right)$$

During the two-qubit $ZZ$ evolution intervals, dynamical decoupling pulses ($X\text{--}Y\text{--}X\text{--}Y\text{--}Y\text{--}X\text{--}Y\text{--}X$) are injected:
- **Sublattice A (Even qubits: 2, 4, 6, 8):** Pulse centers at $t_k - \Delta / 2$.
- **Sublattice B (Odd qubits: 1, 3, 5, 7):** Pulse centers at $t_k + \Delta / 2$ ($\Delta = 80\text{ ns}$).

---

## 4. Adversarial Attack Generation Harness

Adversarial perturbations $\delta$ are generated against model logits $\mathcal{Z}(x)$ using Projected Gradient Descent (PGD-$\ell_\infty$):
$$x^{t+1} = \Pi_{x + [-\epsilon, \epsilon]^8} \left( x^t + \alpha \cdot \text{sign}\left( \nabla_x \mathcal{L}(\theta, x^t, y) \right) \right)$$
- **Perturbation Budgets:** $\epsilon \in \{0.02, 0.05, 0.10\}$
- **Iterations:** $K = 10$ steps with step size $\alpha = \epsilon / 4$
- **Baseline Comparison Attack:** Single-step FGSM ($\alpha = \epsilon$)

---

## 5. Statistical Power & Sample Size Derivation

Based on the empirical findings of the Heron r2 campaign (`manuscript_heron_r2_staggered_dd_null_result.tex`):
- Transmon accidental A/A noise floor: $\sigma_{\text{A/A}} = 1.03\text{ pp}$ RMS.
- Standard shot error per block ($N_{\text{block}} = 1{,}024$ shots): $\sigma_{\text{block}} \approx 1.43\text{ pp}$.
- Resolving a minimum true difference $\Delta \mathcal{F} = 0.50\text{ pp}$ at $2\sigma$ ($95\%$ confidence):
  $$N_{\text{req}} \ge 2 \cdot \left(\frac{1.43\text{ pp}}{0.25\text{ pp}}\right)^2 \times 1{,}024 = 33{,}460 \approx \mathbf{33{,}500\text{ shots per basis per arm}}$$
- **Execution Protocol:** 33 independent randomized acquisition blocks $\times 1{,}024$ shots per evaluation point.

---

## 6. Pre-Registered Hypotheses & Falsification Criteria

1. **Hypothesis 1 (Clean Baseline Verification):**
   - *Claim:* Quantum Feature Map achieves clean accuracy $\ge 85.0\%$ on held-out test partition.
   - *Falsification:* Clean accuracy $< 80.0\%$ (invalidates feature encoding capacity).

2. **Hypothesis 2 (Quantum Adversarial Resilience vs. Classical CNN):**
   - *Claim:* Under PGD-$\ell_\infty$ attack ($\epsilon = 0.05$), Arm 3 (Staggered XY8) retains an accuracy advantage over Arm 0 (Classical CNN):
     $$\Delta_{\text{adv}} = \text{Acc}_{\text{Arm 3}}(\epsilon=0.05) - \text{Acc}_{\text{Arm 0}}(\epsilon=0.05) \ge +5.0\text{ pp}$$
   - *Falsification:* $\Delta_{\text{adv}} < +2.0\text{ pp}$ or confidence interval encompasses zero.

3. **Hypothesis 3 (Staggered Decoupling Advantage over Synchronous DD):**
   - *Claim:* Arm 3 outperforms Arm 2 under adversarial perturbation by suppressing spectator $ZZ$ phase drift:
     $$\Delta_{\text{stag}} = \text{Acc}_{\text{Arm 3}}(\epsilon=0.05) - \text{Acc}_{\text{Arm 2}}(\epsilon=0.05) \ge +1.50\text{ pp} \quad (Z \ge 3.0\sigma)$$
   - *Falsification:* $\Delta_{\text{stag}} < +0.50\text{ pp}$ or $p > 0.01$.

4. **Hypothesis 4 (A/A Drift Quarantine Gate):**
   - *Claim:* The difference between identical arms $|\text{Acc}_{\text{Arm 3}} - \text{Acc}_{\text{Arm 4}}|$ must not exceed $1.03\text{ pp}$ RMS across blocks.
   - *Action:* If observed A/A difference exceeds $1.50\text{ pp}$, the entire hardware run is rejected and classified as a **Calibration Drift Incident**.
