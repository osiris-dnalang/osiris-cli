#!/bin/bash
# OSIRIS Setup Script
# ═══════════════════════════════════════════════════════════════════════════════
# This script sets up OSIRIS as a global command with all dependencies

set -e

OSIRIS_DIR="/workspaces/osiris-cli"
VENV_DIR="${OSIRIS_DIR}/venv"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  OSIRIS Automated Discovery System - Setup                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if in correct directory
if [ ! -f "${OSIRIS_DIR}/osiris_cli.py" ]; then
    echo "❌ Error: Not in OSIRIS directory"
    echo "   Expected: ${OSIRIS_DIR}/osiris_cli.py"
    exit 1
fi

echo "📦 Checking dependencies..."

# Install system dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Installing..."
    sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
fi

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

# Install requirements
echo "📥 Installing Python dependencies..."
if [ -f "${OSIRIS_DIR}/requirements.txt" ]; then
    pip install -r "${OSIRIS_DIR}/requirements.txt"
else
    pip install qiskit qiskit-ibmq qiskit-machine-learning pandas numpy scipy matplotlib rich requests
fi

# Create global command wrapper
echo "🔗 Creating global 'osiris' command..."

WRAPPER_FILE="/usr/local/bin/osiris"

sudo tee "${WRAPPER_FILE}" > /dev/null << 'EOF'
#!/bin/bash
# OSIRIS CLI Wrapper
cd /workspaces/osiris-cli
source venv/bin/activate
exec python3 "$HOME/.local/bin/osiris_launcher.py" "$@"
EOF

sudo chmod +x "${WRAPPER_FILE}"

# Create launcher script
LAUNCHER_FILE="${HOME}/.local/bin/osiris_launcher.py"
mkdir -p "$(dirname "${LAUNCHER_FILE}")"

tee "${LAUNCHER_FILE}" > /dev/null << 'EOF'
#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

osiris_dir = Path("/workspaces/osiris-cli")

# If no args or first arg is a hotkey, start TUI
if len(sys.argv) == 1 or (len(sys.argv) > 1 and len(sys.argv[1]) == 1):
    subprocess.run([sys.executable, str(osiris_dir / "osiris_tui.py")] + sys.argv[1:])
else:
    # Otherwise route to CLI
    subprocess.run([sys.executable, str(osiris_dir / "osiris_cli.py")] + sys.argv[1:])
EOF

chmod +x "${LAUNCHER_FILE}"

# Add bash completion
echo "🎯 Installing bash completion..."

COMPLETION_FILE="/etc/bash_completion.d/osiris"

sudo tee "${COMPLETION_FILE}" > /dev/null << 'EOF'
_osiris_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="run list status publish help --help -h"
    
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}

complete -F _osiris_completion osiris
EOF

sudo chmod +x "${COMPLETION_FILE}"

# Create shell profile entries
echo "🔧 Updating shell profiles..."

for profile in ~/.bashrc ~/.zshrc; do
    if [ -f "$profile" ]; then
        if ! grep -q "OSIRIS_SETUP" "$profile"; then
            cat >> "$profile" << 'EOF'

# OSIRIS Configuration
export OSIRIS_HOME="/workspaces/osiris-cli"
OSIRIS_SETUP=1
EOF
        fi
    fi
done

# Verify installation
echo ""
echo "✓ Verifying installation..."

if [ -f "${WRAPPER_FILE}" ]; then
    echo "  ✓ Global 'osiris' command installed"
fi

if [ -f "${LAUNCHER_FILE}" ]; then
    echo "  ✓ Launcher script installed"
fi

# Test imports
echo ""
echo "✓ Testing Python imports..."
cd "${OSIRIS_DIR}"

python3 -c "from osiris_auto_discovery import AutoDiscoveryPipeline; print('  ✓ osiris_auto_discovery')" 2>/dev/null || echo "  ⚠ osiris_auto_discovery has issues"
python3 -c "from osiris_orchestrator import WorkflowScheduler; print('  ✓ osiris_orchestrator')" 2>/dev/null || echo "  ⚠ osiris_orchestrator has issues"
python3 -c "from osiris_agents import AgentManager; print('  ✓ osiris_agents')" 2>/dev/null || echo "  ⚠ osiris_agents has issues"
python3 -c "from rich.console import Console; print('  ✓ Rich TUI library')" 2>/dev/null || echo "  ⚠ Rich library needs installation"

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ OSIRIS SETUP COMPLETE                                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Quick start:"
echo "  1. Source your shell: source ~/.bashrc  (or ~/.zshrc)"
echo "  2. Start OSIRIS:      osiris"
echo "  3. Use commands:      osiris run          (execute experiments)"
echo "                        osiris list         (show templates)"
echo "                        osiris status       (check progress)"
echo "                        osiris publish      (publish results)"
echo ""
echo "Available hotkeys in TUI:"
echo "  'a' → Analyze     'e' → Execute    'v' → Visualize"
echo "  'o' → Optimize    'd' → Discover   'x' → Explain"
echo "  'p' → Publish     '?' → Help       'q' → Quit"
echo ""
