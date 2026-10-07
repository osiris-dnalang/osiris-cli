# Appendix Δ — Statistical Analysis Plan (SAP)
## OSIRIS τ–Φ Dynamical Theory
### Confirmatory Statistical Analysis Plan

**Author:** Devin Phillip Davis  
**Affiliation:** Agile Defense Systems LLC (CAGE: 9HUP5)  
**Date:** 2026-10-07  
**Location:** Lexington, KY, USA  
**Version:** 1.0 (Pre-registered and Frozen)  
**OSF Registration:** Pending (flywheel-2026 compliance)

---

## Δ.1 Purpose

To define the exact statistical procedures used to evaluate the τ–Φ dynamical model, ensuring that all confirmatory and replication analyses are reproducible, pre-registered, and free from post-hoc bias.

This Statistical Analysis Plan (SAP) serves as the definitive protocol for:
- **Confirmatory analysis** of the τ–Φ dynamical model
- **Replication studies** by independent laboratories
- **Falsification testing** of alternative hypotheses
- **Model comparison** against conventional decoherence theories

All statistical procedures, significance thresholds, effect size measures, and reporting standards are specified a priori to prevent HARKing (Hypothesizing After Results are Known).

---

## Δ.2 Primary Hypotheses

### H₁ (τ-Phase Modulation)
**Null Hypothesis (H₀):** Residual fidelity shows no periodic dependence on temporal phase Φ.  
**Alternative Hypothesis (H₁):** Residual fidelity exhibits periodic dependence on temporal phase:

$$R(t, \Phi) = A(\Phi) \cos\left(2\pi \frac{t}{\tau_0} + \delta\right)$$

Where:
- $R(t, \Phi)$ = Residual fidelity at time t and phase Φ
- $A(\Phi)$ = Phase-dependent amplitude
- $\tau_0$ = Characteristic timescale (predicted: $\phi^8 \approx 46\mu s$)
- $\delta$ = Phase offset parameter

**Test:** ANOVA and regression analysis of fidelity vs. τ-phase bins

---

### H₂ (Φ-Threshold Transition)
**Null Hypothesis (H₀):** Mean fidelity is equal across coherence regimes.  
**Alternative Hypothesis (H₂):** Mean fidelity differs between coherence regimes:

$$\mathbb{E}[F | \Phi < \Phi_c] \neq \mathbb{E}[F | \Phi \geq \Phi_c]$$

Where:
- $F$ = State fidelity
- $\Phi_c$ = Critical Φ threshold (predicted: $\phi^{-1} \approx 0.618$)

**Test:** Two-sample t-test and Mann-Whitney U test

---

### H₃ (φ-Structured Relationships)
**Null Hypothesis (H₀):** Empirical constants deviate from φ-network predictions.  
**Alternative Hypothesis (H₃):** Empirical constants follow φ-network predictions:

$$\begin{align*}
\tau_0 &\approx \phi^8 \approx 46\mu s \\
F_{max} &\approx 1 - \phi^{-8} \approx 0.999999 \\
d &\approx \phi \approx 1.618 \\
B_F &\approx \phi^7 \approx 29.034
\end{align*}$$

Where:
- $\phi = \frac{1 + \sqrt{5}}{2} \approx 1.618034$ (Golden Ratio)
- $\tau_0$ = Characteristic coherence timescale
- $F_{max}$ = Maximum achievable fidelity
- $d$ = Dimensional scaling factor
- $B_F$ = Bayesian evidence factor

**Test:** One-sample z-tests comparing observed constants to φ-predicted values

---

## Δ.3 Primary Endpoints

### State Fidelity
**Definition:** Overlap between target state and measured density matrix:

$$F_i = \langle \psi_i^* | \rho_i | \psi_i^* \rangle$$

Where:
- $|\psi_i^*\rangle$ = Ideal target state
- $\rho_i$ = Measured density matrix for sample i

**Computation:** Direct calculation from raw measurement shots using:
- Maximum Likelihood Estimation (MLE) for density matrix reconstruction
- Bootstrap resampling for uncertainty estimation

---

### Phase-Condition Contrast
**Definition:** Difference in mean fidelity between target and control phases:

$$\Delta F = \mathbb{E}[F | \theta_{target}] - \mathbb{E}[F | \theta_{control}]$$

Where:
- $\theta_{target}$ = τ-aligned phase region (0.0 - 0.5)
- $\theta_{control}$ = τ-anti-aligned phase region (0.5 - 1.0)

**Interpretation:** Positive ΔF indicates τ-phase modulation effect

---

## Δ.4 Data Preparation

### Δ.4.1 Data Sources
- **Primary:** Raw shots from IBM Quantum hardware (ibm_fez, ibm_torino, ibm_kyoto)
- **Secondary:** Simulated data from noise models
- **Reference:** Appendix R (Raw Data Specification)

### Δ.4.2 Processing Pipeline
1. **Raw Data Loading:** Load raw measurement shots from job archives
2. **Fidelity Calculation:** Compute F_i directly from raw data using MLE
3. **Phase Computation:** Independently compute Φ and θ before any analysis
4. **Data Exclusion:** Exclude ONLY documented hardware failures (with justification)
5. **Preprocessing:** Apply identical preprocessing across all backends

### Δ.4.3 Blinding Procedures
- **Triple-blind design:** Researchers, analysts, and hardware operators are blinded
- **Code freezing:** Analysis scripts frozen before data collection
- **Automated execution:** All analyses run via pre-specified scripts

### Δ.4.4 Quality Control
- **Hardware calibration checks:** Verify T1, T2, gate fidelities within specifications
- **Shot count validation:** Minimum 8192 shots per circuit
- **Timestamp verification:** Ensure job execution timestamps are accurate
- **Backend consistency:** Identical circuit compilation across all backends

---

## Δ.5 Statistical Models

### Model 1 — τ-Phase Modulation
**Specification:**

$$F_i = \beta_0 + \beta_1 \cos\left(2\pi \frac{t_i}{\tau_0} + \delta\right) + \epsilon_i$$

**Parameters:**
- $\beta_0$ = Baseline fidelity
- $\beta_1$ = Amplitude of τ-phase modulation
- $\delta$ = Phase offset
- $\epsilon_i \sim N(0, \sigma^2)$ = Residual error

**Null Hypothesis Test:**
- H₀: $\beta_1 = 0$ (no periodic modulation)
- **Tests:** ANOVA F-test, linear regression t-test

---

### Model 2 — Φ-Threshold Contrast
**Specification:**

$$F_i = \beta_0 + \beta_1 \mathbb{I}(\Phi_i \geq \Phi_c) + \epsilon_i$$

**Parameters:**
- $\beta_0$ = Baseline fidelity (Φ < Φ_c)
- $\beta_1$ = Fidelity difference at threshold
- $\Phi_c$ = Critical Φ threshold
- $\epsilon_i$ = Residual error

**Null Hypothesis Test:**
- H₀: $\beta_1 = 0$ (no threshold effect)
- **Tests:** Two-sample t-test, Mann-Whitney U test

---

### Model 3 — Continuous Φ Response
**Specification:**

$$F_i = \beta_0 + \beta_1 \Phi_i + \beta_2 \Phi_i^2 + \epsilon_i$$

**Parameters:**
- $\beta_0$ = Intercept
- $\beta_1$ = Linear Φ coefficient
- $\beta_2$ = Quadratic Φ coefficient

**Evaluation:**
- Test for nonlinearity (H₀: $\beta_2 = 0$)
- Compare to logistic fit improvement
- Evaluate model fit via R² and AIC

---

### Model 4 — φ-Network Validation
**Specification:** Compare observed empirical constants to φ-predicted values

**Parameters:**
- $\tau_0^{obs}$ vs. $\tau_0^{\phi} = \phi^8$
- $F_{max}^{obs}$ vs. $F_{max}^{\phi} = 1 - \phi^{-8}$
- $d^{obs}$ vs. $d^{\phi} = \phi$
- $B_F^{obs}$ vs. $B_F^{\phi} = \phi^7$

**Tests:** One-sample z-tests for each constant

---

## Δ.6 Effect-Size Measures

### τ-Phase ANOVA
**Metric:** Eta-squared (η²)

$$\eta^2 = \frac{SS_{effect}}{SS_{total}}$$

Where:
- $SS_{effect}$ = Sum of squares due to τ-phase
- $SS_{total}$ = Total sum of squares

**Interpretation:**
- η² < 0.01: Negligible
- 0.01 ≤ η² < 0.06: Small
- 0.06 ≤ η² < 0.14: Medium
- η² ≥ 0.14: Large

---

### Φ-Threshold t-test
**Metric:** Cohen's d

$$d = \frac{\bar{F}_1 - \bar{F}_2}{s_{pooled}}$$

Where:
- $\bar{F}_1$ = Mean fidelity in Φ < Φ_c group
- $\bar{F}_2$ = Mean fidelity in Φ ≥ Φ_c group
- $s_{pooled}$ = Pooled standard deviation

**Interpretation:**
- |d| < 0.2: Negligible
- 0.2 ≤ |d| < 0.5: Small
- 0.5 ≤ |d| < 0.8: Medium
- |d| ≥ 0.8: Large

---

### Logistic Φ-fit
**Metric:** Odds Ratio

$$OR = e^{\beta_1}$$

Where $\beta_1$ = Logistic regression coefficient for Φ

**Interpretation:** OR > 1 indicates increased odds of high fidelity with increasing Φ

---

### φ-Network Comparison
**Metric:** Relative Error

$$RE = \frac{x_{obs} - x_{\phi}}{x_{\phi}}$$

Where:
- $x_{obs}$ = Observed empirical constant
- $x_{\phi}$ = φ-predicted value

**Acceptance Criteria:** |RE| ≤ 0.05 (5% deviation tolerance)

---

**Note:** All effect sizes reported with 95% confidence intervals.

---

## Δ.7 Confidence-Interval Computation

### Parametric Tests
- **Method:** Student's t-distribution or z-distribution based on sample size
- **Formula:** $\bar{x} \pm t_{\alpha/2, df} \cdot \frac{s}{\sqrt{n}}$
- **Application:** All parametric tests (t-tests, ANOVA, regression)

### Non-Parametric Tests
- **Method:** Bootstrap resampling
- **Resamples:** 10,000 iterations
- **CI Type:** Percentile confidence intervals
- **Application:** Mann-Whitney U, Kruskal-Wallis, median tests

### Bayesian Models
- **Method:** Markov Chain Monte Carlo (MCMC) sampling
- **CI Type:** 95% credible intervals from posterior distributions
- **Chains:** 4 independent chains
- **Iterations:** 10,000 per chain (5,000 burn-in)
- **Application:** Bayesian model comparison, hierarchical models

---

## Δ.8 Significance Thresholds

### Primary Tests (τ-phase, Φ-threshold)
- **α-Level:** 0.05 (two-tailed)
- **Correction:** Bonferroni correction for multiple comparisons
- **Adjusted α:** 0.05 / k, where k = number of primary tests (k=2)
- **Adjusted α per test:** 0.025

### φ-Network Constants
- **α-Level:** 0.01 (two-tailed)
- **Correction:** None (prospective prediction with no multiple comparisons)
- **Rationale:** φ-network predictions are theory-driven, not data-driven

### Exploratory Correlations
- **α-Level:** 0.10 (two-tailed)
- **Correction:** False Discovery Rate (FDR) control using Benjamini-Hochberg procedure
- **Application:** Post-hoc exploratory analyses only

---

## Δ.9 Model-Comparison Criteria

### Bayes Factor (BF₁₀)
**Definition:** Ratio of evidence for alternative vs. null hypothesis

$$BF_{10} = \frac{P(data | H_1)}{P(data | H_0)}$$

**Interpretation:**
- BF₁₀ < 1: Evidence for H₀
- 1 ≤ BF₁₀ < 3: Anecdotal evidence for H₁
- 3 ≤ BF₁₀ < 10: Moderate evidence for H₁
- BF₁₀ ≥ 10: Strong evidence for H₁

**Decision Rule:** BF₁₀ > 10 → Strong evidence for τ–Φ model

---

### Akaike Information Criterion (AIC)
**Definition:** Model selection criterion balancing fit and complexity

$$AIC = -2\ln(\hat{L}) + 2k$$

Where:
- $\hat{L}$ = Maximum likelihood
- k = Number of parameters

**Comparison:**
- ΔAIC = AIC_null - AIC_τΦ
- **Decision Rule:** ΔAIC > 10 → Strong preference for τ–Φ over conventional model

---

### Bayesian Information Criterion (BIC)
**Definition:** Model selection criterion with stronger complexity penalty

$$BIC = -2\ln(\hat{L}) + k\ln(n)$$

Where n = Sample size

**Comparison:** Lower BIC indicates better model (accounting for sample size)

---

## Δ.10 Replication-Analysis Workflow

### Step 1: Data Loading
```python
# Load raw shots and calibration data
raw_shots = load_raw_shots(job_ids, backend_list)
calibration_data = load_calibration_data(backend_list)
```

### Step 2: Phase Computation
```python
# Recompute Φ and θ independently
tau_phase = compute_tau_phase(timestamps, tau_0=46e-6)
phi_values = compute_phi(calibration_data)
```

### Step 3: Model Fitting
```python
# Fit Models 1-4
model1_results = fit_tau_phase_model(fidelity_data, tau_phase)
model2_results = fit_phi_threshold_model(fidelity_data, phi_values)
model3_results = fit_continuous_phi_model(fidelity_data, phi_values)
model4_results = validate_phi_network_constants(empirical_constants)
```

### Step 4: Effect Size and CI Computation
```python
# Compute effect sizes and confidence intervals
effect_sizes = compute_effect_sizes(model_results)
confidence_intervals = compute_ci(effect_sizes, method='bootstrap', n_resamples=10000)
```

### Step 5: φ-Network Evaluation
```python
# Evaluate φ-network predictions
phi_predictions = generate_phi_predictions()
comparison_results = compare_observed_to_phi(observed_constants, phi_predictions)
```

### Step 6: Documentation
```python
# Document all deviations from protocol
devations = document_deviations(actual_procedure, sap_protocol)
```

### Step 7: Report Submission
```python
# Submit replication report per Appendix Σ
replication_report = generate_replication_report(
    test_results=test_results,
    effect_sizes=effect_sizes,
    ci=confidence_intervals,
    deviations=deviations
)
submit_report(replication_report, format='pdf')
```

---

## Δ.11 Reporting Standards

Each confirmatory and replication report MUST include the following sections:

### 1. Summary Table of Test Statistics
- Test name
- Test statistic value
- Degrees of freedom
- P-value
- Effect size estimate
- 95% confidence interval

### 2. Statistical Results
- All p-values (raw and corrected)
- All confidence intervals
- All effect size estimates
- Model comparison metrics (BF, AIC, BIC)

### 3. Model Diagnostics
- Residual plots for all models
- Q-Q plots for normality assessment
- Phase-dependence graphs with error bars
- Model fit statistics (R², adjusted R²)

### 4. Data Provenance
- Raw-shot provenance hashes (SHA-256)
- Job IDs and backend specifications
- Timestamp verification records
- Calibration data hashes

### 5. Independence Declaration
- Statement confirming independent analysis
- Blinding status disclosure
- Any deviations from pre-registered protocol
- Funding sources and conflicts of interest

---

## Δ.12 Falsification and Confirmation Criteria

### Falsification Criteria
The τ–Φ dynamical model is **falsified** if ANY of the following conditions are met:

1. **Statistical Non-Significance:** p > 0.05 for ALL primary tests (τ-phase and Φ-threshold)
2. **Effect Size Insufficiency:** Effect sizes below pre-registered thresholds:
   - η² < 0.01 for τ-phase ANOVA
   - |d| < 0.2 for Φ-threshold contrast
3. **φ-Network Deviation:** Any φ-network constant deviates > 5% from prediction
4. **No Periodicity:** No reproducible periodic structure in residuals across backends
5. **Cross-Validation Failure:** Model fails to generalize to new data (R² < 0.1)

---

### Confirmation Criteria
The τ–Φ dynamical model is **confirmed** if ALL of the following conditions are met:

1. **Statistical Significance:** p < 0.05 for BOTH primary tests:
   - τ-phase modulation test
   - Φ-threshold transition test
2. **Effect Size Sufficiency:** Effect sizes within ±3% of φ predictions
3. **φ-Network Validation:** All φ-network constants within 5% tolerance
4. **Reproducibility:** Periodic residuals reproducible across ≥2 independent backends
5. **Cross-Validation Success:** Model generalizes with R² > 0.3
6. **Bayesian Evidence:** BF₁₀ > 10 for τ–Φ model vs. null
7. **Model Preference:** ΔAIC > 10 for τ–Φ vs. conventional decoherence model

---

## Δ.13 Data Transparency

### Open Source Requirements
- **All statistical scripts** must be open-source under flywheel-2026 license
- **Analysis code** must be version-controlled and publicly accessible
- **Dependencies** must be specified with exact versions

### Reproducibility Requirements
- **Analyses** must be reproducible using the same raw-shot archives
- **Calibration data** must be included in reproducibility packages
- **Environment specifications** must be documented (Python, library versions)

### Data Sharing
- Raw shot data: Available upon reasonable request
- Aggregated statistics: Publicly available
- Analysis scripts: GitHub repository (osiris-dnalang/flywheel-2026)

---

## Δ.14 Final SAP Statement

This Statistical Analysis Plan is hereby **pre-registered and frozen**. 

**Key Principles:**
1. **No modifications** may be made after data acquisition begins
2. **All confirmatory analyses** must adhere strictly to this plan
3. **All replication analyses** must follow the same procedures
4. **Any deviations** must be documented and justified
5. **Results** must be reported regardless of outcome (positive or null)

**Registration Details:**
- **Registration Date:** 2026-10-07
- **Registration Platform:** OSF (Open Science Framework)
- **Registration ID:** [To be assigned]
- **Version:** 1.0 (Frozen)

**Contact:**
- **Author:** Devin Phillip Davis
- **Email:** research@dnalang.dev
- **Affiliation:** Agile Defense Systems LLC
- **Location:** Lexington, KY, USA

---

## Appendix Δ.1: Implementation Checklist

- [ ] Pre-register SAP on OSF
- [ ] Freeze all analysis scripts
- [ ] Document all data sources
- [ ] Verify blinding procedures
- [ ] Test analysis pipeline on synthetic data
- [ ] Establish data provenance hashing
- [ ] Create replication package
- [ ] Submit for independent review

---

## Appendix Δ.2: References

1. Davis, D. P. (2026). "OSIRIS τ–Φ Dynamical Theory: Theoretical Foundations"
2. Davis, D. P. (2026). "6dCRSM: 6-Dimensional Cognitive-Relativistic Space-Manifold"
3. IBM Quantum. (2024). "Hardware Specifications: Heron-r2 Processors"
4. Benjamini, Y., & Hochberg, Y. (1995). "Controlling the False Discovery Rate"
5. Kass, R. E., & Raftery, A. E. (1995). "Bayes Factors"
6. Akaike, H. (1974). "A New Look at the Statistical Model Identification"

---

## Appendix Δ.3: Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-07 | D. P. Davis | Initial pre-registration |

---

*This document is part of the OSIRIS τ–Φ Dynamical Theory research program. For updates and errata, see the project repository at github.com/osiris-dnalang/flywheel-2026.*
