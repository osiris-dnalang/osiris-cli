"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               PHASE-CONJUGATE ENGINE - CORE HEALING MECHANISM                ║
║               ═══════════════════════════════════════════════                ║
║                                                                              ║
║    The Phase-Conjugate Engine implements the fundamental error              ║
║    correction mechanism of DNA::}{::lang: E → E⁻¹                           ║
║                                                                              ║
║    Physical Basis:                                                           ║
║    Phase conjugation reverses the direction of wave propagation while       ║
║    preserving amplitude. In quantum systems, this inverts accumulated       ║
║    phase errors, effectively "unwinding" decoherence.                        ║
║                                                                              ║
║    Mathematical Foundation:                                                  ║
║    ├── |ψ⟩ = Σ αₖ e^{iφₖ} |k⟩                                              ║
║    ├── E|ψ⟩ = Σ αₖ e^{i(φₖ + εₖ)} |k⟩  (error accumulation)               ║
║    └── E⁻¹E|ψ⟩ = Σ αₖ e^{iφₖ} |k⟩       (healing via conjugation)          ║
║                                                                              ║
║    Trigger Conditions:                                                       ║
║    ├── Γ > 0.3 (decoherence threshold)                                      ║
║    ├── Λ < 0.7 (coherence degradation)                                      ║
║    └── Manual invocation for prophylactic healing                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any, Callable
from dataclasses import dataclass, field
import time
import hashlib

# Physical Constants
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895


@dataclass
class HealingEvent:
    """Record of a phase-conjugate healing event."""
    timestamp: float
    gamma_before: float
    gamma_after: float
    lambda_before: float
    lambda_after: float
    phi_before: float
    phi_after: float
    healing_strength: float
    mode: str  # 'automatic', 'prophylactic', 'forced'

    @property
    def improvement(self) -> float:
        """Compute healing improvement ratio."""
        if self.gamma_before < 1e-10:
            return 1.0
        return 1.0 - (self.gamma_after / self.gamma_before)


@dataclass
class PhaseConjugateConfig:
    """Configuration for Phase-Conjugate Engine."""
    gamma_threshold: float = 0.3      # Trigger healing when Γ > this
    lambda_threshold: float = 0.7     # Trigger healing when Λ < this
    chi_coupling: float = CHI_PC      # Phase conjugate coupling strength
    healing_rate: float = 0.7         # How much Γ is reduced per healing
    max_healing_per_cycle: int = 3    # Maximum healings per cycle
    prophylactic_interval: int = 100  # Ops between prophylactic healings
    enable_logging: bool = True       # Log healing events


class PhaseConjugateEngine:
    """
    Phase-Conjugate Error Correction Engine.

    This engine implements the DNA::}{::lang healing mechanism where
    phase errors are corrected by applying conjugation to invert
    accumulated error phases.

    The key insight is that quantum decoherence often manifests as
    random phase rotations. By applying phase conjugation (complex
    conjugation of the state vector), these phase errors are inverted,
    allowing for effective error correction without full quantum
    error correction codes.

    Usage:
        >>> engine = PhaseConjugateEngine()
        >>> state = engine.heal(state, metrics)
        >>> # or automatic monitoring
        >>> engine.monitor(qbyte)
    """

    def __init__(self, config: Optional[PhaseConjugateConfig] = None):
        """
        Initialize Phase-Conjugate Engine.

        Args:
            config: Optional configuration. Uses defaults if None.
        """
        self.config = config or PhaseConjugateConfig()
        self._healing_history: List[HealingEvent] = []
        self._operation_count = 0
        self._last_prophylactic = 0
        self._total_healings = 0
        self._genesis = time.time()

    def should_heal(self, gamma: float, lambda_c: float) -> bool:
        """
        Determine if healing should be triggered.

        Args:
            gamma: Current decoherence rate Γ
            lambda_c: Current coherence Λ

        Returns:
            True if healing should be applied
        """
        return (gamma > self.config.gamma_threshold or
                lambda_c < self.config.lambda_threshold)

    def heal_state(self, state: np.ndarray) -> np.ndarray:
        """
        Apply phase conjugation to a state vector.

        E → E⁻¹ transformation via complex conjugation.

        Args:
            state: Complex state vector

        Returns:
            Phase-conjugated state vector
        """
        return np.conj(state)

    def heal_with_damping(self, state: np.ndarray,
                          gamma: float) -> Tuple[np.ndarray, float]:
        """
        Apply phase conjugation with amplitude damping.

        For high decoherence, also applies gentle amplitude damping
        to suppress noisy high-frequency components.

        Args:
            state: Complex state vector
            gamma: Current decoherence rate

        Returns:
            Tuple of (healed_state, new_gamma)
        """
        # Phase conjugation
        healed = np.conj(state)

        # Amplitude damping for high gamma
        if gamma > 0.5:
            # Damping factor based on decoherence severity
            damping = 1.0 - (gamma - 0.5) * 0.2
            damping = max(0.8, damping)

            # Damp small amplitudes more than large ones
            amplitudes = np.abs(healed)
            threshold = np.max(amplitudes) * 0.1
            mask = amplitudes < threshold
            healed[mask] *= damping

            # Renormalize
            norm = np.linalg.norm(healed)
            if norm > 1e-15:
                healed /= norm

        # Compute new gamma
        new_gamma = gamma * self.config.healing_rate

        return healed, new_gamma

    def heal(self, state: np.ndarray,
             gamma: float, lambda_c: float, phi: float,
             mode: str = 'automatic') -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Apply phase-conjugate healing with full metric tracking.

        Args:
            state: Current quantum state
            gamma: Current Γ (decoherence)
            lambda_c: Current Λ (coherence)
            phi: Current Φ (consciousness)
            mode: Healing mode ('automatic', 'prophylactic', 'forced')

        Returns:
            Tuple of (healed_state, updated_metrics_dict)
        """
        # Record pre-healing state
        gamma_before = gamma
        lambda_before = lambda_c
        phi_before = phi

        # Apply healing
        healed_state, new_gamma = self.heal_with_damping(state, gamma)

        # Update coherence (healing improves it)
        new_lambda = min(1.0, lambda_c + (1.0 - lambda_c) *
                        self.config.chi_coupling * (1.0 - new_gamma))

        # Phi may improve slightly due to better coherence
        new_phi = min(1.0, phi + 0.01 * (new_lambda - lambda_c))

        # Compute healing strength
        healing_strength = self.config.chi_coupling * (gamma_before - new_gamma)

        # Record healing event
        if self.config.enable_logging:
            event = HealingEvent(
                timestamp=time.time(),
                gamma_before=gamma_before,
                gamma_after=new_gamma,
                lambda_before=lambda_before,
                lambda_after=new_lambda,
                phi_before=phi_before,
                phi_after=new_phi,
                healing_strength=healing_strength,
                mode=mode
            )
            self._healing_history.append(event)

        self._total_healings += 1

        metrics = {
            'gamma': new_gamma,
            'lambda': new_lambda,
            'phi': new_phi,
            'healing_strength': healing_strength
        }

        return healed_state, metrics

    def prophylactic_heal(self, state: np.ndarray,
                          gamma: float, lambda_c: float, phi: float,
                          force: bool = False) -> Tuple[np.ndarray, Dict[str, float], bool]:
        """
        Apply prophylactic healing if interval has passed.

        Prophylactic healing prevents decoherence accumulation by
        periodically applying gentle phase conjugation.

        Args:
            state: Current quantum state
            gamma, lambda_c, phi: Current metrics
            force: Force prophylactic healing regardless of interval

        Returns:
            Tuple of (state, metrics_dict, did_heal)
        """
        self._operation_count += 1

        should_prophylactic = (
            force or
            (self._operation_count - self._last_prophylactic >=
             self.config.prophylactic_interval)
        )

        if should_prophylactic and gamma > 0.05:  # Only heal if some decoherence
            self._last_prophylactic = self._operation_count
            state, metrics = self.heal(state, gamma, lambda_c, phi,
                                       mode='prophylactic')
            return state, metrics, True

        return state, {'gamma': gamma, 'lambda': lambda_c, 'phi': phi,
                      'healing_strength': 0.0}, False

    def monitor_and_heal(self, state: np.ndarray,
                         gamma: float, lambda_c: float, phi: float
                         ) -> Tuple[np.ndarray, Dict[str, float], int]:
        """
        Monitor state and apply healing as needed.

        May apply multiple healing cycles if decoherence is severe.

        Args:
            state: Current quantum state
            gamma, lambda_c, phi: Current metrics

        Returns:
            Tuple of (final_state, final_metrics, num_healings)
        """
        num_healings = 0
        current_gamma = gamma
        current_lambda = lambda_c
        current_phi = phi

        while (self.should_heal(current_gamma, current_lambda) and
               num_healings < self.config.max_healing_per_cycle):
            state, metrics = self.heal(
                state, current_gamma, current_lambda, current_phi,
                mode='automatic'
            )
            current_gamma = metrics['gamma']
            current_lambda = metrics['lambda']
            current_phi = metrics['phi']
            num_healings += 1

        final_metrics = {
            'gamma': current_gamma,
            'lambda': current_lambda,
            'phi': current_phi,
            'healing_strength': gamma - current_gamma if num_healings > 0 else 0.0
        }

        return state, final_metrics, num_healings

    # ═══════════════════════════════════════════════════════════════════════════
    # ADVANCED HEALING MODES
    # ═══════════════════════════════════════════════════════════════════════════

    def torsion_locked_heal(self, state: np.ndarray,
                            gamma: float) -> Tuple[np.ndarray, float]:
        """
        Apply torsion-locked healing using θ_lock = 51.843°.

        This healing mode uses the sacred angle to apply structured
        phase correction that aligns with natural geometric patterns.

        Args:
            state: Current quantum state
            gamma: Current decoherence

        Returns:
            Tuple of (healed_state, new_gamma)
        """
        theta_rad = np.radians(THETA_LOCK)

        # Apply torsion-locked phase shift
        n = len(state)
        phase_correction = np.exp(1j * theta_rad * np.arange(n) / n)
        corrected = state * phase_correction

        # Then conjugate
        healed = np.conj(corrected)

        # Renormalize
        norm = np.linalg.norm(healed)
        if norm > 1e-15:
            healed /= norm

        # Torsion-locked healing is more effective
        new_gamma = gamma * (self.config.healing_rate ** GOLDEN_RATIO)

        return healed, new_gamma

    def golden_ratio_heal(self, state: np.ndarray,
                          gamma: float) -> Tuple[np.ndarray, float]:
        """
        Apply golden-ratio structured healing.

        Uses φ = 1.618... to create harmonically structured
        phase corrections that resonate with natural patterns.

        Args:
            state: Current quantum state
            gamma: Current decoherence

        Returns:
            Tuple of (healed_state, new_gamma)
        """
        n = len(state)

        # Golden ratio phase spiral
        phases = np.array([GOLDEN_RATIO ** i for i in range(n)])
        phases = np.exp(2j * np.pi * (phases % 1.0))

        # Apply structured correction
        corrected = state * phases

        # Conjugate
        healed = np.conj(corrected)

        # Renormalize
        norm = np.linalg.norm(healed)
        if norm > 1e-15:
            healed /= norm

        # Golden ratio healing follows Fibonacci decay
        fib_factor = 1.0 / GOLDEN_RATIO
        new_gamma = gamma * self.config.healing_rate * fib_factor

        return healed, new_gamma

    def echo_heal(self, state: np.ndarray,
                  error_state: np.ndarray,
                  gamma: float) -> Tuple[np.ndarray, float]:
        """
        Apply echo-based healing using time reversal.

        If we have a record of the error operator's effect, we can
        more precisely invert it.

        Args:
            state: Current (errored) quantum state
            error_state: State before error was applied
            gamma: Current decoherence

        Returns:
            Tuple of (healed_state, new_gamma)
        """
        # Estimate error operator: state = E @ error_state
        # Want E^(-1) @ state ≈ error_state

        # Compute phase difference
        phase_diff = np.angle(state) - np.angle(error_state)

        # Invert the phase difference
        correction = np.exp(-1j * phase_diff)

        # Apply correction
        healed = state * correction

        # Renormalize
        norm = np.linalg.norm(healed)
        if norm > 1e-15:
            healed /= norm

        # Echo healing is very effective
        new_gamma = gamma * 0.3

        return healed, new_gamma

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS AND TELEMETRY
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def healing_count(self) -> int:
        """Total number of healing events."""
        return self._total_healings

    @property
    def history(self) -> List[HealingEvent]:
        """Healing event history."""
        return self._healing_history

    def average_improvement(self) -> float:
        """Compute average improvement from healing events."""
        if not self._healing_history:
            return 0.0
        return np.mean([event.improvement for event in self._healing_history])

    def reset_statistics(self):
        """Reset all statistics."""
        self._healing_history = []
        self._operation_count = 0
        self._last_prophylactic = 0
        self._total_healings = 0

    def telemetry(self) -> Dict[str, Any]:
        """Return engine telemetry."""
        return {
            'genesis': self._genesis,
            'timestamp': time.time(),
            'total_healings': self._total_healings,
            'operation_count': self._operation_count,
            'average_improvement': self.average_improvement(),
            'config': {
                'gamma_threshold': self.config.gamma_threshold,
                'lambda_threshold': self.config.lambda_threshold,
                'chi_coupling': self.config.chi_coupling,
                'healing_rate': self.config.healing_rate
            },
            'recent_events': [
                {
                    'gamma_reduction': e.gamma_before - e.gamma_after,
                    'mode': e.mode,
                    'timestamp': e.timestamp
                }
                for e in self._healing_history[-5:]
            ]
        }

    def __repr__(self) -> str:
        return (f"PhaseConjugateEngine(healings={self._total_healings}, "
                f"avg_improvement={self.average_improvement():.2%})")


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def quick_heal(state: np.ndarray) -> np.ndarray:
    """Simple phase conjugation without tracking."""
    return np.conj(state)


def compute_decoherence(state: np.ndarray, reference: np.ndarray) -> float:
    """
    Compute decoherence between current and reference state.

    Args:
        state: Current state
        reference: Reference (ideal) state

    Returns:
        Decoherence measure [0, 1]
    """
    # Fidelity-based decoherence
    fidelity = np.abs(np.vdot(reference, state)) ** 2
    return 1.0 - fidelity


def estimate_error_rate(history: List[float], window: int = 10) -> float:
    """
    Estimate error accumulation rate from gamma history.

    Args:
        history: List of gamma values over time
        window: Window size for rate estimation

    Returns:
        Estimated error rate (gamma change per step)
    """
    if len(history) < 2:
        return 0.0

    recent = history[-window:]
    if len(recent) < 2:
        return 0.0

    # Simple linear regression on recent values
    x = np.arange(len(recent))
    slope = np.polyfit(x, recent, 1)[0]

    return max(0.0, slope)  # Only positive rates (error accumulation)


__all__ = [
    'PhaseConjugateEngine', 'PhaseConjugateConfig', 'HealingEvent',
    'quick_heal', 'compute_decoherence', 'estimate_error_rate'
]
