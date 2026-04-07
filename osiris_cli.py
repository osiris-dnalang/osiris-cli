#!/usr/bin/env python3
"""
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
        
        status = "✓" if sig else "✗"
        logger.info(f"{status} {result.get('name')}: p={p_val:.2e}")
    
    logger.info(f"\nSignificant Results: {significant}/{len(result_files)}")
    logger.info("="*70 + "\n")
    
    return 0


def main():
    """CLI entry point"""
    
    # Setup
    ibm_token, zenodo_token = setup_environment()
    
    # Parser
    parser = argparse.ArgumentParser(
        description="OSIRIS Automated Quantum Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python osiris_cli.py run --campaign week1_foundation
  python osiris_cli.py list --templates
  python osiris_cli.py status --results-dir ./discoveries
  python osiris_cli.py publish --dry-run
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
