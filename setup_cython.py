#!/usr/bin/env python3
"""
Build script for OSIRIS Cython-protected modules.

Usage:
    python setup_cython.py build_ext --inplace

This compiles osiris_torsion_core.pyx into a binary shared object (.so / .pyd)
that protects the torsion mechanics methodology from trivial reverse-engineering.

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False
    print("WARNING: Cython not installed. Install with: pip install cython")
    print("Falling back to pure Python module (unprotected).")

if USE_CYTHON:
    extensions = cythonize(
        [
            Extension(
                "osiris_torsion_core",
                sources=["osiris_torsion_core.pyx"],
            ),
        ],
        compiler_directives={
            'language_level': '3',
            'boundscheck': False,
            'wraparound': False,
        },
    )
else:
    extensions = []

setup(
    name='osiris-torsion-core',
    version='2.0.0',
    description='OSIRIS Torsion Mechanics Core (Cython-protected)',
    author='Devin Phillip Davis',
    author_email='licensing@agiledefensesystems.com',
    ext_modules=extensions,
    python_requires='>=3.9',
    install_requires=[
        'cython>=0.29',
    ],
)
