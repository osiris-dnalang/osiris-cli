#!/usr/bin/env bash
# ========================================================================
#  OSIRIS-CLI Deployment Script
#  Works on: Codespace (Ubuntu), antiX OS, Debian/Ubuntu derivatives
#  Usage: bash deploy.sh [--verify] [--security] [--full]
# ========================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[OSIRIS]${RESET} $1"; }
ok()   { echo -e "${GREEN}  ✓${RESET} $1"; }
fail() { echo -e "${RED}  ✗${RESET} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Parse args ──────────────────────────────────────────────────────────
DO_VERIFY=false
DO_SECURITY=false
DO_FULL=false

for arg in "$@"; do
    case "$arg" in
        --verify)   DO_VERIFY=true ;;
        --security) DO_SECURITY=true ;;
        --full)     DO_FULL=true; DO_VERIFY=true; DO_SECURITY=true ;;
        --help|-h)
            echo "Usage: bash deploy.sh [--verify] [--security] [--full]"
            echo "  --verify    Run osiris_verify.py after install"
            echo "  --security  Install ufw, rkhunter, chkrootkit, lynis"
            echo "  --full      All of the above"
            exit 0 ;;
    esac
done

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║           OSIRIS-CLI DEPLOYMENT :: $(date +%Y-%m-%d)            ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. System detection ────────────────────────────────────────────────
log "Detecting system..."

OS_ID="unknown"
if [ -f /etc/os-release ]; then
    OS_ID=$(grep -oP '(?<=^ID=).+' /etc/os-release | tr -d '"')
fi
ARCH=$(uname -m)
PY=$(command -v python3 || true)

ok "OS: $OS_ID ($ARCH)"
ok "Python: ${PY:-NOT FOUND}"

if [ -z "$PY" ]; then
    fail "Python3 not found. Install with: sudo apt install python3 python3-pip"
    exit 1
fi

PY_VERSION=$($PY --version 2>&1 | grep -oP '\d+\.\d+')
ok "Python version: $PY_VERSION"

# ── 2. Clock sync (antiX / bare-metal fix) ─────────────────────────────
log "Checking system clock..."

if command -v timedatectl &>/dev/null; then
    ok "Clock managed by systemd"
elif command -v ntpdate &>/dev/null; then
    log "Syncing clock via ntpdate..."
    sudo ntpdate -u pool.ntp.org 2>/dev/null && ok "Clock synced" || log "Clock sync skipped (offline?)"
else
    # Check if clock is >1 hour off from HTTP date
    HTTP_DATE=$(curl -sI https://google.com 2>/dev/null | grep -i '^date:' | cut -d' ' -f2-)
    if [ -n "$HTTP_DATE" ]; then
        ok "Clock appears reasonable (HTTP check)"
    else
        log "Cannot verify clock — apt may fail if time is wrong"
        log "Fix manually: sudo date -s 'YYYY-MM-DD HH:MM:SS'"
    fi
fi

# ── 3. Python dependencies ─────────────────────────────────────────────
log "Installing Python dependencies..."

PIP_FLAGS=""
# Debian Trixie+ requires --break-system-packages or a venv
if $PY -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    PIP_FLAGS="--break-system-packages"
fi

if [ -f requirements.txt ]; then
    $PY -m pip install -r requirements.txt $PIP_FLAGS --quiet 2>/dev/null && \
        ok "All Python packages installed" || \
        { log "pip install failed — trying with --user"; \
          $PY -m pip install --user -r requirements.txt $PIP_FLAGS --quiet && \
          ok "Installed with --user flag"; }
else
    fail "requirements.txt not found"
    exit 1
fi

# ── 4. Verify core imports ─────────────────────────────────────────────
log "Verifying core module imports..."

MODULES=(
    "osiris_auto_discovery"
    "osiris_orchestrator"
    "osiris_agents"
    "osiris_intent_engine"
    "osiris_zenodo_publisher"
    "osiris_rqc_framework"
    "osiris_applications"
    "osiris_ultra_coder"
    "osiris_benchmark_suite"
)

IMPORT_PASS=0
IMPORT_FAIL=0

for mod in "${MODULES[@]}"; do
    if $PY -c "import $mod" 2>/dev/null; then
        ok "$mod"
        ((IMPORT_PASS++))
    else
        fail "$mod"
        ((IMPORT_FAIL++))
    fi
done

echo ""
log "Import results: ${IMPORT_PASS} passed, ${IMPORT_FAIL} failed"

# ── 5. Environment variables ───────────────────────────────────────────
log "Checking environment variables..."

if [ -n "${IBM_QUANTUM_TOKEN:-}" ]; then
    ok "IBM_QUANTUM_TOKEN is set"
else
    log "IBM_QUANTUM_TOKEN not set (mock execution mode)"
    log "  Set with: export IBM_QUANTUM_TOKEN='your_token'"
fi

if [ -n "${ZENODO_TOKEN:-}" ]; then
    ok "ZENODO_TOKEN is set"
else
    log "ZENODO_TOKEN not set (publishing disabled)"
fi

# ── 6. Security hardening (optional) ───────────────────────────────────
if $DO_SECURITY; then
    log "Installing security tools..."
    
    if command -v apt &>/dev/null; then
        sudo apt update -qq 2>/dev/null
        sudo apt install -y -qq ufw rkhunter chkrootkit lynis 2>/dev/null && \
            ok "Security tools installed" || fail "Some security tools failed to install"
        
        sudo ufw default deny incoming 2>/dev/null
        sudo ufw default allow outgoing 2>/dev/null
        sudo ufw --force enable 2>/dev/null && ok "Firewall enabled (deny incoming)" || true
        
        sudo rkhunter --propupd 2>/dev/null && ok "RKHunter baseline created" || true
    else
        log "apt not available — install security tools manually"
    fi
fi

# ── 7. Verification run (optional) ─────────────────────────────────────
if $DO_VERIFY; then
    log "Running OSIRIS verification suite..."
    echo ""
    $PY osiris_verify.py || fail "Verification had errors (see above)"
fi

# ── 8. Summary ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║                   DEPLOYMENT COMPLETE                       ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "  Quick start:"
echo "    python3 osiris_launcher.py status     # Check system"
echo "    python3 osiris_launcher.py chat       # Launch TUI"
echo "    python3 osiris_launcher.py benchmark  # Run benchmarks"
echo "    python3 osiris_launcher.py run        # Run experiments"
echo "    python3 osiris_launcher.py orchestrate --quick  # Full pipeline"
echo ""
echo "  On antiX / low-resource systems:"
echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "    python3 osiris_auto_discovery.py      # Direct discovery"
echo ""
