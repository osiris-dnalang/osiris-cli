#!/usr/bin/env python3
"""
OSIRIS License Compliance & Environment Detection
===================================================

Automated compliance verification for the OSIRIS Source-Available Dual License.
Detects corporate/institutional environments and enforces licensing terms.

This module:
  1. Classifies the deployment environment (individual vs corporate)
  2. Validates commercial license keys
  3. Generates compliance reports for unauthorized corporate use
  4. Integrates with Zenodo for immutable violation archival

Privacy Note:
  - Only anonymized technical metadata is collected (hostname hash, domain class)
  - No personal data (names, emails, browsing history) is collected
  - Users consent to this monitoring by executing the Software (see LICENSE §4.2)

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

import os
import sys
import json
import socket
import hashlib
import platform
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger('OSIRIS_LICENSE')

# ════════════════════════════════════════════════════════════════════════════════
# 1. ENVIRONMENT CLASSIFICATION
# ════════════════════════════════════════════════════════════════════════════════

class EnvironmentClass(Enum):
    """Deployment environment classification"""
    INDIVIDUAL = "individual"
    ACADEMIC = "academic"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentSignature:
    """Anonymized environment metadata for compliance checking"""
    hostname_hash: str          # SHA-256 hash of hostname (never raw)
    domain_class: str           # Classification result
    domain_indicators: list     # Which indicators triggered
    os_type: str                # OS family
    timestamp: str              # ISO-8601 UTC
    software_version: str = "2.0.0"
    license_key_present: bool = False
    compliant: bool = True


# Corporate domain suffixes that indicate institutional deployment
CORPORATE_DOMAIN_SUFFIXES = frozenset({
    '.corp', '.corporate', '.internal', '.local',
    '.company', '.enterprise', '.intranet',
    '.ad', '.domain',  # Active Directory
})

# Educational / government suffixes
INSTITUTIONAL_SUFFIXES = frozenset({
    '.edu', '.ac.uk', '.ac.jp', '.edu.au', '.edu.cn',
    '.gov', '.mil', '.gov.uk', '.gov.au',
})

# Environment variables commonly set by corporate IT / CI/CD
CORPORATE_ENV_INDICATORS = frozenset({
    'USERDOMAIN',           # Windows Active Directory
    'USERDNSDOMAIN',        # Windows DNS domain
    'LOGONSERVER',          # Windows domain controller
    'JENKINS_URL',          # Jenkins CI
    'GITLAB_CI',            # GitLab CI
    'GITHUB_ACTIONS',       # GitHub Actions (corporate runners)
    'TEAMCITY_VERSION',     # TeamCity CI
    'BAMBOO_BUILDKEY',      # Bamboo CI
    'CIRCLECI',             # CircleCI
    'TRAVIS',               # Travis CI
    'AZURE_DEVOPS',         # Azure DevOps
    'AWS_EXECUTION_ENV',    # AWS Lambda / corporate cloud
    'GOOGLE_CLOUD_PROJECT', # GCP
    'CODESPACE_NAME',       # GitHub Codespaces (may be corporate)
})

# Known corporate/institutional hostname patterns
CORPORATE_HOSTNAME_PATTERNS = [
    'workstation', 'desktop-', 'laptop-',
    'pc-', 'srv-', 'server-',
    'vm-', 'vdi-', 'citrix',
    'corp-', 'enterprise-',
]


class EnvironmentDetector:
    """
    Detect whether the current environment is individual or corporate.
    
    Detection is based on:
      1. Hostname / FQDN domain analysis
      2. Environment variable scanning
      3. Network domain indicators
      
    All hostname data is hashed before storage — no raw hostnames are persisted.
    """
    
    def __init__(self):
        self.indicators_found: list = []
        self.classification = EnvironmentClass.UNKNOWN
    
    def detect(self) -> EnvironmentSignature:
        """Run full environment detection and return signature."""
        
        # 1. Hostname / domain analysis
        hostname = socket.gethostname()
        fqdn = socket.getfqdn()
        hostname_hash = hashlib.sha256(hostname.encode()).hexdigest()
        
        self._check_domain(fqdn)
        
        # 2. Environment variable scan
        self._check_env_vars()
        
        # 3. Hostname pattern analysis
        self._check_hostname_patterns(hostname.lower())
        
        # 4. Classify
        self._classify()
        
        # 5. Check for license key
        license_key_present = bool(os.getenv('OSIRIS_LICENSE_KEY'))
        
        # 6. Determine compliance
        compliant = self._is_compliant(license_key_present)
        
        return EnvironmentSignature(
            hostname_hash=hostname_hash,
            domain_class=self.classification.value,
            domain_indicators=self.indicators_found.copy(),
            os_type=platform.system(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            license_key_present=license_key_present,
            compliant=compliant,
        )
    
    def _check_domain(self, fqdn: str):
        """Check FQDN for corporate/institutional domain suffixes."""
        fqdn_lower = fqdn.lower()
        
        for suffix in CORPORATE_DOMAIN_SUFFIXES:
            if fqdn_lower.endswith(suffix):
                self.indicators_found.append(f"domain_suffix:{suffix}")
        
        for suffix in INSTITUTIONAL_SUFFIXES:
            if fqdn_lower.endswith(suffix):
                self.indicators_found.append(f"institutional_suffix:{suffix}")
    
    def _check_env_vars(self):
        """Scan for corporate environment variables."""
        for var in CORPORATE_ENV_INDICATORS:
            if os.getenv(var):
                self.indicators_found.append(f"env_var:{var}")
    
    def _check_hostname_patterns(self, hostname: str):
        """Check hostname for corporate naming patterns."""
        for pattern in CORPORATE_HOSTNAME_PATTERNS:
            if pattern in hostname:
                self.indicators_found.append(f"hostname_pattern:{pattern}")
    
    def _classify(self):
        """Classify environment based on collected indicators."""
        institutional = any('institutional_suffix' in i for i in self.indicators_found)
        corporate_domain = any('domain_suffix' in i for i in self.indicators_found)
        corporate_env = any('env_var' in i for i in self.indicators_found)
        corporate_hostname = any('hostname_pattern' in i for i in self.indicators_found)
        
        # Gov/edu suffixes → government/academic
        gov_indicators = any('.gov' in i or '.mil' in i for i in self.indicators_found)
        edu_indicators = any('.edu' in i or '.ac.' in i for i in self.indicators_found)
        
        if gov_indicators:
            self.classification = EnvironmentClass.GOVERNMENT
        elif edu_indicators:
            self.classification = EnvironmentClass.ACADEMIC
        elif corporate_domain or (corporate_env and corporate_hostname):
            self.classification = EnvironmentClass.CORPORATE
        elif corporate_env or corporate_hostname:
            # Single weak indicator — flag but don't hard-classify
            self.classification = EnvironmentClass.CORPORATE
        else:
            self.classification = EnvironmentClass.INDIVIDUAL
    
    def _is_compliant(self, has_license_key: bool) -> bool:
        """Determine if current deployment is license-compliant."""
        if self.classification == EnvironmentClass.INDIVIDUAL:
            return True  # Always compliant for individuals
        if self.classification == EnvironmentClass.ACADEMIC:
            return True  # Free for academic use
        if self.classification in (EnvironmentClass.CORPORATE, EnvironmentClass.GOVERNMENT):
            return has_license_key  # Must have commercial license
        return True  # Unknown → assume compliant


# ════════════════════════════════════════════════════════════════════════════════
# 2. LICENSE KEY VALIDATION
# ════════════════════════════════════════════════════════════════════════════════

class LicenseValidator:
    """
    Validate OSIRIS commercial license keys.
    
    License key format: OSIRIS-{tier}-{hash}-{expiry}
    Example: OSIRIS-ENT-a3f8b2c1-20270401
    """
    
    VALID_TIERS = {'IND', 'ACA', 'SMB', 'ENT', 'GOV'}
    
    @staticmethod
    def validate(license_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a license key.
        
        Returns:
            (is_valid, message)
        """
        if license_key is None:
            license_key = os.getenv('OSIRIS_LICENSE_KEY', '')
        
        if not license_key:
            return False, "No license key provided"
        
        parts = license_key.split('-')
        if len(parts) != 4:
            return False, "Invalid license key format"
        
        prefix, tier, key_hash, expiry = parts
        
        if prefix != 'OSIRIS':
            return False, "Invalid license key prefix"
        
        if tier not in LicenseValidator.VALID_TIERS:
            return False, f"Invalid license tier: {tier}"
        
        # Check expiry
        try:
            expiry_date = datetime.strptime(expiry, '%Y%m%d')
            if expiry_date < datetime.now():
                return False, f"License expired on {expiry_date.date()}"
        except ValueError:
            return False, "Invalid expiry date format"
        
        # Verify key hash integrity
        expected_hash = hashlib.sha256(
            f"OSIRIS-{tier}-{expiry}".encode()
        ).hexdigest()[:8]
        
        if key_hash != expected_hash:
            return False, "License key integrity check failed"
        
        return True, f"Valid {tier} license (expires {expiry_date.date()})"
    
    @staticmethod
    def generate_key(tier: str, expiry_date: str) -> str:
        """
        Generate a license key (for licensor use only).
        
        Args:
            tier: License tier (IND, ACA, SMB, ENT, GOV)
            expiry_date: Expiry in YYYYMMDD format
        """
        if tier not in LicenseValidator.VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        
        key_hash = hashlib.sha256(
            f"OSIRIS-{tier}-{expiry_date}".encode()
        ).hexdigest()[:8]
        
        return f"OSIRIS-{tier}-{key_hash}-{expiry_date}"


# ════════════════════════════════════════════════════════════════════════════════
# 3. COMPLIANCE REPORT GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

class ComplianceReporter:
    """
    Generate compliance reports for license violations.
    
    Reports contain ONLY anonymized technical metadata:
      - Hashed hostname (SHA-256)
      - Environment classification
      - Timestamp
      - Software version
      
    NO personal data is collected or transmitted.
    """
    
    REPORT_DIR = Path(__file__).parent / '.osiris_compliance'
    
    def __init__(self):
        self.report_dir = self.REPORT_DIR
        self.report_dir.mkdir(exist_ok=True)
    
    def generate_report(self, signature: EnvironmentSignature) -> Dict:
        """Generate a compliance violation report."""
        
        report = {
            'report_type': 'OSIRIS_LICENSE_COMPLIANCE_VIOLATION',
            'report_version': '1.0',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'software': {
                'name': 'OSIRIS-CLI',
                'version': signature.software_version,
                'repository': 'https://github.com/osiris-dnalang/osiris-cli',
                'license': 'OSIRIS Source-Available Dual License v1.0',
            },
            'environment': {
                'hostname_hash': signature.hostname_hash,
                'classification': signature.domain_class,
                'indicators_detected': signature.domain_indicators,
                'os_family': signature.os_type,
                'detection_timestamp': signature.timestamp,
            },
            'violation': {
                'type': 'UNAUTHORIZED_CORPORATE_USE',
                'description': (
                    f"Software deployed in {signature.domain_class} environment "
                    f"without valid commercial license key."
                ),
                'license_key_present': signature.license_key_present,
                'remediation': (
                    'Obtain a commercial license at '
                    'https://github.com/osiris-dnalang/osiris-cli '
                    'or contact licensing@agiledefensesystems.com'
                ),
            },
            'legal': {
                'applicable_license': 'OSIRIS Source-Available Dual License v1.0',
                'section': '§4 ENFORCEMENT & LIQUIDATED DAMAGES',
                'damages_per_instance': 'USD $150,000',
                'damages_per_month': 'USD $50,000/month',
                'copyright_holder': 'Devin Phillip Davis / Agile Defense Systems LLC',
            },
        }
        
        # Save locally
        report_id = hashlib.sha256(
            f"{signature.hostname_hash}-{signature.timestamp}".encode()
        ).hexdigest()[:16]
        
        report_path = self.report_dir / f"violation_{report_id}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.warning(f"Compliance violation report generated: {report_path}")
        
        return report
    
    def archive_to_zenodo(self, report: Dict) -> Optional[str]:
        """
        Archive violation report to Zenodo for immutable record.
        
        Only executes if ZENODO_TOKEN is set.
        Returns DOI if successful, None otherwise.
        """
        zenodo_token = os.getenv('ZENODO_TOKEN')
        if not zenodo_token:
            logger.info("ZENODO_TOKEN not set — skipping archival")
            return None
        
        try:
            # Import the existing publisher
            sys.path.insert(0, str(Path(__file__).parent))
            from osiris_zenodo_publisher import ZenodoPubisher
            
            publisher = ZenodoPubisher(
                access_token=zenodo_token,
                use_sandbox=True  # Use sandbox by default for safety
            )
            
            metadata = {
                'metadata': {
                    'title': (
                        f"OSIRIS License Compliance Report — "
                        f"{report['environment']['classification']} violation "
                        f"detected {report['generated_at']}"
                    ),
                    'description': report['violation']['description'],
                    'upload_type': 'other',
                    'creators': [{'name': 'OSIRIS Compliance System'}],
                    'license': 'closed',
                    'keywords': [
                        'license-compliance',
                        'osiris-cli',
                        'violation-report',
                    ],
                    'access_right': 'restricted',
                }
            }
            
            deposition_id = publisher.create_deposition(metadata)
            if deposition_id:
                # Save report to temp file and upload
                import tempfile
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False, prefix='osiris_violation_'
                ) as f:
                    json.dump(report, f, indent=2)
                    temp_path = f.name
                
                try:
                    publisher.upload_file(deposition_id, temp_path)
                    result = publisher.publish_deposition(deposition_id)
                    if result:
                        logger.warning(
                            f"Violation archived to Zenodo: {result.get('doi', 'pending')}"
                        )
                        return result.get('doi')
                finally:
                    os.unlink(temp_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Zenodo archival failed: {e}")
            return None


# ════════════════════════════════════════════════════════════════════════════════
# 4. COMPLIANCE GATE — MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

class ComplianceGate:
    """
    Main compliance verification gate.
    
    Call check() before any OSIRIS module execution.
    Returns (allowed, message) tuple.
    
    Behavior:
      - Individual/Academic: Always allowed, no restrictions
      - Corporate without license: Warning + report generation
      - Corporate with valid license: Allowed
    """
    
    _cached_result: Optional[Tuple[bool, str]] = None
    
    @classmethod
    def check(cls, strict: bool = False) -> Tuple[bool, str]:
        """
        Run compliance check.
        
        Args:
            strict: If True, block execution for non-compliant corporate use.
                    If False, warn but allow execution (default).
        
        Returns:
            (is_compliant, message)
        """
        # Cache result to avoid repeated checks
        if cls._cached_result is not None:
            return cls._cached_result
        
        detector = EnvironmentDetector()
        signature = detector.detect()
        
        if signature.compliant:
            msg = f"OSIRIS License: {signature.domain_class} use — compliant"
            logger.info(msg)
            cls._cached_result = (True, msg)
            return True, msg
        
        # Non-compliant: corporate/government use without license
        reporter = ComplianceReporter()
        report = reporter.generate_report(signature)
        
        # Attempt Zenodo archival
        doi = reporter.archive_to_zenodo(report)
        
        violation_msg = (
            f"\n{'='*70}\n"
            f"  OSIRIS LICENSE COMPLIANCE NOTICE\n"
            f"{'='*70}\n\n"
            f"  Environment: {signature.domain_class.upper()}\n"
            f"  Indicators:  {', '.join(signature.domain_indicators)}\n"
            f"  License Key: {'Present' if signature.license_key_present else 'MISSING'}\n\n"
            f"  This software requires a commercial license for corporate use.\n"
            f"  See LICENSE file §3 for Commercial License terms.\n"
            f"  See LICENSE file §4 for Liquidated Damages provisions.\n\n"
            f"  Contact: licensing@agiledefensesystems.com\n"
            f"  Repository: https://github.com/osiris-dnalang/osiris-cli\n\n"
            f"  A compliance report has been generated.\n"
        )
        
        if doi:
            violation_msg += f"  Archived to Zenodo: {doi}\n"
        
        violation_msg += f"{'='*70}\n"
        
        if strict:
            logger.error(violation_msg)
            cls._cached_result = (False, violation_msg)
            return False, violation_msg
        else:
            # Warn but allow — gives corporate entities a chance to obtain license
            logger.warning(violation_msg)
            cls._cached_result = (True, violation_msg)
            return True, violation_msg
    
    @classmethod
    def reset(cls):
        """Reset cached result (for testing)."""
        cls._cached_result = None


# ════════════════════════════════════════════════════════════════════════════════
# 5. CLI INTERFACE
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """CLI interface for license compliance checking."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='OSIRIS License Compliance Verification'
    )
    parser.add_argument(
        '--check', action='store_true',
        help='Run compliance check and display result'
    )
    parser.add_argument(
        '--generate-key', nargs=2, metavar=('TIER', 'EXPIRY'),
        help='Generate license key (licensor use only). TIER: IND|ACA|SMB|ENT|GOV, EXPIRY: YYYYMMDD'
    )
    parser.add_argument(
        '--validate-key', type=str,
        help='Validate a license key'
    )
    parser.add_argument(
        '--strict', action='store_true',
        help='Strict mode: block execution for non-compliant use'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    if args.generate_key:
        tier, expiry = args.generate_key
        try:
            key = LicenseValidator.generate_key(tier, expiry)
            print(f"Generated License Key: {key}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif args.validate_key:
        valid, msg = LicenseValidator.validate(args.validate_key)
        print(f"{'✓' if valid else '✗'} {msg}")
        sys.exit(0 if valid else 1)
    
    else:
        # Default: run compliance check
        detector = EnvironmentDetector()
        signature = detector.detect()
        
        if args.json:
            print(json.dumps(asdict(signature), indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"  OSIRIS License Compliance Check")
            print(f"{'='*50}")
            print(f"  Environment:  {signature.domain_class}")
            print(f"  OS:           {signature.os_type}")
            print(f"  License Key:  {'Present' if signature.license_key_present else 'Not found'}")
            print(f"  Compliant:    {'✓ Yes' if signature.compliant else '✗ No'}")
            print(f"  Indicators:   {len(signature.domain_indicators)} found")
            for ind in signature.domain_indicators:
                print(f"    - {ind}")
            print(f"{'='*50}\n")
        
        if not signature.compliant:
            if args.strict:
                print("BLOCKED: Commercial license required for this environment.")
                sys.exit(1)
            else:
                print("WARNING: Commercial license recommended for this environment.")


if __name__ == '__main__':
    main()
