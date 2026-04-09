"""
Sentinel: PALS Sentinel System
==============================

Perforce & Capturing Sentinels for threat monitoring and response.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from ..organisms.organism import Organism


class ThreatLevel:
    """Threat level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Threat:
    """Detected threat."""
    
    def __init__(
        self,
        threat_id: str,
        level: str,
        source: str,
        description: str,
        timestamp: Optional[str] = None
    ):
        self.threat_id = threat_id
        self.level = level
        self.source = source
        self.description = description
        self.timestamp = timestamp or datetime.now().isoformat()
        self.mitigated = False
    
    def to_dict(self) -> dict:
        return {
            'threat_id': self.threat_id,
            'level': self.level,
            'source': self.source,
            'description': self.description,
            'timestamp': self.timestamp,
            'mitigated': self.mitigated
        }


class Sentinel:
    """PALS Sentinel for threat monitoring and defense.
    
    Attributes:
        organism: Protected organism
        monitoring: Whether actively monitoring
        threats: Detected threats
        response_callbacks: Threat response handlers
    """
    
    def __init__(self, organism: Organism):
        """Initialize sentinel.
        
        Args:
            organism: Organism to protect
        """
        self.organism = organism
        self.monitoring = False
        self.threats: List[Threat] = []
        self.response_callbacks: Dict[str, Callable] = {}
        self.events: List[Dict] = []
    
    def start_monitoring(self):
        """Start threat monitoring."""
        self.monitoring = True
        self._log_event("monitoring_started", {})
        self.organism._log_event("sentinel_monitoring", {"status": "started"})
    
    def stop_monitoring(self):
        """Stop threat monitoring."""
        self.monitoring = False
        self._log_event("monitoring_stopped", {})
        self.organism._log_event("sentinel_monitoring", {"status": "stopped"})
    
    def detect_threat(
        self,
        threat_id: str,
        level: str,
        source: str,
        description: str
    ) -> Threat:
        """Detect and register a threat.
        
        Args:
            threat_id: Unique threat identifier
            level: Threat level (low, medium, high, critical)
            source: Threat source
            description: Threat description
            
        Returns:
            Threat object
        """
        threat = Threat(threat_id, level, source, description)
        self.threats.append(threat)
        
        self._log_event("threat_detected", threat.to_dict())
        self.organism._log_event("threat_detected", threat.to_dict())
        
        # Auto-respond if critical
        if level == ThreatLevel.CRITICAL:
            self.respond_to_threat(threat)
        
        return threat
    
    def respond_to_threat(self, threat: Threat) -> bool:
        """Respond to detected threat.
        
        Args:
            threat: Threat to respond to
            
        Returns:
            True if successfully mitigated
        """
        # Check for registered callback
        if threat.level in self.response_callbacks:
            callback = self.response_callbacks[threat.level]
            callback(threat)
        
        # Default response: isolate and heal
        self.isolate_threat(threat)
        self.organism.self_heal()
        
        threat.mitigated = True
        
        self._log_event("threat_mitigated", {
            'threat_id': threat.threat_id,
            'level': threat.level
        })
        
        return True
    
    def isolate_threat(self, threat: Threat):
        """Isolate threat from organism.
        
        Args:
            threat: Threat to isolate
        """
        self._log_event("threat_isolated", {
            'threat_id': threat.threat_id
        })
    
    def register_response_handler(self, level: str, callback: Callable):
        """Register custom threat response handler.
        
        Args:
            level: Threat level to handle
            callback: Response callback function
        """
        self.response_callbacks[level] = callback
    
    def get_threat_summary(self) -> Dict[str, Any]:
        """Get summary of detected threats.
        
        Returns:
            Threat summary
        """
        total_threats = len(self.threats)
        mitigated = sum(1 for t in self.threats if t.mitigated)
        
        by_level = {}
        for threat in self.threats:
            by_level[threat.level] = by_level.get(threat.level, 0) + 1
        
        return {
            'organism': self.organism.name,
            'monitoring': self.monitoring,
            'total_threats': total_threats,
            'mitigated': mitigated,
            'active': total_threats - mitigated,
            'by_level': by_level
        }
    
    def _log_event(self, event_type: str, data: Dict):
        """Log sentinel event."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'data': data
        }
        self.events.append(event)
    
    def __repr__(self) -> str:
        return f"Sentinel(organism='{self.organism.name}', monitoring={self.monitoring}, threats={len(self.threats)})"
