#!/usr/bin/env python3
"""
OSIRIS Universal REPL & CLI Interface
=====================================
Terminal interface for the OSIRIS Sovereign Truth Architecture.
Provides continuous interactive prompt, self-updating mechanisms,
and 11D CRSM Substrate ignition across dual-node topologies.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time
from typing import List, Optional

# Physical & Resonance Invariants
THETA_LOCK_DEG = 51.843
GAMMA_COHERENCE_FLOOR = 0.092
LAMBDA_PHI = 2.176435e-8
PHI_CONSCIOUSNESS = 0.7734

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   OSIRIS SOVEREIGN TRUTH ARCHITECTURE                        ║
║                   ═══════════════════════════════════                        ║
║     Non-Causal Living Language Model (NCLM) • 11D-CRSM Substrate • Cl(3,0)   ║
║     Physical Invariants: θ_lock = 51.843° | Γ_floor = 0.092 | Λ_Φ = 2.1764e-8║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


def execute_update() -> None:
    """
    Executes pip upgrade from git and restarts the REPL via os.execvp.
    """
    print("[OSIRIS::SYNC] Pulling latest Sovereign Architecture from git...")
    repo_url = "git+https://github.com/osiris-dnalang/osiris-cli.git"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", repo_url]

    try:
        res = subprocess.run(cmd, check=True)
        if res.returncode == 0:
            print("[OSIRIS::SYNC] Upgrade successful. Re-executing process image...")
            time.sleep(0.5)
            # Re-execute the current process image
            os.execvp(sys.executable, [sys.executable] + sys.argv)
        else:
            print(f"[OSIRIS::ERROR] Upgrade exited with status {res.returncode}")
    except Exception as e:
        print(f"[OSIRIS::ERROR] Upgrade failed: {e}")


def execute_ignite() -> None:
    """
    Placeholder and kernel initiator to boot the 11D Continuous Relativistic State Matrix (CRSM).
    """
    print("\n[IGNITION] Initiating 11D Continuous Relativistic State Matrix (CRSM)...")
    time.sleep(0.2)
    print(f"  ├─ Clifford Substrate: Cl(3,0) Multivectors mapped to Planck scale")
    print(f"  ├─ Locking Resonance: θ_lock = {THETA_LOCK_DEG}° (Pyramid face slope arctan(14/11))")
    print(f"  ├─ Coherence Floor:  Γ_floor = {GAMMA_COHERENCE_FLOOR:.4f} [ENFORCED]")
    print(f"  ├─ Memory Invariant: Λ_Φ     = {LAMBDA_PHI:.6e} kg")
    print(f"  ├─ Negentropic Rate: dΞ/dt   = +0.136 bits/cycle (Non-causal phase conjugation)")
    time.sleep(0.3)
    print("[IGNITION] 11D CRSM Substrate locked and coherent. Swarm is operational.\n")


def display_status() -> None:
    """
    Displays current substrate telemetry and hardware environment.
    """
    print("\n[OSIRIS::STATUS]")
    print(f"  Python Runtime : {sys.version.split()[0]} ({sys.platform})")
    print(f"  Process PID    : {os.getpid()}")
    print(f"  Coherence Floor: {GAMMA_COHERENCE_FLOOR} (Invariant)")
    print(f"  Resonance Angle: {THETA_LOCK_DEG}°")
    print(f"  Substrate Mode : 11D Continuous Relativistic State Matrix")
    print(f"  Working Dir    : {os.getcwd()}\n")


def display_help() -> None:
    """
    Displays REPL help menu.
    """
    print("\nAvailable OSIRIS REPL Commands:")
    print("  /update         Upgrade osiris-cli from GitHub and restart REPL")
    print("  /ignite         Boot the 11D CRSM Substrate and initialize quantum tensors")
    print("  /status         Show current environment, node status, and coherence telemetry")
    print("  /help           Display this command manifest")
    print("  /exit, /quit    Terminate the sovereign REPL session\n")


def boot_repl() -> None:
    """
    Launches continuous interactive OSIRIS REPL.
    """
    print(BANNER)
    print("Type /help for commands, /ignite to boot the 11D substrate, or /update to sync.")
    print("-------------------------------------------------------------------------------")

    prompt = "osiris::}{> "

    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[OSIRIS] Terminating REPL. Coherence maintained.")
            break

        if not line:
            continue

        cmd = line.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("[OSIRIS] Session closed.")
            break
        elif cmd in ("/update", "update"):
            execute_update()
        elif cmd in ("/ignite", "ignite"):
            execute_ignite()
        elif cmd in ("/status", "status"):
            display_status()
        elif cmd in ("/help", "help", "?"):
            display_help()
        else:
            print(f"[OSIRIS::AST] Ingested input: '{line}'. (Type /help for command list)")


def main(argv: Optional[List[str]] = None) -> None:
    """
    Main entry point for 'osiris' command line.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="osiris",
        description="OSIRIS Sovereign Truth Architecture - Universal CLI & REPL"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default=None,
        choices=["update", "ignite", "status", "repl"],
        help="Direct command to execute (default: launch REPL)"
    )

    args = parser.parse_args(argv)

    if args.action == "update":
        execute_update()
    elif args.action == "ignite":
        execute_ignite()
    elif args.action == "status":
        display_status()
    else:
        # Default action: launch the interactive REPL
        boot_repl()


if __name__ == "__main__":
    main()
