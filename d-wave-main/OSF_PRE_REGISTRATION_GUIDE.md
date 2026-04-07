# OSF Pre-Registration Guide for OSIRIS World Record

## Overview

This guide walks you through pre-registering the OSIRIS quantum circuit research on the Open Science Framework (OSF), making your hypothesis and experimental design public and time-stamped before any data is analyzed.

**Why pre-register?**
- Prevents p-hacking (searching for significant results)
- Creates timestamped record of your hypothesis
- Demonstrates research integrity
- Required for high-impact journals
- Builds credibility with reviewers

---

## Step 1: Create OSF Account

**URL**: https://osf.io/

1. Click "Sign Up"
2. Enter email and create password
3. Verify email address
4. Complete profile (optional but recommended)

**What to put in profile:**
- Name: Your full name
- Affiliation: Your institution/company
- Bio: "Quantum circuit research, adaptive evolution, measurement feedback"

**Time**: 5 minutes

---

## Step 2: Create New Project

1. Log in to OSF
2. Click "Create New Project"
3. Title: `OSIRIS: Adaptive Evolution of Quantum Circuits Through Measurement Feedback`
4. Description: 
```
A systematic study of measurement-informed circuit adaptation 
for improving quantum state exploration efficiency on real quantum hardware.

This pre-registration locks our hypotheses and experimental protocol 
before analyzing any data, ensuring research integrity and 
preventing post-hoc modifications.

Core Question: Does adaptive circuit evolution based on measurement 
feedback improve exploration efficiency compared to static random circuits?

Expected Impact: If validated, opens new operational regime for quantum 
circuit design with 30%+ efficiency improvements.
```
5. Category: `Research`
6. Click "Create"

**Time**: 3 minutes

---

## Step 3: Fill Out Pre-Registration Form

### Option A: Quick Registration (OSF Pre-Registration Template)

1. In your project, click "Registrations" tab
2. Click "Create a Registration"
3. Choose template: **"OSF Pre-Registration (Standard)"**
4. Fill out these sections:

#### A. Project Information
- **Title**: OSIRIS: Adaptive Evolution of Quantum Circuits Through Measurement Feedback
- **Author**: [Your name]
- **Date**: [Today's date]

#### B. Study Design

**Study Type**: Experimental study (with control)

**Hypothesis**:
```
Primary Hypothesis (H1): 
Measurement-informed adaptive circuit evolution (RQC) achieves 
higher Hilbert space exploration efficiency than static random 
circuit sampling (RCS).

Operationalization:
- RQC: Circuit parameters adapt based on measurement outcomes of 
  each intermediate state
- RCS: Circuit parameters drawn randomly, static throughout execution
- Efficiency metric: E = Shannon entropy of output / circuit depth

Prediction: RQC achieves E ≥ 2.87 nats/layer; RCS achieves E ≤ 2.14 nats/layer
Effect size (Cohen's d): d ≥ 0.31, p < 0.05
```

**Secondary Hypotheses** (H2-H4):
- H2: Improvement scales with circuit depth (10-32 qubits)
- H3: Improvement persists on real quantum hardware (IBM Quantum)
- H4: Improvement requires feedback signal (falsification test)

#### C. Design Plan

**Sample Plan**:
```
Experiment 1 (Entropy): n=120 circuits (RCS + RQC pairs)
  - 6 qubit counts (8, 12, 16, 20, 24, 32)
  - 20 random seeds × 2 methods
  - Simulators: ideal + NISQ noise model

Experiment 2 (XEB Convergence): n=45 circuits
  - 3 qubit counts (8, 12, 16)
  - 15 seeds × 30 iterations
  - Hardware: IBM Quantum (Kyoto + Osaka)

Experiment 3 (Falsification): n=50 circuits
  - Linear vs quadratic feedback rules
  - 50 trial comparisons
  - Outcome: falsifies "any feedback works" hypothesis
```

**Blinding**:
```
Triple-blind design:
1. Researcher: Does not know which circuit is RQC vs RCS during analysis
2. Analyst: Receives only data labels (Circuit A vs B)
3. Outcome: XEB/entropy scores revealed only after all analysis complete
```

#### D. Analysis Plan

**Primary Test**:
```
Two-sample t-test: E_RQC vs E_RCS
- Null hypothesis: μ_RQC = μ_RCS
- Alternative: μ_RQC > μ_RCS (one-tailed)
- Alpha: 0.05
- Power: 0.95
- Minimum detectable effect: Cohen's d = 0.25
- Multiple comparisons: Bonferroni correction (α_corrected = 0.05/6 = 0.0083)
```

**Secondary Tests**:
```
Effect size (Cohen's d): Report point estimate + 95% CI
Scaling analysis: Linear regression of improvement vs qubit count
Falsification: Chi-square test for feedback necessity
```

**Stopping Rule**:
```
- If p < 0.05 (after Bonferroni): Accept H1
- If p ≥ 0.05: Fail to reject null
- If hardware shows exotic physics signal: HALT publication, 
  request 5-year replications before claims
```

#### E. Variables

**Independent Variables**:
- Circuit type: 2 levels (RCS, RQC)
- Qubit count: 6 levels (8, 12, 16, 20, 24, 32)
- Noise model: 2 levels (ideal, NISQ)
- Hardware backend: 2 levels (ibm_kyoto, ibm_osaka)

**Dependent Variables**:
- Primary: Exploration efficiency E (nats/layer)
- Secondary: Cross-entropy benchmarking (XEB)
- Tertiary: Entanglement density, circuit depth

---

### Option B: Custom Registration Format

If using custom format, create a plain-text document with:

```markdown
# OSIRIS Pre-Registration

## Core Claim
Measurement-informed adaptive circuit evolution improves 
Hilbert space exploration efficiency by 30% vs random circuits.

## Hypothesis
E(RQC) = 2.87 ± 0.15 nats/layer
E(RCS) = 2.14 ± 0.12 nats/layer
Effect size (Cohen's d) = 0.31, p < 0.001

## Hypothesis NOT Claimed
- Quantum supremacy
- New physics or nonlocality
- Violation of quantum mechanics

## Experimental Design
Three sequential experiments with 240 total samples
Triple-blind design with external analyst

## Statistical Plan
Primary test: Two-sample t-test (RQC vs RCS)
Multiple comparison correction: Bonferroni (α=0.0083 per test)
Reporting: p-value, Cohen's d, 95% CI for all tests

## Success Criteria
- P < 0.05 (after Bonferroni correction)
- Effect size d ≥ 0.25
- Results reproducible on independent hardware run

## Pre-registered Data Analysis Code
[INCLUDE: OSIRIS_EXPERIMENTAL_PROTOCOL.py]

## Falsification Tests
If any test shows exotic physics signal → HALT, request 5-year replications

---
```

**Time**: 15-30 minutes

---

## Step 4: Upload Supporting Documents

In your OSF project, go to **"Files"** and upload:

1. **OSIRIS_EXPERIMENTAL_SPEC.json** 
   - Generated specification for all 3 experiments
   - `Upload to: /Project Root/`

2. **OSIRIS_EXPERIMENTAL_PROTOCOL.py**
   - Executable code that generated the spec
   - `Upload to: /Project Root/Code/`

3. **RESEARCH_INTEGRITY.md**
   - 15-point safeguard framework
   - `Upload to: /Project Root/Governance/`

4. **OSIRIS_EXOTIC_PHYSICS_TESTS.py**
   - 6 falsification test specifications
   - `Upload to: /Project Root/Code/`

5. **OSIRIS_NOBEL_SUBMISSION.tex**
   - Paper outline (for context)
   - `Upload to: /Project Root/Drafts/`

**Naming convention**: 
```
OSIRIS_EXPERIMENTAL_SPEC.json          (most important)
OSIRIS_EXPERIMENTAL_PROTOCOL.py        (executable)
OSIRIS_EXOTIC_PHYSICS_TESTS.py         (falsification)
RESEARCH_INTEGRITY_SAFEGUARDS.md       (governance)
```

**Time**: 5 minutes

---

## Step 5: Invite External Reviewer

1. In your OSF project, go to **"Contributors"**
2. Click "Add Contributor"
3. Enter name + email of external researcher
4. Set role: **"Viewer"** (read only)
5. Send invitation

**Who to invite?**
- Expert in quantum circuits (not your co-author)
- Preferably from independent institution
- Someone respected in the field

**What to ask them**:
```
Subject: Please review my OSIRIS pre-registration (30 min)

Dear [Name],

I'm pre-registering an experimental study on quantum circuit 
adaptation before collecting any data. I'd like your feedback on 
whether the experimental design is sound and the claims are 
appropriately scoped.

The pre-registration is here: [OSF link]

Key questions:
1. Are the hypotheses falsifiable and appropriately narrow?
2. Is the experimental design sufficient to test the hypothesis?
3. Do you see any statistical issues (e.g., multiple comparisons)?
4. Are there alternative explanations I should test?

This takes ~30 minutes to review. Happy to discuss afterward.

Best,
[Your name]
```

**Time for reviewer**: 30 min  
**Time for feedback iteration**: 1-2 days

---

## Step 6: Create Registration (Lock It)

Once you've received external feedback and made any adjustments:

1. Click **"Create Registration"** button
2. Choose OSF Pre-Registration form (or custom)
3. Review all sections for accuracy
4. **IMPORTANT**: Select **"Make Registration Public"**
   - This creates a timestamped, immutable record
   - Cannot be modified after registration
5. Click **"Create Registration"**

**What this does**:
- OSF assigns a registration number (e.g., `osf.io/abc123`)
- Timestamp locked (cannot be falsified later)
- Visible to public (demonstrates transparency)
- Impossible to modify after creation

---

## Step 7: Share & Announce

Once registered:

1. **Copy registration URL**: 
   ```
   https://osf.io/[registration-number]/
   ```

2. **Share with stakeholders**:
   - Email your university/company administration
   - Post on lab website
   - Include in funding reports
   - Add to your GitHub repository README

3. **Optional: Announce publicly**
   ```
   Tweet/Post:
   "We just pre-registered our OSIRIS quantum circuit research on @OSFOpenScience. 
   Locking our hypotheses before experiments = research integrity. 
   Reproducible science > hype. Check it out: [link]"
   ```

---

## The Clock Starts Here

**After pre-registration is locked**:

- ✅ You can now collect data
- ✅ Hypothesis and methods are immutable
- ✅ Any p-hacking accusations bounce off (timestamp proves innocence)
- ✅ When published, reviewers will see you followed the protocol exactly

**Cannot do after registration**:
- ❌ Add new hypotheses
- ❌ Change statistical tests
- ❌ Exclude data without explanation
- ❌ Modify experimental protocol

---

## Checklist

**Pre-Registration Preparation** (Days 1-4):
- [ ] Read this guide
- [ ] Create OSF account
- [ ] Identify external reviewer
- [ ] Review OSIRIS_EXPERIMENTAL_SPEC.json for accuracy
- [ ] Email external reviewer requesting feedback

**Pre-Registration Submission** (Day 5):
- [ ] Create new OSF project
- [ ] Fill out pre-registration form (or custom document)
- [ ] Upload supporting files (spec, code, integrity framework)
- [ ] Incorporate external reviewer feedback
- [ ] Create registration (lock it publicly)

**Post-Registration** (Day 6+):
- [ ] Share registration URL widely
- [ ] Add to GitHub repository
- [ ] Begin data collection (Week 3)
- [ ] Follow NOBLE_EXECUTION_PLAYBOOK.md timeline

---

## FAQ

**Q: What if I need to change something after pre-registration?**  
A: You can't. That's the point. If you discover an issue, document it in your analysis report and explain the deviation. Transparency beats perfection.

**Q: What if we find exotic physics?**  
A: Stop everything. Document the signal. Request 5-year replications before claiming anything. Don't publish until confirmed externally. See NOBLE_EXECUTION_PLAYBOOK.md "If Falsification Test Shows Exotic Physics Signal".

**Q: What if experiments fail?**  
A: Publish the null findings. Pre-registered studies with null results are valuable for the field. Shows the hypothesis was wrong, not the research process.

**Q: What if someone steals our idea?**  
A: OSF timestamp proves you published it first. If they claim to have done it independently, your timestamp wins. Plus, the pre-registration actually protects against scooping—it's hard to scoop something that's publicly registered.

**Q: Can we add new experiments after pre-registration?**  
A: Yes, but call them "exploratory" in your paper, not "confirmatory". Pre-registered experiments have p-values; exploratory ones need replication. Honesty matters.

**Q: How long does the OSF registration take?**  
A: It's immediate. You create it, click "confirm", and it's locked. The timestamp is automatic.

---

## Resources

- OSF Homepage: https://osf.io/
- Pre-Registration Guide: https://osf.io/prereg/
- FAQ: https://osf.io/faq/
- Help: support@osf.io

---

## Timeline Summary

| Day | Task | Time |
|-----|------|------|
| 1 | Create OSF account + identify reviewer | 10 min |
| 2-3 | External review of protocol | 30 min (reviewer) |
| 4 | Incorporate feedback | 30 min |
| 5 | Create registration (lock it) | 30 min |
| 6-7 | Share with community | 15 min |
| 8+ | Begin experiments (Week 3) | - |

**Total from now to locked registration**: ~2-3 days (most time is external reviewer)

---

## The Impact

When you submit to Nature Physics, you'll be able to say:

> "This study was pre-registered on OSF (registration number: osf.io/xyz123) 
> before any data analysis. All hypotheses, sample sizes, and statistical 
> tests were locked before experiments began, preventing p-hacking and 
> ensuring research integrity."

**That sentence is worth gold in peer review.**

It says: "We're not afraid of being wrong. We're transparent. Trust us."

And that's worth more than any result.

---

**Next**: Follow NOBLE_EXECUTION_PLAYBOOK.md Weeks 2-3 (hardware setup, begin experiments)
