#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
PY_INC=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")
NUMPY_INC=$(python3 -c "import numpy; print(numpy.get_include())")

echo "Compiling C-SIMD AVX2 kernels..."
echo "Python include: $PY_INC"
echo "NumPy include: $NUMPY_INC"

gcc -O3 -mavx2 -mfma -shared -fPIC \
    -I"${PY_INC}" \
    -I"${NUMPY_INC}" \
    c_simd_ops.c -o _c_simd.so

echo "Compilation successful: $(ls -lh _c_simd.so)"
