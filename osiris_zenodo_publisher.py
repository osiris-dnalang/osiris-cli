#!/usr/bin/env python3
"""
OSIRIS Zenodo Publishing Integration
=====================================

Automated publishing to Zenodo with full provenance and reproducibility.
Only publishes results that pass rigorous statistical validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import requests

logger = logging.getLogger('OSIRIS_ZENODO')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# ════════════════════════════════════════════════════════════════════════════════
# 1. ZENODO API CLIENT
# ════════════════════════════════════════════════════════════════════════════════

class ZenodoPubisher:
    """Publish experiment results to Zenodo"""
    
    # Zenodo endpoints
    SANDBOX_URL = "https://sandbox.zenodo.org"
    PRODUCTION_URL = "https://zenodo.org"
    
    def __init__(self, access_token: str, use_sandbox: bool = True):
        """Initialize Zenodo client"""
        self.token = access_token
        self.base_url = self.SANDBOX_URL if use_sandbox else self.PRODUCTION_URL
        self.api_url = f"{self.base_url}/api/deposit/depositions"
        self.headers = {"Content-Type": "application/json"}
        self.use_sandbox = use_sandbox
        
        logger.info(f"✓ Initialized Zenodo client ({'sandbox' if use_sandbox else 'production'})")
    
    def _auth_headers(self) -> Dict[str, str]:
        """Get authenticated headers"""
        return {**self.headers, "Authorization": f"Bearer {self.token}"}
    
    def test_connection(self) -> bool:
        """Test Zenodo API connection"""
        try:
            response = requests.get(
                f"{self.api_url}?access_token={self.token}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                logger.info("✓ Zenodo connection successful")
                return True
            else:
                logger.error(f"Zenodo connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Zenodo connection error: {e}")
            return False
    
    def create_deposition(self, metadata: Dict) -> Optional[str]:
        """Create new deposition"""
        try:
            response = requests.post(
                f"{self.api_url}?access_token={self.token}",
                json=metadata,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                deposition_id = response.json()['id']
                logger.info(f"✓ Created deposition: {deposition_id}")
                return deposition_id
            else:
                logger.error(f"Failed to create deposition: {response.status_code}")
                logger.error(response.text)
                return None
        
        except Exception as e:
            logger.error(f"Error creating deposition: {e}")
            return None
    
    def upload_file(self, deposition_id: str, filepath: str) -> bool:
        """Upload file to deposition"""
        try:
            filename = Path(filepath).name
            
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f)}
                files_url = f"{self.api_url}/{deposition_id}/files?access_token={self.token}"
                
                response = requests.post(files_url, files=files, timeout=60)
            
            if response.status_code == 201:
                logger.info(f"  ✓ Uploaded: {filename}")
                return True
            else:
                logger.error(f"Upload failed: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def publish_deposition(self, deposition_id: str) -> Optional[Dict]:
        """Publish deposition"""
        try:
            response = requests.post(
                f"{self.api_url}/{deposition_id}/actions/publish?access_token={self.token}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 202:
                record = response.json()
                zenodo_id = record['id']
                zenodo_url = record['links']['record_html']
                logger.info(f"✓ Published! Zenodo ID: {zenodo_id}")
                logger.info(f"  URL: {zenodo_url}")
                return {'id': zenodo_id, 'url': zenodo_url, 'doi': record.get('doi')}
            else:
                logger.error(f"Publication failed: {response.status_code}")
                logger.error(response.text)
                return None
        
        except Exception as e:
            logger.error(f"Publication error: {e}")
            return None


# ════════════════════════════════════════════════════════════════════════════════
# 2. RESULT PACKAGING
# ════════════════════════════════════════════════════════════════════════════════

class ResultPackager:
    """Package experiment results for publishing"""
    
    @staticmethod
    def package_result(result, report_md: str, output_dir: str = ".") -> Path:
        """Create complete result package"""
        
        # Create directory
        package_dir = Path(output_dir) / f"package_{result.result_id}"
        package_dir.mkdir(exist_ok=True)
        
        # Save JSON result
        json_path = package_dir / f"result_{result.result_id}.json"
        result.to_json(str(json_path))
        
        # Save markdown report
        report_path = package_dir / f"report_{result.result_id}.md"
        with open(report_path, 'w') as f:
            f.write(report_md)
        
        # Save metadata
        metadata = {
            'result_id': result.result_id,
            'experiment': result.name,
            'timestamp': result.timestamp,
            'backend': result.backend,
            'statistical_summary': result.statistical_summary,
            'passes_significance': result.passes_significance,
            'falsifiable': result.falsifiable,
        }
        
        metadata_path = package_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✓ Packaged result: {package_dir}")
        return package_dir
    
    @staticmethod
    def create_zenodo_metadata(result, campaign: str = "OSIRIS") -> Dict:
        """Create Zenodo metadata for result"""
        
        keywords = [
            'quantum-computing',
            'ibm-quantum',
            'automated-discovery',
            'falsifiable-hypothesis',
            'statistical-validation'
        ]
        
        if result.passes_significance:
            keywords.append('significant-result')
        else:
            keywords.append('null-result')
        
        return {
            'metadata': {
                'title': f"[{campaign}] {result.name}",
                'description': (
                    f"Automated quantum experiment on {result.backend}\n\n"
                    f"**Hypothesis:** {result.hypothesis}\n\n"
                    f"**Result:** {('SIGNIFICANT' if result.passes_significance else 'NOT SIGNIFICANT')}\n\n"
                    f"p-value: {result.p_value:.2e}\n"
                    f"Effect size (Cohen's d): {result.effect_size:.4f}\n\n"
                    f"Result ID: {result.result_id}\n"
                    f"Falsifiable: {'Yes' if result.falsifiable else 'No'}"
                ),
                'creators': [{'name': 'OSIRIS Automated Discovery Pipeline'}],
                'keywords': keywords,
                'license': 'cc-by-4.0',
                'access_right': 'open',
                'upload_type': 'dataset',
                'publication_date': datetime.now().isoformat()[:10],
            }
        }


# ════════════════════════════════════════════════════════════════════════════════
# 3. AUTOMATED PUBLISHING DECISION
# ════════════════════════════════════════════════════════════════════════════════

class AutoPublishDecision:
    """Decide whether to publish based on rigorous criteria"""
    
    # Publishing thresholds
    PUBLICATION_CRITERIA = {
        'min_p_value': 0.05,  # p < 0.05
        'min_effect_size': 0.5,  # |Cohen's d| >= 0.5
        'require_falsifiable': True,
        'require_ci_not_crossing_zero': True,
        'min_trials': 10,  # Minimum sample size
    }
    
    @staticmethod
    def evaluate(result) -> Tuple[bool, str, List[str]]:
        """Evaluate if result should be published"""
        
        issues = []
        
        # Check falsifiability
        if not result.falsifiable:
            issues.append("Result is not falsifiable")
        
        # Check statistical significance
        if result.p_value >= AutoPublishDecision.PUBLICATION_CRITERIA['min_p_value']:
            issues.append(
                f"p-value {result.p_value:.3f} >= {AutoPublishDecision.PUBLICATION_CRITERIA['min_p_value']}"
            )
        
        # Check effect size
        if abs(result.effect_size) < AutoPublishDecision.PUBLICATION_CRITERIA['min_effect_size']:
            issues.append(
                f"|Cohen's d| = {abs(result.effect_size):.3f} < {AutoPublishDecision.PUBLICATION_CRITERIA['min_effect_size']}"
            )
        
        # Check CI
        if AutoPublishDecision.PUBLICATION_CRITERIA['require_ci_not_crossing_zero']:
            if result.confidence_interval[0] < 0 < result.confidence_interval[1]:
                issues.append("95% CI crosses zero")
        
        # Decision
        should_publish = len(issues) == 0
        
        if should_publish:
            reason = "All publication criteria met ✓"
        else:
            reason = f"Does not meet publication criteria ({len(issues)} issues)"
        
        return should_publish, reason, issues


# ════════════════════════════════════════════════════════════════════════════════
# 4. PUBLISHING WORKFLOW
# ════════════════════════════════════════════════════════════════════════════════

class PublishingWorkflow:
    """Complete publishing workflow"""
    
    def __init__(self, zenodo_token: str, use_sandbox: bool = True):
        self.zenodo = ZenodoPubisher(zenodo_token, use_sandbox=use_sandbox)
        self.packager = ResultPackager()
        self.decision = AutoPublishDecision()
    
    def publish_result(self, result, report_md: str, 
                      campaign: str = "OSIRIS",
                      dry_run: bool = False) -> Optional[Dict]:
        """Publish a single result"""
        
        logger.info(f"\n{'='*70}")
        logger.info(f"PUBLISHING WORKFLOW: {result.name}")
        logger.info(f"{'='*70}\n")
        
        # Decision
        should_publish, reason, issues = self.decision.evaluate(result)
        
        logger.info(f"✓ {reason}")
        if issues:
            for issue in issues:
                logger.info(f"  ✗ {issue}")
        
        if not should_publish:
            logger.info("⚠ Will NOT publish (criteria not met)")
            return None
        
        if dry_run:
            logger.info("(DRY RUN - not actually publishing)")
            return None
        
        logger.info("\n→ Proceeding with publication...\n")
        
        # Test connection
        if not self.zenodo.test_connection():
            logger.error("Cannot connect to Zenodo")
            return None
        
        # Package result
        package_dir = self.packager.package_result(result, report_md)
        
        # Create deposition
        metadata = self.packager.create_zenodo_metadata(result, campaign)
        deposition_id = self.zenodo.create_deposition(metadata['metadata'])
        
        if not deposition_id:
            return None
        
        # Upload files
        for filepath in package_dir.glob("*.json") | package_dir.glob("*.md"):
            self.zenodo.upload_file(deposition_id, str(filepath))
        
        # Publish
        record = self.zenodo.publish_deposition(deposition_id)
        
        if record:
            logger.info(f"\n✓ PUBLISHED SUCCESSFULLY")
            logger.info(f"  Zenodo URL: {record.get('url')}")
            logger.info(f"  DOI: {record.get('doi')}\n")
            
            # Save publication record
            pub_record = {
                'result_id': result.result_id,
                'zenodo_id': record.get('id'),
                'zenodo_url': record.get('url'),
                'doi': record.get('doi'),
                'published_at': datetime.now().isoformat(),
            }
            
            with open(package_dir / 'zenodo_record.json', 'w') as f:
                json.dump(pub_record, f, indent=2)
            
            return pub_record
        
        return None
    
    def publish_campaign(self, campaign, results: List, dry_run: bool = True):
        """Publish all results from a campaign"""
        
        logger.info(f"\n{'='*70}")
        logger.info(f"CAMPAIGN PUBLISHING: {campaign.campaign_name}")
        logger.info(f"Results: {len(results)}")
        logger.info(f"{'='*70}\n")
        
        published = 0
        rejected = 0
        
        for result in results:
            should_publish, reason, _ = self.decision.evaluate(result)
            
            if should_publish:
                logger.info(f"✓ {result.name}: ELIGIBLE")
                if not dry_run:
                    self.publish_result(result, "", campaign.campaign_name)
                published += 1
            else:
                logger.info(f"✗ {result.name}: {reason}")
                rejected += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Summary: {published} published, {rejected} rejected")
        logger.info(f"{'='*70}\n")


# ════════════════════════════════════════════════════════════════════════════════
# 5. EXAMPLE USAGE
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Example: publish a result"""
    
    zenodo_token = os.getenv('ZENODO_TOKEN')
    
    if not zenodo_token:
        logger.warning("ZENODO_TOKEN not set - using sandbox")
        zenodo_token = "test_token"
    
    # Initialize workflow
    workflow = PublishingWorkflow(zenodo_token, use_sandbox=True)
    
    logger.info("Zenodo Publishing Integration Ready")
    logger.info("Use: workflow.publish_result() to publish")


if __name__ == "__main__":
    main()
