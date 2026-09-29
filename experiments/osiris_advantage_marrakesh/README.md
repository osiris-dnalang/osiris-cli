# OSIRIS Quantum Coherence Advantage Hardware Run — IBM Heron r2 (ibm_marrakesh)

**Job ID:** `dau0q3qhcrkc73durtgg`  
**Backend:** `ibm_marrakesh` (156-qubit Heron r2)  
**Date (UTC):** 2026-09-29 19:10:20Z  
**Calibration Hash:** `63f10bd484207c5044237b4115a46a0d29856036c923a2cde165baed57d15c9c`  
**Pre-registration Manifest SHA-256:** `2d4c19a4a53301a1ac42459acd8b5b0d8cba0d588fa2523ed0994e5e1612d2f9`  
**Ledger Head:** `6d7fd1390c1bab25b52f3e5e07be893aaa7194d8e3bd81db8466085da6e38d37`  
**QPU Execution Time:** 5 s  

## Executive Summary
This experiment provides empirical hardware validation on IBM Quantum's 156-qubit Heron r2 processor (`ibm_marrakesh`) testing OSIRIS bipartite-staggered dynamical decoupling against unmitigated idle decoherence and standard textbook simultaneous DD.

The experiment was pre-registered into an immutable write-ahead append-only ledger prior to submission.

## Results Table (8-Qubit Chain: [1, 2, 3, 4, 5, 6, 7, 8])

| Condition | T (µs) | Mean Survival P(+) | 95% Confidence Interval | Effective Loss Rate Γ (µs⁻¹) |
|---|---|---|---|---|
| `cpmg8` | 16.0 | **0.9139** | [0.9075, 0.9204] | 0.0118 |
| `cpmg8` | 32.0 | **0.8344** | [0.8289, 0.8398] | 0.0126 |
| `none` | 16.0 | **0.6382** | [0.6313, 0.6450] | 0.0804 |
| `none` | 32.0 | **0.5945** | [0.5942, 0.5947] | 0.0521 |
| `xy4x2` | 16.0 | **0.9135** | [0.9097, 0.9172] | 0.0119 |
| `xy4x2` | 32.0 | **0.8342** | [0.8291, 0.8394] | 0.0126 |
| `xy4x2_stag` | 16.0 | **0.9313** | [0.9307, 0.9319] | 0.0092 |
| `xy4x2_stag` | 32.0 | **0.8997** | [0.8945, 0.9048] | 0.0070 |
| `xy8_stag` | 16.0 | **0.9318** | [0.9309, 0.9326] | 0.0092 |
| `xy8_stag` | 32.0 | **0.8998** | [0.8982, 0.9014] | 0.0070 |

## Pre-registered Hypothesis Evaluation

1. **Advantage over Bare Idle (T = 32 µs):**
   - Bare idle survival (`none`): **0.5945**
   - OSIRIS best staggered (`xy8_stag`): **0.8998**
   - Observed Gain: **+0.3053** (Threshold: +0.1500) -> **MET**

2. **Advantage over Textbook Simultaneous DD (T = 32 µs):**
   - Standard simultaneous XY4x2 (`xy4x2`): **0.8342**
   - OSIRIS best staggered (`xy8_stag`): **0.8998**
   - Observed Gain: **+0.0656** (Threshold: +0.0200) -> **MET**

3. **Statistical Confidence:**
   - 95% Bootstrap CI `xy8_stag`: `[0.8982, 0.9014]`
   - 95% Bootstrap CI `xy4x2`: `[0.8291, 0.8394]`
   - Non-overlapping: **YES**

## Hardware Provenance & Reproducibility
- All raw counts are stored in `dau0q3qhcrkc73durtgg.counts.json`.
- Full transpiled circuits and metadata are preserved in `dau0q3qhcrkc73durtgg.meta.json`.
- Hash chain verified in `ledger.jsonl`.
