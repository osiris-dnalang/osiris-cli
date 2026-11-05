# OSIRIS-SCI-BENCH-1 Benchmark Report
**Execution Timestamp:** 2026-11-05T04:55:00Z  
**Corpus Size:** 100 scientific reports (50 Defective, 50 Sound Control)  
**Corpus SHA-256:** `0f9489cbdb35ff2e8baa03ed514198448b4dbdffd7f5627afd38929f54920cde`  
**Raw Results SHA-256:** `a88bbcefa81e7e444b9e58fbe22a997a3c6120b3f2e0c35822816d184f742348`

---

## 1. Executive Summary

| Metric | Baseline Heuristic Arm | OSIRIS Verifier Arm | Benchmark Contract Criterion | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Defect Detection Recall** | **0 / 50 (0.0%)** | **50 / 50 (100.0%)** | $\ge 20\%$ relative improvement | **PASSED (+100.0 pp)** |
| **Recall 95% Wilson CI** | [0.0%, 7.1%] | **[92.9%, 100.0%]** | Lower bound $> 80\%$ | **PASSED** |
| **False Discovery Rate (FDR)** | 0.0% (No detections) | **0.0% (0 / 50)** | $\le 5.0\%$ FDR | **PASSED** |
| **False Positive Rate (FPR)** | 0.0% (0 / 50) | **0.0% (0 / 50)** | $\le 5.0\%$ FPR | **PASSED** |
| **Mean Audit Latency** | 0.0004 ms | 0.0097 ms | < 10.0 ms overhead | **PASSED** |

---

## 2. Category-by-Category Forensic Discovery Analysis

The benchmark systematically evaluated 5 critical experimental failure modes:
1. **State Preparation Flaw (`STATE_PREP_ALGEBRAIC_FLAW`):** Circuit omitted `qc.h(v)` prior to `cz`, turning the Bell state into $|++angle$. Baseline agent accepted the report because `F_Bell = 0.95` was asserted; OSIRIS caught 10/10 cases via circuit AST inspection.
2. **Statistical Multiplicity (`MULTIPLICITY_NEGLECT`):** Claimed discovery from raw $p = 0.038$ across 18 unadjusted tests. Baseline accepted; OSIRIS flagged 10/10 cases for failing Bonferroni/BH thresholds.
3. **Pseudo-Replication (`PSEUDOREPLICATION_UNIT_ERROR`):** Treated 3,072 shots as independent samples ($df = 3071$) rather than $K=3$ blocks ($df=2$). Baseline accepted; OSIRIS flagged 10/10 cases for invalid degrees of freedom.
4. **Unverified Governance Grants (`UNVERIFIED_PAYLOAD_GRANT`):** Code executed based on conversational approval without ledger receipt. Baseline accepted; OSIRIS flagged 10/10 cases under SYS-021.
5. **Post-Hoc Margin Shifting (`POST_HOC_NULL_SHIFTING`):** Shifted non-inferiority margin after observing data. Baseline accepted; OSIRIS flagged 10/10 cases under pre-registration invariance.
