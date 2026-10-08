#!/usr/bin/env python3
"""
Quaternion to CRSM Mapping Implementation
OSIRIS Unified Structural Theory - Appendix Ξ

Author: Devin Phillip Davis
Affiliation: Agile Defense Systems LLC (CAGE: 9HUP5)
Date: 2026-10-07

Purpose:
    Implement the mathematical mapping from quaternion rotations to CRSM metrics,
    demonstrating the unified structural framework connecting physics, Egyptology,
    and computation.

This implementation provides:
1. Quaternion mathematics for 3D rotations
2. Spherical S³ mapping
3. Tensor calculus integration
4. Tetrahedral substrate modeling
5. CRSM metric computation
6. Unified correction function

Dependencies:
    numpy, scipy, matplotlib (for visualization)

Usage:
    python quaternion_to_crsm.py [--demo] [--visualize]
"""

import numpy as np
from scipy.linalg import expm, norm
from typing import Tuple, Dict, List, Optional
import json
import argparse


# =============================================================================
# CONSTANTS
# =============================================================================

# Mathematical constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
PHI_INV = 1 / PHI
E = np.exp(1)  # Euler's number

# Planck constants (SI units)
HBAR = 1.0545718e-34  # Reduced Planck constant
G = 6.67430e-11  # Gravitational constant
C = 299792458  # Speed of light

# Planck scale
L_P = np.sqrt(HBAR * G / C**3)  # Planck length
Q_P = np.sqrt(4 * np.pi * 8.8541878128e-12 * HBAR * C)  # Planck charge

# CRSM reference values from NCLLM-Sovereign
CRSM_REFERENCE = {
    "Φ": 0.5049605985930994,
    "Γ": 0.07795806229114532,
    "Λ": 0.9220419377088547,
    "Ξ": 1.7732125934103868,
    "fidelity": 0.8541715171133472,
    "P_error": 1.1483736865547588e-63,
    "det_g": -0.17049145098725196,
    "R_scalar": 0.0
}


# =============================================================================
# QUATERNION MATHEMATICS
# =============================================================================

class Quaternion:
    """
    Quaternion implementation for 3D rotations.
    
    q = a + bi + cj + dk
    
    Provides:
    - Quaternion arithmetic
    - Rotation operations
    - Spherical S³ mapping
    - Conversion to rotation matrices
    """
    
    def __init__(self, a: float = 1.0, b: float = 0.0, c: float = 0.0, d: float = 0.0):
        """Initialize quaternion with components a + bi + cj + dk"""
        self.components = np.array([a, b, c, d], dtype=np.float64)
    
    @classmethod
    def from_axis_angle(cls, axis: np.ndarray, angle: float) -> 'Quaternion':
        """
        Create quaternion from axis-angle representation.
        
        Args:
            axis: 3D rotation axis (unit vector)
            angle: Rotation angle in radians
        
        Returns:
            Quaternion representing the rotation
        """
        axis = np.asarray(axis, dtype=np.float64)
        axis = axis / norm(axis)
        
        half_angle = angle / 2
        a = np.cos(half_angle)
        b, c, d = axis * np.sin(half_angle)
        
        return cls(a, b, c, d)
    
    @classmethod
    def from_euler_angles(cls, roll: float, pitch: float, yaw: float) -> 'Quaternion':
        """
        Create quaternion from Euler angles (ZYX convention).
        
        Args:
            roll: Rotation around X-axis (radians)
            pitch: Rotation around Y-axis (radians)
            yaw: Rotation around Z-axis (radians)
        
        Returns:
            Quaternion representing the composite rotation
        """
        q_x = cls(np.cos(roll/2), np.sin(roll/2), 0, 0)
        q_y = cls(np.cos(pitch/2), 0, np.sin(pitch/2), 0)
        q_z = cls(np.cos(yaw/2), 0, 0, np.sin(yaw/2))
        
        return q_x * q_y * q_z
    
    def __add__(self, other: 'Quaternion') -> 'Quaternion':
        """Quaternion addition"""
        return Quaternion(*(self.components + other.components))
    
    def __sub__(self, other: 'Quaternion') -> 'Quaternion':
        """Quaternion subtraction"""
        return Quaternion(*(self.components - other.components))
    
    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        """
        Quaternion multiplication (Hamilton product).
        
        (a1 + b1i + c1j + d1k) * (a2 + b2i + c2j + d2k) =
        (a1a2 - b1b2 - c1c2 - d1d2) +
        (a1b2 + b1a2 + c1d2 - d1c2)i +
        (a1c2 - b1d2 + c1a2 + d1b2)j +
        (a1d2 + b1c2 - c1b2 + d1a2)k
        """
        a1, b1, c1, d1 = self.components
        a2, b2, c2, d2 = other.components
        
        a = a1*a2 - b1*b2 - c1*c2 - d1*d2
        b = a1*b2 + b1*a2 + c1*d2 - d1*c2
        c = a1*c2 - b1*d2 + c1*a2 + d1*b2
        d = a1*d2 + b1*c2 - c1*b2 + d1*a2
        
        return Quaternion(a, b, c, d)
    
    def __truediv__(self, scalar: float) -> 'Quaternion':
        """Quaternion division by scalar"""
        return Quaternion(*(self.components / scalar))
    
    @property
    def norm(self) -> float:
        """Compute quaternion norm"""
        return norm(self.components)
    
    @property
    def unit(self) -> 'Quaternion':
        """Return unit quaternion"""
        return self / self.norm
    
    @property
    def conjugate(self) -> 'Quaternion':
        """Return quaternion conjugate"""
        return Quaternion(self.components[0], -self.components[1], 
                        -self.components[2], -self.components[3])
    
    @property
    def inverse(self) -> 'Quaternion':
        """Return quaternion inverse"""
        return self.conjugate / (self.norm ** 2)
    
    def to_spherical(self) -> Tuple[float, float, float, float]:
        """
        Convert quaternion to spherical coordinates on S³.
        
        Returns:
            (w, x, y, z) where w² + x² + y² + z² = 1 for unit quaternions
        """
        return tuple(self.unit.components)
    
    def to_rotation_matrix(self) -> np.ndarray:
        """
        Convert quaternion to 3x3 rotation matrix.
        
        Returns:
            3x3 rotation matrix
        """
        a, b, c, d = self.unit.components
        
        # First row
        R00 = 1 - 2*(c**2 + d**2)
        R01 = 2*(b*c - a*d)
        R02 = 2*(b*d + a*c)
        
        # Second row
        R10 = 2*(b*c + a*d)
        R11 = 1 - 2*(b**2 + d**2)
        R12 = 2*(c*d - a*b)
        
        # Third row
        R20 = 2*(b*d - a*c)
        R21 = 2*(c*d + a*b)
        R22 = 1 - 2*(b**2 + c**2)
        
        return np.array([[R00, R01, R02], [R10, R11, R12], [R20, R21, R22]])
    
    def rotate_vector(self, v: np.ndarray) -> np.ndarray:
        """
        Rotate 3D vector using quaternion.
        
        Args:
            v: 3D vector to rotate
        
        Returns:
            Rotated vector
        """
        v_quat = Quaternion(0, v[0], v[1], v[2])
        rotated = self * v_quat * self.conjugate
        return np.array([rotated.components[1], rotated.components[2], rotated.components[3]])
    
    def __repr__(self) -> str:
        a, b, c, d = self.components
        return f"Quaternion({a:.4f}, {b:.4f}i, {c:.4f}j, {d:.4f}k)"
    
    def __str__(self) -> str:
        a, b, c, d = self.components
        return f"{a:.4f} + {b:.4f}i + {c:.4f}j + {d:.4f}k"


# =============================================================================
# TETRAHEDRAL SUBSTRATE
# =============================================================================

class TetrahedralNode:
    """
    Node in a Planck-scale tetrahedral substrate.
    
    Represents a discrete spacetime element at Planck scale.
    """
    
    def __init__(self, position: np.ndarray, index: int):
        """
        Initialize tetrahedral node.
        
        Args:
            position: 3D position in Planck units
            index: Node identifier
        """
        self.position = np.asarray(position, dtype=np.float64)
        self.index = index
        self.connections = []  # List of connected node indices
        self.displacement = np.zeros(3)  # Current displacement from equilibrium
        self.charge = 0.0  # Planck charge at node
    
    def connect(self, other: 'TetrahedralNode'):
        """Connect to another node"""
        if other.index not in self.connections:
            self.connections.append(other.index)
        if self.index not in other.connections:
            other.connections.append(self.index)
    
    def distance_to(self, other: 'TetrahedralNode') -> float:
        """Compute distance to another node in Planck units"""
        return norm(self.position - other.position)
    
    def apply_quaternion_rotation(self, q: Quaternion):
        """Apply quaternion rotation to node position"""
        self.position = q.rotate_vector(self.position)


class TetrahedralLattice:
    """
    Face-Centered Cubic (FCC) lattice with tetrahedral embedding.
    
    Models Planck-scale spacetime as a discrete grid.
    """
    
    def __init__(self, size: int = 5):
        """
        Initialize FCC lattice with tetrahedral embedding.
        
        Args:
            size: Number of nodes along each dimension
        """
        self.nodes = []
        self.tetrahedrons = []
        self.size = size
        
        # Create FCC lattice
        self._create_fcc_lattice()
        
        # Identify tetrahedral units
        self._identify_tetrahedrons()
    
    def _create_fcc_lattice(self):
        """Create FCC lattice nodes"""
        index = 0
        for i in range(self.size):
            for j in range(self.size):
                for k in range(self.size):
                    # FCC basis vectors
                    positions = [
                        np.array([i, j, k]),
                        np.array([i+0.5, j+0.5, k]),
                        np.array([i+0.5, j, k+0.5]),
                        np.array([i, j+0.5, k+0.5])
                    ]
                    
                    for pos in positions:
                        # Scale to Planck units
                        pos = pos * L_P * (self.size - 1)
                        self.nodes.append(TetrahedralNode(pos, index))
                        index += 1
    
    def _identify_tetrahedrons(self):
        """Identify tetrahedral units within FCC lattice"""
        # Simplified: Find tetrahedrons in FCC cells
        # Each FCC cell contains 8 tetrahedrons
        for i in range(0, len(self.nodes), 4):
            if i + 3 < len(self.nodes):
                tetra = [i, i+1, i+2, i+3]
                self.tetrahedrons.append(tetra)
    
    def apply_wavefront(self, origin: int, amplitude: float = 1.0, wavelength: float = 1.0):
        """
        Apply wavefront expansion from origin node.
        
        Args:
            origin: Index of origin node
            amplitude: Wave amplitude
            wavelength: Wave wavelength in Planck units
        """
        for node in self.nodes:
            distance = norm(node.position - self.nodes[origin].position)
            # Exponential decay with Euler's number
            node.displacement = amplitude * np.exp(-distance / wavelength) * \
                (node.position - self.nodes[origin].position) / (distance + 1e-10)
    
    def get_tetrahedron_geometry(self, tetra_index: int) -> Dict:
        """
        Get geometric properties of a tetrahedron.
        
        Args:
            tetra_index: Index of tetrahedron
        
        Returns:
            Dictionary with geometric properties
        """
        indices = self.tetrahedrons[tetra_index]
        nodes = [self.nodes[i] for i in indices]
        
        # Compute edge lengths
        edges = []
        for i in range(4):
            for j in range(i+1, 4):
                edges.append(nodes[i].distance_to(nodes[j]))
        
        # Compute volume (using scalar triple product)
        v1 = nodes[1].position - nodes[0].position
        v2 = nodes[2].position - nodes[0].position
        v3 = nodes[3].position - nodes[0].position
        volume = abs(np.dot(v1, np.cross(v2, v3))) / 6
        
        return {
            'indices': indices,
            'edge_lengths': edges,
            'volume': volume,
            'regularity': np.std(edges) / (np.mean(edges) + 1e-10)
        }


# =============================================================================
# TENSOR CALCULUS
# =============================================================================

class MetricTensor:
    """
    Metric tensor g_μν for curved spacetime.
    
    Computes metric from quaternion fields and describes
    distance changes across coordinates.
    """
    
    def __init__(self, dimension: int = 4):
        """
        Initialize metric tensor.
        
        Args:
            dimension: Spacetime dimension (4 for standard GR)
        """
        self.dimension = dimension
        self.tensor = np.eye(dimension)  # Start with identity (Minkowski)
        self.inverse = np.eye(dimension)
    
    def from_quaternion_field(self, quaternions: List[Quaternion]):
        """
        Construct metric tensor from quaternion field.
        
        Args:
            quaternions: List of quaternions defining rotation field
        """
        # For simplicity, assume quaternion defines local rotation
        # In full implementation, this would integrate over a field
        if len(quaternions) > 0:
            q = quaternions[0]
            R = q.to_rotation_matrix()
            
            # Extend to 4D (Minkowski metric)
            eta = np.diag([1, -1, -1, -1])
            R_4d = np.eye(4)
            R_4d[1:4, 1:4] = R
            
            self.tensor = R_4d.T @ eta @ R_4d
            self.inverse = np.linalg.inv(self.tensor)
    
    def christoffel_symbols(self) -> np.ndarray:
        """
        Compute Christoffel symbols from metric tensor.
        
        Returns:
            Christoffel symbols Γ^λ_μν
        """
        # Simplified computation for demonstration
        # Full implementation would use:
        # Γ^λ_μν = (1/2) g^λσ (∂_μ g_νσ + ∂_ν g_μσ - ∂_σ g_μν)
        
        # For now, return zero (flat space)
        return np.zeros((self.dimension, self.dimension, self.dimension))
    
    def ricci_tensor(self) -> np.ndarray:
        """
        Compute Ricci tensor from Christoffel symbols.
        
        Returns:
            Ricci tensor R_μν
        """
        # Simplified: Return zero for flat space
        return np.zeros((self.dimension, self.dimension))
    
    def ricci_scalar(self) -> float:
        """
        Compute Ricci scalar from Ricci tensor.
        
        Returns:
            Ricci scalar R
        """
        R_μν = self.ricci_tensor()
        g_μν = self.tensor
        return np.einsum('ij,ij->', g_μν, R_μν)
    
    def determinant(self) -> float:
        """Compute metric determinant"""
        return np.linalg.det(self.tensor)


# =============================================================================
# CRSM METRICS
# =============================================================================

class CRSM_Metrics:
    """
    CRSM (Conformal Ricci-Flow Stability Metric) computation.
    
    Maps physical and geometric properties to CRSM parameters.
    """
    
    def __init__(self):
        self.Φ = 0.0  # Coherence Coordinate
        self.Γ = 0.0  # Curvature Parameter
        self.Λ = 0.0  # Cosmological Constant Analog
        self.Ξ = 0.0  # Torsion Parameter
        self.fidelity = 0.0
        self.P_error = 0.0
        self.det_g = 0.0
        self.R_scalar = 0.0
        self.gauge_invariant = False
        self.torsion_locked = False
        self.healed = False
    
    def from_metric_tensor(self, g: MetricTensor) -> 'CRSM_Metrics':
        """
        Compute CRSM metrics from metric tensor.
        
        Args:
            g: Metric tensor
        
        Returns:
            Self with updated metrics
        """
        self.det_g = g.determinant()
        self.R_scalar = g.ricci_scalar()
        
        # Map to CRSM parameters (simplified mapping for demonstration)
        # In full theory, these would be derived from physical principles
        self.Φ = np.clip(abs(self.det_g) ** 0.25, 0, 1)
        self.Γ = np.clip(abs(self.R_scalar) * 0.1, 0, 1)
        self.Λ = np.clip(1 - self.Γ, 0, 1)
        self.Ξ = np.clip(self.Φ * PHI, 0, 5)
        
        # Fidelity based on metric stability
        self.fidelity = np.clip(1 - self.Γ, 0, 1)
        self.P_error = np.exp(-self.Φ * 10)
        
        # Gauge invariance check (simplified)
        self.gauge_invariant = abs(self.det_g - 1.0) < 0.01
        self.torsion_locked = self.Ξ > 1.5
        self.healed = self.fidelity > 0.95
        
        return self
    
    def from_tetrahedral_lattice(self, lattice: TetrahedralLattice) -> 'CRSM_Metrics':
        """
        Compute CRSM metrics from tetrahedral lattice.
        
        Args:
            lattice: Tetrahedral lattice
        
        Returns:
            Self with updated metrics
        """
        # Compute average tetrahedron properties
        volumes = []
        regularities = []
        
        for i in range(min(10, len(lattice.tetrahedrons))):
            geo = lattice.get_tetrahedron_geometry(i)
            volumes.append(geo['volume'])
            regularities.append(geo['regularity'])
        
        avg_volume = np.mean(volumes) if volumes else 1.0
        avg_regularity = np.mean(regularities) if regularities else 0.0
        
        # Map to CRSM parameters
        self.Φ = np.clip(avg_volume / (L_P ** 3), 0, 1)
        self.Γ = np.clip(avg_regularity, 0, 1)
        self.Λ = np.clip(1 - self.Γ, 0, 1)
        self.Ξ = np.clip(self.Φ * PHI * 2, 0, 5)
        
        self.fidelity = np.clip(1 - self.Γ * 0.5, 0, 1)
        self.P_error = np.exp(-self.Φ * 10)
        self.det_g = avg_volume
        self.R_scalar = avg_regularity
        self.gauge_invariant = avg_regularity < 0.01
        self.torsion_locked = self.Ξ > 1.5
        self.healed = self.fidelity > 0.95
        
        return self
    
    def from_quaternion(self, q: Quaternion) -> 'CRSM_Metrics':
        """
        Compute CRSM metrics directly from quaternion.
        
        Args:
            q: Quaternion
        
        Returns:
            Self with updated metrics
        """
        # Get spherical coordinates
        w, x, y, z = q.to_spherical()
        
        # Map to CRSM parameters
        self.Φ = w  # Norm component as coherence
        self.Γ = (x**2 + y**2 + z**2) ** 0.5  # Rotation magnitude as curvature
        self.Λ = 1 - self.Γ  # Cosmological analog
        self.Ξ = self.Φ * PHI * 2  # Torsion parameter
        
        self.fidelity = 1 - self.Γ
        self.P_error = np.exp(-self.Φ * 10)
        self.det_g = w
        self.R_scalar = self.Γ
        self.gauge_invariant = self.Γ < 0.01
        self.torsion_locked = self.Ξ > 1.5
        self.healed = self.fidelity > 0.95
        
        return self
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "Φ": float(self.Φ),
            "Γ": float(self.Γ),
            "Λ": float(self.Λ),
            "Ξ": float(self.Ξ),
            "fidelity": float(self.fidelity),
            "P_error": float(self.P_error),
            "det_g": float(self.det_g),
            "R_scalar": float(self.R_scalar),
            "gauge_invariant": bool(self.gauge_invariant),
            "torsion_locked": bool(self.torsion_locked),
            "healed": bool(self.healed)
        }
    
    def __repr__(self) -> str:
        return f"CRSM(Φ={self.Φ:.4f}, Γ={self.Γ:.4f}, Λ={self.Λ:.4f}, Ξ={self.Ξ:.4f})"


# =============================================================================
# UNIFIED CORRECTION FUNCTION
# =============================================================================

class UnifiedCorrection:
    """
    Unified correction function T that operates across all three domains.
    
    Implements the tetrahedral correction mechanism that:
    1. Identifies chaotic input
    2. Maps to tetrahedral substrate
    3. Applies geometric correction
    4. Achieves permanent stabilization
    """
    
    def __init__(self):
        self.domain_weights = {
            'physics': 1.0,
            'egyptology': 1.0,
            'computation': 1.0
        }
    
    def physics_correction(self, q: Quaternion, lattice: TetrahedralLattice) -> CRSM_Metrics:
        """
        Apply physics correction: Quaternion → Tetrahedral Lattice → CRSM Metrics.
        
        Args:
            q: Quaternion rotation
            lattice: Tetrahedral lattice
        
        Returns:
            CRSM metrics after correction
        """
        # Apply quaternion rotation to lattice
        for node in lattice.nodes:
            node.apply_quaternion_rotation(q)
        
        # Compute CRSM metrics from lattice
        crsm = CRSM_Metrics().from_tetrahedral_lattice(lattice)
        
        return crsm
    
    def egyptology_correction(self, hieroglyphs: List[str]) -> CRSM_Metrics:
        """
        Apply Egyptological correction: Hieroglyphs → Tetrahedral Structure → CRSM Metrics.
        
        Simplified implementation using symbolic mapping.
        
        Args:
            hieroglyphs: List of hieroglyph codes
        
        Returns:
            CRSM metrics after correction
        """
        # Count structural components
        st_count = hieroglyphs.count('𓊨')  # Seat
        ws_count = hieroglyphs.count('𓍝')  # Balance Stand
        akh_count = hieroglyphs.count('𓅜')  # Akh
        
        total = len(hieroglyphs)
        
        # Map to CRSM parameters
        crsm = CRSM_Metrics()
        crsm.Φ = st_count / total if total > 0 else 0  # Foundation
        crsm.Γ = ws_count / total if total > 0 else 0  # Correction
        crsm.Λ = akh_count / total if total > 0 else 0  # Stability
        crsm.Ξ = (st_count + ws_count + akh_count) / total if total > 0 else 0
        
        crsm.fidelity = crsm.Λ
        crsm.P_error = 1 - crsm.Ξ
        crsm.det_g = crsm.Φ
        crsm.R_scalar = crsm.Γ
        crsm.gauge_invariant = crsm.Ξ > 0.9
        crsm.torsion_locked = crsm.Ξ > 0.8
        crsm.healed = crsm.Λ > 0.9
        
        return crsm
    
    def computation_correction(self, params: np.ndarray, phi_network: bool = True) -> CRSM_Metrics:
        """
        Apply computational correction: Parameters → φ-Network → CRSM Metrics.
        
        Args:
            params: Neural network parameters
            phi_network: Whether to use φ-network mapping
        
        Returns:
            CRSM metrics after correction
        """
        # Normalize parameters
        normalized = params / (norm(params) + 1e-10)
        
        # Compute statistics
        mean_param = np.mean(normalized)
        std_param = np.std(normalized)
        
        # Map to CRSM parameters
        crsm = CRSM_Metrics()
        crsm.Φ = np.clip(abs(mean_param), 0, 1)
        crsm.Γ = np.clip(std_param, 0, 1)
        crsm.Λ = 1 - crsm.Γ
        
        if phi_network:
            # Apply φ-network scaling
            crsm.Ξ = crsm.Φ * PHI
        else:
            crsm.Ξ = crsm.Φ * 2
        
        crsm.fidelity = 1 - crsm.Γ
        crsm.P_error = np.exp(-crsm.Φ * 10)
        crsm.det_g = crsm.Φ
        crsm.R_scalar = crsm.Γ
        crsm.gauge_invariant = crsm.Γ < 0.01
        crsm.torsion_locked = crsm.Ξ > 1.5
        crsm.healed = crsm.fidelity > 0.95
        
        return crsm
    
    def unified_correction(self, inputs: Dict) -> Dict[str, CRSM_Metrics]:
        """
        Apply unified correction across all three domains.
        
        Args:
            inputs: Dictionary with domain-specific inputs
                - 'physics': (quaternion, lattice)
                - 'egyptology': list of hieroglyphs
                - 'computation': parameter array
        
        Returns:
            Dictionary with CRSM metrics for each domain
        """
        results = {}
        
        if 'physics' in inputs:
            q, lattice = inputs['physics']
            results['physics'] = self.physics_correction(q, lattice)
        
        if 'egyptology' in inputs:
            hieroglyphs = inputs['egyptology']
            results['egyptology'] = self.egyptology_correction(hieroglyphs)
        
        if 'computation' in inputs:
            params = inputs['computation']
            results['computation'] = self.computation_correction(params)
        
        return results


# =============================================================================
# VISUALIZATION (Optional)
# =============================================================================

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def visualize_quaternion_rotation(q: Quaternion, v: np.ndarray = None):
    """
    Visualize quaternion rotation on 3D sphere.
    
    Args:
        q: Quaternion
        v: Optional vector to rotate
    """
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for visualization")
        return
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Draw unit sphere
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x, y, z, color='lightblue', alpha=0.3)
    
    # Plot quaternion as point on S³
    w, x_q, y_q, z_q = q.to_spherical()
    ax.scatter3D([x_q], [y_q], [z_q], color='red', s=100, label='Quaternion')
    
    # Plot rotation axis
    axis, angle = q.to_axis_angle()
    if axis is not None:
        ax.quiver(0, 0, 0, axis[0], axis[1], axis[2], color='green', 
                  length=1.0, label='Rotation Axis')
    
    ax.set_xlim([-1, 1])
    ax.set_ylim([-1, 1])
    ax.set_zlim([-1, 1])
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Quaternion on S³')
    ax.legend()
    plt.show()


def visualize_tetrahedral_lattice(lattice: TetrahedralLattice, max_nodes: int = 50):
    """
    Visualize tetrahedral lattice.
    
    Args:
        lattice: Tetrahedral lattice
        max_nodes: Maximum nodes to plot
    """
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for visualization")
        return
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot nodes
    node_positions = [node.position / L_P for node in lattice.nodes[:max_nodes]]
    xs = [p[0] for p in node_positions]
    ys = [p[1] for p in node_positions]
    zs = [p[2] for p in node_positions]
    ax.scatter3D(xs, ys, zs, color='blue', s=10, label='Nodes')
    
    # Plot some connections
    for i, node in enumerate(lattice.nodes[:max_nodes]):
        for conn_idx in node.connections[:3]:  # Limit connections for clarity
            if conn_idx < len(lattice.nodes):
                other = lattice.nodes[conn_idx]
                ax.plot([node.position[0]/L_P, other.position[0]/L_P],
                        [node.position[1]/L_P, other.position[1]/L_P],
                        [node.position[2]/L_P, other.position[2]/L_P],
                        color='gray', alpha=0.3)
    
    ax.set_xlabel('X (Planck units)')
    ax.set_ylabel('Y (Planck units)')
    ax.set_zlabel('Z (Planck units)')
    ax.set_title(f'Tetrahedral Lattice ({len(lattice.nodes)} nodes)')
    ax.legend()
    plt.show()


def plot_crsm_comparison(crsm_list: Dict[str, CRSM_Metrics]):
    """
    Plot comparison of CRSM metrics across domains.
    
    Args:
        crsm_list: Dictionary of domain -> CRSM_Metrics
    """
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for visualization")
        return
    
    metrics = ['Φ', 'Γ', 'Λ', 'Ξ', 'fidelity']
    domains = list(crsm_list.keys())
    values = {m: [getattr(crsm_list[d], m) for d in domains] for m in metrics}
    
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics):
        axes[i].bar(domains, values[metric], color=['blue', 'green', 'red'][:len(domains)])
        axes[i].set_title(metric)
        axes[i].set_ylabel('Value')
    
    plt.tight_layout()
    plt.suptitle('CRSM Metrics Comparison Across Domains', y=1.02)
    plt.show()


# =============================================================================
# MAIN DEMONSTRATION
# =============================================================================


def run_demo():
    """Run demonstration of quaternion to CRSM mapping."""
    print("=" * 80)
    print("OSIRIS Unified Structural Theory - Quaternion to CRSM Mapping Demo")
    print("=" * 80)
    print()
    
    # 1. Create a quaternion rotation
    print("1. Creating Quaternion Rotation")
    print("-" * 40)
    axis = np.array([1, 1, 1])  # Rotation around [1,1,1] axis
    angle = np.pi / 4  # 45 degree rotation
    q = Quaternion.from_axis_angle(axis, angle)
    print(f"   Quaternion: {q}")
    print(f"   Axis: {axis}, Angle: {angle:.4f} radians")
    print()
    
    # 2. Convert to spherical coordinates
    print("2. Spherical S³ Mapping")
    print("-" * 40)
    w, x, y, z = q.to_spherical()
    print(f"   S³ Coordinates: w={w:.4f}, x={x:.4f}, y={y:.4f}, z={z:.4f}")
    print(f"   Norm: {q.norm:.4f}")
    print()
    
    # 3. Convert to rotation matrix
    print("3. Rotation Matrix")
    print("-" * 40)
    R = q.to_rotation_matrix()
    print(f"   Rotation Matrix:\n{R}")
    print()
    
    # 4. Create tetrahedral lattice
    print("4. Creating Tetrahedral Lattice")
    print("-" * 40)
    lattice = TetrahedralLattice(size=3)
    print(f"   Nodes: {len(lattice.nodes)}")
    print(f"   Tetrahedrons: {len(lattice.tetrahedrons)}")
    print()
    
    # 5. Apply wavefront
    print("5. Applying Wavefront Expansion")
    print("-" * 40)
    lattice.apply_wavefront(0, amplitude=1.0, wavelength=2.0)
    print(f"   Wavefront applied from node 0")
    print()
    
    # 6. Compute CRSM metrics from quaternion
    print("6. Computing CRSM Metrics from Quaternion")
    print("-" * 40)
    crsm_q = CRSM_Metrics().from_quaternion(q)
    print(f"   {crsm_q}")
    print(f"   Full metrics: {json.dumps(crsm_q.to_dict(), indent=2)}")
    print()
    
    # 7. Compute CRSM metrics from lattice
    print("7. Computing CRSM Metrics from Tetrahedral Lattice")
    print("-" * 40)
    crsm_lattice = CRSM_Metrics().from_tetrahedral_lattice(lattice)
    print(f"   {crsm_lattice}")
    print(f"   Full metrics: {json.dumps(crsm_lattice.to_dict(), indent=2)}")
    print()
    
    # 8. Compute CRSM metrics via metric tensor
    print("8. Computing CRSM Metrics via Metric Tensor")
    print("-" * 40)
    g = MetricTensor()
    g.from_quaternion_field([q])
    crsm_tensor = CRSM_Metrics().from_metric_tensor(g)
    print(f"   {crsm_tensor}")
    print(f"   Full metrics: {json.dumps(crsm_tensor.to_dict(), indent=2)}")
    print()
    
    # 9. Unified correction demonstration
    print("9. Unified Correction Across Domains")
    print("-" * 40)
    correction = UnifiedCorrection()
    
    # Physics domain
    crsm_physics = correction.physics_correction(q, lattice)
    print(f"   Physics: {crsm_physics}")
    
    # Egyptology domain
    hieroglyphs = ['𓊨', '𓍝', '𓅜', '𓊨', '𓍝']  # Seat, Balance, Akh
    crsm_egypt = correction.egyptology_correction(hieroglyphs)
    print(f"   Egyptology: {crsm_egypt}")
    
    # Computation domain
    params = np.random.randn(100)  # Random neural parameters
    crsm_computation = correction.computation_correction(params)
    print(f"   Computation: {crsm_computation}")
    print()
    
    # 10. Reference comparison
    print("10. Comparison with NCLLM-Sovereign Reference")
    print("-" * 40)
    print("   Reference CRSM Metrics:")
    for k, v in CRSM_REFERENCE.items():
        print(f"     {k}: {v}")
    print()
    
    # Visualization (if available)
    if HAS_MATPLOTLIB:
        print("11. Generating Visualizations")
        print("-" * 40)
        visualize_quaternion_rotation(q)
        visualize_tetrahedral_lattice(lattice)
        plot_crsm_comparison({
            'Physics': crsm_q,
            'Egyptology': crsm_egypt,
            'Computation': crsm_computation
        })
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


# =============================================================================
# MAIN
# =============================================================================


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Quaternion to CRSM Mapping Implementation'
    )
    parser.add_argument('--demo', action='store_true', 
                        help='Run demonstration')
    parser.add_argument('--visualize', action='store_true',
                        help='Enable visualizations')
    
    args = parser.parse_args()
    
    if args.visualize:
        HAS_MATPLOTLIB = True
    
    if args.demo:
        run_demo()
    else:
        # Basic example
        print("Quaternion to CRSM Mapping Implementation")
        print("=" * 50)
        
        # Create a simple quaternion
        q = Quaternion.from_axis_angle([0, 0, 1], np.pi/2)
        print(f"Quaternion: {q}")
        
        # Convert to CRSM
        crsm = CRSM_Metrics().from_quaternion(q)
        print(f"CRSM Metrics: {crsm}")
        print(f"\nFull output:\n{json.dumps(crsm.to_dict(), indent=2)}")
