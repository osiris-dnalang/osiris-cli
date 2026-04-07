# OSIRIS Automated Discovery System

**Rigorous automated quantum research with statistical validation and falsification.**

Transform single-shot experiments into a continuous discovery pipeline that:
- ✅ Runs real quantum experiments on IBM Quantum hardware
- ✅ Applies peer-review-grade statistical validation
- ✅ Only publishes results that meet publication thresholds
- ✅ Publishes null results transparently
- ✅ Auto-publishes to Zenodo with full provenance
- ✅ Supports independent replication

**Timeline:** Start to publication-ready in **1 week**.

---

## Quick Start

### 1. **Set Environment Variables**

```bash
# IBM Quantum API token
export IBM_QUANTUM_TOKEN="your_token_here"

# Zenodo token (for publishing)
export ZENODO_TOKEN="your_zenodo_token"

# Optional: backend selection
export IBM_BACKEND="ibm_torino"  # or ibm_fez, ibm_nazca, etc.
```

### 2. **Install Dependencies**

```bash
pip install qiskit qiskit-ibm-runtime numpy scipy matplotlib
```

### 3. **Run Week-1 Campaign**

```bash
# See what will run
python osiris_cli.py list

# Execute foundation experiments (XEB, entropy, noise)
python osiris_cli.py run --campaign week1_foundation

# Check results
python osiris_cli.py status

# Publish to Zenodo (dry-run first!)
python osiris_cli.py publish --dry-run
python osiris_cli.py publish
```

---

## System Components

### `osiris_auto_discovery.py`
**Core execution engine** - Handles:
- Random quantum circuit generation
- IBM Quantum hardware execution
- Statistical validation (t-tests, effect sizes, confidence intervals)
- XEB computation
- Result packaging

**Key Class:** `AutoDiscoveryPipeline`

```python
pipeline = AutoDiscoveryPipeline(api_token="...")
config = ExperimentConfig(
    name="xeb_baseline",
    hypothesis="Random circuits produce measurable XEB",
    null_hypothesis="XEB is indistinguishable from noise",
    n_qubits=12,
    circuit_depth=8,
    trials=20,
)
result = pipeline.run_hypothesis_test(config)
```

---

### `osiris_orchestrator.py`
**Workflow management** - Manages:
- Experiment campaigns (related experiments)
- Week-1 timeline breakdown
- Experiment templates for reproducibility
- Automated publishing decisions

**Key Classes:**
- `ExperimentCampaign` - Group related experiments
- `WorkflowScheduler` - Execute campaigns
- `ExperimentTemplates` - Standard protocols

```python
campaign = ExperimentCampaign(
    "week1_foundation",
    "Establish XEB baseline and validation"
)
campaign.add_experiment(template_dict)
campaign.run_all(pipeline)
logger.info(campaign.summary())
```

---

### `osiris_zenodo_publisher.py`
**Publishing automation** - Handles:
- Zenodo API integration
- Automatic publication decisions (p < 0.05, |d| > 0.5)
- Result packaging with provenance
- DOI generation

**Key Classes:**
- `ZenodoPublisher` - API client
- `AutoPublishDecision` - Publication criteria
- `PublishingWorkflow` - Complete workflow

```python
workflow = PublishingWorkflow(zenodo_token)
workflow.publish_result(result, report_md, dry_run=False)
```

---

### `osiris_cli.py`
**Command-line interface**

```bash
# Run experiments
python osiris_cli.py run --campaign week1_foundation

# See available templates
python osiris_cli.py list

# Check status
python osiris_cli.py status

# Publish results
python osiris_cli.py publish --dry-run
```

---

## Publication Criteria (RIGOROUS)

Results are **ONLY published** when:

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| p-value | < 0.05 | Standard statistical significance |
| Effect size (Cohen's d) | ≥ 0.5 | Medium effect minimum |
| Falsifiable | Yes | Must state null hypothesis |
| CI excludes zero | Yes | Confidence interval doesn't cross zero |
| Minimum trials | ≥ 10 | Adequate sample size |

**If ANY criterion fails:** Result is NOT published (but is saved)

---

## Week-1 Campaign Structure

### Day 1-2: **Foundation**
```python
campaign_week1_foundation()  # XEB baseline, entropy, noise robustness
```

Experiments:
- `day1_xeb_baseline_12q` - Establish XEB on 12 qubits
- `day2_entropy_growth` - Entropy vs depth relationship  
- `day3_shallow_vs_deep` - Noise robustness validation
- `day4_backend_consistency` - Cross-backend validation

### Day 3-5: **Adaptive Hypothesis**
```python
campaign_week1_adaptive()  # RQC vs RCS comparison
```

Experiments:
- `adaptive_xeb_improvement` - RQC better than RCS?
- `adaptive_convergence_rate` - RQC converges faster?

---

## Result Package Contents

When a result is saved/published, you get:

```
package_<result_id>/
├── result_<id>.json          # Raw data (counts, metrics, stats)
├── report_<id>.md            # Markdown report
├── metadata.json             # Experiment metadata
└── zenodo_record.json        # Publishing record (if published)
```

**Example:** `discoveries/package_a1b2c3d4/`

---

## Custom Experiments

Create your own experiment config (JSON):

```json
{
  "name": "my_custom_experiment",
  "n_qubits": 14,
  "circuit_depth": 10,
  "shots": 5000,
  "trials": 25,
  "hypothesis": "My specific hypothesis here",
  "null_hypothesis": "The null hypothesis",
  "predicted_outcome": "What I expect to see"
}
```

Run it:
```bash
python osiris_cli.py run --experiment my_custom --config my_config.json
```

---

## Interpreting Results

### ✓ Significant Result (Published)
```
p-value: 2.1e-06 ✓
Cohen's d: 0.87 ✓  
CI: [0.23, 0.61] ✓ (excludes zero)
→ PUBLISHED to Zenodo
```

### ✗ Null Result (Saved, Not Published)
```
p-value: 0.187 ✗
Cohen's d: 0.32 ✗
CI: [-0.05, 0.42] ✗ (crosses zero)
→ Saved locally, not published
→ Still scientifically valuable!
```

---

## Transparency & Reproducibility

Every result includes:

1. **Hardware ID** - IBM Quantum job IDs
2. **Experiment Config** - Exact parameters
3. **Raw Data** - All measurement counts
4. **Statistical Analysis** - p, d, CI, BF
5. **Falsification Criteria** - What would disprove this?
6. **Timestamp & Hardware** - Exactly when/where

**Anyone can:**
- Download from Zenodo
- Replicate independently
- Challenge results
- Propose improvements

---

## Important Notes

### What This Is
✅ Rigorous automated experimental validation
✅ Honest statistical testing
✅ Supports replication
✅ Publishes null results
✅ Grounded in real hardware

### What This Is NOT
❌ Auto-generating theories
❌ Publishing without validation
❌ Avoiding null results
❌ Making extraordinary claims without extraordinary evidence
❌ Overselling preliminary results

---

## Troubleshooting

### "IBM_QUANTUM_TOKEN not set"
```bash
export IBM_QUANTUM_TOKEN="your_token"
# Get token at: https://quantum.ibm.com/
```

### "Connection failed"
Uses mock execution. Results will be synthetic data.
Good for testing! But real hardware is needed for claims.

### "Results not publishing"
Check publication criteria with `--dry-run`:
```bash
python osiris_cli.py publish --dry-run
```

All criteria must pass. This is intentional.

---

## Next Steps

1. **Setup:** Set environment variables and install deps
2. **Baseline:** Run `week1_foundation` campaign  
3. **Review:** Check results with `status`
4. **Validate:** Run again to check reproducibility
5. **Publish:** Use `publish --dry-run` then `publish`
6. **Replicate:** Share for independent confirmation

---

## Contact & Contributing

Questions about methodology? Issues with execution?

The system is designed for **honest science**. All feedback welcome.

---

**Version:** 1.0  
**Status:** Production-ready for NISQ experiments  
**Last Updated:** April 2026
