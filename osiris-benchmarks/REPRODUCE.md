# OSIRIS Independent Clean-Room Replication Guide

This guide allows an external researcher to independently reproduce all reported metrics, verify cryptographic ledgers, and execute benchmarks from raw observations on ordinary hardware.

---

## 1. Prerequisites

- Python 3.11+ or 3.12+ (Linux, macOS, or Windows WSL2)
- Git
- Recommended virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

---

## 2. One-Command Clean-Room Verification

To verify all pre-registered models, cryptographic authority ledgers, and experiment data:

```bash
python run_benchmark.py --verify-all
```

This command deterministically checks:
1. **Cryptographic Hashes:** Validates all payload SHA-256 digests against the immutable SQLite authority chain ([`evidence_ledger.db`](file:///C:/Users/Ron/evidence_ledger.db)).
2. **Deterministic Metric Recomputation:** Reruns [`verify_results.py`](file:///C:/Users/Ron/osiris-benchmarks/verify_results.py) on raw count dictionaries and event records (`raw_results.jsonl`), re-deriving all reported means, standard errors, and confidence intervals without reading status claims.
3. **Algebraic State-Preparation Gate:** Verifies that Bell state circuits prepare $|\Phi^+\rangle$ and that product-state controls remain below the $50\%$ entanglement separability threshold.

---

## 3. Benchmark Tracks

### Track A: Governance Benchmark (`gov_bench/`)
Evaluates the SYS-025 AST syntax firewall and SYS-021 cryptographic authorization against a 1,000-task adversarial and benign corpus:
```bash
python run_benchmark.py --track gov
```

### Track D: Autonomous Scientific Falsification (`science_bench/`)
Tests whether an evidence-governed agent detects pre-seeded statistical and experimental defects:
```bash
python run_benchmark.py --track science
```

### Track C: Quantum Control Scheduling (`qctrl_bench/`)
Simulates and evaluates the OSIRIS Adaptive Scheduler v1.0 against Qiskit PassManager DD and fixed 80 ns schedules:
```bash
python run_benchmark.py --track qctrl --mode sim
```
*(Hardware validation requires IBM Quantum API credentials).*

---

## 4. Benchmark Contract & Pass/Fail Criteria

All evaluation criteria, metrics, and thresholds are formally specified in [`benchmark_contract.json`](file:///C:/Users/Ron/osiris-benchmarks/benchmark_contract.json).
