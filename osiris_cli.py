#!/usr/bin/env python3
"""
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> CLI ENTRY POINT                                         |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+

OSIRIS Automated Discovery - Command Line Interface
====================================================

Usage:
  
  # Run week-1 campaign
  python osiris_cli.py run --campaign week1_foundation
  
  # List available experiments
  python osiris_cli.py list --templates
  
  # Run single experiment
  python osiris_cli.py run --experiment xeb_baseline_12q
  
  # Publish results
  python osiris_cli.py publish --results-dir ./discoveries --dry-run

  # Ultra-Coder: solve a coding task
  python osiris_cli.py ultra-coder --task "implement quicksort"

  # Ultra-Coder: interactive mode
  python osiris_cli.py ultra-coder --interactive

  # Benchmark suite
  python osiris_cli.py benchmark --full --compare

  # NCLM: evolve circuit parameters
  python osiris_cli.py nclm --evolve --generations 50

  # NCLM: generate text from evolved genome
  python osiris_cli.py nclm --generate --seed "# Hello" --length 100

  # NCLM: interactive chat
  python osiris_cli.py nclm --chat

  # NCLM: benchmark suite
  python osiris_cli.py nclm --benchmark
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger('OSIRIS_CLI')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def setup_environment():
    """Check and display environment setup"""
    
    ibm_token = bool(os.getenv('IBM_QUANTUM_TOKEN'))
    zenodo_token = bool(os.getenv('ZENODO_TOKEN'))
    
    logger.info("\n" + "="*70)
    logger.info("OSIRIS AUTOMATED DISCOVERY - ENVIRONMENT CHECK")
    logger.info("="*70)
    logger.info(f"IBM Quantum Token:  {'✓' if ibm_token else '✗'} {('SET' if ibm_token else 'NOT SET')}")
    logger.info(f"Zenodo Token:       {'✓' if zenodo_token else '✗'} {('SET' if zenodo_token else 'NOT SET')}")
    logger.info(f"Backend:            {os.getenv('IBM_BACKEND', 'ibm_torino (default)')}")
    logger.info("="*70 + "\n")
    
    if not ibm_token:
        logger.warning("⚠ IBM_QUANTUM_TOKEN not set - will use mock execution")
    
    return ibm_token, zenodo_token


def cmd_run(args):
    """Run experiment or campaign"""
    
    from osiris_auto_discovery import AutoDiscoveryPipeline, ExperimentConfig
    from osiris_orchestrator import (
        campaign_week1_foundation, 
        campaign_week1_adaptive,
        WorkflowScheduler
    )
    
    api_token = os.getenv('IBM_QUANTUM_TOKEN', 'mock')
    pipeline = AutoDiscoveryPipeline(api_token, output_dir=args.output_dir)
    
    if args.campaign:
        # Run named campaign
        logger.info(f"\n➜ Running campaign: {args.campaign}\n")
        
        scheduler = WorkflowScheduler(pipeline)
        
        if args.campaign == 'week1_foundation':
            scheduler.add_campaign(campaign_week1_foundation())
        elif args.campaign == 'week1_adaptive':
            scheduler.add_campaign(campaign_week1_adaptive())
        else:
            logger.error(f"Unknown campaign: {args.campaign}")
            return 1
        
        scheduler.run_all_campaigns()
        
    elif args.experiment:
        # Run single experiment config
        logger.info(f"\n➜ Running experiment: {args.experiment}\n")
        
        # Parse experiment config
        if args.config:
            with open(args.config) as f:
                exp_dict = json.load(f)
        else:
            logger.error("--config required for single experiment")
            return 1
        
        config = ExperimentConfig(**exp_dict)
        result = pipeline.run_hypothesis_test(config)
        pipeline.save_result(result)
        
        report = pipeline.generate_report(result)
        logger.info(f"\n{report}")
    
    else:
        logger.error("Specify --campaign or --experiment")
        return 1
    
    return 0


def cmd_list(args):
    """List available templates and campaigns"""
    
    from osiris_orchestrator import ExperimentTemplates
    
    logger.info("\n" + "="*70)
    logger.info("AVAILABLE TEMPLATES")
    logger.info("="*70)
    
    templates = {
        'xeb_vs_depth': ExperimentTemplates.xeb_vs_depth(),
        'entropy_saturation': ExperimentTemplates.entropy_saturation(),
        'noise_robustness': ExperimentTemplates.noise_robustness(),
    }
    
    for name, config in templates.items():
        logger.info(f"\n{name}:")
        logger.info(f"  Hypothesis: {config.get('hypothesis')}")
        logger.info(f"  Qubits: {config.get('n_qubits')}")
        logger.info(f"  Depth: {config.get('circuit_depth')}")
        logger.info(f"  Trials: {config.get('trials')}")
    
    logger.info("\n" + "="*70)
    logger.info("AVAILABLE CAMPAIGNS")
    logger.info("="*70)
    logger.info("\nweek1_foundation - Baseline measurements (XEB, entropy, noise)")
    logger.info("week1_adaptive   - Adaptive circuit hypothesis (RQC vs RCS)")
    
    logger.info("\n" + "="*70 + "\n")
    return 0


def cmd_publish(args):
    """Publish results to Zenodo"""
    
    from osiris_zenodo_publisher import PublishingWorkflow, ResultPackager
    
    zenodo_token = os.getenv('ZENODO_TOKEN')
    
    if not zenodo_token and not args.dry_run:
        logger.error("ZENODO_TOKEN not set")
        return 1
    
    # Initialize workflow
    workflow = PublishingWorkflow(zenodo_token or 'mock', use_sandbox=True)
    
    # Find results
    results_dir = Path(args.results_dir)
    result_files = list(results_dir.glob('*_*.json'))
    
    if not result_files:
        logger.warning(f"No results found in {results_dir}")
        return 1
    
    logger.info(f"\nFound {len(result_files)} results")
    
    # TODO: Load results and publish
    logger.info("(Publishing workflow not yet fully implemented)")
    
    return 0


def cmd_status(args):
    """Check discovery status and recent results"""
    
    results_dir = Path(args.results_dir)
    
    logger.info("\n" + "="*70)
    logger.info("DISCOVERY STATUS")
    logger.info("="*70 + "\n")
    
    result_files = list(results_dir.glob('*_*.json'))
    
    if not result_files:
        logger.info("No results yet. Run experiments with: osiris_cli.py run")
        return 0
    
    logger.info(f"Total Results: {len(result_files)}\n")
    
    # Load and summarize
    significant = 0
    total_p_value = 0
    
    for f in sorted(result_files)[-10:]:  # Last 10
        with open(f) as fp:
            result = json.load(fp)
        
        sig = result.get('passes_significance', False)
        p_val = result.get('p_value', 0)
        
        if sig:
            significant += 1
        
        total_p_value += p_val
        
        status = "[+]" if sig else "[-]"
        logger.info(f"{status} {result.get('name')}: p={p_val:.2e}")
    
    logger.info(f"\nSignificant Results: {significant}/{len(result_files)}")
    logger.info("="*70 + "\n")
    
    return 0


def cmd_ultra_coder(args):
    """Run the NCLLM Ultra-Coder swarm"""
    import asyncio
    from osiris_ultra_coder import UltraCoderSwarm, NCLLMPersonality, NLPSelfEditor, SelfImprovementCoach

    personality = NCLLMPersonality()
    swarm = UltraCoderSwarm(personality=personality, user_id=args.user or "cli")

    if args.self_edit:
        editor = NLPSelfEditor(personality)
        result = editor.process_edit_request(args.self_edit)
        if result["applied"]:
            logger.info(f"Applied edit: {result['modifications']}")
        else:
            logger.info(f"Edit rejected: {result.get('error', 'unknown')}")
        return 0

    if args.coach:
        coach = SelfImprovementCoach(personality)
        suggestions = coach.generate_suggestions()
        for s in suggestions:
            logger.info(f"  [{s['priority']}] {s['area']}: {s['suggestion']}")
        return 0

    if args.interactive:
        asyncio.run(_interactive_ultra_coder(swarm, personality))
        return 0

    if args.task:
        result = asyncio.run(swarm.solve(args.task, context=args.file or ""))
        if args.json_output:
            print(json.dumps({"solution": result}, indent=2))
        else:
            print(result)
        return 0

    logger.error("Specify --task, --interactive, --self-edit, or --coach")
    return 1


async def _interactive_ultra_coder(swarm, personality):
    """Interactive Ultra-Coder REPL"""
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
            from osiris_ultra_coder import NLPSelfEditor
            editor = NLPSelfEditor(personality)
            result = editor.process_edit_request(task[5:])
            print(f"  Result: {result}")
            continue
        if task.lower() == "coach":
            from osiris_ultra_coder import SelfImprovementCoach
            coach = SelfImprovementCoach(personality)
            for s in coach.generate_suggestions():
                print(f"  [{s['priority']}] {s['area']}: {s['suggestion']}")
            continue

        result = await swarm.solve(task)
        print(result)
        print()


def cmd_nclm(args):
    """Run the NCLM (Non-Causal Living Model) module"""
    from nclm.core.qbyte_generator import QByteTextGenerator
    from nclm.benchmark.harness import NCLMBenchmark
    from osiris_livlm import LivLMConfig

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
        if args.json_output:
            print(json.dumps(results, indent=2, default=str))
        if args.output:
            bench.save_results(results, args.output)
            logger.info(f"Results saved to {args.output}")
        return 0

    # Create generator
    config = LivLMConfig(
        max_generations=args.generations or 50,
        population_size=args.population or 30,
        n_layers=args.layers or 3,
    )
    gen = QByteTextGenerator(config=config, genome_path=args.genome)

    if args.evolve:
        print("\n  NCLM Evolution")
        print("  " + "-" * 40)
        gen.load_corpus()
        result = gen.evolve(
            seed_text=args.seed or "# ",
            verbose=True,
        )
        gen.save_genome()
        print(f"\n  Evolution complete:")
        print(f"    Generations: {result['generations']}")
        print(f"    Best Ξ:      {result['best_fitness']:.6f}")
        print(f"    Best Φ:      {result['best_phi']:.6f}")
        print(f"    State:       {result['consciousness_state']}")
        print(f"    Genome:      {gen._genome_path}")
        if args.json_output:
            print(json.dumps(result, indent=2, default=str))
        return 0

    if args.generate:
        seed = args.seed or "# "
        length = args.length or 64
        # Try to load existing genome
        if not gen.auto_load():
            print("  No evolved genome found — evolving first...")
            gen.load_corpus()
            gen.evolve(seed_text=seed, verbose=True)
            gen.save_genome()

        text = gen.generate(prompt=seed, max_length=length,
                            temperature=args.temperature)
        print(f"\n  Seed: {seed!r}")
        print(f"  Generated ({length} chars):\n")
        print(text)
        if args.json_output:
            print(json.dumps({
                'seed': seed, 'length': length,
                'output': text, 'metrics': gen._last_metrics,
            }, indent=2))
        return 0

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
        return 0

    if args.status:
        status = gen.status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        return 0

    logger.error("Specify --evolve, --generate, --chat, --benchmark, or --status")
    return 1


def cmd_benchmark(args):
    """Run the NCLLM benchmark suite"""
    import asyncio
    from osiris_benchmark_suite import BenchmarkRunner

    runner = BenchmarkRunner()

    if args.full:
        result = asyncio.run(runner.run_suite())
    elif args.category:
        result = asyncio.run(runner.run_suite(categories=[args.category]))
    else:
        result = asyncio.run(runner.run_suite())

    runner.print_results(result)

    if args.compare:
        runner.print_comparison_table(result)

    if args.json_output:
        summary = {
            "total": result.total_tasks,
            "passed": result.passed,
            "failed": result.failed,
            "avg_score": result.average_score,
            "categories": {
                cat: {"avg": scores.average_score if hasattr(scores, 'average_score') else 0}
                for cat, scores in result.category_results.items()
            }
        }
        print(json.dumps(summary, indent=2))

    return 0


def main():
    """CLI entry point"""
    
    # Setup
    ibm_token, zenodo_token = setup_environment()
    
    # Parser
    parser = argparse.ArgumentParser(
        description="OSIRIS Automated Quantum Discovery + NCLLM Ultra-Coder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python osiris_cli.py run --campaign week1_foundation
  python osiris_cli.py list --templates
  python osiris_cli.py status --results-dir ./discoveries
  python osiris_cli.py publish --dry-run
  python osiris_cli.py ultra-coder --task "implement quicksort in Python"
  python osiris_cli.py ultra-coder --interactive
  python osiris_cli.py ultra-coder --self-edit "increase creativity"
  python osiris_cli.py ultra-coder --coach
  python osiris_cli.py benchmark --full --compare
  python osiris_cli.py nclm --evolve --generations 50
  python osiris_cli.py nclm --generate --seed "# Hello" --length 100
  python osiris_cli.py nclm --chat
  python osiris_cli.py nclm --benchmark

co-authored by devin phillip davis and OSIRIS dna::}{::lang NCLM
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # RUN command
    run_parser = subparsers.add_parser('run', help='Run experiment or campaign')
    run_parser.add_argument('--campaign', help='Campaign name (week1_foundation, week1_adaptive)')
    run_parser.add_argument('--experiment', help='Single experiment name')
    run_parser.add_argument('--config', help='Experiment config JSON file')
    run_parser.add_argument('--output-dir', default='./discoveries', help='Output directory')
    run_parser.set_defaults(func=cmd_run)
    
    # LIST command
    list_parser = subparsers.add_parser('list', help='List templates and campaigns')
    list_parser.add_argument('--templates', action='store_true', help='Show templates')
    list_parser.set_defaults(func=cmd_list)
    
    # PUBLISH command
    pub_parser = subparsers.add_parser('publish', help='Publish to Zenodo')
    pub_parser.add_argument('--results-dir', default='./discoveries', help='Results directory')
    pub_parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual publish)')
    pub_parser.set_defaults(func=cmd_publish)
    
    # STATUS command
    status_parser = subparsers.add_parser('status', help='Check discovery status')
    status_parser.add_argument('--results-dir', default='./discoveries', help='Results directory')
    status_parser.set_defaults(func=cmd_status)
    
    # ULTRA-CODER command
    uc_parser = subparsers.add_parser('ultra-coder', help='NCLLM Ultra-Coder 9-agent swarm')
    uc_parser.add_argument('--task', help='Coding task to solve')
    uc_parser.add_argument('--file', help='File context for the task')
    uc_parser.add_argument('--interactive', action='store_true', help='Interactive REPL mode')
    uc_parser.add_argument('--user', default='cli', help='User ID for personalization')
    uc_parser.add_argument('--self-edit', help='Natural language self-edit request')
    uc_parser.add_argument('--coach', action='store_true', help='Get self-improvement suggestions')
    uc_parser.add_argument('--json', dest='json_output', action='store_true', help='JSON output')
    uc_parser.set_defaults(func=cmd_ultra_coder)

    # NCLM command
    nclm_parser = subparsers.add_parser('nclm', help='NCLM Non-Causal Living Model')
    nclm_parser.add_argument('--evolve', action='store_true', help='Evolve circuit parameters via genetic algorithm')
    nclm_parser.add_argument('--generate', action='store_true', help='Generate text from evolved genome')
    nclm_parser.add_argument('--chat', action='store_true', help='Interactive NCLM chat REPL')
    nclm_parser.add_argument('--benchmark', action='store_true', help='Run NCLM benchmark suite')
    nclm_parser.add_argument('--status', action='store_true', help='Show NCLM model status')
    nclm_parser.add_argument('--seed', help='Seed text for generation/evolution')
    nclm_parser.add_argument('--length', type=int, help='Generation length in characters')
    nclm_parser.add_argument('--temperature', type=float, help='Generation temperature (0.1-2.0)')
    nclm_parser.add_argument('--generations', type=int, help='Evolution generations')
    nclm_parser.add_argument('--population', type=int, help='Evolution population size')
    nclm_parser.add_argument('--layers', type=int, help='Circuit depth (number of rotation layers)')
    nclm_parser.add_argument('--genome', default='nclm_genome.json', help='Genome file path')
    nclm_parser.add_argument('--output', help='Output file for benchmark results')
    nclm_parser.add_argument('--json', dest='json_output', action='store_true', help='JSON output')
    nclm_parser.set_defaults(func=cmd_nclm)

    # BENCHMARK command
    bm_parser = subparsers.add_parser('benchmark', help='Run NCLLM benchmark suite')
    bm_parser.add_argument('--full', action='store_true', help='Run full benchmark suite')
    bm_parser.add_argument('--category', help='Run specific category')
    bm_parser.add_argument('--compare', action='store_true', help='Show comparison table')
    bm_parser.add_argument('--json', dest='json_output', action='store_true', help='JSON output')
    bm_parser.set_defaults(func=cmd_benchmark)
    
    # Parse
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
