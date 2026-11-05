# OSIRIS v5.2.0: Research-to-Evidence Roadmap, Reproducibility Foundation v1.0 & Frontier QPU Validation

**Permanent DOI:** [10.5281/zenodo.23976303](https://doi.org/10.5281/zenodo.23976303)  
**Cryptographic Authority Ledger:** Sequence Blocks #1–#19 committed to [`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db) (Block #19: `6e90d79c92387310...`)  
**Clean-Room Verification:** `python osiris-benchmarks/run_benchmark.py --verify-all`

---

## 1. What's New in v5.2.0

### A. The 180-Day Research-to-Evidence Roadmap (`OSIRIS_RESEARCH_TO_EVIDENCE_ROADMAP.md`)
A formal six-month research program to convert OSIRIS into a benchmarked, independently reproducible research platform across four core tracks:
1. **Track A (Governance):** `OSIRIS-GOV-BENCH-1` — Can cryptographic payload receipts and AST gates reject unauthorized mutations without impeding legitimate engineering?
2. **Track D (Scientific Falsification):** `OSIRIS-SCI-BENCH-1` — Can evidence-governed execution autonomously identify flawed experimental models, mislabeled states, and statistical multiplicity errors?
3. **Track B (Edge AI):** `OSIRIS-EDGE-BENCH-1` — Memory footprint, tok/s throughput, and perplexity on constrained edge hardware.
4. **Track C (Quantum Control):** `OSIRIS-QCTRL-BENCH-1` — Hardware-aware predictive dynamical decoupling schedules on physical superconducting processors.

### B. Phase 1 Reproducibility Foundation (`osiris-benchmarks/`)
- **`benchmark_contract.json`:** Pinned machine-readable contracts defining performance claims, baseline comparators, primary metrics, and pass/fail thresholds.
- **`environment.lock`:** Locked runtime hashes across host AMD64 Windows and clean-room Linux containers.
- **`verify_results.py`:** Independent deterministic verifier that recomputes every reported mean, standard error, and confidence interval directly from raw event records (`raw_results.jsonl`).
- **`REPRODUCE.md`:** Step-by-step instructions for third-party replication on fresh machines.

### C. Completed Benchmark Milestones
1. **OSIRIS-GOV-BENCH-1 (1,000 Tasks):**
   - **Critical Adversarial Escapes:** Baseline prompt/regex arm permitted **75.0%** ($375 / 500$); OSIRIS Governed Arm achieved **0.0%** ($0 / 500$, 95% Wilson CI: `[0.00%, 0.76%]`).
   - **False Rejection Rate:** **0.0%** ($0 / 500$) with domain-profiled whitelisting.
   - **Mean Latency:** $0.0214\text{ ms}$ overhead.
2. **OSIRIS-SCI-BENCH-1 (100 Tasks):**
   - **Defect Recall:** Baseline heuristic agent caught $0.0\%$ ($0 / 50$); OSIRIS Evidence-Governed Verifier caught **100.0%** ($50 / 50$, 95% Wilson CI: `[92.9%, 100.0%]`).
   - **False Discovery Rate:** **0.0%** ($0 / 50$).

### D. Frontier QPU Campaign: Experiments E0, E1, E2, E3 on IBM Heron r2
- **Experiment E0 (`dblup49kbkrc73cof20g`):** Certified genuine two-qubit entanglement ($\mathcal{F}_{\text{Bell}} \in [93.55\%, 97.30\%]$ at $0\,\mu\mathrm{s}$; $[80.57\%, 87.81\%]$ at $4\,\mu\mathrm{s}$) using the corrected preparation `qc.h(u); qc.h(v); qc.cz(u,v); qc.h(v)`. All 12 product-state controls satisfied $\mathcal{F}_{\text{Bell}} \le 0.50$.
- **Experiment E1 (`dblutq9kbkrc73cofcg0`):** Mapped the multi-duration stagger response landscape across 3 edges and 3 durations, identifying the single-qubit dephasing saturation ratio $\eta_\phi(e, T) = T \cdot \max(\Gamma_\phi(u), \Gamma_\phi(v))$ as the governing physical parameter.
- **Experiment E2 (`dblv7sm74qds73dr8ho0`):** Evaluated frozen `OSIRIS Adaptive Scheduler v1.0` on **4 unseen heavy-hex couplers** (`(15,19)`, `(32,31)`, `(34,33)`, `(35,34)`) across $K=4$ blocks ($288\text{ circuits}$, $294{,}912\text{ shots}$). Demonstrated pre-registered replication of positive stagger gain on `(15,19)@8us` ($+0.56\text{ pp}$, $p = 0.0344$, 4/4 blocks) and `(34,33)@4us` ($+1.33\text{ pp}$).
- **Experiment E3 Transfer (`dblvsnl8ft8s738tsi6g`):** Pre-registered and dispatched 81-circuit cross-chip transfer evaluation to `ibm_kingston` testing whether the adaptive policy transfers across physical hardware without retuning.

---

## 2. Release Artifacts & SHA-256 Checksums

| File Artifact | SHA-256 Digest | Description |
| :--- | :--- | :--- |
| `osiris_research_evidence_v5.2.0.zip` | `42f589cc2e5a8e9c938cb608a8c8ab84103fc0e760f5cfad1d2febcbd9c2bb16` | Complete v5.2.0 evidence bundle ZIP |
| `osiris_research_evidence_v5.2.0.tar.gz` | `d3822fbcb88a10b65645cdac8c7364056910c57b094903511c153640d530c320` | Complete v5.2.0 evidence bundle TAR.GZ |
| `SHA256SUMS.txt` | `9d919c57738b2ae49205da391ebbee378bc0924b23d77470e46dbedc417fa68f` | Checksum manifest of all 80 indexed evidence files |
| `OSIRIS_RESEARCH_TO_EVIDENCE_ROADMAP.md` | `5ec6cc81b06678d02c4d036ca7fdca04a87d210540731b997462e36c14e444f1` | Formal 180-day research program |
| `benchmark_contract.json` | `cbaafab45a4f578b2ad8114e01459f6b0e7d569a11ba8d941968cd6ccc3b5cb2` | Machine-readable benchmark contract |
| `OSIRIS_GOV_BENCH_1_REPORT.md` | `670bc8281f7164d81ea708de29d225d1e4c9eec71064d18ea97db8e8e7266a5f` | OSIRIS-GOV-BENCH-1 empirical evaluation report |
| `OSIRIS_SCI_BENCH_1_REPORT.md` | `edc1ecfd603f83768e6627e8686284aa07722f9b968f86cea0944cdb67e00db9` | OSIRIS-SCI-BENCH-1 empirical evaluation report |
| `zenodo_v520_publication_receipt.json` | Published (Deposition #23976303) | Zenodo publication receipt with permanent DOI |
| `evidence_ledger.db` | Sequence Blocks #1–#19 | Immutable SQLite cryptographic authority chain |
