#!/bin/bash
# Start NCLM-1 workflow: OSIRIS + monitoring

set -e

cd /root/osiris-cli

# Set environment
: "${OSIRIS_PG_URL:?set OSIRIS_PG_URL in your shell first}"
export OSIRIS_QUANTUM_BACKEND=aer

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║        🚀 NCLM-1 EXPLORATORY EVALUATION WORKFLOW                   ║"
echo "║                                                                    ║"
echo "║     Memory Engine + Quantum Discovery + Real-time Monitoring       ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Verify environment
echo "[1/4] Verifying environment..."
if ! command -v osiris &> /dev/null; then
    echo "❌ osiris CLI not found"
    exit 1
fi

if [ -z "$OSIRIS_PG_URL" ]; then
    echo "❌ OSIRIS_PG_URL not set"
    exit 1
fi

echo "✅ Environment ready"
echo ""

# Start monitoring in background
echo "[2/4] Starting monitoring pipeline..."
python3 nclm_analysis.py --watch &
MONITOR_PID=$!
echo "✅ Monitor running (PID: $MONITOR_PID)"
echo ""

# Wait a moment
sleep 2

# Start OSIRIS
echo "[3/4] Starting OSIRIS console..."
echo "⏳ Memory engine initializing..."
echo ""

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  OSIRIS CONSOLE READY                                              ║"
echo "║                                                                    ║"
echo "║  Type research questions about quantum computing.                  ║"
echo "║  Memory automatically embeds, retrieves, and tracks metrics.       ║"
echo "║                                                                    ║"
echo "║  Example prompts:                                                  ║"
echo "║    • How does staggered XY4 improve coherence?                    ║"
echo "║    • Implement Bell state preparation                              ║"
echo "║    • Compare DD sequences on near-term hardware                    ║"
echo "║    • Analyze quantum error correction limits                       ║"
echo "║                                                                    ║"
echo "║  To exit: /exit or Ctrl+D                                          ║"
echo "║  Monitoring updates every 30s in background                        ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Launch OSIRIS (foreground, so user can interact)
osiris

# Clean up monitor when OSIRIS exits
echo ""
echo "[4/4] Cleaning up..."
kill $MONITOR_PID 2>/dev/null || true
wait $MONITOR_PID 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ SESSION ENDED                                                   ║"
echo "║                                                                    ║"
echo "║  To view final results:                                            ║"
echo "║    python3 nclm_analysis.py --report --csv nclm_evaluation.csv    ║"
echo "║                                                                    ║"
echo "║  To continue monitoring:                                           ║"
echo "║    python3 nclm_analysis.py --watch                                ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
