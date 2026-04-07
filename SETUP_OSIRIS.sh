#!/usr/bin/env bash
# OSIRIS Quick Setup & Token Configuration
# Run this to get OSIRIS working with your IBM Quantum tokens

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          OSIRIS QUANTUM DISCOVERY SYSTEM - SETUP               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "✓ Checking Python environment..."
python3 --version || { echo "✗ Python 3.9+ required"; exit 1; }

# Check for tokens
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            STEP 1: CONFIGURE API TOKENS                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "🔑 IBM Quantum Token:"
if [[ -z "${IBM_QUANTUM_TOKEN}" ]]; then
    echo "   ⚠ NOT SET"
    echo ""
    echo "   To get your token:"
    echo "   1. Go to: https://quantum.ibm.com/settings/tokens"
    echo "   2. Copy your API token"
    echo "   3. Set environment variable:"
    echo ""
    echo "      export IBM_QUANTUM_TOKEN='paste_your_token_here'"
    echo ""
    echo "   Then add to ~/.bashrc or ~/.zshrc to persist:"
    echo "      echo \"export IBM_QUANTUM_TOKEN='your_token'\" >> ~/.bashrc"
    echo ""
    read -p "Do you want to set IBM_QUANTUM_TOKEN now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Paste your IBM Quantum token: " IBM_QUANTUM_TOKEN
        export IBM_QUANTUM_TOKEN
        echo "✓ Token set for this session"
    fi
else
    echo "   ✓ SET"
    TOKEN_SHORT="${IBM_QUANTUM_TOKEN:0:20}...${IBM_QUANTUM_TOKEN: -10}"
    echo "      $TOKEN_SHORT"
fi

echo ""
echo "🔑 Zenodo Token (Optional - for publishing):"
if [[ -z "${ZENODO_TOKEN}" ]]; then
    echo "   ⚠ NOT SET"
    echo ""
    echo "   To get your token:"
    echo "   1. Go to: https://zenodo.org/account/settings/applications/"
    echo "   2. Create a 'Personal access token'"
    echo "   3. Check: 'deposit:write' permission"
    echo "   4. Copy the token"
    echo "   5. Set:"
    echo ""
    echo "      export ZENODO_TOKEN='paste_your_token_here'"
    echo ""
    read -p "Do you want to set ZENODO_TOKEN now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Paste your Zenodo token: " ZENODO_TOKEN
        export ZENODO_TOKEN
        echo "✓ Token set for this session"
    fi
else
    echo "   ✓ SET"
    TOKEN_SHORT="${ZENODO_TOKEN:0:20}...${ZENODO_TOKEN: -10}"
    echo "      $TOKEN_SHORT"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              STEP 2: VERIFY INSTALLATION                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Run status check
python3 /workspaces/osiris-cli/osiris_launcher.py status

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                STEP 3: RUN A TEST BENCHMARK                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "Running quick benchmark (this creates mock data, not real hardware calls yet)..."
echo ""

python3 /workspaces/osiris-cli/osiris_launcher.py benchmark --quick

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                 SETUP COMPLETE ✓                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Launch Chat Interface:"
echo "   python3 /workspaces/osiris-cli/osiris_launcher.py chat"
echo ""
echo "   OR use shell alias:"
echo "   osiris chat"
echo ""
echo "2. Natural language commands:"
echo "   ❯ benchmark ibm_torino with extreme parameters"
echo "   ❯ test all backends at 64 qubits"
echo "   ❯ show status"
echo ""
echo "3. Real Hardware Benchmarking (with token):"
echo "   ❯ benchmark extreme depth with max shots"
echo ""
echo "4. Direct CLI commands:"
echo "   python3 /workspaces/osiris-cli/osiris_launcher.py benchmark      # Full suite"
echo "   python3 /workspaces/osiris-cli/osiris_launcher.py run --campaign week1_foundation"
echo ""
echo "📖 Full documentation: /workspaces/osiris-cli/OSIRIS_CHAT_README.md"
echo ""
