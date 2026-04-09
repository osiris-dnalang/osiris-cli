#!/usr/bin/env python3
"""
OSIRIS Experiment Orchestrator
===============================

High-level workflow manager for automated discovery campaigns.
Manages:
  • Experiment scheduling
  • Result tracking
  • Validation pipelines
  • Publishing decisions
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger('OSIRIS_ORCHESTRATOR')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# ════════════════════════════════════════════════════════════════════════════════
# 1. EXPERIMENT CAMPAIGN DEFINITION
# ════════════════════════════════════════════════════════════════════════════════

class ExperimentCampaign:
    """Define and track a campaign of related experiments"""
    
    def __init__(self, campaign_name: str, description: str = ""):
        self.campaign_name = campaign_name
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.experiments: List[Dict[str, Any]] = []
        self.results: Dict[str, Dict[str, Any]] = {}
        self.metadata = {
            'ibm_backend': os.getenv('IBM_BACKEND', 'ibm_torino'),
            'api_token_set': bool(os.getenv('IBM_QUANTUM_TOKEN')),
            'zenodo_token_set': bool(os.getenv('ZENODO_TOKEN')),
        }
    
    def add_experiment(self, exp_config: Dict[str, Any]):
        """Add experiment to campaign"""
        self.experiments.append(exp_config)
        logger.info(f"✓ Added experiment: {exp_config.get('name', 'unnamed')}")
    
    def run_all(self, pipeline):
        """Execute all experiments in campaign"""
        logger.info(f"\n{'='*70}")
        logger.info(f"CAMPAIGN: {self.campaign_name}")
        logger.info(f"Description: {self.description}")
        logger.info(f"Experiments: {len(self.experiments)}")
        logger.info(f"{'='*70}\n")
        
        for i, exp_config in enumerate(self.experiments, 1):
            logger.info(f"\n[{i}/{len(self.experiments)}] Running: {exp_config.get('name', 'unnamed')}")
            
            # Create config object from dict
            from osiris_auto_discovery import ExperimentConfig
            
            config = ExperimentConfig(**exp_config)
            result = pipeline.run_hypothesis_test(config)
            
            self.results[config.name] = {
                'passed': result.passes_significance,
                'p_value': result.p_value,
                'effect_size': result.effect_size,
                'xeb_mean': result.statistical_summary.get('xeb_mean'),
            }
            
            pipeline.save_result(result)
    
    def summary(self) -> str:
        """Generate campaign summary"""
        passed = sum(1 for r in self.results.values() if r['passed'])
        total = len(self.results)
        
        lines = [
            f"\n{'='*70}",
            f"CAMPAIGN SUMMARY: {self.campaign_name}",
            f"{'='*70}",
            f"Total Experiments: {total}",
            f"Passed: {passed} ✓",
            f"Failed/Null: {total - passed} ✗",
            f"Success Rate: {100*passed/total if total > 0 else 0:.1f}%",
            "",
            "Results:",
        ]
        
        for name, result in self.results.items():
            status = "✓" if result['passed'] else "✗"
            lines.append(f"  {status} {name}: p={result.get('p_value', 0):.2e}, d={result.get('effect_size', 0):.3f}")
        
        lines.append(f"{'='*70}\n")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# 2. EXPERIMENT TEMPLATES (REPRODUCTION PROTOCOL)
# ════════════════════════════════════════════════════════════════════════════════

class ExperimentTemplates:
    """Standard experiment configurations for reproducibility"""
    
    @staticmethod
    def xeb_vs_depth() -> Dict[str, Any]:
        """XEB scaling with circuit depth"""
        return {
            'name': 'xeb_vs_depth',
            'n_qubits': 12,
            'circuit_depth': 8,
            'shots': 4000,
            'trials': 20,
            'alpha': 0.05,
            'hypothesis': 'XEB increases with circuit depth',
            'null_hypothesis': 'XEB is independent of depth',
            'predicted_outcome': 'Positive correlation between depth and XEB',
        }
    
    @staticmethod
    def entropy_saturation() -> Dict[str, Any]:
        """Entropy growth and saturation"""
        return {
            'name': 'entropy_saturation',
            'n_qubits': 12,
            'circuit_depth': 12,
            'shots': 4000,
            'trials': 20,
            'alpha': 0.05,
            'hypothesis': 'Entropy approaches maximum value',
            'null_hypothesis': 'Entropy shows no pattern',
            'predicted_outcome': 'Entropy grows then saturates',
        }
    
    @staticmethod
    def noise_robustness() -> Dict[str, Any]:
        """Circuit robustness under noise"""
        return {
            'name': 'noise_robustness_comparison',
            'n_qubits': 12,
            'circuit_depth': 6,
            'shots': 4000,
            'trials': 15,
            'alpha': 0.05,
            'hypothesis': 'Shallow circuits preserve XEB under noise',
            'null_hypothesis': 'XEB degradation is independent of depth',
            'predicted_outcome': 'Shallower circuits degrade less',
        }
    
    @staticmethod
    def replication_protocol(original_result: Dict[str, Any]) -> Dict[str, Any]:
        """Independent replication of published result"""
        return {
            'name': f"replication_{original_result.get('result_id', 'unknown')}",
            'n_qubits': original_result.get('config', {}).get('n_qubits', 12),
            'circuit_depth': original_result.get('config', {}).get('circuit_depth', 8),
            'shots': original_result.get('config', {}).get('shots', 4000),
            'trials': 30,  # More trials for replication
            'alpha': 0.05,
            'hypothesis': f"Replication of: {original_result.get('name', 'unknown')}",
            'null_hypothesis': f"Original result is device or environment specific",
            'predicted_outcome': f"Independent confirmation of p < 0.05",
        }


# ════════════════════════════════════════════════════════════════════════════════
# 3. CAMPAIGN DEFINITIONS (1-WEEK TIMELINE)
# ════════════════════════════════════════════════════════════════════════════════

def campaign_week1_foundation() -> ExperimentCampaign:
    """Week 1: Establish baseline measurements and validation"""
    
    campaign = ExperimentCampaign(
        "week1_foundation",
        "Establish XEB baseline, entropy growth, and noise robustness baseline"
    )
    
    # Day 1-2: XEB baseline
    campaign.add_experiment({
        'name': 'day1_xeb_baseline_12q',
        'n_qubits': 12,
        'circuit_depth': 8,
        'shots': 4000,
        'trials': 30,
        'hypothesis': 'Random circuits on ibm_torino produce measurable XEB',
        'null_hypothesis': 'XEB is statistically indistinguishable from 0',
        'predicted_outcome': 'XEB > 0.1 with p < 0.05',
    })
    
    # Day 2-3: Entropy growth
    campaign.add_experiment({
        'name': 'day2_entropy_growth',
        'n_qubits': 12,
        'circuit_depth': 12,
        'shots': 4000,
        'trials': 20,
        'hypothesis': 'Entropy grows with circuit depth',
        'null_hypothesis': 'Entropy is independent of depth',
        'predicted_outcome': 'Positive trend between depth and entropy',
    })
    
    # Day 3-4: Noise robustness
    campaign.add_experiment({
        'name': 'day3_shallow_vs_deep',
        'n_qubits': 12,
        'circuit_depth': 4,
        'shots': 4000,
        'trials': 25,
        'hypothesis': 'Shallow circuits (d=4) preserve XEB better than deep (d=12)',
        'null_hypothesis': 'XEB preservation is independent of depth',
        'predicted_outcome': 'd=4 shows less XEB degradation than d=12',
    })
    
    # Day 4-5: Multiple backend validation
    campaign.add_experiment({
        'name': 'day4_backend_consistency',
        'n_qubits': 10,
        'circuit_depth': 8,
        'shots': 3000,
        'trials': 15,
        'backend': 'ibm_fez',
        'hypothesis': 'XEB behavior is consistent across Hardware Backends',
        'null_hypothesis': 'Backend shows different XEB characteristics',
        'predicted_outcome': 'Similar XEB statistics on ibm_fez vs ibm_torino',
    })
    
    return campaign


def campaign_week1_adaptive() -> ExperimentCampaign:
    """Week 1: Test adaptive circuit hypotheses"""
    
    campaign = ExperimentCampaign(
        "week1_adaptive_hypothesis",
        "Test RQC (Recursive Quantum Circuits) vs RCS (Random Circuit Sampling)"
    )
    
    campaign.add_experiment({
        'name': 'adaptive_xeb_improvement',
        'n_qubits': 12,
        'circuit_depth': 8,
        'shots': 4000,
        'trials': 20,
        'hypothesis': 'Adaptive circuits (RQC) achieve higher XEB than random (RCS)',
        'null_hypothesis': 'Adaptive and random circuits have equivalent XEB',
        'predicted_outcome': 'RQC XEB > RCS XEB with effect size d > 0.5',
    })
    
    campaign.add_experiment({
        'name': 'adaptive_convergence_rate',
        'n_qubits': 12,
        'circuit_depth': 6,
        'shots': 3000,
        'trials': 25,
        'hypothesis': 'Adaptive circuits converge to high XEB faster',
        'null_hypothesis': 'Convergence rate is independent of adaptation',
        'predicted_outcome': 'RQC shows faster XEB growth per iteration',
    })
    
    return campaign


# ════════════════════════════════════════════════════════════════════════════════
# 4. WORKFLOW SCHEDULER
# ════════════════════════════════════════════════════════════════════════════════

class WorkflowScheduler:
    """Schedule and execute experiments with dependencies"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.campaigns: List[ExperimentCampaign] = []
    
    def add_campaign(self, campaign: ExperimentCampaign):
        """Register campaign"""
        self.campaigns.append(campaign)
        logger.info(f"✓ Registered campaign: {campaign.campaign_name}")
    
    def run_all_campaigns(self):
        """Execute all registered campaigns"""
        for campaign in self.campaigns:
            campaign.run_all(self.pipeline)
            logger.info(campaign.summary())
    
    def run_campaign(self, campaign_name: str):
        """Run single campaign by name"""
        for campaign in self.campaigns:
            if campaign.campaign_name == campaign_name:
                campaign.run_all(self.pipeline)
                logger.info(campaign.summary())
                return
        
        logger.error(f"Campaign not found: {campaign_name}")


# ════════════════════════════════════════════════════════════════════════════════
# 5. AUTO-PUBLICATION DECISION LOGIC
# ════════════════════════════════════════════════════════════════════════════════

class PublicationDecisionEngine:
    """Automatically decide if results should be published"""
    
    @staticmethod
    def should_publish(result) -> Tuple[bool, str]:
        """Decide if result meets publication threshold"""
        
        checks = {
            'falsifiable': result.falsifiable,
            'statistically_significant': result.p_value < 0.05,
            'large_effect': abs(result.effect_size) > 0.5,
            'wide_ci_not_crossing_zero': (
                result.confidence_interval[0] > 0 or 
                result.confidence_interval[1] < 0
            ),
        }
        
        all_passed = all(checks.values())
        reasons = [k for k, v in checks.items() if not v]
        
        if all_passed:
            return True, "All publication criteria met"
        else:
            return False, f"Failed: {', '.join(reasons)}"
    
    @staticmethod
    def generate_zenodo_metadata(result, campaign_name: str) -> Dict[str, Any]:
        """Generate Zenodo metadata"""
        return {
            'title': f"[{campaign_name}] {result.name}",
            'description': f"Automated discovery result: {result.name}",
            'keywords': [
                'quantum-computing',
                'ibm-quantum',
                'automated-discovery',
                'falsifiable-hypothesis'
            ],
            'creators': [{'name': 'OSIRIS Automated Discovery'}],
            'access_right': 'open',
            'license': 'other-closed',
            'upload_type': 'dataset',
        }


# ════════════════════════════════════════════════════════════════════════════════
# 6. MAIN ORCHESTRATION
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Run orchestrated discovery campaign"""
    
    from osiris_auto_discovery import AutoDiscoveryPipeline
    
    # Initialize
    api_token = os.getenv('IBM_QUANTUM_TOKEN', 'mock')
    pipeline = AutoDiscoveryPipeline(api_token, output_dir="./week1_discoveries")
    scheduler = WorkflowScheduler(pipeline)
    
    # Register campaigns
    logger.info("\n═══════════════════════════════════════════════════════════════════")
    logger.info("OSIRIS WEEK-1 AUTOMATED DISCOVERY CAMPAIGN")
    logger.info("═══════════════════════════════════════════════════════════════════\n")
    
    # Week 1 campaigns
    scheduler.add_campaign(campaign_week1_foundation())
    scheduler.add_campaign(campaign_week1_adaptive())
    
    # Run all
    logger.info(f"Executing {sum(len(c.experiments) for c in scheduler.campaigns)} experiments...\n")
    scheduler.run_all_campaigns()
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("CAMPAIGN EXECUTION COMPLETE")
    logger.info("="*70)
    logger.info(f"Results saved to: {pipeline.output_dir}")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    main()
