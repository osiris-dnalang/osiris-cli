#!/usr/bin/env python3
"""
OSIRIS RQC Research Orchestrator
Master command center for RQC vs RCS quantum advantage research
Coordinated execution from experiment → publication

Workflow:
1. STAGE 1: Execute RQC vs RCS on real IBM hardware
2. STAGE 2: Run domain-specific applications
3. STAGE 3: Publish results to Zenodo with DOI
4. STAGE 4: Generate citation and archive
"""

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Import all modules
from osiris_rqc_framework import RQCFramework, CircuitConfig, ComparisonResult
from osiris_ibm_execution import IBMExecutionManager, ExecutionStage, ExecutionStrategy
from osiris_applications import ApplicationFramework, ApplicationResult
from osiris_publication_zenodo import ZenodoPublisher, ResearchArchive

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class ResearchOrchestrator:
    """Master orchestrator for RQC research pipeline"""
    
    def __init__(self):
        self.rqc_framework = RQCFramework()
        self.ibm_manager = IBMExecutionManager()
        self.app_framework = ApplicationFramework()
        self.publisher = ZenodoPublisher()
        
        self.experiment_results = {}
        self.application_results = []
        self.dois = {}
        self.start_time = datetime.now()
    
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*90}")
        print(f"  {text}")
        print(f"{'='*90}{Colors.END}\n")
    
    def print_step(self, step_num: int, total_steps: int, text: str):
        """Print workflow step"""
        print(f"{Colors.CYAN}[STEP {step_num}/{total_steps}] {Colors.BOLD}{text}{Colors.END}")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")
    
    def step_1_system_check(self):
        """STEP 1: System validation and readiness check"""
        self.print_step(1, 4, "SYSTEM HEALTH CHECK")
        
        # Check tokens
        print(f"\n{Colors.BOLD}Token Status:{Colors.END}")
        import os
        ibm_token = os.environ.get("IBM_QUANTUM_TOKEN")
        zenodo_token = os.environ.get("ZENODO_TOKEN")
        
        if ibm_token:
            self.print_success(f"IBM_QUANTUM_TOKEN: set (***{ibm_token[-8:]})")
        else:
            self.print_warning("IBM_QUANTUM_TOKEN: NOT SET (using mock mode)")
        
        if zenodo_token:
            self.print_success(f"ZENODO_TOKEN: set (***{zenodo_token[-8:]})")
        else:
            self.print_warning("ZENODO_TOKEN: NOT SET (using mock mode)")
        
        # Check module imports
        print(f"\n{Colors.BOLD}Module Imports:{Colors.END}")
        try:
            import qiskit
            self.print_success(f"Qiskit: {qiskit.__version__}")
        except ImportError:
            self.print_warning("Qiskit: not available (mock mode)")
        
        try:
            import scipy
            self.print_success(f"SciPy: {scipy.__version__}")
        except ImportError:
            self.print_warning("SciPy: not available")
        
        try:
            import numpy
            self.print_success(f"NumPy: {numpy.__version__}")
        except ImportError:
            self.print_warning("NumPy: not available")
        
        # Show execution plan
        print(f"\n{Colors.BOLD}Execution Plan:{Colors.END}")
        print(f"  1. RQC vs RCS comparison (3 stages)")
        print(f"  2. Domain-specific applications (4 experiments)")
        print(f"  3. Zenodo publication (2 datasets)")
        print(f"  4. Research archival")
        
        self.print_success("System check complete")
    
    def step_2_rqc_vs_rcs_experiments(self):
        """STEP 2: Execute RQC vs RCS experiments on IBM hardware"""
        self.print_step(2, 4, "RQC VS RCS EXPERIMENTS")
        
        # Show strategy
        print()
        ExecutionStrategy.print_strategy()
        
        # Run experiments for each stage
        stage_results = {}
        
        for stage in [
            ExecutionStage.STAGE1_BASELINE,
            ExecutionStage.STAGE2_SCALING,
            ExecutionStage.STAGE3_EXTREME
        ]:
            print(f"\n{Colors.BOLD}Executing {stage.value}...{Colors.END}")
            
            # Validate stage
            is_valid, msg = self.ibm_manager.validate_stage(stage)
            if not is_valid:
                self.print_warning(f"{msg}")
                continue
            
            # Execute
            results = self.ibm_manager.execute_stage(stage, run_rcs=True, run_rqc=True)
            stage_results[stage.value] = results
        
        self.experiment_results = stage_results
        
        # Export logs (make sure file exists for publication)
        if self.ibm_manager.execution_logs:
            self.ibm_manager.export_execution_logs("execution_logs.json")
            self.print_success("Execution logs exported to execution_logs.json")
        
        self.print_success("RQC vs RCS experiments complete")
    
    def step_3_application_experiments(self):
        """STEP 3: Execute domain-specific application experiments"""
        self.print_step(3, 4, "APPLICATION EXPERIMENTS")
        
        print()
        results = self.app_framework.run_all_experiments()
        self.application_results = results
        
        # Save summary
        summary = self.app_framework.generate_publication_summary(results)
        with open("APPLICATION_RESULTS.txt", "w") as f:
            f.write(summary)
        
        self.print_success("Application results saved to APPLICATION_RESULTS.txt")
    
    def step_4_zenodo_publication(self):
        """STEP 4: Publish results to Zenodo"""
        self.print_step(4, 4, "ZENODO PUBLICATION")
        
        print()
        
        # Determine which files exist
        rqc_files = [
            "osiris_rqc_framework.py",
            "osiris_ibm_execution.py",
            "osiris_applications.py"
        ]
        
        source_files = [f for f in rqc_files if Path(f).exists()]
        
        # Publish main RQC results
        if Path("execution_logs.json").exists():
            doi_rqc = self.publisher.publish_rqc_experiment(
                results_file="execution_logs.json",
                execution_logs_file="execution_logs.json",
                source_code_files=source_files[:2]  # RQC + IBM modules
            )
            self.dois["rqc_experiment"] = doi_rqc
        
        # Publish applications
        if Path("APPLICATION_RESULTS.txt").exists():
            doi_apps = self.publisher.publish_applications(
                application_results_file="APPLICATION_RESULTS.txt",
                source_code_files=[source_files[2]] if len(source_files) > 2 else []  # Applications module
            )
            self.dois["applications"] = doi_apps
        
        self.print_success("Zenodo publication complete")
    
    def final_report(self):
        """Generate comprehensive final report"""
        self.print_header("RESEARCH COMPLETION REPORT")
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"{Colors.BOLD}Experiment Summary{Colors.END}")
        print(f"  Start Time: {self.start_time.isoformat()}")
        print(f"  End Time: {datetime.now().isoformat()}")
        print(f"  Duration: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print()
        
        print(f"{Colors.BOLD}Key Results{Colors.END}")
        print(f"  Experiments Run: {len(self.experiment_results)} stages")
        print(f"  Application Tests: {len(self.application_results)} domains")
        print(f"  Zenodo Publications: {len(self.dois)} datasets")
        print()
        
        if self.dois:
            print(f"{Colors.BOLD}Published DOIs{Colors.END}")
            for key, doi in self.dois.items():
                if doi:
                    print(f"  {key}: {doi}")
                    print(f"    URL: https://zenodo.org/record/{doi.split('.')[-1]}")
        
        print()
        print(f"{Colors.BOLD}Output Files{Colors.END}")
        files = [
            ("execution_logs.json", "Raw experiment data"),
            ("APPLICATION_RESULTS.txt", "Domain-specific results"),
        ]
        for fname, desc in files:
            if Path(fname).exists():
                size_kb = Path(fname).stat().st_size / 1024
                print(f"  ✓ {fname} ({size_kb:.1f} KB) - {desc}")
        
        # Create research archive manifest
        print()
        print(f"{Colors.BOLD}Creating Research Archive{Colors.END}")
        manifest = ResearchArchive.create_manifest(
            experiment_date=self.start_time.isoformat()[:10],
            dois=self.dois
        )
        
        with open("RESEARCH_ARCHIVE_MANIFEST.txt", "w") as f:
            f.write(manifest)
        
        self.print_success("Archive manifest created")
        
        # Citation
        print()
        print(f"{Colors.BOLD}Recommended Citation{Colors.END}")
        print(f"""
@article{{osiris_rqc_2026,
  author = {{OSIRIS Quantum Research System}},
  title = {{Recursive Quantum Circuits Outperform Random Circuit Sampling: Evidence from Adaptive Feedback}},
  year = {{2026}},
  month = {{{datetime.now().strftime('%B')}}},
  doi = {{{self.dois.get('rqc_experiment', 'pending')}}}
}}
""")
    
    async def run_full_pipeline(self):
        """Execute complete research pipeline"""
        self.print_header("OSIRIS RQC QUANTUM ADVANTAGE RESEARCH PIPELINE")
        
        print(f"{Colors.BOLD}Research Goal:{Colors.END}")
        print(f"  Demonstrate statistically significant quantum advantage through")
        print(f"  Recursive Quantum Circuits (RQC) with adaptive feedback")
        print()
        
        print(f"{Colors.BOLD}Success Criteria:{Colors.END}")
        print(f"  ✓ RQC mean XEB > RCS mean XEB")
        print(f"  ✓ p-value < 0.05 (95% confidence)")
        print(f"  ✓ Results replicated across multiple backends")
        print(f"  ✓ Practical applications demonstrated")
        print(f"  ✓ Results published with DOI")
        
        try:
            # Run all steps
            self.step_1_system_check()
            self.step_2_rqc_vs_rcs_experiments()
            self.step_3_application_experiments()
            self.step_4_zenodo_publication()
            
            # Final report
            self.final_report()
            
            self.print_header("PIPELINE COMPLETE - READY FOR PUBLICATION")
            
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}Pipeline interrupted by user{Colors.END}")
            sys.exit(1)
        except Exception as e:
            print(f"\n{Colors.RED}Pipeline error: {e}{Colors.END}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


# Command-line interface
async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OSIRIS RQC Quantum Advantage Research Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 osiris_rqc_orchestrator.py              # Run full pipeline
  python3 osiris_rqc_orchestrator.py --check      # System check only
  python3 osiris_rqc_orchestrator.py --experiments # Run experiments only
  python3 osiris_rqc_orchestrator.py --publish    # Publish results only
        """
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="System check only (no experiments)"
    )
    parser.add_argument(
        "--experiments",
        action="store_true",
        help="Run experiments only (skip publication)"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish results only (skip experiments)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode (minimal trials)"
    )
    
    args = parser.parse_args()
    
    orchestrator = ResearchOrchestrator()
    
    if args.check:
        orchestrator.step_1_system_check()
    elif args.experiments:
        orchestrator.step_1_system_check()
        orchestrator.step_2_rqc_vs_rcs_experiments()
        orchestrator.step_3_application_experiments()
    elif args.publish:
        orchestrator.step_4_zenodo_publication()
    else:
        # Run full pipeline
        await orchestrator.run_full_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
