---
name: exotic-physics-paper
description: "Use when: drafting, reviewing, or refining academic physics papers from OSIRIS experimental results. Translates CRSM framework concepts into peer-review-grade language. Generates LaTeX-ready sections. Maps experimental data to falsifiable claims. Use when: writing papers, preparing submissions, translating visionary physics into academic register, generating figures, checking statistical rigor."
---

# Exotic Physics Paper Drafting Skill

## Purpose
Transform OSIRIS quantum experimental results and CRSM theoretical predictions into papers that survive hostile peer review at Nature, PRL, and Nature Quantum Information.

## The Translation Problem
The CRSM research program uses a geometric-intuitive language that reviewers will reject on sight. This skill bridges the gap.

### Forbidden → Required Translations

| NEVER write this | ALWAYS write this instead |
|---|---|
| "consciousness metric" | "observer-coupled decoherence functional" |
| "cognitive resonance" | "measurement-back-action correlation" |
| "null point" | "fixed point of the renormalization group flow" |
| "centripetal convergence" | "geodesic focusing (Raychaudhuri equation)" |
| "centrifugal divergence" | "geodesic deviation (Jacobi field expansion)" |
| "renormalizing c" | "effective phase velocity in the dispersive medium" |
| "vacuum stiffness" | "vacuum impedance $Z_0 = \sqrt{\mu_0/\epsilon_0}$" |
| "tetrahedral vacuum lattice" | "$A_4$-symmetric lattice regularization" |
| "DNA-Lang" | "domain-specific quantum circuit compiler" |
| "qByte emission" | "negentropic excess from decoherence-coherence transition" |
| "Resonant Monad Field" | "scalar field $\Psi$ on the fiber bundle" |
| "phase-conjugate feedback" | "time-reversed wavefront via four-wave mixing" |
| "fractal holographic" | "scale-invariant holographic (AdS/CFT correspondence)" |
| "coaxial circuit field perturbation" | "covariant perturbation of the cylindrical gauge connection" |
| "Mission Accomplished" | [cite the specific metric: XEB score, p-value, fidelity] |
| "proving quantum advantage" | "evidence for quantum computational advantage under [specific conditions]" |
| "VTOL-GENESIS propulsion" | [DO NOT include in physics papers — separate engineering publication] |

### Hedging Rules
- "We prove X" → "We present evidence consistent with X"
- "X is true" → "Our results support X at the $N\sigma$ level"
- "This revolutionizes" → "This result, if confirmed by independent groups, would extend..."
- Claims of novelty require: "To our knowledge, this is the first..."

## Paper Templates

### Template A: Falsification Study (paper.md style)
Best for testing whether CRSM predictions violate standard physics.

```
Title: "Testing [specific prediction] in [system]: A Falsification Study"

Abstract (4 sentences):
1. [Established physics context — what we know]
2. [The gap — what hasn't been tested]
3. [Our method — what we did]
4. [Our result — what we found, with the key number]

1. Introduction
   - Paragraph 1: Standard model context (cite textbooks)
   - Paragraph 2: The specific gap this paper addresses
   - Paragraph 3: Prior experimental attempts (if any)
   - Paragraph 4: "In this work, we..." (one sentence summary)

2. Theoretical Framework
   - Start from established equations
   - Derive the testable prediction step by step
   - State H₀ (standard physics) and H₁ (new prediction)
   - Show that H₁ reduces to H₀ in the appropriate limit

3. Experimental Design
   - Hardware: IBM Quantum [specific backend], [qubit count], [connectivity]
   - Circuits: [structure], [depth range], [gate set]
   - Controls: identity circuits (noise floor), shuffled bitstrings (correlation destruction)
   - Statistics: [shot count], [number of circuit variants], [significance threshold]

4. Results
   - Table: all measured values with error bars
   - Figure 1: data vs prediction
   - Statistical test: Z-score, p-value, effect size
   - Noise characterization: readout error rate, gate error rate, T1/T2

5. Discussion
   - What the result means
   - What it does NOT mean (explicit list)
   - Systematic uncertainties
   - Comparison with null hypothesis

6. Conclusion
   - One paragraph. No speculation.

Data Availability: "All code, circuits, and raw measurement data are available at [Zenodo DOI]."
```

### Template B: Quantum Advantage Study (RQC vs RCS style)
Best for demonstrating that adaptive circuits outperform random ones.

```
Title: "Adaptive Quantum Circuits [Outperform/Show No Advantage Over] Random Circuit Sampling on [N]-Qubit Hardware"

Key metrics to report:
- XEB scores: mean ± std for both RCS and RQC
- t-test: t-statistic, degrees of freedom, p-value (two-tailed)
- Effect size: Cohen's d with 95% CI
- Number of trials: n ≥ 20 per condition
- Cross-backend: results on ≥ 2 IBM systems
```

### Template C: Geometric Circuit Optimization
Best for demonstrating that $A_4$-symmetric qubit mapping reduces errors.

```
Title: "Tetrahedral Qubit Mapping Reduces Gate Errors in Heavy-Hex Architectures"

Key comparison:
- Standard linear chain mapping vs tetrahedral embedding
- Metric: total CNOT count, circuit depth after transpilation, measured fidelity
- Control: same logical circuit, different physical mapping
```

## Statistical Checklist (Required Before Submission)

- [ ] Sample size ≥ 20 per condition
- [ ] Significance level stated a priori (not post-hoc)
- [ ] Multiple comparison correction applied (Bonferroni/FDR) if >1 hypothesis tested
- [ ] Effect size reported (Cohen's d or equivalent)
- [ ] Confidence intervals reported (95%)
- [ ] Noise floor characterized (identity circuit baseline)
- [ ] Cross-backend replication attempted
- [ ] Negative results reported if hypothesis fails
- [ ] Raw data archived with DOI

## Figure Standards

1. All figures must have axis labels with units
2. Error bars on every data point (1σ from shot noise + systematic)
3. Theory prediction line with shaded uncertainty band
4. Caption must be self-contained (reader understands figure without reading paper)
5. Use colorblind-safe palettes

## Reference Standards

- NEVER fabricate references
- ALWAYS cite:
  - Original RCS paper (Arute et al., Nature 2019)
  - XEB definition (cross-entropy benchmarking methodology)
  - IBM hardware specifications (from docs.quantum.ibm.com)
  - Qiskit version used
  - Any prior OSIRIS publications on Zenodo (real DOIs only)
- For CRSM-specific concepts, cite the user's own Zenodo publications

## Execution Workflow

```
1. User provides theoretical framework + experimental idea
2. Oracle DECODES into formal structure
3. Oracle DESIGNS the experiment (circuit, controls, statistics)
4. Oracle EXECUTES via OSIRIS (or specifies the exact command)
5. Oracle ANALYZES results (is the hypothesis supported?)
6. Oracle DRAFTS the paper section-by-section
7. User reviews → Oracle revises
8. Oracle prepares Zenodo archive + generates CITATION.cff
```
