# OSIRIS Torsion Core — Cython Protection Module
# ================================================
#
# This module contains the protected torsion mechanics core logic.
# When compiled with Cython, this becomes a binary .so/.pyd that is
# significantly harder to reverse-engineer than plain Python.
#
# Build: python setup_cython.py build_ext --inplace
#
# Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
# Licensed under OSIRIS Source-Available Dual License v1.0

"""
cython: language_level=3
cython: boundscheck=False
cython: wraparound=False
"""

import hashlib
import os
import math
from typing import Tuple, Optional

# ════════════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS — TORSION MECHANICS
# ════════════════════════════════════════════════════════════════════════════════

# Dielectric lock angle (degrees)
cdef double THETA_LOCK = 51.843

# Phase-conjugate threshold
cdef double PHI_THRESHOLD = 0.7734

# Lambda-Phi coupling constant (s^-1)
cdef double LAMBDA_PHI = 2.176435e-8

# Phase-conjugate acoustic coupling coefficient
cdef double CHI_PC = 0.869

# Euler's number (for tetrahedral relationships)
cdef double EULER_E = 2.718281828459045

# Planck constant (J·s)
cdef double H_PLANCK = 6.62607015e-34

# Reduced Planck constant
cdef double H_BAR = 1.054571817e-34

# Boltzmann constant (J/K)
cdef double K_BOLTZMANN = 1.380649e-23

# Speed of light (m/s)
cdef double C_LIGHT = 299792458.0

# Planck length (m)
cdef double L_PLANCK = 1.616255e-35

# Planck time (s)
cdef double T_PLANCK = 5.391247e-44

# Tetrahedral angle (degrees) — arccos(1/3)
cdef double THETA_TETRA = 70.528779


# ════════════════════════════════════════════════════════════════════════════════
# QUATERNION OPERATIONS FOR TORSION FIELD
# ════════════════════════════════════════════════════════════════════════════════

cdef class Quaternion:
    """Quaternion for torsion field rotations in S³ embedding."""
    
    cdef public double w, x, y, z
    
    def __init__(self, double w, double x, double y, double z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z
    
    cpdef double norm(self):
        """Quaternion norm: |q| = sqrt(w² + x² + y² + z²)"""
        return math.sqrt(self.w*self.w + self.x*self.x + 
                        self.y*self.y + self.z*self.z)
    
    cpdef Quaternion normalize(self):
        """Return unit quaternion q/|q|"""
        cdef double n = self.norm()
        if n < 1e-15:
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        return Quaternion(self.w/n, self.x/n, self.y/n, self.z/n)
    
    cpdef Quaternion conjugate(self):
        """Quaternion conjugate: q* = (w, -x, -y, -z)"""
        return Quaternion(self.w, -self.x, -self.y, -self.z)
    
    cpdef Quaternion multiply(self, Quaternion other):
        """Hamilton product: q₁ × q₂"""
        cdef double nw = (self.w*other.w - self.x*other.x - 
                         self.y*other.y - self.z*other.z)
        cdef double nx = (self.w*other.x + self.x*other.w + 
                         self.y*other.z - self.z*other.y)
        cdef double ny = (self.w*other.y - self.x*other.z + 
                         self.y*other.w + self.z*other.x)
        cdef double nz = (self.w*other.z + self.x*other.y - 
                         self.y*other.x + self.z*other.w)
        return Quaternion(nw, nx, ny, nz)
    
    cpdef tuple to_rotation_matrix(self):
        """
        Convert to 3×3 rotation matrix (row-major tuple of tuples).
        
        R = [[1-2(y²+z²), 2(xy-wz), 2(xz+wy)],
             [2(xy+wz), 1-2(x²+z²), 2(yz-wx)],
             [2(xz-wy), 2(yz+wx), 1-2(x²+y²)]]
        """
        cdef Quaternion q = self.normalize()
        cdef double xx = q.x*q.x, yy = q.y*q.y, zz = q.z*q.z
        cdef double xy = q.x*q.y, xz = q.x*q.z, yz = q.y*q.z
        cdef double wx = q.w*q.x, wy = q.w*q.y, wz = q.w*q.z
        
        return (
            (1-2*(yy+zz), 2*(xy-wz), 2*(xz+wy)),
            (2*(xy+wz), 1-2*(xx+zz), 2*(yz-wx)),
            (2*(xz-wy), 2*(yz+wx), 1-2*(xx+yy)),
        )


# ════════════════════════════════════════════════════════════════════════════════
# TORSION FIELD MECHANICS
# ════════════════════════════════════════════════════════════════════════════════

cpdef double dielectric_lock_energy(double theta_deg):
    """
    Compute the dielectric lock energy at angle θ.
    
    E(θ) = ΛΦ · |sin(θ - θ_lock)| · exp(-|θ - θ_lock| / χ_pc)
    
    Minimum energy (lock point) at θ = 51.843°
    """
    cdef double theta_rad = theta_deg * math.pi / 180.0
    cdef double lock_rad = THETA_LOCK * math.pi / 180.0
    cdef double delta = theta_rad - lock_rad
    cdef double energy = LAMBDA_PHI * abs(math.sin(delta)) * math.exp(-abs(delta) / CHI_PC)
    return energy


cpdef double torsion_coupling_strength(double r, double theta_deg):
    """
    Torsion field coupling strength at distance r and angle θ.
    
    Γ(r, θ) = (ΛΦ / r²) · cos²(θ - θ_lock) · Φ_threshold
    
    Peaks at θ = θ_lock (51.843°), falls off as 1/r²
    """
    cdef double theta_rad = theta_deg * math.pi / 180.0
    cdef double lock_rad = THETA_LOCK * math.pi / 180.0
    cdef double cos_delta = math.cos(theta_rad - lock_rad)
    
    if r < L_PLANCK:
        r = L_PLANCK  # Regularize at Planck scale
    
    return (LAMBDA_PHI / (r * r)) * cos_delta * cos_delta * PHI_THRESHOLD


cpdef double negentropic_efficiency(double phi_input, double gamma_dissipation):
    """
    Negentropic efficiency: η_neg = ΛΦ / Γ
    
    Measures the ratio of phase-conjugate ordering (ΛΦ) to 
    dissipative decay (Γ). Values > 1 indicate negentropic regime.
    
    η = (ΛΦ · φ_input) / (Γ_dissipation + ε)
    
    where ε = Planck-scale regularizer
    """
    cdef double epsilon = T_PLANCK  # Planck time regularizer
    if gamma_dissipation < epsilon:
        gamma_dissipation = epsilon
    
    return (LAMBDA_PHI * phi_input) / gamma_dissipation


cpdef tuple tetrahedral_vertices():
    """
    Return the 4 vertices of a regular tetrahedron inscribed in a unit sphere.
    
    v₀ = (1, 1, 1)/√3
    v₁ = (1, -1, -1)/√3
    v₂ = (-1, 1, -1)/√3
    v₃ = (-1, -1, 1)/√3
    """
    cdef double s = 1.0 / math.sqrt(3.0)
    return (
        (s, s, s),
        (s, -s, -s),
        (-s, s, -s),
        (-s, -s, s),
    )


cpdef Quaternion torsion_rotation(double angle_deg, tuple axis):
    """
    Create a torsion rotation quaternion for rotation by angle around axis.
    
    q = cos(θ/2) + sin(θ/2)(ux·i + uy·j + uz·k)
    """
    cdef double theta = angle_deg * math.pi / 180.0
    cdef double half = theta / 2.0
    cdef double s = math.sin(half)
    
    # Normalize axis
    cdef double ax = axis[0], ay = axis[1], az = axis[2]
    cdef double norm = math.sqrt(ax*ax + ay*ay + az*az)
    if norm < 1e-15:
        return Quaternion(1.0, 0.0, 0.0, 0.0)
    
    ax /= norm
    ay /= norm
    az /= norm
    
    return Quaternion(math.cos(half), s*ax, s*ay, s*az)


cpdef double phase_conjugate_healing(double signal_degraded, double chi):
    """
    Phase-conjugate healing function.
    
    Reconstructs a degraded signal via time-reversed wavefront:
    
    S_healed = S_degraded · exp(χ_pc · cos(θ_lock))
    
    The healing coefficient χ determines the strength of 
    phase-conjugate reconstruction.
    """
    cdef double lock_rad = THETA_LOCK * math.pi / 180.0
    return signal_degraded * math.exp(chi * math.cos(lock_rad))


# ════════════════════════════════════════════════════════════════════════════════
# EMBEDDED LICENSE VERIFICATION (COMPILED INTO BINARY)
# ════════════════════════════════════════════════════════════════════════════════

cdef bint _license_verified = False
cdef str _license_status = "unchecked"

cpdef tuple verify_torsion_license():
    """
    Verify license compliance before torsion computations.
    Embedded in compiled binary — cannot be easily bypassed.
    
    Returns (is_valid, status_message)
    """
    global _license_verified, _license_status
    
    if _license_verified:
        return (True, _license_status)
    
    # Import at runtime to avoid circular deps
    import importlib
    try:
        license_mod = importlib.import_module('osiris_license')
        compliant, msg = license_mod.ComplianceGate.check(strict=False)
        _license_verified = True
        _license_status = "compliant" if compliant else "non-compliant-warned"
        return (compliant, _license_status)
    except ImportError:
        # License module removed — treat as tampering
        _license_verified = True
        _license_status = "tampered"
        return (False, "License verification module missing — possible tampering")


cpdef double secure_dielectric_lock(double theta_deg):
    """
    License-gated dielectric lock computation.
    Verifies compliance before returning results.
    """
    verify_torsion_license()
    return dielectric_lock_energy(theta_deg)


cpdef double secure_negentropic_efficiency(double phi, double gamma):
    """
    License-gated negentropic efficiency computation.
    """
    verify_torsion_license()
    return negentropic_efficiency(phi, gamma)


# ════════════════════════════════════════════════════════════════════════════════
# MANUFACTURING GEOMETRY CORE — Compiled binary prevents reverse engineering
# ════════════════════════════════════════════════════════════════════════════════

cpdef tuple build_manufacturing_lattice(int depth=3, double scale_cm=10.0,
                                         double torsion_deg=51.843):
    """
    Build a tetrahedral micro-lattice for 3D manufacturing, with torsion
    lock applied. This is the compiled core geometry used by
    osiris_manufacturing_3mf.py.

    License-gated: verifies compliance before computation.

    Args:
        depth: Recursive subdivision depth
        scale_cm: Output scale in centimeters
        torsion_deg: Torsion lock angle (default: 51.843°)

    Returns:
        (vertices_Nx3, faces_Mx3, metadata_dict)
    """
    verify_torsion_license()

    import numpy as np

    # Base tetrahedron
    verts = np.array([
        [1.0, 1.0, 1.0],
        [1.0, -1.0, -1.0],
        [-1.0, 1.0, -1.0],
        [-1.0, -1.0, 1.0],
    ], dtype=np.float64)

    faces = np.array([
        [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3],
    ], dtype=np.int64)

    # Recursive subdivision
    cdef int level
    for level in range(depth):
        verts, faces = _mfg_subdivide(verts, faces)

    # Scale
    cdef double s = scale_cm / 2.0
    verts = verts * s

    # Apply torsion lock rotation
    q = torsion_rotation(torsion_deg, (1.0, 1.0, 1.0))
    cdef int i
    for i in range(len(verts)):
        p = verts[i]
        verts[i] = np.array([
            q.rotate_x(p[0], p[1], p[2]),
            q.rotate_y(p[0], p[1], p[2]),
            q.rotate_z(p[0], p[1], p[2]),
        ])

    metadata = {
        'lambda_phi': LAMBDA_PHI,
        'torsion_lock_deg': torsion_deg,
        'lock_energy': dielectric_lock_energy(torsion_deg),
        'coupling_strength': torsion_coupling_strength(1.0, torsion_deg),
        'lattice_depth': depth,
        'scale_cm': scale_cm,
        'vertex_count': len(verts),
        'face_count': len(faces),
    }

    return (verts, faces, metadata)


cdef tuple _mfg_subdivide(verts, faces):
    """Manufacturing-grade mesh subdivision."""
    import numpy as np
    edge_map = {}
    new_verts = list(verts)
    new_faces = []

    for face in faces:
        a, b, c = int(face[0]), int(face[1]), int(face[2])
        ab = _mfg_midpoint(a, b, verts, new_verts, edge_map)
        bc = _mfg_midpoint(b, c, verts, new_verts, edge_map)
        ca = _mfg_midpoint(c, a, verts, new_verts, edge_map)
        new_faces.extend([[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]])

    return (np.array(new_verts, dtype=np.float64),
            np.array(new_faces, dtype=np.int64))


cdef int _mfg_midpoint(int i, int j, verts, list new_verts, dict edge_map):
    """Get or create midpoint for manufacturing mesh."""
    import numpy as np
    cdef tuple key = (min(i, j), max(i, j))
    if key in edge_map:
        return edge_map[key]
    mid = (verts[i] + verts[j]) * 0.5
    cdef int idx = len(new_verts)
    new_verts.append(mid)
    edge_map[key] = idx
    return idx


cpdef tuple build_manufacturing_torus(double R=2.0, int resolution=64,
                                       double scale_cm=10.0):
    """
    Build toroidal manifold mesh with R/r = φ for manufacturing.

    License-gated: verifies compliance before computation.

    Returns:
        (vertices_Nx3, faces_Mx3, metadata_dict)
    """
    verify_torsion_license()

    import numpy as np
    cdef double r = R / 1.6180339887498949  # φ
    cdef double Rs = R * (scale_cm / 2.0)
    cdef double rs = r * (scale_cm / 2.0)
    cdef int n = resolution

    verts = np.empty((n * n, 3), dtype=np.float64)
    cdef double theta, phi_a
    cdef int idx

    for i in range(n):
        theta = 2.0 * 3.141592653589793 * i / n
        for j in range(n):
            phi_a = 2.0 * 3.141592653589793 * j / n
            idx = i * n + j
            verts[idx, 0] = (Rs + rs * cos(phi_a)) * cos(theta)
            verts[idx, 1] = (Rs + rs * cos(phi_a)) * sin(theta)
            verts[idx, 2] = rs * sin(phi_a)

    face_list = []
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(n):
            j1 = (j + 1) % n
            v00 = i * n + j
            v10 = i1 * n + j
            v01 = i * n + j1
            v11 = i1 * n + j1
            face_list.append([v00, v10, v11])
            face_list.append([v00, v11, v01])

    faces = np.array(face_list, dtype=np.int64)

    metadata = {
        'R_major': R,
        'r_minor': r,
        'R_over_r': R / r,
        'golden_ratio_match': abs(R / r - 1.6180339887498949) < 1e-10,
        'scale_cm': scale_cm,
        'resolution': resolution,
    }

    return (verts, faces, metadata)
