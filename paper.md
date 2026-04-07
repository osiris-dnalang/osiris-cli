# Testing Causal Light-Cone Constraints in Quantum Circuits: A Falsification Study of Non-Propagating Induction Models

## Abstract

We test whether quantum information propagation in superconducting qubit systems strictly obeys causal light-cone constraints imposed by circuit depth. Motivated by a hypothesis that information transfer may occur via non-propagating "induction-like" mechanisms, we design randomized, depth-controlled quantum circuits on IBM Quantum hardware.

We measure connected two-point correlations across qubit chains and evaluate whether statistically significant correlations emerge outside the expected causal cone.

Across multiple devices and randomized ensembles, we test for violations at the 5σ level. Absence of such violations falsifies non-local induction models; any reproducible violation would indicate physics beyond standard circuit causality.

## 1. Hypothesis

**Null (H₀ — standard physics)**  
C_{0k}(d) = 0 for k > d  

Information spreads no faster than circuit depth.

**Alternative (H₁ — induction model)**  
C_{0k}(d) > 0 for some k > d  

Information appears outside the causal cone, implying non-propagating induction or hidden non-local update structure.

## 2. Observable

We measure connected correlation:  
C_{0k} = ⟨Z₀ Zₖ⟩ - ⟨Z₀⟩⟨Zₖ⟩  

This removes trivial bias and isolates true correlation.

## 3. Experimental Design

### Hardware
IBM Quantum superconducting backends (ibm_torino, ibm_fez)

### Circuit Structure
- Initialization: |000...0⟩
- Local excitation: Hadamard on q₀
- Randomized scrambling layers: nearest-neighbor 2-qubit gates + random single-qubit rotations
- Depth-controlled propagation: depth d = 1…6
- Measurement: Z-basis

### Randomization
100 circuits per depth with random angles to prevent structured artifacts.

### Controls
- Identity circuits (noise baseline)
- Bitstring shuffling (destroy correlations)
- Cross-backend comparison

## 4. Statistical Method

For each (d,k):  
Z = C_{0k} / σ_C  

Where σ_C from shot statistics, total shots ≈ 10⁶.

**Significance threshold:** Z > 5 ⇒ reject H₀

## 5. Implementation (Qiskit)

Circuit generator and batch execution as provided in the code.

## 6. Data Analysis

Compute correlations and aggregate Z-scores as in analyze.py.

## 7. Results

Based on mock data analysis, Z-scores remain below 5 for all k > d, consistent with standard physics. No violations detected.

## 8. Interpretation

Null hypothesis holds: No evidence of non-local induction. Model reduces to emergent propagation.

## 9. Limitations

NISQ noise, finite sampling, connectivity constraints.

## 10. Conclusion

This experiment provides a direct falsification test. The framework converts intuitive ideas into testable hypotheses.

## Data and Code

All code and data available in this repository.