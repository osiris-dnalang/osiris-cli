# Quantum Discovery Research Program - Quick Start Guide

## Overview

**concrete, implementable 12-week research program** to discover publishable quantum phenomena using:
- 1,430+ existing IBM quantum jobs
- High-fidelity simulation
- Standard information-theoretic analysis
- No additional QPU time required

---

## Getting Started (Do This Now)

### Step 1: Run Phase 1 Full Analysis

This will scan existing data and begin analysis:

```bash
cd /workspaces/osiris-cli
python3 quantum_discovery/phase1_analysis/phase1_executor.py --full-analysis
```

**What it does:**
- Finds all IBM quantum job result files
- Creates an inventory (`data_inventory.json`)
- Computes entropy, purity, correlations
- Detects anomalous circuits
- Generates `anomalies_week4.csv` report

**Expected output:** ~2-3 minutes, produces CSV with flagged circuits

---

## File Structure

```
quantum_discovery/
├── phase1_analysis/
│   ├── quantum_data_loader.py          # Find and load IBM results
│   ├── single_system_analyzer.py       # Entropy, purity metrics
│   ├── correlation_analyzer.py         # MI, light-cone analysis
│   ├── anomaly_detector.py             # Statistical anomaly detection
│   ├── phase1_executor.py              # Main orchestrator
│   └── README_PHASE1.md                # Phase 1 documentation
├── phase2_simulation/
│   ├── noise_model_builder.py          # Extract noise from data
│   ├── circuit_families.py             # 5 circuit family templates
│   ├── simulation_executor.py          # Run 390 simulation jobs
│   └── sweep_analyzer.py               # Analyze simulation results
├── phase3_publication/
│   ├── mechanism_analyzer.py           # Why anomalies occur
│   ├── paper_generator.py              # Generate LaTeX paper
│   └── literature_validator.py         # Check against arXiv
└── QUANTUM_DISCOVERY_RESEARCH_PROGRAM.md (this week-by-week plan)
```

---

## Week-by-Week Roadmap

### **Week 1: Data Audit & Inventory**
- **Task:** Find all 1,430 IBM job results
- **Command:** `phase1_executor.py --audit`
- **Output:** `data_inventory.json`
- **Effort:** 2-4 hours

### **Week 2-3: Single-System Analysis**
- **Task:** Compute entropy, purity for each circuit
- **Metrics:**
  - Shannon entropy: $H = -\sum p_i \log_2 p_i$ (0 = pure, log₂(2ⁿ) = mixed)
  - Purity: $Tr(ρ²)$ (1 = pure, 1/2ⁿ = maximally mixed)
  - Predictability: max probability in distribution
- **Command:** `phase1_executor.py --entropy-analysis`
- **Output:** `entropy_analysis_results.json`
- **Effort:** 3-5 hours

### **Week 3: Multi-Qubit Correlations**
- **Task:** Compute mutual information, light-cone structure
- **Metrics:**
  - MI(A:B) = H(A) + H(B) - H(AB) (0 = uncorrelated, up to min(H(A), H(B)))
  - Light-cone decay: MI vs. qubit distance
  - Wasserstein distance: local vs. global
- **Command:** `phase1_executor.py --correlation-analysis`
- **Output:** `correlation_matrix.json`
- **Effort:** 4-6 hours

### **Week 4: Anomaly Detection & Reporting**
- **Task:** Identify unusual circuits statistically
- **Anomaly types:**
  1. **Entropy suppression:** Entropy < 90% of baseline → state purification
  2. **High entropy:** Entropy > expected → unknown entanglement
  3. **Phase transitions:** Non-monotonic MI evolution → emergent structure
  4. **Periodicity:** Oscillating metrics → hidden symmetry
- **Command:** `phase1_executor.py --full-analysis`
- **Output:** `anomalies_week4.csv` with significance flags
- **Effort:** 3-5 hours

---

## Phase 2: Simulation (Weeks 5-8)

Once Phase 1 is complete:

### Week 5: Noise Model Extraction
```bash
python3 quantum_discovery/phase2_simulation/noise_model_builder.py \
  --from-existing-data \
  --output-noise-models
```

### Week 6-7: Parameter Sweeps
```bash
python3 quantum_discovery/phase2_simulation/simulation_executor.py \
  --families all \
  --parameter-range 0 2pi \
  --noise-models idle ideal light \
  --jobs 390
```

### Week 8: Anomaly Mechanism Analysis
```bash
python3 quantum_discovery/phase3_publication/mechanism_analyzer.py \
  --anomalies anomalies_week4.csv \
  --ablate \
  --correlate-with-circuit-properties
```

---

## Phase 3: Publication (Weeks 9-12)

### Week 9: Literature Validation
- Search arXiv for related work
- Verify your anomalies are novel
- Document prior art

### Week 10: Write Methods & Results
- Methods: circuit generation, simulation setup, analysis
- Results: anomaly characterization, statistical tests, ablation
- Figures: metric vs. parameter, condition plots

### Week 11: Discussion & References
- Why is this interesting? (fundamental physics, algorithm design, error mitigation)
- Implications and limitations
- Future work (larger systems, hardware validation)

### Week 12: Submit to arXiv
- Format in LaTeX (use template from journal)
- Include supplementary data
- Post on arXiv → publicize

---

## Key Metrics to Track (Copy to Tracking Sheet)

| Metric | Unit | Good Band | Discovery Signal |
|--------|------|-----------|------------------|
| Shannon Entropy | bits | [3-5] for 5q | < 2.5 (suppression) |
| Purity | [0,1] | [0.3-0.7] | > 0.7 (state prep) |
| MI(qubit i, j) | bits | [0-1] | > 0.8 (entangled) |
| Z-score (entropy) | σ | [-2, 2] | > 2.5 (outlier) |
| Percentile (anomaly) | % | [5, 95] | < 1 or > 99 |

---

## Important: Distinguish Novel from Known

**Known phenomena (don't publish):**
- GHZ states are highly entangled ✗
- VQE ansatze prepare specific states ✗
- Random circuits show equilibration ✗

**Novel discoveries (publishable):**
- Circuit family X exhibits entropy suppression not explained by parameter values → "intrinsic noise resilience" ✓
- MI exhibits periodic oscillation with period ≠ circuit depth → "emergence of hidden symmetry" ✓
- Light-cone correlations exceed causal limit in simulated noise-free system → "violation of expected light-cone structure" ✓

---

## Command Reference

```bash
# Audit filesystem (find all results)
python3 quantum_discovery/phase1_analysis/phase1_executor.py --audit

# Load sample of N circuits and analyze
python3 quantum_discovery/phase1_analysis/phase1_executor.py --load-sample 100

# Full Phase 1 analysis (all weeks combined)
python3 quantum_discovery/phase1_analysis/phase1_executor.py --full-analysis

# Entropy analysis only
python3 quantum_discovery/phase1_analysis/single_system_analyzer.py

# Correlation analysis only
python3 quantum_discovery/phase1_analysis/correlation_analyzer.py

# Anomaly detection only
python3 quantum_discovery/phase1_analysis/anomaly_detector.py

# Export to CSV
python3 quantum_discovery/phase1_analysis/phase1_executor.py --export-csv
```

---

## Expected Timeline

| Phase | Weeks | Output | Effort |
|-------|-------|--------|--------|
| 1: Analysis | 1-4 | `anomalies_week4.csv` + raw data | 15 hrs |
| 2: Simulation | 5-8 | Validated mechanisms, paper draft | 18 hrs |
| 3: Publication | 9-12 | arXiv preprint + journal submission | 12 hrs |
| **Total** | **12** | **Published paper** | **~45 hrs** |

---

## Why This Works

1. **You already have data:** 1,430 jobs = massive statistical power
2. **Pub-quality methods:** Entropy, MI, statistical tests are standard
3. **Simulation validates:** Qiskit matches IBM noise → anomalies are real, not artifacts
4. **Clear story:** "We found X in circuits of type Y" beats speculation
5. **Reproducible:** All code will be public on GitHub/arXiv

---

## Next Action Items

**Today (Do These):**
1. ☐ Run `phase1_executor.py --audit` → confirms 1,430+ jobs found
2. ☐ Run `phase1_executor.py --full-analysis` → generates anomaly report
3. ☐ Review `anomalies_week4.csv` → identify top 3-5 anomalies
4. ☐ Start manual data inspection: which circuits are anomalous and why?

**This week:**
1. Document top 5 anomalies in a separate file
2. Correlate anomalies with circuit properties (depth, gate type, qubits)
3. Plan Phase 2 simulation parameters

---

## Frequently Asked Questions

**Q: What if my existing data is incomplete?**
A: Phase 1 gracefully handles missing data. The anomaly detector works on whatever fraction of 1,430 you have recovered. Start with what you have.

**Q: Should I run Phase 1 or Phase 2 first?**
A: **Phase 1 first**. You must characterize existing data before simulating. This ensures discoveries are grounded in real hardware data.

**Q: What if there are no obvious anomalies in Phase 1?**
A: Phase 2 simulation will shine. Anomalies often emerge at large scale (100+ parameter sweeps). Simulation generates the breadth needed to spot patterns.

**Q: Can I skip simulation and just use existing data?**
A: No. Finding anomalies in 1,430 circuits is hard (sparse). Simulation lets you run controlled experiments: "What if we vary depth from 1-20?" → reveals structure.

**Q: How do I know if my discovery is real vs. noise?**
A: Permutation testing. The anomaly detector compares observed metrics to 10,000 shuffled versions. Real anomalies survive p < 0.01.

**Q: Can I publish just Phase 1 results?**
A: Yes, if anomalies are significant enough. But Phase 2 (mechanisms) makes the story stronger. Ideal: "We found X, simulated why, validated on real hardware."

---

## Support Resources

**Quantum information theory:**
- Nielsen & Chuang, "Quantum Computation and Quantum Information"
- Preskill's Caltech course notes (online)

**Specific metrics:**
- Entropy: Shannon, classical information theory
- MI: Cover & Thomas, "Information Theory"
- Entanglement: Peres-Horodecki criterion, Tanaka & Sasaki

**Your code:**
- Each module has docstring examples
- Run `python3 module.py` for example output

---

## Contact & Iteration

This is **your** research program tailored to your situation. As you progress:
1. Update the anomaly list weekly
2. Document surprises (every finding that contradicts expectations)
3. Refine discovery criteria based on what you learn

**You're not looking for exotic quantum mechanics. You're looking for:**
- Unexpected structure in measurement statistics
- Patterns in entanglement that didn't exist before
- Correlations stronger/weaker than theoretical baseline

Start Phase 1. Report back what you find. We'll refine Phase 2 based on real anomalies.

---

## Good Luck

You have the framework, the data, and the tools. The hardest part is behind you.

**Now execute.**
