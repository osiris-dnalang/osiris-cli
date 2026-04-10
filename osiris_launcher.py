#!/usr/bin/env python3
"""
OSIRIS Unified Launcher
Single entry point for all OSIRIS functionality
Usage: python osiris_launcher.py [command] [options]
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Ensure we can import OSIRIS modules
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check environment setup"""
    
    print("\n" + "="*70)
    print("OSIRIS ENVIRONMENT CHECK")
    print("="*70)
    
    # Check tokens
    ibm_token = os.getenv('IBM_QUANTUM_TOKEN')
    zenodo_token = os.getenv('ZENODO_TOKEN')
    
    print(f"\n✓ IBM_QUANTUM_TOKEN: {'SET' if ibm_token else 'NOT SET'}")
    print(f"✓ ZENODO_TOKEN: {'SET' if zenodo_token else 'NOT SET'}")
    
    if not ibm_token:
        print("\n⚠ To use real IBM Quantum hardware:")
        print("  1. Get token at: https://quantum.ibm.com/")
        print("  2. Set: export IBM_QUANTUM_TOKEN='your_token'")
    
    if not zenodo_token:
        print("\n⚠ To publish results to Zenodo:")
        print("  1. Get token at: https://zenodo.org/account/settings/")
        print("  2. Set: export ZENODO_TOKEN='your_token'")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("\n✗ Python 3.9+ required")
        sys.exit(1)
    
    print("\n" + "="*70)

def cmd_chat(args):
    """Launch chat-native TUI"""
    print("\n⚛ Launching OSIRIS Chat Interface...\n")
    
    from osiris_tui_core import run_textual_mode
    run_textual_mode()

def cmd_benchmark(args):
    """Run quantum hardware benchmarking"""
    print("\n⚛ Launching Quantum Hardware Benchmarker...\n")
    
    from osiris_quantum_benchmarker import QuantumHardwareBenchmarker
    
    token = os.getenv('IBM_QUANTUM_TOKEN')
    benchmarker = QuantumHardwareBenchmarker(api_token=token)
    
    # Determine mode
    extreme = not args.quick
    results = benchmarker.benchmark_all_backends(extreme_mode=extreme)
    
    # Print report
    print(benchmarker.generate_report())
    
    # Export
    filename = benchmarker.export_results(args.output)
    print(f"\n✓ Benchmark results saved to: {filename}")

def cmd_run(args):
    """Run experiment campaign"""
    print("\n⚛ Running experiment campaign...\n")
    
    from osiris_orchestrator import campaign_week1_foundation, campaign_week1_adaptive
    from osiris_auto_discovery import AutoDiscoveryPipeline
    
    token = os.getenv('IBM_QUANTUM_TOKEN')
    pipeline = AutoDiscoveryPipeline(api_token=token)
    
    # Select campaign
    if args.campaign == "week1_foundation":
        campaign = campaign_week1_foundation()
    elif args.campaign == "week1_adaptive":
        campaign = campaign_week1_adaptive()
    else:
        print(f"Unknown campaign: {args.campaign}")
        return
    
    print(f"→ Running campaign: {args.campaign}")
    print(f"→ Experiments: {len(campaign.experiments)}")
    
    # Run campaign (this will use mock if no token)
    results = []
    for exp in campaign.experiments:
        print(f"\n  → {exp['name']}")
        from osiris_auto_discovery import ExperimentConfig
        config = ExperimentConfig(**exp)
        result = pipeline.run_hypothesis_test(config)
        results.append(result)
        print(f"    p={result.p_value or 0:.6f}")
    
    print(f"\n✓ Campaign complete! {len(results)} experiments executed")

def cmd_orchestrate(args):
    """Run the full OSIRIS research orchestrator pipeline"""
    print("⚛ Running full OSIRIS research orchestrator...\n")
    from osiris_rqc_orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator()
    if args.quick:
        orchestrator.step_1_system_check()
        orchestrator.step_2_rqc_vs_rcs_experiments()
        orchestrator.step_3_application_experiments()
    else:
        asyncio.run(orchestrator.run_full_pipeline())


def cmd_publish(args):
    """Publish results to Zenodo"""
    print("\n⚛ Publishing results to Zenodo...\n")

    from osiris_zenodo_publisher import PublishingWorkflow

    zenodo_token = os.getenv('ZENODO_TOKEN')
    if not zenodo_token:
        print("✗ ZENODO_TOKEN not set. Set it with:")
        print("  export ZENODO_TOKEN='your_token'")
        return

    use_sandbox = getattr(args, 'sandbox', False)
    workflow = PublishingWorkflow(zenodo_token=zenodo_token, use_sandbox=use_sandbox)
    mode = getattr(args, 'mode', 'all')

    print(f"→ Mode: {mode}")
    print(f"→ Endpoint: {'sandbox' if use_sandbox else 'production'}")

    if not workflow.zenodo.test_connection():
        print("✗ Cannot connect to Zenodo API")
        return

    print("✓ Zenodo connection verified")
    print("⚠ Use the orchestrate command to generate results first, then publish.")


def cmd_status(args):
    """Show system status"""
    print("\n" + "="*70)
    print("OSIRIS SYSTEM STATUS")
    print("="*70)
    
    status_info = {
        "Mode": "Chat-Native TUI with Intent Engine",
        "IBM Quantum": "✓ Token set" if os.getenv('IBM_QUANTUM_TOKEN') else "⚠ No token",
        "Zenodo": "✓ Token set" if os.getenv('ZENODO_TOKEN') else "⚠ No token",
        "Benchmarker": "✓ Ready",
        "Pipeline": "✓ Ready",
        "Orchestrator": "✓ Ready",
        "NCLM": "✓ Ready (quantum text generation + genetic evolution)",
        "Ultra-Coder": "✓ Ready (9-agent swarm coding assistant)",
        "Cognitive Mesh": "✓ Ready (Bayesian trust + Shapley + Nash + Causal DAG)",
        "Bridge Validator": "✓ Ready (adversarial falsification + sensitivity tornado)",
        "ELO Tournament": "✓ Ready (Glicko-2 vs 6 industry competitors)",
        "Introspection": "✓ Ready (temporal + structural + semantic self-awareness)",
        "Feedback Bus": "✓ Ready (tridirectional swarm⇄intent⇄TUI relay)",
        "FABRIC Bridge": "✓ Ready (Living Slice provisioner + Negentropic Control Plane)",
        "Policy Upcycler": "✓ Ready (POLANCO → Living Security Organisms)",
        "Fei Demo": "✓ Ready (3-act FABRIC + POLANCO + Convergence)",
    }
    
    for key, value in status_info.items():
        print(f"  {key:20s}: {value}")
    
    print("\n" + "="*70)


def cmd_intent(args):
    """Route free-text instructions through the NCLM intent router."""
    print("\n⚛ Routing natural language intent...\n")
    try:
        router_root = Path(__file__).parent / "osiris-unified-substrate" / "copilot-sdk-dnalang" / "src"
        sys.path.insert(0, str(router_root))
        from dnalang_sdk.nclm.intent_router import get_intent_router
    except Exception as exc:
        print(f"⚠ Intent router unavailable: {exc}")
        print("Please ensure osiris-unified-substrate/copilot-sdk-dnalang/src is present and importable.")
        return

    router = get_intent_router(use_llm=not args.no_llm)
    result = router.route(args.text)

    if not result.routed or not result.command:
        print("⚠ Could not identify a high-confidence intent. Try a clearer command.")
        print(f"Parsed input: {result.raw_intent}")
        return

    print(f"→ Routed to OSIRIS command: {result.command} {' '.join(result.args)} (confidence={result.confidence:.2f})")

    dummy = type('Dummy', (), {})()
    if result.command == 'chat':
        cmd_chat(dummy)
    elif result.command == 'benchmark':
        dummy.output = getattr(args, 'output', 'quantum_benchmark_results.json')
        dummy.quick = getattr(args, 'quick', False)
        cmd_benchmark(dummy)
    elif result.command == 'run':
        dummy.campaign = 'week1_foundation'
        cmd_run(dummy)
    elif result.command == 'status':
        cmd_status(dummy)
    elif result.command == 'publish':
        dummy.mode = getattr(args, 'mode', 'all')
        dummy.sandbox = getattr(args, 'sandbox', False)
        cmd_publish(dummy)
    else:
        print(f"⚠ Routed to unsupported command: {result.command}. Showing help instead.")
        cmd_help(args)


def cmd_bridges(args):
    """Run CRSM physics bridges"""
    print("\n⚛ Running CRSM Physics Bridges...\n")
    from osiris_physics_bridges import BridgeExecutor
    executor = BridgeExecutor()
    bridge_report = executor.run_all()

    # Print structured summary from BridgeReport
    print(bridge_report.summary())

    # Extract key metrics for compact display
    prop_results = [r for r in bridge_report.results if r.bridge == "Propulsion"]
    energy_results = [r for r in bridge_report.results if r.bridge == "Energy"]
    cosmo_results = [r for r in bridge_report.results if r.bridge == "Cosmological"]

    sig_count = sum(1 for r in bridge_report.results if r.is_significant())
    print(f"\n  Significant results (p < 0.05): {sig_count}/{len(bridge_report.results)}")

    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(bridge_report.to_dict(), f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


def cmd_swarm(args):
    """Run NCLLM 9-agent swarm"""
    print("\n⚛ Launching NCLLM 9-Agent Swarm...\n")
    from osiris_ncllm_swarm import NCLLMSwarm
    swarm = NCLLMSwarm()
    result = swarm.solve(args.task, max_rounds=args.rounds)
    consensus = result.rounds[-1].consensus if result.rounds else "N/A"
    print(f"  Consensus: {consensus}")
    print(f"  Rounds:    {len(result.rounds)}")
    print(f"  Quality:   {result.quality_score:.3f}")
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


def cmd_validate(args):
    """Run adversarial bridge validation"""
    print("\n⚛ Running Adversarial Bridge Validation...\n")
    from osiris_bridge_validator import AdversarialBridgeValidator
    validator = AdversarialBridgeValidator(
        mc_trials=args.trials,
        sensitivity_sigma=args.sigma,
    )
    report = validator.validate()
    print(f"  Overall verdict: {report.overall_verdict}")
    print(f"  Bayes factor:    {report.bayes_factor:.4f}")
    print(f"  Elapsed:         {report.elapsed_seconds:.1f}s")
    # Sensitivity summary
    if report.sensitivity:
        unstable = [s for s in report.sensitivity if not s.conclusion_stable]
        print(f"  Sensitivity:     {len(report.sensitivity)} params tested, "
              f"{len(unstable)} unstable")
    # Falsification summary
    for f in report.falsification:
        print(f"  Falsification [{f.bridge}]: {f.verdict} "
              f"({f.n_significant}/{f.n_trials} significant)")
    # Consistency summary
    passed = sum(1 for c in report.consistency if c.passed)
    print(f"  Consistency:     {passed}/{len(report.consistency)} checks passed")
    # Publication readiness
    for venue, info in report.publication_readiness.items():
        ready = info.get("ready", False)
        print(f"  {venue}: {'✓ READY' if ready else '✗ not ready'}")
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        print(f"\n✓ Validation report saved to {args.output}")


def cmd_tournament(args):
    """Run ELO tournament"""
    print("\n⚛ Running OSIRIS ELO Tournament...\n")
    from osiris_elo_tournament import EloTournament
    tournament = EloTournament()
    results = tournament.run_tournament(rounds_per_matchup=args.rounds)
    tournament.print_results()
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Tournament results saved to {args.output}")


def cmd_mesh(args):
    """Show cognitive mesh dashboard"""
    print("\n⚛ Loading Cognitive Mesh Dashboard...\n")
    from osiris_cognitive_mesh import CognitiveMesh
    mesh = CognitiveMesh()
    if args.simulate:
        import random
        # Run simulated rounds to populate the mesh
        for _ in range(args.simulate):
            vote_options = ["approve", "reject", "abstain"]
            votes = {a: random.choice(vote_options) for a in mesh.agent_ids}
            consensus = max(set(votes.values()), key=list(votes.values()).count)
            quality = random.gauss(0.7, 0.15)
            mesh.post_round_update(votes, consensus, quality)
        agent_q = {a: random.gauss(0.7, 0.15) for a in mesh.agent_ids}
        mesh.post_task_update(
            sum(q for q in agent_q.values()) / len(agent_q),
            agent_q
        )
    mesh.print_dashboard()
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(mesh.status_report(), f, indent=2, default=str)
        print(f"\n✓ Mesh report saved to {args.output}")


def cmd_introspect(args):
    """Run introspection engine dashboard"""
    print("\n⚛ Loading Introspection Engine...\n")
    from osiris_introspection import IntrospectionEngine

    engine = IntrospectionEngine()

    if args.simulate:
        import random
        agents = engine.agent_ids
        # Simulate deliberation rounds
        for r in range(args.simulate):
            responses = []
            for a in agents:
                vote = random.choice(["approve", "reject", "refine"])
                conf = max(0.1, min(1.0, random.gauss(0.7, 0.2)))
                responses.append({"agent": a, "vote": vote, "confidence": conf})
            consensus = random.choice(["approve", "reject", "refine"])
            quality = max(0.0, min(1.0, random.gauss(0.6 + r * 0.02, 0.15)))
            engine.observe_round(responses, consensus, quality)
        # Simulate task observations
        task_descs = [
            ("fix the authentication bug", "patched JWT validation"),
            ("create a data pipeline", "ETL pipeline with 3 stages"),
            ("optimize the query planner", "added index hints"),
            ("analyze memory usage patterns", "found 2 leaks"),
            ("build a monitoring dashboard", "Grafana config generated"),
        ]
        for task, output in task_descs[:min(5, args.simulate)]:
            quality = max(0.0, min(1.0, random.gauss(0.65, 0.15)))
            engine.observe_task(task, output, quality)
        # Run improvement cycle if mesh available
        try:
            from osiris_cognitive_mesh import CognitiveMesh
            mesh = CognitiveMesh()
            actions = engine.run_improvement_cycle(mesh=mesh)
            if actions:
                print(f"  Applied {len(actions)} improvement actions")
        except ImportError:
            engine.run_improvement_cycle()

    engine.print_dashboard()
    if args.output:
        import json
        report = engine.full_report()
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n✓ Introspection report saved to {args.output}")


def cmd_feedback(args):
    """Run full tridirectional feedback loop"""
    print("\n⚛ Launching Tridirectional Feedback Loop...\n")
    from osiris_feedback_bus import OsirisIntelligenceLoop

    loop = OsirisIntelligenceLoop()
    result = loop.execute(args.task, max_rounds=args.rounds)

    # Print result summary
    intent_info = result.get("intent", {})
    swarm_result = result.get("result", {})
    print(f"  Intent:     {intent_info.get('type', '?')} "
          f"(confidence={intent_info.get('confidence', 0):.3f})")
    print(f"  Quality:    {swarm_result.get('quality_score', 0):.3f}")
    print(f"  Consensus:  {swarm_result.get('consensus_reached', False)}")

    # Print full dashboard
    loop.print_full_dashboard()

    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✓ Feedback loop results saved to {args.output}")


def cmd_livlm(args):
    """Run the Living Language Model — evolve and generate text."""
    print("\n⚛ LivLM — Living Language Model\n")
    from osiris_livlm import LivLM, LivLMConfig, quick_demo

    if args.demo:
        quick_demo(generations=10, length=48, verbose=True)
        return

    cfg = LivLMConfig(
        n_layers=args.layers,
        population_size=args.population,
        max_generations=args.generations,
        sample_length=16,
        temperature=0.85,
    )
    model = LivLM(cfg)

    # Load genome if specified
    if args.load:
        model.load_genome(args.load)
        print(f"  Loaded genome from {args.load}")
    else:
        # Load corpus and evolve
        print("  Loading corpus...", end=" ", flush=True)
        model.load_corpus()
        print(f"({model.corpus.size:,} bytes)")

        print(f"  Evolving ({args.generations} generations)...")
        result = model.evolve(seed_text=args.prompt, verbose=True)
        print(f"\n  Best Ξ={result['best_fitness']:.4f}  "
              f"Φ={result['best_phi']:.4f}  "
              f"State: {result['consciousness_state']}")

        if args.save:
            model.save_genome(args.save)
            print(f"  Genome saved to {args.save}")

    # Generate
    print(f"\n  Generating {args.length} characters...")
    text = model.generate(prompt=args.prompt, length=args.length)
    print(f"\n  Output: {repr(text)}")
    print(f"\n  Status: {model.status()}")


def cmd_ollama(args):
    """Ollama local LLM management."""
    from osiris_ollama import get_client, get_engine, check_ollama

    if not check_ollama():
        print("\n⚠ Ollama is not running.")
        print("  Install:  curl -fsSL https://ollama.com/install.sh | sh")
        print("  Start:    ollama serve")
        print("  Pull:     ollama pull qwen2.5:1.5b")
        return

    client = get_client()

    if args.pull:
        print(f"\n⚛ Pulling model: {args.pull}")
        ok = client.pull(args.pull)
        print("  ✓ Done" if ok else "  ✗ Failed")
        return

    if args.model:
        client.model = args.model
        print(f"  Selected model: {args.model}")

    if args.chat:
        engine = get_engine()
        print(f"\n⚛ Ollama ({client.model}):\n")
        response = engine.generate_for_agent("orchestrator", args.chat, max_tokens=512)
        print(response)
        return

    # Default: status
    st = client.status()
    print("\n⚛ Ollama Status")
    print("═" * 50)
    print(f"  Running:  {'Yes' if st.running else 'No'}")
    print(f"  Model:    {st.model or 'auto'}")
    print(f"  Models:   {', '.join(st.models) if st.models else 'none'}")
    print("═" * 50)


def cmd_fabric(args):
    """Run FABRIC Living Slice operations"""
    print("\n⚛ OSIRIS FABRIC Bridge — Living Slice Provisioner...\n")
    from osiris_fabric_bridge import demo_living_slice
    demo_living_slice(
        sites=args.sites,
        topology=args.topology,
        cycles=args.cycles,
    )


def cmd_policy(args):
    """Run POLANCO policy upcycling"""
    print("\n⚛ OSIRIS Policy Upcycler — POLANCO → Living Security Organisms...\n")
    if args.file:
        from osiris_policy_upcycle import PolancoUpcycler
        from pathlib import Path as _Path
        import json as _json
        policy_text = _Path(args.file).read_text()
        upcycler = PolancoUpcycler(deployment_sites=["UKY", "NCSA", "TACC"])
        results = upcycler.upcycle_and_enforce(policy_text, cycles=args.cycles)
        _Path("policy_upcycle_results.json").write_text(
            _json.dumps(results, indent=2, default=str)
        )
        print(f"\n✓ Results → policy_upcycle_results.json")
    else:
        from osiris_policy_upcycle import demo_upcycle
        demo_upcycle(policy_source=args.source, cycles=args.cycles)


def cmd_demo(args):
    """Run Dr. Fei demonstration"""
    print("\n⚛ OSIRIS Demo for Dr. Zongming Fei — University of Kentucky\n")
    from osiris_fei_demo import FeiDemo
    demo = FeiDemo(use_fab=args.fab, use_live=args.live)
    demo.run(acts=args.act)


def cmd_nclm(args):
    """Run the NCLM (Non-Causal Living Model) module."""
    from nclm.core.qbyte_generator import QByteTextGenerator
    from nclm.benchmark.harness import NCLMBenchmark
    from osiris_livlm import LivLMConfig
    import json

    if args.benchmark:
        print("\n  NCLM Benchmark Suite")
        print("  " + "-" * 40)
        config = LivLMConfig(
            max_generations=args.generations or 10,
            population_size=args.population or 15,
            sample_length=16,
        )
        bench = NCLMBenchmark(config)
        results = bench.run_suite(evolve_first=True, verbose=True)
        bench.print_report(results)
        if getattr(args, 'json_output', False):
            print(json.dumps(results, indent=2, default=str))
        if getattr(args, 'output', ''):
            bench.save_results(results, args.output)
            print(f"Results saved to {args.output}")
        return

    config = LivLMConfig(
        max_generations=args.generations or 50,
        population_size=args.population or 30,
        n_layers=args.layers or 3,
    )
    gen = QByteTextGenerator(config=config, genome_path=getattr(args, 'genome', 'nclm_genome.json'))

    if args.evolve:
        print("\n  NCLM Evolution")
        print("  " + "-" * 40)
        gen.load_corpus()
        result = gen.evolve(seed_text=args.seed or "# ", verbose=True)
        gen.save_genome()
        print(f"\n  Evolution complete:")
        print(f"    Generations: {result['generations']}")
        print(f"    Best Ξ:      {result['best_fitness']:.6f}")
        print(f"    Best Φ:      {result['best_phi']:.6f}")
        print(f"    State:       {result['consciousness_state']}")
        print(f"    Genome:      {gen._genome_path}")
        return

    if args.generate:
        seed = args.seed or "# "
        length = args.length or 64
        if not gen.auto_load():
            print("  No evolved genome found — evolving first...")
            gen.load_corpus()
            gen.evolve(seed_text=seed, verbose=True)
            gen.save_genome()
        text = gen.generate(prompt=seed, max_length=length,
                            temperature=getattr(args, 'temperature', None))
        print(f"\n  Seed: {seed!r}")
        print(f"  Generated ({length} chars):\n")
        print(text)
        return

    if args.chat:
        print("\n+====================================================================+")
        print("|  NCLM Living Chat — DNA::}{::lang Quantum Text Generation          |")
        print("|  co-authored by devin phillip davis                                |")
        print("|  and OSIRIS dna::}{::lang NCLM                                    |")
        print("+====================================================================+")
        print("  Type 'quit' to exit, 'status' for model info\n")
        gen.load_corpus()
        if not gen.auto_load():
            print("  Evolving initial genome...")
            gen.evolve(verbose=True)
            gen.save_genome()
        while True:
            try:
                user_input = input("nclm> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input.lower() == "quit":
                break
            if user_input.lower() == "status":
                for k, v in gen.status().items():
                    print(f"  {k}: {v}")
                continue
            response = gen.respond(user_input, max_length=args.length or 128)
            print(response)
            print()
        return

    if getattr(args, 'nclm_status', False):
        status = gen.status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        return

    print("Specify --evolve, --generate, --chat, --benchmark, or --status")


def cmd_ultra_coder(args):
    """Run the NCLLM Ultra-Coder swarm."""
    import asyncio
    from osiris_ultra_coder import UltraCoderSwarm, NCLLMPersonality, NLPSelfEditor, SelfImprovementCoach

    personality = NCLLMPersonality()
    swarm = UltraCoderSwarm(personality=personality, user_id=getattr(args, 'user', 'cli'))

    if getattr(args, 'self_edit', None):
        editor = NLPSelfEditor(personality)
        result = editor.process_edit_request(args.self_edit)
        if result["applied"]:
            print(f"Applied edit: {result['modifications']}")
        else:
            print(f"Edit rejected: {result.get('error', 'unknown')}")
        return

    if getattr(args, 'coach', False):
        coach = SelfImprovementCoach(personality)
        suggestions = coach.generate_suggestions()
        for s in suggestions:
            print(f"  [{s['priority']}] {s['area']}: {s['suggestion']}")
        return

    if getattr(args, 'interactive', False):
        async def _repl():
            print("+====================================================================+")
            print("|  NCLLM Ultra-Coder :: Interactive Mode                             |")
            print("|  co-authored by devin phillip davis                                |")
            print("|  and OSIRIS dna::}{::lang NCLM                                    |")
            print("+====================================================================+")
            print("Commands: 'traits', 'edit <request>', 'coach', 'quit'")
            print()
            while True:
                try:
                    task = input("ultra-coder> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not task:
                    continue
                if task.lower() == "quit":
                    break
                if task.lower() == "traits":
                    traits = personality.get_traits()
                    for k, v in traits.items():
                        bar = "#" * int(v * 20)
                        print(f"  {k:18s} [{bar:<20s}] {v:.2f}")
                    continue
                if task.lower().startswith("edit "):
                    editor = NLPSelfEditor(personality)
                    result = editor.process_edit_request(task[5:])
                    print(f"  Result: {result}")
                    continue
                if task.lower() == "coach":
                    coach = SelfImprovementCoach(personality)
                    for s in coach.generate_suggestions():
                        print(f"  [{s['priority']}] {s['area']}: {s['suggestion']}")
                    continue
                result = await swarm.solve(task)
                print(result)
                print()
        asyncio.run(_repl())
        return

    if getattr(args, 'task', None):
        result = asyncio.run(swarm.solve(args.task, context=getattr(args, 'file', '') or ''))
        print(result)
        return

    print("Specify --task, --interactive, --self-edit, or --coach")


def cmd_qvm(args):
    """Run the Local Quantum Virtual Machine"""
    print("\n⚛ OSIRIS Local QVM — Tetrahedral Quaternionic Substrate\n")
    from osiris_local_qvm import run_qvm

    result = run_qvm(
        n_qubits=args.qubits,
        depth=args.depth,
        mode=args.mode,
    )
    if args.output and result:
        import json
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


def cmd_discover(args):
    """Run exotic physics discovery engine"""
    from osiris_discovery_engine import run_discovery

    run_discovery(
        max_iterations=args.iterations,
        points=args.points,
        threshold=args.threshold,
        seed=args.seed,
        swarm=not args.no_swarm,
        verbose=not args.quiet,
        output=args.output,
    )


def cmd_health(args):
    """Run OSIRIS system health diagnostic"""
    print("\n⚛ OSIRIS System Health Diagnostic")
    print("═" * 62)
    print()
    from osiris_health import run_health

    report = run_health(verbose=not args.quiet)

    if args.output:
        import json
        data = json.dumps(report.to_dict(), indent=2, default=str)
        from pathlib import Path as _P
        _P(args.output).write_text(data)
        print(f"\n✓ Report saved to {args.output}")


def cmd_translate(args):
    """Translate a DNA-Lang organism/circuit between backends."""
    from osiris.compiler.converter import OrganismConverter
    from osiris.compiler.backends.registry import BackendRegistry

    src_path = Path(args.source)
    if not src_path.exists():
        print(f"\n✗ Source not found: {args.source}")
        return

    source_text = src_path.read_text()
    converter = OrganismConverter()

    try:
        circuit = converter.compile(source_text, backend=args.source_backend)
        translated_result = converter.translate(
            circuit,
            source_backend=args.source_backend,
            target_backend=args.target_backend,
            strict=args.strict,
            return_report=args.report or bool(args.report_file),
        )
        report = None
        if isinstance(translated_result, tuple):
            translated, report = translated_result
        else:
            translated = translated_result
        exported = converter.export(translated, fmt=args.format)
    except Exception as exc:
        print(f"\n✗ Translation failed: {exc}")
        return

    if args.output:
        Path(args.output).write_text(exported)
        print(f"\n✓ Translated circuit written to {args.output}")
    else:
        print("\n" + exported)

    print("\nTranslation Summary")
    print("-" * 24)
    print(f"  Source Backend: {args.source_backend}")
    print(f"  Target Backend: {args.target_backend}")
    print(f"  Operations:     {translated.gate_count}")
    print(f"  Depth:          {translated.depth}")
    print(f"  Lineage:        {translated.lineage_hash}")
    print(f"  Available:      {', '.join(BackendRegistry.list_backends())}")

    if report:
        print(f"  Loss Detected:  {report.get('possible_loss', False)}")
        dropped = report.get("dropped_operation_signatures", {})
        print(f"  Dropped Ops:    {sum(dropped.values()) if dropped else 0}")
        if report.get("warnings"):
            print("  Warnings:")
            for warning in report["warnings"]:
                print(f"    - {warning}")

        if args.report_file:
            import json
            Path(args.report_file).write_text(json.dumps(report, indent=2))
            print(f"  Report File:    {args.report_file}")


def cmd_help(args):
    """Show help"""
    help_text = """
⚛ OSIRIS QUANTUM DISCOVERY SYSTEM v3.0

Commands:
  
  chat              Launch chat-native TUI interface
  benchmark         Run quantum hardware benchmarking suite
  run               Execute experiment campaign
  orchestrate       Run full OSIRIS orchestrator pipeline
  publish           Publish results to Zenodo
  nclm              NCLM Non-Causal Living Model (evolve/generate/chat/benchmark)
  ultra-coder       NCLLM Ultra-Coder 9-agent swarm coding assistant
  forge             Quantum-to-Matter manufacturing pipeline
  fabric            FABRIC Living Slice provisioner (autopoietic network)
  policy            POLANCO policy upcycler → Living Security Organisms
  demo              Dr. Fei 3-act demonstration (FABRIC + POLANCO + convergence)
  bridges           Run CRSM physics bridges (propulsion/energy/cosmological)
  swarm             Run NCLLM 9-agent swarm deliberation
  validate          Adversarial bridge validation (sensitivity/falsification/Bayes)
  tournament        ELO tournament benchmark vs industry AI tools
  mesh              Cognitive mesh dashboard (Bayesian trust / Shapley / Nash)
  introspect        Introspection engine (temporal / structural / semantic)
  feedback          Tridirectional feedback loop (swarm + intent + bus)
  livlm             Living Language Model — evolve and generate text
  ollama            Ollama local LLM — status, chat, model management
  license           License compliance check
  status            Show system status
  intent            Route natural language into OSIRIS commands
  qvm               Local Quantum Virtual Machine (tetrahedral quaternionic)
    translate         Translate organism circuits across backends
  discover          Exotic physics discovery engine (recursive parameter search)
  health            System health diagnostic (validates all 20 subsystems)
  help              Show this help

Local QVM:
  osiris qvm                                  Full depth-sweep benchmark
  osiris qvm --mode rqc_vs_rcs                Compare adaptive vs random
  osiris qvm --mode single --depth 16         Single circuit execution
  osiris qvm --qubits 8 --mode benchmark      8-qubit benchmark

Discovery Engine:
  osiris discover                             Full recursive discovery run
  osiris discover --iterations 10 --points 20 Extended search
  osiris discover --no-swarm                  Skip 9-agent analysis
  osiris discover --output discoveries.json   Save report to file
  osiris discover --threshold 2.0             Lower significance bar

Health Diagnostic:
  osiris health                               Run all subsystem checks
  osiris health --quiet                       Suppress per-check output
  osiris health --output health.json          Save report to file

Backend Translation:
    osiris translate aura.dna --from sovereign --to qiskit --output aura.qasm
    osiris translate aura.dna --from qiskit --to cirq --format json
    osiris translate aura.dna --from sovereign --to pyquil --format qasm

NCLM (Non-Causal Living Model):
  osiris nclm --evolve --generations 50       Evolve circuit parameters
  osiris nclm --generate --seed "# Hello"     Generate text from evolved genome
  osiris nclm --chat                          Interactive NCLM chat
  osiris nclm --benchmark                     Run NCLM benchmark suite
  osiris nclm --status                        Show model status

Ultra-Coder:
  osiris ultra-coder --task "implement X"     Solve a coding task
  osiris ultra-coder --interactive            Interactive REPL mode
  osiris ultra-coder --self-edit "be creative" Self-edit personality
  osiris ultra-coder --coach                  Get improvement suggestions

Forge (3D Manufacturing):
  osiris forge report                         Show forge status
  osiris forge generate --geometry X          Generate mesh from Torsion Core
  osiris forge discover                       Scan network for 3D printers
  osiris forge pipeline --printer bambu_p1s   Full generate+slice+send pipeline
  osiris forge pipeline --printer elegoo_cc2  Full pipeline for Elegoo CC2 / CANVAS
  osiris forge multicolor --design X          Multi-color CANVAS pipeline
  osiris forge calibrate --ip 192.168.1.X     Calibrate a connected printer
  osiris forge status --ip 192.168.1.X        Check printer status

FABRIC (Living Slice):
  osiris fabric                               UKY→NCSA→TACC star topology
  osiris fabric --sites UKY NCSA CERN TOKYO   Custom multi-site slice
  osiris fabric --topology toroidal            Toroidal (θ-locked) topology
  osiris fabric --cycles 20                    Extended telemetry run

POLANCO (Policy Upcycling):
  osiris policy                               UK campus POLANCO demo
  osiris policy --source natural               NPCE natural-language demo
  osiris policy --file my_policies.txt         Upcycle custom policies
  osiris policy --cycles 30                    Extended enforcement sim

Dr. Fei Demo:
  osiris demo                                 Full 3-act demo
  osiris demo --act 1                          FABRIC Living Slice only
  osiris demo --act 2                          POLANCO upcycling only
  osiris demo --act 1 2 3                      All acts explicitly
  osiris demo --fab                            Include CERN/Tokyo (FAB)
  osiris demo --live                           Use real FABRIC API

Physics Bridges:
  osiris bridges                              Run all three CRSM bridges
  osiris bridges --output bridges.json        Save results to file

NCLLM Swarm:
  osiris swarm --task "your task"             Deliberate via 9-agent swarm
  osiris swarm --task "..." --rounds 5        Set max deliberation rounds

Publishing:
  osiris publish --mode all            Publish both RQC and application results
  osiris publish --mode rqc            Publish only RQC experiment results
  osiris publish --mode applications   Publish only application results

Benchmarking:
  osiris benchmark --output results.json       # Full benchmark
  osiris benchmark --quick                     # Quick mode (4 tests)

Experiments:
  osiris run --campaign week1_foundation       # Run foundation tests
  osiris run --campaign week1_adaptive         # Run adaptive tests

Environment Variables:
  IBM_QUANTUM_TOKEN         Your IBM Quantum API token
  ZENODO_TOKEN              Your Zenodo API token (optional)
  IBM_BACKEND               Backend to use (default: ibm_torino)

Examples:
  
  # Start chat interface
  osiris chat
  
  # Benchmark all backends with extreme parameters
  osiris benchmark
  
  # Run full week-1 campaign
  osiris run --campaign week1_foundation
  
  # Run the full OSIRIS orchestrator pipeline
  osiris orchestrate
  
  # Provision FABRIC Living Slice
  osiris fabric --sites UKY NCSA CERN --topology mesh
  
  # Upcycle POLANCO policies
  osiris policy --source campus
  
  # Run Dr. Fei 3-act demo
  osiris demo --fab
  
  # Run physics bridges
  osiris bridges --output results.json
  
  # Launch 9-agent swarm
  osiris swarm --task "optimize torsion field solver"
  
  # Adversarial bridge validation
  osiris validate --trials 500 --output validation.json
  
  # ELO tournament against industry competitors
  osiris tournament --rounds 10 --output tournament.json
  
  # Cognitive mesh dashboard with simulated rounds
  osiris mesh --simulate 20
  
  # Introspection engine with simulated rounds
  osiris introspect --simulate 15 --output introspection.json
  
  # Full tridirectional feedback loop
  osiris feedback --task "optimize torsion field solver" --rounds 5
  
  # Check system status
  osiris status
"""
    print(help_text)

def cmd_forge(args):
    """Launch Quantum-to-Matter Manufacturing Forge"""
    from osiris_forge import OsirisForge, ForgeJob, PrinterHardware

    forge = OsirisForge()

    action = getattr(args, 'forge_action', 'report')

    if action == 'generate':
        job = ForgeJob(
            geometry=getattr(args, 'geometry', 'tetrahedral_lattice'),
            scale_cm=getattr(args, 'scale', 10.0),
            output_format=getattr(args, 'format', 'stl'),
            target_printer=PrinterHardware(getattr(args, 'printer', 'bambu_p1s')),
            slice_gcode=False,
        )
        path = forge.generate(job)
        if path:
            print(f"\n\u2713 Model generated: {path}")
        else:
            print("\n\u2717 Generation failed")
    elif action == 'pipeline':
        job = ForgeJob(
            geometry=getattr(args, 'geometry', 'tetrahedral_lattice'),
            scale_cm=getattr(args, 'scale', 10.0),
            target_printer=PrinterHardware(getattr(args, 'printer', 'bambu_p1s')),
            infill_percent=getattr(args, 'infill', 20),
            infill_pattern=getattr(args, 'pattern', 'gyroid'),
            auto_send=getattr(args, 'send', False),
            export_flash=getattr(args, 'flash', False),
            printer_ip=getattr(args, 'ip', ''),
            printer_serial=getattr(args, 'serial', ''),
            access_code=getattr(args, 'code', ''),
        )
        result = forge.run(job)
        sym = '\u2713' if result.success else '\u2717'
        print(f"\n{sym} {result.message}")
        if result.model_path:
            print(f"  Model:  {result.model_path}")
        if result.gcode_path:
            print(f"  G-code: {result.gcode_path}")
        print(f"  Steps:  {' -> '.join(result.steps_completed)}")
    elif action == 'discover':
        print("\n\u269b Scanning local network for 3D printers...\n")
        printers = forge.discover_printers()
        if printers:
            for p in printers:
                print(f"  {p['name']} ({p['type']}) @ {p['ip']}:{p['port']} [{p['protocol']}]")
        else:
            print("  No printers found.")
    elif action == 'status':
        job = ForgeJob(
            target_printer=PrinterHardware(getattr(args, 'printer', 'bambu_p1s')),
            printer_ip=getattr(args, 'ip', ''),
            printer_serial=getattr(args, 'serial', ''),
            access_code=getattr(args, 'code', ''),
        )
        status = forge.get_printer_status(job)
        print(f"\n\u269b Printer Status: {status.get('status', 'unknown')}")
        for k, v in status.items():
            if k != 'raw':
                print(f"  {k}: {v}")
    elif action == 'calibrate':
        job = ForgeJob(
            target_printer=PrinterHardware(getattr(args, 'printer', 'bambu_p1s')),
            printer_ip=getattr(args, 'ip', ''),
            printer_serial=getattr(args, 'serial', ''),
            access_code=getattr(args, 'code', ''),
        )
        result = forge.calibrate_printer(job)
        cal_ok = result.get('success', False)
        print(f"\n\u269b Calibration: {'Complete' if cal_ok else 'Failed'}")
        if result.get('message'):
            print(result['message'])
    elif action == 'multicolor':
        print("\n\u269b Running multi-color CANVAS pipeline...\n")
        design = getattr(args, 'design', 'shannon_map')
        scale = getattr(args, 'scale', 10.0)
        ip = getattr(args, 'ip', '')
        result = forge.forge_multicolor(design=design, scale_cm=scale, printer_ip=ip)
        sym = '\u2713' if result.get('success', False) else '\u2717'
        print(f"{sym} Multi-color pipeline: {result.get('message', 'done')}")
    elif action == 'telemetry':
        from osiris_feedback_bus import FeedbackBus, PrinterTelemetryRelay
        bus = FeedbackBus()
        relay = PrinterTelemetryRelay(bus)
        printer_type = getattr(args, 'printer', 'bambu_p1s')
        ip = getattr(args, 'ip', '')
        serial = getattr(args, 'serial', '')
        code = getattr(args, 'code', '')
        print(f"\n\u269b Polling telemetry from {printer_type} @ {ip}...\n")
        status = relay.poll_printer(printer_type, ip, serial=serial, access_code=code)
        state = status.get('state', 'unknown')
        print(f"  State: {state}")
        for k, v in status.items():
            if k != 'state':
                print(f"  {k}: {v}")
        bus.print_status()
    else:
        print(forge.status_report())

    forge.cleanup()


def cmd_license(args):
    """Run license compliance check"""
    from osiris_license import ComplianceGate, EnvironmentDetector, LicenseValidator
    
    if hasattr(args, 'validate') and args.validate:
        valid, msg = LicenseValidator.validate(args.validate)
        print(f"{'✓' if valid else '✗'} {msg}")
        return
    
    detector = EnvironmentDetector()
    sig = detector.detect()
    
    print(f"\n{'='*50}")
    print(f"  OSIRIS License Compliance")
    print(f"{'='*50}")
    print(f"  Environment:  {sig.domain_class}")
    print(f"  License Key:  {'Present' if sig.license_key_present else 'Not found'}")
    print(f"  Compliant:    {'✓ Yes' if sig.compliant else '✗ No'}")
    print(f"  Indicators:   {len(sig.domain_indicators)} found")
    for ind in sig.domain_indicators:
        print(f"    - {ind}")
    print(f"{'='*50}\n")


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='⚛ OSIRIS Quantum Discovery System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Chat command
    subparsers.add_parser('chat', help='Launch chat interface')
    
    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Run benchmarking')
    bench_parser.add_argument('--output', default='quantum_benchmark_results.json', help='Output file')
    bench_parser.add_argument('--quick', action='store_true', help='Quick mode (fewer tests)')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run experiment campaign')
    run_parser.add_argument('--campaign', default='week1_foundation', 
                           choices=['week1_foundation', 'week1_adaptive'],
                           help='Campaign to run')
    
    # Orchestrator command
    orchestrator_parser = subparsers.add_parser('orchestrate', help='Run full OSIRIS orchestrator pipeline')
    orchestrator_parser.add_argument('--quick', action='store_true', help='Quick mode (skip publication)')

    # Intent command
    intent_parser = subparsers.add_parser('intent', help='Route natural language into OSIRIS commands')
    intent_parser.add_argument('--text', required=True, help='Natural language instruction')
    intent_parser.add_argument('--no-llm', action='store_true', help='Disable LLM fallback for intent routing')

    # Publish command
    publish_parser = subparsers.add_parser('publish', help='Publish results to Zenodo')
    publish_parser.add_argument('--mode', default='all', choices=['rqc', 'applications', 'all'],
                                help='Publish RQC results, application results, or both')
    publish_parser.add_argument('--sandbox', action='store_true', help='Use Zenodo sandbox endpoint')

    # Status command
    subparsers.add_parser('status', help='Show system status')

    # Forge command
    forge_parser = subparsers.add_parser('forge', help='Quantum-to-Matter manufacturing pipeline')
    forge_subs = forge_parser.add_subparsers(dest='forge_action', help='Forge action')

    forge_gen = forge_subs.add_parser('generate', help='Generate 3D mesh')
    forge_gen.add_argument('--geometry', default='tetrahedral_lattice',
                           choices=['tetrahedral_lattice', 'toroidal_manifold',
                                    'planck_reference_cube', 'acoustic_resonance_cavity',
                                    'quaternion_orbit_model', 'torsion_lock_visualizer',
                                    'gyroscopic_spinner'])
    forge_gen.add_argument('--scale', type=float, default=10.0, help='Scale in cm')
    forge_gen.add_argument('--format', default='stl', choices=['3mf', 'stl', 'both'])
    forge_gen.add_argument('--printer', default='bambu_p1s',
                           choices=['bambu_p1s', 'bambu_a1_mini', 'elegoo_centauri_2',
                                    'generic_fdm', 'generic_resin'])
    forge_gen.add_argument('--rings', type=int, default=3, help='Gyroscope gimbal ring count')
    forge_gen.add_argument('--bearings', type=int, default=8, help='Bearings per ring gap')

    forge_pipe = forge_subs.add_parser('pipeline', help='Full: generate + slice + send')
    forge_pipe.add_argument('--geometry', default='tetrahedral_lattice',
                            choices=['tetrahedral_lattice', 'toroidal_manifold',
                                     'planck_reference_cube', 'acoustic_resonance_cavity',
                                     'quaternion_orbit_model', 'torsion_lock_visualizer',
                                     'gyroscopic_spinner'])
    forge_pipe.add_argument('--scale', type=float, default=10.0)
    forge_pipe.add_argument('--printer', default='bambu_p1s',
                            choices=['bambu_p1s', 'bambu_a1_mini', 'elegoo_centauri_2'])
    forge_pipe.add_argument('--ip', type=str, default='', help='Printer IP address')
    forge_pipe.add_argument('--serial', type=str, default='', help='Bambu serial number')
    forge_pipe.add_argument('--code', type=str, default='', help='Bambu LAN access code')
    forge_pipe.add_argument('--infill', type=int, default=20, help='Infill percent')
    forge_pipe.add_argument('--pattern', default='gyroid')
    forge_pipe.add_argument('--send', action='store_true', help='Auto-send to printer')
    forge_pipe.add_argument('--flash', action='store_true', help='Export to USB flash drive')

    forge_subs.add_parser('discover', help='Scan network for 3D printers')

    forge_stat = forge_subs.add_parser('status', help='Check printer status')
    forge_stat.add_argument('--printer', default='bambu_p1s')
    forge_stat.add_argument('--ip', type=str, required=True)
    forge_stat.add_argument('--serial', type=str, default='')
    forge_stat.add_argument('--code', type=str, default='')

    forge_cal = forge_subs.add_parser('calibrate', help='Run printer calibration')
    forge_cal.add_argument('--printer', default='bambu_p1s')
    forge_cal.add_argument('--ip', type=str, required=True)
    forge_cal.add_argument('--serial', type=str, default='')
    forge_cal.add_argument('--code', type=str, default='')

    forge_subs.add_parser('report', help='Show forge status report')

    forge_telem = forge_subs.add_parser('telemetry', help='Poll printer telemetry into feedback bus')
    forge_telem.add_argument('--printer', default='bambu_p1s',
                             choices=['bambu_p1s', 'bambu_a1_mini', 'moonraker',
                                      'elegoo_centauri_2'])
    forge_telem.add_argument('--ip', type=str, required=True, help='Printer IP address')
    forge_telem.add_argument('--serial', type=str, default='')
    forge_telem.add_argument('--code', type=str, default='')

    # FABRIC command
    fabric_parser = subparsers.add_parser('fabric', help='FABRIC Living Slice provisioner')
    fabric_parser.add_argument('--sites', nargs='+', default=['UKY', 'NCSA', 'TACC'],
                               help='FABRIC sites (e.g., UKY NCSA TACC CERN TOKYO)')
    fabric_parser.add_argument('--topology', default='star',
                               choices=['star', 'mesh', 'linear', 'toroidal'],
                               help='Slice topology pattern')
    fabric_parser.add_argument('--cycles', type=int, default=10, help='Telemetry cycles')

    # Policy command
    policy_parser = subparsers.add_parser('policy', help='POLANCO policy upcycler')
    policy_parser.add_argument('--source', default='campus',
                               choices=['campus', 'natural'],
                               help="Policy source: 'campus' (POLANCO) or 'natural' (NPCE)")
    policy_parser.add_argument('--cycles', type=int, default=20, help='Enforcement simulation cycles')
    policy_parser.add_argument('--file', type=str, default='',
                               help='Path to custom POLANCO policy file')

    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Dr. Fei 3-act demonstration')
    demo_parser.add_argument('--act', type=int, nargs='+', default=None,
                             help='Which acts to run (1, 2, 3)')
    demo_parser.add_argument('--fab', action='store_true',
                             help='Include FABRIC Across Borders (CERN, TOKYO)')
    demo_parser.add_argument('--live', action='store_true',
                             help='Use live FABRIC API (requires credentials)')

    # Bridges command
    bridges_parser = subparsers.add_parser('bridges', help='Run CRSM physics bridges')
    bridges_parser.add_argument('--output', type=str, default='', help='Save results to JSON file')

    # Swarm command
    swarm_parser = subparsers.add_parser('swarm', help='Run NCLLM 9-agent swarm')
    swarm_parser.add_argument('--task', type=str, required=True, help='Task for swarm deliberation')
    swarm_parser.add_argument('--rounds', type=int, default=3, help='Max deliberation rounds')
    swarm_parser.add_argument('--output', type=str, default='', help='Save results to JSON file')

    # Forge multicolor subcommand
    forge_multi = forge_subs.add_parser('multicolor', help='Multi-color CANVAS pipeline')
    forge_multi.add_argument('--design', default='shannon_map',
                             choices=['shannon_map', 'torsion_gradient', 'bridge_report'])
    forge_multi.add_argument('--scale', type=float, default=10.0)
    forge_multi.add_argument('--ip', type=str, default='', help='CC2 printer IP')

    # License command
    license_parser = subparsers.add_parser('license', help='License compliance check')
    license_parser.add_argument('--validate', type=str, help='Validate a license key')

    # Validate command (adversarial bridge validator)
    validate_parser = subparsers.add_parser('validate', help='Adversarial bridge validation')
    validate_parser.add_argument('--trials', type=int, default=500, help='Monte Carlo trials')
    validate_parser.add_argument('--sigma', type=int, default=3, help='Sensitivity perturbation sigma')
    validate_parser.add_argument('--output', type=str, default='', help='Save validation report to JSON')

    # Tournament command (ELO benchmark)
    tournament_parser = subparsers.add_parser('tournament', help='ELO tournament benchmark')
    tournament_parser.add_argument('--rounds', type=int, default=10, help='Rounds per matchup')
    tournament_parser.add_argument('--output', type=str, default='', help='Save tournament results to JSON')

    # Mesh command (cognitive mesh dashboard)
    mesh_parser = subparsers.add_parser('mesh', help='Cognitive mesh dashboard')
    mesh_parser.add_argument('--simulate', type=int, default=0,
                             help='Run N simulated rounds to populate mesh state')
    mesh_parser.add_argument('--output', type=str, default='', help='Save mesh report to JSON')

    # Introspect command (tridirectional self-awareness dashboard)
    introspect_parser = subparsers.add_parser('introspect',
                                               help='Introspection engine dashboard')
    introspect_parser.add_argument('--simulate', type=int, default=0,
                                    help='Run N simulated rounds to populate introspection state')
    introspect_parser.add_argument('--output', type=str, default='',
                                    help='Save introspection report to JSON')

    # Feedback command (full tridirectional intelligence loop)
    feedback_parser = subparsers.add_parser('feedback',
                                             help='Tridirectional feedback loop (swarm+intent+bus)')
    feedback_parser.add_argument('--task', type=str, required=True,
                                  help='Task for tridirectional intelligence loop')
    feedback_parser.add_argument('--rounds', type=int, default=5,
                                  help='Max deliberation rounds')
    feedback_parser.add_argument('--output', type=str, default='',
                                  help='Save feedback results to JSON')

    # LivLM — Living Language Model
    livlm_parser = subparsers.add_parser('livlm',
                                          help='Living Language Model — evolve and generate text')
    livlm_parser.add_argument('--prompt', type=str, default='# ',
                               help='Seed text for generation')
    livlm_parser.add_argument('--length', type=int, default=64,
                               help='Characters to generate')
    livlm_parser.add_argument('--generations', type=int, default=12,
                               help='Evolution generations')
    livlm_parser.add_argument('--population', type=int, default=20,
                               help='Genetic population size')
    livlm_parser.add_argument('--layers', type=int, default=2,
                               help='Circuit depth (rotation layers)')
    livlm_parser.add_argument('--demo', action='store_true',
                               help='Run quick demo')
    livlm_parser.add_argument('--save', type=str, default='',
                               help='Save evolved genome to file')
    livlm_parser.add_argument('--load', type=str, default='',
                               help='Load genome from file')

    # Ollama — Local LLM engine
    ollama_parser = subparsers.add_parser('ollama',
                                           help='Ollama local LLM — status, chat, model management')
    ollama_parser.add_argument('--status', action='store_true',
                                help='Show Ollama status and available models')
    ollama_parser.add_argument('--chat', type=str, default='',
                                help='Send a message to Ollama')
    ollama_parser.add_argument('--pull', type=str, default='',
                                help='Pull a model (e.g., qwen2.5:1.5b)')
    ollama_parser.add_argument('--model', type=str, default='',
                                help='Select a specific model')

    # NCLM — Non-Causal Living Model
    nclm_parser = subparsers.add_parser('nclm', help='NCLM Non-Causal Living Model')
    nclm_parser.add_argument('--evolve', action='store_true', help='Evolve circuit parameters via genetic algorithm')
    nclm_parser.add_argument('--generate', action='store_true', help='Generate text from evolved genome')
    nclm_parser.add_argument('--chat', action='store_true', help='Interactive NCLM chat REPL')
    nclm_parser.add_argument('--benchmark', action='store_true', help='Run NCLM benchmark suite')
    nclm_parser.add_argument('--status', dest='nclm_status', action='store_true', help='Show NCLM model status')
    nclm_parser.add_argument('--seed', type=str, default='', help='Seed text for generation/evolution')
    nclm_parser.add_argument('--length', type=int, default=0, help='Generation length in characters')
    nclm_parser.add_argument('--temperature', type=float, default=0.85, help='Generation temperature (0.1-2.0)')
    nclm_parser.add_argument('--generations', type=int, default=0, help='Evolution generations')
    nclm_parser.add_argument('--population', type=int, default=0, help='Evolution population size')
    nclm_parser.add_argument('--layers', type=int, default=0, help='Circuit depth (rotation layers)')
    nclm_parser.add_argument('--genome', default='nclm_genome.json', help='Genome file path')
    nclm_parser.add_argument('--output', type=str, default='', help='Output file')
    nclm_parser.add_argument('--json', dest='json_output', action='store_true', help='JSON output')

    # QVM — Local Quantum Virtual Machine
    qvm_parser = subparsers.add_parser('qvm', help='Local Quantum Virtual Machine')
    qvm_parser.add_argument('--qubits', type=int, default=4, help='Number of qubits (default: 4)')
    qvm_parser.add_argument('--depth', type=int, default=8, help='Circuit depth (default: 8)')
    qvm_parser.add_argument('--mode', default='benchmark',
                            choices=['benchmark', 'rqc_vs_rcs', 'single', 'status'],
                            help='Execution mode')
    qvm_parser.add_argument('--output', type=str, default='', help='Save results to JSON file')

    # Discover — Exotic Physics Discovery Engine
    disc_parser = subparsers.add_parser('discover', help='Exotic physics discovery engine')
    disc_parser.add_argument('--iterations', type=int, default=5, help='Refinement iterations (default: 5)')
    disc_parser.add_argument('--points', type=int, default=10, help='Points per iteration (default: 10)')
    disc_parser.add_argument('--threshold', type=float, default=3.0, help='Significance threshold σ (default: 3.0)')
    disc_parser.add_argument('--seed', type=int, default=42, help='Random seed')
    disc_parser.add_argument('--no-swarm', dest='no_swarm', action='store_true', help='Disable swarm analysis')
    disc_parser.add_argument('--quiet', action='store_true', help='Suppress progress output')
    disc_parser.add_argument('--output', type=str, default='', help='Save report to JSON file')

    # Health — System diagnostic
    health_parser = subparsers.add_parser('health', help='System health diagnostic')
    health_parser.add_argument('--quiet', action='store_true', help='Suppress per-check output')
    health_parser.add_argument('--output', type=str, default='', help='Save report to JSON file')

    # Translate — Cross-backend organism translation
    translate_parser = subparsers.add_parser('translate', help='Translate organism across backends')
    translate_parser.add_argument('source', type=str, help='Path to .dna source file')
    translate_parser.add_argument('--from', dest='source_backend', default='sovereign',
                                  choices=['sovereign', 'qiskit', 'cirq', 'pyquil'],
                                  help='Source backend representation')
    translate_parser.add_argument('--to', dest='target_backend', default='qiskit',
                                  choices=['sovereign', 'qiskit', 'cirq', 'pyquil'],
                                  help='Target backend representation')
    translate_parser.add_argument('--format', default='qasm', choices=['qasm', 'json'],
                                  help='Export format')
    translate_parser.add_argument('--output', type=str, default='',
                                  help='Output file path (prints to stdout if omitted)')
    translate_parser.add_argument('--strict', action='store_true',
                                  help='Fail translation when possible semantic loss is detected')
    translate_parser.add_argument('--report', action='store_true',
                                  help='Print translation quality report in summary output')
    translate_parser.add_argument('--report-file', type=str, default='',
                                  help='Write translation quality report JSON to file')

    # Ultra-Coder — 9-agent coding swarm
    uc_parser = subparsers.add_parser('ultra-coder', help='NCLLM Ultra-Coder 9-agent swarm')
    uc_parser.add_argument('--task', type=str, default='', help='Coding task to solve')
    uc_parser.add_argument('--file', type=str, default='', help='File context for the task')
    uc_parser.add_argument('--interactive', action='store_true', help='Interactive REPL mode')
    uc_parser.add_argument('--user', default='cli', help='User ID for personalization')
    uc_parser.add_argument('--self-edit', dest='self_edit', type=str, default='', help='Natural language self-edit request')
    uc_parser.add_argument('--coach', action='store_true', help='Get self-improvement suggestions')
    uc_parser.add_argument('--json', dest='json_output', action='store_true', help='JSON output')

    # If no command, launch interactive shell
    if len(sys.argv) == 1:
        from osiris_shell import main as shell_main
        shell_main()
        return
    else:
        args = parser.parse_args()
    
    # Check environment
    check_environment()
    
    # Run license compliance gate
    try:
        from osiris_license import ComplianceGate
        compliant, msg = ComplianceGate.check(strict=False)
        if not compliant:
            print(msg)
    except ImportError:
        pass  # License module not available — skip check
    
    # Execute command
    if args.command == 'chat':
        cmd_chat(args)
    elif args.command == 'benchmark':
        cmd_benchmark(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'publish':
        cmd_publish(args)
    elif args.command == 'orchestrate':
        cmd_orchestrate(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'intent':
        cmd_intent(args)
    elif args.command == 'forge':
        cmd_forge(args)
    elif args.command == 'bridges':
        cmd_bridges(args)
    elif args.command == 'swarm':
        cmd_swarm(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'tournament':
        cmd_tournament(args)
    elif args.command == 'mesh':
        cmd_mesh(args)
    elif args.command == 'introspect':
        cmd_introspect(args)
    elif args.command == 'feedback':
        cmd_feedback(args)
    elif args.command == 'livlm':
        cmd_livlm(args)
    elif args.command == 'ollama':
        cmd_ollama(args)
    elif args.command == 'fabric':
        cmd_fabric(args)
    elif args.command == 'policy':
        cmd_policy(args)
    elif args.command == 'demo':
        cmd_demo(args)
    elif args.command == 'license':
        cmd_license(args)
    elif args.command == 'nclm':
        cmd_nclm(args)
    elif args.command == 'ultra-coder':
        cmd_ultra_coder(args)
    elif args.command == 'qvm':
        cmd_qvm(args)
    elif args.command == 'health':
        cmd_health(args)
    elif args.command == 'translate':
        cmd_translate(args)
    elif args.command == 'discover':
        cmd_discover(args)
    elif args.command == 'help':
        cmd_help(args)
    else:
        # Default to chat
        cmd_chat(args)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚛ OSIRIS shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
