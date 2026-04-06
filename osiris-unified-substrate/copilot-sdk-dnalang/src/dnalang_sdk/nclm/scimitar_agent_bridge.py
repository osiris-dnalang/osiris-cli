"""
OSIRIS Scimitar Elite Wireless SE — Agent Feedback Bridge.

Maps swarm agent states to Corsair Scimitar Elite RGB LED zones.
12 side buttons + scroll wheel + logo + DPI indicators provide a
real-time haptic+visual feedback channel for OSIRIS orchestration.

State → Color protocol:
  ● Green   (0, 255, 0)      — nominal / swarm idle / task complete OK
  ● Blue    (0, 150, 255)    — task active / agent running
  ● Yellow  (255, 200, 0)    — warning / retry / threshold near
  ● Red     (255, 0, 0)      — CRITICAL STOP / syntax fail / kill switch
  ● Purple  (150, 0, 255)    — GA evolution in progress
  ● Teal    (0, 255, 200)    — apprentice learning / synthesis
  ● Cyan    (0, 255, 255)    — AURA (code agent)
  ● Orange  (255, 100, 0)    — AIDEN (security agent)
  ● Magenta (200, 0, 255)    — OMEGA (quantum agent)
  ● Gold    (255, 180, 0)    — CHRONOS (temporal agent)

Button → Role mapping (side buttons 1–12):
  1  complete    — fill stubs / finish implementations
  2  test        — write pytest coverage
  3  document    — add/improve docstrings
  4  harden      — add validation + error handling
  5  integrate   — wire into package
  6  learn       — apprentice synthesis / flush corpus
  7  force       — force-queue a role
  8  status      — swarm status
  9  evolve      — trigger GA evolution step
  10 freeze      — freeze strategy genome
  11 kill        — kill switch (emergency stop)
  12 sync        — dual-drive backup sync

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Tuple

try:
    import hid  # pip install hidapi
    _HID_AVAILABLE = True
except ImportError:
    _HID_AVAILABLE = False

# ── Hardware constants ──────────────────────────────────────────────────────

CORSAIR_VID  = 0x1B1C
SCIMITAR_PID = 0x1B8B

# ── Zone / button constants ─────────────────────────────────────────────────

# Zone IDs (0xFF = broadcast to all zones)
ZONE_ALL    = 0xFF
ZONE_LOGO   = 0x00
ZONE_SCROLL = 0x01
ZONE_DPI    = 0x02

# Side button zone IDs (1-indexed, matching physical labels)
BUTTON_ZONES = {i: i for i in range(1, 13)}

# Physical constants (CODES / CRSM)
_LAMBDA_PHI = 2.176435e-8
_THETA_LOCK = 51.843

# ── Color palette ───────────────────────────────────────────────────────────

COLORS = {
    "nominal":   (0,   255,   0),    # green
    "active":    (0,   150, 255),    # blue
    "warning":   (255, 200,   0),    # yellow
    "critical":  (255,   0,   0),    # red
    "evolving":  (150,   0, 255),    # purple
    "learning":  (0,   255, 200),    # teal
    "idle":      (20,   20,  20),    # near-black (dim)
    "off":       (0,     0,   0),    # off
    # Agent colors
    "AURA":      (0,   255, 255),    # cyan
    "AIDEN":     (255, 100,   0),    # orange
    "OMEGA":     (200,   0, 255),    # magenta
    "CHRONOS":   (255, 180,   0),    # gold
    "OSIRIS":    (0,   200, 255),    # sky blue
}

# ── Button → swarm role mapping ─────────────────────────────────────────────

AGENT_BUTTON_MAP: dict[str, int] = {
    "complete":  1,
    "test":      2,
    "document":  3,
    "harden":    4,
    "integrate": 5,
    "learn":     6,
    "force":     7,
    "status":    8,
    "evolve":    9,
    "freeze":   10,
    "kill":     11,
    "sync":     12,
}
BUTTON_ROLE_MAP: dict[int, str] = {v: k for k, v in AGENT_BUTTON_MAP.items()}

# Role → accent color (shown when role is active)
ROLE_COLORS: dict[str, str] = {
    "complete":  "active",
    "test":      "AURA",
    "document":  "learning",
    "harden":    "AIDEN",
    "integrate": "OSIRIS",
    "learn":     "learning",
    "force":     "warning",
    "status":    "nominal",
    "evolve":    "evolving",
    "freeze":    "CHRONOS",
    "kill":      "critical",
    "sync":      "OMEGA",
}


# ══════════════════════════════════════════════════════════════════════════════
# ██  SCIMITAR AGENT BRIDGE                                                  ██
# ══════════════════════════════════════════════════════════════════════════════

class ScimitarAgentBridge:
    """
    Real-time OSIRIS orchestration feedback via Corsair Scimitar Elite SE.

    Thread-safe. If HID device is not available (no hardware or no driver),
    all methods silently no-op — OSIRIS still functions without the mouse.
    """

    def __init__(self):
        self.device = None
        self._lock = threading.Lock()
        self._state = "nominal"
        self._button_states: dict[int, str] = {i: "idle" for i in range(1, 13)}
        self._connect()

    def _connect(self) -> bool:
        """Attempt to open the HID device. Returns True if connected."""
        if not _HID_AVAILABLE:
            return False
        try:
            dev = hid.device()
            dev.open(CORSAIR_VID, SCIMITAR_PID)
            dev.set_nonblocking(True)
            self.device = dev
            self.signal_swarm_state("nominal")
            return True
        except Exception:
            self.device = None
            return False

    @property
    def connected(self) -> bool:
        return self.device is not None

    # ── Low-level primitives ────────────────────────────────────────────────

    def _send(self, zone: int, r: int, g: int, b: int):
        """Send a single RGB payload to one zone. Never raises."""
        if not self.device:
            return
        payload = [0x00, 0x07, zone, r, g, b] + [0x00] * 58
        try:
            self.device.write(payload)
        except OSError:
            self.device = None  # lost connection

    def _color(self, name_or_rgb) -> Tuple[int, int, int]:
        """Resolve a color name or (r,g,b) tuple."""
        if isinstance(name_or_rgb, tuple):
            return name_or_rgb
        return COLORS.get(name_or_rgb, COLORS["idle"])

    # ── Zone state broadcasts ───────────────────────────────────────────────

    def signal_swarm_state(self, state: str):
        """
        Broadcast swarm health state to all zones.

        state: "nominal" | "active" | "warning" | "critical" |
               "evolving" | "learning"
        """
        self._state = state
        r, g, b = self._color(state)
        with self._lock:
            self._send(ZONE_ALL, r, g, b)

    def signal_all_green(self):
        """All zones green: everything nominal."""
        self.signal_swarm_state("nominal")

    def signal_critical_stop(self):
        """
        Emergency stop: rapid red flash across all zones.
        Blocks for ~1.5s of visual alarm, then holds red.
        """
        self._state = "critical"
        r, g, b = self._color("critical")
        def _flash():
            with self._lock:
                for _ in range(5):
                    self._send(ZONE_ALL, r, g, b)
                    time.sleep(0.12)
                    self._send(ZONE_ALL, 0, 0, 0)
                    time.sleep(0.12)
                self._send(ZONE_ALL, r, g, b)  # hold red
        threading.Thread(target=_flash, daemon=True).start()

    def signal_evolution(self, generation: int = 0):
        """
        Purple pulse: GA evolution running.
        Scrollwheel pulses, numbered buttons ripple.
        """
        self._state = "evolving"
        pr, pg, pb = self._color("evolving")
        def _pulse():
            with self._lock:
                self._send(ZONE_SCROLL, pr, pg, pb)
                for btn in range(1, 10):
                    self._send(BUTTON_ZONES[btn], pr, pg, pb)
                    time.sleep(0.05)
                time.sleep(0.8)
                self._send(ZONE_SCROLL, 0, 0, 0)
                for btn in range(1, 10):
                    nr, ng, nb = self._color("idle")
                    self._send(BUTTON_ZONES[btn], nr, ng, nb)
        threading.Thread(target=_pulse, daemon=True).start()

    def signal_learning(self):
        """Teal sweep: apprentice synthesis in progress."""
        self._state = "learning"
        r, g, b = self._color("learning")
        def _sweep():
            with self._lock:
                for btn in [6, 3, 2, 7]:  # learn, document, test, force
                    self._send(BUTTON_ZONES[btn], r, g, b)
                    time.sleep(0.1)
                time.sleep(0.8)
                for btn in [6, 3, 2, 7]:
                    ir, ig, ib = self._color("idle")
                    self._send(BUTTON_ZONES[btn], ir, ig, ib)
        threading.Thread(target=_sweep, daemon=True).start()

    # ── Role-level signals ──────────────────────────────────────────────────

    def signal_role_active(self, role: str):
        """
        Light up the button for an active role while it runs.
        Also dims all other role buttons to indicate single-focus.
        """
        btn = AGENT_BUTTON_MAP.get(role)
        if btn is None:
            return
        color_name = ROLE_COLORS.get(role, "active")
        r, g, b = self._color(color_name)
        self._button_states[btn] = "active"
        with self._lock:
            # Dim all other role buttons
            for b_id in range(1, 13):
                if b_id != btn:
                    ir, ig, ib = self._color("idle")
                    self._send(BUTTON_ZONES[b_id], ir, ig, ib)
            # Light active button
            self._send(BUTTON_ZONES[btn], r, g, b)

    def signal_role_complete(self, role: str, success: bool):
        """
        Flash green (success) or red (failure) on the role's button,
        then return to idle. Updates swarm state indicator.
        """
        btn = AGENT_BUTTON_MAP.get(role)
        if btn is None:
            return
        self._button_states[btn] = "done" if success else "failed"
        flash_color = self._color("nominal" if success else "critical")
        fr, fg, fb = flash_color
        ir, ig, ib = self._color("idle")

        def _blink():
            with self._lock:
                for _ in range(3):
                    self._send(BUTTON_ZONES[btn], fr, fg, fb)
                    time.sleep(0.15)
                    self._send(BUTTON_ZONES[btn], ir, ig, ib)
                    time.sleep(0.15)
                # Hold dim green/red for 1s
                self._send(BUTTON_ZONES[btn], fr // 3, fg // 3, fb // 3)
                time.sleep(1.0)
                self._send(BUTTON_ZONES[btn], ir, ig, ib)
        threading.Thread(target=_blink, daemon=True).start()

        # If all tasks done → signal full green
        if success and not self._has_active_tasks():
            self.signal_all_green()

    def _has_active_tasks(self) -> bool:
        return any(v == "active" for v in self._button_states.values())

    # ── Agent identity signals ──────────────────────────────────────────────

    def phase_agent_directive(self, agent_name: str, target_button: int):
        """
        Signal a sovereign agent directive on a specific button.
        AURA = cyan pulse, AIDEN = orange, OMEGA = magenta, CHRONOS = gold.
        """
        color_name = agent_name if agent_name in COLORS else "OSIRIS"
        r, g, b = self._color(color_name)

        def _pulse():
            with self._lock:
                self._send(ZONE_ALL, 0, 0, 0)  # clear
                for _ in range(5):
                    self._send(BUTTON_ZONES.get(target_button, ZONE_ALL), r, g, b)
                    time.sleep(0.3)
                    self._send(BUTTON_ZONES.get(target_button, ZONE_ALL), 0, 0, 0)
                    time.sleep(0.3)
                self._send(BUTTON_ZONES.get(target_button, ZONE_ALL), r, g, b)
        threading.Thread(target=_pulse, daemon=True).start()

    # ── User input wait ─────────────────────────────────────────────────────

    def await_biological_input(self, target_button: int, timeout: float = 10.0) -> bool:
        """
        Wait for user to press the specified side button.
        Returns True if pressed within timeout, False otherwise.
        """
        if not self.device:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                data = self.device.read(64)
                if data and len(data) > 4 and data[4] == target_button:
                    self.signal_all_green()
                    return True
            except Exception:
                break
            time.sleep(0.01)
        self.signal_all_green()
        return False

    # ── Fdna health indicator ───────────────────────────────────────────────

    def signal_fdna_health(self, fdna: float):
        """
        Map Fdna score to LED health state on logo zone.

        Fdna > 0.6  → green  (nominal coherence)
        0.3–0.6     → yellow (degraded)
        < 0.3       → red    (critical decoherence)
        """
        if fdna > 0.6:
            self._send(ZONE_LOGO, *self._color("nominal"))
        elif fdna > 0.3:
            self._send(ZONE_LOGO, *self._color("warning"))
        else:
            self._send(ZONE_LOGO, *self._color("critical"))

    def refresh_dod_buttons(self, dod_scores: dict[str, float]):
        """
        Update side buttons 1–5 with DoD gradient colors.
        Maps role to DoD completion score:
          green (≥0.8), yellow (0.5-0.8), red (<0.5)
        """
        role_order = ["complete", "test", "document", "harden", "integrate"]
        with self._lock:
            for i, role in enumerate(role_order, start=1):
                score = dod_scores.get(role, 0.5)
                if score >= 0.8:
                    r, g, b = self._color("nominal")
                elif score >= 0.5:
                    r, g, b = self._color("warning")
                else:
                    r, g, b = self._color("critical")
                # Dim to 30% so it's ambient, not blinding
                self._send(BUTTON_ZONES[i], r // 3, g // 3, b // 3)


# ══════════════════════════════════════════════════════════════════════════════
# ██  SINGLETON                                                               ██
# ══════════════════════════════════════════════════════════════════════════════

_bridge: Optional[ScimitarAgentBridge] = None
_bridge_lock = threading.Lock()


def get_bridge() -> ScimitarAgentBridge:
    """Get the singleton ScimitarAgentBridge (lazy init, never raises)."""
    global _bridge
    with _bridge_lock:
        if _bridge is None:
            _bridge = ScimitarAgentBridge()
    return _bridge
