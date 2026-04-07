#!/usr/bin/env python3
"""
QUANTUM DISCOVERY VERIFICATION SCRIPT

Runs all checks to verify Phase 1 framework is complete and working.
Use this to confirm your environment is ready before Phase 2.

Usage:
    python3 verify_quantum_discovery.py
"""

import os
import sys
import json
import csv
from pathlib import Path

def check_file_exists(path, description):
    """Check if a file exists and report."""
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✅ {description}: {path} ({size_kb:.1f} KB)")
        return True
    else:
        print(f"  ❌ {description}: {path} NOT FOUND")
        return False

def check_module_imports():
    """Check if all Phase 1 modules can be imported."""
    print("\n[3/5] Checking Python module imports...")
    sys.path.insert(0, '/workspaces/osiris-cli/quantum_discovery/phase1_analysis')
    
    modules = [
        ('quantum_data_loader', 'QuantumDataLoader'),
        ('single_system_analyzer', 'SingleSystemAnalyzer'),
        ('correlation_analyzer', 'CorrelationAnalyzer'),
        ('anomaly_detector', 'AnomalyDetector'),
        ('qbyte_miner', 'QBYTEMiner'),
        ('phase1_executor', 'Phase1Executor'),
    ]
    
    all_imported = True
    for module_name, class_name in modules:
        try:
            module = __import__(module_name)
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name}: {str(e)[:60]}")
            all_imported = False
    
    return all_imported

def check_output_files():
    """Check if Phase 1 outputs exist."""
    print("\n[4/5] Checking Phase 1 output files...")
    
    files = [
        ('data_inventory.json', 'Circuit inventory'),
        ('entropy_analysis_results.json', 'Entropy analysis'),
        ('anomalies_week4.csv', 'Anomaly report'),
    ]
    
    all_exist = True
    for filename, description in files:
        if not check_file_exists(filename, description):
            all_exist = False
    
    # Check CSV content
    if os.path.exists('anomalies_week4.csv'):
        with open('anomalies_week4.csv') as f:
            rows = list(csv.DictReader(f))
            print(f"    → {len(rows)} anomalies detected")
            if rows:
                first = rows[0]
                print(f"    → Example: Z={first.get('z_score')}, p={first.get('p_value')}")
    
    return all_exist

def check_documentation():
    """Check if documentation files exist."""
    print("\n[2/5] Checking documentation files...")
    
    docs = [
        ('QUANTUM_DISCOVERY_RESEARCH_PROGRAM.md', '12-week roadmap'),
        ('QBYTE_MINING_STRATEGY.md', 'QBYTE theory & strategy'),
        ('QUANTUM_DISCOVERY_QUICKSTART.md', 'Quick reference'),
        ('RUNNABLE_PHASE1_START.md', 'Execution guide'),
        ('STATUS_DASHBOARD.md', 'Status & overview'),
    ]
    
    all_exist = True
    for filename, description in docs:
        if not check_file_exists(filename, description):
            all_exist = False
    
    return all_exist

def check_code_modules():
    """Check if Python modules exist."""
    print("\n[1/5] Checking code modules...")
    
    modules = [
        ('quantum_discovery/phase1_analysis/quantum_data_loader.py', 'Data loader'),
        ('quantum_discovery/phase1_analysis/single_system_analyzer.py', 'Entropy analyzer'),
        ('quantum_discovery/phase1_analysis/correlation_analyzer.py', 'Correlation analyzer'),
        ('quantum_discovery/phase1_analysis/anomaly_detector.py', 'Anomaly detector'),
        ('quantum_discovery/phase1_analysis/qbyte_miner.py', 'QBYTE miner'),
        ('quantum_discovery/phase1_analysis/phase1_executor.py', 'Phase 1 executor'),
    ]
    
    all_exist = True
    for filepath, description in modules:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def print_summary(results):
    """Print final summary."""
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(results.values())
    
    if passed == total:
        print(f"\n✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\n🚀 PHASE 1 FRAMEWORK IS READY")
        print("\nNext steps:")
        print("  1. Run: python3 quantum_discovery/phase1_analysis/phase1_executor.py --full-analysis")
        print("  2. Review: cat anomalies_week4.csv")
        print("  3. Plan Phase 2: Read QUANTUM_DISCOVERY_RESEARCH_PROGRAM.md")
        return True
    else:
        print(f"\n❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\nFailing checks:")
        for check, result in results.items():
            if not result:
                print(f"  - {check}")
        return False

def main():
    """Run all verification checks."""
    print("="*60)
    print("QUANTUM DISCOVERY VERIFICATION SCRIPT")
    print("="*60)
    
    os.chdir('/workspaces/osiris-cli')
    
    results = {
        'Code modules': check_code_modules(),
        'Documentation': check_documentation(),
        'Module imports': check_module_imports(),
        'Output files': check_output_files(),
    }
    
    success = print_summary(results)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
