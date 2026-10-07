#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# OSIRIS — Ollama Setup Script
# Installs Ollama and pulls a lightweight model for the NCLLM swarm
# ═══════════════════════════════════════════════════════════════════════════
set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  OSIRIS :: Ollama Language Engine Setup              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo

# Step 1: Install Ollama
if command -v ollama &>/dev/null; then
    echo "✓ Ollama already installed: $(ollama --version 2>/dev/null || echo 'unknown')"
else
    echo "⚛ Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
fi
echo

# Step 2: Start Ollama server (if not running)
if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Ollama server already running"
else
    echo "⚛ Starting Ollama server..."
    ollama serve &>/dev/null &
    sleep 3
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✓ Ollama server started"
    else
        echo "⚠ Could not start Ollama server. Try: ollama serve"
    fi
fi
echo

# Step 3: Pull a model — try smallest first for fast startup
MODELS=("smollm2:360m" "qwen2.5:0.5b" "qwen2.5:1.5b" "tinyllama" "phi3:mini")
PULLED=""
for model in "${MODELS[@]}"; do
    echo "⚛ Pulling $model..."
    if ollama pull "$model" 2>/dev/null; then
        echo "✓ Model ready: $model"
        PULLED="$model"
        break
    else
        echo "⚠ Failed to pull $model, trying next..."
    fi
done
echo

if [ -n "$PULLED" ]; then
    echo "════════════════════════════════════════════════════════"
    echo "  Setup complete! Model: $PULLED"
    echo "  Run OSIRIS:  ./osiris"
    echo "  Quick test:  ollama run $PULLED 'Hello'"
    echo "════════════════════════════════════════════════════════"
else
    echo "⚠ No models pulled. Check your internet connection."
    echo "  Manual install:  ollama pull smollm2:360m"
fi
