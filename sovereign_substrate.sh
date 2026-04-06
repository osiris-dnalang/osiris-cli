#!/bin/bash

# Sovereign Substrate Management Script
# Consolidates repositories, neutralizes URLs, removes .git metadata

set -e

WORKSPACE_DIR="/workspaces/osiris-cli"
UNIFIED_DIR="$WORKSPACE_DIR/osiris-unified-substrate"

# Function to perform sparse-shallow clone
sovereign_clone() {
    local repo_url=$1
    local target_dir=$2

    echo "Cloning $repo_url to $target_dir with depth 1..."
    git clone --depth 1 "$repo_url" "$target_dir"
    echo "Removing .git from $target_dir..."
    rm -rf "$target_dir/.git"
}

# Create unified directory
mkdir -p "$UNIFIED_DIR"

# Clone ENKI-420 and quantum-advantage (if they exist)
sovereign_clone "https://github.com/ENKI-420" "$WORKSPACE_DIR/enki-420-temp" 2>/dev/null || echo "ENKI-420 not found, skipping."
sovereign_clone "https://github.com/quantum-advantage" "$WORKSPACE_DIR/quantum-advantage-temp" 2>/dev/null || echo "quantum-advantage not found, skipping."

# Consolidate into unified substrate
echo "Consolidating repositories into $UNIFIED_DIR..."
cp -r "$WORKSPACE_DIR/enki-420-temp/"* "$UNIFIED_DIR/" 2>/dev/null || true
cp -r "$WORKSPACE_DIR/quantum-advantage-temp/"* "$UNIFIED_DIR/" 2>/dev/null || true
cp -r "$WORKSPACE_DIR/d-wave-main/"* "$UNIFIED_DIR/" 2>/dev/null || true

# Clean up temp dirs
rm -rf "$WORKSPACE_DIR/enki-420-temp" "$WORKSPACE_DIR/quantum-advantage-temp"

# Neutralize external URLs and IPs
echo "Neutralizing external URLs and IPs..."
find "$UNIFIED_DIR" -type f \( -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "*.json" \) -exec sed -i 's|https\?://[^[:space:]]*|localhost/PURIFIED|g' {} \;
find "$UNIFIED_DIR" -type f \( -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "*.json" \) -exec sed -i 's|[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+|127.0.0.1/PURIFIED|g' {} \;

echo "Sovereign Substrate consolidated and neutralized."