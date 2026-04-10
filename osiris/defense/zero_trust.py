"""
Zero Trust Verification
======================

Zero-trust security verification for OSIRIS subsystems.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class ZeroTrust:
    """Zero-trust security verifier with continuous verification."""

    def __init__(self):
        self.verifications: List[Dict] = []
        self.trusted_domains: List[str] = []
        self.policies: Dict[str, Any] = {
            "min_lambda_phi": 1e-9,
            "max_gamma": 0.5,
            "require_genesis": True,
        }

    def verify(self, name: str, metrics: Dict[str, Any]) -> bool:
        """Verify a subsystem against zero-trust policies.

        Args:
            name: Subsystem name
            metrics: Dict with lambda_phi, gamma, domain, has_genesis keys
        """
        checks = {
            "valid_lambda_phi": metrics.get("lambda_phi", 0) >= self.policies["min_lambda_phi"],
            "gamma_within_bounds": metrics.get("gamma", 1.0) <= self.policies["max_gamma"],
            "domain_trusted": (
                metrics.get("domain", "default") in self.trusted_domains
                if self.trusted_domains
                else True
            ),
        }
        if self.policies.get("require_genesis"):
            checks["has_genesis"] = bool(metrics.get("has_genesis", False))

        passed = all(checks.values())

        verification = {
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "passed": passed,
            "checks": checks,
        }
        self.verifications.append(verification)
        return passed

    def add_trusted_domain(self, domain: str):
        if domain not in self.trusted_domains:
            self.trusted_domains.append(domain)

    def set_policy(self, policy_name: str, value: Any):
        self.policies[policy_name] = value

    def get_verification_summary(self) -> Dict[str, Any]:
        if not self.verifications:
            return {"total_verifications": 0, "passed": 0, "failed": 0}
        passed = sum(1 for v in self.verifications if v["passed"])
        return {
            "total_verifications": len(self.verifications),
            "passed": passed,
            "failed": len(self.verifications) - passed,
            "success_rate": passed / len(self.verifications),
            "policies": self.policies,
            "trusted_domains": self.trusted_domains,
        }
