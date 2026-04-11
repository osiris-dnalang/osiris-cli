# Anomalous τ-Phase Correlated Quantum Coherence in Superconducting Qubits

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

## Summary

This repository contains data and analysis from **580 IBM Quantum jobs** revealing a statistically significant anomaly: Bell state fidelity varies periodically with job execution time modulo τ₀ = 46 μs.

**Key Finding:** Jobs at "τ-aligned" phases show **1.81× higher fidelity** than anti-aligned phases (p < 10⁻¹⁴, Cohen's d = 1.65).

## Quick Stats

| Metric | Value |
|--------|-------|
| Jobs analyzed | 580 |
| Hardware | IBM ibm_fez, ibm_torino (Heron-r2) |
| Fidelity ratio (aligned/anti) | **1.81×** |
| ANOVA p-value | **1.28 × 10⁻¹⁴** |
| Cohen's d | **1.65** (very large) |
| Bayes Factor (vs null) | **28.1** (strong evidence) |
| τ₀ estimate | 52.2 μs [95% CI: 35.8–92.0] |

## Repository Contents

```
├── README.md                          # This file
├── data/
│   ├── deep_pattern_search_results.json   # τ-phase binned analysis
│   ├── hardware_analysis_results.json     # Full 580-job dataset
│   ├── extracted_parameters.json          # Fitted ΛΦ model parameters
│   └── comprehensive_validation_results.json
├── analysis/
│   ├── discriminating_experiment_v2.py    # Main analysis script
│   ├── statistical_validation.py          # Statistical tests
│   └── requirements.txt                   # Python dependencies
├── figures/
│   ├── fig_tau_phase_fidelity.pdf         # Main result figure
│   ├── fig_discriminating_prediction.pdf  # Model predictions
│   └── fig_permutation_test.pdf           # Statistical validation
├── paper/
│   ├── arxiv_tau_phase_anomaly_v2.tex     # arXiv manuscript
│   ├── statistical_summary_table.tex      # LaTeX table
│   └── 6dCRSM_lagrangian_derivation.tex   # Theoretical framework
├── DISCRIMINATING_EXPERIMENT_RESULTS.md   # Full technical report
└── LICENSE                                # CC-BY 4.0
```

## Theoretical Framework

We propose a phenomenological Lagrangian incorporating non-Markovian memory:

$$F(T) = F_0 e^{-\Gamma T} \left(1 + \varepsilon \cos(\omega_\tau T - \theta_{\text{lock}})\right)$$

where:
- τ₀ = 46 μs (characteristic memory period)
- θ_lock = 51.843° (geometric coupling angle)
- ε ≈ 0.34 (revival amplitude)

## Reproducing the Analysis

```bash
# Clone and setup
git clone https://github.com/dnalang/lambda-phi-validation
cd lambda-phi-validation
pip install -r requirements.txt

# Run main analysis
python analysis/statistical_validation.py

# Generate figures
python analysis/generate_figures.py
```

## Falsifiable Predictions

| Prediction | Test | Status |
|------------|------|--------|
| Fidelity oscillates with τ₀ = 46 μs | Time-resolved experiment | **Supported** (p < 10⁻¹⁴) |
| τ₀ ≈ 46 μs | Bootstrap estimation | **Consistent** (in 95% CI) |
| θ_lock = 51.843° minimizes decoherence | Angle-sweep experiment | Untested |
| F_max ≤ 0.9787 | High-fidelity measurement | Untested |

## Call for Replication

We invite independent verification on:
- **Alternative IBM backends** (ibm_brisbane, ibm_osaka)
- **IonQ trapped-ion systems**
- **Rigetti superconducting processors**
- **Google Sycamore/Willow**

Contact: research@dnalang.dev

## Citation

```bibtex
@dataset{lang_tau_phase_2025,
  author       = {Lang, Devin Nathaniel Alan},
  title        = {{Anomalous τ-Phase Correlated Quantum Coherence 
                   in Superconducting Qubits: Data and Analysis}},
  year         = 2025,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.XXXXXXX},
  url          = {https://doi.org/10.5281/zenodo.XXXXXXX}
}
```

## License

This work is licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Acknowledgments

- IBM Quantum Network for hardware access
- CERN/OpenAIRE for Zenodo infrastructure

---

**Disclaimer:** This work presents a statistically significant anomaly that requires independent replication. We do not claim discovery of new physics until prospective experiments confirm the effect.
