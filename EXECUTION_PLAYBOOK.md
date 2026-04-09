```
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> EXECUTION PLAYBOOK                                      |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+
```

# OSIRIS Automated Discovery - Execution Playbook

**How to run a 1-week automated research campaign from zero to publication.**

---

## Phase 1: Setup (30 minutes)

### Step 1: Get API Tokens

**IBM Quantum Token:**
1. Visit https://quantum.ibm.com/
2. Sign in / create account
3. Go to Settings → Account
4. Copy "API Token"

**Zenodo Token (optional, for publishing):**
1. Visit https://zenodo.org/
2. Sign in / create account
3. Go to Settings → Applications
4. Create personal access token
5. Copy token

### Step 2: Configure Environment

```bash
# Add to ~/.bashrc or ~/.zshrc (persistent)
export IBM_QUANTUM_TOKEN="your_ibm_token_here"
export ZENODO_TOKEN="your_zenodo_token_here"
export IBM_BACKEND="ibm_torino"  # or ibm_fez, ibm_nazca

# Test immediately
source ~/.bashrc
echo $IBM_QUANTUM_TOKEN  # Should output your token
```

### Step 3: Install & Verify

```bash
cd /workspaces/osiris-cli

# Run setup
bash setup_osiris.sh

# Verify installation
python3 -c "
from osiris_auto_discovery import AutoDiscoveryPipeline
from osiris_orchestrator import campaign_week1_foundation
print('✓ All imports successful')
"
```

---

## Phase 2: Week-1 Campaign (Mon-Fri)

### Monday-Tuesday: Foundation Experiments

**Goal:** Establish baseline measurements

Run foundation campaign:
```bash
python osiris_cli.py run --campaign week1_foundation
```

**What runs:**
1. **XEB Baseline** - Is random circuit sampling producing measurable XEB?
2. **Entropy Growth** - Does entropy increase with circuit depth?
3. **Shallow vs Deep** - Do shallower circuits degrade less under noise?
4. **Backend Consistency** - Are results reproducible across hardware?

**Expected output:**
```
discoveries/
├── day1_xeb_baseline_12q_<id>.json
├── day2_entropy_growth_<id>.json
├── day3_shallow_vs_deep_<id>.json
└── day4_backend_consistency_<id>.json
```

**Check results:**
```bash
python osiris_cli.py status
```

Sample output:
```
Total Results: 4

✓ day1_xeb_baseline_12q: p=3.2e-05  (SIGNIFICANT)
✓ day2_entropy_growth: p=0.0012      (SIGNIFICANT)
✗ day3_shallow_vs_deep: p=0.156      (null result)
✓ day4_backend_consistency: p=0.031  (SIGNIFICANT)

Significant Results: 3/4
```

**What this means:**
- ✓ = Can be published to Zenodo
- ✗ = Saved locally, but not published (still scientifically valuable!)

---

### Wednesday: Adaptive Hypothesis Testing

**Goal:** Test if feedback-driven circuits improve performance

Run adaptive campaign:
```bash
python osiris_cli.py run --campaign week1_adaptive
```

**What runs:**
1. **RQC vs RCS** - Do adaptive circuits beat random ones?
2. **Convergence Rate** - Does adaptation speed up learning?

**Interpretation:**
- If both pass → You have a publishable discovery
- If one passes → Partial validation of hypothesis
- If both fail → Null result (still valuable for ruling out claims)

Example result:
```
✓ adaptive_xeb_improvement: p=0.008, d=0.72
  → Adaptive circuits DO beat random circuits
  → PUBLISHABLE

✗ adaptive_convergence_rate: p=0.34, d=0.18
  → Convergence speed not significantly different
  → NOT PUBLISHABLE (but informative)
```

---

### Thursday: Replication & Validation

**Goal:** Ensure results are reproducible

Re-run Monday's experiments with fresh random seeds:
```bash
python osiris_cli.py run --campaign week1_foundation
```

**Why:** If results replicate, confidence is much higher.

Expected: Results should be **similar but not identical** (that's normal with stochastic processes).

If drastically different → Hardware variability or environmental change.

---

### Friday: Publishing & Documentation

**Step 1: Review all results**
```bash
ls -lah discoveries/
# Count .json files
find discoveries/ -name "*_*.json" | wc -l
```

**Step 2: Check publication eligibility (dry-run)**
```bash
python osiris_cli.py publish --dry-run
```

Output will show:
```
PUBLISHING WORKFLOW: day1_xeb_baseline_12q
✓ All publication criteria met
→ ELIGIBLE FOR ZENODO

PUBLISHING WORKFLOW: day3_shallow_vs_deep
✗ p-value 0.156 >= 0.05
→ NOT ELIGIBLE (but saved locally)
```

**Step 3: Publish eligible results**
```bash
python osiris_cli.py publish
```

This will:
1. Package all results
2. Upload to Zenodo
3. Generate DOIs
4. Create citation entries

Output:
```
✓ PUBLISHED SUCCESSFULLY
  Zenodo URL: https://zenodo.org/record/XXXX
  DOI: 10.5281/zenodo.XXXX
```

**Step 4: Save documentation**

Create a summary markdown:
```markdown
# Week-1 Campaign Summary

**Dates:** April 1-5, 2026

## Experiments Conducted: 6
- Foundation: 4 experiments
- Adaptive: 2 experiments

## Results Published: 5
- Significant: 5 results
- Parameters: 20-30 trials each, 4000 shots

## Key Findings

1. **XEB established baseline**
   - Measurement on ibm_torino consistently produces XEB > 0.1
   - p = 3.2e-05, Cohen's d = 0.54
   
2. **Entropy grows with depth**
   - Entropy increases from ~3.2 to ~4.8 as depth increases
   - p = 0.0012, Cohen's d = 0.61

3. **Adaptive circuits show promise**
   - RQC XEB > RCS XEB (p = 0.008)
   - Effect size: d = 0.72 (large effect)

## Published to Zenodo
- 5 datasets with DOIs
- All reproducible via job IDs
- Falsifiable hypotheses throughout

## Next Steps
- Independent replication by other groups
- Extend to larger qubit counts
- Investigate mechanism of adaptive improvement
```

---

## Phase 3: Publication Strategy

### Type A: Immediate Publication (Significant Results)

If you have:
- ✓ p < 0.05
- ✓ Cohen's d > 0.5
- ✓ Large sample (20+ trials)
- ✓ Falsifiable

→ **Publish immediately to Zenodo**

This creates a **searchable scientific record** with a DOI.

### Type B: Preprint + Peer Review (Major Claim)

If you have multiple significant results that together suggest new physics:

1. Write up as formal paper
2. Use LaTeX template from earlier
3. Submit to arXiv
4. Solicit peer review
5. Publish revised version

### Type C: Null Results (Still Publication-Worthy)

If you test a hypothesis and it FAILS:

Example null result:
```
Hypothesis: Resonance at 51.843° improves XEB
Result: p = 0.89, d = -0.02 (no effect)
```

→ **Still publish!** Null results prevent field from chasing dead ends.

Zenodo accepts null results. Other researchers will cite them.

---

## Phase 4: Advanced - Finding New Physics

Once you have the **foundation campaign established**, you can:

### Discovery Protocol

**Week 2-3: Novel Hypothesis Testing**

1. **Identify anomaly** from Week 1 data
   - Example: "XEB shows unexpected periodicity"
   - Examine raw data for patterns

2. **Formalize falsifiable hypothesis**
   - Example: "XEB oscillates with period τ = φ⁸ microseconds"
   - Null: "Period is random / no special structure"

3. **Design targeted experiment**
   ```json
   {
     "name": "test_tau_periodicity",
     "n_qubits": 12,
     "circuit_depth": 8,
     "shots": 8000,  // More data for finer detection
     "trials": 50,   // Repeats to detect periodicity
     "hypothesis": "XEB oscillates with period τ = φ⁸",
     "null_hypothesis": "No periodic structure in XEB"
   }
   ```

4. **Run & analyze**
   ```bash
   python osiris_cli.py run --experiment test_tau_periodicity --config config.json
   ```

5. **Apply Fourier/spectral analysis**
   ```python
   from scipy.fft import fft
   
   xeb_values = result.xeb_values
   frequencies = np.fft.fftfreq(len(xeb_values))
   power = np.abs(np.fft.fft(xeb_values))**2
   
   # Check if peak frequency matches φ⁸
   peak_freq = frequencies[np.argmax(power)]
   expected_freq = 1.0 / (1.618**8)  # φ⁸
   
   if abs(peak_freq - expected_freq) < threshold:
       print("✓ Anomaly detected!")
   ```

6. **Publish discovery**
   ```bash
   python osiris_cli.py publish
   ```

---

## Example: Complete 1-Week Timeline

```
MONDAY:
  09:00 - Setup + environment configuration
  11:00 - Run week1_foundation campaign
  14:00 - Check first results
  16:00 - Let experiments continue

TUESDAY-WEDNESDAY:
  Daily: Monitor progress, add new experiments
  Run adaptive campaign
  
THURSDAY:
  Replication runs
  Data analysis
  
FRIDAY:
  Final results review
  Dry-run publishing
  Actual publishing
  Documentation
  
WEEKEND:
  Write up findings
  Email to colleagues for replication
  Submit to preprint server
```

---

## Troubleshooting

### "No results after 1 hour"
Check if using real hardware or mock:
```bash
echo $IBM_QUANTUM_TOKEN
# If empty or "mock" → using simulation
```

Real hardware can have queue times 5-30 minutes per job.

### "Results show p > 0.05"
This is **not a failure**. It means:
- Your hypothesis wasn't supported
- But you've learned something
- Null result is still publishable
- Prevents field from false claims

### "Different results on second run"
**Expected!** Quantum is stochastic.

But if VERY different (3+ sigma), might indicate:
- Hardware calibration changed
- Node version changed
- Time of day (thermal effects)

Document these variations!

### "Zenodo won't connect"
1. Check token is correct
2. Check internet connection
3. Try sandbox first: `--sandbox`
4. For testing: `--dry-run --sandbox`

---

##  Key Metrics To Track

Track these for your campaign report:

| Metric | Target | Notes |
|--------|--------|-------|
| Experiments run | 6-10 | Week 1 foundation + adaptive |
| Results significant | 50%+ | Not all will pass |
| Replication rate | 80%+ | Second run agrees with first |
| Time to publish | < 5 days | Publication-ready results |
| Zenodo citations | TBD | Measure success later |

---

## Publishing Checklist

Before publishing to Zenodo:

- [ ] Results meet p < 0.05 OR are interesting null result
- [ ] Effect size calculated (Cohen's d)
- [ ] 95% confidence interval computed
- [ ] Hypothesis and null both stated
- [ ] Job IDs recorded (for verification)
- [ ] Falsification criteria clear
- [ ] README explains methodology
- [ ] Code is reproducible
- [ ] Dry-run test passed

---

## Expected Outcomes (1 Week)

### Conservative (Baseline Only)
- ✓ 4-6 experiments executed
- ✓ 2-3 significant results published
- ✓ Generated 2-3 Zenodo DOIs
- ✓ Methodology documented

### Realistic (Baseline + Adaptive)
- ✓ 8-10 experiments
- ✓ 5-6 significant results
- ✓ Discovered RQC vs RCS comparison
- ✓ Generated 5-6 Zenodo DOIs
- ✓ Ready for formal paper

### Ambitious (Foundation + Novel Discovery)
- ✓ 10+ experiments
- ✓ 6+ significant results
- ✓ Discovered anomaly (periodicity, pattern, etc.)
- ✓ Generated 8+ Zenodo DOIs
- ✓ New physics hypothesis formulated
- ✓ Ready for arXiv preprint

---

## Remember

**This system is designed for rigorous science:**

- ✅ Publish null results
- ✅ When p ≥ 0.05, say "not significant"
- ✅ Include all data, not just supporting evidence
- ✅ State limitations clearly
- ✅ Invite replication

**This is how science advances.**

Not through hype. Through honest, reproducible work.

---

**Ready to start?**

```bash
bash setup_osiris.sh
python osiris_cli.py run --campaign week1_foundation
```

**Good luck. Science awaits.**
