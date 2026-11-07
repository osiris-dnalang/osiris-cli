# OSIRIS-QAML-002: Pre-Registered High-Sample Adversarial Hardware Benchmark Specification
**Protocol:** Multi-Depth Adversarial Robustness of Staggered-DD Transmon Quantum Feature Maps vs. Classical Baselines  
**Target Hardware:** IBM Quantum Heron r2 (`ibm_marrakesh` / `ibm_fez`, 156-qubit transmon)  
**Execution Authority:** SYS-021 (Operator: `Devin Phillip Davis / Enki`)  
**Sample Resolution:** $N_{\text{test}} \ge 50$ test samples ($2.0\text{ pp}$ discrete resolution)  
**Statistical Power Floor:** $N \ge 33{,}500$ shots per evaluation point (33 blocks $\times 1{,}024$ shots)  
**Status:** PRE-REGISTERED & STAGED  

---

## 1. Scientific Objective & Motivation

The preliminary benchmark `OSIRIS-QAML-001` evaluated adversarial accuracy on $N_{\text{test}} = 5$ samples, producing a discrete $\pm 20\text{ pp}$ step size that obscured true comparative efficacy and necessitated formal methodological quarantine.

`OSIRIS-QAML-002` resolves this statistical power deficit by scaling to:
1. **High Sample Density:** $N_{\text{test}} = 50$ test samples from an 8-dimensional non-linear classification task (binary hypersphere separation).
2. **Multi-Depth Circuit Scaling:** Evaluating depth layers $D \in \{2, 4, 6, 8\}$ to pinpoint the exact circuit depth threshold where spectator crosstalk suppression via bipartite staggered dynamical decoupling (`stag_xy8`) outperforms standard synchronous decoupling (`sync_xy8`).
3. **Adversarial Threat Continuum:** Standard clean inputs ($\epsilon = 0.00$), PGD-$\ell_\infty$ attacks ($\epsilon \in \{0.02, 0.05, 0.10\}$, 10 steps, $\alpha = \epsilon/4$), and single-step FGSM.

---

## 2. Experimental Arms & Conditions

The benchmark evaluates five matched arms across an 8-qubit heavy-hex coupling chain:

| Arm ID | Policy | Decoupling Schedule | Purpose |
| :--- | :--- | :--- | :--- |
| **Arm 0** | **Classical Baseline** | 4-layer MLP / CNN with LeakyReLU | Classical reference standard |
| **Arm 1** | **Bare Quantum Feature Map** | Unmitigated idle windows | Environmental decoherence baseline |
| **Arm 2** | **Synchronous XY8 Map** | Simultaneous XY8 ($\Delta = 0\text{ ns}$) | Standard dynamical decoupling baseline |
| **Arm 3** | **Staggered XY8 Map (OSIRIS)**| Bipartite offset ($\Delta = 80\text{ ns}$) | Cross-talk & spectator dephasing cancellation |
| **Arm 4** | **Identical A/A Control** | Bipartite offset ($\Delta = 80\text{ ns}$) | Real-time processor calibration drift monitor |

---

## 3. Quantum Feature Map & Layer Scaling

For $x \in [0, \pi]^8$ and layer depth $D \in \{2, 4, 6, 8\}$:
$$U_{\Phi}^{(D)}(x) = \prod_{d=1}^D \left[ U_Z(x) \cdot H^{\otimes 8} \right]$$
where the phase unitary is:
$$U_Z(x) = \exp\left( -i \sum_{j=1}^8 x_j Z_j - i \sum_{j < k}^8 (\pi - x_j)(\pi - x_k) Z_j Z_k \right)$$

During the two-qubit $ZZ$ evolution intervals, dynamical decoupling sequences ($X\text{--}Y\text{--}X\text{--}Y\text{--}Y\text{--}X\text{--}Y\text{--}X$) are inserted:
- **Sublattice A (Even qubits: 0, 2, 4, 6):** Center at $t_k - \Delta/2$
- **Sublattice B (Odd qubits: 1, 3, 5, 7):** Center at $t_k + \Delta/2$ ($\Delta = 80\text{ ns}$)

---

## 4. Pre-Registered Hypotheses & Success Criteria

- **$H_1$ (Statistical Power Resolution):** With $N_{\text{test}} = 50$, standard error on accuracy is bounded by $\mathrm{SEM} \le 3.5\text{ pp}$. The discrete $\pm 20\text{ pp}$ step size of QAML-001 is eliminated.
- **$H_2$ (High-Depth Staggering Advantage):** At deep circuit layers ($D \ge 6$), spectator crosstalk accumulation degrades `sync_xy8`. The staggered map demonstrates a statistically significant adversarial accuracy gain:
  $$\Delta \mathrm{Acc}(D \ge 6) = \mathrm{Acc}_{\text{stag}} - \mathrm{Acc}_{\text{sync}} \ge +4.0\text{ pp} \quad (p < 0.01)$$
- **$H_3$ (A/A Drift Quarantine Gate):** The difference between the staggered arm and its identical A/A control must not exceed $|\mathrm{Acc}_{\text{stag}} - \mathrm{Acc}_{\text{aa}}| \le 2\sigma_{\text{A/A}} = 2.06\text{ pp}$. Any excess invalidates the run as processor calibration drift.
- **$H_4$ (Classical vs Quantum Robustness Margin):** At high perturbation budget ($\epsilon = 0.10$), the protected quantum feature map maintains retention $\mathrm{Acc}_{\text{stag}}(\epsilon=0.10) / \mathrm{Acc}_{\text{stag}}(\epsilon=0) \ge 0.50$, exceeding the classical baseline collapse threshold.
