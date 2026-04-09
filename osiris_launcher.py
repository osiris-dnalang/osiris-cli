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
    report = executor.run_all()
    print(f"  Propulsion Bridge:  p={report['propulsion']['bootstrap_p']:.4f}  "
          f"Poynting flux={report['propulsion']['integrated_flux']:.3e} W")
    print(f"  Energy Bridge:      modes={report['energy']['n_modes']}  "
          f"peak R_n={report['energy']['peak_spectral_deviation']:.8f}")
    print(f"  Cosmological Bridge: chi2_flat={report['cosmological']['chi2_flat']:.2f}  "
          f"chi2_crsm={report['cosmological']['chi2_crsm']:.2f}")
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


def cmd_swarm(args):
    """Run NCLLM 9-agent swarm"""
    print("\n⚛ Launching NCLLM 9-Agent Swarm...\n")
    from osiris_ncllm_swarm import NCLLMSwarm
    swarm = NCLLMSwarm()
    result = swarm.deliberate(args.task, max_rounds=args.rounds)
    print(f"  Consensus: {result.get('consensus', 'N/A')}")
    print(f"  Rounds:    {result.get('rounds', 0)}")
    print(f"  Quality:   {result.get('quality_score', 0):.3f}")
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


def cmd_help(args):
    """Show help"""
    help_text = """
⚛ OSIRIS QUANTUM DISCOVERY SYSTEM

Commands:
  
  chat              Launch chat-native TUI interface
  benchmark         Run quantum hardware benchmarking suite
  run               Execute experiment campaign
  orchestrate       Run full OSIRIS orchestrator pipeline
  publish           Publish results to Zenodo
  forge             Quantum-to-Matter manufacturing pipeline
  bridges           Run CRSM physics bridges (propulsion/energy/cosmological)
  swarm             Run NCLLM 9-agent swarm deliberation
  status            Show system status
  intent            Route natural language into OSIRIS commands
  help              Show this help

Forge (3D Manufacturing):
  osiris forge report                         Show forge status
  osiris forge generate --geometry X          Generate mesh from Torsion Core
  osiris forge discover                       Scan network for 3D printers
  osiris forge pipeline --printer bambu_p1s   Full generate+slice+send pipeline
  osiris forge pipeline --printer elegoo_cc2  Full pipeline for Elegoo CC2 / CANVAS
  osiris forge multicolor --design X          Multi-color CANVAS pipeline
  osiris forge calibrate --ip 192.168.1.X     Calibrate a connected printer
  osiris forge status --ip 192.168.1.X        Check printer status

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
  
  # Run physics bridges
  osiris bridges --output results.json
  
  # Launch 9-agent swarm
  osiris swarm --task "optimize torsion field solver"
  
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
                                    'quaternion_orbit_model', 'torsion_lock_visualizer'])
    forge_gen.add_argument('--scale', type=float, default=10.0, help='Scale in cm')
    forge_gen.add_argument('--format', default='stl', choices=['3mf', 'stl', 'both'])
    forge_gen.add_argument('--printer', default='bambu_p1s',
                           choices=['bambu_p1s', 'bambu_a1_mini', 'elegoo_centauri_2',
                                    'generic_fdm', 'generic_resin'])

    forge_pipe = forge_subs.add_parser('pipeline', help='Full: generate + slice + send')
    forge_pipe.add_argument('--geometry', default='tetrahedral_lattice')
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

    # If no command, default to chat
    if len(sys.argv) == 1:
        args = parser.parse_args(['chat'])
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
    elif args.command == 'license':
        cmd_license(args)
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
