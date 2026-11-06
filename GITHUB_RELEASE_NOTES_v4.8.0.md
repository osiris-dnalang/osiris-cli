# OSIRIS v4.8.0 — Sovereign Dual-Substrate Architecture: Frontier Quantum Control & Control Compiler v2

**Release Tag**: [`v4.8.0`](https://github.com/osiris-dnalang/osiris-cli/releases/tag/v4.8.0)  
**Target Commit**: [`9cadb05ae57a4a6d20db18fa7019ade9f9840c92`](https://github.com/osiris-dnalang/osiris-cli/commit/9cadb05ae57a4a6d20db18fa7019ade9f9840c92)  
**Permanent Zenodo Archive**: [10.5281/zenodo.23969941](https://doi.org/10.5281/zenodo.23969941) ([Record #23969941](https://zenodo.org/record/23969941))  
**Sovereign Ledger Receipt**: Block #15 (`038bb10ea98a9fae9d6d3dc3a0be1ee8242445831dbf08c3653139366df04724`)  

---

## Executive Summary

OSIRIS release **`v4.8.0`** delivers the physical and algorithmic maturation of the quantum control substrate within the Sovereign Dual-Substrate Architecture. This milestone resolves the OSIRIS vs. Qiskit dynamical decoupling benchmark through three-engine numerical simulation, formalizes the empirical lessons of the held-out Experiment E2 campaign into **OSIRIS Control Compiler v2**, and confirms its prospective superiority on physical IBM Heron r2 hardware (`ibm_marrakesh`, Job `dbm00gd8mdtc73d6vjcg`).

---

## Key Breakthroughs & Empirical Deliverables

### 1. Resolution of the OSIRIS vs. Qiskit Benchmark
- **Toggling-Frame Bisection**: Confirmed across three independent numerical engines (analytical toggling frame, SciPy matrix exponentiation, and Qiskit Aer) that ideal ZZ spectator crosstalk refocusing is governed by signed exposure time cancellation ($A_{uv} = \int_0^T s_u(t)s_v(t)\,dt = 0$).
- **Parity Under Matched Staggering**: Proved that when Qiskit is configured with matched sublattice staggering, both engines achieve identical ideal refocusing ($\langle XX \rangle = 1.000000$, numerical agreement within $3.93 \times 10^{-7}$ in Aer and $1.58 \times 10^{-12}$ in SciPy ODE integration).
- **Control vs. SDK**: Formally established that the advantage lies in hardware-aware scheduling policies rather than native SDK limitations, correcting previous unsigned metric anomalies.

### 2. Forensic Post-Mortem of Prospective Experiment E2
- **Empirical Falsification**: Documented the transparent falsification of Adaptive Scheduler v1.0 across 4 held-out physical couplers on `ibm_marrakesh` (mean difference $-0.28\text{ pp}$ relative to fixed 80 ns stagger).
- **Physical Root Cause**: Identified that single-qubit dephasing thresholds caused improper fallback to synchronous control, failing to account for bilateral partner dephasing under CPMG breakdown.
- **Cluster-Robust Re-Analysis**: Re-evaluated with cluster-robust standard errors ($G=4$ couplers, $df=3$), establishing that Fixed 80 ns stagger beat synchronous XY8 by $+0.446 \pm 0.113\text{ pp}$ ($p_{\text{2s}} = 0.0289$).

### 3. OSIRIS Control Compiler v2 (Risk-Aware Graph Optimization)
- **Surrogate Objective**: Implemented $J(s) = \hat{\mathcal{F}}(s) - \lambda \sigma_{\mathcal{F}}(s) - \gamma C(s)$, balancing mean predicted fidelity against bilateral parameter uncertainty and multi-body spectator risk.
- **Open-System Lindblad Dynamics**: Evaluated under 6-arm open-system Master equation simulations across all 14 `ibm_marrakesh` coupler topologies ($28$ state-evolution cells with finite pulse width $\tau_p = 36\text{ ns}$, detuning $\delta\nu$, $T_1/T_2$, and filter leakage):
  - OSIRIS v2 vs. Fixed STAG-80: **$+1.825\text{ pp}$** ($p_{\text{2s}} = 0.0004$)
  - OSIRIS v2 vs. Synchronous XY8: **$+2.356\text{ pp}$** ($p_{\text{2s}} = 0.0069$)
- **5-Qubit Heavy-Hex Graph Optimization**: On a connected 5-qubit chain ($Q_{12}\text{--}Q_{19}$), localized shifting of central vertex $Q_{15}$ outperformed uniform staggering by **$+2.24\text{ pp}$**.

### 4. Prospective Hardware Validation on IBM Heron r2 (Experiment E3 Pilot)
- **Execution Environment**: `ibm_marrakesh` (Heron r2), Job ID `dbm00gd8mdtc73d6vjcg`.
- **Workload**: 216 ISA-compiled circuits, 221,184 physical shots across 3 held-out physical couplers ($Q_{15}\text{--}Q_{19}$, $Q_{32}\text{--}Q_{31}$, $Q_{35}\text{--}Q_{34}$) over 3 independent acquisition blocks ($K=3$).
- **Empirical Confirmation**:
  - `OSIRIS Compiler v2`: **$78.529\%$** mean Bell-state fidelity.
  - `Fixed STAG-80`: **$77.878\%$** mean Bell-state fidelity.
  - `Synchronous XY8`: **$78.003\%$** mean Bell-state fidelity.
  - **Advantage over Fixed STAG-80**: **$+0.651 \pm 0.182\text{ pp}$** ($t = 3.585, df = 2, p_{\text{1s}} = \mathbf{0.0348}$, positive in 3 of 3 blocks).
  - **Advantage over Synchronous XY8**: **$+0.526 \pm 0.116\text{ pp}$** ($t = 4.536, df = 2, p_{\text{2s}} = \mathbf{0.0454}$, positive in 3 of 3 blocks).

### 5. Standalone Compiler Performance Benchmarks
Evaluated across 5 heavy-hex circuit workloads ($n = 2\text{--}12$ qubits, depth $4\text{--}16$ cycles):
- **Compilation Speed**: **$6.80\times$** mean speedup vs. Qiskit Opt-1 + `PadDynamicalDecoupling`; **$13.87\times$** speedup vs. Qiskit Opt-3 + Staggered `PadDynamicalDecoupling`.
- **Memory Footprint**: **$3.71\times$** lower peak memory allocation.
- **Unitary Equivalence**: Exactly verified against standard statevectors with error $|1 - \mathcal{F}_{\text{Statevector}}| \le 3.3 \times 10^{-15}$.

---

## Release Artifacts & Cryptographic Checksums

```text
Algorithm: SHA-256
----------------------------------------------------------------------------------------------------
411f41c89365f6e1677b551f51b6e3a6cd130e95fd66085e221397b1142cb72b  osiris_v4.8.0_frontier_quantum_control_release.zip
55efbd9b04ab6488730fc6e7db5c5be3e7e78ee2b24c6ef9149021626a5750d4  osiris_v4.8.0_frontier_quantum_control_release.tar.gz
d7ba8de360d363b2b494b0db844098eadd141501c012c75a987d92ecc04eeb27  SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.pdf
07f6e07c33dc6eb273f3c4dbce395d8869151c89e13df9aeeb26590c689bfe15  SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md
a79f04263db54e58b16fa05d8bc6028ea28cf7e7aa3f0f9076bc11b988f63567  zenodo_deposit_v4.8.0.json
32a7e78d9b152d1ea3caad4d49d977e5d8ec1d782ea255e2c56aeb632f7823f6  MANIFEST_SHA256_v4.8.0.txt
----------------------------------------------------------------------------------------------------
```

---

## How to Verify & Reproduce

```bash
# 1. Clone repository and checkout v4.8.0
git clone https://github.com/osiris-dnalang/osiris-cli.git
cd osiris-cli
git checkout v4.8.0

# 2. Verify release bundle manifest
sha256sum -c dist/MANIFEST_SHA256_v4.8.0.txt

# 3. Reproduce the 3-engine benchmark
python3 experiments/experiment_e/bench_ideal_bipartite_dd.py

# 4. Reproduce the open-system Lindblad simulation
python3 experiments/experiment_e/bench_compiler_lindblad.py

# 5. Reproduce the compiler performance benchmark
python3 experiments/experiment_e/bench_compiler_performance.py
```
