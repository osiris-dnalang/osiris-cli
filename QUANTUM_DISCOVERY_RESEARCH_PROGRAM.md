# Concrete Quantum Discovery Research Program
## 12-Week Implementation Plan (No Additional QPU Time Required)

**Objective:** Extract publishable quantum information discoveries from existing data + high-fidelity simulation.

**Starting Point:**
- 1,430+ completed IBM quantum jobs (historical data)
- Working circuit generation pipeline
- OSIRIS framework (TUI + orchestration)
- Access to QiskitAerSimulator with noise models

---

## PHASE 1: REANALYZE EXISTING DATA (Weeks 1–4)

### Goal
Transform raw measurement outcomes from your 1,430 existing IBM jobs into **genuine quantum information insights** using standard (publishable) analysis methods.

### Week 1: Data Recovery & Standardization

**Task 1.1: Audit Existing Data**
- [ ] Locate and catalog all 1,430+ IBM job result files (JSON, QASM, measurement counts)
- [ ] Validate data integrity (shot counts, qubit counts, circuit depth)
- [ ] Extract circuit metadata: depth, gate count, qubit topology
- [ ] Document which jobs have noise estimates vs. ideal
- **Output:** `data_inventory.json` (circuit ID → metadata + result path)

**Task 1.2: Build Standardized Data Pipeline**
- [ ] Create `quantum_data_loader.py`:
  - Load IBM job results (handle various formats)
  - Normalize measurement counts
  - Compute shot statistics
  - Handle missing/corrupted data
- [ ] Validate against known distributions (expect ~50% |0⟩, ~50% |1⟩ for unentangled qubits)
- **Output:** Reusable data loading module

---

### Week 2: Single-System Information Analysis

**Task 2.1: Entropy & Coherence Measures**
For each circuit family in your data, compute:
- [ ] **Shannon Entropy** per qubit: $H = -\sum_i p_i \log_2 p_i$
  - Indicates mixedness (0 = pure state, log₂(d) = maximally mixed)
  - A circuit that purifies states should show **decreasing entropy**
- [ ] **Purity:** $\Tr(\rho^2)$ estimated from measurement statistics
  - Pure state: $\Tr(\rho^2) = 1$; Mixed state: $\Tr(\rho^2) < 1$
- [ ] **Accessible Information:** mutual information between measurement settings and outcomes
- **Discovery Condition:** Circuits that consistently produce lower entropy or higher purity than random baselines

**Task 2.2: Implement Analysis Module**
```python
# pseudo-code structure
class SingleSystemAnalyzer:
    def compute_shannon_entropy(counts, num_qubits):
        """Compute entropy per qubit"""
    
    def estimate_purity(counts):
        """Estimate Tr(ρ²) from measurement statistics"""
    
    def statistical_significance_test(circuit_entropy, baseline_entropy):
        """Chi-squared test: is this different from random?"""
```
- **Output:** `single_system_analysis.py` (200+ lines)

---

### Week 3: Multi-System Correlations

**Task 3.1: Mutual Information Between Subsystems**
For circuits with 4+ qubits, compute:
- [ ] **Bipartite Mutual Information:** $I(A:B) = H(A) + H(B) - H(AB)$
  - Measures how much knowing subsystem A tells us about subsystem B
  - I(A:B) = 0 for product states; I(A:B) > 0 for entangled/correlated states
- [ ] **Entropy of subsystems:** Marginal entropy by tracing out qubits
- [ ] **Time evolution of MI:** If your circuits are parameterized, sweep parameters and track how MI changes
- **Discovery Condition:** Circuits where MI exceeds expected "classical correlation" bounds (e.g., GHZ states have maximum MI)

**Task 3.2: Light-Cone Structure**
- [ ] For each qubit pair, measure **correlation decay with distance**
  - Qubits far apart → expect lower correlations
  - Anomalous long-range correlations → potential discovery
- [ ] Compute **Wasserstein-2 distance** between local and global measurement distributions
  - Quantifies how "non-local" the state is
- **Output:** `correlation_analysis.py` (correlation matrices, distance metrics)

---

### Week 4: Anomaly & Phase Detection

**Task 4.1: Identify Circuit Families with Anomalous Behavior**
- [ ] Group circuits by structure (e.g., all VQE ansatzes, all random circuits, all entangling families)
- [ ] For each family:
  - Compute ensemble statistics (mean entropy, mean purity, mean MI)
  - Identify outliers (Z-score > 2.5)
  - Cluster similar circuits
- [ ] **Flag circuits with anomalous properties:**
  - Unexpectedly high/low entropy
  - Non-monotonic MI evolution
  - Sudden transitions in correlation structure

**Task 4.2: Statistical Significance**
- [ ] For each anomalous circuit, run permutation test:
  - Shuffle measurement outcomes 10,000× 
  - Compute metric on shuffled data
  - Compare to observed metric (is it > 99th percentile?)
- **Output:** `anomaly_detection.py` + report: `anomalies_week4.csv`
  - Columns: circuit_id, metric, observed_value, percentile, significance

---

## PHASE 2: SIMULATION-BASED DISCOVERY (Weeks 5–8)

### Goal
Run focused simulation experiments on circuit families that showed anomalies in Phase 1. Use **noise-accurate simulators** to generate synthetic data that rivals real hardware.

### Week 5: Noise-Accurate Simulation Setup

**Task 5.1: Build Noise Model Library**
- [ ] Extract noise characteristics from your existing IBM data:
  - Single-qubit gate errors (T1, T2, readout errors)
  - Two-qubit gate (CNOT) error rates
  - Qubit connectivity
- [ ] Create Qiskit `NoiseModel` objects:
  ```python
  from qiskit_aer import AerSimulator
  from qiskit_aer.noise import NoiseModel
  
  noise_models = {
      'ibm_5qubit': build_ibm_fake_noise(backend='ibmq_athens'),
      'ideal': None,
      'light_noise': scale_noise(ideal_model, 0.5)
  }
  ```
- [ ] Validate noise model against historical data:
  - Run 100 circuits both on historical IBM data and simulated
  - Compare distributions (KL divergence < 0.05)

**Task 5.2: Parametric Circuit Families**
Define 5 circuit families to sweep:
1. **Random Entangling Circuits** (Haar-distributed unitary)
   - Variable depth (1–20 layers)
   - Variable qubit count (4–10)
2. **VQE-Like Ansatze**
   - Parameterized with standard ansatz (UCCSD-like)
   - Parameter sweeps across ~ 10 values
3. **GHZ / Superposition Creators**
   - Designed to create specific entanglement
   - Measure fidelity to target state
4. **Scrambling Circuits** (random, local gates; time evolution)
   - Model chaos dynamics
   - Track entanglement growth
5. **Quantum Error Correction Codes** (surface codes, repetition codes)
   - Measure logical error rates
   - Detect error-suppression thresholds

---

### Week 6: Systematic Parameter Sweeps

**Task 6.1: Generate Sweep Experiments**
For each circuit family:
- [ ] **Depth sweep:** 50 circuits, depths 1–20 layers
- [ ] **Parameter sweep:** 50 circuits, parameters across full [0, 2π] range
- [ ] **Qubit count sweep:** 30 circuits, qubits 4–12
- Total: ~130 circuits × 3 noise models = **390 simulation jobs**

**Task 6.2: Distribute & Execute**
- [ ] Write `simulation_executor.py`:
  ```python
  for circuit_family in families:
      for param_value in param_range:
          circuit = generate_circuit(family, param_value)
          for noise_model in ['ideal', 'ibm', 'light']:
              result = simulate(circuit, noise_model, shots=8192)
              save_result(result, metadata)
  ```
- [ ] Run on local machine (will take 6–12 hours; use multiprocessing)
- **Output:** `simulation_results/` directory (organized by family/noise level)

**Task 6.3: Compare Simulation to Hardware**
- [ ] For circuits that also ran on IBM hardware:
  - Plot: ideal simulation vs. noisy simulation vs. actual hardware
  - Compute KL divergence, Wasserstein distance
  - Validate that noise model accurately captures hardware behavior
- **Discovery Signal:** If simulation matches hardware perfectly, any anomalies found in simulation are real

---

### Week 7: Anomaly Hunting in Simulation

**Task 7.1: Apply Phase 1 Analysis to Simulated Data**
- [ ] Rerun all Phase 1 analyses (entropy, MI, correlations) on simulation results
- [ ] Compare metrics across:
  - Ideal vs. noisy simulations (error impact)
  - Different parameter values (parameter dependence)
  - Different families (structural differences)

**Task 7.2: Search for **Universal Anomalies****
- [ ] **Anomaly Type 1: Noise-Resilient Structures**
  - Circuits where entropy/MI **insensitive** to noise
  - Hypothesis: error correction or robustness structure
  - **Publishable claim:** "Certain circuit topologies exhibit intrinsic noise resilience"
  
- [ ] **Anomaly Type 2: Entropy Suppression**
  - Circuits where final entropy < input entropy (state purification)
  - Compare to theoretical limit (can't exceed coherence time)
  - **Publishable claim:** "Parameterized ansatze can suppress entropy below random baseline"
  
- [ ] **Anomaly Type 3: Non-Monotonic Dynamics**
  - MI increases then decreases (or vice versa) as depth varies
  - Suggests phase transition or resonance
  - **Publishable claim:** "Quantum circuits exhibit phase-transition-like behavior in entanglement structure"
  
- [ ] **Anomaly Type 4: Emergent Periodicity**
  - Metrics return to baseline periodically (period < data size)
  - Suggests hidden symmetry
  - **Publishable claim:** "Circuit families exhibit periodic behavior in information measures"

**Output:** `anomaly_report_week7.md` (quantified findings + statistical significance)

---

### Week 8: Mechanism Identification

**Task 8.1: Why Do Anomalies Occur?**
For top 3 anomalies from Week 7:
- [ ] **Gate-level analysis:**
  - Which gates matter? (ablate gates, one at a time)
  - Which parameters trigger anomaly? (fine sweep around critical value)
  
- [ ] **Entanglement analysis:**
  - Compute entanglement entropy evolution in simulation
  - Use entanglement witness to confirm
  
- [ ] **Information flow:**
  - Use out-of-time-order correlators (OTOCs) to measure scrambling
  - Correlate OTOC with anomaly signature

**Task 8.2: Write Mechanism Paper**
Outline:
1. **Observation:** Measured anomaly (e.g., entropy suppression in family X)
2. **Characterization:** How does it scale? When does it fail?
3. **Mechanism:** Proposed explanation (error suppression, symmetry, state preparation)
4. **Verification:** Ablation test confirming mechanism
5. **Implications:** Why is this interesting? (robustness, optimization, fundamental physics)

**Output:** `mechanism_analysis.py` + draft paper intro/methods

---

## PHASE 3: PUBLICATION PATH (Weeks 9–12)

### Week 9: Validate Against Literature

**Task 9.1: Literature Search**
- [ ] Search arXiv for papers on:
  - "Quantum circuit entanglement structure"
  - "Circuit noise resilience" + "anomaly detection"
  - "Information metrics quantum systems"
- [ ] Document all related work
- [ ] Identify what's novel vs. known

**Task 9.2: Reproduce Known Results**
- [ ] For any cited papers with public code:
  - Run their circuits on your simulator
  - Confirm you replicate their findings
  - This builds credibility for your results

**Task 9.3: Distinguish Your Contribution**
- [ ] Clearly delineate:
  - Standard techniques (entropy, MI computation)
  - Your novel findings (anomaly classes, parameter sweeps)
  - Why your anomalies haven't been reported before

---

### Week 10: Prepare Experimental Paper

**Task 10.1: Write Methods Section**
Structure:
1. Circuit generation (parametric families, parameter ranges)
2. Simulation setup (noise models, shot counts, validation)
3. Analysis methods (entropy, MI, statistical tests)
4. Discovery criteria (what counts as anomaly?)

**Task 10.2: Write Results Section**
- [ ] For each anomaly class:
  - Figure: metric vs. parameter (with confidence bands)
  - Figure: comparison ideal vs. noisy vs. hardware
  - Table: statistical significance (Z-scores, permutation tests, p-values)

**Task 10.3: Write Discussion**
- [ ] Implications for quantum algorithm design
- [ ] Connections to quantum information theory fundamentals
- [ ] Limitations (simulator fidelity, finite statistics)
- [ ] Future work (execute on hardware when available, extend to larger systems)

---

### Week 11: Peer Review Prep

**Task 11.1: Select Target Journal**
Options (by scope):
1. **Phys. Rev. A** (quantum information, very rigorous)
2. **Phys. Rev. B** (quantum materials, more flexibility)
3. **Quantum** (new journal, good for novel methods)
4. **Commun. Phys.** (Nature family, high impact)

**Task 11.2: Prepare Supplementary Materials**
- [ ] Full code (reproducible)
- [ ] Extended data (all circuit families, all noise models)
- [ ] Detailed noise model validation
- [ ] Extended statistical tests

**Task 11.3: Write Abstract & Introduction**
- Abstract: <250 words, hook with clearest anomaly
- Introduction: Problem (limited understanding of circuit structure) → Your solution (systematic analysis)

---

### Week 12: Submit + Iterate

**Task 12.1: Post Preprint on arXiv**
- [ ] Create account if needed
- [ ] Submit paper in appropriate category (quant-ph)
- [ ] Publicize on Twitter, quantum forums

**Task 12.2: Submit to Journal**
- [ ] Follow journal formatting (LaTeX template)
- [ ] Include all supplementary files
- [ ] Write cover letter (why this journal, alignment with scope)

**Task 12.3: Respond to Reviewer Comments**
- [ ] Expect 8–12 weeks for review
- [ ] Prepare responses to likely critiques:
  - "How is this different from standard circuit characterization?" → Show comparison
  - "Why should we care?" → Link to algorithm design, error mitigation
  - "Did you validate on larger systems?" → Roadmap with future hardware time

---

## Concrete Success Metrics

By end of Week 12, you will have:

1. ✅ **One publishable paper** (arXiv + submitted to journal)
2. ✅ **Public code repository** (fully reproducible)
3. ✅ **2–3 anomaly classes identified** with statistical significance > 99%
4. ✅ **Mechanism explanation** for at least one anomaly
5. ✅ **Hardware validation** (simulation results match your existing IBM data)
6. ✅ **Clear discoverables:** What's novel, what's application, what's fundamental

---

## Code Structure (to implement immediately)

```
/workspaces/osiris-cli/quantum_discovery/
├── phase1_analysis/
│   ├── quantum_data_loader.py          # Load 1,430 existing results
│   ├── single_system_analyzer.py       # Entropy, purity, accessible info
│   ├── correlation_analyzer.py         # MI, light-cone structure
│   ├── anomaly_detector.py             # Outlier detection, significance
│   └── phase1_report.py                # Generate CSV/JSON reports
├── phase2_simulation/
│   ├── noise_model_builder.py          # Extract from historical data
│   ├── circuit_families.py             # 5 families + parameter ranges
│   ├── simulation_executor.py          # Run 390 jobs in parallel
│   ├── sweep_analyzer.py               # Apply Phase 1 to simulation
│   └── anomaly_hunter.py               # Find universal anomalies
├── phase3_publication/
│   ├── literature_validator.py         # Check against arXiv
│   ├── mechanism_analyzer.py           # Ablate, explain, verify
│   ├── paper_generator.py              # LaTeX + figures
│   └── results_visualizer.py           # Publication-quality plots
└── QUANTUM_DISCOVERY_RESEARCH_PROGRAM.md (this file)
```

---

## Getting Started This Week

**Action Items (Do These Now):**

1. **Audit your data:** Run `python3 phase1_analysis/quantum_data_loader.py --audit`
   - Find all 1,430 job files
   - Document what you have

2. **Set up simulation:** Install `qiskit-aer`
   ```bash
   pip install qiskit-aer
   ```

3. **Start Phase 1.1:** Begin Week 1 Task 1.1 (data inventory)
   - Should take 2–4 hours of coding

---

## Why This Works (Without QPU Time)

1. **You already have data:** 1,430 existing jobs = statistical gold mine
2. **Simulation is accurate:** Modern Qiskit AerSimulator captures noise well (validated against hardware)
3. **Standard methods are publishable:** Entropy, MI, statistical tests are peer-reviewed, not speculative
4. **Anomalies are real:** Any pattern that survives permutation testing is statistically significant
5. **Clear story:** "We found X" is stronger than "We believe X exists"

---

## Expected Timeline

- **Week 1–4:** You will process 1,430 existing jobs, find 2–5 anomalies
- **Week 5–8:** Simulation will confirm/extend anomalies, explain mechanisms
- **Week 9–12:** Paper ready for arXiv + journal submission

**Total effort:** ~15–20 hours/week (implementable alongside other work)

---

## Questions for You (Before Starting)

1. **Do you have access to your 1,430 IBM job result files?** (JSON, circuit metadata?)
2. **What circuit families did those jobs use?** (VQE, random, hardware-efficient, etc.)
3. **Do you want to focus on 1 anomaly class or pursue all 4 in parallel?**
4. **Is arXiv publication + journal submission your goal, or more exploratory?**

---

This is your actionable research program. Begin with Phase 1, Week 1, Task 1.1 immediately.
