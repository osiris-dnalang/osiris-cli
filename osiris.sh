#!/usr/bin/env bash
# OSIRIS — NCLLM-Powered Interactive Shell
# Just type: ./osiris
# If you pass subcommands (e.g. ./osiris benchmark), routes to launcher.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"

# Ensure PYTHONPATH includes current directory
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# If arguments provided, use the traditional launcher for backwards compat
if [[ $# -gt 0 ]]; then
    exec "$PY" "${SCRIPT_DIR}/osiris_launcher.py" "$@"
fi

# No arguments = launch interactive NCLLM shell
exec "$PY" "${SCRIPT_DIR}/osiris_shell.py"
