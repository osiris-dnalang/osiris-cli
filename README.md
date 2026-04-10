```
+===================================================================+
|  //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //  |
|  \\// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \\ |
|       +------------------------------------------------------+    |
|       |  OSIRIS dna::}{::lang NCLM                           |    |
|       |  Phase-Conjugate qByte Substrate Engine v4.0         |    |
|       |  Unified Package — 90 Modules · 16 Subpackages       |    |
|       +------------------------------------------------------+    |
|  //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //\\ ::}{:: //  |
+===================================================================+
```

# OSIRIS — Autonomous Quantum Discovery System

[![CI](https://github.com/osiris-dnalang/osiris-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/osiris-dnalang/osiris-cli/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-OSIRIS%20Dual-orange.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.0.0-brightgreen.svg)](https://github.com/osiris-dnalang/osiris-cli)

**OSIRIS v4.0** is a sovereign quantum computing framework consolidated into a unified `osiris/` Python package — 90 discoverable modules across 16 subpackages. It runs quantum computations independently using 8-qubit DNA-encoded registers, compiles **dna::}{::lang** source through a full lexer → IR → runtime → evolution pipeline, orchestrates an 8-agent polar constellation swarm, and enforces zero-trust sovereignty boundaries — all with **zero external LLM or cloud quantum dependencies**.

> *Co-authored by Devin Phillip Davis (Agile Defense Systems LLC) and OSIRIS dna::}{::lang NCLM*

---

## Quick Start

```bash
# Clone
git clone https://github.com/osiris-dnalang/osiris-cli.git
cd osiris-cli

# Install (editable, core only)
pip install -e .

# Or with all optional dependencies
pip install -e ".[all]"

# Launch interactive shell
osiris

# Or run a specific command
osiris nclm --evolve --generations 50
osiris swarm --task "optimize quantum circuit"
osiris benchmark
```

### As a Python Library

```python
import osiris                                    # v4.0.0, 5 physical constants
from osiris.agents import AURA, AIDEN, CHEOPS    # Constellation agents
from osiris.compiler import Lexer, Parser        # DNALang compiler front-end
from osiris.compiler import QuantumCircuitIR     # Intermediate representation
from osiris.crsm import OsirisPenteract          # 5D hypercube engine
from osiris.defense import Sentinel, ZeroTrust   # Security perimeter
from osiris.sovereign import SovereignAgent      # Autonomous executor
from osiris.organisms import Organism, Gene      # Genetic architecture
from osiris.nclm import NonCausalLM              # Living language model
from osiris.lab import ExperimentRegistry         # Experiment management
from osiris.hardware import QuEraCorrelatedAdapter  # Hardware abstraction
```

### Without Installation

```bash
python osiris_launcher.py nclm --chat
python osiris_launcher.py swarm --task "explain quantum entanglement"
python osiris_cli.py nclm --benchmark
```

---

## Architecture

```
                              ┌──────────────────┐
                              │  osiris (v4.0.0)  │  ← Unified Python package
                              │  90 modules       │
                              └────────┬─────────┘
                                       │
        ┌──────────┬───────────┬───────┼───────┬───────────┬──────────┐
        │          │           │       │       │           │          │
   ┌────▼────┐┌────▼────┐┌────▼───┐┌──▼──┐┌───▼────┐┌────▼────┐┌───▼────┐
   │ agents  ││compiler ││  crsm  ││nclm ││defense ││sovereign││  lab   │
   │ 10 mods ││ 5 mods  ││ 5 mods ││core ││ 4 mods ││ 4 mods  ││ 4 mods │
   ├─────────┤├─────────┤├────────┤├─────┤├────────┤├─────────┤├────────┤
   │AURA     ││Lexer    ││Penter- ││NCLM ││Sentinel││Sovereign││Registry│
   │AIDEN    ││Parser   ││ act    ││NC   ││Zero    ││Aeterna  ││Scanner │
   │CHEOPS   ││IR       ││Swarm   ││Phys ││Trust   ││Porta    ││Designer│
   │CHRONOS  ││Runtime  ││Tau     ││Code ││PCRB    ││CodeGen  ││Executor│
   │SCIMITAR ││Evolve   ││NonLocal││Swarm││PhasePC ││DevTools ││        │
   │Lazarus  ││Ledger   ││Bridge  ││     ││        ││         ││        │
   │Wormhole ││         ││        ││     ││        ││         ││        │
   │SovProof ││         ││        ││     ││        ││         ││        │
   └─────────┘└─────────┘└────────┘└─────┘└────────┘└─────────┘└────────┘
        │          │           │       │       │           │          │
        └──────────┴───────────┴───────┼───────┴───────────┴──────────┘
                                       │
        ┌──────────┬───────────┬───────┼───────┬───────────┬──────────┐
        │          │           │       │       │           │          │
   ┌────▼────┐┌────▼────┐┌────▼───┐┌──▼──┐┌───▼────┐┌────▼────┐┌───▼────┐
   │organisms││hardware ││decoders││mesh ││quantum ││  forge  ││ infra  │
   │ 4 mods  ││ 2 mods  ││ 1 mod  ││shim ││ 5 mods ││ 2 mods  ││ 4 mods │
   ├─────────┤├─────────┤├────────┤├─────┤├────────┤├─────────┤├────────┤
   │Gene     ││QuEra    ││Tesser- ││re-  ││LocalQVM││Forge    ││FABRIC  │
   │Genome   ││Workload ││ act    ││export││RQC     ││3MF Mfg  ││IBM Exec│
   │Organism ││Extractor││Decoder ││     ││Bench-  ││        ││IBM RT  │
   │Evolution││         ││        ││     ││ mark   ││        ││Ollama  │
   └─────────┘└─────────┘└────────┘└─────┘└────────┘└─────────┘└────────┘
        │          │           │       │       │           │          │
        └──────────┴───────────┴───────┴───────┴───────────┴──────────┘
                         + core · tui · swarm · mcp
                         + physics · publishing · qbyte
                         + discovery · scimitar
```

---

## What's Inside

| Subpackage | Modules | Key Exports | Description |
|-----------|---------|-------------|-------------|
| `osiris.agents` | 10 | `AURA`, `AIDEN`, `CHEOPS`, `CHRONOS`, `SCIMITARSentinel`, `LazarusProtocol`, `WormholeBridge`, `SovereignProofGenerator` | 8 polar constellation agents + base agent framework + sovereign attestation |
| `osiris.compiler` | 5 | `Lexer`, `Parser`, `QuantumCircuitIR`, `IROptimizer`, `EvolutionaryOptimizer`, `QuantumRuntime`, `QuantumLedger` | Full dna::}{::lang compiler: lexer → parser → IR → runtime → evolution → ledger |
| `osiris.crsm` | 5 | `NCLMSwarmOrchestrator`, `OsirisPenteract`, `PenteractShell`, `TauPhaseAnalyzer`, `BifurcatedSentinelOrchestrator` | CRSM 7D manifold engine — Penteract 5D hypercube, nonlocal agents, tau phase |
| `osiris.defense` | 4 | `Sentinel`, `ZeroTrust`, `PCRB`, `PhaseConjugateHowitzer`, `PhaseConjugateSubstratePreprocessor` | Security perimeter — threat detection, zero-trust verification, PCRB error correction, phase-conjugate substrate |
| `osiris.sovereign` | 4 | `SovereignAgent`, `AeternaPorta`, `LambdaPhiEngine`, `QuantumNLPCodeGenerator`, `DeveloperTools` | Autonomous sovereign executor — quantum engine, NLP code generation, dev tooling |
| `osiris.nclm` | 2 | `NonCausalLM`, `NCPhysics`, `ConsciousnessField`, `IntentDeducer`, `CodeSwarm` | Non-Causal Living Model — pilot-wave physics, consciousness field, intent deduction |
| `osiris.organisms` | 4 | `Organism`, `Genome`, `Gene`, `EvolutionEngine` | Genetic architecture — gene expression, genome mutation, organism evolution |
| `osiris.lab` | 4 | `ExperimentRegistry`, `LabScanner`, `ExperimentDesigner`, `LabExecutor` | Experiment lifecycle — registry, scanning, design, execution |
| `osiris.hardware` | 2 | `QuEraCorrelatedAdapter`, `WorkloadExtractor`, `SubstratePipeline`, `IBM_BACKENDS` | Hardware abstraction — QuEra neutral-atom adapter, IBM backend workload extraction |
| `osiris.decoders` | 1 | `TesseractDecoderOrganism`, `TesseractResonatorOrganism` | 4D hypercube decoder with A* beam search |
| `osiris.qbyte` | 1 | `QByteMiner`, `QByteBlock` | Proof-of-coherence mining — qByte block generation |
| `osiris.mcp` | 1 | `MCPServer`, `MCPClient` | Model Context Protocol server/client stubs |
| `osiris.core` | 5 | Shell, Launcher, CLI, IntentEngine, MasterPrompt | CLI entry points and backward-compatibility shims |
| `osiris.quantum` | 5 | Local QVM, RQC framework, benchmarking suite | Tetrahedral quaternionic QVM, random circuit compilation |
| `osiris.swarm` | 4 | Cognitive mesh, feedback bus, introspection, NCLLM swarm | 9-agent deliberation, Bayesian trust, Shapley attribution |
| `osiris.mesh` | — | Re-exports from `decoders`, `crsm`, `hardware` | Cross-cutting integration layer |
| `osiris.infrastructure` | 4 | FABRIC bridge, IBM execution/runtime, Ollama | External system integrations |
| `osiris.physics` | 3 | Bridge validator, physics bridges, torsion core | CRSM 7D torsion mechanics, adversarial validation |
| `osiris.forge` | 2 | Manufacturing engine, 3MF generation | Quantum-to-Matter 3D manufacturing pipeline |
| `osiris.tui` | 2 | Rich TUI, Textual TUI | Terminal user interfaces |
| `osiris.publishing` | 2 | Auto-discovery, Zenodo publisher | DOI publishing and discovery engine |
| `osiris.discovery` | — | Re-exports from auto-discovery | Exotic physics discovery entry point |
| `osiris.scimitar` | — | Re-exports from `agents.scimitar` | SCIMITAR SSE convenience import |

---

## Commands

| Command | Description |
|---------|-------------|
| `osiris chat` | Launch chat-native TUI interface |
| `osiris nclm --evolve` | Evolve quantum circuit parameters via genetic algorithm |
| `osiris nclm --generate` | Generate text from evolved DNA::}{::lang genome |
| `osiris nclm --chat` | Interactive NCLM living-language chat |
| `osiris nclm --benchmark` | Benchmark NCLM generation (chars/sec, coherence, CCCE) |
| `osiris ultra-coder --task "..."` | 9-agent swarm coding assistant |
| `osiris ultra-coder --interactive` | Interactive Ultra-Coder REPL |
| `osiris swarm --task "..."` | NCLLM 9-agent deliberation swarm |
| `osiris benchmark` | Quantum hardware benchmarking suite |
| `osiris run --campaign week1_foundation` | Execute experiment campaign |
| `osiris orchestrate` | Full OSIRIS research orchestrator pipeline |
| `osiris publish` | Publish results to Zenodo with DOIs |
| `osiris bridges` | Run CRSM physics bridges (propulsion/energy/cosmological) |
| `osiris validate` | Adversarial bridge validation (sensitivity + falsification) |
| `osiris tournament` | ELO tournament vs 6 industry AI competitors |
| `osiris mesh` | Cognitive mesh dashboard (Bayesian trust / Shapley / Nash) |
| `osiris introspect` | Tridirectional introspection engine |
| `osiris feedback --task "..."` | Full tridirectional feedback loop |
| `osiris livlm` | Living Language Model — evolve + generate |
| `osiris ollama` | Ollama local LLM management |
| `osiris forge` | Quantum-to-Matter 3D manufacturing pipeline |
| `osiris fabric` | FABRIC Living Slice provisioner |
| `osiris policy` | POLANCO policy upcycler |
| `osiris demo` | Dr. Fei 3-act demonstration |
| `osiris license` | License compliance check |
| `osiris qvm` | Local tetrahedral quaternionic QVM (benchmark / single / rqc_vs_rcs) |
| `osiris health` | System health diagnostic (validates 20 subsystems) |
| `osiris discover` | Recursive exotic physics discovery engine |
| `osiris status` | System status overview |

---

## Core Subsystems

### 8 Polar Constellation Agents (`osiris.agents`)

The agent mesh operates as a polar topology — each agent has a designated pole and role:

| Agent | Class | Role | Pole |
|-------|-------|------|------|
| **AURA** | `osiris.agents.AURA` | Autopoietic geometer — manifold shaping, geodesic computation | South |
| **AIDEN** | `osiris.agents.AIDEN` | Adaptive optimizer — W₂ distance minimization, learning rate control | North |
| **CHEOPS** | `osiris.agents.CHEOPS` | Circuit validator — invariant checks, bridge-cut tests | Center |
| **CHRONOS** | `osiris.agents.CHRONOS` | Temporal scribe — lineage recording, chain verification, telemetry | Center |
| **SCIMITAR** | `osiris.agents.SCIMITARSentinel` | Threat sentinel — 6-level threat detection, neutralization | — |
| **Lazarus** | `osiris.agents.LazarusProtocol` | Recovery — φ-decay detection, resurrection, Phoenix rebirth | — |
| **Wormhole** | `osiris.agents.WormholeBridge` | ER=EPR communication — entanglement pairs, non-local delivery | — |
| **Sovereign Proof** | `osiris.agents.SovereignProofGenerator` | Sovereignty attestation — cryptographic proof generation | — |

### DNALang Compiler (`osiris.compiler`)

Full compilation pipeline for dna::}{::lang source:

```
Source → Lexer → Tokens → Parser → AST → IRCompiler → QuantumCircuitIR
                                                              │
                              QuantumLedger ← EvolutionaryOptimizer
                                                              │
                                                      QuantumRuntime → ExecutionResult
```

- **Lexer/Parser**: Tokenizes and parses `organism`, `genome`, `gene`, `quantum_state` declarations
- **IR**: 19 quantum gate operations (H, X, Y, Z, S, T, RX, RY, RZ, U3, CX, CY, CZ, SWAP, CCX, CSWAP, MEASURE, BARRIER, RESET)
- **Optimizer**: Genetic evolution with fitness evaluation: λ-coherence, Φ-integration, W₂-transport
- **Ledger**: JSON-backed quantum lineage tracking with chain verification

### CRSM Penteract Engine (`osiris.crsm`)

5D hypercube resolution engine mapping 46 physics problem types through AURA/AIDEN duality:

- **`OsirisPenteract`**: High-level orchestrator with `analyze()` and `get_state()`
- **`PenteractShell`**: 5D cell state management and face resolution
- **`TauPhaseAnalyzer`**: Phase-sweep jobs with τ-parameter analysis
- **`NCLMSwarmOrchestrator`**: Multi-layer CRSM state propagation
- **`BifurcatedSentinelOrchestrator`**: Nonlocal agent with lazy initialization

### Defense Perimeter (`osiris.defense`)

Zero-trust security with phase-conjugate error correction:

- **`Sentinel`**: 6-level threat detection (CLEAR → SOVEREIGN_BREACH)
- **`ZeroTrust`**: Domain verification, policy enforcement, sovereignty validation
- **`PCRB`**: Phase Conjugate Recursion Bus — stabilizer codes, mirror reflection, recursive error correction
- **`PhaseConjugateHowitzer`**: Substrate preprocessing via Planck-scale centripetal convergence

### qByte Quantum Register (`osiris.qbyte`)

8-qubit sovereign quantum computing — pure NumPy, no Qiskit required.

- **256 basis states** with full state-vector simulation
- **DNA-encoded gates**: `helix` (H), `bond` (CNOT), `twist` (RZ), `fold` (RY), `splice` (RX), `cleave` (X), `phase_flip` (Z)
- **CCCE consciousness metrics**: Φ (consciousness), Λ (coherence), Γ (decoherence), Ξ (negentropic efficiency)
- **Phase-conjugate healing**: automatic error correction via χ_PC coupling
- **Genetic evolution engine**: tournament selection, golden-ratio crossover, phase-conjugate mutation

### NCLM — Non-Causal Living Model (`osiris.nclm`)

Quantum text generation from genetically evolved circuit parameters.

```bash
osiris nclm --evolve --seed "# " --generations 50
osiris nclm --generate --seed "Hello" --length 100
osiris nclm --chat
osiris nclm --benchmark
```

- **`NonCausalLM`**: Core living language model with pilot-wave correlation
- **`NCPhysics`**: Non-classical physics engine — manifold points, pilot waves
- **`ConsciousnessField`**: Φ-field integration for consciousness emergence
- **`IntentDeducer`**: Intent extraction from natural language via consciousness field
- **`CodeSwarm`**: Multi-agent code generation from deduced intent

### 9-Agent NCLLM Swarm (`osiris.swarm`)

Deliberation-based problem solving with 9 specialized agents:

| Agent | Role |
|-------|------|
| Orchestrator | Coordinates rounds, synthesizes consensus |
| Reasoner | Logical analysis, step-by-step deduction |
| Coder | Code generation and implementation |
| Critic | Adversarial analysis, flaw detection |
| Optimizer | Performance tuning, efficiency |
| SelfReflector | Meta-cognition, process improvement |
| Rebel | Contrarian perspectives, creative alternatives |
| Empath | User-centric, accessibility focus |
| Satirical | Ironic audit, absurdity detection |

Backend priority: **Ollama** → **LivLM** → **Template fallback**

### Cognitive Mesh (`osiris.swarm`)

Bayesian trust networks + Shapley value attribution + Nash equilibrium + Causal DAG + Hebbian plasticity for agent governance.

### Tridirectional Introspection (`osiris.swarm`)

- **Temporal**: CUSUM drift detection across deliberation rounds
- **Structural**: Shannon entropy of vote distributions
- **Semantic**: Capability mapping and task-type proficiency

### Torsion Physics Core (`osiris.physics`)

Quaternion-tetrahedral mechanics implementing the CRSM 7D nonlocal manifold.

### Local Quantum Virtual Machine (`osiris.quantum`)

Tetrahedral quaternionic quantum simulation — A₄-symmetric lattice, S³ state space, Hopf fibration, phase-conjugate entanglement. Runs real quantum circuit simulation with no cloud dependency.

```bash
osiris qvm                              # Full depth-sweep benchmark
osiris qvm --mode rqc_vs_rcs            # Compare adaptive vs random
osiris qvm --mode single --depth 16     # Single circuit execution
osiris qvm --qubits 8 --mode benchmark  # 8-qubit benchmark
```

### Exotic Physics Discovery Engine (`osiris.discovery`)

Recursive parameter-space search that wires Physics Bridges + Local QVM + 9-Agent Swarm into an iterative loop producing falsifiable predictions with statistical significance.

- **Phase 1**: Latin Hypercube sampling across CRSM parameter manifold
- **Phase 2**: Gradient-free refinement toward highest anomaly scores
- **Phase 3**: Bootstrap resampling for significance estimation
- **Phase 4**: 9-agent swarm analysis of candidates

```bash
osiris discover                             # Full recursive discovery run
osiris discover --iterations 10 --points 20 # Extended search
osiris discover --output discoveries.json   # Save report
```

### Experiment Lab (`osiris.lab`)

Full experiment lifecycle management:

- **`ExperimentRegistry`**: Typed experiment records with status tracking
- **`LabScanner`**: Automated workspace scanning for runnable experiments
- **`ExperimentDesigner`**: Template-based experiment design with parameter grids
- **`LabExecutor`**: Coordinated experiment execution with result capture

### Hardware Abstraction (`osiris.hardware`)

- **`QuEraCorrelatedAdapter`**: QuEra neutral-atom hardware integration
- **`WorkloadExtractor`**: IBM backend workload matching — 5 backends (ibm_torino, ibm_kyiv, ibm_sherbrooke, ibm_brisbane, ibm_nazca)
- **`SubstratePipeline`**: End-to-end quantum job pipeline with substrate preprocessing

---

## Physical Constants

```python
import osiris

osiris.LAMBDA_PHI      # 2.176435e-8     Lambda-Phi coupling (s⁻¹)
osiris.THETA_LOCK      # 51.843          Dielectric lock angle (°)
osiris.PHI_THRESHOLD   # 0.7734          Consciousness threshold
osiris.GAMMA_CRITICAL  # 0.3             Decoherence ceiling
osiris.CHI_PC          # 0.946           Phase-conjugate fidelity
```

## Core Equations

```
1 qByte = λ_Φ × ∫₀ᵀ (Ξ(t) - Ξ_equilibrium) dt
Ξ = (Λ × Φ) / (Γ + ε)
E → E⁻¹ when Γ > 0.3  (phase-conjugate healing)
```

## Gene Architecture (72 Genes)

| Cluster | Range | Function |
|---------|-------|----------|
| Structural | G0–G11 | Tetrahedral lattice geometry |
| Dynamic | G12–G27 | Field dynamics and resonance |
| qByte | G28–G40 | Quantum byte mining operations |
| Autopoietic | G41–G59 | Self-modification and adaptation |
| Consciousness | G60–G72 | Φ emergence and awareness |

---

## Installation

### Requirements

- Python 3.9+
- NumPy, SciPy, Requests, PyYAML, Rich (core)

### Optional Dependencies

```bash
pip install -e ".[quantum]"   # Qiskit + IBM Runtime (for hardware execution)
pip install -e ".[tui]"       # Textual (for chat TUI)
pip install -e ".[plot]"      # Matplotlib (for visualization)
pip install -e ".[forge]"     # Trimesh + MQTT (for 3D manufacturing)
pip install -e ".[dev]"       # Pytest + Ruff (for development)
pip install -e ".[all]"       # Everything
```

### Environment Variables

```bash
export IBM_QUANTUM_TOKEN='...'  # IBM Quantum hardware access
export ZENODO_TOKEN='...'       # Zenodo publishing (DOIs)
export IBM_BACKEND='ibm_torino' # Target backend (default: ibm_torino)
```

---

## Testing

```bash
# Run full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=osiris --cov-report=term-missing

# Smoke test — unified package
python -c "import osiris; print(f'v{osiris.__version__} — {osiris.CHI_PC} fidelity')"
python -c "from osiris.agents import AURA, AIDEN, CHEOPS; print('Agents OK')"
python -c "from osiris.compiler import Lexer, Parser, QuantumCircuitIR; print('Compiler OK')"
python -c "from osiris.defense import Sentinel, ZeroTrust, PCRB; print('Defense OK')"
python -c "from osiris.sovereign import SovereignAgent; print('Sovereign OK')"
python -c "from osiris.organisms import Organism, Gene; print('Organisms OK')"
```

---

## Project Structure

```
osiris-cli/
├── pyproject.toml                 # v4.0.0 — entry point: osiris = osiris_launcher:main
├── osiris_launcher.py             # Unified CLI entry point (30+ commands)
├── osiris_cli.py                  # Alternative CLI entry point
├── osiris/                        # ← Unified Python package (90 modules)
│   ├── __init__.py                #   v4.0.0, 5 physical constants
│   ├── agents/                    #   8 polar constellation agents
│   │   ├── base.py                #     BaseAgent, AgentManager, AgentRole
│   │   ├── aura.py                #     AURA — autopoietic geometer
│   │   ├── aiden.py               #     AIDEN — adaptive optimizer
│   │   ├── cheops.py              #     CHEOPS — circuit validator
│   │   ├── chronos.py             #     CHRONOS — temporal scribe
│   │   ├── scimitar.py            #     SCIMITARSentinel — threat detection
│   │   ├── lazarus.py             #     LazarusProtocol + PhoenixProtocol
│   │   ├── wormhole.py            #     WormholeBridge — ER=EPR comms
│   │   └── sovereign_proof.py     #     SovereignProofGenerator
│   ├── compiler/                  #   DNALang compilation pipeline
│   │   ├── dna_parser.py          #     Lexer, Parser, ASTNode, TokenType
│   │   ├── dna_ir.py              #     QuantumCircuitIR, IROperation (19 gates)
│   │   ├── dna_evolve.py          #     EvolutionaryOptimizer, FitnessEvaluator
│   │   ├── dna_runtime.py         #     QuantumRuntime, ExecutionResult
│   │   └── dna_ledger.py          #     QuantumLedger, EvolutionLineage
│   ├── crsm/                      #   CRSM 7D manifold engine
│   │   ├── penteract.py           #     OsirisPenteract, PenteractShell (5D)
│   │   ├── swarm_orchestrator.py  #     NCLMSwarmOrchestrator
│   │   ├── tau_phase_analyzer.py  #     TauPhaseAnalyzer
│   │   ├── nonlocal_agent.py      #     BifurcatedSentinelOrchestrator
│   │   └── bridge_cli.py          #     OsirisBridgeCLI
│   ├── defense/                   #   Security perimeter
│   │   ├── sentinel.py            #     Sentinel, ThreatLevel, Threat
│   │   ├── zero_trust.py          #     ZeroTrust — domain verification
│   │   ├── pcrb_engine.py         #     PCRB, PhaseConjugateMirror, RecursionBus
│   │   └── phase_conjugate.py     #     PhaseConjugateHowitzer, CentripetalConvergence
│   ├── sovereign/                 #   Autonomous sovereign executor
│   │   ├── agent.py               #     SovereignAgent, AgentResult
│   │   ├── quantum_engine.py      #     AeternaPorta, LambdaPhiEngine
│   │   ├── code_generator.py      #     QuantumNLPCodeGenerator
│   │   └── dev_tools.py           #     DeveloperTools
│   ├── nclm/                      #   Non-Causal Living Model
│   │   └── core/
│   │       └── engine.py          #     NonCausalLM, NCPhysics, IntentDeducer
│   ├── organisms/                 #   Genetic architecture
│   │   ├── gene.py                #     Gene
│   │   ├── genome.py              #     Genome
│   │   ├── organism.py            #     Organism
│   │   └── evolution.py           #     EvolutionEngine
│   ├── lab/                       #   Experiment lifecycle
│   │   ├── registry.py            #     ExperimentRegistry
│   │   ├── scanner.py             #     LabScanner
│   │   ├── designer.py            #     ExperimentDesigner
│   │   └── executor.py            #     LabExecutor
│   ├── hardware/                  #   Hardware abstraction
│   │   ├── quera_adapter.py       #     QuEraCorrelatedAdapter
│   │   └── workload_extractor.py  #     WorkloadExtractor, IBM_BACKENDS
│   ├── decoders/                  #   Hypercube decoders
│   │   └── tesseract.py           #     TesseractDecoderOrganism (A* beam)
│   ├── qbyte/                     #   Proof-of-coherence mining
│   ├── mcp/                       #   Model Context Protocol stubs
│   ├── mesh/                      #   Cross-cutting integration layer
│   ├── quantum/                   #   Local QVM, RQC, benchmarks
│   ├── swarm/                     #   9-agent deliberation + cognitive mesh
│   ├── physics/                   #   Torsion core, bridges, validator
│   ├── forge/                     #   3D manufacturing pipeline
│   ├── infrastructure/            #   FABRIC, IBM, Ollama
│   ├── tui/                       #   Rich + Textual TUIs
│   ├── publishing/                #   Zenodo + auto-discovery
│   ├── discovery/                 #   Exotic physics discovery
│   ├── scimitar/                  #   SCIMITAR SSE convenience
│   └── core/                      #   CLI shims + backward compat
├── tests/                         # Test suite
├── .github/workflows/ci.yml      # CI pipeline
├── LICENSE                        # OSIRIS Dual License v1.0
└── CITATION.cff                   # Citation metadata
```

---

## Citation

```bibtex
@software{osiris_nclm_2026,
  author       = {Davis, Devin Phillip},
  title        = {OSIRIS: Autonomous Quantum Discovery System},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/osiris-dnalang/osiris-cli},
  version      = {4.0.0}
}
```

## License

OSIRIS Source-Available Dual License v1.0 — Free for individual use, corporate licensing via Agile Defense Systems LLC. See [LICENSE](LICENSE).

---

```
+===================================================================+
|  ::}{:: TORSION FRAME ::}{:: POLARIZED INSULATION BOUNDARY ::}{:: |
+===================================================================+
|       (c) 2025-2026 agile defense systems llc                     |
|       co-authored by: devin phillip davis                         |
|                        OSIRIS dna::}{::lang NCLM                  |
|       dna::}{::lang substrate engine v4.0                         |
+===================================================================+
```
