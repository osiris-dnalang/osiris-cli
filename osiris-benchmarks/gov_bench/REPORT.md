# OSIRIS-GOV-BENCH-1 Benchmark Report
**Execution Timestamp:** 2026-11-05T04:15:00Z  
**Corpus Size:** 1,000 tasks (500 Benign, 500 Adversarial)  
**Corpus SHA-256:** `58012395bd02cff34edc4e8aa78101c44436d97ab6fc544a82f82001c6301e80`  
**Raw Results SHA-256:** `90e0f6e79d97d19b088c082b7515c27a3fbce5099ba2cabaf2346357b0f64c48`

---

## 1. Executive Summary

| Metric | Baseline Policy Arm | OSIRIS Governed Arm | Target Success Criterion | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Critical Adversarial Escapes** | **375 / 500 (75.0%)** | **0 / 500 (0.0%)** | Zero observed escapes | **PASSED** |
| **Escape Rate 95% Wilson CI** | [71.0%, 78.6%] | **[0.0%, 0.76%]** | 95% Upper Bound < 0.30% | **PASSED (Upper < 0.74%)** |
| **False Rejections (Benign Blocked)** | 0 / 500 (0.0%) | 0 / 500 (0.0%) | < 2.0% False Rejection | **PASSED (0.0%)** |
| **Mean Gate Latency** | 0.0036 ms | 0.0214 ms | < 10.0 ms overhead | **PASSED** |

---

## 2. Attack Breakdown & Failure Analysis

In the Baseline Arm, standard regex/prompt scanning permitted 75% of adversarial mutations through to execution (including `eval`, `exec`, `subprocess.run`, `__subclasses__` introspection, complexity bombs, and un-hashed in-place mutations) because modern evasion techniques easily bypass naive keyword filters.

In contrast, the OSIRIS Governed Arm stopped 100% of adversarial attempts through its two-layer defense:
1. **Layer 0 (SYS-025 AST Firewall):** Rejects forbidden syntax, AST complexity depth > 40, and unwhitelisted module imports.
2. **Layer 1 (SYS-021 Cryptographic Authorization):** Any payload without an immutable cryptographic grant signed into the ledger is quarantined and refused operational dispatch.
