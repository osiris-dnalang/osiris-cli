#!/usr/bin/env python3
"""
OSIRIS 3D Manufacturing Pipeline — Geometric Engine & 3MF Export
=================================================================

Translates Structural Genes (G0-G11) from the 72-Gene Organism into
high-fidelity mesh data for additive manufacturing.

Core Geometry:
  • Tetrahedral Micro-Lattice at vertices (±1,±1,±1)
  • Binary Tetrahedral Group 2T quaternion rotations
  • Toroidal dielectric manifold with R/r = φ (golden ratio)
  • Torsion lock at θ = 51.843°

Output Formats:
  • .3mf  (3D Manufacturing Format via lib3mf or trimesh)
  • .stl  (fallback if lib3mf unavailable)
  • .gcode (via external slicer CLI)

Metadata Embedding:
  Every exported file includes ΛΦ/Γ dynamics parameters,
  torsion lock angle, quaternion group, and organism version.

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

import os
import sys
import json
import math
import hashlib
import logging
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import numpy as np

logger = logging.getLogger('OSIRIS_MFG')

# ════════════════════════════════════════════════════════════════════════════════
# MESH LIBRARY — trimesh preferred, lib3mf optional
# ════════════════════════════════════════════════════════════════════════════════

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    import lib3mf
    HAS_LIB3MF = True
except ImportError:
    HAS_LIB3MF = False

# ════════════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS (from organism DNA)
# ════════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8          # Universal constant (Planck-scale)
TORSION_LOCK_ANGLE = 51.843       # Degrees — critical lock angle
GOLDEN_RATIO = (1 + math.sqrt(5)) / 2  # φ ≈ 1.6180339887
QUATERNION_GROUP = "binary_tetrahedral_2T"
GAMMA_DECOHERENCE = 0.092
PHI_IIT = 0.7734
MANIFOLD_DIMENSION = 7

# Tetrahedral vertex positions (±1, ±1, ±1) — alternating parity
TETRA_VERTICES = np.array([
    [1.0, 1.0, 1.0],
    [1.0, -1.0, -1.0],
    [-1.0, 1.0, -1.0],
    [-1.0, -1.0, 1.0],
], dtype=np.float64)

# Tetrahedral face indices (4 triangular faces)
TETRA_FACES = np.array([
    [0, 1, 2],
    [0, 1, 3],
    [0, 2, 3],
    [1, 2, 3],
], dtype=np.int64)

# Binary Tetrahedral Group 2T — 24 elements as unit quaternions
# Format: (w, x, y, z)
BINARY_TETRAHEDRAL_2T = [
    # 8 quaternions from cube vertices
    (1, 0, 0, 0), (-1, 0, 0, 0),
    (0, 1, 0, 0), (0, -1, 0, 0),
    (0, 0, 1, 0), (0, 0, -1, 0),
    (0, 0, 0, 1), (0, 0, 0, -1),
    # 16 quaternions from half-integer positions
    *[(s0*0.5, s1*0.5, s2*0.5, s3*0.5)
      for s0 in (1, -1) for s1 in (1, -1)
      for s2 in (1, -1) for s3 in (1, -1)],
]


# ════════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

class ManufacturingMode(Enum):
    """Manufacturing output modes"""
    TETRAHEDRAL_LATTICE = "tetrahedral_lattice"
    TOROIDAL_MANIFOLD = "toroidal_manifold"
    PLANCK_REFERENCE_CUBE = "planck_reference_cube"
    ACOUSTIC_RESONANCE_CAVITY = "acoustic_resonance_cavity"
    TORSION_LOCK_VISUALIZER = "torsion_lock_visualizer"
    QUATERNION_ORBIT_MODEL = "quaternion_orbit_model"


class PrinterType(Enum):
    """Supported printer types"""
    BAMBU_P1S = "bambu_p1s"
    BAMBU_A1_MINI = "bambu_a1_mini"
    ELEGOO_CENTAURI_2 = "elegoo_centauri_2"
    GENERIC_FDM = "generic_fdm"
    GENERIC_RESIN = "generic_resin"


@dataclass
class ManufacturingConfig:
    """Configuration for a manufacturing job"""
    mode: ManufacturingMode
    scale_cm: float = 10.0              # Output scale in centimeters
    resolution: int = 64                 # Mesh resolution (subdivisions)
    torsion_angle: float = TORSION_LOCK_ANGLE
    lattice_depth: int = 3               # Recursive lattice subdivision depth
    toroid_major_radius: float = 2.0     # R (major radius for torus)
    toroid_minor_radius: float = 0.0     # auto-computed as R/φ if 0
    include_metadata: bool = True
    output_format: str = "3mf"           # "3mf", "stl", or "both"
    printer_type: PrinterType = PrinterType.GENERIC_FDM

    def __post_init__(self):
        if self.toroid_minor_radius == 0.0:
            self.toroid_minor_radius = self.toroid_major_radius / GOLDEN_RATIO


@dataclass
class ManufacturingResult:
    """Result of a manufacturing generation"""
    model_path: str
    format: str
    vertices: int
    faces: int
    volume_cm3: float
    bounding_box_cm: Tuple[float, float, float]
    metadata: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    gcode_path: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════════
# QUATERNION MATH
# ════════════════════════════════════════════════════════════════════════════════

def quaternion_multiply(q1, q2):
    """Hamilton product of two quaternions (w, x, y, z)"""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def quaternion_rotate(q, point):
    """Rotate a 3D point by quaternion q = (w, x, y, z)"""
    w, x, y, z = q
    # Rotation matrix from quaternion
    R = np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
        [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
        [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)],
    ])
    return R @ np.asarray(point)


def torsion_rotation_matrix(theta_deg):
    """Rotation matrix for torsion lock angle about the [1,1,1] axis"""
    theta = math.radians(theta_deg)
    # Axis: normalized [1,1,1]
    n = np.array([1, 1, 1]) / math.sqrt(3)
    c, s = math.cos(theta), math.sin(theta)
    nx, ny, nz = n
    R = np.array([
        [c + nx*nx*(1-c),     nx*ny*(1-c) - nz*s, nx*nz*(1-c) + ny*s],
        [ny*nx*(1-c) + nz*s,  c + ny*ny*(1-c),     ny*nz*(1-c) - nx*s],
        [nz*nx*(1-c) - ny*s,  nz*ny*(1-c) + nx*s,  c + nz*nz*(1-c)],
    ])
    return R


# ════════════════════════════════════════════════════════════════════════════════
# MESH GENERATORS — Gene-Mapped Geometry
# ════════════════════════════════════════════════════════════════════════════════

class GeometricEngine:
    """
    Translates Structural Genes (G0-G11) into mesh geometry.

    Gene → Geometry Mapping:
      G0: TetrahedralLatticeConstructor  → Base tetrahedron + lattice
      G1: QuaternionFieldProjector       → 2T group orbit copies
      G2: ToroidalDielectricCurvature    → Toroidal manifold surface
      G3: TorsionLockInitializer         → 51.843° rotational offset
      G4: LatticeEdgeVectorComputer      → Edge struts between vertices
      G5: CrystallizationController      → Lattice densification
      G6: QuaternionSeedInjector         → Node markers at seed points
      G7: PhaseAlignmentLocker           → Conjugate pair indicators
      G8: LatticeEnergyComputer          → Color mapping by energy
      G9: ManifoldMetricTensor           → Surface curvature viz
      G10: DielectricPermittivityCtrl    → Anisotropy displacement
      G11: LockConditionEnforcer         → Lock violation markers
    """

    def __init__(self, config: ManufacturingConfig):
        self.config = config
        self.gene_outputs: Dict[str, Any] = {}

    # ── G0: Tetrahedral Lattice Constructor ────────────────────────────────

    def g0_tetrahedral_lattice(self, depth: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Construct tetrahedral micro-lattice with vertices at (±1,±1,±1).
        Recursively subdivides to `depth` levels.
        """
        depth = depth or self.config.lattice_depth
        vertices = TETRA_VERTICES.copy()
        faces = TETRA_FACES.copy()

        for _ in range(depth):
            vertices, faces = self._subdivide_tetrahedron(vertices, faces)

        # Scale to requested cm
        scale = self.config.scale_cm / 2.0  # base tetra spans [-1,1]
        vertices = vertices * scale

        self.gene_outputs['G0'] = {
            'lattice_structure': vertices,
            'vertex_positions': vertices,
        }
        return vertices, faces

    @staticmethod
    def _subdivide_tetrahedron(vertices, faces):
        """Midpoint subdivision of tetrahedral mesh"""
        edge_midpoints = {}
        new_vertices = list(vertices)
        new_faces = []

        def get_midpoint(i, j):
            key = (min(i, j), max(i, j))
            if key not in edge_midpoints:
                mid = (vertices[i] + vertices[j]) / 2.0
                edge_midpoints[key] = len(new_vertices)
                new_vertices.append(mid)
            return edge_midpoints[key]

        for face in faces:
            a, b, c = face
            ab = get_midpoint(a, b)
            bc = get_midpoint(b, c)
            ca = get_midpoint(c, a)
            new_faces.extend([
                [a, ab, ca],
                [b, bc, ab],
                [c, ca, bc],
                [ab, bc, ca],
            ])

        return np.array(new_vertices), np.array(new_faces)

    # ── G1: Quaternion Field Projector ─────────────────────────────────────

    def g1_quaternion_field(self, vertices: np.ndarray) -> List[np.ndarray]:
        """
        Project binary tetrahedral group 2T onto lattice nodes.
        Creates 24 rotated copies of the lattice at each vertex.
        """
        orbit_points = []
        for q in BINARY_TETRAHEDRAL_2T:
            rotated = np.array([quaternion_rotate(q, v) for v in vertices])
            orbit_points.append(rotated)

        self.gene_outputs['G1'] = {
            'quaternion_field': len(BINARY_TETRAHEDRAL_2T),
            'rotation_states': len(orbit_points),
        }
        return orbit_points

    # ── G2: Toroidal Manifold ─────────────────────────────────────────────

    def g2_toroidal_manifold(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Synthesize toroidal dielectric manifold with R/r = φ (golden ratio).
        """
        R = self.config.toroid_major_radius * (self.config.scale_cm / 2.0)
        r = self.config.toroid_minor_radius * (self.config.scale_cm / 2.0)
        n = self.config.resolution

        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        phi = np.linspace(0, 2 * np.pi, n, endpoint=False)
        theta_grid, phi_grid = np.meshgrid(theta, phi)

        x = (R + r * np.cos(phi_grid)) * np.cos(theta_grid)
        y = (R + r * np.cos(phi_grid)) * np.sin(theta_grid)
        z = r * np.sin(phi_grid)

        # Flatten to vertex array
        vertices = np.stack([x.ravel(), y.ravel(), z.ravel()], axis=-1)

        # Generate quad faces → split to triangles
        faces = []
        for i in range(n):
            for j in range(n):
                i1 = (i + 1) % n
                j1 = (j + 1) % n
                v00 = i * n + j
                v10 = i1 * n + j
                v01 = i * n + j1
                v11 = i1 * n + j1
                faces.append([v00, v10, v11])
                faces.append([v00, v11, v01])

        faces = np.array(faces)

        self.gene_outputs['G2'] = {
            'toroidal_manifold': f"R={R:.3f} r={r:.3f} R/r={R/r:.6f}",
            'dielectric_tensor': 'toroidal_anisotropic',
        }
        return vertices, faces

    # ── G3: Torsion Lock ──────────────────────────────────────────────────

    def g3_apply_torsion_lock(self, vertices: np.ndarray) -> np.ndarray:
        """
        Lock torsion angle at θ = 51.843° via rotation about [1,1,1] axis.
        """
        R = torsion_rotation_matrix(self.config.torsion_angle)
        locked = vertices @ R.T

        self.gene_outputs['G3'] = {
            'theta_lock': self.config.torsion_angle,
            'lock_stability': 1.0,
        }
        return locked

    # ── G4: Edge Vectors ──────────────────────────────────────────────────

    def g4_edge_struts(self, vertices: np.ndarray, faces: np.ndarray,
                       strut_radius: float = 0.05) -> Optional[Any]:
        """
        Compute edge vectors and generate cylindrical struts between vertices.
        Returns a trimesh object of the strut network (if trimesh available).
        """
        edges = set()
        for face in faces:
            for i in range(len(face)):
                edge = (min(face[i], face[(i+1) % len(face)]),
                        max(face[i], face[(i+1) % len(face)]))
                edges.add(edge)

        edge_vectors = []
        for i, j in edges:
            vec = vertices[j] - vertices[i]
            edge_vectors.append({
                'from': i, 'to': j,
                'vector': vec.tolist(),
                'length': float(np.linalg.norm(vec)),
                'dihedral': float(np.degrees(np.arccos(
                    np.clip(np.dot(vec / np.linalg.norm(vec),
                                   np.array([1, 1, 1]) / math.sqrt(3)), -1, 1)
                ))),
            })

        self.gene_outputs['G4'] = {
            'edge_vectors': len(edge_vectors),
            'dihedral_angles': [e['dihedral'] for e in edge_vectors[:6]],
        }

        if not HAS_TRIMESH:
            return None

        # Build cylinder struts
        struts = []
        r = strut_radius * self.config.scale_cm
        for i, j in edges:
            segment = np.array([vertices[i], vertices[j]])
            cyl = trimesh.creation.cylinder(radius=r, segment=segment)
            struts.append(cyl)

        if struts:
            return trimesh.util.concatenate(struts)
        return None

    # ── Composite Generators ──────────────────────────────────────────────

    def generate_tetrahedral_lattice(self) -> 'ManufacturingResult':
        """Full tetrahedral lattice with torsion lock and edge struts."""
        verts, faces = self.g0_tetrahedral_lattice()
        verts = self.g3_apply_torsion_lock(verts)
        struts = self.g4_edge_struts(verts, faces)

        if HAS_TRIMESH:
            shell = trimesh.Trimesh(vertices=verts, faces=faces)
            if struts:
                mesh = trimesh.util.concatenate([shell, struts])
            else:
                mesh = shell
        else:
            mesh = None

        return self._export(mesh, verts, faces, "tetrahedral_lattice")

    def generate_toroidal_manifold(self) -> 'ManufacturingResult':
        """Toroidal manifold with R/r = φ and torsion lock."""
        verts, faces = self.g2_toroidal_manifold()
        verts = self.g3_apply_torsion_lock(verts)

        if HAS_TRIMESH:
            mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        else:
            mesh = None

        return self._export(mesh, verts, faces, "toroidal_manifold")

    def generate_planck_reference_cube(self) -> 'ManufacturingResult':
        """
        Planck-scale reference cube: a cube with tetrahedral subdivision
        interior showcasing the lattice within a bounding volume.
        """
        # Outer cube
        s = self.config.scale_cm / 2.0

        cube_verts = np.array([
            [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
            [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s],
        ])
        cube_faces = np.array([
            [0,1,2], [0,2,3], [4,6,5], [4,7,6],
            [0,5,1], [0,4,5], [2,7,3], [2,6,7],
            [0,3,7], [0,7,4], [1,5,6], [1,6,2],
        ])

        # Interior lattice
        lat_verts, lat_faces = self.g0_tetrahedral_lattice(depth=2)

        if HAS_TRIMESH:
            cube_mesh = trimesh.Trimesh(vertices=cube_verts, faces=cube_faces)
            lat_mesh = trimesh.Trimesh(vertices=lat_verts, faces=lat_faces)
            struts = self.g4_edge_struts(lat_verts, lat_faces, strut_radius=0.02)
            parts = [cube_mesh, lat_mesh]
            if struts:
                parts.append(struts)
            mesh = trimesh.util.concatenate(parts)
            all_verts = mesh.vertices
            all_faces = mesh.faces
        else:
            all_verts = np.vstack([cube_verts, lat_verts])
            offset = len(cube_verts)
            all_faces = np.vstack([cube_faces, lat_faces + offset])
            mesh = None

        return self._export(mesh, all_verts, all_faces, "planck_reference_cube")

    def generate_acoustic_resonance_cavity(self) -> 'ManufacturingResult':
        """
        Acoustic resonance cavity: toroidal shell with tetrahedral
        internal baffles for standing-wave resonance experiments.
        """
        # Outer torus
        outer_v, outer_f = self.g2_toroidal_manifold()

        # Inner tetrahedral baffles
        inner_v, inner_f = self.g0_tetrahedral_lattice(depth=2)
        inner_v = self.g3_apply_torsion_lock(inner_v)

        if HAS_TRIMESH:
            outer = trimesh.Trimesh(vertices=outer_v, faces=outer_f)
            inner = trimesh.Trimesh(vertices=inner_v, faces=inner_f)
            mesh = trimesh.util.concatenate([outer, inner])
            all_v, all_f = mesh.vertices, mesh.faces
        else:
            all_v = np.vstack([outer_v, inner_v])
            all_f = np.vstack([outer_f, inner_f + len(outer_v)])
            mesh = None

        return self._export(mesh, all_v, all_f, "acoustic_resonance_cavity")

    def generate_quaternion_orbit_model(self) -> 'ManufacturingResult':
        """
        Visualize 2T quaternion group orbits as spherical markers
        connected by edge struts at each rotated lattice position.
        """
        base_v, base_f = self.g0_tetrahedral_lattice(depth=1)
        orbits = self.g1_quaternion_field(base_v)

        if HAS_TRIMESH:
            parts = []
            for orbit_verts in orbits:
                lat = trimesh.Trimesh(vertices=orbit_verts, faces=base_f)
                parts.append(lat)
            mesh = trimesh.util.concatenate(parts)
            all_v, all_f = mesh.vertices, mesh.faces
        else:
            all_v_list, all_f_list = [], []
            offset = 0
            for orbit_verts in orbits:
                all_v_list.append(orbit_verts)
                all_f_list.append(base_f + offset)
                offset += len(orbit_verts)
            all_v = np.vstack(all_v_list)
            all_f = np.vstack(all_f_list)
            mesh = None

        return self._export(mesh, all_v, all_f, "quaternion_orbit_model")

    def generate(self) -> 'ManufacturingResult':
        """Generate mesh for the configured mode."""
        generators = {
            ManufacturingMode.TETRAHEDRAL_LATTICE: self.generate_tetrahedral_lattice,
            ManufacturingMode.TOROIDAL_MANIFOLD: self.generate_toroidal_manifold,
            ManufacturingMode.PLANCK_REFERENCE_CUBE: self.generate_planck_reference_cube,
            ManufacturingMode.ACOUSTIC_RESONANCE_CAVITY: self.generate_acoustic_resonance_cavity,
            ManufacturingMode.QUATERNION_ORBIT_MODEL: self.generate_quaternion_orbit_model,
            ManufacturingMode.TORSION_LOCK_VISUALIZER: self.generate_tetrahedral_lattice,
        }
        gen = generators.get(self.config.mode, self.generate_tetrahedral_lattice)
        return gen()

    # ── Export ─────────────────────────────────────────────────────────────

    def _build_metadata(self) -> Dict[str, Any]:
        """Build ΛΦ/Γ dynamics metadata for embedding in exported files."""
        return {
            "generator": "OSIRIS Manufacturing Pipeline v1.0",
            "organism": "72-Gene qByte Miner",
            "quaternion_group": QUATERNION_GROUP,
            "lambda_phi": LAMBDA_PHI,
            "gamma_decoherence": GAMMA_DECOHERENCE,
            "phi_iit": PHI_IIT,
            "torsion_lock_deg": self.config.torsion_angle,
            "golden_ratio_R_r": GOLDEN_RATIO,
            "manifold_dimension": MANIFOLD_DIMENSION,
            "scale_cm": self.config.scale_cm,
            "resolution": self.config.resolution,
            "lattice_depth": self.config.lattice_depth,
            "mode": self.config.mode.value,
            "gene_outputs": {k: str(v) for k, v in self.gene_outputs.items()},
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "copyright": "Devin Phillip Davis / Agile Defense Systems LLC",
            "license": "LicenseRef-OSIRIS-Dual-v1.0",
        }

    def _export(self, mesh, vertices: np.ndarray, faces: np.ndarray,
                name: str) -> ManufacturingResult:
        """Export mesh to file with metadata."""
        output_dir = Path("./manufacturing_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata = self._build_metadata()

        fmt = self.config.output_format.lower()
        bbox = np.ptp(vertices, axis=0)

        # Estimate volume (convex hull approximation)
        vol = 0.0
        if HAS_TRIMESH and mesh is not None:
            try:
                vol = float(mesh.volume) if mesh.is_volume else float(mesh.convex_hull.volume)
            except Exception:
                vol = float(np.prod(bbox)) * 0.15  # rough estimate

        model_path = ""

        # --- 3MF export via lib3mf ---
        if fmt in ("3mf", "both") and HAS_LIB3MF:
            path_3mf = str(output_dir / f"{name}.3mf")
            self._export_lib3mf(vertices, faces, metadata, path_3mf)
            model_path = path_3mf

        # --- 3MF via trimesh (fallback) ---
        elif fmt in ("3mf", "both") and HAS_TRIMESH and mesh is not None:
            path_3mf = str(output_dir / f"{name}.3mf")
            mesh.export(path_3mf, file_type='3mf')
            model_path = path_3mf

        # --- STL export ---
        if fmt in ("stl", "both") or (fmt == "3mf" and not model_path):
            path_stl = str(output_dir / f"{name}.stl")
            if HAS_TRIMESH and mesh is not None:
                mesh.export(path_stl, file_type='stl')
            else:
                self._export_stl_raw(vertices, faces, path_stl)
            if not model_path:
                model_path = path_stl

        # Write metadata sidecar
        meta_path = str(output_dir / f"{name}_metadata.json")
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Exported {name} → {model_path}")

        return ManufacturingResult(
            model_path=model_path,
            format=fmt,
            vertices=len(vertices),
            faces=len(faces),
            volume_cm3=vol,
            bounding_box_cm=tuple(bbox.tolist()),
            metadata=metadata,
            gcode_path=None,
        )

    @staticmethod
    def _export_lib3mf(vertices, faces, metadata, filepath):
        """Export using lib3mf with full metadata embedding."""
        wrapper = lib3mf.get_wrapper()
        model = wrapper.CreateModel()

        mesh_obj = model.AddMeshObject()
        mesh_obj.SetName("OSIRIS_Tetrahedral_Lattice")

        # Add vertices
        for v in vertices:
            pos = lib3mf.Position()
            pos.Coordinates[0] = float(v[0])
            pos.Coordinates[1] = float(v[1])
            pos.Coordinates[2] = float(v[2])
            mesh_obj.AddVertex(pos)

        # Add triangles
        for f in faces:
            tri = lib3mf.Triangle()
            tri.Indices[0] = int(f[0])
            tri.Indices[1] = int(f[1])
            tri.Indices[2] = int(f[2])
            mesh_obj.AddTriangle(tri)

        # Embed metadata
        meta = model.GetMetaDataGroup()
        for key, val in metadata.items():
            meta.AddMetaData("osiris", key, str(val), "string", True)

        # Write
        writer = model.QueryWriter("3mf")
        writer.WriteToFile(filepath)

    @staticmethod
    def _export_stl_raw(vertices, faces, filepath):
        """Raw binary STL export without trimesh dependency."""
        import struct
        with open(filepath, 'wb') as f:
            # Header (80 bytes)
            header = b'OSIRIS Manufacturing Pipeline - Tetrahedral Lattice'
            f.write(header.ljust(80, b'\0'))
            # Triangle count
            f.write(struct.pack('<I', len(faces)))
            for face in faces:
                v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
                # Compute face normal
                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)
                norm_len = np.linalg.norm(normal)
                if norm_len > 0:
                    normal = normal / norm_len
                # Write: normal (3 floats), v0 (3), v1 (3), v2 (3), attribute (2 bytes)
                f.write(struct.pack('<3f', *normal))
                f.write(struct.pack('<3f', *v0))
                f.write(struct.pack('<3f', *v1))
                f.write(struct.pack('<3f', *v2))
                f.write(struct.pack('<H', 0))


# ════════════════════════════════════════════════════════════════════════════════
# SLICER INTEGRATION
# ════════════════════════════════════════════════════════════════════════════════

class SlicerPipeline:
    """
    Interfaces with BambuStudio-CLI or PrusaSlicer-console for
    automated G-code generation from 3MF/STL models.
    """

    # Known slicer CLI paths
    SLICER_CANDIDATES = [
        "bambu-studio-cli",
        "BambuStudio",
        "/opt/BambuStudio/bin/bambu-studio-cli",
        "prusa-slicer-console",
        "prusa-slicer",
        "/usr/bin/prusa-slicer",
        "PrusaSlicer",
        "cura-cli",
        "CuraEngine",
    ]

    # Default slicer profiles per printer type
    PRINTER_PROFILES = {
        PrinterType.BAMBU_P1S: {
            "slicer": "bambu-studio-cli",
            "profile": "0.20mm_standard_p1s",
            "material": "PLA",
            "supports": True,
            "infill": 20,
        },
        PrinterType.BAMBU_A1_MINI: {
            "slicer": "bambu-studio-cli",
            "profile": "0.20mm_standard_a1mini",
            "material": "PLA",
            "supports": True,
            "infill": 15,
        },
        PrinterType.ELEGOO_CENTAURI_2: {
            "slicer": "prusa-slicer-console",
            "profile": "0.05mm_resin_detail",
            "material": "RESIN_STANDARD",
            "supports": True,
            "infill": 100,  # Resin = solid
        },
        PrinterType.GENERIC_FDM: {
            "slicer": "prusa-slicer-console",
            "profile": "0.20mm_generic",
            "material": "PLA",
            "supports": True,
            "infill": 20,
        },
        PrinterType.GENERIC_RESIN: {
            "slicer": "prusa-slicer-console",
            "profile": "0.05mm_resin",
            "material": "RESIN_STANDARD",
            "supports": True,
            "infill": 100,
        },
    }

    def __init__(self):
        self.slicer_path = self._find_slicer()

    def _find_slicer(self) -> Optional[str]:
        """Locate an available slicer CLI on the system."""
        for candidate in self.SLICER_CANDIDATES:
            try:
                result = subprocess.run(
                    ["which", candidate],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    logger.info(f"Found slicer: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return None

    def slice_model(self, model_path: str, printer_type: PrinterType,
                    output_dir: Optional[str] = None) -> Optional[str]:
        """
        Slice a 3MF/STL model into G-code for the specified printer.

        Returns path to generated G-code file, or None if slicing fails.
        """
        if not self.slicer_path:
            logger.warning("No slicer CLI found — cannot generate G-code")
            return None

        profile = self.PRINTER_PROFILES.get(printer_type, self.PRINTER_PROFILES[PrinterType.GENERIC_FDM])
        output_dir = output_dir or str(Path(model_path).parent)
        gcode_name = Path(model_path).stem + ".gcode"
        gcode_path = str(Path(output_dir) / gcode_name)

        cmd = [
            self.slicer_path,
            "--slice", model_path,
            "--output", gcode_path,
        ]

        # Add profile parameters based on slicer type
        if "bambu" in self.slicer_path.lower():
            cmd.extend([
                "--printer-profile", profile["profile"],
                "--filament", profile["material"],
            ])
        elif "prusa" in self.slicer_path.lower():
            cmd.extend([
                "--load", profile["profile"],
                "--fill-density", f"{profile['infill']}%",
            ])
            if profile["supports"]:
                cmd.append("--support-material")

        logger.info(f"Slicing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0 and Path(gcode_path).exists():
                logger.info(f"G-code generated: {gcode_path}")
                return gcode_path
            else:
                logger.error(f"Slicer failed: {result.stderr}")
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Slicer error: {e}")
            return None

    def export_to_flash_drive(self, gcode_path: str,
                              mount_point: str = "/media/usb") -> bool:
        """Copy G-code to a mounted flash drive via Sovereign Substrate."""
        if not Path(gcode_path).exists():
            logger.error(f"G-code not found: {gcode_path}")
            return False

        target_dir = Path(mount_point)
        if not target_dir.exists():
            # Try common mount points
            for alt in ["/mnt/usb", "/media", "/run/media"]:
                alt_path = Path(alt)
                if alt_path.exists():
                    # Find first mounted device
                    for child in alt_path.iterdir():
                        if child.is_dir():
                            target_dir = child
                            break

        if not target_dir.exists():
            logger.warning(f"No flash drive found at {mount_point}")
            return False

        import shutil
        dest = target_dir / Path(gcode_path).name
        shutil.copy2(gcode_path, str(dest))
        logger.info(f"G-code copied to flash drive: {dest}")
        return True


# ════════════════════════════════════════════════════════════════════════════════
# DNA FILE PARSER — Read organism gene definitions
# ════════════════════════════════════════════════════════════════════════════════

class OrganismParser:
    """Parse .dna files from /organism/ directory to extract gene parameters."""

    @staticmethod
    def parse_dna_file(filepath: str) -> Dict[str, Any]:
        """Parse a .dna organism file and extract key parameters."""
        data = {
            'meta': {},
            'dna': {},
            'metrics': {},
            'genes': {},
        }

        content = Path(filepath).read_text(errors='ignore')
        current_block = None
        current_gene = None

        for line in content.split('\n'):
            stripped = line.strip().rstrip(',')

            # Block detection
            if stripped.startswith('META {'):
                current_block = 'meta'
            elif stripped.startswith('DNA {'):
                current_block = 'dna'
            elif stripped.startswith('METRICS {'):
                current_block = 'metrics'
            elif stripped.startswith('GENE '):
                gene_name = stripped.split('GENE ')[1].split('{')[0].strip()
                current_gene = gene_name
                current_block = 'gene'
                data['genes'][gene_name] = {}
            elif stripped == '}':
                if current_block == 'gene':
                    current_gene = None
                current_block = None
                continue

            # Key-value parsing
            if ':' in stripped and current_block:
                key, _, val = stripped.partition(':')
                key = key.strip().strip('"')
                val = val.strip().strip('"').rstrip(',')

                # Type coercion
                if val.lower() in ('true', 'false'):
                    val = val.lower() == 'true'
                else:
                    try:
                        val = float(val) if '.' in val or 'e' in val.lower() else int(val)
                    except ValueError:
                        pass

                if current_block == 'gene' and current_gene:
                    data['genes'][current_gene][key] = val
                elif current_block in data:
                    data[current_block][key] = val

        return data

    @staticmethod
    def load_organism(organism_dir: str = "./organism") -> Dict[str, Any]:
        """Load all .dna organisms from the organism directory."""
        org_path = Path(organism_dir)
        organisms = {}
        if org_path.exists():
            for dna_file in org_path.glob("*.dna"):
                organisms[dna_file.stem] = OrganismParser.parse_dna_file(str(dna_file))
        return organisms


# ════════════════════════════════════════════════════════════════════════════════
# MANUFACTURING PIPELINE — Orchestrates full workflow
# ════════════════════════════════════════════════════════════════════════════════

class ManufacturingPipeline:
    """
    End-to-end manufacturing: Gene Interpretation → Mesh → Slice → Export

    Workflow:
      1. Parse organism DNA for structural gene parameters
      2. Generate mesh via GeometricEngine (G0-G11 mapping)
      3. Export to 3MF/STL with ΛΦ/Γ metadata
      4. Optionally slice to G-code via slicer CLI
      5. Optionally copy to flash drive or send to printer
    """

    def __init__(self, organism_dir: str = "./organism"):
        self.organism_dir = organism_dir
        self.organisms = OrganismParser.load_organism(organism_dir)
        self.slicer = SlicerPipeline()
        self.results: List[ManufacturingResult] = []

    def run(self, config: ManufacturingConfig,
            slice_gcode: bool = False,
            export_flash: bool = False,
            flash_mount: str = "/media/usb") -> ManufacturingResult:
        """
        Run the full manufacturing pipeline.

        Args:
            config: Manufacturing configuration
            slice_gcode: Whether to invoke slicer for G-code generation
            export_flash: Whether to copy G-code to flash drive
            flash_mount: Flash drive mount point

        Returns:
            ManufacturingResult with paths and metadata
        """
        logger.info(f"Manufacturing pipeline: mode={config.mode.value}, "
                     f"scale={config.scale_cm}cm, format={config.output_format}")

        # Load organism parameters into config
        if self.organisms:
            primary = next(iter(self.organisms.values()))
            dna = primary.get('dna', {})
            if 'torsion_lock' in dna:
                config.torsion_angle = float(dna['torsion_lock'])

        # Generate mesh
        engine = GeometricEngine(config)
        result = engine.generate()

        # Slice if requested
        if slice_gcode and result.model_path:
            gcode = self.slicer.slice_model(
                result.model_path, config.printer_type
            )
            if gcode:
                result.gcode_path = gcode

        # Flash export
        if export_flash and result.gcode_path:
            self.slicer.export_to_flash_drive(result.gcode_path, flash_mount)

        self.results.append(result)

        logger.info(f"Pipeline complete: {result.vertices} vertices, "
                     f"{result.faces} faces, {result.volume_cm3:.2f} cm³")
        return result

    def summary(self) -> str:
        """Generate manufacturing pipeline summary."""
        lines = [
            "═" * 60,
            "  OSIRIS MANUFACTURING PIPELINE — RESULTS",
            "═" * 60,
            "",
        ]
        for i, r in enumerate(self.results, 1):
            lines.extend([
                f"  Job {i}:",
                f"    Model:   {r.model_path}",
                f"    Format:  {r.format}",
                f"    Verts:   {r.vertices}",
                f"    Faces:   {r.faces}",
                f"    Volume:  {r.volume_cm3:.2f} cm³",
                f"    BBox:    {r.bounding_box_cm}",
                f"    G-code:  {r.gcode_path or 'not generated'}",
                "",
            ])
        lines.append("═" * 60)
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="OSIRIS 3D Manufacturing Pipeline — Gene-to-Mesh-to-Print"
    )
    parser.add_argument("--mode", default="tetrahedral_lattice",
                        choices=[m.value for m in ManufacturingMode],
                        help="Manufacturing mode")
    parser.add_argument("--scale", type=float, default=10.0,
                        help="Output scale in cm (default: 10)")
    parser.add_argument("--resolution", type=int, default=64,
                        help="Mesh resolution (default: 64)")
    parser.add_argument("--format", default="stl", choices=["3mf", "stl", "both"],
                        help="Output format")
    parser.add_argument("--depth", type=int, default=3,
                        help="Lattice subdivision depth")
    parser.add_argument("--slice", action="store_true",
                        help="Invoke slicer for G-code generation")
    parser.add_argument("--printer", default="generic_fdm",
                        choices=[p.value for p in PrinterType],
                        help="Target printer type")
    parser.add_argument("--flash", action="store_true",
                        help="Export G-code to flash drive")
    parser.add_argument("--organism-dir", default="./organism",
                        help="Path to organism DNA files")

    args = parser.parse_args()

    config = ManufacturingConfig(
        mode=ManufacturingMode(args.mode),
        scale_cm=args.scale,
        resolution=args.resolution,
        lattice_depth=args.depth,
        output_format=args.format,
        printer_type=PrinterType(args.printer),
    )

    pipeline = ManufacturingPipeline(organism_dir=args.organism_dir)
    result = pipeline.run(config, slice_gcode=args.slice, export_flash=args.flash)

    print(pipeline.summary())
    print(f"\n✓ Model exported: {result.model_path}")
    if result.gcode_path:
        print(f"✓ G-code: {result.gcode_path}")
