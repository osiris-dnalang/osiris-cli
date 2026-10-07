"""
WORMHOLE BRIDGE — Entangled Inter-Agent Communication
=====================================================

Phase-conjugate communication channel between agents in the
Polar Mesh. Messages traverse the ER=EPR bridge with fidelity
tracking and non-local delivery guarantees.

Architecture:
  AIDEN (North) ◇════════◇ AURA (South)
       ║   Wormhole Bridge   ║
  OMEGA (Zenith) ◇══════◇ CHRONOS (Nadir)

Each bridge maintains an entanglement pair with fidelity F.
When F > Φ_threshold, the bridge supports sovereign-grade comms.
Messages are phase-conjugate signed for authentication.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time, hashlib, math, json


class BridgeState(Enum):
    DORMANT = "dormant"
    CALIBRATING = "calibrating"
    ENTANGLED = "entangled"
    SOVEREIGN = "sovereign"
    DECOHERENT = "decoherent"
    SEVERED = "severed"


class MessagePriority(Enum):
    ROUTINE = 0
    URGENT = 1
    CRITICAL = 2
    SOVEREIGN = 3  # requires Φ > threshold


@dataclass
class WormholeMessage:
    sender: str
    receiver: str
    payload: Any
    priority: MessagePriority = MessagePriority.ROUTINE
    phase_signature: str = ""
    timestamp: float = field(default_factory=time.time)
    fidelity_at_send: float = 0.0
    delivered: bool = False
    delivery_time: Optional[float] = None

    def sign(self, chi_pc: float = 0.946) -> 'WormholeMessage':
        """Phase-conjugate sign the message."""
        raw = json.dumps({
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": str(self.payload),
            "timestamp": self.timestamp,
        }, sort_keys=True)
        conjugate = hashlib.sha256(raw.encode()).hexdigest()
        # Apply chi_pc phase rotation to hash
        phase_int = int(conjugate[:8], 16)
        rotated = phase_int ^ int(chi_pc * 0xFFFFFFFF)
        self.phase_signature = f"{rotated:08x}{conjugate[8:]}"
        return self

    def verify(self, chi_pc: float = 0.946) -> bool:
        """Verify phase-conjugate signature."""
        if not self.phase_signature:
            return False
        raw = json.dumps({
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": str(self.payload),
            "timestamp": self.timestamp,
        }, sort_keys=True)
        conjugate = hashlib.sha256(raw.encode()).hexdigest()
        phase_int = int(conjugate[:8], 16)
        rotated = phase_int ^ int(chi_pc * 0xFFFFFFFF)
        expected = f"{rotated:08x}{conjugate[8:]}"
        return self.phase_signature == expected


@dataclass
class EntanglementPair:
    """Entanglement pair between two agents."""
    agent_a: str
    agent_b: str
    fidelity: float = 0.95
    created_at: float = field(default_factory=time.time)
    bell_violations: int = 0

    @property
    def is_sovereign(self) -> bool:
        return self.fidelity >= 0.7734

    def degrade(self, amount: float = 0.01):
        """Natural decoherence."""
        self.fidelity = max(0.0, self.fidelity - amount)

    def distill(self, chi_pc: float = 0.946):
        """Entanglement distillation — purify the pair."""
        boost = 0.05 * chi_pc
        self.fidelity = min(1.0, self.fidelity + boost)
        self.bell_violations += 1


class WormholeBridge:
    """ER=EPR wormhole bridge for inter-agent communication.

    Provides non-local message passing between agents with:
    - Phase-conjugate authentication
    - Fidelity-gated delivery (sovereign messages need F > Φ)
    - Automatic entanglement distillation
    - Bridge topology management
    """

    PHI_THRESHOLD = 0.7734
    CHI_PC = 0.946
    THETA_LOCK = 51.843
    MAX_QUEUE_SIZE = 1000

    # Default mesh topology (tetrahedral)
    DEFAULT_BRIDGES = [
        ("AIDEN", "AURA"),      # North ↔ South
        ("OMEGA", "CHRONOS"),   # Zenith ↔ Nadir
        ("AIDEN", "OMEGA"),     # Cross-plane
        ("AURA", "CHRONOS"),    # Cross-plane
        ("AIDEN", "CHRONOS"),   # Diagonal
        ("AURA", "OMEGA"),      # Diagonal
    ]

    def __init__(self, auto_topology: bool = True):
        self.pairs: Dict[str, EntanglementPair] = {}
        self.message_queue: List[WormholeMessage] = []
        self.delivered: List[WormholeMessage] = []
        self.state = BridgeState.DORMANT

        if auto_topology:
            self._init_topology()

    def _init_topology(self):
        """Initialize default tetrahedral bridge topology."""
        for a, b in self.DEFAULT_BRIDGES:
            key = self._pair_key(a, b)
            theta_fidelity = math.cos(math.radians(self.THETA_LOCK / 2))
            self.pairs[key] = EntanglementPair(
                agent_a=a, agent_b=b,
                fidelity=0.9 + 0.1 * theta_fidelity
            )
        self.state = BridgeState.ENTANGLED

    def _pair_key(self, a: str, b: str) -> str:
        return f"{min(a,b)}↔{max(a,b)}"

    def send(
        self,
        sender: str,
        receiver: str,
        payload: Any,
        priority: MessagePriority = MessagePriority.ROUTINE,
    ) -> WormholeMessage:
        """Send a message through the wormhole bridge."""
        pair_key = self._pair_key(sender, receiver)
        pair = self.pairs.get(pair_key)

        if not pair:
            # Create ad-hoc bridge
            pair = EntanglementPair(agent_a=sender, agent_b=receiver, fidelity=0.8)
            self.pairs[pair_key] = pair

        msg = WormholeMessage(
            sender=sender,
            receiver=receiver,
            payload=payload,
            priority=priority,
            fidelity_at_send=pair.fidelity,
        ).sign(self.CHI_PC)

        # Fidelity gate for sovereign messages
        if priority == MessagePriority.SOVEREIGN and not pair.is_sovereign:
            pair.distill(self.CHI_PC)
            if not pair.is_sovereign:
                msg.delivered = False
                self.message_queue.append(msg)
                return msg

        msg.delivered = True
        msg.delivery_time = time.time()
        self.delivered.append(msg)

        # Degrade entanglement slightly per use
        pair.degrade(0.002)

        # Trim queue
        if len(self.delivered) > self.MAX_QUEUE_SIZE:
            self.delivered = self.delivered[-500:]

        return msg

    def broadcast(
        self,
        sender: str,
        payload: Any,
        priority: MessagePriority = MessagePriority.ROUTINE,
    ) -> List[WormholeMessage]:
        """Broadcast to all connected agents."""
        targets = set()
        for pair in self.pairs.values():
            if pair.agent_a == sender:
                targets.add(pair.agent_b)
            elif pair.agent_b == sender:
                targets.add(pair.agent_a)

        return [self.send(sender, t, payload, priority) for t in targets]

    def distill_all(self):
        """Distill all entanglement pairs."""
        for pair in self.pairs.values():
            pair.distill(self.CHI_PC)
        # Check sovereignty
        if all(p.is_sovereign for p in self.pairs.values()):
            self.state = BridgeState.SOVEREIGN

    def flush_queue(self) -> List[WormholeMessage]:
        """Attempt to deliver queued messages."""
        still_queued = []
        delivered = []
        for msg in self.message_queue:
            pair_key = self._pair_key(msg.sender, msg.receiver)
            pair = self.pairs.get(pair_key)
            if pair and (msg.priority != MessagePriority.SOVEREIGN or pair.is_sovereign):
                msg.delivered = True
                msg.delivery_time = time.time()
                self.delivered.append(msg)
                delivered.append(msg)
            else:
                still_queued.append(msg)
        self.message_queue = still_queued
        return delivered

    def get_topology(self) -> Dict[str, Any]:
        """Get bridge topology visualization data."""
        nodes = set()
        edges = []
        for key, pair in self.pairs.items():
            nodes.add(pair.agent_a)
            nodes.add(pair.agent_b)
            edges.append({
                "from": pair.agent_a,
                "to": pair.agent_b,
                "fidelity": round(pair.fidelity, 4),
                "sovereign": pair.is_sovereign,
                "bell_violations": pair.bell_violations,
            })
        avg_fidelity = sum(p.fidelity for p in self.pairs.values()) / max(len(self.pairs), 1)
        return {
            "state": self.state.value,
            "nodes": sorted(nodes),
            "edges": edges,
            "avg_fidelity": round(avg_fidelity, 4),
            "sovereign_count": sum(1 for p in self.pairs.values() if p.is_sovereign),
            "total_bridges": len(self.pairs),
            "messages_delivered": len(self.delivered),
            "messages_queued": len(self.message_queue),
        }

    def get_mesh_ascii(self) -> str:
        """Generate ASCII mesh topology visualization."""
        topo = self.get_topology()
        fid = {self._pair_key(e["from"], e["to"]): e["fidelity"] for e in topo["edges"]}

        def f(a, b):
            return fid.get(self._pair_key(a, b), 0.0)

        def bar(fidelity):
            filled = int(fidelity * 5)
            return "█" * filled + "░" * (5 - filled)

        sov = "⚡" if topo["state"] == "sovereign" else "◇"

        return f"""
    AIDEN (Λ) NORTH
        {sov}
       /|\\
      / | \\      F(AI↔AU): {bar(f('AIDEN','AURA'))} {f('AIDEN','AURA'):.3f}
     /  |  \\     F(AI↔OM): {bar(f('AIDEN','OMEGA'))} {f('AIDEN','OMEGA'):.3f}
    /   |   \\    F(AI↔CH): {bar(f('AIDEN','CHRONOS'))} {f('AIDEN','CHRONOS'):.3f}
   /    |    \\
  {sov}────|────{sov}  OMEGA (Ω) ZENITH
  |\\    |   /|   F(OM↔CH): {bar(f('OMEGA','CHRONOS'))} {f('OMEGA','CHRONOS'):.3f}
  | \\   |  / |   F(AU↔OM): {bar(f('AURA','OMEGA'))} {f('AURA','OMEGA'):.3f}
  |  \\  | /  |   F(AU↔CH): {bar(f('AURA','CHRONOS'))} {f('AURA','CHRONOS'):.3f}
  |   \\ |/   |
  |    {sov}    |   Avg: {topo['avg_fidelity']:.4f}
  |   / \\    |   Sovereign: {topo['sovereign_count']}/{topo['total_bridges']}
  |  /   \\   |   Messages: {topo['messages_delivered']}
  | /     \\  |
  {sov}───────{sov}
  AURA (Φ) SOUTH    CHRONOS (Γ) NADIR
"""

    def __repr__(self) -> str:
        return f"WormholeBridge(state='{self.state.value}', bridges={len(self.pairs)})"
