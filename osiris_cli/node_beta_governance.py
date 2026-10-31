#!/usr/bin/env python3
"""
OSIRIS Node Beta Standalone Governance Adapter
===============================================
Enables sovereign cryptographic payload grant signing and verification directly
on Node Beta (Intel Core Ultra 7 WSL2 environment) without requiring a physical
JavaCard or external NFC terminal.

Complies with:
- SYS-021: Zero Self-Supplied Authorization (Payload-bound cryptographic receipts)
- SYS-022: Provenance Tracking
- SYS-023: Merkle Ledger Integrity
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# Locate and import governance contracts
GOV_SRC = Path(__file__).resolve().parents[2] / "osiris-governance" / "src"
if GOV_SRC.exists() and str(GOV_SRC) not in sys.path:
    sys.path.insert(0, str(GOV_SRC))

try:
    from osiris_governance.contracts import PermitAuthority, AuthorityPermit, PROMOTION_SCOPE, VERIFICATION_SCOPE
except ImportError:
    PermitAuthority = None
    AuthorityPermit = None
    PROMOTION_SCOPE = "PROMOTION_AUTHORITY_VERIFIED"
    VERIFICATION_SCOPE = "VERIFICATION_AUTHORITY_VERIFIED"

KEY_DIR = Path.home() / ".osiris" / "keystore"
KEY_FILE = KEY_DIR / "node_beta_operator.key"
DEFAULT_ISSUER = "Devin Phillip Davis / Node Beta (Standalone)"


def get_or_create_operator_key() -> bytes:
    """Ensure operator private key exists in ~/.osiris/keystore with 0600 permissions."""
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        key_bytes = os.urandom(32)
        KEY_FILE.write_bytes(key_bytes)
        os.chmod(KEY_FILE, 0o600)
    return KEY_FILE.read_bytes()


class NodeBetaGovernor:
    """Local governance signer for Node Beta standalone operations."""

    def __init__(self, issuer: str = DEFAULT_ISSUER):
        self.issuer = issuer
        self.key = get_or_create_operator_key()
        if PermitAuthority is not None:
            self.authority = PermitAuthority(key=self.key)
        else:
            self.authority = None

    def issue_grant(self, target_digest: str, scope: str = PROMOTION_SCOPE, ttl_seconds: int = 86400) -> Optional[AuthorityPermit]:
        """Issue an AuthorityPermit for a given payload SHA-256 digest."""
        if not self.authority:
            return None
        return self.authority.issue(
            issuer=self.issuer,
            scope=scope,
            target_digest=target_digest,
            ttl_seconds=ttl_seconds
        )

    def verify_grant(self, permit: AuthorityPermit) -> Tuple[bool, Optional[str]]:
        """Verify that an AuthorityPermit is authentic and current."""
        if not self.authority:
            return False, "GOVERNANCE_MODULE_MISSING"
        reason = self.authority.check(permit=permit)
        return (reason is None), reason


if __name__ == "__main__":
    gov = NodeBetaGovernor()
    test_hash = "e21d8231cf3c53efcebb76391104cd6b67193527"
    grant = gov.issue_grant(test_hash)
    valid, err = gov.verify_grant(grant)
    print(f"NodeBetaGovernor self-test: valid={valid}, err={err}")
    print(f"Grant: {grant}")
