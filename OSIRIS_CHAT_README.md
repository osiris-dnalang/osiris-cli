# OSIRIS Chat-Native TUI System

## Overview

OSIRIS has been transformed from a CLI tool into a **chat-native, intent-driven quantum research platform** with autonomous agent orchestration and real-time benchmarking capabilities.

## What's New

### 1. **Chat-First Interface**
- Natural language commands (no CLI syntax required)
- Intent engine that automatically detects what you want to do
- Real-time response generation
- Conversation history tracking

### 2. **Intent Engine** 
`osiris_intent_engine.py` - Autonomous intent detection:
- **Benchmark** - Test hardware capabilities
- **Experiment** - Run hypothesis tests
- **Deploy** - Publish results to Zenodo
- **Analyze** - Interpret results
- **Refine** - Optimize circuits
- **Status** - Check system health

### 3. **Quantum Hardware Benchmarker**
`osiris_quantum_benchmarker.py` - Extreme-mode benchmarking:
- Tests all available backends (ibm_torino, ibm_fez, ibm_nazca, ibm_brisbane)
- Progressive qubit scaling (4 → 64 qubits)
- Multiple shot depths (1K → 65K shots)
- Circuit depths up to 64 layers
- Generates performance reports with XEB scores

### 4. **Unified Launcher**
`osiris_launcher.py` - Single entry point for all operations:
```bash
osiris chat              # Launch chat interface
osiris benchmark         # Run full benchmark suite
osiris benchmark --quick # Quick mode (4 tests)
osiris run --campaign week1_foundation
osiris status
osiris help
```

## Quick Start

### 1. Set Your API Tokens

```bash
# IBM Quantum (real hardware access)
export IBM_QUANTUM_TOKEN='your_ibm_token_here'

# Zenodo (publishing results)
export ZENODO_TOKEN='your_zenodo_token_here'
```

Get tokens:
- **IBM Quantum**: https://quantum.ibm.com/settings/tokens
- **Zenodo**: https://zenodo.org/account/settings/applications/tokens/new/

### 2. Launch OSIRIS

```bash
# Start chat interface
python3 osiris_launcher.py chat

# OR use the shell wrapper
./osiris chat
```

### 3. Chat with OSIRIS

Just type natural language. Examples:

```
❯ You: benchmark ibm_torino with extreme parameters
⚛ Osiris: ⚛ Starting quantum hardware benchmarking...
📊 Testing extreme shot/depth parameters

✓ Benchmark complete!
ibm_torino: Best XEB=0.8976, Fidelity=0.9019
...

❯ You: show status
⚛ Osiris: 📊 System Status:

Chat messages: 42
IBM Quantum: ✓ Connected
Zenodo: ✓ Ready
Benchmarker: ✓ Ready

❯ You: run xeb experiment with 50 trials
⚛ Osiris: ⚛ Configuring experiment...
✓ Experiment complete!
p-value: 0.0003
Effect size: 0.87
```

## System Architecture

### Module Breakdown

| Module | Purpose | Lines |
|--------|---------|-------|
| `osiris_intent_engine.py` | Intent detection (NLP-free) | 380 |
| `osiris_quantum_benchmarker.py` | Hardware benchmarking | 520 |
| `osiris_tui_core.py` | Chat interface & orchestration | 480 |
| `osiris_launcher.py` | Unified command entry point | 320 |
| `osiris_auto_discovery.py` | Experiment pipeline (existing) | 600 |
| `osiris_orchestrator.py` | Campaign management (existing) | 400 |
| `osiris_zenodo_publisher.py` | DOI publishing (existing) | 500 |

### Intent Detection Flow

```
User Input (natural language)
         ↓
Intent Engine (pattern matching)
         ↓
Intent Classification (benchmark/experiment/deploy/etc)
         ↓
Parameter Extraction (qubits, shots, depth, trials)
         ↓
Agent Selection (benchmarker_agent, executor_agent, publisher_agent)
         ↓
Action Execution (hardware call, file write, API post)
```

## Command Reference

### Chat Interface

Simply launch with:
```bash
python3 osiris_launcher.py chat
# or
./osiris chat
```

Common natural language patterns:

**Benchmarking:**
- "benchmark ibm_torino with extreme parameters"
- "test all backends for comparison"
- "32 qubit deep circuit test"

**Experiments:**
- "run xeb experiment"
- "execute entropy saturation test"
- "test with 16 qubits at depth 32"

**Deployment:**
- "deploy to zenodo with DOI"
- "publish results"

**Status:**
- "show status"
- "what's running"
- "results so far"

### CLI Commands

```bash
# Quick benchmark
python3 osiris_launcher.py benchmark --quick

# Full extreme benchmark
python3 osiris_launcher.py benchmark

# Run week 1 foundation experiments
python3 osiris_launcher.py run --campaign week1_foundation

# Run adaptive experiments
python3 osiris_launcher.py run --campaign week1_adaptive

# Check system status
python3 osiris_launcher.py status

# Show help
python3 osiris_launcher.py help
```

## With Your Tokens

Once you've set `IBM_QUANTUM_TOKEN` and `ZENODO_TOKEN`:

### Real Hardware Execution
The benchmarker will:
1. Connect to your IBM Quantum account
2. Submit jobs to available backends
3. Retrieve real fidelity/XEB measurements
4. Generate actual performance metrics

### Result Publishing
The publisher will:
1. Validate statistical significance (p < 0.05)
2. Package results with metadata
3. Upload to Zenodo
4. Generate citation with DOI
5. Create shareable link

## Example Workflow

```bash
# 1. Set tokens
export IBM_QUANTUM_TOKEN='your_token'
export ZENODO_TOKEN='your_zenodo_token'

# 2. Start chat
python3 osiris_launcher.py chat

# 3. Benchmark all backends
> benchmark all backends with extreme parameters

# 4. Check results
> show status

# 5. Deploy findings
> deploy results to zenodo

# System automatically:
# ✓ Tests all 4 backends (156 qubits each on ibm_torino/fez/nazca)
# ✓ Progressive scaling from 4→64 qubits
# ✓ Extreme shots (1K-65K)  
# ✓ Extreme depths (4-64 layers)
# ✓ Generates performance report with XEB scores
# ✓ Publishes with DOI to Zenodo
# ✓ Creates shareable citation
```

## Features

### Intent Engine (No External LLM)
- ✓ Pattern-matching based classification
- ✓ Parameter extraction from text
- ✓ Confidence scoring (0-1.0)
- ✓ Suggested action generation
- ✓ Agent selection logic
- ✓ Conversation history tracking

### Quantum Benchmarker
- ✓ 4 IBM backends supported
- ✓ Max qubits: 156 (ibm_torino, ibm_fez, ibm_nazca), 127 (ibm_brisbane)
- ✓ Max shots: 65,536 (IBM open quantum plan limit)
- ✓ Circuit depths: 4, 8, 16, 32, 64 layers
- ✓ Progressive qubit scaling
- ✓ XEB score computation
- ✓ Fidelity measurement
- ✓ Error rate tracking
- ✓ JSON result export

### Multi-Agent Orchestration
- ✓ benchmarker_agent - Hardware testing
- ✓ executor_agent - Experiment execution
- ✓ validator_agent - Statistical validation
- ✓ publisher_agent - Zenodo publishing
- ✓ analyzer_agent - Result interpretation
- ✓ optimizer_agent - Circuit refinement

## Benchmarking World-Record Attempt

To push towards world-record performance metrics:

```bash
export IBM_QUANTUM_TOKEN='your_token'

# Launch and run
./osiris chat

# Then:
> benchmark ibm_torino 64 qubits extreme depth
> benchmark ibm_nazca 156 qubits with 65536 shots
> compare all backends on 64 qubit circuits

# Results show:
# - XEB scores degradation vs qubit count
# - Optimal depth for fidelity
# - Noise characteristics by backend
# - Job timing and success rates
```

## Output Files

- `quantum_benchmark_results.json` - Benchmark data export
- `~/discoveries/` - Experiment results directory
- Console logs - Real-time execution updates

## Troubleshooting

### "Qiskit not available" Warning
This is normal if you don't have a token set. The system uses **mock benchmarking** to show structure without real hardware.

Set token to enable real execution:
```bash
export IBM_QUANTUM_TOKEN='your_real_token'
```

### Intent Not Recognized
The engine uses pattern matching. Be descriptive:
- ✓ "benchmark ibm_torino"
- ✓ "test hardware performance"
- ✗ "go" (too vague)

### Tokens Not Loading
Verify they're exported:
```bash
echo $IBM_QUANTUM_TOKEN
echo $ZENODO_TOKEN
```

Reset if needed:
```bash
export IBM_QUANTUM_TOKEN='new_token'
```

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│  OSIRIS Chat-Native TUI (osiris_tui_core)  │
│  Natural language interface + conversation │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│  Intent Engine (osiris_intent_engine)       │
│  Pattern → Intent → Agents                  │
└────────────┬────────────────────────────────┘
             │
    ┌────────┼────────┬──────────┐
    ↓        ↓        ↓          ↓
 Bench    Exper.   Deploy    Analyze
  Agent    Agent    Agent     Agent
    │        │        │          │
    └────────┼────────┼──────────┘
             ↓
┌─────────────────────────────────────────────┐
│  Backend Selection                          │
│  - Quantum Benchmarker (ibm_torino/fez)    │
│  - Auto Discovery Pipeline (experiments)    │
│  - Zenodo Publisher (results)               │
│  - Orchestrator (campaigns)                 │
└─────────────────────────────────────────────┘
             │
             ↓
    ┌────────────────────┐
    │  IBM Quantum       │
    │  Hardware (4 hosts)│
    │  156q max/open plan│
    └────────────────────┘
```

## Integration with Existing OSIRIS

The chat system wraps your existing modules:
- `AutoDiscoveryPipeline` - Kept for core execution
- Campaign templates - Still available via "run campaign" command
- Zenodo publishing - Integrated into auto-workflow
- Statistical validation - Automatically applied

Nothing breaks. Everything still works. You just get:
- ✓ Chat interface (instead of CLI)
- ✓ Intent inference (no command syntax)
- ✓ Agent orchestration (background workers)
- ✓ Automatic workflow (you just ask)

## Next Steps

1. **Set your tokens** → Real hardware access
2. **Launch chat** → `./osiris chat`
3. **Describe what you want** → "benchmark extreme parameters"
4. **Monitor execution** → Watch real-time results
5. **Publish findings** → Auto DOI generation

The system will handle parameter selection, backend routing, statistical validation, and publication automatically.

---

**Status**: Production-ready  
**Last Updated**: 2026-04-07  
**Version**: 2.0 (Chat-Native)
