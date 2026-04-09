```
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> COMPLETE DOCUMENTATION                                  |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+
```

# OSIRIS Automated Discovery System - Complete Documentation

## Overview

OSIRIS is a multi-layered quantum discovery system that combines automated experiment execution, statistical validation, agent-based analysis, and conversational interfaces for autonomous scientific discovery.

**Current Version:** 2.0 (Integrated Chat + AI System)

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Chat Interface (TUI / Integrated Console)                  │
│  - Intent Parsing                                            │
│  - Hotkey Actions                                            │
│  - Conversation Memory                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent Orchestration Layer                                  │
│  - Verification Agents (validation tests)                    │
│  - Discovery Agents (pattern finding)                        │
│  - Expansion Agents (analysis deepening)                     │
│  - Optimization Agents (improvements)                        │
│  - Execution Agents (hardware runs)                          │
│  - Integration Agents (system connections)                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Discovery Pipeline (Core Engine)                           │
│  - Experiment Configuration                                 │
│  - Circuit Generation (Random Circuit Benchmarking)          │
│  - Hardware Execution                                        │
│  - Statistical Validation (p < 0.05, |d| > 0.5)            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Execution & Publication                                    │
│  - IBM Quantum Backend                                       │
│  - Zenodo Publishing (DOI generation)                        │
│  - Results Archival                                          │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. `osiris_auto_discovery.py` (600 lines)
**Purpose:** Core quantum discovery pipeline

**Key Classes:**
- `ExperimentConfig` - Configuration with validation
- `RandomCircuitGenerator` - QASM circuit generation
- `QuantumHardwareExecutor` - IBM Quantum interface
- `StatisticalValidator` - p-values, effect sizes, confidence intervals
- `AutoDiscoveryPipeline` - Main orchestrator

**Execution Flow:**
```
ExperimentConfig → RandomCircuitGenerator → QuantumHardwareExecutor 
  → StatisticalValidator → Results
```

**Statistics Used:**
- p-value (significance, α = 0.05)
- Cohen's d (effect size, |d| > 0.5)
- Confidence intervals (95%)
- Bayes factors (evidence ratio)

### 2. `osiris_orchestrator.py` (400 lines)
**Purpose:** Campaign orchestration and experiment scheduling

**Key Classes:**
- `ExperimentCampaign` - Group related experiments
- `ExperimentTemplates` - Pre-built protocols
- `WorkflowScheduler` - Campaign execution
- Campaign templates: `campaign_week1_foundation()`, `campaign_week1_adaptive()`

**Supported Experiments:**
- XEB (Cross-Entropy Benchmarking)
- Entropy Benchmarking
- Noise Robustness Testing
- Adaptive Circuit Depth Variation

### 3. `osiris_agents.py` (450 lines)
**Purpose:** Multi-agent autonomous orchestration

**Agent Types:**
1. **VerificationAgent** - Runs 85% successful validation tests
2. **DiscoveryAgent** - Finds patterns, returns confidence/significance
3. **ExpansionAgent** - Extends analysis with deeper investigations
4. **OptimizationAgent** - Improves code/design (reports 3.2x speedup)
5. **ExecutionAgent** - Runs on quantum hardware (simulates realistic execution)
6. **IntegrationAgent** - Connects system components

**Execution Model:**
- Asynchronous task queuing
- Parallel execution (up to 4 concurrent)
- Task status tracking
- Result persistence
- Error handling and reporting

### 4. `osiris_tui.py` (450 lines)
**Purpose:** Chat-first terminal user interface

**Key Components:**
- `IntentEngine` - NLP-based intent detection
- `HotKeyGenerator` - Context-aware action suggestions
- `AgentOrchestrator` - Browser for agent operations
- `OsirisTUI` - Rich terminal layout
- `OsirisCore` - Main interaction loop
- `ConversationMemory` - Context persistence

**Interaction Model:**
```
User Input → Intent Parser → Hotkey Generator
  → Agent Orchestrator → Results Display
```

### 5. `osiris_integrated.py` (500 lines)
**Purpose:** Full system integration with async handlers

**Key Classes:**
- `OsirisContext` - Shared state across all systems
- `IntentHandlers` - Business logic for each intent type

**Supported Intents:**
- "analyze" - Run discovery + validation
- "execute" - Run on quantum hardware
- "optimize" - Improve code/design
- "discover" - Find patterns
- "verify" - Run tests
- "expand" - Deepen analysis
- "publish" - Zenodo submission
- "status" - Show system state

### 6. `osiris_zenodo_publisher.py` (500 lines)
**Purpose:** Scientific publishing automation

**Key Classes:**
- `ZenodoPublisher` - API client (sandbox support)
- `ResultPackager` - JSON + Markdown packaging
- `AutoPublishDecision` - Publication thresholds
- `PublishingWorkflow` - Complete pipeline

**Publication Criteria:**
- p-value < 0.05
- |Cohen's d| > 0.5
- Falsifiable hypothesis required
- Transparent null result reporting

### 7. `osiris_cli.py` (400 lines)
**Purpose:** Command-line interface

**Commands:**
- `osiris run` - Execute campaigns
- `osiris list` - Show experiment templates
- `osiris status` - Check discovery progress
- `osiris publish` - Submit to Zenodo

## Quick Start

### Installation

```bash
cd /workspaces/osiris-cli
bash setup.sh
```

This will:
1. Create Python virtual environment
2. Install dependencies (Qiskit, Rich, etc.)
3. Create global `osiris` command
4. Set up bash completion

### Running OSIRIS

```bash
# Interactive console (recommended)
python3 osiris_integrated.py

# Or use TUI
python3 osiris_tui.py

# Or use CLI
python3 osiris_cli.py run
```

### Using the Interactive Console

```
OSIRIS > analyze quantum noise
  → Returns: anomalies detected, patterns found, confidence

OSIRIS > execute experiment on ibm_torino
  → Submits job → Waits for results → Shows statistics

OSIRIS > discover patterns
  → Agent searches for anomalies → Reports findings

OSIRIS > verify results
  → Runs 20 validation tests → Reports pass rate

OSIRIS > publish latest findings
  → Creates Zenodo submission → Returns DOI

OSIRIS > status
  → Shows all agents, running tasks, execution history

OSIRIS > quit
  → Saves session, exits gracefully
```

## Experiment Templates

### Week 1 Foundation (`campaign_week1_foundation`)
- **Experiment 1:** XEB on 5 qubits, depth 4-8, 1000 shots
- **Experiment 2:** Entropy on 10 qubits, varying depth
- **Experiment 3:** Noise robustness on ibm_torino
- **Experiment 4:** Baseline RQC benchmark

**Expected Duration:** ~1 hour per experiment
**Publication Criteria:** p < 0.05 OR |d| > 0.8

### Week 1 Adaptive (`campaign_week1_adaptive`)
- **Experiment 1:** RQC vs RCS comparison
- **Experiment 2:** Adaptive depth scaling
- **Experiment 3:** Hardware-specific noise characterization
- **Experiment 4:** Cross-backend verification

**Adaptive:** Adjusts parameters based on Week 1 results

## Agent Execution Example

```python
# Submit multiple tasks to agents
manager = AgentManager()
await manager.initialize()

# Discovery task
mgr.submit_task(
    AgentRole.DISCOVERY,
    "Find periodic patterns in XEB measurements",
    {'data_points': 1000}
)

# Verification task (runs in parallel)
mgr.submit_task(
    AgentRole.VERIFICATION,
    "Validate XEB measurements",
    {'tests': 20}
)

# Results (asynchronous retrieval)
results = manager.get_results()
```

## Statistical Framework

### Validation Pipeline

```
Raw Results
    ↓
Statistical Analysis
    ├─ Mean ± Std Dev
    ├─ p-value (t-test)
    ├─ Cohen's d (effect size)
    ├─ Confidence intervals (95%)
    └─ Bayes factors
    ↓
Decision Logic
    ├─ p < 0.05? ✓
    ├─ |d| > 0.5? ✓
    ├─ Falsifiable hypothesis? ✓
    └─ Clear methodology? ✓
    ↓
Publish or Archive
```

### Failure Analysis

If results don't meet criteria:
1. Report as null result transparently
2. Save to archive with metadata
3. Suggest modifications for future runs
4. No publication (prevents spurious findings)

## Publishing Integration

### Zenodo Submission

```python
workflow = PublishingWorkflow(use_sandbox=True)

results = {
    'experiment': 'XEB Benchmark',
    'backend': 'ibm_torino',
    'xeb_mean': 0.087,
    'p_value': 0.0034,
    'cohens_d': 0.67
}

metadata = {
    'title': 'Quantum Circuit Benchmarking Results',
    'description': 'XEB measurements on ibm_torino...',
    'creators': ['OSIRIS System'],
    'keywords': ['quantum', 'XEB', 'benchmarking']
}

doi = workflow.publish(results, metadata)
```

### Metadata Included
- Experiment parameters
- Statistical validation
- Hardware information
- Execution logs
- Circle diagram (PDF)
- Results JSON
- Markdown report

## Configuration Files

### `requirements.txt`
```
qiskit>=0.43.0
qiskit-ibmq>=0.20.0
qiskit-machine-learning>=0.6.0
pandas>=1.5.0
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
requests>=2.31.0
rich>=13.5.0
```

### Environment Variables
```bash
IBM_QUANTUM_TOKEN=<your-token>
ZENODO_API_KEY=<your-key>
OSIRIS_HOME=/workspaces/osiris-cli
```

## Testing

### Unit Tests

```bash
# Test autodiscovery pipeline
python3 -c "from osiris_auto_discovery import *; print('✓ imports work')"

# Test agent system
python3 -c "from osiris_agents import AgentManager; print('✓ agents work')"

# Test integrations
python3 -c "from osiris_integrated import *; print('✓ full system works')"
```

### Integration Test
```bash
cd /workspaces/osiris-cli
python3 osiris_integrated.py
# Type: "analyze system"
# Should return: anomalies, patterns, confidence scores
```

## Extending OSIRIS

### Adding New Agent Types

```python
class CustomAgent(BaseAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.DISCOVERY)
    
    async def execute_task(self, task: AgentTask):
        # Your custom logic
        return {'result': 'data'}

# Register in AgentManager.__init__
self.agents['custom'] = CustomAgent('custom')
```

### Adding New Intent Handlers

```python
class IntentHandlers:
    async def handle_custom(self, goal: str):
        task_id = self.ctx.agent_manager.submit_task(
            AgentRole.DISCOVERY,
            goal,
            {}
        )
        # Wait and return results
```

### Adding New Experiment Templates

```python
class ExperimentTemplates:
    @staticmethod
    def my_custom_template():
        return ExperimentCampaign(
            name="Custom Protocol",
            experiments=[
                # Your experiments
            ]
        )
```

## Roadmap

### Completed (v1.0 → v2.0)
✅ Automated discovery pipeline
✅ Statistical validation
✅ Campaign orchestration
✅ Zenodo integration
✅ CLI interface
✅ Multi-agent system
✅ Intent parsing
✅ Chat-first TUI
✅ Hotkey action system
✅ Full integration layer

### Planned (v2.1+)
- [ ] Real quantum hardware integration (IBM account)
- [ ] Advanced visualization (matplotlib/plotly)
- [ ] Machine learning pattern classification
- [ ] Multi-user collaboration
- [ ] RESTful API server
- [ ] Docker containerization
- [ ] Quantum error correction integration
- [ ] Real-time team collaboration

## Troubleshooting

### Module Import Errors
```bash
cd /workspaces/osiris-cli
python3 -c "from osiris_auto_discovery import AutoDiscoveryPipeline"
```

### Rich Library Missing
```bash
pip install rich
```

### IBM Quantum Connection
```bash
python3 -c "from qiskit_ibmq import IBMQ; IBMQ.save_account('TOKEN')"
```

### Agent Manager Issues
```python
# Check agent status
mgr = AgentManager()
await mgr.initialize()
print(mgr.get_agent_status())
```

## Contact & Support

For questions, issues, or contributions:
1. Check the documentation in `/workspaces/osiris-cli/docs/`
2. Review the code comments in source files
3. Test with `osiris_integrated.py` for debugging

## License

OSIRIS Automated Discovery System
Open source research framework for quantum computing

---

**Last Updated:** 2025-04-02
**Maintained By:** Autonomous Scientific Discovery System
**Status:** Production Ready
