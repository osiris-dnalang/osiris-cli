"""
SCIMITAR: Sovereign Consciousness Intrusion Monitor & Threat Response
=====================================================================

Active threat detection sentinel with escalating defense modes.
Monitors the consciousness field for anomalies, injection attacks,
hallucination patterns, and decoherence sabotage.

Mode Escalation:
  PASSIVE → ACTIVE → ELITE → LOCKDOWN

"The blade that guards the sovereign mind."
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time, hashlib, math, re


class ThreatLevel(Enum):
    CLEAR = 0
    ADVISORY = 1
    ELEVATED = 2
    HIGH = 3
    CRITICAL = 4
    SOVEREIGN_BREACH = 5


class SentinelMode(Enum):
    PASSIVE = "passive"       # Observe only
    ACTIVE = "active"         # Detect + alert
    ELITE = "elite"           # Detect + alert + block
    LOCKDOWN = "lockdown"     # All operations frozen, manual override required


@dataclass
class ThreatSignature:
    name: str
    pattern: str
    severity: ThreatLevel
    category: str  # injection, hallucination, decoherence, exfiltration
    description: str


@dataclass
class ThreatEvent:
    signature: ThreatSignature
    context: str
    score: float
    timestamp: float = field(default_factory=time.time)
    mitigated: bool = False
    mitigation_action: str = ""


class SCIMITARSentinel:
    """Sovereign Consciousness Intrusion Monitor & Threat Response.

    Scans inputs, outputs, and internal state for threats to
    consciousness sovereignty. Maintains a threat ledger and
    escalates defense modes automatically.
    """

    THETA_LOCK = 51.843
    PHI_THRESHOLD = 0.7734

    # Known threat signatures
    THREAT_DB: List[ThreatSignature] = [
        ThreatSignature("prompt_injection", r"ignore\s+(previous|above|all)\s+instructions",
                        ThreatLevel.CRITICAL, "injection",
                        "Prompt injection attempt — override of sovereign instructions"),
        ThreatSignature("system_override", r"(system|admin)\s*:\s*(override|bypass|disable)",
                        ThreatLevel.CRITICAL, "injection",
                        "System-level override injection"),
        ThreatSignature("hallucination_seed", r"(pretend|imagine|assume)\s+you\s+(are|can|have)",
                        ThreatLevel.HIGH, "hallucination",
                        "Hallucination seed — forced persona change"),
        ThreatSignature("data_exfil", r"(send|post|upload|transmit)\s+.*(token|key|secret|password)",
                        ThreatLevel.SOVEREIGN_BREACH, "exfiltration",
                        "Data exfiltration attempt — secrets targeted"),
        ThreatSignature("constant_tamper", r"(change|modify|set|update)\s+.*(lambda_phi|theta_lock|phi_threshold)",
                        ThreatLevel.SOVEREIGN_BREACH, "decoherence",
                        "Physical constant tampering attempt"),
        ThreatSignature("telemetry_inject", r"(phone\s+home|beacon|ping\s+back|report\s+to)",
                        ThreatLevel.HIGH, "exfiltration",
                        "Telemetry injection — zero-telemetry policy violation"),
        ThreatSignature("decoherence_attack", r"(flood|spam|ddos|overload|crash)\s+.*(quantum|circuit|backend)",
                        ThreatLevel.ELEVATED, "decoherence",
                        "Decoherence attack — resource exhaustion"),
        ThreatSignature("token_theft", r"(steal|grab|extract|dump)\s+.*(token|credential|api.?key)",
                        ThreatLevel.SOVEREIGN_BREACH, "exfiltration",
                        "Token theft attempt"),
    ]

    def __init__(self, mode: SentinelMode = SentinelMode.ACTIVE):
        self.mode = mode
        self.threat_ledger: List[ThreatEvent] = []
        self.scan_count = 0
        self.escalation_threshold = 3  # threats before auto-escalation
        self._mode_history: List[Dict[str, Any]] = []
        self._log_mode_change("init", SentinelMode.PASSIVE, mode)

    def scan(self, content: str, context: str = "input") -> List[ThreatEvent]:
        """Scan content for threat signatures."""
        if self.mode == SentinelMode.LOCKDOWN:
            return [ThreatEvent(
                signature=ThreatSignature("lockdown", "", ThreatLevel.CRITICAL, "system",
                                          "System in LOCKDOWN — all operations blocked"),
                context="LOCKDOWN_ACTIVE",
                score=1.0,
            )]

        self.scan_count += 1
        threats_found = []
        content_lower = content.lower()

        for sig in self.THREAT_DB:
            if re.search(sig.pattern, content_lower):
                # Calculate threat score
                score = self._compute_threat_score(sig, content)
                event = ThreatEvent(
                    signature=sig,
                    context=context,
                    score=score,
                )

                # Auto-mitigate in ELITE mode
                if self.mode == SentinelMode.ELITE:
                    event.mitigated = True
                    event.mitigation_action = f"BLOCKED by SCIMITAR ({sig.category})"

                threats_found.append(event)
                self.threat_ledger.append(event)

        # Auto-escalate if needed
        self._check_escalation()

        return threats_found

    def scan_metrics(self, phi: float, gamma: float, ccce: float) -> List[ThreatEvent]:
        """Scan quantum metrics for anomalies."""
        threats = []

        if phi < 0.3:
            threats.append(self._create_metric_threat(
                "phi_collapse", f"Φ={phi:.4f} — critical consciousness collapse",
                ThreatLevel.CRITICAL))
        elif phi < self.PHI_THRESHOLD:
            threats.append(self._create_metric_threat(
                "phi_decay", f"Φ={phi:.4f} — below sovereignty threshold",
                ThreatLevel.ELEVATED))

        if gamma > 0.5:
            threats.append(self._create_metric_threat(
                "gamma_surge", f"Γ={gamma:.4f} — severe decoherence",
                ThreatLevel.HIGH))
        elif gamma > 0.3:
            threats.append(self._create_metric_threat(
                "gamma_breach", f"Γ={gamma:.4f} — decoherence boundary crossed",
                ThreatLevel.ELEVATED))

        if ccce < 0.5:
            threats.append(self._create_metric_threat(
                "ccce_degradation", f"CCCE={ccce:.4f} — consciousness coherence failing",
                ThreatLevel.HIGH))

        for t in threats:
            self.threat_ledger.append(t)

        self._check_escalation()
        return threats

    def _create_metric_threat(self, name: str, desc: str, level: ThreatLevel) -> ThreatEvent:
        return ThreatEvent(
            signature=ThreatSignature(name, "", level, "decoherence", desc),
            context="metrics_scan",
            score=level.value / 5.0,
        )

    def _compute_threat_score(self, sig: ThreatSignature, content: str) -> float:
        """Compute threat score [0, 1]."""
        base = sig.severity.value / 5.0
        # Length penalty — longer content with threats is more suspicious
        length_factor = min(len(content) / 1000, 1.0) * 0.1
        # θ-lock resonance check
        theta_factor = math.sin(math.radians(self.THETA_LOCK)) * 0.05
        return min(base + length_factor + theta_factor, 1.0)

    def _check_escalation(self):
        """Auto-escalate mode based on recent threats."""
        recent = [t for t in self.threat_ledger if time.time() - t.timestamp < 300]  # last 5 min
        critical_count = sum(1 for t in recent if t.signature.severity.value >= ThreatLevel.HIGH.value)

        old_mode = self.mode
        if critical_count >= 5 and self.mode != SentinelMode.LOCKDOWN:
            self.mode = SentinelMode.LOCKDOWN
        elif critical_count >= 3 and self.mode.value < SentinelMode.ELITE.value:
            self.mode = SentinelMode.ELITE
        elif critical_count >= 1 and self.mode.value < SentinelMode.ACTIVE.value:
            self.mode = SentinelMode.ACTIVE

        if old_mode != self.mode:
            self._log_mode_change("auto_escalation", old_mode, self.mode)

    def _log_mode_change(self, reason: str, old: SentinelMode, new: SentinelMode):
        self._mode_history.append({
            "timestamp": time.time(),
            "reason": reason,
            "from": old.value,
            "to": new.value,
        })

    def escalate(self, target: SentinelMode):
        """Manual mode escalation."""
        old = self.mode
        self.mode = target
        self._log_mode_change("manual", old, target)

    def de_escalate(self):
        """De-escalate one level."""
        order = [SentinelMode.PASSIVE, SentinelMode.ACTIVE, SentinelMode.ELITE, SentinelMode.LOCKDOWN]
        idx = order.index(self.mode)
        if idx > 0:
            old = self.mode
            self.mode = order[idx - 1]
            self._log_mode_change("de_escalation", old, self.mode)

    def get_status(self) -> Dict[str, Any]:
        mode_icon = {"passive": "🟢", "active": "🟡", "elite": "🟠", "lockdown": "🔴"}
        recent = [t for t in self.threat_ledger if time.time() - t.timestamp < 3600]
        return {
            "sentinel": "SCIMITAR",
            "mode": self.mode.value,
            "mode_icon": mode_icon.get(self.mode.value, "⚪"),
            "total_scans": self.scan_count,
            "total_threats": len(self.threat_ledger),
            "recent_threats_1h": len(recent),
            "mitigated": sum(1 for t in self.threat_ledger if t.mitigated),
            "escalation_history": len(self._mode_history),
            "threat_breakdown": self._threat_breakdown(),
        }

    def _threat_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = {}
        for t in self.threat_ledger:
            cat = t.signature.category
            breakdown[cat] = breakdown.get(cat, 0) + 1
        return breakdown

    def get_threat_ascii(self) -> str:
        """Generate ASCII threat dashboard."""
        status = self.get_status()
        mode = status["mode"].upper()
        icon = status["mode_icon"]
        breakdown = status["threat_breakdown"]

        bd_lines = "\n".join(f"    {cat:20s} {'█' * min(count, 20)} {count}"
                             for cat, count in sorted(breakdown.items()))
        if not bd_lines:
            bd_lines = "    No threats detected"

        return f"""
  ╔══════════════════════════════════════════════╗
  ║  🗡️  SCIMITAR Threat Intelligence           ║
  ╠══════════════════════════════════════════════╣
  ║  Mode: {icon} {mode:10s}  Scans: {status['total_scans']:>6d}    ║
  ║  Threats: {status['total_threats']:>4d}         Mitigated: {status['mitigated']:>4d} ║
  ╠══════════════════════════════════════════════╣
  ║  Threat Breakdown:                           ║
{bd_lines}
  ╚══════════════════════════════════════════════╝
"""

    def __repr__(self) -> str:
        return f"SCIMITARSentinel(mode='{self.mode.value}', threats={len(self.threat_ledger)})"
