# OSIRIS

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23063462.svg)](https://doi.org/10.5281/zenodo.23063462)

A local-first console for testing whether a small language model can learn from
conversation. OSIRIS's own model (`osiris.nclm`, the *core*) trains on every exchange and on your
documents, and may answer in its own voice only after it passes a held-out test; it has not
passed yet. Until then a local Ollama model speaks *for* it, labelled as such, and the core
trains on what it says. Models propose; deterministic code decides, measures and records.

Author: Devin Phillip Davis (Agile Defense Systems LLC). License: OSIRIS Source-Available
Dual License v1.0 (see `LICENSE`) — source-available, not open source.

Research Strategy Roadmap: Validating Learning Classifier Systems and Quantum Error Suppression on Physical QPUs

1. Strategic Context & Codebase Technical Audit

1.1 Verified Core Inventory Assessment

The execution of rigorous forensic code audits and hardware probes marks a decisive transition in research strategy: shifting away from historical speculative software claims toward empirically verified computational components. Prior architectural assertions regarding broad physics abstractions have been systematically audited, yielding a lean, fully functional, and auditable software core across the primary repository packages.

The verified inventory of execution-tested modules, their precise technical behavior, and their current empirical limitations are summarized in the table below:

Component Package	Key Submodule / File	Verified Behavior & Key Metrics	Empirical Status / Limitations
organism_sim	lcs.py	Implementation of textbook XCS (Wilson 1995; Butz & Wilson 2002) featuring match sets, covering per action, fitness-weighted prediction arrays, Widrow-Hoff updates, accuracy \kappa, niche GA with two-point crossover, Kovacs deletion, and bucket brigade with discount factor \gamma.	Solves 6-multiplexer to 100\% exploit accuracy within \sim 2,000 trials across 6/6 seeds; compacts macro-population from 130 to 50 rules. Includes a Roth–Erev reinforcement mode.
organism_sim	rules.py	Closed s-expression action language (emit, set, send, sever, route, adjust, if, seq) governed by an 8-operator set, static validator, and tree-walking interpreter.	Operates under a strict step budget with no I/O or eval primitives; fully sandboxed and safe.
organism_sim	bus.py	RoutedBus providing directed routing, tick-ordered message queues, typed payloads (signal, result, credit, state), line severing, drop accounting, and JSON descriptions.	Verified in-process deque execution.
organism_sim	agent.py	LCSAgent binding rule engines to agent registers (input bits \oplus last received symbol). Implements cross-agent credit assignment.	When Agent B receives a reward, it forwards credit to the agent whose symbol was consumed, closing the bucket brigade across the bus.
organism_sim	benchmarks/mux.py	Split 6-multiplexer environment. Agent A sees 2 address bits (can only send 1 of 4 symbols); Agent B sees 4 data bits plus the symbol.	Isolated Agent B caps at 0.69\text{--}0.75 accuracy (majority ceiling). Paired with a fixed protocol sender, Agent B achieves 1.00 accuracy on tested seeds.
dnalang-core	lexer.py, parser.py, sema.py	Hand-written recursive descent compiler for domain-specific circuit families. Validates typed gene parameters, duration units (16\,\mu\text{s}), formal qubit ports, constant folding, and static physics invariants.	Includes static dd-parity check: flags a warning if a gene has an odd echo count per port, preventing uncompensated net Pauli action prior to dispatch.
dnalang-core	lower.py, qc_ir.py	Canonical lowering engine compiling abstract specifications to flat IR, exporting to Qiskit and OpenQASM 3 (delays in dt or ns), generating canonical circuit hashes.	Deterministic lowering path; verified on Bell state execution (961/1039 on Aer) and dd_staggered_xy4.dna (82 ops, zero diagnostics).
dnalang-core	backends/ibm.py, ledger.py	Direct backend interface executing single-qubit/two-qubit configurations without transpiler re-mapping.	Features write-ahead provenance ledger logging submit-intent hashes prior to execution.
dnalang-core	metrics/core.py	Exact calculation of GHZ parity fidelity: F = \frac{1}{2}(P_{\text{pop}} + C) utilizing Discrete Fourier Transform (DFT) parity amplitudes.	Validated benchmark metric for entangled multi-qubit states.
dnalang-core	evolve/	DDSpace compiler integration, quasi-static statevector surrogate modeling detuning, ZZ crosstalk, and amplitude errors.	Surrogate ordering (xy4_stag > xy4 \approx cpmg \approx none) matches physical hardware trends (ibm_fez), though absolute magnitudes differ due to unmodeled T_2 dynamics.
osiris.nclm	autograd.py	Pure NumPy, tape-based reverse-mode automatic differentiation engine operating in float32.	Gradient-checked across matrix multiplication, GELU, Softmax, and Cross-Entropy functions within 2 \times 10^{-4} relative error.
osiris.nclm	transformer.py	2-layer, 18,000-parameter sequence transformer with custom training and optimization loops.	Validated convergence: loss drops from 3.45 to 0.008 in 60 steps on repeating sequence tasks (69/69 tests passing).
osiris.nclm	osiris_cognitive_mesh.py	Textbook Monte-Carlo Permutation-Sampling Shapley Value estimator calculating player contributions over a coalition quality function.	Functionally verified game-theoretic valuation component; sensitivity depends entirely on the accuracy of the underlying heuristic quality function.
Provenance Infra	Write-Ahead Ledger	Multi-implementation audit infrastructure (dnalang/ledger.py, organism_sim/audit.py with HMAC, osiris/compiler/dna_ledger.py).	Cryptographic intent-logging mechanism retained as the primary provenance standard.

Independent empirical probes beyond automated test suites revealed key dynamics not previously captured:

1. Multi-Agent Co-Adaptation Rates: In a from-scratch co-adaptation setup where both Agent A and Agent B learn simultaneously without a fixed protocol, 1 out of 6 random seeds converges to an optimal 4-symbol signalling system (1.00 accuracy). The remaining 5 seeds settle into partial pooling states (2\text{--}3 symbols, 0.72\text{--}0.88 accuracy). This reflects the established theoretical dynamics of reinforcement learning in Lewis signalling games and dictates that multi-agent performance must be evaluated as a statistical convergence rate across seed distributions rather than a single-seed success metric.
2. Organism Layer Ablation: Comparative ablation testing comparing the Learning Classifier System (LCS) with structural repair/mutation enabled (structural=True) against plain LCS execution (structural=False) demonstrated identical 6-multiplexer accuracy (1.00 across 4/4 seeds). This confirms that the top-level organism repair, phase coupling, and mutation triggers currently perform zero computational work in solving the task; the underlying LCS engine performs the entirety of the optimization.

These findings establish the baseline for an operational autopsy of legacy software failure modes.

1.2 Diagnostic Autopsy of Legacy Artifacts & Procedural Invariants

A thorough technical autopsy of historical failure modes is mandatory to establish future engineering controls and prevent the resurgence of ungrounded scientific claims. Forensic review reveals that prior high-impact claims stemmed from unvalidated instrumentation, uncorrected software defects, and premature physics nomenclature:

* Deconstruction of Historical Record Claims: Investigation of the 10^6\times gain artifact revealed that the reported 0.3843 "noise floor" was mathematically identical to \cos^2(51.7^\circ), representing the exact ideal theoretical population of the target state at the evaluated rotation angle \theta = 51.7^\circ. Rather than reflecting physical hardware decoherence suppression, hardcoded metrics were written into static JSON files. Physical re-execution of these circuit patterns on ibm_kingston yielded a classical state fidelity of 0.050, demonstrating that the physical \theta = 51.7^\circ rotation was statistically indistinguishable from zero rotation (\theta = 0), while transpiler routing generated 166 CX gates where 39 were sufficient.
* Deconstruction of Pseudo-Physics Terminology: Examination of physics-named code abstractions in the legacy osiris module demonstrated functional disconnects between nomenclature and computation:
  * "Pilot-wave attention" was implemented as a static scalar score multiplier: 1 + e^{-|i-j|/T}.
  * "Golden scale" consisted of a constant multiplication factor (0.618) applied to Feed-Forward Network (FFN) outputs, which was trivially absorbed by subsequent weight matrices.
  * "Phase-conjugate positional encoding" was a sinusoidal positional encoding using base \phi \approx 1.618 instead of 10^4. Whereas standard positional encoding spans four orders of magnitude to prevent positional aliasing across sequence lengths, base-\phi encoding restricted spectral representation to a narrow window of [0.38, 1]\text{ rad/position}, forcing severe frequency aliasing and creating a fundamental mathematical defect.
* Decoder Architectural Defects: The decoder module osiris/decoders/tesseract.py calculated residual syndromes via elementwise Bitwise XOR: \text{syndrome}_{\text{residual}} = \text{syndrome} \oplus \text{correction}. Standard Quantum Error Correction (QEC) decoders map data-qubit corrections through a parity-check matrix H. Treating syndrome bits and correction bits as identical structural objects invalidated the module as a functional QEC decoder.

To permanently prevent the recurrence of these software and experimental failure modes, all operations within this roadmap are strictly governed by a non-negotiable procedural invariant:

Procedural Governing Rule: No number gets a name until a histogram produced it, and no AI-written summary substitutes for opening the counts.

This procedural rule establishes the foundation for the formal unified paradigm and the underlying theoretical intent of the substrate.

2. Theoretical Intent & Provenance Architecture

2.1 The Unified Evolutionary & Reinforcement Loop

Stripping away non-functional nomenclature clarifies the core compute function of the substrate. The platform is formally defined as: an evolutionary and reinforcement learning architecture operating over populations of rule-based agents and quantum circuit space, evaluated via physical or simulated fitness metrics, passing messages over structured buses, and cryptographically verified through write-ahead provenance ledgers.

The unified, canonical execution loop governing both multi-agent reinforcement and quantum control sequence optimization is formally specified as:

\text{Genome / Rule Set} \longrightarrow \text{Compile} \longrightarrow \text{Execute (Sim | QPU | Agent)} \longrightarrow \text{Measure} \longrightarrow \text{Select} \longrightarrow \text{Hash-Chained Ledger}

+---------------------+     +-----------------+     +--------------------------+
| Genome / Rule Set   | --> | Compile (DNA)   | --> | Execute (Sim/QPU/Agent)  |
+---------------------+     +-----------------+     +--------------------------+
                                                                 |
                                                                 v
+---------------------+     +-----------------+     +--------------------------+
| Hash-Chained Ledger | <-- | Select / Evolve | <-- | Measure / Evaluate       |
+---------------------+     +-----------------+     +--------------------------+


Strict operational boundaries define the validated limits of this architecture:

* Verified Scope: Local multi-agent message passing via RoutedBus within a single process memory space, featuring cross-agent credit assignment and deterministic execution ticks.
* Unverified Scope: Assertions of "decentralized edge swarms," "fault-tolerant distributed infrastructure," or "resilient mesh routing" represent category errors when applied to an in-process, single-memory-space deque (RoutedBus). No code exists in the repository to handle multi-machine network transport, node failure recovery, or network partition tolerance. These unverified claims are formally excluded from active operational scope.

This unified loop transitions directly into cryptographic provenance mechanics.

2.2 Tamper-Evident Provenance & Write-Ahead Ledger Mechanics

To guarantee scientific validity and eliminate post-hoc data selection, all experimental executions on physical QPUs or agent simulations must pass through a write-ahead cryptographic ledger (backends/ibm.py and organism_sim/audit.py).

The operational execution sequence proceeds through three strictly enforced phases:

[Phase 1: Pre-Execution]
  ├── Construct Logical Circuit (LCID)
  ├── Compute Canonical JSON Hash: H(LCID)
  ├── Capture Backend Calibration Table: H(Calib)
  └── Write Submit-Intent Log Entry ---> Write-Ahead Ledger
                                                |
[Phase 2: Hardware Dispatch]                    v
  └── Dispatch to SamplerV2 / Target QPU -------+
                                                |
[Phase 3: Post-Execution Receipt]               v
  ├── Receive Raw Measurement Shots             |
  ├── Compute Shot Counts Hash: H(Shots)        |
  └── Write Post-Execution Receipt Entry <------+


1. Pre-Execution Submit-Intent Entry: Prior to dispatching a job to the hardware execution queue (e.g., via Qiskit SamplerV2.run), the environment constructs a canonical submit-intent record. This entry contains the UTF-8 SHA-256 hash of the logical circuit representation, explicit 2-qubit gate counts, target physical qubit mappings, and a complete SHA-256 hash of the target QPU's immediate calibration table. This intent is committed to append-only storage before job submission.
2. Hardware Dispatch: The circuit payload is submitted to the target QPU backend or simulation surrogate.
3. Post-Execution Receipt: Upon job completion, the raw, unedited measurement shot counts, output bitstrings, and execution metadata are logged alongside the pre-execution submit-intent hash, generating a closed provenance block.

Under the cryptographic security of SHA-256 collision resistance, this sequence prevents post-hoc circuit filtering, selective data omission, or metric alteration after hardware execution. Establishing this tamper-evident cryptographic chain provides the operational prerequisite for executing the phased research roadmap.

3. Phased Execution Roadmap

+-----------------------------------------------------------------------------------+
| MILESTONE 1: Multi-Agent Signalling Rates & LCS Scaling                           |
| - 50-seed co-adaptation sweep; Roth-Erev decay; 11/20-mux & 3-agent bus scaling.  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| MILESTONE 2: Organism Layer Operationalization vs. Ablation                       |
| - Non-stationary 6-mux environment; dynamic adaptation metrics; keep or strip.   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| MILESTONE 3: Unified Evolutionary & Ledger Interface                              |
| - Unify dnalang-core Space & LCS RuleEngine under single `evolve` package.        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| MILESTONE 4: Pre-Registered Hardware Error Suppression Paper                      |
| - Device surrogate calibration; pre-registered controls; physical QPU validation. |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| MILESTONE 5: Repository Consolidation & Asset Sanitization                        |
| - Consolidate to `dnalang` and `organism_sim`; Zenodo errata trail archiving.     |
+-----------------------------------------------------------------------------------+


3.1 Milestone 1: Multi-Agent Signalling Rates & LCS Scaling

The primary objective of Milestone 1 is to convert single-seed communication demonstrations into statistically rigorous, multi-seed convergence profiles.

* Statistical Rate Protocol: Conduct multi-agent co-adaptation benchmarks across 50 independent random seeds. Evaluate and report the probability of achieving full 4-symbol signalling P(\text{full}), probability of settling in partial pooling P(\text{partial}), and mean population accuracy accompanied by 95\% bootstrap confidence intervals. Package unit tests must be updated to assert rate distribution bounds rather than single-seed outcomes.
* Algorithmic Interventions: Implement and evaluate two communication recovery mechanisms to mitigate sub-optimal pooling equilibria:
  1. Forgetting parameters in Roth–Erev reinforcement (reinforce_decay < 1.0).
  2. Explicit niche exploration scheduling within the XCS engine.
  * Target Metric: Demonstrate a statistically significant increase in P(\text{full}) from \sim 0.17 to > 0.80.
* Scaling & Topology Expansion: Benchmark the core lcs.py engine against standard 11-multiplexer and 20-multiplexer environments to confirm scalability. Extend the message bus architecture to a 3-agent linear topology (\text{Address Agent} \rightarrow \text{Relay Agent} \rightarrow \text{Data Agent}) to test multi-hop credit backpropagation across intermediate nodes. This multi-hop experiment is critical to prove that reward signals propagate transitively across RoutedBus queues via forwarded credit payloads rather than relying on direct single-step feedback.

This empirical rate baseline leads directly to the critical evaluation of the organism layer.

3.2 Milestone 2: Organism Layer Operationalization vs. Ablation

Architectural abstractions must demonstrate clear computational utility under experimental stress testing; components that do not alter physical measurements must be removed.

* Non-Stationary Environment Design: Construct a dynamic 6-multiplexer benchmark where the underlying address bit mapping is permuted every N trials (e.g., flipping address bit indices at N = 5,000).
* Comparative Ablation Metrics: Measure fitness loss recovery rates and re-adaptation latency post-permutation, comparing three configurations:
  1. Standard baseline LCS (lcs.py).
  2. LCS with structural repair driven by entropy triggers (gp_mutate).
  3. LCS with sever-on-pressure signaling (sever).
* Decision Criteria: If structural mutation logic yields a statistically significant reduction in adaptation latency post-shift, retain and document the organism layer. If performance is statistically indistinguishable from baseline LCS, completely remove the organism abstraction layer from the active codebase.

This empirical evaluation precedes the consolidation of the evolutionary software interface.

3.3 Milestone 3: Unified Evolutionary & Ledger Interface

Optimization procedures across quantum circuit compilation and classifier learning must be consolidated into a single unified architecture.

                  +-----------------------------------+
                  |      Unified `evolve` Package      |
                  | Interface: Sample | Mutate | Cross |
                  |            Screen | Evaluate      |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  dnalang-core `Space` |                       | LCS `RuleEngine`      |
|  (Circuit Genomes)    |                       | (Classifier Rulesets) |
+-----------------------+                       +-----------------------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |    Write-Ahead Provenance Ledger   |
                  |     (SHA-256 / Hardware Hash)     |
                  +-----------------------------------+


* Unified Core Package Implementation: Construct a unified evolve module unifying dnalang-core's Space protocol and organism_sim's RuleEngine under a common object-oriented interface:
  * Sample(): Draw candidate specifications from search spaces.
  * Mutate(): Apply domain-specific mutation operators.
  * Cross(): Perform crossover across parent candidate specifications.
  * Screen(): Apply static invariant filters (e.g., static dd-parity checks).
  * Evaluate(): Fitness evaluation via surrogate models, physical QPUs, or multi-agent environments.
* Embedded Ledger Integration: Position the write-ahead cryptographic ledger directly underneath the evolve interface. Every evaluation automatically generates a cryptographically chained block containing the input genome, chosen evaluator, raw measurement output, and fitness score.

This software architecture provides the foundation for executing pre-registered QPU error suppression experiments.

3.4 Milestone 4: Pre-Registered Hardware Error Suppression Paper

The goal of Milestone 4 is to execute and publish a publication-grade error suppression experiment on physical IBM Quantum QPUs (\sim 30\text{ minutes} total QPU allocation).

[1. Surrogate Calibration]
  └── Fit quasi-static model from 30s Ramsey/echo hardware data.
  └── Assert Spearman rank correlation (rho >= 0.85, p < 0.01) before QPU expenditure.
        |
        v
[2. Domain & Genome Definition]
  └── Deploy per-qubit genome architecture with shared-structure prior.
        |
        v
[3. Control & Baseline Registration]
  └── Register Baselines: CPMG, XY4, XY8, UR, staggered XY4, PadDynamicalDecoupling.
  └── Enforce Matched Controls: Equal 2q gate counts, sign-flipped & random-angle controls.
        |
        v
[4. Hardware Execution & Metrics]
  └── Execute across >= 2 QPUs, >= 3 independent sessions, over >= 2 calendar days.
  └── Calculate Metrics: GHZ Parity Fidelity Witness & Wasserstein-2 (W2) Distances.


1. Surrogate Calibration: Fit a quasi-static statevector surrogate model using empirical device calibration data (30\text{ seconds} of Ramsey/echo pulse sequences per qubit chain). Validate surrogate predictive capability by asserting a statistically significant Spearman rank correlation threshold (\rho \ge 0.85, p < 0.01) between surrogate predictions and physical QPU sequence rankings prior to expending hardware execution time.
2. Genome & Domain Architecture: Implement a per-qubit sequence genome incorporating a shared-structure prior to systematically target and mitigate T_2 outlier channels across multi-qubit registers.
3. Pre-Registered Controls & Baselines: Evaluate candidate dynamically decoupled sequences against standard baseline controls: CPMG, XY4, XY8, UR, staggered XY4, and PadDynamicalDecoupling. All comparative test circuits must maintain identical 2-qubit gate counts, matched idle durations, sign-flipped controls, and randomized angle controls.
4. Replication & Target Metrics: Execute pre-registered experimental runs across \ge 2 distinct physical QPU backends, acquiring \ge 3 independent session replicates over \ge 2 calendar days. Quantify error suppression capabilities using GHZ parity fidelity witnesses (F = \frac{1}{2}(P_{\text{pop}} + C)) and Wasserstein-2 (W_2) distribution distances accompanied by 95\% bootstrap confidence intervals.

Completing this hardware demonstration enables repository consolidation.

3.5 Milestone 5: Repository Consolidation & Asset Sanitization

The final operational phase requires consolidating repository fragmentation into a clean, auditable repository structure.

* Target Architecture: Consolidate 172 fragmented legacy repositories down to two production-grade repositories:
  1. dnalang: Compiler, QPU execution pipeline, hardware surrogate models, and evolutionary sequence optimization.
  2. organism_sim: LCS engine, multi-agent bus, cross-agent credit assignment, and communication benchmarks.
* Documentation Sanitization: Update primary repository READMEs to state strictly verified operational behavior and raw measurement counts.
* Archival & Errata Management: Formally archive all remaining historical repositories, embedding clear pointers to the public Zenodo errata bundle (dnalang/zenodo_v2_bundle/).

With repository assets consolidated and legacy code archived, the strategy shifts to formal measurement governance and pre-registered execution protocols.

4. Measurement Governance & Pre-Registered Execution Protocol

4.1 Data & Execution Hierarchy Specifications

To prevent ambiguity between logical program code, hardware job dispatch, and physical measurement instances, all experiments must adhere to a strict four-level identity hierarchy:

Level	Definition	Identity Determinant	Mutability / Scope
Logical Circuit (LCID)	Pre-specified computational experiment defining target gates, state preparations, and measurement operators.	Canonical UTF-8 SHA-256 hash of standardized JSON circuit schema.	Immutable. Global logical scope; remains constant across backend executions.
Physical Circuit (PCID)	Transpiled/compiled physical execution specification mapped to explicit hardware qubit layouts and native gate sets.	Canonical UTF-8 SHA-256 hash of compiled physical gate sequence schema.	Immutable. Backend-specific scope; changes if layout or routing varies.
Execution Batch (ExecutionID)	A single physical execution batch of a PCID acquired under a specific calibration state and execution timestamp.	Unique UUIDv4 identifier linked to hardware Session ID and calibration hash.	Immutable post-acquisition. Instance-level scope.
Measurement Shot	Individual measurement outcome bitstring generated during an execution batch (Y_{ikj}).	Array index position j within the raw measurement array of an ExecutionID.	Immutable raw data. Nested strictly within an ExecutionID.

+-----------------------------------------------------------------------------------+
| Logical Circuit (LCID)                                                            |
| Hash: UTF-8 SHA-256 of Canonical Logical Schema                                   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Physical Circuit (PCID)                                                           |
| Hash: UTF-8 SHA-256 of Native Gate & Physical Qubit Mapping                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Execution Batch (ExecutionID)                                                     |
| Identity: UUIDv4 + Session ID + Calibration Hash                                  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Measurement Shot (Y_ikj)                                                          |
| Identity: Bitstring Outcome Index within Execution Batch Array                     |
+-----------------------------------------------------------------------------------+


* Physical Replication Rule: Individual measurement shots (N_{\text{shots}}) estimate the outcome distribution for a single execution batch; shots are not independent physical replicates. True physical replication occurs only across independent hardware execution batches (ExecutionID), separate calibration cycles, distinct operational sessions, and multiple QPU backends.

This execution hierarchy establishes the mandatory structural baseline for defining primary causal estimands and matched-pair statistical contrasts.

4.2 Primary Statistical Estimand & Matched-Pair Analysis

Confirmatory testing of quantum error suppression interventions requires pre-registered causal estimands and matched-pair statistical contrasts.

Primary Causal Estimand (\Delta F)

The primary statistical estimand is the population-level mean fidelity contrast (\Delta F) between the pre-registered test condition (T) and the matched control condition (C) across target circuit trials:

\Delta F = E[F_i \mid C_i = T] - E[F_i \mid C_i = C]

Matched-Pair Estimator

For K matched circuit pairs sharing identical logical depth, 2-qubit gate counts, target states, and physical qubit allocations, the pair-level difference D_k and overall sample estimator \widehat{\Delta F} are defined as:

D_k = F_{k,T} - F_{k,C}

\widehat{\Delta F} = \frac{1}{K} \sum_{k=1}^{K} (F_{k,T} - F_{k,C})

Hierarchical Mixed-Effects Model

Multi-backend and multi-session physical hardware acquisitions are analyzed using a pre-registered hierarchical linear mixed-effects model:

F_{ik} = \beta_0 + \beta_1 C_i + u_{\text{backend}} + u_{\text{circuit}} + \epsilon_{ik}

where i indexes the specific circuit trial instance and k indexes the matched pair or execution session. The variable C_i \in \{0, 1\} denotes the binary condition indicator (0 = \text{Control}, 1 = \text{Test}), while u_{\text{backend}} \sim \mathcal{N}(0, \sigma^2_{\text{backend}}) and u_{\text{circuit}} \sim \mathcal{N}(0, \sigma^2_{\text{circuit}}) represent random intercepts accounting for variance across hardware devices and circuit topologies, respectively. The fixed-effect coefficient \beta_1 = \Delta F defines the population-level intervention effect.

Falsification Criteria

The proposed error suppression intervention T is formally declared falsified if any of the following conditions occur:

1. The 95\% bootstrap confidence interval for \widehat{\Delta F} overlaps zero (\Delta F \le 0).
2. Conventional decoherence models (e.g., standard CPMG/XY4 dynamical decoupling) match or exceed the candidate intervention's fidelity out-of-sample.
3. The observed fidelity improvements vanish when evaluated against independently constructed calibration state tables.

Adherence to this pre-registered execution and provenance framework guarantees publication-grade scientific validity.

## What works today (v4.4.0)

| Part | What it does | Where |
|---|---|---|
| Conversation | Plain text talks to OSIRIS. Replies stream; keys typed during a reply are held and sent next, never mixed into the answer. | `osiris_cli/living.py` |
| Grounding | A stable brief of what is on record (pre-registered results, projects) plus per-message retrieval over your notes; answers name the file they used. | `osiris_cli/knowledge.py` |
| Read-only checks | Code, not the model, runs checks before answering — training status, git history, exchange-ledger integrity, system load, a file you name (credential files are never read). `/check` shows them directly. | `osiris_cli/probes.py` |
| Memory | Recent exchanges carry into the next session from the ledger (no model summarises them); `/remember` and `/forget` keep explicit facts. | `osiris_cli/living.py` |
| Speaking gate | The core answers in its own voice only after 30 held-out exchanges at ≤ 2.0 bits/byte and below a unigram baseline. Every 5th exchange is held out and never trained on. | `osiris_cli/living.py` |
| Batch training | `osiris train --hours 8 --detach` trains the core on a configured corpus, chat lessons and grounded distillation; distillation pauses while you chat. | `osiris_cli/train.py` |
| Provenance | Every exchange is appended to a SHA-256 hash chain (`~/.osiris/living/exchanges.jsonl`); `/check ledger` recomputes it. | `osiris_cli/probes.py` |

### Current measured state

The core has **not** earned its voice. After the first training runs it scored 7.60 bits/byte
on held-out documents against 5.03 for a unigram baseline — worse than the baseline. That is
the starting point the gate exists to measure honestly; the pre-registered learning test
(NCLM-1: gain over a memory-only baseline seven days after a restart) has not been run.

## Install and run

```bash
pip install -e .                 # core; Python 3.9+
pip install -e ".[research]"     # optional: dnalang, organism_sim, bridge sibling repos
ollama pull qwen2.5:7b           # a local mentor voice (qwen2.5:1.5b on small machines)
osiris                           # start talking
```

In the console: `/osiris` (core status and gate) · `/check [trainer|git|ledger|system]` ·
`/remember <fact>` · `/forget <words>` · `/train [start H|stop]` · `/mentor [model]` ·
`/self <text>` (the core's raw voice, ungated) · `/help` for everything else.

Optional sibling checkouts (`~/dnalang-core`, `~/bridge`, `~/organism_sim`, …) are found
automatically; other locations can be added with `OSIRIS_EXTRA_PATHS` (path-separated), and
dnalang-core's ledger with `OSIRIS_DNALANG_LEDGER`. Installed packages always take precedence.

## Related, separately published work

- **organism_sim / dnalang-core / bridge** — pre-registered ALife and dynamical-decoupling
  experiments with a checked-in scorecard (PASS and FAIL recorded alike).
  Zenodo [10.5281/zenodo.22862567](https://doi.org/10.5281/zenodo.22862567).
- **Staggered dynamical decoupling on ibm_marrakesh** — a pre-registered run in which
  bipartite-staggered DD kept P(+) = 0.900 at 32 µs versus 0.834 for simultaneous DD and 0.595
  idle (non-overlapping 95 % CIs; job `dau0q3qhcrkc73durtgg`; data in
  `experiments/osiris_advantage_marrakesh/`; Zenodo
  [10.5281/zenodo.23045494](https://doi.org/10.5281/zenodo.23045494)). This is a
  crosstalk-suppression result for a known technique family, not a quantum-advantage claim.

## What this repository also contains

The `osiris/` package and many root-level `osiris_*.py` modules come from earlier phases of the
project (the CRSM framework, qByte simulator, agent constellation, dna::}{::lang compiler v1).
Several of their headline constants and metrics — the τ-phase anomaly, θ_lock = 51.843°, the
CCCE "consciousness" metrics — were tested on hardware by the author and **refuted**; the code
is kept for provenance and still runs, but those quantities are not presented as physics.
The previous README is preserved at `docs/README_v4_legacy.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/
```
