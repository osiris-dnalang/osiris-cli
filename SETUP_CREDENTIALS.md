# OSIRIS Setup Guide - Credentials & Configuration

**How to get your API tokens and configure the system.**

---

## IBM Quantum Token

### Get Your Token

1. Visit https://quantum.ibm.com/
2. Sign in (create account if needed - **free tier available**)
3. Click your profile icon (top right)
4. Select "Settings"
5. Scroll to "Account"
6. Copy your "API Token"

### Set in Environment

**Option A: Temporary (current session only)**
```bash
export IBM_QUANTUM_TOKEN="your_copied_token_here"
```

**Option B: Permanent (add to ~/.bashrc or ~/.zshrc)**
```bash
# Add line to ~/.bashrc
echo 'export IBM_QUANTUM_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Option C: In Python (for scripts)**
```python
import os
os.environ['IBM_QUANTUM_TOKEN'] = 'your_token_here'
```

### Verify
```bash
echo $IBM_QUANTUM_TOKEN
# Should output your token (not empty)
```

---

## Zenodo Token (Optional - for Publishing)

### Get Your Token

1. Visit https://zenodo.org/
2. Sign in (create account if needed - **free tier**)
3. Click your profile (top right)
4. Select "Settings"
5. Click "Applications"
6. "Create new token"
7. Check all scopes: `deposit:write`
8. Click "Create"
9. Copy the token

### Set in Environment

```bash
export ZENODO_TOKEN="your_zenodo_token_here"
```

### Verify
```bash
echo $ZENODO_TOKEN
# Should output your token
```

---

## Backend Selection (Optional)

Choose which IBM Quantum processor to use.

Available backends (as of April 2026):
- `ibm_torino` (133 qubits) - Recommended default
- `ibm_fez` (156 qubits)
- `ibm_nazca` (156 qubits)
- `ibm_brisbane` (127 qubits)

### Set Backend
```bash
export IBM_BACKEND="ibm_torino"
```

### Change Backend Mid-Campaign
Either:
1. Edit in `osiris_cli.py` --backend flag
2. Modify experiment config JSON

---

## Complete Setup Example

### ~/.bashrc or ~/.zshrc
```bash
# OSIRIS Quantum Discovery Configuration

# IBM Quantum
export IBM_QUANTUM_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export IBM_BACKEND="ibm_torino"

# Zenodo (for publishing)
export ZENODO_TOKEN="zpCOe-ABC1234xyz..."

# Python path (if needed)
export PYTHONPATH="/workspaces/osiris-cli:$PYTHONPATH"
```

Then:
```bash
source ~/.bashrc
python osiris_cli.py run --campaign week1_foundation
```

---

## Verify All Tokens

```bash
#!/bin/bash
echo "IBM Token: $([ -n '$IBM_QUANTUM_TOKEN' ] && echo 'SET' || echo 'NOT SET')"
echo "Zenodo Token: $([ -n '$ZENODO_TOKEN' ] && echo 'SET' || echo 'NOT SET')"
echo "Backend: $IBM_BACKEND"
```

Run:
```bash
bash verify_setup.sh
```

---

## Using Mock Execution (Testing)

If you don't have IBM Quantum token:

```bash
# Set to 'mock' explicitly
export IBM_QUANTUM_TOKEN="mock"

# Run - will use synthetic data
python osiris_cli.py run --campaign week1_foundation
```

Mock execution is **perfect for:**
- Testing workflows
- Debugging code
- Learning system
- Validating logic

---

## Sandbox Publishing (Testing)

First-time publishing? Test on Zenodo sandbox:

```python
# In your publishing code
workflow = PublishingWorkflow(
    zenodo_token,
    use_sandbox=True  # <-- Test first!
)
```

Sandbox URL: https://sandbox.zenodo.org/

---

## Troubleshooting

### "Unknown token format"
- Copy token exactly (no leading/trailing spaces)
- Verify you used IBM Quantum, not IBM Cloud

### "Connection refused"
- Check internet connection
- Token may have expired (get new one)

### "Zenodo permission denied"
- Check token has `deposit:write` scope
- Got token from https://zenodo.org/ NOT ibm.com

### "Using mock execution"
- IBM_QUANTUM_TOKEN not set or invalid
- This is fine for testing!

---

## Security Notes

### Do NOT
- ❌ Commit tokens to git
- ❌ Share tokens with others
- ❌ Post tokens in public forums
- ❌ Use same token in multiple machines

### Do
- ✅ Store in environment variables
- ✅ Use ~/.bashrc (local machine only)
- ✅ Rotate tokens periodically
- ✅ Use separate tokens per machine

### If Compromised
- Immediately revoke token in settings
- Generate new token
- Update environment

---

## Multi-User Setup

If sharing a machine:

**Option 1: Separate accounts**
- Each user has own IBM/Zenodo account
- Each sets own tokens

**Option 2: Shared credentials (less secure)**
```bash
# Create .env file
cat > .envrc << 'EOF'
export IBM_QUANTUM_TOKEN="shared_token"
export ZENODO_TOKEN="shared_token"
EOF

# Use direnv or source manually
direnv allow
# or
source .envrc
```

---

## Production Deployment

For servers/CI/CD:

**Option 1: Environment variables (recommended)**
```bash
# In CI/CD secrets (GitHub Actions, GitLab CI, etc.)
export IBM_QUANTUM_TOKEN=***
export ZENODO_TOKEN=***
```

**Option 2: Config file (less secure)**
```bash
# Create secure config
cat > /etc/osiris/config.env << 'EOF'
IBM_QUANTUM_TOKEN="..."
ZENODO_TOKEN="..."
EOF

# Load in script
source /etc/osiris/config.env
```

**Option 3: Service account**
```python
# Use IBM Quantum service account for automation
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService.load_account(
    channel="ibm_quantum",
    token="service_account_token"
)
```

---

## Quick Verification Script

Save as `verify_setup.sh`:

```bash
#!/bin/bash

echo "═══════════════════════════════════════"
echo "OSIRIS Configuration Verification"
echo "═══════════════════════════════════════"
echo ""

# Check tokens
[ -n "$IBM_QUANTUM_TOKEN" ] && IBM_OK="✓" || IBM_OK="✗"
[ -n "$ZENODO_TOKEN" ] && ZENODO_OK="✓" || ZENODO_OK="✗"

echo "$IBM_OK IBM Quantum Token: ${IBM_QUANTUM_TOKEN:0:20}..."
echo "$ZENODO_OK Zenodo Token: ${ZENODO_TOKEN:0:20}..."
echo "   Backend: ${IBM_BACKEND:-ibm_torino (default)}"
echo ""

# Check Python
echo "→ Python environment:"
python3 --version
python3 -c "import qiskit; print(f'  ✓ Qiskit {qiskit.__version__}')" 2>/dev/null || echo "  ✗ Qiskit not installed"

echo ""
echo "═══════════════════════════════════════"

if [ -z "$IBM_QUANTUM_TOKEN" ]; then
    echo "⚠  Set IBM_QUANTUM_TOKEN to begin"
    exit 1
fi

echo "✓ Ready to run OSIRIS"
exit 0
```

Run:
```bash
bash verify_setup.sh
```

---

## Next Step

Once configured:
```bash
python osiris_cli.py list
python osiris_cli.py run --campaign week1_foundation
```

You're ready to discover!
