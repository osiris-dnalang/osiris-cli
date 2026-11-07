# OSIRIS-HP-003: Pre-Registration Specification
## Two-Qubit Quantum Capacity & Multi-Photon Hayden–Preskill Scaling Benchmark

**Protocol Identifier:** `OSIRIS-HP-003`  
**Governing Policy:** SYS-021 (Zero Self-Supplied Authorization) / Gate 0 Conformance  
**Lead Investigator:** Devin Phillip Davis / Enki  
**Target Hardware:** IBM Quantum Heron r2 (`ibm_fez` / `ibm_kingston`, 156-qubit heavy-hex processors)  
**Execution Topology:** 8-qubit connected transmon subgraph  
**Timestamp:** November 7, 2026  

---

### 1. Abstract & Scientific Purpose
In `OSIRIS-HP-001` and `OSIRIS-HP-002`, we experimentally demonstrated restricted-access quantum information recovery for a single-qubit message ($k = 1$) across a 6-qubit open quantum processor, confirming off-diagonal Bell entanglement fidelity $\mathcal{F}_{\text{ent}} = 68.37 \pm 0.09\%$ with verified subsystem decoupling ($I(R:C)=0, I(R:DE)=2\text{ bits}$).

`OSIRIS-HP-003` scales this protocol to a **two-qubit message** ($k = 2$) across an 8-qubit transmon register. This provides an experimental test of the **Hayden–Preskill Quantum Capacity Theorem**:
> *To retrieve a $k$-qubit quantum message scrambled into an old, maximally entangled black hole, the external observer must collect at least $k + c$ photons of Hawking radiation.*

For $k = 2$:
1. When **both late radiation photons** $D = (D_1, D_2)$ are collected, joint radiation contains the complete 4 bits of quantum mutual information:
   $$I(R_1 R_2 : D_1 D_2 E_1 E_2) = 4.000000\ \text{bits}.$$
   Restricted decoding succeeds, achieving recovery of both message qubits.
2. When only a **single photon** $D_1$ is collected (Arm B-Deficient), the quantum information capacity is strictly capped at 1 qubit:
   $$I(R_1 R_2 : D_1 E_1 E_2) = 2.000000\ \text{bits}.$$
   The joint two-qubit message cannot be reconstructed, and joint recovery collapses.

---

### 2. Register Definitions & Physical Layout
The 8-qubit operational system is partitioned into five distinct physical subsystems:
1. **Reference Register $R$:** Qubits $(R_1, R_2)$ (qubits 0, 1) — retain reference entanglement with the messages.
2. **Message Register $M$:** Qubits $(M_1, M_2)$ (qubits 2, 3) — injected into the black hole.
3. **Black Hole Remnant Register $B$:** Qubits $(B_1, B_2)$ (qubits 4, 5) — internal black hole microstates.
4. **Early Radiation Register $E$:** Qubits $(E_1, E_2)$ (qubits 6, 7) — prior Hawking radiation entangled with $B$.
5. **Late Radiation Register $D$:** Qubits $(D_1, D_2)$ — the emission ports of the scrambling unitary $U_{MB}$ acting on $(M_1, M_2, B_1, B_2)$.

---

### 3. Five-Arm Comparative Design

| Arm Index | Protocol Arm | Accessible Qubits | Remnant Status | Early Radiation State | Scrambler | Theoretical Capacity |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Arm A** | Full-Access Inverse Control | $D_1, D_2, C_1, C_2$ | Unquarantined (Full $U^\dagger$) | Entangled $|\Phi^+\rangle^{\otimes 2}$ | Matched $U_1$ | Ideal Reversibility ($100\%$) |
| **Arm B** | Restricted Recovery (Full Capacity) | $D_1, D_2, E_1, E_2$ | **Quarantined ($C_1, C_2$ traced out)** | Entangled $|\Phi^+\rangle^{\otimes 2}$ | Matched $U_1$ | Full Recovery ($4.0\text{ bits}$) |
| **Arm B-Def** | Sub-Capacity Control (Single Photon) | $D_1, E_1, E_2$ | **Quarantined ($C_1, C_2, D_2$ traced out)** | Entangled $|\Phi^+\rangle^{\otimes 2}$ | Matched $U_1$ | **Deficient ($2.0\text{ bits}$ capacity)** |
| **Arm B-Ctrl**| Separable Trapped Control | $D_1, D_2, E_1, E_2$ | **Quarantined ($C_1, C_2$ traced out)** | Separable $|0000\rangle$ | Matched $U_1$ | Trapped Noise Floor ($25\%$) |
| **Arm B-Held**| Scrambler Specificity Gate | $D_1, D_2, E_1, E_2$ | **Quarantined ($C_1, C_2$ traced out)** | Entangled $|\Phi^+\rangle^{\otimes 2}$ | Held-Out $U_2$ | Specificity Floor ($25\%$) |

---

### 4. Mathematical Decoupling & Firewall Audit Invariants
Before hardware submission, the compiled circuit must mathematically satisfy:
1. $I(R_1 R_2 : D_1 D_2) = 0.000000\text{ bits}$ (Late photons alone carry 0 message information).
2. $I(R_1 R_2 : E_1 E_2) = 0.000000\text{ bits}$ (Early radiation alone carries 0 message information).
3. $I(R_1 R_2 : C_1 C_2) = 0.000000\text{ bits}$ (Black hole remnant retains 0 message information).
4. $I(R_1 R_2 : D_1 D_2 E_1 E_2) = 4.000000\text{ bits}$ (Joint radiation contains 100% of message quantum information).
5. $I(R_1 R_2 : D_1 E_1 E_2) = 2.000000\text{ bits}$ (Single photon collection strictly bounds information to 1 qubit).
6. **Firewall Quarantine Invariant:** Exactly 0 gates connect the decoder to physical qubits $(C_1, C_2)$ in Arms B, B-Def, B-Ctrl, and B-Held.

---

### 5. Pre-Registered Hypotheses & Falsification Criteria

1. **Hypothesis $H_1$ (Reversibility Positive Control):**
   $$\mathcal{F}_{\text{ent}}^{(1)}(\text{Arm A}) \ge 0.85,\quad \mathcal{F}_{\text{ent}}^{(2)}(\text{Arm A}) \ge 0.85$$
   Falsified if either reconstructed message arm fails to achieve $\ge 85\%$ Bell fidelity under full access.

2. **Hypothesis $H_2$ (Primary Multi-Qubit Restricted Recovery):**
   $$\bar{\mathcal{F}}_{\text{ent}}(\text{Arm B}) = \frac{1}{2}\left(\mathcal{F}_{\text{ent}}^{(1)} + \mathcal{F}_{\text{ent}}^{(2)}\right) > 0.50$$
   Falsified if the average reconstructed Bell fidelity does not strictly exceed the classical separability threshold ($0.50$) with $p < 10^{-4}$ (entanglement witness $\mathcal{W} < 0$).

3. **Hypothesis $H_3$ (Quantum Capacity Threshold / Photon Deprivation):**
   $$\mathcal{F}_{\text{joint}}(\text{Arm B-Def}) \le 0.35$$
   Falsified if collecting only a single photon $D_1$ achieves coherent 2-qubit reconstruction ($\mathcal{F} > 0.50$). Single-photon collection must fail to recover the second qubit, confirming the $k=2$ capacity bound.

4. **Hypothesis $H_4$ (Separable Entanglement Bridge):**
   $$\bar{\mathcal{F}}_{\text{ent}}(\text{Arm B-Ctrl}) \le 0.35$$
   Falsified if message information is recovered without prior EPR entanglement between black hole and early radiation.

5. **Hypothesis $H_5$ (Held-Out Scrambler Specificity):**
   $$\bar{\mathcal{F}}_{\text{ent}}(\text{Arm B-Held}) \le 0.35$$
   Falsified if applying the fixed decoder $V_{\text{dec}}(U_1)$ to an unaligned scrambler $U_2$ yields $\mathcal{F} > 0.50$.
