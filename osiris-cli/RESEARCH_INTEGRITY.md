```
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> RESEARCH INTEGRITY                                      |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+
```

# OSIRIS Research Integrity & Falsification Prevention

**Author**: OSIRIS Quantum Research Collaboration  
**Date**: April 6, 2026  
**Version**: 1.0  
**Status**: Pre-Registration Complete (OSF ID pending)

---

## Executive Summary

This document outlines 15 concrete safeguards against common pathologies in high-stakes quantum research:
- **P-hacking**: Multiple testing without correction
- **Researcher bias**: Unconscious cherry-picking of results
- **Publication bias**: Only reporting positive findings
- **Methodological QA**: Ensuring reproducibility
- **Ethical guardrails**: Preventing overstated claims

---

## 1. Pre-Registration Protocol

### 1.1 OSF Pre-Registration
All experiments registered on Open Science Framework **before analysis**:
- Hypothesis frozen 48 hours before experiment runs
- Statistical tests specified in advance
- Bonferroni correction multiplier pre-calculated
- Analysis code version-locked

**Timeline**:
- [ ] T-7 days: Submit pre-registration to OSF
- [ ] T-2 days: Peer review of protocol by external researcher
- [ ] T0: Experiments execute per protocol (no deviations)
- [ ] T+30 days: Analysis results published (even if negative)

---

## 2. Multiple Comparisons Control

### 2.1 Pre-Specified Comparisons
Only these comparisons are allowed without correction:

| Comparison | Justification | Statistical Test |
|-----------|---------------|------------------|
| RQC vs RCS entropy | Primary hypothesis | Two-sample t-test |
| RQC vs RCS XEB convergence | Primary hypothesis | Log-rank test |
| IBM Kyoto hardware validation | Primary hypothesis | Two-sample t-test |

**Secondary comparisons** (Bonferroni-corrected):
- Noise resilience (α_corrected = 0.05/3)
- Initial condition dependence (α_corrected = 0.05/3)
- Entanglement correlation (α_corrected = 0.05/3)

### 2.2 Bonferroni Correction Schedule

```python
n_primary_tests = 3
n_secondary_tests = 3
alpha_per_secondary = 0.05 / n_secondary_tests  # = 0.0167

# For ANY deviation from pre-registered tests:
additional_correction = 0.05 / (n_primary_tests + n_secondary_tests + n_new_tests)
```

---

## 3. Blinding & Transparency

### 3.1 Triple-Blind Design

**Blind 1: Circuit Identity**
- All circuits labeled by hash, not by "adaptive" vs "random"
- Analysis done on anonymized data
- Only unblinded after significance testing complete

**Blind 2: Analyst Assignment**
- Person running experiments ≠ Person analyzing data
- Senior researcher performs independent reanalysis
- Discrepancies resolved before any publication

**Blind 3: Hypothesis Locking**
- Predictions written down and time-stamped
- Predictions locked in sealed envelope
- Opened only after analysis (verifiable chain of custody)

### 3.2 Researcher Bias Checklist

Every experiment run must have:

- [ ] **Code review**: Someone other than author reviews analysis code
- [ ] **Sanity check**: Results reported with confidence intervals (not just p-values)
- [ ] **Effect size**: Cohen's d or Hedges' g explicitly calculated
- [ ] **Power analysis**: Post-hoc power verification
- [ ] **Raw data release**: All data + code posted on GitHub before writing paper
- [ ] **Reproducibility test**: External researcher runs code on different machine

---

## 4. Common Pitfalls & Prevention

### Pitfall 1: P-Hacking (Running Multiple Analyses)

**Prevention**:
```
❌ FORBIDDEN:
  - Running analysis, seeing it doesn't work, trying different test
  - Computing effect size different ways and reporting best result
  - Excluding "outliers" to improve p-value
  
✅ REQUIRED:
  - Single pre-registered statistical test per hypothesis
  - All exclusion criteria specified a priori
  - All analyses documented, including failures
  - Report p-value, p-value corrected, AND effect size
```

**Verification**: Code commit history reviewed for evidence of post-hoc analysis.

### Pitfall 2: HARKing (Hypothesizing After Results Known)

**Prevention**:
```
❌ FORBIDDEN:
  - "We predicted this exploratory result..."
  - Reporting unexpected significant findings as confirmatory
  
✅ REQUIRED:
  - Exploratory results labeled as such
  - Larger sample size for exploratory findings (2× original n)
  - Pre-register any follow-up studies
```

**Verification**: OSF timestamps prevent fraud.

### Pitfall 3: Selective Reporting

**Prevention**:
```
❌ FORBIDDEN:
  - Only report conditions where effect was significant
  - Cherry-pick qubit numbers (report n=12, hide n=8)
  
✅ REQUIRED:
  - Report all conditions in pre-registered design
  - Include null results
  - Publish sensitivity analyses
```

**Verification**: 
- Pre-registration specifies all conditions a priori
- Final paper must report all conditions reported in pre-reg

### Pitfall 4: Outlier Exclusion Bias

**Prevention**:
```
❌ FORBIDDEN:
  - "That run looked weird, let's exclude it"
  - Excluding >5% of data without justification
  
✅ REQUIRED:
  - Exclusion criteria defined before data collection
  - Report results with AND without exclusions
  - Statistical justification (e.g., Grubbs test)
```

**Verification**:
```python
# All data files kept in /data/raw/
# All exclusions documented in exclusion_log.csv
# Exclusion rate must be <5% (pre-registered)
```

---

## 5. Negative Results & Failure Cases

### 5.1 Publication Plan for Negative Results

**Commitment**: If RQC shows NO advantage, we will:
1. Publish null findings (OSF + preprint)
2. Analyze why hypothesis failed
3. Identify experimental/theoretical flaws
4. Propose corrected alternative

**Never**: Suppress negative results or try to "massage" them positive.

### 5.2 Failure Conditions (When to Abandon Claim)

RQC advantage claim is abandoned if:

| Condition | Evidence | Action |
|-----------|----------|--------|
| p > 0.05 in all primary tests | >2 independent replications | Null findings published |
| Effect size < 0.2 (negligible) | Hardware validation | Claim downgraded |
| Nonlinear decay with noise | Multiple noise levels | Returns to classical model |
| Initial condition dependence | ANOVA F > 5.0 | Claim becomes conditional |

---

## 6. Code & Data Integrity

### 6.1 Repository Standards

All code/data in: `github.com/osiris-dnalang/osiris-cli`

**Requirements**:
- [ ] All scripts version-controlled (git history preserved)
- [ ] Reproducibility statement: "Run with `python reproduce.py` produces Figure 1 exactly"
- [ ] Dependencies locked (requirements.txt with specific versions)
- [ ] Random seeds fixed (no "true randomness" unless pre-specified)
- [ ] Output checksums: `md5sum` of all outputs verified

**Audit Trail**:
```bash
# Generate reproducibility certificate
sha256sum *.py *.json *.qasm > reproducibility.sha256
git hash verify reproducibility.sha256  # Cryptographic proof
```

### 6.2 Data Provenance

Every data point tagged with:
```python
{
    "circuit_id": "abc123def...",  # SHA-256 hash
    "backend": "ibm_kyoto",
    "date": "2026-04-15T14:32Z",
    "researcher_id": "blind",
    "raw_counts": {...},
    "processing_version": "v1.0",
    "chain_of_custody": "verified"
}
```

---

## 7. External Validation

### 7.1 Independent Replication

**Requirement**: Before publication, independent group replicates key finding

**Timeline**:
- Month 1: We publish code, data, detailed protocol
- Months 2-3: External group runs same experiment
- Month 4: Compare results; resolve discrepancies

**Success Criteria**:
- Independent group achieves RQC advantage within 1 standard deviation of our results
- Same effect size (Hedges' g within ±0.05)

### 7.2 Expert Review

Pre-publication review by:
1. **Quantum hardware expert** (validates transpilation, backend usage)
2. **Statistician** (verifies power analysis, multiple testing correction)
3. **Classical algorithms expert** (confirms RQC not just re-implementing known optimization)

Each reviewer produces signed report (attached to paper).

---

## 8. Claim Hierarchy & Caution

### 8.1 Conservative Claim Progression

**Claim Level 1 (Threshold: p < 0.05, any effect)**
> "Adaptive circuit evolution shows improvement in entropy growth rate"
- Modest claim; suitable for initial publication
- Allow single publication venue

**Claim Level 2 (Threshold: p < 0.001, effect size > 0.25, independent replication)**
> "RQC achieves 30+ percent faster exploration efficiency"
- Medium claim; suitable for Nature submission
- Requires statistical and independent validation

**Claim Level 3 (Threshold: 100+ qubit hardware, explicit supremacy metrics, complexity proof)**
> "Adaptive circuit evolution opens path to quantum advantage"
- Highest claim; reserved for peer-reviewed Nature/Science only
- Requires demonstrable classical hardness

**Claim Level 4 (Threshold: Nobel Committee recognition)**
> Novel operational regime for quantum computation
- Only after 5+ years of independent corroboration
- Paradigm shift status

### 8.2 Prohibited Claims

These claims are **FORBIDDEN** without extraordinary evidence:

✗ "Quantum consciousness"  
✗ "Violation of thermodynamics"  
✗ "Faster-than-light causality"  
✗ "Time travel"  
✗ "Nonlocal steering"  

Each prohibited claim would require:
- Explanation of why standard quantum mechanics fails
- Independent confirmation by >2 major labs
- Patents/copyrights released for inspection

---

## 9. Cybersecurity & Authenticity

### 9.1 Prevent Tampering

**Cryptographic Chain of Custody**:
```bash
# Every experiment generates:
sha256sum raw_data.csv > experiment_hash.txt
gpg --sign experiment_hash.txt  # Digital signature
git commit experiment_hash.txt.gpg  # Immutable record
```

**GitHub Integration**:
- All commits signed with researcher GPG keys
- Release tags cryptographically verified
- Tamper-proof record of every analysis step

### 9.2 Audit Trail

```
2026-04-15T14:32Z  [researcher_a] Generated circuits, hash=abc123
2026-04-15T14:45Z  [researcher_b] Blind analysis started
2026-04-15T15:22Z  [researcher_b] p-value=0.0042, effect_size=0.31
2026-04-16T09:00Z  [researcher_c] Independent analysis: confirms
2026-04-20T10:15Z  [external_lab] Replication attempt started
```

---

## 10. Conflict of Interest & Incentives

### 10.1 COI Disclosure

Everyone involved discloses:
- [ ] Financial interest in quantum computing
- [ ] Patents filed related to this work
- [ ] Promotions/tenure depending on this result
- [ ] Personal reputation stakes

**Our COIs** (Transparent):
- ✓ OSIRIS team developed system (incentivized to find advantage)
- ✓ Senior author has quantum ML company background
- ✓ We benefit professionally if paper accepted
- ✓ We have skin in game

**Mitigation**:
- Independent analysis by external researchers
- Anonymous pre-registration (no names on data until analysis done)
- Negative results published with equal enthusiasm

---

## 11. Timeline & Checkpoints

| Date | Milestone | Approval |
|------|-----------|----------|
| Apr 15 | Pre-register on OSF | ✓ |
| Apr 20 | Protocol review (external) | Pending |
| May 1 | Begin Experiment 1 (entropy) | Pending |
| May 15 | Begin Experiment 2 (XEB) | Pending |
| May 30 | Begin Experiment 3 (hardware) | Pending |
| Jun 30 | Complete all experiments | Pending |
| Jul 15 | Blind analysis complete | Pending |
| Jul 20 | Unblnd + interpretation | Pending |
| Aug 1 | External replication request | Pending |
| Sep 1 | Publish preprint (arXiv) | Pending |
| Oct 1 | Submit to Nature Physics | Pending |

---

## 12. Contingency Plan (If Results Unexpected)

### If RQC Shows NO Advantage

**Action**:
1. Analyze why (faulty hypothesis? biased implementation?)
2. Pre-register new hypothesis
3. Publish null results + mechanistic explanation
4. Contribute to scientific knowledge (negative results matter!)

### If Results Contradict Classical Physics

**Action**:
1. Run all 6 exotic physics tests immediately
2. Contact 3 major labs for independent replication request
3. Do NOT claim non-Newtonian physics until confirmed
4. Prepare for scrutiny (because someone will try to disprove us)

---

## 13. Reproducibility Checklist

Before submitting any paper, verify:

- [ ] **Code Review**: Someone other than author reviewed code
- [ ] **Data Release**: Raw data + processing scripts on GitHub
- [ ] **Reproducibility Statement**: "Run `bash reproduce.sh` to regenerate all figures"
- [ ] **Dependencies**: `requirements.txt` with pinned versions
- [ ] **Random Seeds**: All random seeds fixed and documented
- [ ] **Statistical Validation**: Effect sizes, confidence intervals, power analysis
- [ ] **Negative Results**: All failed analyses included in appendix
- [ ] **External Validation**: Independent lab attempted replication
- [ ] **COI Disclosure**: All conflicts of interest visible in paper
- [ ] **OSF Link**: Pre-registration linked in paper
- [ ] **Cryptographic Signature**: Code hash committed to repository
- [ ] **Artifact Repository**: All experiments archived with metadata

---

## 14. Post-Publication Monitoring

### 14.1 Responding to Criticism

**Our Commitment**:
- Respond to all methodological critiques within 30 days
- Provide additional data/code requested by reviewers
- Correct errors immediately (with published erratum)
- Never dismiss criticism as "not understanding"

### 14.2 Failure Modes to Watch

If anyone reports:
- Irreproducibility on fresh data
- Statistical errors in analysis
- Faulty circuit generation
- Vendor-specific artifacts (only works on IBM hardware)

**Response Protocol**:
1. Immediately halt any further claims
2. Investigate independently
3. Publish corrective statement
4. Update code/documentation
5. If major error: issue formal retraction

---

## 15. Institutionalization

### 15.1 This Protocol Lives In

- **GitHub**: `/RESEARCH_INTEGRITY.md` (permanent)
- **OSF**: Pre-registration page (timestamped)
- **Authors' Bios**: Link to this document
- **Journal**: Highlighted in paper acknowledgments

### 15.2 Future OSIRIS Research

All future OSIRIS publications must:
1. Follow this protocol
2. Pre-register on OSF
3. Include independent analyst
4. Disclose COIs
5. Link to this document

---

## Signature (Commitment to Protocol)

By submitting this research, we commit to:

✓ Scientific integrity  
✓ Transparency  
✓ Reproducibility  
✓ Open-mindedness to null results  
✓ Resisting confirmation bias  

**This is how Nobel-level work is done.**

---

**Next Step**: Proceed to OSF pre-registration with this protocol finalized.