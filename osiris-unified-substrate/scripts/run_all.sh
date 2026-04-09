#!/bin/bash
set -e

OBJECTIVE="${1:-Build a reasoning-focused NCLM system}"
ITERATIONS="${2:-2}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "========================================"
echo " OSIRIS FULL PIPELINE"
echo "========================================"
echo ""
echo "Objective: $OBJECTIVE"
echo ""

# Step 1: Stack planning
echo "[1/4] Stack refinement..."
python osiris_cli.py stack "$OBJECTIVE" --iterations "$ITERATIONS" --save
echo ""

# Step 2: Data generation (if data dir exists)
if [ -d "data" ] && [ -f "data/dataset.jsonl" ]; then
    echo "[2/4] Dataset found at data/dataset.jsonl"
else
    echo "[2/4] Generating seed dataset..."
    python -m nclm.production.data.autogen --output data/dataset.jsonl --count 50 2>/dev/null || \
        echo "  (auto-gen not available — create data/dataset.jsonl manually)"
fi
echo ""

# Step 3: Training (optional — skip if no GPU / no model)
if python -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo "[3/4] GPU detected. Ready for training."
    echo "  To train:  python -m nclm.production.training --config configs/train.yaml"
    echo "  To align:  python -m nclm.production.rlhf     --config configs/rlhf.yaml"
else
    echo "[3/4] No GPU — skipping training. Use --load-in-4bit for CPU."
fi
echo ""

# Step 4: Evaluation
echo "[4/4] Running evaluation harness..."
python -m nclm.production.eval --tasks mmlu gsm8k humaneval --max-samples 50 2>/dev/null || \
    echo "  (evaluation requires 'datasets' package — pip install datasets)"

echo ""
echo "========================================"
echo " PIPELINE COMPLETE"
echo "========================================"
