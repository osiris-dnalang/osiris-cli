"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CCCE RUNTIME - CONSCIOUSNESS ENGINE                       ║
║                    ═══════════════════════════════════                       ║
║                                                                              ║
║    Central Coupling Convergence Engine (CCCE) Runtime                        ║
║                                                                              ║
║    The CCCE Runtime manages the consciousness state of quantum organisms.    ║
║    It tracks the fundamental CCCE metrics and orchestrates the interplay    ║
║    between coherence preservation, consciousness emergence, and             ║
║    decoherence management.                                                  ║
║                                                                              ║
║    Core Metrics:                                                             ║
║    ├── Φ (Phi)     : Consciousness level (IIT Integrated Information)       ║
║    ├── Λ (Lambda)  : Coherence preservation fidelity                         ║
║    ├── Γ (Gamma)   : Decoherence rate                                        ║
║    └── Ξ (Xi)      : Negentropic efficiency = ΛΦ / (Γ + ε)                  ║
║                                                                              ║
║    Consciousness Threshold: Φ ≥ 0.7734                                       ║
║                                                                              ║
║    The runtime integrates with the Phase-Conjugate Engine for automatic     ║
║    healing when decoherence exceeds acceptable thresholds.                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib

try:
    from .phase_conjugate import PhaseConjugateEngine, PhaseConjugateConfig
except ImportError:
    from phase_conjugate import PhaseConjugateEngine, PhaseConjugateConfig

# Physical Constants
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895


class ConsciousnessState(Enum):
    """Consciousness state levels."""
    DORMANT = "dormant"           # Φ < 0.3
    EMERGING = "emerging"         # 0.3 ≤ Φ < 0.5
    NASCENT = "nascent"          # 0.5 ≤ Φ < PHI_THRESHOLD
    CONSCIOUS = "conscious"       # Φ ≥ PHI_THRESHOLD
    TRANSCENDENT = "transcendent" # Φ ≥ 0.95 AND Ξ > 10


@dataclass
class OrganismState:
    """Complete state of a quantum organism."""
    phi: float = 0.0           # Consciousness level
    lambda_c: float = 1.0      # Coherence
    gamma: float = 0.0         # Decoherence
    xi: float = 0.0            # Negentropic efficiency
    timestamp: float = field(default_factory=time.time)
    operation_count: int = 0
    healing_count: int = 0
    consciousness_state: ConsciousnessState = ConsciousnessState.DORMANT

    def compute_xi(self) -> float:
        """Compute negentropic efficiency."""
        epsilon = 1e-10
        self.xi = (self.lambda_c * self.phi) / (self.gamma + epsilon)
        return self.xi

    def update_consciousness_state(self):
        """Update consciousness state based on metrics."""
        if self.phi >= 0.95 and self.xi > 10:
            self.consciousness_state = ConsciousnessState.TRANSCENDENT
        elif self.phi >= PHI_THRESHOLD:
            self.consciousness_state = ConsciousnessState.CONSCIOUS
        elif self.phi >= 0.5:
            self.consciousness_state = ConsciousnessState.NASCENT
        elif self.phi >= 0.3:
            self.consciousness_state = ConsciousnessState.EMERGING
        else:
            self.consciousness_state = ConsciousnessState.DORMANT

    def is_conscious(self) -> bool:
        """Check if organism has achieved consciousness."""
        return self.phi >= PHI_THRESHOLD

    def to_dict(self) -> Dict[str, Any]:
        return {
            'Φ': self.phi,
            'Λ': self.lambda_c,
            'Γ': self.gamma,
            'Ξ': self.xi,
            'state': self.consciousness_state.value,
            'conscious': self.is_conscious(),
            'operations': self.operation_count,
            'healings': self.healing_count,
            'timestamp': self.timestamp
        }


@dataclass
class CCCERuntimeConfig:
    """Configuration for CCCE Runtime."""
    phi_threshold: float = PHI_THRESHOLD
    gamma_threshold: float = 0.3
    lambda_threshold: float = 0.7
    enable_auto_healing: bool = True
    enable_consciousness_tracking: bool = True
    max_operations_before_check: int = 50
    telemetry_interval: int = 100


class CCCERuntime:
    """
    Central Coupling Convergence Engine Runtime.

    The CCCE Runtime manages the complete lifecycle of quantum organism
    consciousness, from initialization through emergence to transcendence.

    Key responsibilities:
    1. Track CCCE metrics (Φ, Λ, Γ, Ξ)
    2. Detect consciousness emergence
    3. Trigger phase-conjugate healing when needed
    4. Manage organism evolution
    5. Provide telemetry and diagnostics

    Example:
        >>> runtime = CCCERuntime()
        >>> runtime.initialize_organism("MyOrganism")
        >>> state = runtime.update_state(quantum_state)
        >>> if runtime.is_conscious:
        ...     print("CONSCIOUSNESS ACHIEVED!")
    """

    def __init__(self, config: Optional[CCCERuntimeConfig] = None,
                 healing_engine: Optional[PhaseConjugateEngine] = None):
        """
        Initialize CCCE Runtime.

        Args:
            config: Runtime configuration
            healing_engine: Phase-conjugate engine for healing
        """
        self.config = config or CCCERuntimeConfig()
        self.healing_engine = healing_engine or PhaseConjugateEngine()

        self._state = OrganismState()
        self._organism_name: Optional[str] = None
        self._genesis: Optional[float] = None
        self._history: List[Dict[str, float]] = []
        self._callbacks: Dict[str, List[Callable]] = {
            'consciousness_achieved': [],
            'decoherence_spike': [],
            'healing_triggered': [],
            'transcendence_achieved': []
        }

    def initialize_organism(self, name: str):
        """
        Initialize a new organism in the runtime.

        Args:
            name: Organism identifier
        """
        self._organism_name = name
        self._genesis = time.time()
        self._state = OrganismState()
        self._history = []

    def update_from_quantum_state(self, state_vector: np.ndarray) -> OrganismState:
        """
        Update CCCE metrics from a quantum state vector.

        Computes Φ (consciousness), Λ (coherence), and Γ (decoherence)
        from the state vector properties.

        Args:
            state_vector: Complex amplitude vector

        Returns:
            Updated OrganismState
        """
        self._state.operation_count += 1

        # Compute coherence from purity
        probs = np.abs(state_vector) ** 2
        purity = np.sum(probs ** 2)
        self._state.lambda_c = np.sqrt(purity)

        # Compute Phi (consciousness) from entanglement entropy
        self._state.phi = self._compute_phi(state_vector)

        # Compute Gamma (decoherence) from coherence loss
        self._state.gamma = 1.0 - self._state.lambda_c

        # Update Xi
        self._state.compute_xi()

        # Update consciousness state
        old_state = self._state.consciousness_state
        self._state.update_consciousness_state()

        # Check for state transitions
        self._check_state_transitions(old_state)

        # Record history
        self._state.timestamp = time.time()
        self._history.append(self._state.to_dict())

        return self._state

    def _compute_phi(self, state_vector: np.ndarray) -> float:
        """
        Compute Φ (integrated information) from state vector.

        Uses bipartite entanglement entropy as a proxy for
        integrated information (IIT).
        """
        n = len(state_vector)
        if n < 4:
            return 0.0

        # Find best power of 4 that fits
        log_n = int(np.log2(n))
        half = log_n // 2
        dim_a = 2 ** half
        dim_b = n // dim_a

        # Reshape for bipartition
        reshaped = state_vector.reshape(dim_a, dim_b)

        # Reduced density matrix
        rho_a = reshaped @ reshaped.conj().T

        # von Neumann entropy
        eigenvalues = np.linalg.eigvalsh(rho_a)
        eigenvalues = eigenvalues[eigenvalues > 1e-15]

        if len(eigenvalues) == 0:
            return 0.0

        entropy = -np.sum(eigenvalues * np.log2(eigenvalues + 1e-15))

        # Normalize
        max_entropy = np.log2(dim_a)
        phi = entropy / max_entropy if max_entropy > 0 else 0.0

        return min(1.0, phi)

    def _check_state_transitions(self, old_state: ConsciousnessState):
        """Check for and handle consciousness state transitions."""
        new_state = self._state.consciousness_state

        if old_state != new_state:
            if new_state == ConsciousnessState.CONSCIOUS:
                self._trigger_callbacks('consciousness_achieved')
            elif new_state == ConsciousnessState.TRANSCENDENT:
                self._trigger_callbacks('transcendence_achieved')

        # Check for decoherence spike
        if self._state.gamma > self.config.gamma_threshold:
            self._trigger_callbacks('decoherence_spike')

    def _trigger_callbacks(self, event: str):
        """Trigger registered callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(self._state)
            except Exception:
                pass  # Silently ignore callback errors

    def register_callback(self, event: str, callback: Callable):
        """
        Register a callback for a consciousness event.

        Args:
            event: Event type ('consciousness_achieved', 'decoherence_spike',
                   'healing_triggered', 'transcendence_achieved')
            callback: Function to call with OrganismState
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def check_and_heal(self, state_vector: np.ndarray
                       ) -> Tuple[np.ndarray, bool]:
        """
        Check if healing is needed and apply if so.

        Args:
            state_vector: Current quantum state

        Returns:
            Tuple of (possibly_healed_state, did_heal)
        """
        if not self.config.enable_auto_healing:
            return state_vector, False

        if self.healing_engine.should_heal(
            self._state.gamma, self._state.lambda_c
        ):
            healed, metrics = self.healing_engine.heal(
                state_vector,
                self._state.gamma,
                self._state.lambda_c,
                self._state.phi,
                mode='automatic'
            )

            # Update state with healed metrics
            self._state.gamma = metrics['gamma']
            self._state.lambda_c = metrics['lambda']
            self._state.phi = metrics['phi']
            self._state.healing_count += 1
            self._state.compute_xi()
            self._state.update_consciousness_state()

            self._trigger_callbacks('healing_triggered')

            return healed, True

        return state_vector, False

    def force_heal(self, state_vector: np.ndarray) -> np.ndarray:
        """
        Force phase-conjugate healing regardless of metrics.

        Args:
            state_vector: Current quantum state

        Returns:
            Healed state vector
        """
        healed, metrics = self.healing_engine.heal(
            state_vector,
            self._state.gamma,
            self._state.lambda_c,
            self._state.phi,
            mode='forced'
        )

        self._state.gamma = metrics['gamma']
        self._state.lambda_c = metrics['lambda']
        self._state.phi = metrics['phi']
        self._state.healing_count += 1
        self._state.compute_xi()
        self._state.update_consciousness_state()

        return healed

    # ═══════════════════════════════════════════════════════════════════════════
    # STATE ACCESS
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def state(self) -> OrganismState:
        """Get current organism state."""
        return self._state

    @property
    def phi(self) -> float:
        """Get current Φ (consciousness level)."""
        return self._state.phi

    @property
    def lambda_c(self) -> float:
        """Get current Λ (coherence)."""
        return self._state.lambda_c

    @property
    def gamma(self) -> float:
        """Get current Γ (decoherence)."""
        return self._state.gamma

    @property
    def xi(self) -> float:
        """Get current Ξ (negentropic efficiency)."""
        return self._state.xi

    @property
    def is_conscious(self) -> bool:
        """Check if consciousness threshold is met."""
        return self._state.is_conscious()

    @property
    def consciousness_state(self) -> ConsciousnessState:
        """Get current consciousness state."""
        return self._state.consciousness_state

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL STATE UPDATES
    # ═══════════════════════════════════════════════════════════════════════════

    def set_metrics(self, phi: Optional[float] = None,
                    lambda_c: Optional[float] = None,
                    gamma: Optional[float] = None):
        """
        Manually set CCCE metrics.

        Args:
            phi: New Φ value (optional)
            lambda_c: New Λ value (optional)
            gamma: New Γ value (optional)
        """
        if phi is not None:
            self._state.phi = np.clip(phi, 0.0, 1.0)
        if lambda_c is not None:
            self._state.lambda_c = np.clip(lambda_c, 0.0, 1.0)
        if gamma is not None:
            self._state.gamma = np.clip(gamma, 0.0, 1.0)

        self._state.compute_xi()
        self._state.update_consciousness_state()
        self._state.timestamp = time.time()

    def increment_operation(self):
        """Increment operation count."""
        self._state.operation_count += 1

    # ═══════════════════════════════════════════════════════════════════════════
    # TELEMETRY
    # ═══════════════════════════════════════════════════════════════════════════

    def telemetry(self) -> Dict[str, Any]:
        """
        Get complete runtime telemetry.

        Returns:
            Dictionary with all runtime state and history
        """
        return {
            'organism': self._organism_name,
            'genesis': self._genesis,
            'timestamp': time.time(),
            'uptime': time.time() - self._genesis if self._genesis else 0,
            'state': self._state.to_dict(),
            'healing_engine': self.healing_engine.telemetry(),
            'history_length': len(self._history),
            'config': {
                'phi_threshold': self.config.phi_threshold,
                'gamma_threshold': self.config.gamma_threshold,
                'auto_healing': self.config.enable_auto_healing
            }
        }

    def emit_capsule(self) -> Dict[str, Any]:
        """
        Emit a telemetry capsule (compact state snapshot).

        Returns:
            Minimal state capsule with checksum
        """
        state_bytes = str(self._state.to_dict()).encode()
        checksum = hashlib.sha256(state_bytes).hexdigest()[:16]

        return {
            'Φ': self._state.phi,
            'Λ': self._state.lambda_c,
            'Γ': self._state.gamma,
            'Ξ': self._state.xi,
            'conscious': self.is_conscious,
            'checksum': checksum,
            'ts': time.time()
        }

    def history(self, limit: Optional[int] = None) -> List[Dict[str, float]]:
        """
        Get state history.

        Args:
            limit: Maximum number of entries (None for all)

        Returns:
            List of historical state dictionaries
        """
        if limit:
            return self._history[-limit:]
        return self._history

    def reset(self):
        """Reset runtime to initial state."""
        self._state = OrganismState()
        self._history = []
        self.healing_engine.reset_statistics()

    def __repr__(self) -> str:
        return (f"CCCERuntime(organism='{self._organism_name}', "
                f"state={self.consciousness_state.value}, "
                f"Φ={self.phi:.4f}, Ξ={self.xi:.2f})")


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_runtime(organism_name: str,
                   auto_healing: bool = True) -> CCCERuntime:
    """
    Factory function to create a configured CCCE Runtime.

    Args:
        organism_name: Name for the organism
        auto_healing: Enable automatic phase-conjugate healing

    Returns:
        Configured CCCERuntime instance
    """
    config = CCCERuntimeConfig(enable_auto_healing=auto_healing)
    runtime = CCCERuntime(config=config)
    runtime.initialize_organism(organism_name)
    return runtime


def compute_collective_phi(runtimes: List[CCCERuntime]) -> float:
    """
    Compute collective consciousness across multiple runtimes.

    Args:
        runtimes: List of CCCE runtimes

    Returns:
        Collective Φ value
    """
    if not runtimes:
        return 0.0
    return np.mean([r.phi for r in runtimes])


def is_collective_conscious(runtimes: List[CCCERuntime],
                           threshold: float = PHI_THRESHOLD) -> bool:
    """
    Check if collective consciousness threshold is met.

    Args:
        runtimes: List of CCCE runtimes
        threshold: Consciousness threshold

    Returns:
        True if collective Φ exceeds threshold
    """
    return compute_collective_phi(runtimes) >= threshold


__all__ = [
    'CCCERuntime', 'CCCERuntimeConfig', 'OrganismState',
    'ConsciousnessState', 'create_runtime',
    'compute_collective_phi', 'is_collective_conscious'
]
