#!/usr/bin/env bash
# OSIRIS Setup Script
# ═══════════════════════════════════════════════════════════════════════════════
# This script sets up OSIRIS as a local command with dependencies and alias support

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${REPO_ROOT}/venv"
LOCAL_BIN="${HOME}/.local/bin"
WRAPPER_FILE="${LOCAL_BIN}/osiris"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  OSIRIS Automated Discovery System - Setup                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Create virtual environment
if [ ! -d "${VENV_DIR}" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "${VENV_DIR}"
fi

# Activate venv
source "${VENV_DIR}/bin/activate"

# Upgrade pip
echo "📥 Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install Python dependencies
echo "📥 Installing Python dependencies..."
if [ -f "${REPO_ROOT}/requirements.txt" ]; then
    pip install -r "${REPO_ROOT}/requirements.txt"
else
    pip install qiskit qiskit-ibm-runtime qiskit-aer numpy scipy matplotlib requests PyYAML
fi

# Create local executable wrapper
echo "🔗 Installing local 'osiris' command into ${LOCAL_BIN}..."
mkdir -p "${LOCAL_BIN}"
cat > "${WRAPPER_FILE}" << 'EOF'
#!/usr/bin/env bash
REPO_ROOT="${REPO_ROOT}"
cd "${REPO_ROOT}"
exec "${REPO_ROOT}/venv/bin/python3" "${REPO_ROOT}/osiris_launcher.py" "$@"
EOF
chmod +x "${WRAPPER_FILE}"

# Add ~/.local/bin to shell profile if needed
echo "🔧 Updating shell profiles..."
for profile in ~/.bashrc ~/.zshrc; do
    if [ -f "$profile" ]; then
        if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$profile"; then
            cat >> "$profile" << 'EOF'

# OSIRIS local command path
export PATH="$HOME/.local/bin:$PATH"
EOF
        fi
        if ! grep -q 'export OSIRIS_HOME="${REPO_ROOT}"' "$profile"; then
            cat >> "$profile" << 'EOF'

# OSIRIS environment
export OSIRIS_HOME="${REPO_ROOT}"
EOF
        fi
    fi
done

# Compile Cython extension (optional, for IP protection)
echo "🔧 Attempting Cython compilation..."
if python3 -c "import Cython" 2>/dev/null; then
    if [ -f "${REPO_ROOT}/setup_cython.py" ]; then
        cd "${REPO_ROOT}"
        python3 setup_cython.py build_ext --inplace 2>/dev/null && \
            echo "  ✓ Cython torsion core compiled" || \
            echo "  ⚠ Cython build failed — using pure-Python fallback"
    fi
else
    echo "  ⚠ Cython not installed — using pure-Python torsion core"
fi

# Create discovery output directory
mkdir -p "${REPO_ROOT}/discoveries"
mkdir -p "${REPO_ROOT}/papers"

echo ""
echo "✓ Verifying OSIRIS installation..."
if [ -f "${WRAPPER_FILE}" ]; then
    echo "  ✓ Local 'osiris' command installed at: ${WRAPPER_FILE}"
fi

echo ""
echo "✓ Testing Python imports..."
cd "${REPO_ROOT}"
python3 -c "from osiris_auto_discovery import AutoDiscoveryPipeline; print('  ✓ osiris_auto_discovery')" 2>/dev/null || echo "  ⚠ osiris_auto_discovery import failed"
python3 -c "from osiris_orchestrator import WorkflowScheduler; print('  ✓ osiris_orchestrator')" 2>/dev/null || echo "  ⚠ osiris_orchestrator import failed"
python3 -c "from osiris_launcher import main; print('  ✓ osiris_launcher')" 2>/dev/null || echo "  ⚠ osiris_launcher import failed"
python3 -c "from osiris_physics_bridges import BridgeExecutor; print('  ✓ osiris_physics_bridges')" 2>/dev/null || echo "  ⚠ osiris_physics_bridges import failed"
python3 -c "from osiris_ncllm_swarm import NCLLMSwarm; print('  ✓ osiris_ncllm_swarm')" 2>/dev/null || echo "  ⚠ osiris_ncllm_swarm import failed"
python3 -c "from osiris_forge import OsirisForge; print('  ✓ osiris_forge')" 2>/dev/null || echo "  ⚠ osiris_forge import failed"
python3 -c "from rich.console import Console; print('  ✓ Rich library')" 2>/dev/null || echo "  ⚠ rich import failed"

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ OSIRIS SETUP COMPLETE                                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Reload shell: source ~/.bashrc or source ~/.zshrc"
echo "  2. Run OSIRIS with: osiris status"
echo "  3. Run an experiment: osiris run --campaign week1_foundation"
echo "  4. Launch interactive chat: osiris chat"
echo ""
echo "Helpful commands:" 
  echo "  - osiris status"
  echo "  - osiris benchmark --quick"
  echo "  - osiris bridges --output bridges.json"
  echo "  - osiris swarm --task 'optimize torsion solver'"
  echo "  - osiris forge pipeline --printer elegoo_cc2 --ip 192.168.1.X"
  echo "  - osiris forge multicolor --design shannon_map"
  echo "  - osiris publish --mode all --sandbox"
  echo "  - osiris intent --text 'run a benchmark'"

echo ""
