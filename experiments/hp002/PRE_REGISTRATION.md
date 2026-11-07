# OSIRIS-HP-002: Pre-Registered Hardware Benchmark Specification
**Protocol Title:** Restricted Quantum Information Recovery Certification with Held-Out Scrambler Controls  
**Target Architecture:** IBM Quantum Heron r2 (`ibm_fez` or `ibm_marrakesh`, 156-qubit heavy-hex)  
**Governance Standard:** Gate 0 / SYS-021 Immutable Cryptographic Ledger  
**Execution Authority:** Operator `Devin Phillip Davis / Enki` (Gated upon QAML-001 completion)  
**Status:** STAGED & PRE-REGISTERED (DISPATCH GATED)

---

## 1. Scientific Objective

The OSIRIS-HP-002 benchmark experimentally tests the canonical Hayden–Preskill quantum information recovery protocol on physical superconducting qubits. It certifies that a one-qubit quantum message $M$ entangled with an external reference $R$ and scrambled into an old black hole can be reconstructed by an observer possessing *only* the emitted late radiation $D$ and the entangled early radiation $E$, while the internal black hole remnants $C_1, C_2$ remain strictly inaccessible behind the event horizon.

---

## 2. Six-Qubit Register Roles & Subsystem Mapping

The protocol defines a strict six-qubit bipartite register mapping on physical transmon qubits:

| Register | Qubit Index | Subsystem Role | Physical Subgraph Node (`ibm_fez`) |
| :---: | :---: | :--- | :---: |
| **$R$** | 0 | External reference qubit (held outside, un-evolved) | Qubit 14 |
| **$M \to D$** | 1 | Message qubit input $\to$ Emitted late radiation photon output | Qubit 15 |
| **$B_1 \to C_1$** | 2 | Black hole input qubit $\to$ Internal quarantined remnant output | Qubit 19 |
| **$B_2 \to C_2$** | 3 | Black hole input qubit $\to$ Internal quarantined remnant output | Qubit 35 |
| **$E_1$** | 4 | Early radiation photon (maximally entangled with $B_1$) | Qubit 13 |
| **$E_2$** | 5 | Early radiation photon (maximally entangled with $B_2$) | Qubit 34 |

### Mathematical Access Boundary Guarantees:
1. **Decoupling from Remnant:** $I(R : C_1 C_2) = 0.000000\text{ bits}$ (no message information is retained in the black hole).
2. **Individual Radiation Insufficiency:** $I(R : D) = 0.000000\text{ bits}$ and $I(R : E_1 E_2) = 0.000000\text{ bits}$ (neither late radiation nor early radiation alone reveals the message).
3. **Joint Recovery Completeness:** $I(R : D E_1 E_2) = 2.000000\text{ bits}$ (the joint radiation subsystem contains the full message quantum information).
4. **Boundary Isolation:** The decoding unitary $V_{\text{dec}}$ operates exclusively on qubits $(1, 4, 5)$. Zero gates connect the decoder to remnants $(2, 3)$.

---

## 3. Experimental Arms & Frozen Circuit Volume

The benchmark evaluates 4 experimental conditions across 3 Pauli measurement bases ($XX, YY, ZZ$) and 3 randomized acquisition blocks:

| Arm ID | Scrambler Unitary | Early Radiation State | Decoder Subsystem | Purpose & Theoretical Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **Arm A** | Matched Scrambler $U_1$ | Entangled $|\Phi^+\rangle_{BE}$ | Full Access ($D, C_1, C_2$) | Positive Control Ceiling ($\mathcal{F}_{\text{ideal}} = 1.000000$) |
| **Arm B** | Matched Scrambler $U_1$ | Entangled $|\Phi^+\rangle_{BE}$ | Restricted Access ($D, E_1, E_2$) | **Primary Endpoint: Restricted Recovery ($\mathcal{F}_{\text{ideal}} = 1.000000$)** |
| **Arm B Control** | Matched Scrambler $U_1$ | Separable $|0000\rangle_{BE}$ | Restricted Access ($D, E_1, E_2$) | **Negative Control: Trapped Information ($\mathcal{F}_{\text{ideal}} = 0.250000$)** |
| **Arm B Held-Out** | Held-Out Scrambler $U_2$ | Entangled $|\Phi^+\rangle_{BE}$ | Fixed Decoder $V(U_1)$ on ($D, E$) | **Specificity Gate: Rules Out Identity Routing ($\mathcal{F}_{\text{ideal}} = 0.250000$)** |

### Frozen Hardware Execution Budget:
- **Circuits per block:** 4 arms $\times$ 3 bases ($XX, YY, ZZ$) = 12 circuits
- **Randomized blocks:** 3 blocks
- **Total frozen circuits:** $12 \times 3 = \mathbf{36\text{ ISA circuits}}$
- **Shots per circuit:** $2{,}048$ shots
- **Total physical shots:** $36 \times 2{,}048 = \mathbf{73{,}728\text{ physical shots}}$
- **Estimated QPU runtime:** $\approx 24\text{ seconds}$ (well within remaining 90s allocation)

---

## 4. Pre-Registered Falsification Criteria & Decision Rules

1. **Criterion 1 (Primary Endpoint — Restricted Recovery):**
   - *Claim:* Under matched scrambling $U_1$, Arm B achieves an entanglement fidelity exceeding the classical separability threshold:
     $$\mathcal{F}_{\text{ent}}(\text{Arm B}) > 0.50 \iff \mathcal{W} = 0.50 - \mathcal{F}_{\text{ent}} < 0 \quad (p < 10^{-10})$$
   - *Falsification:* Lower bound of $99\%$ confidence interval falls below $0.50$.

2. **Criterion 2 (Secondary Endpoint — Recovery Gain over Trapped Control):**
   - *Claim:* Restricted recovery requires early entanglement, exhibiting a statistically defensible gain:
     $$\Delta \mathcal{F}_{\text{ent}} = \mathcal{F}_{\text{ent}}(\text{Arm B}) - \mathcal{F}_{\text{ent}}(\text{Arm B Control}) \ge +50.0\text{ pp} \quad (Z \ge 10.0\sigma)$$
   - *Falsification:* $\Delta \mathcal{F}_{\text{ent}} < +25.0\text{ pp}$ or confidence interval encompasses zero.

3. **Criterion 3 (Scrambler Specificity Gate — Held-Out Control):**
   - *Claim:* Applying the fixed decoder $V(U_1)$ to the held-out scrambler $U_2$ yields separable fidelity:
     $$\mathcal{F}_{\text{ent}}(\text{Arm B Held-Out}) \le 0.50$$
   - *Falsification:* $\mathcal{F}_{\text{ent}}(\text{Arm B Held-Out}) > 0.50$ (invalidates claims of quantum decoding; indicates trivial identity routing or subsystem leakage).

4. **Criterion 4 (Reversibility Positive Control Ceiling):**
   - *Claim:* Arm A achieves $\mathcal{F}_{\text{ent}}(\text{Arm A}) \ge 0.90$ under physical readout noise.
   - *Falsification:* Arm A fidelity $< 0.80$ (indicates excessive hardware calibration drift).
