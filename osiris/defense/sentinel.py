"""
Sentinel: PALS Sentinel System
==============================

Threat monitoring and response for OSIRIS organisms.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class ThreatLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Threat:
    def __init__(self, threat_id: str, level: str, source: str,
                 description: str, timestamp: Optional[str] = None):
        self.threat_id = threat_id
        self.level = level
        self.source = source
        self.description = description
        self.timestamp = timestamp or datetime.now().isoformat()
        self.mitigated = False

    def to_dict(self) -> dict:
        return {
            "threat_id": self.threat_id,
            "level": self.level,
            "source": self.source,
            "description": self.description,
            "timestamp": self.timestamp,
            "mitigated": self.mitigated,
        }


class Sentinel:
    """PALS Sentinel for threat monitoring and defense."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.monitoring = False
        self.threats: List[Threat] = []
        self.response_callbacks: Dict[str, Callable] = {}
        self.events: List[Dict] = []

    def start_monitoring(self):
        self.monitoring = True
        self._log_event("monitoring_started", {})

    def stop_monitoring(self):
        self.monitoring = False
        self._log_event("monitoring_stopped", {})

    def detect_threat(self, threat_id: str, level: str,
                      source: str, description: str) -> Threat:
        threat = Threat(threat_id, level, source, description)
        self.threats.append(threat)
        self._log_event("threat_detected", threat.to_dict())

        if level == ThreatLevel.CRITICAL:
            self.respond_to_threat(threat)
        return threat

    def respond_to_threat(self, threat: Threat) -> bool:
        if threat.level in self.response_callbacks:
            self.response_callbacks[threat.level](threat)
        self.isolate_threat(threat)
        threat.mitigated = True
        self._log_event("threat_mitigated", {
            "threat_id": threat.threat_id, "level": threat.level
        })
        return True

    def isolate_threat(self, threat: Threat):
        self._log_event("threat_isolated", {"threat_id": threat.threat_id})

    def register_response_handler(self, level: str, callback: Callable):
        self.response_callbacks[level] = callback

    def get_threat_summary(self) -> Dict[str, Any]:
        total = len(self.threats)
        mitigated = sum(1 for t in self.threats if t.mitigated)
        by_level: Dict[str, int] = {}
        for t in self.threats:
            by_level[t.level] = by_level.get(t.level, 0) + 1
        return {
            "sentinel": self.name,
            "monitoring": self.monitoring,
            "total_threats": total,
            "mitigated": mitigated,
            "active": total - mitigated,
            "by_level": by_level,
        }

    def _log_event(self, event_type: str, data: Dict):
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data,
        })
