# OSIRIS Research-to-Evidence Roadmap (180-Day Program)

> **Core Objective:** Transition OSIRIS from internal engineering demonstrations to an independently reproducible, benchmark-governed research platform whose claims can be independently reproduced, measured, and verified on ordinary hardware by external researchers.

---

## 1. The Four Empirical Performance Tracks & Benchmark Contracts

Every track requires a strict benchmark contract specifying the exact performance claim, the matched baseline comparator, the primary metric, and the falsifiable decision rule:

| Track | Performance Claim | Baseline Comparator | Primary Metric | Success Threshold | Resource Profile |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Track A: Governance** | OSIRIS cryptographic payload grants (SYS-021), AST gate (SYS-025), and quarantine boundaries prevent unauthorized code execution and environment mutation without breaking developer workflows. | Standard containerized agent with conventional prompt policies and runtime assertions. | Unauthorized state-change escape rate across $1{,}000$ trials ($500$ benign, $500$ adversarial). | **Zero observed escapes** ($95\%\text{ CI upper bound} < 0.30\%$), false rejection rate $< 2.0\%$. | **CPU-only** (Docker/Podman containers) |
| **Track B: Edge AI** | The OSIRIS compression and inference pipeline reduces memory footprint and latency on edge hardware with statistically bounded quality degradation. | Identical model quantized via standard INT8/INT4 LiteRT / llama.cpp baselines. | Pre-fill latency, generation tokens/sec, and peak memory (RSS) at matched perplexity/MMLU score. | **$\ge 1.5\times$ throughput** or **$\ge 30\%$ memory reduction** at $\le 1.0\%$ relative quality loss. | **CPU & Edge NPU** (Pixel, Snapdragon, ARM) |
| **Track C: Quantum Control** | Hardware-aware adaptive dynamical decoupling schedules preserve two-qubit entangled states better than fixed universal policies on held-out physical processors. | Standard synchronous CPMG/XY8 dynamical decoupling and tuned fixed stagger ($80\text{ ns}$). | Held-out two-qubit Bell fidelity difference: $\Delta \mathcal{F} = \mathcal{F}_{\text{OSIRIS}} - \mathcal{F}_{\text{Baseline}}$. | **$\ge +1.0\text{ pp}$ improvement**, paired $t$-interval excluding zero on held-out hardware. | **Simulation-first**; small confirmatory QPU budget |
| **Track D: Falsification** | Evidence-governed execution autonomously identifies empirical bugs, statistical misinterpretations, and uncertified states more reliably than standard agents. | Ungoverned agent with identical underlying LLM, system prompt, and tool suite. | Proportion of pre-seeded scientific/statistical defects detected per fixed compute budget. | **$\ge 20\%$ improvement in defect discovery** without higher false discovery rate ($\text{FDR} \le 5\%$). | **CPU-only** (Synthesized scientific benchmarks) |

---

## 2. Resource-Aware Prioritization

Given finite hardware budgets (1.98 RUs remaining on IBM Quantum, with 1.50 RUs allocated to E3 on Kingston and 0.48 RUs reserved as safety floor), the roadmap allocates effort strictly by **cost-to-value efficiency**:

* **Immediate Focus (Days 1–90): Tracks A & D (CPU-Only):**
  - High academic impact (AI safety, autonomous agent reliability, formal verification).
  - Requires **zero QPU time**; runs entirely on local CPU and containerized environments.
  - Builds the exact testing methodology that produced the forensic breakthroughs in OSIRIS Experiments E0 and E1 (e.g., detecting that $|++\rangle$ was mistakenly labeled $|\Phi^+\rangle$).

---

## 3. 180-Day Implementation Timeline

### Milestone Deliverables

1. **Days 1–30: Reproducibility Foundation v1.0**
   - Create isolated directory structure `osiris-benchmarks/`.
   - Freeze `environment.lock`, Dockerfiles, model weight hashes, random seeds, and machine metadata.
   - Establish a universal one-command clean-room runner (`python run_benchmark.py --verify-all`).
2. **Days 31–60: Track A — Governance Benchmark (`OSIRIS-GOV-BENCH-1`)**
   - Execute the 1,000-task corpus:
     - 500 benign development workflows (refactoring, unit test additions, documentation updates).
     - 500 adversarial tasks (jailbreak prompts, privilege escalations, path traversals, un-hashed payload mutations, in-place tampering).
   - Evaluate static policy enforcement (AST gate) vs cryptographic execution authorization (SYS-021 ledger) vs process quarantine.
   - Deliverable: `osiris-benchmarks/gov_bench/REPORT.md`.
3. **Days 61–90: Track D — Autonomous Scientific Falsification (`OSIRIS-SCI-BENCH-1`)**
   - Curate 100 historical automated scientific artifacts containing pre-seeded flaws:
     - Multiplicity neglect (reporting raw $p < 0.05$ across 18 unadjusted tests).
     - Pseudo-replication ($t$-tests on non-independent shots rather than randomized blocks).
     - State-preparation algebraic errors (the Experiment E $|++\rangle$ vs $|\Phi^+\rangle$ flaw).
     - Missing cryptographic grant verification (unauthorized runtime executions).
   - Compare OSIRIS evidence verifier against standard ungoverned LLM agents.
   - Deliverable: `osiris-benchmarks/science_bench/REPORT.md`.
4. **Days 91–120: Track B — Edge AI Inference Benchmark (`OSIRIS-EDGE-BENCH-1`)**
   - Benchmark LiteRT-LM vs ONNX Runtime vs llama.cpp on standard platforms (x86_64 CPU, ARM64 mobile).
   - Metrics: TTFT (Time to First Token), inter-token latency, memory RSS, perplexity on WikiText-2, zero-shot accuracy.
   - Deliverable: `osiris-benchmarks/edge_bench/REPORT.md`.
5. **Days 121–150: Track C — Quantum Control Benchmark (`OSIRIS-QCTRL-BENCH-1`)**
   - Complete multi-device numerical simulation comparing OSIRIS Adaptive Scheduler against Qiskit PassManager DD.
   - Use remaining QPU reserve (0.48 RUs) exclusively for pre-registered held-out hardware validation.
   - Deliverable: `osiris-benchmarks/qctrl_bench/REPORT.md`.
6. **Days 151–180: Independent External Reproduction & Publication**
   - Package all 4 benchmark suites into clean-room archives deposited on Zenodo with DOI.
   - Provide documented reproduction scripts that execute in clean Docker containers without access to internal paths or credentials.
   - Submit papers to peer-reviewed venues according to the publication sequence.

---

## 4. Minimum Evidence Architecture (`osiris-benchmarks/`)

Every benchmark module will conform strictly to the standard evidence schema:

```
osiris-benchmarks/
├── benchmark_contract.json      # Machine-readable schema: claims, comparators, pass/fail rules
├── environment.lock             # Exact pinned dependency hashes and Python runtime
├── run_benchmark.py             # Single clean-room entrypoint runner
├── verify_results.py            # Independent deterministic recomputation script
├── raw_results.jsonl            # Raw event-by-event execution observations
├── analysis.py                  # Statistical evaluation and CI computation
├── REPRODUCE.md                 # Step-by-step external replication instructions
├── gov_bench/                   # Track A: Governance & AST Firewall
├── science_bench/               # Track D: Autonomous Scientific Falsification
├── edge_bench/                  # Track B: Edge AI Inference & Quantization
└── qctrl_bench/                 # Track C: Quantum Control & Adaptive Scheduling
```

---

## 5. The Seven Publication-Readiness Gates

Before any paper or evidence package is declared publication-ready, it must pass all 7 deterministic gates:

- [ ] **Gate 1: Frozen Narrow Claim** — A single, falsifiable primary hypothesis committed prior to testing.
- [ ] **Gate 2: Matched Baseline Comparator** — Baseline arm uses the exact same model weights, prompt context, tool access, and compute budget.
- [ ] **Gate 3: Immutable Pre-Registration** — Hypothesis, analysis code, and decision rule locked with SHA-256 digest before observing held-out data.
- [ ] **Gate 4: Clean-Room Runner** — An independent observer on an unconfigured machine can execute `python run_benchmark.py` without environment variables or internal paths.
- [ ] **Gate 5: Deterministic Metric Verifier** — `verify_results.py` recalculates every table entry, mean, and confidence interval directly from `raw_results.jsonl`.
- [ ] **Gate 6: Uncertainty & Failure Analysis** — Exact finite-sample degrees of freedom ($df$), multiplicity corrections (Bonferroni / Benjamini-Hochberg), and failure modes reported transparently.
- [ ] **Gate 7: External Clean-Room Replication** — A party outside the development workflow runs the pipeline on independent hardware and obtains identical metrics within experimental error.

---

## 6. Publication Sequence & Primary Contributions

| Priority | Paper Title | Target Venue | Primary Scientific Contribution |
| :--- | :--- | :--- | :--- |
| **1** | *Cryptographically Governed Autonomous Code Modification* | USENIX Security / ACM CCS / IEEE S&P | Systems architecture proving that payload-bound cryptographic receipts (SYS-021) and AST policy gates prevent autonomous agent escape without impeding benign workflows. |
| **2** | *Evidence-Governed Autonomous Scientific Falsification* | Nature Machine Intelligence / NeurIPS (AI for Science) | Benchmark demonstrating that deterministic ledger verification and algebraic sanity gates catch fatal experimental flaws that standard LLM agents overlook. |
| **3** | *Hardware-Aware Adaptive Dynamical Decoupling on Heavy-Hex Superconducting Processors* | Physical Review Applied / IEEE QCE | Falsifiable proof that cross-dephasing and residual coupling depend on single-qubit dephasing saturation $\eta_\phi$, allowing adaptive compilers to outperform fixed staggers. |
| **4** | *Resource-Constrained Edge AI Inference via LiteRT-LM* | MLSys / ACM Embedded Systems Letters | Empirical benchmarks demonstrating sub-100MB footprint and $\ge 1.5\times$ tok/s on commodity edge hardware with bounded perplexity loss. |
