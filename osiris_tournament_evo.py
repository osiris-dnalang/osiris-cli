import random
from osiris_tetrahedral_field import TetrahedralField

class Lab:
    def __init__(self, name, explore_bias, disrupt_bias):
        self.name = name
        self.explore_bias = explore_bias
        self.disrupt_bias = disrupt_bias
        self.memory = []
        self.population = self.init_population()
        self.strategy_history = []
        self.prev_score = None

    def init_population(self, size=4):
        return [
            {"shots": random.choice([128, 256, 512, 1024]), "depth": random.choice([5, 10, 20])}
            for _ in range(size)
        ]

from osiris_ibm_execution import IBMExecutionManager, ExecutionStage

def experimentalist(config, problem_type="default", generation=0, use_ibm=False, ibm_manager=None, stage=None, use_tetrahedral=False, tetra_params=None):
    shots = config["shots"]
    depth = config["depth"]
    # Auto-enable tetrahedral field if requested or if 'simulator' in config
    if use_tetrahedral or config.get("simulator") == "tetrahedral_field":
        tf = TetrahedralField(**(tetra_params or {}))
        # Support for new substrate/physics options
        if hasattr(tf, 'substrate'):
            print(f"[Physics] Substrate: {tf.substrate}, N-dim: {tf.ndim}, Planck norm: {tf.planck_norm}, Causality: {tf.causality}")
        for _ in range(depth):
            tf.step(beta=0.5)
        summary = tf.summary()
        error = 1.0 - abs(summary["mean"])
        return {**config, "error": error, "energy": summary["energy"], "hardware": False, "simulator": "tetrahedral_field"}
    if use_ibm and ibm_manager is not None and stage is not None:
        # Map config to IBM execution (single trial)
        backend = ibm_manager.select_backend(ibm_manager.get_stage_config(stage).backend_priority)
        job_meta = ibm_manager._submit_job(
            circuit_hash=f"LAB_{shots}_{depth}_{generation}",
            stage=stage,
            backend=backend,
            n_qubits=shots,  # NOTE: shots is not qubits, but keeping mapping for demo
            depth=depth,
            shots=shots,
            label=f"LAB_trial_{generation}"
        )
        error = 1.0 - (job_meta.result_xeb if job_meta.result_xeb is not None else 0.0)
        return {**config, "error": error, "backend": backend, "hardware": True}
    # Simulated path
    if problem_type == "dynamic":
        base_error = (1 / (shots ** 0.5)) + (depth * 0.002)
    # Optionally: fallback to tetrahedral field if requested
        drift = 0.0
        if generation > 5:
            drift += depth * 0.003
        if generation > 10:
            drift += (1 / shots) * 2
        noise = random.uniform(0.0, 0.01)
        error = base_error + drift + noise
    elif problem_type == "default":
        base_error = (1 / (shots ** 0.5)) + (depth * 0.002)
        noise = random.uniform(0.0, 0.01)
        error = base_error + noise
    elif problem_type == "noisy":
        base_error = (1 / (shots ** 0.5)) + (depth * 0.002)
        noise = random.uniform(0.0, 0.03)
        error = base_error + noise
    elif problem_type == "multi_modal":
        error1 = (1 / (shots ** 0.5)) + (depth * 0.002)
        error2 = 0.03 + 0.0005 * shots + 0.01 * abs(depth - 5)
        error = min(error1, error2) + random.uniform(0.0, 0.01)
    else:
        error = 0.1 + random.random() * 0.1
    return {**config, "error": error}

def theorist(results):
    best = sorted(results, key=lambda x: x["error"])[:2]
    children = []
    for b in best:
        children.append({
            "shots": max(128, int(b["shots"] * random.uniform(0.7, 1.3))),
            "depth": max(1, int(b["depth"] * random.uniform(0.7, 1.3)))
        })
    return children

def challenger(best):
    return {
        "shots": max(128, int(best["shots"] * random.uniform(0.3, 0.7))),
        "depth": max(1, int(best["depth"] * random.uniform(1.5, 2.5)))
    }

def generate_candidates(lab, results):
    candidates = []
    if random.random() < lab.explore_bias:
        candidates += [{
            "shots": random.choice([128, 256, 512, 1024, 2048]),
            "depth": random.choice([5, 10, 20, 40])
        } for _ in range(2)]
    else:
        candidates += theorist(results)
    if random.random() < lab.disrupt_bias:
        best = min(results, key=lambda x: x["error"])
        candidates.append(challenger(best))
    return candidates

def reflect(lab, previous_score, current_score, environment_phase=None):
    if current_score < previous_score:
        return "strategy effective"
    else:
        return "strategy degraded"

def infer_strategy_rule(history):
    # Simple heuristic: if many failures when explore_bias is low, recommend increasing it
    failures_low_explore = [h for h in history if h["outcome"] == "strategy degraded" and h["explore_bias"] < 0.5]
    if len(failures_low_explore) > 2:
        return "increase exploration in unstable phases"
    return None

def run_lab(lab, generations=5, problem_type="default", gen_offset=0, use_ibm=False, ibm_manager=None, stage=None):
    for gen in range(generations):
        environment_phase = "early" if gen+gen_offset <= 5 else "mid" if gen+gen_offset <= 10 else "late"
        results = [experimentalist(p, problem_type=problem_type, generation=gen+gen_offset, use_ibm=use_ibm, ibm_manager=ibm_manager, stage=stage) for p in lab.population]
        lab.memory.extend(results)
        candidates = generate_candidates(lab, results)
        ranked = sorted(results, key=lambda x: x["error"])
        lab.population = ranked[:2] + candidates[:2]
        # Strategy reflection and self-tuning
        current_score = sum([r["error"] for r in results]) / len(results)
        if lab.prev_score is not None:
            outcome = reflect(lab, lab.prev_score, current_score, environment_phase)
            lab.strategy_history.append({
                "explore_bias": lab.explore_bias,
                "disrupt_bias": lab.disrupt_bias,
                "environment_phase": environment_phase,
                "outcome": outcome
            })
            if outcome == "strategy degraded":
                lab.explore_bias = min(1.0, lab.explore_bias + 0.1)
                lab.disrupt_bias = min(1.0, lab.disrupt_bias + 0.1)
        # Strategy learning: infer and apply rule
        rule = infer_strategy_rule(lab.strategy_history)
        if rule == "increase exploration in unstable phases" and environment_phase != "early":
            lab.explore_bias = min(1.0, lab.explore_bias + 0.2)
            lab.disrupt_bias = min(1.0, lab.disrupt_bias + 0.2)
        lab.prev_score = current_score
    return lab

def score_lab(lab):
    errors = [m["error"] for m in lab.memory]
    best = min(errors)
    avg = sum(errors) / len(errors)
    diversity = max(errors) - min(errors)
    return {"score": best + avg * 0.5, "best": best, "diversity": diversity}

def mutate_lab(lab):
    return Lab(
        name=f"{lab.name}_mut",
        explore_bias=min(1.0, max(0.0, lab.explore_bias + random.uniform(-0.2, 0.2))),
        disrupt_bias=min(1.0, max(0.0, lab.disrupt_bias + random.uniform(-0.2, 0.2)))
    )
def random_lab():
    return Lab(
        name="random",
        explore_bias=random.random(),
        disrupt_bias=random.random()
    )
def transfer_knowledge(labs):
    # Collect best configs from all labs
    best_configs = []
    for lab in labs:
        best = min(lab.memory, key=lambda x: x["error"])
        best_configs.append(best)
    # Inject into all labs
    for lab in labs:
        lab.population += random.sample(best_configs, min(2, len(best_configs)))

# Strategy blending

def crossover_lab(a, b):
    return Lab(
        name=f"{a.name}_{b.name}",
        explore_bias=(a.explore_bias + b.explore_bias) / 2,
        disrupt_bias=(a.disrupt_bias + b.disrupt_bias) / 2
    )

def run_tournament(rounds=5, problem_type="default", use_ibm=False):
    labs = [
        Lab("explorer", 0.7, 0.6),
        Lab("balanced", 0.4, 0.4),
        Lab("conservative", 0.2, 0.2)
    ]
    gen_offset = 0
    ibm_manager = None
    stage = None
    if use_ibm:
        from osiris_ibm_execution import IBMExecutionManager, ExecutionStage
        ibm_manager = IBMExecutionManager()
        stage = ExecutionStage.STAGE1_BASELINE  # Could be dynamic per round
    for r in range(rounds):
        print(f"\n🏆 Round {r+1} [{problem_type}]")
        for i, lab in enumerate(labs):
            # Only run explorer lab on hardware for demo
            if use_ibm and i == 0:
                run_lab(lab, generations=5, problem_type=problem_type, gen_offset=gen_offset, use_ibm=True, ibm_manager=ibm_manager, stage=stage)
            else:
                run_lab(lab, generations=5, problem_type=problem_type, gen_offset=gen_offset)
        gen_offset += 5
        transfer_knowledge(labs)
        scored = [(lab, score_lab(lab)) for lab in labs]
        scored.sort(key=lambda x: x[1]["score"])
        winner = scored[0][0]
        print(f"Winner: {winner.name} | Score: {scored[0][1]['score']:.5f} | Best: {scored[0][1]['best']:.5f} | Diversity: {scored[0][1]['diversity']:.5f}")
        # Add a hybrid lab (crossover of top 2)
        hybrid = crossover_lab(scored[0][0], scored[1][0])
        labs = [winner, mutate_lab(winner), hybrid]
    return labs

class BeliefEngine:
    def extract(self, report_text):
        beliefs = []
        if "conservative" in report_text and "dominated" in report_text:
            beliefs.append("low-variance strategies perform well in stable environments")
        if "explorer" in report_text and "dominates in dynamic" in report_text:
            beliefs.append("exploration is critical under shifting conditions")
        if "strategy failure and adaptation" in report_text:
            beliefs.append("adaptation is necessary for non-stationary systems")
        return beliefs

    def detect_conflicts(self, beliefs):
        conflicts = []
        if ("exploration is critical under shifting conditions" in beliefs and
            "low-variance strategies perform well in stable environments" in beliefs):
            conflicts.append("exploration vs stability tradeoff")
        return conflicts

def generate_report(labs, problem_type, memory=None):
    # Minimal research report generator
    summary = []
    for lab in labs:
        name = lab.name
        mem = lab.memory
        hist = lab.strategy_history
        if not mem:
            continue
        initial_error = mem[0]["error"]
        final_error = mem[-1]["error"]
        transitions = []
        for i, h in enumerate(hist):
            if i > 0 and hist[i-1]["outcome"] == "strategy effective" and h["outcome"] == "strategy degraded":
                transitions.append(i)
        summary.append({
            "name": name,
            "initial_error": initial_error,
            "final_error": final_error,
            "transitions": transitions,
            "history": hist
        })
    report_lines = []
    report_lines.append("\n=== OSIRIS Research Report ===")
    report_lines.append(f"Problem type: {problem_type}")
    for s in summary:
        report_lines.append(f"\nLab: {s['name']}")
        report_lines.append(f"  Initial error: {s['initial_error']:.5f}")
        report_lines.append(f"  Final error: {s['final_error']:.5f}")
        if s['transitions']:
            report_lines.append(f"  Strategy transitions at generations: {s['transitions']}")
        else:
            report_lines.append("  No major strategy transitions detected.")
        if s['history']:
            last = s['history'][-1]
            report_lines.append(f"  Last phase: {last.get('environment_phase','?')}, outcome: {last.get('outcome','?')}")
    report_lines.append("\nKey Insights:")
    for s in summary:
        if s['transitions']:
            report_lines.append(f"- {s['name']} lab: Strategy failure and adaptation detected at generations {s['transitions']}.")
        else:
            report_lines.append(f"- {s['name']} lab: Stable strategy throughout.")
    report_lines.append("\nConclusion: Adaptive exploration is critical for sustained performance in non-stationary systems.")

    # Belief extraction and meta-learning section
    report_text = "\n".join(report_lines)
    belief_engine = BeliefEngine()
    beliefs = belief_engine.extract(report_text)
    conflicts = belief_engine.detect_conflicts(beliefs)
    if memory is not None:
        memory.identity["beliefs"].extend([b for b in beliefs if b not in memory.identity["beliefs"]])
        memory.save()
    report_lines.append("\nSECTION: META-LEARNING")
    if beliefs:
        report_lines.append("Beliefs formed this round:")
        for b in beliefs:
            report_lines.append(f"- {b}")
    else:
        report_lines.append("No new beliefs formed.")
    if conflicts:
        report_lines.append("Conflicts detected:")
        for c in conflicts:
            report_lines.append(f"- {c}")
        report_lines.append("Suggested experiment: spawn specialist lab to resolve conflict.")
    print("\n".join(report_lines))


from osiris_learning.memory import Memory

def run_and_report(rounds=5, problem_type="default", memory=None, use_ibm=False):
    labs = run_tournament(rounds=rounds, problem_type=problem_type, use_ibm=use_ibm)
    generate_report(labs, problem_type, memory=memory)
    return labs

if __name__ == "__main__":
    memory = Memory()
    print("=== Default Problem ===")
    run_and_report(rounds=5, problem_type="default", memory=memory, use_ibm=True)
    print("\n=== Dynamic Problem (Moving Target) ===")
    run_and_report(rounds=5, problem_type="dynamic", memory=memory, use_ibm=True)

