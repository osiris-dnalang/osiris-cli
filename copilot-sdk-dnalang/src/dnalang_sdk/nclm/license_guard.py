"""
OSIRIS Commercial License Guard & Institutional Detection

Ensures OSIRIS is only used in compliant commercial contexts.
Detects and blocks usage on corporate and academic institution servers.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

import os
import socket
import subprocess
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime

# Commercial license
COMMERCIAL_LICENSE = """
OSIRIS COMMERCIAL LICENSE AGREEMENT (v1.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROPRIETARY & CONFIDENTIAL

© 2026 Agile Defense Systems — All Rights Reserved

This software is provided under exclusive commercial license.
Unauthorized use, reproduction, or distribution is strictly prohibited.

RESTRICTIONS:
  ✗ Corporate/Enterprise use requires explicit license agreement
  ✗ Academic institution use is STRICTLY PROHIBITED
  ✗ Government use requires DoD authorization (CAGE 9HUP5)
  ✗ Unauthorized commercial deployment will trigger automated shutdown
  ✗ License violations subject to legal action

APPROVED USAGE:
  ✓ Individual developer evaluation (non-commercial)
  ✓ Authorized corporate licensees
  ✓ U.S. Defense Department (authorized contractors)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Institutional detection patterns
CORPORATE_DOMAINS = {
    "microsoft.com", "google.com", "amazon.com", "ibm.com", "apple.com",
    "oracle.com", "salesforce.com", "adobe.com", "vmware.com", "cisco.com",
    "intel.com", "nvidia.com", "qualcomm.com", "broadcom.com", "amd.com",
    "meta.com", "openai.com", "anthropic.com", "deepmind.com",
    # Add enterprise patterns
    "company.com", "corp.com", "enterprise.com"
}

ACADEMIC_TLD = {".edu", ".ac.uk", ".ac.jp", ".edu.au", ".edu.cn"}

INSTITUTIONAL_INDICATORS = {
    "paths": [
        "/opt/cern/",
        "/usr/local/cern/",
        "/data/academic/",
        "/research/",
        "/university/",
        "/college/",
        "/mit/",
        "/stanford/",
        "/harvard/",
        "/berkeley/",
        "/caltech/",
    ],
    "env_vars": [
        "CERN_HOME",
        "UNIVERSITY",
        "COLLEGE",
        "ACADEMIC_LICENSE",
        "RESEARCH_MODE",
        "INSTITUTIONAL_USE",
    ],
    "users": [
        "researcher",
        "professor",
        "student",
        "admin",
        "root",  # Common on institutional servers
    ]
}


def detect_restricted_environment() -> Tuple[bool, str, Dict[str, str]]:
    """
    Detect if running in restricted environment (corporate/academic).
    
    Returns:
        (is_restricted, reason, details)
    """
    details = {}
    
    # 1. Check hostname
    try:
        hostname = socket.gethostname()
        details["hostname"] = hostname
        
        # Academic patterns
        if any(x in hostname.lower() for x in ["mit", "stanford", "harvard", "yale", "princeton", "cern", "uni", "college", "edu"]):
            return True, "Academic institution detected (hostname)", details
        
        # Corporate patterns
        if any(x in hostname.lower() for x in ["corp", "enterprise", "aws", "azure", "gcp", "company", "office"]):
            return True, "Corporate environment detected (hostname)", details
    except Exception as e:
        details["hostname_error"] = str(e)
    
    # 2. Check domain
    try:
        fqdn = socket.getfqdn()
        details["fqdn"] = fqdn
        
        # Check against known corporate domains
        for domain in CORPORATE_DOMAINS:
            if domain in fqdn.lower():
                return True, f"Restricted corporate domain detected: {domain}", details
        
        # Check academic TLDs
        for tld in ACADEMIC_TLD:
            if fqdn.lower().endswith(tld):
                return True, f"Academic institution TLD detected: {tld}", details
    except Exception as e:
        details["fqdn_error"] = str(e)
    
    # 3. Check filesystem paths
    for path in INSTITUTIONAL_INDICATORS["paths"]:
        if Path(path).exists():
            return True, f"Institutional path detected: {path}", {"institutional_path": path}
    
    # 4. Check environment variables
    for env_var in INSTITUTIONAL_INDICATORS["env_vars"]:
        if env_var in os.environ:
            return True, f"Institutional marker detected: {env_var}={os.environ[env_var]}", {env_var: os.environ[env_var]}
    
    # 5. Check current user
    try:
        current_user = os.environ.get("USER", "").lower()
        details["user"] = current_user
        
        if current_user in INSTITUTIONAL_INDICATORS["users"]:
            return True, f"Institutional user detected: {current_user}", details
    except Exception as e:
        details["user_error"] = str(e)
    
    # 6. Check process environment (detect container/VM attribution)
    try:
        if Path("/.dockerenv").exists():
            details["container"] = "Docker detected"
        if Path("/proc/sys/kernel/osrelease").exists():
            with open("/proc/sys/kernel/osrelease") as f:
                osrel = f.read().lower()
                if any(x in osrel for x in ["docker", "kubernetes", "container", "cern", "academic"]):
                    return True, f"Containerized academic/corporate environment detected", {"osrelease": osrel}
    except Exception:
        pass
    
    # 7. Check network configuration for institutional patterns
    try:
        result = subprocess.run(["hostname", "-d"], capture_output=True, text=True, timeout=2)
        domain = result.stdout.strip()
        details["domain_cmd"] = domain
        
        for tld in ACADEMIC_TLD:
            if domain.endswith(tld):
                return True, f"Academic domain detected via hostname -d", {"domain": domain}
    except Exception:
        pass
    
    return False, "", details


def enforce_commercial_license():
    """
    Enforce commercial license restrictions.
    Raises SystemExit if running in restricted environment.
    """
    is_restricted, reason, details = detect_restricted_environment()
    
    if is_restricted:
        print("\n" + "═" * 80)
        print("🛑 OSIRIS COMMERCIAL LICENSE RESTRICTION TRIGGERED")
        print("═" * 80)
        print(f"\n⚠️  {reason}")
        print("\nDetails:")
        for key, value in details.items():
            print(f"  • {key}: {value}")
        print("\n" + COMMERCIAL_LICENSE)
        print("\n❌ OSIRIS has detected restricted usage environment and is shutting down.")
        print("\n📧 To license OSIRIS for your organization:")
        print("   Contact: licensing@agilede defense-systems.com")
        print("   CAGE Code: 9HUP5")
        print("   Classification: Commercial / DoD Authorized")
        print("\n" + "═" * 80 + "\n")
        
        exit(1)


def get_license_info() -> Dict[str, str]:
    """Get current license information."""
    return {
        "type": "COMMERCIAL",
        "version": "1.0",
        "issued": "2026-04-06",
        "status": "ACTIVE",
        "restrictions": [
            "Corporate/Academic use prohibited without explicit agreement",
            "Institutional deployment triggers automatic shutdown",
            "License violations subject to legal action"
        ]
    }
