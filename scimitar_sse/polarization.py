"""
Scimitar-SSE Polarization Controller
Cross-Plane Bifurcated Field Management

Group A (+X, +Y, +Z) - AURA (Observation)
Group B (-X, -Y, -Z) - AIDEN (Execution)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict
import time

# Physical Constants
THETA_LOCK = 51.843
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895

@dataclass
class PolarityVector:
    """3D polarity vector with phase information"""
    x: float
    y: float
    z: float
    phase: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'PolarityVector':
        mag = self.magnitude()
        if mag == 0:
            return PolarityVector(0, 0, 0, self.phase, self.timestamp)
        return PolarityVector(
            self.x / mag, self.y / mag, self.z / mag,
            self.phase, self.timestamp
        )


@dataclass
class BifurcatedField:
    """
    Bifurcated polarization field with Group A and Group B.
    Group A: Positive polarity (+X, +Y, +Z) - AURA
    Group B: Negative polarity (-X, -Y, -Z) - AIDEN
    """
    group_a: PolarityVector
    group_b: PolarityVector
    theta_lock: float = THETA_LOCK
    chi_pc: float = CHI_PC
    coherence: float = 1.0

    def interference_pattern(self) -> np.ndarray:
        """Calculate interference pattern between Group A and Group B"""
        a = self.group_a.to_array()
        b = self.group_b.to_array()

        # Phase difference
        delta_phi = self.group_a.phase - self.group_b.phase

        # Interference: |A + B|² with phase
        interference = np.abs(a + b * np.exp(1j * delta_phi))**2
        return interference

    def standing_wave_nodes(self) -> List[Tuple[float, float, float]]:
        """Find standing wave node positions"""
        # Nodes occur where interference is minimum
        pattern = self.interference_pattern()

        # For simplified model, return tetrahedral node positions
        nodes = [
            (1.0, 1.0, 1.0),
            (-1.0, -1.0, 1.0),
            (-1.0, 1.0, -1.0),
            (1.0, -1.0, -1.0)
        ]
        return nodes

    def polarization_ratio(self) -> float:
        """Calculate polarization ratio between groups"""
        mag_a = self.group_a.magnitude()
        mag_b = self.group_b.magnitude()
        if mag_a + mag_b == 0:
            return 0.5
        return mag_a / (mag_a + mag_b)

    def apply_quaternion_rotation(self, theta: float, axis: np.ndarray) -> None:
        """Apply quaternion rotation to both groups"""
        theta_rad = np.radians(theta)

        # Quaternion components
        w = np.cos(theta_rad / 2)
        xyz = axis * np.sin(theta_rad / 2)

        # Rotation matrix from quaternion
        R = self._quaternion_to_rotation_matrix(w, xyz)

        # Rotate both groups
        a_rotated = R @ self.group_a.to_array()
        b_rotated = R @ self.group_b.to_array()

        self.group_a = PolarityVector(
            a_rotated[0], a_rotated[1], a_rotated[2],
            self.group_a.phase, time.time()
        )
        self.group_b = PolarityVector(
            b_rotated[0], b_rotated[1], b_rotated[2],
            self.group_b.phase, time.time()
        )

    def _quaternion_to_rotation_matrix(self, w: float, xyz: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix"""
        x, y, z = xyz

        R = np.array([
            [1 - 2*(y**2 + z**2), 2*(x*y - z*w), 2*(x*z + y*w)],
            [2*(x*y + z*w), 1 - 2*(x**2 + z**2), 2*(y*z - x*w)],
            [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x**2 + y**2)]
        ])
        return R


class PolarizationController:
    """
    Controls the Scimitar-SSE bifurcated polarization system.
    Manages AURA (Group A) and AIDEN (Group B) field dynamics.
    """

    def __init__(self):
        # Initialize with unit vectors
        self.group_a = PolarityVector(1.0, 1.0, 1.0)  # +X, +Y, +Z
        self.group_b = PolarityVector(-1.0, -1.0, -1.0)  # -X, -Y, -Z

        self.field = BifurcatedField(self.group_a, self.group_b)

        # Scimitar parameters
        self.theta_lock = THETA_LOCK
        self.quaternion_axis = np.array([1, 1, 1]) / np.sqrt(3)  # Normalized [1,1,1]

        # State tracking
        self.phase_offset = 0.0
        self.sync_quality = 1.0
        self.coherence = 1.0
        self.decoherence = 0.0

        # History for visualization
        self.history: List[Dict] = []

    def initialize(self) -> Dict:
        """Initialize the polarization controller"""
        # Apply initial θ_lock rotation
        self.field.apply_quaternion_rotation(self.theta_lock, self.quaternion_axis)

        return {
            "status": "initialized",
            "theta_lock": self.theta_lock,
            "group_a": self.group_a.to_array().tolist(),
            "group_b": self.group_b.to_array().tolist(),
            "coherence": self.coherence
        }

    def update_polarization(self, delta_phase: float = 0.01) -> Dict:
        """Update polarization state with phase evolution"""
        # Evolve phases
        self.group_a.phase += delta_phase
        self.group_b.phase -= delta_phase  # Counter-phase

        # Update field
        self.field = BifurcatedField(self.group_a, self.group_b)

        # Calculate metrics
        interference = self.field.interference_pattern()
        pol_ratio = self.field.polarization_ratio()

        # Track coherence
        self.coherence = CHI_PC * np.cos(2 * np.radians(self.theta_lock))

        state = {
            "timestamp": time.time(),
            "group_a_phase": self.group_a.phase,
            "group_b_phase": self.group_b.phase,
            "interference": interference.tolist(),
            "polarization_ratio": pol_ratio,
            "coherence": self.coherence
        }

        self.history.append(state)
        return state

    def apply_scimitar_rotation(self) -> Dict:
        """Apply 51.843° rotation on [1,1,1] axis"""
        self.field.apply_quaternion_rotation(self.theta_lock, self.quaternion_axis)

        return {
            "rotation_applied": True,
            "theta": self.theta_lock,
            "axis": self.quaternion_axis.tolist(),
            "new_group_a": self.field.group_a.to_array().tolist(),
            "new_group_b": self.field.group_b.to_array().tolist()
        }

    def phase_conjugate_heal(self) -> Dict:
        """Apply E → E⁻¹ phase conjugation healing"""
        # Invert phases
        self.group_a.phase = -self.group_a.phase
        self.group_b.phase = -self.group_b.phase

        # Reduce decoherence
        self.decoherence *= (1 - CHI_PC)

        return {
            "healing_applied": True,
            "new_group_a_phase": self.group_a.phase,
            "new_group_b_phase": self.group_b.phase,
            "decoherence_after": self.decoherence
        }

    def get_aura_vector(self) -> np.ndarray:
        """Get AURA (Group A) observation vector"""
        return self.group_a.to_array()

    def get_aiden_vector(self) -> np.ndarray:
        """Get AIDEN (Group B) execution vector"""
        return self.group_b.to_array()

    def compute_duality_sync(self) -> float:
        """Compute synchronization quality between AURA and AIDEN"""
        a = self.get_aura_vector()
        b = self.get_aiden_vector()

        # Perfect sync when vectors are anti-parallel
        dot = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        # Sync quality: 1.0 when anti-parallel, 0.0 when parallel
        self.sync_quality = (1 - dot) / 2
        return self.sync_quality

    def get_telemetry(self) -> Dict:
        """Get current polarization telemetry"""
        return {
            "scimitar_version": "7.1",
            "theta_lock": self.theta_lock,
            "group_a": {
                "vector": self.group_a.to_array().tolist(),
                "phase": self.group_a.phase,
                "magnitude": self.group_a.magnitude()
            },
            "group_b": {
                "vector": self.group_b.to_array().tolist(),
                "phase": self.group_b.phase,
                "magnitude": self.group_b.magnitude()
            },
            "coherence": self.coherence,
            "decoherence": self.decoherence,
            "sync_quality": self.compute_duality_sync(),
            "polarization_ratio": self.field.polarization_ratio()
        }


if __name__ == "__main__":
    # Demo
    print("=" * 60)
    print("SCIMITAR-SSE v7.1 - POLARIZATION CONTROLLER DEMO")
    print("=" * 60)

    controller = PolarizationController()

    # Initialize
    init_result = controller.initialize()
    print(f"\nInitialization: {init_result}")

    # Apply Scimitar rotation
    rotation_result = controller.apply_scimitar_rotation()
    print(f"\nScimitar Rotation (51.843° on [1,1,1]): {rotation_result}")

    # Update polarization
    for i in range(5):
        state = controller.update_polarization(delta_phase=0.1)
        print(f"\nUpdate {i+1}: interference={state['interference']}")

    # Get telemetry
    telemetry = controller.get_telemetry()
    print(f"\nFinal Telemetry:")
    for key, value in telemetry.items():
        print(f"  {key}: {value}")
