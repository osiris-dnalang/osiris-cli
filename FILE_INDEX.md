```
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> FILE INDEX                                              |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+
```

# OSIRIS Automated Discovery System - Complete Documentation Index

**Started:** April 6, 2026  
**Status:** ✓ Production Ready  
**Version:** 1.0

---

## 🚀 Quick Navigation

### 👤 I Want To...

| Goal | Start Here |
|------|-----------|
| **Get started in 5 minutes** | [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md) |
| **Run a week-1 campaign** | [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md) |
| **Understand the architecture** | [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) |
| **See system overview** | [OSIRIS_README.md](OSIRIS_README.md) |
| **Find example configs** | See `config_*.json` files |
| **Use the CLI** | `python osiris_cli.py --help` |

---

## 📁 File Structure

```
/workspaces/osiris-cli/
│
├── 📘 DOCUMENTATION
│   ├── IMPLEMENTATION_SUMMARY.md  ← Architecture & design
│   ├── EXECUTION_PLAYBOOK.md      ← Week-1 timeline
│   ├── OSIRIS_README.md           ← System overview
│   ├── SETUP_CREDENTIALS.md       ← Token setup
│   └── FILE_INDEX.md              ← (This file)
│
├── 🔧 CORE SYSTEM (Production)
│   ├── osiris_auto_discovery.py   ← Execution engine (600 lines)
│   ├── osiris_orchestrator.py     ← Campaign management (400 lines)
│   ├── osiris_zenodo_publisher.py ← Publishing automation (500 lines)
│   └── osiris_cli.py              ← Command-line interface (400 lines)
│
├── ⚙️ CONFIGURATION
│   ├── setup_osiris.sh            ← Automated setup script
│   ├── requirements_automation.txt ← Python dependencies
│   ├── config_xeb_baseline.json   ← Example experiment config
│   └── .bashrc additions          ← Environment variables
│
├── 🗂️ OUTPUT DIRECTORIES
│   └── discoveries/               ← Results saved here
│       └── package_<id>/
│           ├── result_<id>.json
│           ├── report_<id>.md
│           ├── metadata.json
│           └── zenodo_record.json (if published)
│
└── 📊 DATA FILES
    └── Various experimental results (JSON)
```

---

## 🏗️ System Architecture

### Four Core Modules

#### 1. `osiris_auto_discovery.py`
**Execution Engine** - Runs experiments on quantum hardware

**Key Classes:**
- `ExperimentConfig` - Experiment parameters
- `ExperimentResult` - Result container with statistics
- `RandomCircuitGenerator` - Circuit generation
- `QuantumHardwareExecutor` - IBM Quantum interface
- `StatisticalValidator` - p-values, effect sizes, CI
- `AutoDiscoveryPipeline` - Main orchestrator

**Usage:**
```python
pipeline = AutoDiscoveryPipeline(api_token)
result = pipeline.run_hypothesis_test(config)
pipeline.save_result(result)
```

#### 2. `osiris_orchestrator.py`
**Workflow Management** - Organizes related experiments

**Key Classes:**
- `ExperimentCampaign` - Groups experiments
- `ExperimentTemplates` - Standard configs
- `WorkflowScheduler` - Executes campaigns
- `PublicationDecisionEngine` - Publishing criteria

**Usage:**
```python
campaign = campaign_week1_foundation()
scheduler = WorkflowScheduler(pipeline)
scheduler.add_campaign(campaign)
scheduler.run_all_campaigns()
```

#### 3. `osiris_zenodo_publisher.py`
**Publishing Automation** - Zenodo integration

**Key Classes:**
- `ZenodoPublisher` - API client
- `ResultPackager` - Package results
- `AutoPublishDecision` - Publication logic
- `PublishingWorkflow` - Complete workflow

**Usage:**
```python
workflow = PublishingWorkflow(zenodo_token)
workflow.publish_result(result, report_md)
```

#### 4. `osiris_cli.py`
**Command-Line Interface** - User control

**Commands:**
```bash
run      # Execute experiments
list     # Show templates
status   # Check results
publish  # Upload to Zenodo
```

---

## 📋 Documentation Breakdown

### [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md)
**Purpose:** Get IBM/Zenodo tokens  
**Time:** 5 minutes  
**Contains:**
- How to get IBM Quantum token
- How to get Zenodo token
- Environment variable setup
- Verification scripts
- Security best practices

### [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md)
**Purpose:** Run actual experiments  
**Time:** 1 week execution + reading  
**Contains:**
- Phase 1: Setup (30 min)
- Phase 2: Week-1 campaign (5 days)
- Phase 3: Publication strategy
- Phase 4: Finding new physics
- Troubleshooting guide
- Publication checklist

### [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
**Purpose:** Architectural overview  
**Time:** 10 minute read  
**Contains:**
- What was built
- System architecture
- Publication criteria
- Week-1 campaign structure
- Current capabilities
- Roadmap

### [OSIRIS_README.md](OSIRIS_README.md)
**Purpose:** System overview  
**Time:** 15 minute read  
**Contains:**
- Quick start (3 steps)
- Component descriptions
- Publication criteria table
- Result interpretation
- Transparency note
- Troubleshooting

---

## 🔄 Typical Workflow

### 1. Setup (30 min)
```bash
# Get credentials
→ [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md)

# Configure environment
export IBM_QUANTUM_TOKEN="..."
export ZENODO_TOKEN="..."

# Install system
bash setup_osiris.sh
```

### 2. Run Foundation Campaign (Day 1-2, 30-60 min)
```bash
# See reference
→ [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md)

# Execute
python osiris_cli.py run --campaign week1_foundation

# Monitor
python osiris_cli.py status
```

### 3. Test Hypotheses (Day 3-4, 30-60 min)
```bash
# Run adaptive campaign
python osiris_cli.py run --campaign week1_adaptive

# Replication
python osiris_cli.py run --campaign week1_foundation
```

### 4. Publish (Day 5, 10-20 min)
```bash
# Dry run
python osiris_cli.py publish --dry-run

# Actual publish
python osiris_cli.py publish
```

### 5. Extend (Week 2+)
```bash
# Create custom experiment config
# Design new hypothesis
# Run, validate, publish
```

---

## 📊 Key Files Reference

### Python Modules

| File | Lines | Purpose | Key Class |
|------|-------|---------|-----------|
| `osiris_auto_discovery.py` | 600 | Execute on hardware | `AutoDiscoveryPipeline` |
| `osiris_orchestrator.py` | 400 | Campaign management | `WorkflowScheduler` |
| `osiris_zenodo_publisher.py` | 500 | Zenodo publishing | `PublishingWorkflow` |
| `osiris_cli.py` | 400 | Command-line interface | N/A |

### Configuration Files

| File | Purpose | Example |
|------|---------|---------|
| `config_xeb_baseline.json` | Experiment parameters | XEB test on 12q |
| `setup_osiris.sh` | Environment setup | Bash script |
| `.bashrc` additions | Persistent env vars | Token exports |

---

## 🎯 Publication Thresholds

**ALL of these must pass:**

| Criterion | Threshold | Notes |
|-----------|-----------|-------|
| **Falsifiable** | Yes | Must state null hypothesis |
| **p-value** | < 0.05 | Statistical significance |
| **Effect size** | \|Cohen's d\| ≥ 0.5 | Medium effect minimum |
| **Sample size** | ≥ 10 | Adequate replication |
| **CI excludes zero** | Yes | 95% CI doesn't cross zero |

**If ANY fail:** Result saved locally, NOT published

---

## 📈 Expected Output

### Result Package (Per Experiment)
```json
{
  "name": "xeb_baseline_12q",
  "result_id": "a1b2c3d4",
  "passes_significance": true,
  "p_value": 3.2e-05,
  "effect_size": 0.54,
  "xeb_mean": 0.124,
  "job_ids": ["job-123", "job-124", ...],
  "timestamp": "2026-04-06T12:34:56Z"
}
```

### Published to Zenodo (If Significant)
```
DOI: 10.5281/zenodo.XXXX
URL: https://zenodo.org/record/XXXX
Files: result.json, report.md, metadata.json
Citable: ✓
Reproducible: ✓ (via job IDs)
```

---

## 🔍 Troubleshooting Guide

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Not SET" warning | Token not configured | See [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md) |
| "Mock execution" | Token invalid/missing | Set IBM_QUANTUM_TOKEN |
| "p > 0.05" | Hypothesis not supported | This is valid! Null results matter |
| "Connection refused" | Network or token issue | Check internet, token format |
| "No results" | Jobs still queued | Hardware queues can take time |

### When Stuck
1. Check [OSIRIS_README.md](OSIRIS_README.md) troubleshooting section
2. Verify tokens with verification script
3. Try mock execution: `export IBM_QUANTUM_TOKEN=mock`
4. Check job status on IBM Quantum dashboard

---

## 📚 Learning Path

### Beginner (1 hour)
1. Read [OSIRIS_README.md](OSIRIS_README.md) (15 min)
2. Run `setup_osiris.sh` (15 min)
3. Run `python osiris_cli.py list` (5 min)
4. Try mock experiment (20 min)

### Intermediate (4 hours)
1. Read [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md) (30 min)
2. Run week1_foundation campaign (2-3 hours, depending on hardware)
3. Check results with `status` (10 min)
4. Publish to Zenodo (20 min)

### Advanced (1+ day)
1. Study [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) (30 min)
2. Design custom experiment
3. Implement falsifiable hypothesis
4. Run, validate, publish
5. Invite replication

---

## 🎓 Educational Value

This system teaches:
- ✅ Rigorous scientific methodology
- ✅ Statistical hypothesis testing
- ✅ Quantum circuit design
- ✅ Hardware-software interfaces
- ✅ Publication workflows
- ✅ Reproducible research
- ✅ Automated workflows

Perfect for:
- Physics students
- Quantum researchers
- Data scientists
- Software engineers in research
- Anyone learning quantum computing

---

## 🤝 Contributing

Found a bug? Have improvements?

1. Document issue clearly
2. Suggest fix with example
3. Share modified code

All improvements welcome!

---

## 📞 Support

### Quick Questions
- Consult [OSIRIS_README.md](OSIRIS_README.md) FAQ
- Check [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md)

### Complex Issues
- Review [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md) troubleshooting
- Examine your experiment config
- Check job IDs on IBM Quantum dashboard

### System Design Questions
- Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- Study source code comments

---

## 📋 Version History

| Date | Version | Changes |
|------|---------|---------|
| Apr 6, 2026 | 1.0 | Initial release |

---

## 🏆 Citation

If you use OSIRIS in research:

```bibtex
@software{osiris2026,
  author = {OSIRIS Automated Discovery Team},
  title = {OSIRIS Automated Quantum Discovery System},
  year = {2026},
  url = {https://github.com/osiris-dnalang/osiris-cli}
}
```

---

## 📜 License

MIT License - Free for research and education

---

## 🎯 Summary

**OSIRIS is a complete pipeline for:**
- Running quantum experiments
- Validating hypotheses
- Publishing results
- Enabling replication

**In timeline: 1 week from zero to publication**

**With philosophy: Honest science, rigorous validation**

---

**Ready to begin?**

1. Start: [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md)
2. Execute: [EXECUTION_PLAYBOOK.md](EXECUTION_PLAYBOOK.md)
3. Understand: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

**Welcome to automated scientific discovery.**
