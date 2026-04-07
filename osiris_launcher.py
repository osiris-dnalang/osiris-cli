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
    
    from osiris_tui_core import run_cli_mode
    asyncio.run(run_cli_mode())

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
        print(f"\n  → {exp.name}")
        result = pipeline.run_hypothesis_test(exp.config)
        results.append(result)
        print(f"    p={result.get('p_value', 'N/A'):.6f}")
    
    print(f"\n✓ Campaign complete! {len(results)} experiments executed")

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
    }
    
    for key, value in status_info.items():
        print(f"  {key:20s}: {value}")
    
    print("\n" + "="*70)

def cmd_help(args):
    """Show help"""
    help_text = """
⚛ OSIRIS QUANTUM DISCOVERY SYSTEM

Commands:
  
  chat              Launch chat-native TUI interface
  benchmark         Run quantum hardware benchmarking suite
  run               Execute experiment campaign
  status            Show system status
  help              Show this help

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
  
  # Check system status
  osiris status
"""
    print(help_text)

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
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Help command
    subparsers.add_parser('help', help='Show help')
    
    # If no command, default to chat
    if len(sys.argv) == 1:
        args = parser.parse_args(['chat'])
    else:
        args = parser.parse_args()
    
    # Check environment
    check_environment()
    
    # Execute command
    if args.command == 'chat':
        cmd_chat(args)
    elif args.command == 'benchmark':
        cmd_benchmark(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'status':
        cmd_status(args)
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
