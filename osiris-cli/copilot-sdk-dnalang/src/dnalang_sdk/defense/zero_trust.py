"""
Zero Trust Verification
======================

Zero-trust security verification for organisms.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from ..organisms.organism import Organism


class ZeroTrust:
    """Zero-trust security verifier.
    
    Implements continuous verification of organism integrity and permissions.
    """
    
    def __init__(self):
        """Initialize zero-trust verifier."""
        self.verifications: List[Dict] = []
        self.trusted_domains: List[str] = []
        self.policies: Dict[str, Any] = {
            'min_lambda_phi': 1e-9,
            'max_gamma': 0.5,
            'require_genesis': True
        }
    
    def verify(self, organism: Organism) -> bool:
        """Verify organism against zero-trust policies.
        
        Args:
            organism: Organism to verify
            
        Returns:
            True if verification passed
        """
        checks = {
            'has_genesis': bool(organism.genesis),
            'valid_lambda_phi': organism.lambda_phi >= self.policies['min_lambda_phi'],
            'domain_trusted': organism.domain in self.trusted_domains if self.trusted_domains else True,
            'has_genome': len(organism.genome) > 0
        }
        
        passed = all(checks.values())
        
        verification = {
            'timestamp': datetime.now().isoformat(),
            'organism': organism.name,
            'passed': passed,
            'checks': checks
        }
        
        self.verifications.append(verification)
        organism._log_event("zero_trust_verification", verification)
        
        return passed
    
    def add_trusted_domain(self, domain: str):
        """Add domain to trusted list.
        
        Args:
            domain: Domain to trust
        """
        if domain not in self.trusted_domains:
            self.trusted_domains.append(domain)
    
    def set_policy(self, policy_name: str, value: Any):
        """Set security policy.
        
        Args:
            policy_name: Policy to set
            value: Policy value
        """
        self.policies[policy_name] = value
    
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get summary of verifications.
        
        Returns:
            Verification summary
        """
        if not self.verifications:
            return {
                'total_verifications': 0,
                'passed': 0,
                'failed': 0
            }
        
        passed = sum(1 for v in self.verifications if v['passed'])
        
        return {
            'total_verifications': len(self.verifications),
            'passed': passed,
            'failed': len(self.verifications) - passed,
            'success_rate': passed / len(self.verifications),
            'policies': self.policies,
            'trusted_domains': self.trusted_domains
        }
    
    def __repr__(self) -> str:
        return f"ZeroTrust(verifications={len(self.verifications)}, policies={len(self.policies)})"
