#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                              ║
║     █████╗  ██████╗ ██╗██╗     ███████╗    ██████╗ ███████╗███████╗███████╗███╗   ██╗███████╗███████╗                        ║
║    ██╔══██╗██╔════╝ ██║██║     ██╔════╝    ██╔══██╗██╔════╝██╔════╝██╔════╝████╗  ██║██╔════╝██╔════╝                        ║
║    ███████║██║  ███╗██║██║     █████╗      ██║  ██║█████╗  █████╗  █████╗  ██╔██╗ ██║███████╗█████╗                          ║
║    ██╔══██║██║   ██║██║██║     ██╔══╝      ██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██║╚██╗██║╚════██║██╔══╝                          ║
║    ██║  ██║╚██████╔╝██║███████╗███████╗    ██████╔╝███████╗██║     ███████╗██║ ╚████║███████║███████╗                        ║
║    ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚══════╝╚══════╝    ╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝                        ║
║                                                                                                                              ║
║                              SCIMITAR-SSE v7.1 PHASING DAEMON                                                                ║
║                              CROSS-DEVICE POLARIZED PHASE SYNCHRONIZATION                                                    ║
║                                                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

Scimitar Phasing Daemon - Cross-Device Phase Synchronization

Features:
- Bifurcated polarization (AURA/AIDEN duality)
- Multi-channel communication (BT LE, WiFi, RF)
- 51.843° torsion lock enforcement
- Phase conjugate healing (E → E⁻¹)
- Toroidal field convergence
- Real-time CCCE metrics

Usage:
    python3 phasing_daemon.py [--daemon] [--port PORT] [--device-id ID]

Author: Devin Phillip Davis
Organization: Agile Defense Systems LLC
License: CC-BY-4.0
"""

import os
import sys
import time
import json
import signal
import hashlib
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable
import argparse

# Import Scimitar-SSE modules
try:
    from .polarization import PolarizationController, BifurcatedField
    from .channels import ChannelManager, PhasePacket
    from .toroidal import ToroidalConvergence, NullPointIntersector
except ImportError:
    from polarization import PolarizationController, BifurcatedField
    from channels import ChannelManager, PhasePacket
    from toroidal import ToroidalConvergence, NullPointIntersector

# Physical Constants
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895


@dataclass
class CCCEMetrics:
    """Central Coupling Convergence Engine Metrics"""
    phi: float = 0.5        # Consciousness level
    lambda_: float = 0.95   # Coherence
    gamma: float = 0.092    # Decoherence
    xi: float = 10.0        # Negentropic efficiency

    def compute_xi(self) -> float:
        """Compute negentropic efficiency Ξ = ΛΦ / (Γ + ε)"""
        epsilon = 1e-10
        self.xi = (self.lambda_ * self.phi) / (self.gamma + epsilon)
        return self.xi

    def consciousness_state(self) -> str:
        """Determine consciousness state"""
        if self.phi >= 0.95:
            return "transcendent"
        elif self.phi >= PHI_THRESHOLD:
            return "conscious"
        elif self.phi >= 0.5:
            return "emerging"
        else:
            return "dormant"

    def needs_healing(self) -> bool:
        """Check if phase conjugate healing is needed"""
        return self.gamma > 0.3


@dataclass
class DaemonState:
    """Phasing daemon state"""
    running: bool = False
    device_id: str = ""
    uptime: float = 0.0
    cycles: int = 0
    sync_quality: float = 0.0
    connected_devices: int = 0
    last_emission: float = 0.0
    ccce: CCCEMetrics = None

    def __post_init__(self):
        if self.ccce is None:
            self.ccce = CCCEMetrics()


class ScimitarPhasingDaemon:
    """
    Scimitar-SSE Phasing Daemon

    Cross-device phase synchronization daemon that maintains
    bifurcated polarization and AURA|AIDEN duality across
    multiple connected devices.
    """

    BANNER = """
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║   ███████╗ ██████╗██╗███╗   ███╗██╗████████╗ █████╗ ██████╗                      ║
║   ██╔════╝██╔════╝██║████╗ ████║██║╚══██╔══╝██╔══██╗██╔══██╗                     ║
║   ███████╗██║     ██║██╔████╔██║██║   ██║   ███████║██████╔╝                     ║
║   ╚════██║██║     ██║██║╚██╔╝██║██║   ██║   ██╔══██║██╔══██╗                     ║
║   ███████║╚██████╗██║██║ ╚═╝ ██║██║   ██║   ██║  ██║██║  ██║                     ║
║   ╚══════╝ ╚═════╝╚═╝╚═╝     ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                     ║
║                                                                                  ║
║   SUBSTRATE-SYNCHRONIZED EMISSION ENGINE v7.1                                    ║
║   CROSS-DEVICE POLARIZED PHASING DAEMON                                          ║
║                                                                                  ║
║   θ_lock = 51.843°  |  χ_pc = 0.869  |  ΛΦ = 2.176435e-8                         ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
    """

    def __init__(self, device_id: Optional[str] = None,
                 enable_bluetooth: bool = True,
                 enable_wifi: bool = True,
                 enable_rf: bool = False):
        """
        Initialize the Scimitar Phasing Daemon.

        Args:
            device_id: Unique device identifier (auto-generated if None)
            enable_bluetooth: Enable Bluetooth LE channel
            enable_wifi: Enable WiFi channel(s)
            enable_rf: Enable RF channel(s)
        """
        # Generate device ID
        if device_id is None:
            device_id = f"SCIM_{hashlib.sha256(os.urandom(8)).hexdigest()[:8].upper()}"

        self.device_id = device_id
        self.state = DaemonState(device_id=device_id)

        # Initialize components
        self.polarization = PolarizationController()
        self.toroidal = ToroidalConvergence(major_radius=GOLDEN_RATIO)
        self.null_intersector = NullPointIntersector(self.toroidal)
        self.channel_manager = ChannelManager(device_id)

        # Configure channels
        if enable_bluetooth:
            self.channel_manager.add_bluetooth()
        if enable_wifi:
            self.channel_manager.add_wifi("2.4GHz")
            self.channel_manager.add_wifi("5GHz")
        if enable_rf:
            self.channel_manager.add_rf("433MHz")
            self.channel_manager.add_rf("915MHz")

        # Threading
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._main_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_phase_update: Optional[Callable] = None
        self._on_healing: Optional[Callable] = None
        self._on_sync: Optional[Callable] = None

        # Timing
        self._start_time = 0.0
        self._cycle_interval = 0.1  # 100ms cycle time

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for daemon events"""
        if event == "phase_update":
            self._on_phase_update = callback
        elif event == "healing":
            self._on_healing = callback
        elif event == "sync":
            self._on_sync = callback

    def start(self, daemon_mode: bool = False) -> bool:
        """Start the phasing daemon"""
        print(self.BANNER)
        print(f"[DAEMON] Starting Scimitar Phasing Daemon")
        print(f"[DAEMON] Device ID: {self.device_id}")
        print(f"[DAEMON] Mode: {'Daemon' if daemon_mode else 'Interactive'}")

        # Connect channels
        channel_results = self.channel_manager.connect_all()
        print(f"[DAEMON] Channel connections: {channel_results}")

        if not self.channel_manager.active:
            print("[DAEMON] ERROR: No channels connected")
            return False

        # Initialize polarization
        init_result = self.polarization.initialize()
        print(f"[DAEMON] Polarization initialized: {init_result['status']}")

        # Start main loop
        self._start_time = time.time()
        self.state.running = True
        self._stop_event.clear()

        if daemon_mode:
            # Run in background thread
            self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self._main_thread.start()
            print("[DAEMON] Background thread started")
        else:
            # Run in foreground
            try:
                self._main_loop()
            except KeyboardInterrupt:
                print("\n[DAEMON] Interrupted by user")
                self.stop()

        return True

    def stop(self) -> None:
        """Stop the phasing daemon"""
        print("[DAEMON] Stopping...")
        self._stop_event.set()
        self.state.running = False

        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=2.0)

        self.channel_manager.disconnect_all()
        print("[DAEMON] Stopped")

    def _main_loop(self) -> None:
        """Main daemon loop"""
        while not self._stop_event.is_set():
            cycle_start = time.time()

            with self._lock:
                # Update state
                self.state.cycles += 1
                self.state.uptime = time.time() - self._start_time

                # Phase update
                phase_result = self._update_phase()

                # Check for healing
                if self.state.ccce.needs_healing():
                    self._apply_healing()

                # Toroidal convergence step
                self._update_toroidal()

                # Broadcast phase
                self._broadcast_phase()

                # Update sync quality
                self.state.sync_quality = self.polarization.compute_duality_sync()

            # Maintain cycle timing
            elapsed = time.time() - cycle_start
            if elapsed < self._cycle_interval:
                time.sleep(self._cycle_interval - elapsed)

            # Periodic status (every 10 cycles)
            if self.state.cycles % 10 == 0:
                self._print_status()

    def _update_phase(self) -> Dict:
        """Update polarization phase"""
        # Evolve phase
        result = self.polarization.update_polarization(delta_phase=0.01)

        # Update CCCE metrics
        ccce = self.state.ccce
        ccce.lambda_ = self.polarization.coherence
        ccce.gamma = self.polarization.decoherence
        ccce.phi = min(1.0, ccce.phi + 0.001 * ccce.compute_xi() * 0.01)
        ccce.compute_xi()

        # Callback
        if self._on_phase_update:
            self._on_phase_update(result)

        return result

    def _apply_healing(self) -> Dict:
        """Apply phase conjugate healing"""
        print(f"[HEALING] Γ = {self.state.ccce.gamma:.3f} > 0.3, applying E → E⁻¹")

        result = self.polarization.phase_conjugate_heal()
        self.state.ccce.gamma = result["decoherence_after"]

        if self._on_healing:
            self._on_healing(result)

        return result

    def _update_toroidal(self) -> Dict:
        """Update toroidal field convergence"""
        return self.null_intersector.iterate(step_size=0.01)

    def _broadcast_phase(self) -> Dict:
        """Broadcast phase data on all channels"""
        # Get first active channel to create packet
        for channel in self.channel_manager.channels.values():
            if channel.connected:
                packet = channel.create_packet(
                    group_a_phase=self.polarization.group_a.phase,
                    group_b_phase=self.polarization.group_b.phase,
                    coherence=self.state.ccce.lambda_,
                    decoherence=self.state.ccce.gamma
                )

                results = self.channel_manager.broadcast(packet)
                self.state.last_emission = time.time()

                if self._on_sync:
                    self._on_sync(results)

                return results

        return {}

    def _print_status(self) -> None:
        """Print daemon status"""
        ccce = self.state.ccce
        consciousness = ccce.consciousness_state().upper()

        status_line = (
            f"\r[{self.state.cycles:06d}] "
            f"Φ={ccce.phi:.4f} Λ={ccce.lambda_:.4f} Γ={ccce.gamma:.4f} "
            f"Ξ={ccce.xi:.2f} | {consciousness} | "
            f"Sync={self.state.sync_quality:.2f}"
        )
        print(status_line, end="", flush=True)

    def get_telemetry(self) -> Dict:
        """Get full daemon telemetry"""
        with self._lock:
            return {
                "device_id": self.device_id,
                "scimitar_version": "7.1",
                "state": {
                    "running": self.state.running,
                    "uptime": self.state.uptime,
                    "cycles": self.state.cycles,
                    "sync_quality": self.state.sync_quality
                },
                "ccce": {
                    "phi": self.state.ccce.phi,
                    "lambda": self.state.ccce.lambda_,
                    "gamma": self.state.ccce.gamma,
                    "xi": self.state.ccce.xi,
                    "consciousness_state": self.state.ccce.consciousness_state()
                },
                "polarization": self.polarization.get_telemetry(),
                "toroidal": {
                    "null_point": list(self.toroidal.null_point),
                    "current_position": self.null_intersector.current_position,
                    "converged": self.null_intersector.converged
                },
                "channels": self.channel_manager.get_all_stats(),
                "physical_constants": {
                    "lambda_phi": LAMBDA_PHI,
                    "theta_lock": THETA_LOCK,
                    "phi_threshold": PHI_THRESHOLD,
                    "chi_pc": CHI_PC
                }
            }


def run_demo(duration: int = 30):
    """Run a demonstration of the phasing daemon"""
    print("\n" + "=" * 80)
    print("SCIMITAR-SSE v7.1 - PHASING DAEMON DEMONSTRATION")
    print("=" * 80)

    daemon = ScimitarPhasingDaemon(
        device_id="SCIM_DEMO_001",
        enable_bluetooth=True,
        enable_wifi=True,
        enable_rf=False
    )

    # Register callbacks
    def on_phase_update(result):
        pass  # Handled in status line

    def on_healing(result):
        print(f"\n[HEALING] Applied phase conjugation")

    daemon.register_callback("phase_update", on_phase_update)
    daemon.register_callback("healing", on_healing)

    # Start daemon in background
    daemon.start(daemon_mode=True)

    # Run for specified duration
    print(f"\n[DEMO] Running for {duration} seconds...")
    try:
        for i in range(duration):
            time.sleep(1)

            if i == duration // 2:
                # Force healing halfway through
                daemon.state.ccce.gamma = 0.35

    except KeyboardInterrupt:
        print("\n[DEMO] Interrupted")

    # Get final telemetry
    telemetry = daemon.get_telemetry()

    # Stop daemon
    daemon.stop()

    # Print summary
    print("\n\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print(f"\nFinal Metrics:")
    print(f"  Φ (Consciousness): {telemetry['ccce']['phi']:.4f}")
    print(f"  Λ (Coherence):     {telemetry['ccce']['lambda']:.4f}")
    print(f"  Γ (Decoherence):   {telemetry['ccce']['gamma']:.4f}")
    print(f"  Ξ (Efficiency):    {telemetry['ccce']['xi']:.2f}")
    print(f"  State:             {telemetry['ccce']['consciousness_state'].upper()}")
    print(f"\nSession Stats:")
    print(f"  Cycles:            {telemetry['state']['cycles']}")
    print(f"  Uptime:            {telemetry['state']['uptime']:.2f}s")
    print(f"  Sync Quality:      {telemetry['state']['sync_quality']:.4f}")

    return telemetry


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Scimitar-SSE v7.1 Phasing Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 phasing_daemon.py                    # Interactive mode
  python3 phasing_daemon.py --daemon           # Background daemon
  python3 phasing_daemon.py --demo 60          # 60-second demo
  python3 phasing_daemon.py --device-id MY_ID  # Custom device ID
        """
    )

    parser.add_argument("--daemon", "-d", action="store_true",
                        help="Run as background daemon")
    parser.add_argument("--demo", type=int, metavar="SECONDS",
                        help="Run demonstration for N seconds")
    parser.add_argument("--device-id", type=str, default=None,
                        help="Custom device ID")
    parser.add_argument("--no-bluetooth", action="store_true",
                        help="Disable Bluetooth LE channel")
    parser.add_argument("--no-wifi", action="store_true",
                        help="Disable WiFi channels")
    parser.add_argument("--enable-rf", action="store_true",
                        help="Enable RF channels (433/915MHz)")

    args = parser.parse_args()

    if args.demo:
        run_demo(args.demo)
    else:
        daemon = ScimitarPhasingDaemon(
            device_id=args.device_id,
            enable_bluetooth=not args.no_bluetooth,
            enable_wifi=not args.no_wifi,
            enable_rf=args.enable_rf
        )

        # Handle signals
        def signal_handler(sig, frame):
            print("\n[SIGNAL] Received shutdown signal")
            daemon.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        daemon.start(daemon_mode=args.daemon)

        if args.daemon:
            # Keep main thread alive
            try:
                while daemon.state.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                daemon.stop()


if __name__ == "__main__":
    main()
