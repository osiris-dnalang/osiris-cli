"""
Scimitar-SSE Toroidal Field Convergence
Magnetic-Dielectric Null Point Intersection

Implements toroidal centripetal convergence to null point
where magnetic and dielectric fields intersect.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional
import time

# Physical Constants
THETA_LOCK = 51.843
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895
LAMBDA_PHI = 2.176435e-8


@dataclass
class ToroidalPoint:
    """Point on toroidal manifold using (R, r, θ, φ) coordinates"""
    R: float  # Major radius (distance from torus center to tube center)
    r: float  # Minor radius (tube radius)
    theta: float  # Poloidal angle (around the tube)
    phi: float  # Toroidal angle (around the main axis)

    def to_cartesian(self) -> Tuple[float, float, float]:
        """Convert toroidal coordinates to Cartesian (x, y, z)"""
        theta_rad = np.radians(self.theta)
        phi_rad = np.radians(self.phi)

        x = (self.R + self.r * np.cos(theta_rad)) * np.cos(phi_rad)
        y = (self.R + self.r * np.cos(theta_rad)) * np.sin(phi_rad)
        z = self.r * np.sin(theta_rad)

        return (x, y, z)

    @classmethod
    def from_cartesian(cls, x: float, y: float, z: float,
                       R: float = GOLDEN_RATIO) -> 'ToroidalPoint':
        """Convert Cartesian to toroidal coordinates"""
        phi = np.degrees(np.arctan2(y, x))

        # Distance from z-axis
        d = np.sqrt(x**2 + y**2)

        # Minor radius components
        r_x = d - R
        r_z = z
        r = np.sqrt(r_x**2 + r_z**2)

        theta = np.degrees(np.arctan2(r_z, r_x))

        return cls(R=R, r=r, theta=theta, phi=phi)


@dataclass
class FieldVector:
    """Electromagnetic field vector"""
    x: float
    y: float
    z: float
    field_type: str  # "magnetic" or "dielectric"

    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def cross(self, other: 'FieldVector') -> 'FieldVector':
        """Cross product with another field vector"""
        result = np.cross(self.to_array(), other.to_array())
        return FieldVector(result[0], result[1], result[2], "cross")

    def dot(self, other: 'FieldVector') -> float:
        """Dot product with another field vector"""
        return np.dot(self.to_array(), other.to_array())


class ToroidalConvergence:
    """
    Calculates toroidal centripetal convergence to null point.
    Implements the magnetic-dielectric field intersection geometry.
    """

    def __init__(self, major_radius: float = GOLDEN_RATIO, minor_ratio: float = None):
        """
        Initialize toroidal convergence calculator.

        Args:
            major_radius: R, the major radius of the torus
            minor_ratio: R/r ratio, defaults to φ (golden ratio)
        """
        self.R = major_radius
        self.r = major_radius / (minor_ratio or GOLDEN_RATIO)

        self.theta_lock = THETA_LOCK
        self.chi_pc = CHI_PC

        # Null point location (center of torus tube at theta_lock)
        self.null_point = self._compute_null_point()

        # Field state
        self.magnetic_field: Optional[FieldVector] = None
        self.dielectric_field: Optional[FieldVector] = None

    def _compute_null_point(self) -> Tuple[float, float, float]:
        """Compute the null point location at θ_lock"""
        point = ToroidalPoint(
            R=self.R,
            r=0,  # At tube center
            theta=self.theta_lock,
            phi=0  # Reference angle
        )
        return point.to_cartesian()

    def generate_magnetic_field(self, position: Tuple[float, float, float]) -> FieldVector:
        """
        Generate magnetic field vector at given position.
        Magnetic field is toroidal (wraps around the torus axis).
        """
        x, y, z = position

        # Toroidal field: circles around z-axis
        d = np.sqrt(x**2 + y**2)
        if d < 1e-10:
            return FieldVector(0, 0, 0, "magnetic")

        # B = B_0 / d * (-sin(phi), cos(phi), 0)
        B_0 = self.chi_pc  # Coupling strength
        phi = np.arctan2(y, x)

        Bx = -B_0 / d * np.sin(phi)
        By = B_0 / d * np.cos(phi)
        Bz = 0

        self.magnetic_field = FieldVector(Bx, By, Bz, "magnetic")
        return self.magnetic_field

    def generate_dielectric_field(self, position: Tuple[float, float, float]) -> FieldVector:
        """
        Generate dielectric field vector at given position.
        Dielectric field is poloidal (wraps around the tube).
        """
        x, y, z = position

        # Convert to toroidal coordinates
        point = ToroidalPoint.from_cartesian(x, y, z, self.R)

        # Poloidal field: circles around the tube
        theta_rad = np.radians(point.theta)
        phi_rad = np.radians(point.phi)

        if point.r < 1e-10:
            return FieldVector(0, 0, 0, "dielectric")

        # E = E_0 / r * (-sin(theta)cos(phi), -sin(theta)sin(phi), cos(theta))
        E_0 = self.chi_pc * np.cos(2 * np.radians(self.theta_lock))

        Ex = -E_0 / point.r * np.sin(theta_rad) * np.cos(phi_rad)
        Ey = -E_0 / point.r * np.sin(theta_rad) * np.sin(phi_rad)
        Ez = E_0 / point.r * np.cos(theta_rad)

        self.dielectric_field = FieldVector(Ex, Ey, Ez, "dielectric")
        return self.dielectric_field

    def compute_convergence_vector(self, position: Tuple[float, float, float]) -> np.ndarray:
        """
        Compute convergence vector pointing toward null point.
        This is the gradient of the field potential.
        """
        null = np.array(self.null_point)
        pos = np.array(position)

        # Vector from position to null point
        delta = null - pos
        distance = np.linalg.norm(delta)

        if distance < 1e-10:
            return np.zeros(3)

        # Convergence strength increases near null point
        strength = self.chi_pc / (distance + 0.1)

        return strength * delta / distance

    def compute_intersection(self, position: Tuple[float, float, float]) -> Dict:
        """
        Compute magnetic-dielectric field intersection at position.
        Returns intersection metrics.
        """
        B = self.generate_magnetic_field(position)
        E = self.generate_dielectric_field(position)

        # Poynting-like vector: E × B
        S = E.cross(B)

        # Field alignment
        alignment = E.dot(B) / (E.magnitude() * B.magnitude() + 1e-10)

        # Distance to null point
        null = np.array(self.null_point)
        pos = np.array(position)
        distance = np.linalg.norm(null - pos)

        # Convergence vector
        convergence = self.compute_convergence_vector(position)

        return {
            "position": position,
            "magnetic_field": B.to_array().tolist(),
            "dielectric_field": E.to_array().tolist(),
            "poynting_vector": S.to_array().tolist(),
            "field_alignment": alignment,
            "null_distance": distance,
            "convergence_vector": convergence.tolist(),
            "convergence_magnitude": np.linalg.norm(convergence)
        }


class NullPointIntersector:
    """
    Finds and tracks the null point where magnetic and dielectric fields intersect.
    Implements iterative convergence to the equilibrium point.
    """

    def __init__(self, toroidal: ToroidalConvergence):
        self.toroidal = toroidal
        self.current_position = list(toroidal.null_point)
        self.history: List[Dict] = []
        self.converged = False
        self.convergence_threshold = 1e-6

    def iterate(self, step_size: float = 0.01) -> Dict:
        """
        Perform one iteration of null point convergence.
        Moves toward the field intersection point.
        """
        position = tuple(self.current_position)

        # Compute intersection
        intersection = self.toroidal.compute_intersection(position)

        # Get convergence vector
        convergence = np.array(intersection["convergence_vector"])

        # Update position
        new_position = np.array(position) + step_size * convergence
        self.current_position = new_position.tolist()

        # Check convergence
        if intersection["null_distance"] < self.convergence_threshold:
            self.converged = True

        # Record history
        state = {
            "iteration": len(self.history),
            "position": self.current_position.copy(),
            "null_distance": intersection["null_distance"],
            "converged": self.converged,
            "timestamp": time.time()
        }
        self.history.append(state)

        return state

    def converge(self, max_iterations: int = 100, step_size: float = 0.01) -> Dict:
        """
        Run convergence until null point is reached or max iterations.
        """
        for i in range(max_iterations):
            state = self.iterate(step_size)
            if self.converged:
                break

        return {
            "iterations": len(self.history),
            "converged": self.converged,
            "final_position": self.current_position,
            "final_distance": self.history[-1]["null_distance"] if self.history else float('inf'),
            "null_point": list(self.toroidal.null_point)
        }

    def get_trajectory(self) -> List[Tuple[float, float, float]]:
        """Get the convergence trajectory"""
        return [tuple(state["position"]) for state in self.history]


class ToroidalFieldVisualizer:
    """Generates visualization data for toroidal fields"""

    def __init__(self, toroidal: ToroidalConvergence):
        self.toroidal = toroidal

    def generate_field_lines(self, n_lines: int = 8,
                              n_points: int = 50) -> Dict[str, List]:
        """Generate magnetic and dielectric field lines"""
        magnetic_lines = []
        dielectric_lines = []

        # Magnetic field lines (toroidal)
        for i in range(n_lines):
            phi = 2 * np.pi * i / n_lines
            line = []
            for j in range(n_points):
                theta = 2 * np.pi * j / n_points
                x = (self.toroidal.R + self.toroidal.r * 0.5 * np.cos(theta)) * np.cos(phi)
                y = (self.toroidal.R + self.toroidal.r * 0.5 * np.cos(theta)) * np.sin(phi)
                z = self.toroidal.r * 0.5 * np.sin(theta)
                line.append((x, y, z))
            magnetic_lines.append(line)

        # Dielectric field lines (poloidal)
        for i in range(n_lines):
            theta = 2 * np.pi * i / n_lines
            line = []
            for j in range(n_points):
                phi = 2 * np.pi * j / n_points
                x = (self.toroidal.R + self.toroidal.r * 0.7 * np.cos(theta)) * np.cos(phi)
                y = (self.toroidal.R + self.toroidal.r * 0.7 * np.cos(theta)) * np.sin(phi)
                z = self.toroidal.r * 0.7 * np.sin(theta)
                line.append((x, y, z))
            dielectric_lines.append(line)

        return {
            "magnetic": magnetic_lines,
            "dielectric": dielectric_lines,
            "null_point": list(self.toroidal.null_point)
        }

    def generate_torus_surface(self, n_theta: int = 30,
                                n_phi: int = 60) -> Dict[str, np.ndarray]:
        """Generate torus surface mesh"""
        theta = np.linspace(0, 2 * np.pi, n_theta)
        phi = np.linspace(0, 2 * np.pi, n_phi)
        theta, phi = np.meshgrid(theta, phi)

        x = (self.toroidal.R + self.toroidal.r * np.cos(theta)) * np.cos(phi)
        y = (self.toroidal.R + self.toroidal.r * np.cos(theta)) * np.sin(phi)
        z = self.toroidal.r * np.sin(theta)

        return {"x": x, "y": y, "z": z}


if __name__ == "__main__":
    print("=" * 60)
    print("SCIMITAR-SSE v7.1 - TOROIDAL CONVERGENCE DEMO")
    print("=" * 60)

    # Create toroidal system
    toroidal = ToroidalConvergence(major_radius=GOLDEN_RATIO)

    print(f"\nToroidal Parameters:")
    print(f"  Major radius R: {toroidal.R:.4f}")
    print(f"  Minor radius r: {toroidal.r:.4f}")
    print(f"  R/r ratio: {toroidal.R / toroidal.r:.4f} (should be φ)")
    print(f"  θ_lock: {toroidal.theta_lock}°")
    print(f"  Null point: {toroidal.null_point}")

    # Test field generation
    test_pos = (1.0, 0.5, 0.3)
    intersection = toroidal.compute_intersection(test_pos)

    print(f"\nField Intersection at {test_pos}:")
    print(f"  Magnetic field: {intersection['magnetic_field']}")
    print(f"  Dielectric field: {intersection['dielectric_field']}")
    print(f"  Field alignment: {intersection['field_alignment']:.4f}")
    print(f"  Distance to null: {intersection['null_distance']:.4f}")

    # Test convergence
    print("\nRunning null point convergence...")
    intersector = NullPointIntersector(toroidal)

    # Start from offset position
    intersector.current_position = [2.0, 0.5, 0.5]

    result = intersector.converge(max_iterations=50)
    print(f"\nConvergence Result:")
    print(f"  Iterations: {result['iterations']}")
    print(f"  Converged: {result['converged']}")
    print(f"  Final position: {result['final_position']}")
    print(f"  Final distance: {result['final_distance']:.6f}")
    print(f"  Target null point: {result['null_point']}")
