#!/bin/bash
set -e

OUTPUT="${1:-data/dataset.jsonl}"
COUNT="${2:-100}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "Generating $COUNT samples → $OUTPUT"
python -m nclm.production.data.autogen --output "$OUTPUT" --count "$COUNT"
echo "Done."
