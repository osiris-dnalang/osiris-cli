#!/usr/bin/env python3
"""
OSIRIS Tridirectional Feedback Bus
=====================================

The nervous system of the NCLLM swarm. Three axes of information
flow simultaneously, creating a self-reinforcing intelligence loop:

    ┌─────────────┐    telemetry     ┌─────────────┐
    │   NCLLM     │ ──────────────→ │   Intent    │
    │   Swarm     │                 │   Engine    │
    │             │ ←────────────── │             │
    └──────┬──────┘   context       └──────┬──────┘
           │                               │
           │  diagnostics                  │  routing
           ▼                               ▼
    ┌─────────────────────────────────────────────┐
    │              TUI / CLI Surface              │
    │  (displays live swarm intelligence state)   │
    └─────────────────────────────────────────────┘

Bus message types:
  TELEMETRY  — swarm → intent: quality, introspection, capability map
  CONTEXT    — intent → swarm: user context, routing confidence, history
  DIAGNOSTIC — swarm → TUI: alerts, forecasts, blind spots, health
  ROUTING    — intent → TUI: suggested actions, confidence visualization

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import time
import json
import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger("OSIRIS_FEEDBACK_BUS")


class MessageType(Enum):
    """Categories of feedback bus messages."""
    TELEMETRY = "telemetry"      # swarm → intent
    CONTEXT = "context"          # intent → swarm
    DIAGNOSTIC = "diagnostic"    # swarm → TUI
    ROUTING = "routing"          # intent → TUI
    ALERT = "alert"              # any → any
    IMPROVEMENT = "improvement"  # introspection → mesh
    PRINTER_TELEMETRY = "printer_telemetry"  # printer → swarm + TUI


@dataclass
class BusMessage:
    """A single message on the feedback bus."""
    msg_type: MessageType
    source: str                  # "swarm", "intent", "tui", "introspection"
    target: str                  # "swarm", "intent", "tui", "all"
    payload: Dict[str, Any]
    priority: float = 0.5        # 0-1, higher = more urgent
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return d


class FeedbackBus:
    """
    Central message bus connecting the three axes:
      Axis 1: NCLLM Swarm (intelligence engine)
      Axis 2: Intent Engine (routing & confidence)
      Axis 3: TUI/CLI (user-facing surface)

    Supports synchronous pub/sub with priority queuing.
    """

    def __init__(self, max_history: int = 200):
        self._subscribers: Dict[str, List[Callable]] = {
            "swarm": [],
            "intent": [],
            "tui": [],
            "all": [],
        }
        self._message_history: deque = deque(maxlen=max_history)
        self._message_count = 0

        # Accumulated state snapshots from each axis
        self._swarm_state: Dict[str, Any] = {}
        self._intent_state: Dict[str, Any] = {}
        self._tui_state: Dict[str, Any] = {}

    def subscribe(self, target: str,
                  callback: Callable[[BusMessage], None]):
        """Register a callback for messages targeting a specific axis."""
        if target not in self._subscribers:
            self._subscribers[target] = []
        self._subscribers[target].append(callback)

    def publish(self, message: BusMessage):
        """Publish a message to the bus."""
        self._message_count += 1
        self._message_history.append(message)

        # Update accumulated state
        if message.source == "swarm":
            self._swarm_state.update(message.payload)
        elif message.source == "intent":
            self._intent_state.update(message.payload)
        elif message.source == "tui":
            self._tui_state.update(message.payload)

        # Deliver to target subscribers
        for cb in self._subscribers.get(message.target, []):
            try:
                cb(message)
            except Exception as e:
                logger.error("Feedback bus delivery error: %s", e)

        # Also deliver to "all" subscribers
        if message.target != "all":
            for cb in self._subscribers.get("all", []):
                try:
                    cb(message)
                except Exception as e:
                    logger.error("Feedback bus broadcast error: %s", e)

    # ═══════════════════════════════════════════════════════════════════════
    # CONVENIENCE PUBLISHERS
    # ═══════════════════════════════════════════════════════════════════════

    def emit_swarm_telemetry(self, quality: float,
                              introspection_data: Dict[str, Any],
                              mesh_data: Dict[str, Any]):
        """
        Swarm → Intent + TUI: publish execution results and introspection.
        """
        payload = {
            "quality": quality,
            "introspection": introspection_data,
            "mesh": mesh_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # To intent engine (for adaptive confidence)
        self.publish(BusMessage(
            msg_type=MessageType.TELEMETRY,
            source="swarm",
            target="intent",
            payload=payload,
            priority=0.7,
        ))
        # To TUI (for live dashboard)
        self.publish(BusMessage(
            msg_type=MessageType.DIAGNOSTIC,
            source="swarm",
            target="tui",
            payload=payload,
            priority=0.5,
        ))

    def emit_intent_routing(self, intent_type: str, confidence: float,
                             suggested_actions: List[str],
                             capability_context: Dict[str, Any]):
        """
        Intent → Swarm + TUI: publish routing decisions and context.
        """
        payload = {
            "intent_type": intent_type,
            "confidence": confidence,
            "actions": suggested_actions,
            "capability_context": capability_context,
        }
        # To swarm (inject intent context into deliberation)
        self.publish(BusMessage(
            msg_type=MessageType.CONTEXT,
            source="intent",
            target="swarm",
            payload=payload,
            priority=0.6,
        ))
        # To TUI (show routing decision)
        self.publish(BusMessage(
            msg_type=MessageType.ROUTING,
            source="intent",
            target="tui",
            payload=payload,
            priority=0.4,
        ))

    def emit_alert(self, source: str, message: str,
                   severity: float = 0.5, details: Dict = None):
        """
        Any → All: publish an alert.
        """
        self.publish(BusMessage(
            msg_type=MessageType.ALERT,
            source=source,
            target="all",
            payload={
                "message": message,
                "severity": severity,
                "details": details or {},
            },
            priority=severity,
        ))

    def emit_improvement(self, actions: List[Dict[str, Any]]):
        """
        Introspection → Mesh: publish improvement actions.
        """
        self.publish(BusMessage(
            msg_type=MessageType.IMPROVEMENT,
            source="introspection",
            target="swarm",
            payload={"actions": actions},
            priority=0.8,
        ))

    def emit_printer_telemetry(self, printer_id: str,
                                status: Dict[str, Any],
                                print_progress: Optional[float] = None):
        """
        Printer → Swarm + TUI: publish real-time printer telemetry.
        Feeds nozzle temp, bed temp, print state, layer progress
        into the swarm for deliberation context and TUI for dashboard.
        """
        payload = {
            "printer_id": printer_id,
            "printer_status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if print_progress is not None:
            payload["print_progress"] = print_progress

        # To swarm (inject printer context into deliberation)
        self.publish(BusMessage(
            msg_type=MessageType.PRINTER_TELEMETRY,
            source="printer",
            target="swarm",
            payload=payload,
            priority=0.6,
        ))
        # To TUI (live printer dashboard)
        self.publish(BusMessage(
            msg_type=MessageType.PRINTER_TELEMETRY,
            source="printer",
            target="tui",
            payload=payload,
            priority=0.5,
        ))

        # Auto-alert on temperature anomalies
        nozzle_t = status.get("nozzle_temp", 0)
        bed_t = status.get("bed_temp", 0)
        state = status.get("state", "")

        if isinstance(nozzle_t, (int, float)) and nozzle_t > 280:
            self.emit_alert("printer", f"Nozzle over-temp: {nozzle_t}°C on {printer_id}",
                           severity=0.9, details=status)
        if isinstance(bed_t, (int, float)) and bed_t > 120:
            self.emit_alert("printer", f"Bed over-temp: {bed_t}°C on {printer_id}",
                           severity=0.8, details=status)
        if state in ("error", "failed", "fault"):
            self.emit_alert("printer", f"Printer fault on {printer_id}: {state}",
                           severity=0.95, details=status)

    # ═══════════════════════════════════════════════════════════════════════
    # STATE QUERIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_swarm_state(self) -> Dict[str, Any]:
        """Latest accumulated swarm state."""
        return dict(self._swarm_state)

    def get_intent_state(self) -> Dict[str, Any]:
        """Latest accumulated intent state."""
        return dict(self._intent_state)

    def get_unified_state(self) -> Dict[str, Any]:
        """Combined state from all three axes."""
        return {
            "swarm": dict(self._swarm_state),
            "intent": dict(self._intent_state),
            "tui": dict(self._tui_state),
            "bus_stats": {
                "total_messages": self._message_count,
                "history_size": len(self._message_history),
            },
        }

    def recent_messages(self, n: int = 20,
                        msg_type: Optional[MessageType] = None
                        ) -> List[Dict]:
        """Get recent messages, optionally filtered by type."""
        messages = list(self._message_history)
        if msg_type:
            messages = [m for m in messages if m.msg_type == msg_type]
        return [m.to_dict() for m in messages[-n:]]

    def recent_alerts(self, n: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return self.recent_messages(n, MessageType.ALERT)

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════

    def print_status(self):
        """Print feedback bus status."""
        print(f"\n{'═' * 72}")
        print("  OSIRIS FEEDBACK BUS — Tridirectional Intelligence Relay")
        print(f"{'═' * 72}")
        print(f"  Messages relayed: {self._message_count}")

        # Message type breakdown
        type_counts: Dict[str, int] = {}
        for msg in self._message_history:
            t = msg.msg_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items()):
            bar = "█" * min(c, 30)
            print(f"    {t:15s} {bar} ({c})")

        # Swarm state summary
        if self._swarm_state:
            quality = self._swarm_state.get("quality", "?")
            print(f"\n  Swarm state: quality={quality}")

        # Intent state summary
        if self._intent_state:
            intent = self._intent_state.get("intent_type", "?")
            conf = self._intent_state.get("confidence", "?")
            print(f"  Intent state: type={intent}, confidence={conf}")

        # Recent alerts
        alerts = [m for m in self._message_history
                  if m.msg_type == MessageType.ALERT]
        if alerts:
            print(f"\n  Recent alerts ({len(alerts)}):")
            for a in list(alerts)[-3:]:
                sev = a.payload.get("severity", 0)
                icon = "🔴" if sev > 0.7 else "🟡" if sev > 0.4 else "🟢"
                print(f"    {icon} [{a.source}] {a.payload.get('message', '?')}")

        print(f"{'═' * 72}")


# ════════════════════════════════════════════════════════════════════════════════
# PRINTER TELEMETRY RELAY — Bridge from Forge to Feedback Bus
# ════════════════════════════════════════════════════════════════════════════════

class PrinterTelemetryRelay:
    """
    Bridges real-time printer status from OsirisForge bridges (Bambu MQTT,
    Moonraker HTTP, Elegoo) into the Feedback Bus, enabling the NCLLM Swarm
    to reason about physical manufacturing state during deliberation.

    Usage:
        bus = FeedbackBus()
        relay = PrinterTelemetryRelay(bus)
        relay.poll_printer("bambu_p1s", ip="192.168.1.100", serial="01S...", access_code="...")
        relay.poll_printer("moonraker", ip="192.168.1.200")
    """

    def __init__(self, bus: FeedbackBus):
        self.bus = bus
        self._printer_states: Dict[str, Dict[str, Any]] = {}

    def poll_printer(self, printer_type: str, ip: str,
                     serial: str = "", access_code: str = "",
                     port: int = 0) -> Dict[str, Any]:
        """
        Query a printer's current status and relay it to the feedback bus.
        Returns the raw status dict.

        printer_type: 'bambu_p1s', 'moonraker', 'elegoo_centauri_2'
        """
        status = {}
        printer_id = f"{printer_type}@{ip}"

        if printer_type.startswith("bambu"):
            status = self._poll_bambu(ip, serial, access_code)
        elif printer_type in ("moonraker", "elegoo_centauri_2", "elegoo_cc2"):
            status = self._poll_moonraker(ip, port or 7125)
        else:
            status = {"state": "unknown", "printer_type": printer_type}

        self._printer_states[printer_id] = status

        # Relay to feedback bus
        progress = None
        if "progress" in status:
            try:
                progress = float(status["progress"])
            except (ValueError, TypeError):
                pass

        self.bus.emit_printer_telemetry(printer_id, status, progress)

        return status

    @staticmethod
    def _poll_bambu(ip: str, serial: str, access_code: str) -> Dict[str, Any]:
        """Query Bambu printer via MQTT single-shot status request."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            return {"state": "error", "error": "paho-mqtt not installed"}

        result_data: Dict[str, Any] = {"state": "connecting"}
        received = []

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                topic = f"device/{serial}/report"
                client.subscribe(topic)
                # Request status
                push_topic = f"device/{serial}/request"
                client.publish(push_topic, json.dumps({
                    "pushing": {"sequence_id": "0", "command": "pushall"}
                }))
            else:
                result_data["state"] = "auth_failed"
                result_data["rc"] = rc

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8", errors="replace"))
                if "print" in payload:
                    p = payload["print"]
                    result_data.update({
                        "state": p.get("gcode_state", "unknown"),
                        "progress": p.get("mc_percent", 0),
                        "nozzle_temp": p.get("nozzle_temper", 0),
                        "bed_temp": p.get("bed_temper", 0),
                        "layer": p.get("layer_num", 0),
                        "total_layers": p.get("total_layer_num", 0),
                        "fan_speed": p.get("cooling_fan_speed", 0),
                        "wifi_signal": p.get("wifi_signal", ""),
                    })
                    ams = p.get("ams", {})
                    if ams:
                        result_data["ams"] = ams
                received.append(True)
            except Exception:
                pass

        client = mqtt.Client()
        client.username_pw_set("bblp", access_code)
        client.tls_set()
        client.tls_insecure_set(True)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(ip, 8883, keepalive=10)
            # Non-blocking loop with timeout
            deadline = time.time() + 5.0
            client.loop_start()
            while not received and time.time() < deadline:
                time.sleep(0.1)
            client.loop_stop()
            client.disconnect()
        except Exception as e:
            result_data = {"state": "connection_failed", "error": str(e)}

        return result_data

    @staticmethod
    def _poll_moonraker(ip: str, port: int = 7125) -> Dict[str, Any]:
        """Query Moonraker/Klipper printer via HTTP API."""
        try:
            import requests as req
        except ImportError:
            return {"state": "error", "error": "requests not installed"}

        base = f"http://{ip}:{port}"
        try:
            resp = req.get(f"{base}/printer/objects/query",
                           params={"extruder": None, "heater_bed": None,
                                   "print_stats": None, "toolhead": None,
                                   "fan": None},
                           timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("result", {}).get("status", {})
                extruder = data.get("extruder", {})
                bed = data.get("heater_bed", {})
                stats = data.get("print_stats", {})
                toolhead = data.get("toolhead", {})
                fan = data.get("fan", {})

                progress = 0.0
                if stats.get("print_duration", 0) > 0:
                    # Estimate progress from file position if available
                    resp2 = req.get(f"{base}/printer/objects/query",
                                    params={"virtual_sdcard": None},
                                    timeout=3)
                    if resp2.status_code == 200:
                        vsd = resp2.json().get("result", {}).get("status", {}).get("virtual_sdcard", {})
                        progress = vsd.get("progress", 0) * 100

                return {
                    "state": stats.get("state", "unknown"),
                    "nozzle_temp": extruder.get("temperature", 0),
                    "nozzle_target": extruder.get("target", 0),
                    "bed_temp": bed.get("temperature", 0),
                    "bed_target": bed.get("target", 0),
                    "print_duration": stats.get("print_duration", 0),
                    "filename": stats.get("filename", ""),
                    "position": toolhead.get("position", []),
                    "fan_speed": fan.get("speed", 0),
                    "progress": progress,
                }
            return {"state": "http_error", "status_code": resp.status_code}
        except Exception as e:
            return {"state": "connection_failed", "error": str(e)}

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Return cached states from all polled printers."""
        return dict(self._printer_states)


# ════════════════════════════════════════════════════════════════════════════════
# INTEGRATED SWARM RUNNER WITH FULL FEEDBACK LOOP
# ════════════════════════════════════════════════════════════════════════════════

class OsirisIntelligenceLoop:
    """
    The full tridirectional loop wiring swarm, intent, and feedback bus.

    Usage:
        loop = OsirisIntelligenceLoop()
        result = loop.execute("build a thread-safe cache")
        result = loop.execute("now optimize it for read-heavy workloads")
        loop.print_full_dashboard()

    Each execution:
      1. Intent engine parses input → routing decision
      2. Feedback bus relays intent context to swarm
      3. Swarm deliberates with cognitive mesh + introspection
      4. Feedback bus relays telemetry back to intent engine
      5. Intent engine adjusts confidence for next routing
      6. TUI receives diagnostics for display
    """

    def __init__(self, user_id: str = "default"):
        from osiris_ncllm_swarm import NCLLMSwarm
        from osiris_intent_engine import IntentEngine

        self.swarm = NCLLMSwarm(user_id=user_id, enable_mesh=True)
        self.intent_engine = IntentEngine()
        self.bus = FeedbackBus()

        self._task_count = 0
        self._quality_history: List[float] = []

        # Wire up bus subscribers
        self.bus.subscribe("intent", self._on_intent_message)
        self.bus.subscribe("swarm", self._on_swarm_message)

    def _on_intent_message(self, msg: BusMessage):
        """Handle messages targeting the intent engine."""
        if msg.msg_type == MessageType.TELEMETRY:
            # Swarm results feed back into intent confidence
            quality = msg.payload.get("quality", 0.5)
            introspection = msg.payload.get("introspection", {})
            intent_state = self.bus.get_intent_state()
            intent_type = intent_state.get("intent_type", "unknown")
            self.intent_engine.receive_swarm_feedback(
                intent_type, quality, introspection
            )

    def _on_swarm_message(self, msg: BusMessage):
        """Handle messages targeting the swarm."""
        if msg.msg_type == MessageType.CONTEXT:
            # Intent context can be injected into swarm personality
            # Adjust personality based on detected intent
            intent_type = msg.payload.get("intent_type", "")
            if "debug" in intent_type or "experiment" in intent_type:
                self.swarm.personality.debug_weight = min(
                    0.9, self.swarm.personality.debug_weight + 0.05
                )
            elif "create" in intent_type or "manufacturing" in intent_type:
                self.swarm.personality.creativity = min(
                    0.9, self.swarm.personality.creativity + 0.05
                )

    def execute(self, user_input: str,
                max_rounds: int = 5) -> Dict[str, Any]:
        """
        Execute one full tridirectional loop.

        Returns a dict with swarm result, intent analysis, and bus state.
        """
        self._task_count += 1

        # Step 1: Intent engine parses input
        intent = self.intent_engine.parse_intent(user_input)
        capability_ctx = self.intent_engine.get_swarm_capability_context()

        # Adjust confidence with learned feedback
        adjusted_confidence = self.intent_engine.get_adaptive_confidence(
            intent.confidence, intent.intent_type
        )

        # Step 2: Publish intent routing to bus
        self.bus.emit_intent_routing(
            intent_type=intent.intent_type.value,
            confidence=adjusted_confidence,
            suggested_actions=intent.suggested_actions,
            capability_context=capability_ctx,
        )

        # Step 3: Swarm deliberates
        result = self.swarm.solve(user_input, max_rounds=max_rounds)

        # Step 4: Publish swarm telemetry to bus
        introspection_data = result.metadata.get("introspection", {})
        mesh_data = result.metadata.get("cognitive_mesh", {})
        self.bus.emit_swarm_telemetry(
            quality=result.quality_score,
            introspection_data=introspection_data,
            mesh_data=mesh_data,
        )

        # Step 5: Emit alerts from introspection
        if introspection_data:
            for action in introspection_data.get("improvement_actions", [])[:3]:
                if action.get("priority", 0) > 0.7:
                    self.bus.emit_alert(
                        source="introspection",
                        message=action.get("rationale", "improvement needed"),
                        severity=action["priority"],
                    )

        # Step 6: Record quality
        self._quality_history.append(result.quality_score)

        # Store in conversation history
        self.intent_engine.add_to_history(user_input, result.final_output[:200])

        return {
            "task": user_input,
            "intent": {
                "type": intent.intent_type.value,
                "confidence": adjusted_confidence,
                "agents": intent.required_agents,
            },
            "result": result.to_dict(),
            "bus_state": self.bus.get_unified_state(),
        }

    def print_full_dashboard(self):
        """Print comprehensive dashboard across all three axes."""
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║  OSIRIS TRIDIRECTIONAL INTELLIGENCE DASHBOARD" + " " * 24 + "║")
        print("╚" + "═" * 70 + "╝")
        print(f"  Tasks executed: {self._task_count}")

        if self._quality_history:
            avg_q = sum(self._quality_history) / len(self._quality_history)
            trend = ""
            if len(self._quality_history) >= 3:
                recent = self._quality_history[-3:]
                older = self._quality_history[-6:-3] if len(self._quality_history) >= 6 else self._quality_history[:3]
                delta = (sum(recent) / len(recent)) - (sum(older) / len(older))
                trend = " ↑" if delta > 0.02 else " ↓" if delta < -0.02 else " →"
            print(f"  Average quality: {avg_q:.3f}{trend}")
            print(f"  Quality trace: {' → '.join(f'{q:.2f}' for q in self._quality_history[-10:])}")

        # Swarm section
        print(f"\n{'─' * 72}")
        print("  AXIS 1: NCLLM Swarm Intelligence")
        print(f"{'─' * 72}")
        print(self.swarm.status_report())

        # Introspection section
        if self.swarm._introspection is not None:
            self.swarm._introspection.print_dashboard()

        # Intent section
        print(f"\n{'─' * 72}")
        print("  AXIS 2: Adaptive Intent Engine")
        print(f"{'─' * 72}")
        cap_ctx = self.intent_engine.get_swarm_capability_context()
        if cap_ctx.get("intent_success_rates"):
            print("  Intent success rates (learned):")
            for intent, rate in cap_ctx["intent_success_rates"].items():
                bar = "█" * int(rate * 20) + "░" * (20 - int(rate * 20))
                print(f"    {intent:15s} [{bar}] {rate:.3f}")
        if cap_ctx.get("confidence_adjustments"):
            print("  Confidence adjustments:")
            for intent, adj in cap_ctx["confidence_adjustments"].items():
                sign = "+" if adj >= 0 else ""
                print(f"    {intent:15s} {sign}{adj:.3f}")

        # Bus section
        print(f"\n{'─' * 72}")
        print("  AXIS 3: Tridirectional Feedback Bus")
        print(f"{'─' * 72}")
        self.bus.print_status()
