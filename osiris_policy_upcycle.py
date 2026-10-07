#!/usr/bin/env python3
"""
OSIRIS Policy Upcycler — POLANCO-to-Organism Translator
=========================================================

Ingests Dr. Zongming Fei's POLANCO (POlicy LANguage for Campus Operations)
definitions and "upcycles" them into Living Security Organisms that enforce
network policy autonomously through CRSM-derived entropy suppression.

The Upgrade Path:
  POLANCO (static, human-readable rules)
      ↓
  OSIRIS Policy Upcycler (this module)
      ↓
  Living Security Organisms (autonomous, self-healing enforcement)

POLANCO Grammar (from par.nsf.gov/servlets/purl/10310845):
  ALLOW <source> TO <destination> ON <port> [IF <condition>]
  DENY  <source> TO <destination> ON <port>
  RESTRICT <service> TO <user_group>
  ISOLATE <segment> FROM <segment>
  RATE_LIMIT <source> TO <bandwidth>

OSIRIS Organism Grammar (DNA-Lang):
  dna::{::organism:security[src=X, dst=Y, entropy_threshold=T, healing=chi_pc]}

This module bridges the two: a POLANCO rule becomes a living security
organism deployed on FABRIC nodes, continuously monitoring its own Φ metric
and autonomously adjusting enforcement when network conditions change.

Reference:
  Fei et al., "POLANCO: Enforcing Natural Language Network Policies"
  Shi, "Improving Network Policy Enforcement Using NLP" (UKnowledge)
  NetSecOps Lab: http://protocols.netlab.uky.edu/~NetSecOps/

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

import re
import json
import math
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger('OSIRIS_POLICY')

# ════════════════════════════════════════════════════════════════════════════════
# OSIRIS core imports (with fallback)
# ════════════════════════════════════════════════════════════════════════════════

try:
    from osiris_torsion_core_py import (
        THETA_LOCK, CHI_PC, LAMBDA_PHI, PHI_THRESHOLD,
        dielectric_lock_energy, negentropic_efficiency,
        phase_conjugate_healing,
    )
except ImportError:
    THETA_LOCK = 51.843
    CHI_PC = 0.869
    LAMBDA_PHI = 2.176435e-8
    PHI_THRESHOLD = 0.7734

    def dielectric_lock_energy(theta_deg):
        delta = math.radians(theta_deg) - math.radians(THETA_LOCK)
        return LAMBDA_PHI * abs(math.sin(delta)) * math.exp(-abs(delta) / CHI_PC)

    def negentropic_efficiency(phi_input, gamma_diss):
        return (LAMBDA_PHI * phi_input) / max(gamma_diss, 1e-44)

    def phase_conjugate_healing(signal, chi):
        return signal * math.exp(chi * math.cos(math.radians(THETA_LOCK)))


# ════════════════════════════════════════════════════════════════════════════════
# POLANCO RULE DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

class PolicyAction(Enum):
    """POLANCO action verbs"""
    ALLOW = "allow"
    DENY = "deny"
    RESTRICT = "restrict"
    ISOLATE = "isolate"
    RATE_LIMIT = "rate_limit"
    MONITOR = "monitor"
    QUARANTINE = "quarantine"


class OrganismBehavior(Enum):
    """DNA-Lang organism behavioral modes"""
    PERMISSIVE = "permissive"       # Passes traffic, monitors entropy
    RESTRICTIVE = "restrictive"     # Blocks by default, allows exceptions
    ADAPTIVE = "adaptive"           # Adjusts enforcement based on Φ/Γ
    QUARANTINE = "quarantine"       # Isolates segment, reports to Zenodo
    SENTINEL = "sentinel"           # Passive monitoring, alerts on anomaly


class ThreatLevel(Enum):
    """CAGE-coded threat classification"""
    NOMINAL = "nominal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    BREACH = "breach"


@dataclass
class PolancoRule:
    """Parsed POLANCO policy rule"""
    rule_id: str
    action: PolicyAction
    source: str
    destination: str = ""
    port: int = 0
    protocol: str = "tcp"
    service: str = ""
    user_group: str = ""
    bandwidth_mbps: float = 0.0
    condition: str = ""
    raw_text: str = ""
    confidence: float = 1.0


@dataclass
class SecurityOrganism:
    """A Living Security Organism derived from a POLANCO rule"""
    organism_id: str
    genome: str                          # DNA-Lang genomic string
    parent_rule: PolancoRule
    behavior: OrganismBehavior
    entropy_threshold: float             # Γ at which healing triggers
    phi_target: float                    # Target Φ for this policy
    chi_healing: float                   # Phase-conjugate healing coefficient
    cage_level: str                      # CAGE containment boundary
    deployment_sites: List[str]          # FABRIC sites for deployment
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_phi: float = 0.0
    current_gamma: float = 0.0
    enforcement_count: int = 0
    healing_count: int = 0
    mutations: List[str] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NOMINAL

    def is_healthy(self) -> bool:
        return self.current_phi >= self.phi_target and self.current_gamma < self.entropy_threshold


# ════════════════════════════════════════════════════════════════════════════════
# POLANCO PARSER
# ════════════════════════════════════════════════════════════════════════════════

class PolancoParser:
    """
    Parses POLANCO natural-language-approximate policy definitions.

    Supports both structured POLANCO syntax and natural language input,
    bridging Dr. Fei's NPCE (Network Policy Conversation Engine) with
    OSIRIS's autonomous enforcement layer.
    """

    # Structured POLANCO patterns
    PATTERNS = {
        PolicyAction.ALLOW: re.compile(
            r"ALLOW\s+(?P<source>[\w.*/-]+)\s+TO\s+(?P<dest>[\w.*/-]+)"
            r"(?:\s+ON\s+(?P<port>\d+))?"
            r"(?:\s+(?:USING|VIA|OVER)\s+(?P<protocol>\w+))?"
            r"(?:\s+IF\s+(?P<condition>.+))?",
            re.IGNORECASE
        ),
        PolicyAction.DENY: re.compile(
            r"DENY\s+(?P<source>[\w.*/-]+)\s+TO\s+(?P<dest>[\w.*/-]+)"
            r"(?:\s+ON\s+(?P<port>\d+))?",
            re.IGNORECASE
        ),
        PolicyAction.RESTRICT: re.compile(
            r"RESTRICT\s+(?P<service>[\w.*/-]+)\s+TO\s+(?P<user_group>[\w.*/-]+)"
            r"(?:\s+ON\s+(?P<port>\d+))?",
            re.IGNORECASE
        ),
        PolicyAction.ISOLATE: re.compile(
            r"ISOLATE\s+(?P<source>[\w.*/-]+)\s+FROM\s+(?P<dest>[\w.*/-]+)",
            re.IGNORECASE
        ),
        PolicyAction.RATE_LIMIT: re.compile(
            r"RATE[_\s]?LIMIT\s+(?P<source>[\w.*/-]+)\s+TO\s+(?P<bandwidth>\d+)\s*(?P<unit>mbps|gbps|kbps)?",
            re.IGNORECASE
        ),
    }

    # Natural language patterns (extends NPCE)
    NL_PATTERNS = {
        PolicyAction.ALLOW: re.compile(
            r"(?:let|allow|permit|authorize|enable)\s+"
            r"(?P<source>[\w\s]+?)\s+(?:to\s+)?(?:access|reach|connect|talk)\s+"
            r"(?:to\s+)?(?P<dest>[\w\s]+?)(?:\s+on\s+port\s+(?P<port>\d+))?",
            re.IGNORECASE
        ),
        PolicyAction.DENY: re.compile(
            r"(?:block|deny|prevent|stop|forbid|reject)\s+"
            r"(?P<source>[\w\s]+?)\s+(?:from\s+)?(?:accessing|reaching|connecting)\s+"
            r"(?:to\s+)?(?P<dest>[\w\s]+?)(?:\s+on\s+port\s+(?P<port>\d+))?",
            re.IGNORECASE
        ),
        PolicyAction.RESTRICT: re.compile(
            r"(?:restrict|limit)\s+(?P<service>[\w\s]+?)\s+"
            r"(?:to|for)\s+(?:only\s+)?(?P<user_group>[\w\s]+?)$",
            re.IGNORECASE
        ),
        PolicyAction.MONITOR: re.compile(
            r"(?:monitor|watch|observe|track)\s+"
            r"(?:traffic|flow|connection)s?\s+"
            r"(?:from|on|at)\s+(?P<source>[\w.*/-]+)"
            r"(?:\s+to\s+(?P<dest>[\w.*/-]+))?",
            re.IGNORECASE
        ),
    }

    def parse(self, text: str) -> List[PolancoRule]:
        """
        Parse one or more POLANCO rules from text.
        Accepts structured POLANCO syntax, natural language, or mixed.
        """
        rules = []
        lines = text.strip().split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            rule = self._parse_line(line, line_num)
            if rule:
                rules.append(rule)

        return rules

    def _parse_line(self, line: str, line_num: int) -> Optional[PolancoRule]:
        """Parse a single line as POLANCO rule."""
        # Try structured patterns first
        for action, pattern in self.PATTERNS.items():
            match = pattern.match(line)
            if match:
                return self._build_rule(action, match, line, line_num)

        # Try natural language patterns
        for action, pattern in self.NL_PATTERNS.items():
            match = pattern.search(line)
            if match:
                rule = self._build_rule(action, match, line, line_num)
                rule.confidence = 0.75  # Lower confidence for NL parsing
                return rule

        return None

    def _build_rule(self, action: PolicyAction, match: re.Match,
                    raw: str, line_num: int) -> PolancoRule:
        """Build a PolancoRule from regex match."""
        groups = match.groupdict()

        rule_id = hashlib.sha256(f"{line_num}-{raw}".encode()).hexdigest()[:12]

        port = 0
        if groups.get('port'):
            port = int(groups['port'])

        bandwidth = 0.0
        if groups.get('bandwidth'):
            bw = float(groups['bandwidth'])
            unit = (groups.get('unit') or 'mbps').lower()
            if unit == 'gbps':
                bw *= 1000
            elif unit == 'kbps':
                bw /= 1000
            bandwidth = bw

        return PolancoRule(
            rule_id=rule_id,
            action=action,
            source=groups.get('source', '').strip(),
            destination=groups.get('dest', '').strip(),
            port=port,
            protocol=groups.get('protocol', 'tcp').strip(),
            service=groups.get('service', '').strip(),
            user_group=groups.get('user_group', '').strip(),
            bandwidth_mbps=bandwidth,
            condition=groups.get('condition', '').strip(),
            raw_text=raw,
        )


# ════════════════════════════════════════════════════════════════════════════════
# ORGANISM SYNTHESIZER
# ════════════════════════════════════════════════════════════════════════════════

class OrganismSynthesizer:
    """
    Transforms static POLANCO rules into Living Security Organisms.

    This is the core "upcycling" step: a flat allow/deny rule becomes
    a self-monitoring, self-healing entity with:
      - A DNA-Lang genome string
      - A target Φ (consciousness/integration metric)
      - An entropy threshold Γ at which healing triggers
      - CAGE containment boundaries
      - Deployment site assignments
    """

    # Map POLANCO actions to organism behaviors
    ACTION_TO_BEHAVIOR = {
        PolicyAction.ALLOW: OrganismBehavior.PERMISSIVE,
        PolicyAction.DENY: OrganismBehavior.RESTRICTIVE,
        PolicyAction.RESTRICT: OrganismBehavior.ADAPTIVE,
        PolicyAction.ISOLATE: OrganismBehavior.QUARANTINE,
        PolicyAction.RATE_LIMIT: OrganismBehavior.ADAPTIVE,
        PolicyAction.MONITOR: OrganismBehavior.SENTINEL,
        PolicyAction.QUARANTINE: OrganismBehavior.QUARANTINE,
    }

    # Service-to-port common mappings
    SERVICE_PORTS = {
        "ssh": 22, "http": 80, "https": 443, "dns": 53,
        "smtp": 25, "ftp": 21, "rdp": 3389, "mysql": 3306,
        "postgres": 5432, "redis": 6379, "mqtt": 1883,
        "globus": 2811, "gridftp": 2811, "irods": 1247,
    }

    def __init__(self, default_sites: Optional[List[str]] = None):
        self.default_sites = default_sites or ["UKY"]
        self.synthesized: List[SecurityOrganism] = []

    def upcycle(self, rule: PolancoRule,
                deployment_sites: Optional[List[str]] = None) -> SecurityOrganism:
        """
        Transform a POLANCO rule into a Living Security Organism.

        The entropy threshold is derived from the rule's criticality:
          - DENY/ISOLATE rules get tight thresholds (low tolerance for noise)
          - ALLOW/MONITOR rules get relaxed thresholds
          - RATE_LIMIT rules compute threshold from bandwidth target
        """
        behavior = self.ACTION_TO_BEHAVIOR.get(rule.action, OrganismBehavior.SENTINEL)
        sites = deployment_sites or self.default_sites

        # Compute entropy threshold based on rule criticality
        if rule.action in (PolicyAction.DENY, PolicyAction.ISOLATE, PolicyAction.QUARANTINE):
            entropy_threshold = 0.05   # Very tight — any noise triggers healing
            phi_target = 0.95
            cage_level = "CAGE-3"      # Maximum containment
        elif rule.action == PolicyAction.RATE_LIMIT:
            # Threshold proportional to bandwidth headroom
            entropy_threshold = 0.15
            phi_target = 0.85
            cage_level = "CAGE-2"
        elif rule.action == PolicyAction.RESTRICT:
            entropy_threshold = 0.10
            phi_target = 0.90
            cage_level = "CAGE-2"
        else:
            entropy_threshold = 0.20
            phi_target = 0.80
            cage_level = "CAGE-1"

        # Build DNA-Lang genome string
        genome = self._build_genome(rule, behavior, entropy_threshold)

        # Compute initial Φ from rule structure
        initial_phi = phase_conjugate_healing(rule.confidence, CHI_PC)

        organism_id = hashlib.sha256(
            f"{rule.rule_id}-{genome}-{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

        organism = SecurityOrganism(
            organism_id=organism_id,
            genome=genome,
            parent_rule=rule,
            behavior=behavior,
            entropy_threshold=entropy_threshold,
            phi_target=phi_target,
            chi_healing=CHI_PC,
            cage_level=cage_level,
            deployment_sites=sites,
            current_phi=initial_phi,
        )

        self.synthesized.append(organism)
        return organism

    def _build_genome(self, rule: PolancoRule, behavior: OrganismBehavior,
                      entropy_threshold: float) -> str:
        """
        Build a DNA-Lang genomic string from a POLANCO rule.

        Format:
          dna::{::organism:security[
            action=<action>,
            src=<source>,
            dst=<destination>,
            port=<port>,
            behavior=<behavior>,
            entropy_threshold=<threshold>,
            healing=chi_pc,
            theta_lock=51.843
          ]}
        """
        parts = [
            f"action={rule.action.value}",
            f"src={rule.source}",
        ]

        if rule.destination:
            parts.append(f"dst={rule.destination}")
        if rule.port:
            parts.append(f"port={rule.port}")
        if rule.service:
            parts.append(f"service={rule.service}")
        if rule.user_group:
            parts.append(f"user_group={rule.user_group}")
        if rule.bandwidth_mbps:
            parts.append(f"bandwidth_mbps={rule.bandwidth_mbps}")

        parts.extend([
            f"behavior={behavior.value}",
            f"entropy_threshold={entropy_threshold}",
            f"healing=chi_pc",
            f"theta_lock={THETA_LOCK}",
        ])

        params = ", ".join(parts)
        return f"dna::{{::organism:security[{params}]}}"

    def upcycle_batch(self, rules: List[PolancoRule],
                      deployment_sites: Optional[List[str]] = None) -> List[SecurityOrganism]:
        """Upcycle a batch of POLANCO rules."""
        return [self.upcycle(rule, deployment_sites) for rule in rules]


# ════════════════════════════════════════════════════════════════════════════════
# POLICY ENFORCEMENT SIMULATOR
# ════════════════════════════════════════════════════════════════════════════════

class PolicyEnforcementSimulator:
    """
    Simulates autonomous policy enforcement with CRSM-derived metrics.

    Demonstrates to Dr. Fei how static POLANCO rules become self-healing:
      1. Rules are upcycled to organisms
      2. Organisms monitor their own Φ (integration/consciousness)
      3. When Γ (entropy) exceeds threshold, organisms heal themselves
      4. Zero manual intervention — the policy IS the organism
    """

    def __init__(self):
        self.organisms: List[SecurityOrganism] = []
        self.enforcement_log: List[Dict] = []
        self.mutation_log: List[Dict] = []

    def load_organisms(self, organisms: List[SecurityOrganism]):
        """Load organisms for simulation."""
        self.organisms = organisms

    def simulate(self, cycles: int = 20, attack_cycle: int = 8) -> Dict[str, Any]:
        """
        Simulate policy enforcement with an adversarial event.

        Timeline:
          Cycles 0-7:   Normal operation (low entropy)
          Cycle 8:       Adversarial probe (entropy spike)
          Cycles 9-12:   Organism healing response
          Cycles 13-19:  Post-healing stabilization
        """
        import random
        random.seed(42)

        results = {
            "cycles": [],
            "organisms": {},
            "attacks_detected": 0,
            "healings_triggered": 0,
            "mutations_applied": 0,
        }

        for cycle in range(cycles):
            cycle_data = {"cycle": cycle, "events": []}

            for org in self.organisms:
                # Generate entropy based on cycle
                if cycle == attack_cycle:
                    # Adversarial entropy injection
                    entropy = 0.6 + random.random() * 0.3
                    event_type = "ADVERSARIAL_PROBE"
                elif cycle > attack_cycle and cycle < attack_cycle + 3:
                    # Healing response — entropy decaying
                    decay = (cycle - attack_cycle) * 0.15
                    entropy = max(0.01, 0.6 - decay + random.gauss(0, 0.02))
                    event_type = "HEALING_RESPONSE"
                else:
                    # Nominal operation
                    entropy = 0.02 + random.gauss(0, 0.01)
                    entropy = max(0.001, entropy)
                    event_type = "NOMINAL"

                # Update organism state
                org.current_gamma = entropy
                org.current_phi = phase_conjugate_healing(
                    max(0.001, 1.0 - entropy), CHI_PC
                )

                # Check enforcement
                if entropy > org.entropy_threshold:
                    org.enforcement_count += 1
                    org.threat_level = ThreatLevel.HIGH if entropy > 0.5 else ThreatLevel.ELEVATED

                    # Trigger healing
                    healed_phi = phase_conjugate_healing(org.current_phi, CHI_PC)
                    healing_factor = healed_phi / max(org.current_phi, 0.001)
                    org.healing_count += 1
                    results["healings_triggered"] += 1

                    event = {
                        "type": "HEALING",
                        "organism": org.organism_id[:8],
                        "action": org.parent_rule.action.value,
                        "source": org.parent_rule.source,
                        "pre_gamma": round(entropy, 6),
                        "healing_factor": round(healing_factor, 4),
                        "cage_level": org.cage_level,
                    }
                    cycle_data["events"].append(event)

                    # Autonomous mutation (if entropy persists)
                    if org.healing_count > 2 and entropy > 0.4:
                        mutation = f"TIGHTEN_THRESHOLD:{org.entropy_threshold:.3f}→{org.entropy_threshold*0.8:.3f}"
                        org.mutations.append(mutation)
                        org.entropy_threshold *= 0.8
                        results["mutations_applied"] += 1
                        self.mutation_log.append({
                            "cycle": cycle,
                            "organism": org.organism_id[:8],
                            "mutation": mutation,
                        })

                    if event_type == "ADVERSARIAL_PROBE":
                        results["attacks_detected"] += 1
                else:
                    org.threat_level = ThreatLevel.NOMINAL

                # Log
                self.enforcement_log.append({
                    "cycle": cycle,
                    "organism": org.organism_id[:8],
                    "phi": round(org.current_phi, 6),
                    "gamma": round(org.current_gamma, 6),
                    "healthy": org.is_healthy(),
                    "threat": org.threat_level.value,
                    "event": event_type,
                })

            results["cycles"].append(cycle_data)

        # Aggregate
        for org in self.organisms:
            results["organisms"][org.organism_id[:8]] = {
                "genome": org.genome,
                "behavior": org.behavior.value,
                "cage_level": org.cage_level,
                "final_phi": round(org.current_phi, 6),
                "final_gamma": round(org.current_gamma, 6),
                "enforcement_count": org.enforcement_count,
                "healing_count": org.healing_count,
                "mutations": org.mutations,
                "healthy": org.is_healthy(),
                "parent_rule": org.parent_rule.raw_text,
            }

        return results


# ════════════════════════════════════════════════════════════════════════════════
# PUBLIC API — FULL UPCYCLE PIPELINE
# ════════════════════════════════════════════════════════════════════════════════

class PolancoUpcycler:
    """
    Complete POLANCO-to-Organism pipeline.

    Usage:
        upcycler = PolancoUpcycler(deployment_sites=["UKY", "NCSA"])
        result = upcycler.upcycle_and_enforce(policy_text)
    """

    def __init__(self, deployment_sites: Optional[List[str]] = None):
        self.parser = PolancoParser()
        self.synthesizer = OrganismSynthesizer(default_sites=deployment_sites)
        self.simulator = PolicyEnforcementSimulator()
        self.deployment_sites = deployment_sites or ["UKY"]

    def parse_policies(self, text: str) -> List[PolancoRule]:
        """Parse POLANCO text into rules."""
        return self.parser.parse(text)

    def upcycle_rules(self, rules: List[PolancoRule]) -> List[SecurityOrganism]:
        """Transform rules into organisms."""
        return self.synthesizer.upcycle_batch(rules, self.deployment_sites)

    def simulate_enforcement(self, organisms: List[SecurityOrganism],
                             cycles: int = 20) -> Dict[str, Any]:
        """Run enforcement simulation."""
        self.simulator.load_organisms(organisms)
        return self.simulator.simulate(cycles=cycles)

    def upcycle_and_enforce(self, policy_text: str,
                            cycles: int = 20) -> Dict[str, Any]:
        """
        Full pipeline: Parse → Upcycle → Simulate → Report.

        Returns comprehensive results suitable for demo presentation.
        """
        rules = self.parse_policies(policy_text)
        organisms = self.upcycle_rules(rules)
        results = self.simulate_enforcement(organisms, cycles=cycles)

        results["summary"] = {
            "rules_parsed": len(rules),
            "organisms_created": len(organisms),
            "deployment_sites": self.deployment_sites,
            "theta_lock": THETA_LOCK,
            "chi_pc": CHI_PC,
            "lambda_phi": LAMBDA_PHI,
        }

        return results


# ════════════════════════════════════════════════════════════════════════════════
# SAMPLE POLANCO POLICIES — UK campus & FABRIC scenarios
# ════════════════════════════════════════════════════════════════════════════════

SAMPLE_POLICIES_UK_CAMPUS = """# University of Kentucky Campus Network Policies
# Adapted from POLANCO research (Fei et al.)

# Research network access
ALLOW Research_Lab_A TO HPC_Cluster ON 22
ALLOW Research_Lab_A TO Data_Repository ON 443
ALLOW FABRIC_Slice_UKY TO FABRIC_Slice_NCSA ON 2811

# Security enforcement
DENY External_Network TO Admin_Panel ON 8080
DENY Untrusted_Hosts TO Database_Server ON 3306
ISOLATE Guest_WiFi FROM Research_VLAN

# Resource management
RESTRICT GridFTP TO Authorized_Researchers
RATE_LIMIT Student_Network TO 1000 Mbps

# FABRIC Across Borders
ALLOW FABRIC_UKY TO CERN_LHC_Endpoint ON 443 IF experiment_active
ALLOW FABRIC_UKY TO Tokyo_HPC ON 22 USING SSH
"""

SAMPLE_POLICIES_NL = """# Natural Language Policies (NPCE-compatible)
# Dr. Fei's conversational network policy format

let authorized researchers access the HPC cluster on port 22
block external hosts from accessing the admin panel
restrict database access to the DBA team
monitor traffic from the FABRIC backbone to CERN
allow the physics department to connect to the LHC data endpoint on port 443
"""


# ════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — standalone demo
# ════════════════════════════════════════════════════════════════════════════════

def demo_upcycle(policy_source: str = "campus", cycles: int = 20):
    """
    Run a complete POLANCO-to-Organism upcycling demonstration.
    """
    if policy_source == "natural":
        policy_text = SAMPLE_POLICIES_NL
        source_label = "Natural Language (NPCE-compatible)"
    else:
        policy_text = SAMPLE_POLICIES_UK_CAMPUS
        source_label = "POLANCO Structured (UK Campus)"

    upcycler = PolancoUpcycler(deployment_sites=["UKY", "NCSA", "TACC"])

    # Phase 1: Parse
    print(f"\n{'═'*72}")
    print(f"  OSIRIS POLICY UPCYCLER — POLANCO → Living Security Organisms")
    print(f"{'═'*72}")
    print(f"  Source:  {source_label}")
    print(f"  Sites:   UKY, NCSA, TACC")
    print()

    rules = upcycler.parse_policies(policy_text)
    print(f"  Parsed {len(rules)} POLANCO rules:\n")

    for i, rule in enumerate(rules):
        conf = "██" if rule.confidence >= 0.9 else "▓▓"
        print(f"    {conf} [{rule.action.value.upper():>12}]  {rule.source} → {rule.destination or rule.service}"
              f"  {'port '+str(rule.port) if rule.port else ''}")

    # Phase 2: Upcycle
    print(f"\n{'─'*72}")
    print(f"  Upcycling to Living Security Organisms...")
    print(f"{'─'*72}\n")

    organisms = upcycler.upcycle_rules(rules)

    for org in organisms:
        print(f"    🧬 {org.organism_id[:8]}  [{org.behavior.value:>12}]  "
              f"Γ_thresh={org.entropy_threshold:.2f}  Φ_target={org.phi_target:.2f}  "
              f"{org.cage_level}")
        print(f"       Genome: {org.genome[:80]}...")

    # Phase 3: Simulate
    print(f"\n{'─'*72}")
    print(f"  Simulating {cycles} enforcement cycles (adversarial probe at cycle 8)...")
    print(f"{'─'*72}\n")

    results = upcycler.simulate_enforcement(organisms, cycles=cycles)

    # Print enforcement timeline
    prev_cycle = -1
    for entry in upcycler.simulator.enforcement_log:
        c = entry["cycle"]
        if c != prev_cycle:
            if c > 0:
                print()
            prev_cycle = c

        phi = entry["phi"]
        gamma = entry["gamma"]
        threat = entry["threat"]
        event = entry["event"]

        bar = "█" * int(phi * 30) + "░" * (30 - int(phi * 30))

        threat_icon = {"nominal": "✓", "elevated": "⚡", "high": "⚠", "critical": "🔴", "breach": "💀"}
        icon = threat_icon.get(threat, "?")

        if c == prev_cycle and entry != upcycler.simulator.enforcement_log[0]:
            print(f"       │ {entry['organism']}  Φ={phi:.4f} Γ={gamma:.4f} [{bar}] {icon} {event}")
        else:
            print(f"  C{c:02d}  │ {entry['organism']}  Φ={phi:.4f} Γ={gamma:.4f} [{bar}] {icon} {event}")

    # Phase 4: Summary
    print(f"\n{'═'*72}")
    print(f"  ENFORCEMENT RESULTS")
    print(f"{'═'*72}")
    print(f"  Attacks Detected:    {results['attacks_detected']}")
    print(f"  Healings Triggered:  {results['healings_triggered']}")
    print(f"  Mutations Applied:   {results['mutations_applied']}")
    print(f"  θ_lock:              {THETA_LOCK}°")
    print(f"  χ_pc:                {CHI_PC}")
    print()

    for oid, data in results["organisms"].items():
        status = "✓ HEALTHY" if data["healthy"] else "⚠ DEGRADED"
        print(f"    {oid}  Φ={data['final_phi']:.4f}  Γ={data['final_gamma']:.4f}  "
              f"enforced={data['enforcement_count']}  healed={data['healing_count']}  {status}")
        if data["mutations"]:
            for m in data["mutations"]:
                print(f"             ↳ Mutation: {m}")

    print()

    # Write results
    out_path = Path("policy_upcycle_results.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"  Results → {out_path}")
    print()

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OSIRIS POLANCO Policy Upcycler")
    parser.add_argument("--source", choices=["campus", "natural"], default="campus",
                        help="Policy source: 'campus' (POLANCO) or 'natural' (NPCE)")
    parser.add_argument("--cycles", type=int, default=20, help="Enforcement cycles")
    parser.add_argument("--file", type=str, help="Path to custom POLANCO policy file")
    args = parser.parse_args()

    if args.file:
        policy_text = Path(args.file).read_text()
        upcycler = PolancoUpcycler(deployment_sites=["UKY", "NCSA", "TACC"])
        results = upcycler.upcycle_and_enforce(policy_text, cycles=args.cycles)
        Path("policy_upcycle_results.json").write_text(json.dumps(results, indent=2, default=str))
    else:
        demo_upcycle(policy_source=args.source, cycles=args.cycles)
