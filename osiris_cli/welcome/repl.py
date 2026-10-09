"""Onboarding walkthrough for the osiris REPL (/welcome).

The tour shows three steps, each naming one read-only parent command, and runs
none of them: typing the command at the osiris prompt is the only way it runs.
It hands the parent a WelcomeResult (status, chosen profile, steps seen), which
carries no permissions and is only printed.

Model rewording is off by default and needs an adapter; its text must pass
safe_text and name no command, and is shown labelled "AI-generated, unverified".
Analytics are off by default, kept in this object's memory only, and deleted
by /analytics clear.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional, Protocol


@dataclass(frozen=True)
class WelcomeStep:
    id: str
    title: str
    content: str
    suggested_command: str


@dataclass(frozen=True)
class WelcomeResult:
    status: str
    industry: str
    style: str
    visited_steps: tuple[str, ...]


class NCLLMAdapter(Protocol):
    def propose_text(self, request: dict[str, str]) -> str:
        """Return bounded display text; never execute a task."""
        ...


# Each suggested command is read-only and handled by osiris_repl.dispatch_command
# (tests/test_welcome.py checks both against the parent's handlers).
STEPS = (
    WelcomeStep(
        "orientation",
        "OSIRIS workspace orientation",
        "See what each pipeline layer implements and what is not built yet. "
        "Nothing here executes imported research.",
        "/architecture",
    ),
    WelcomeStep(
        "research",
        "Research discovery",
        "Inspect indexed sources and their SHA-256 provenance before you use them.",
        "/sources",
    ),
    WelcomeStep(
        "governance",
        "Authority and evidence",
        "Model suggestions do not grant execution or publication rights. "
        "The claims register shows which statements have evidence.",
        "/legit list",
    ),
)

INDUSTRIES = ("research", "healthcare", "defense", "finance")
STYLES = ("direct", "guided", "exploratory")

# A word starting with "/" reads as a command; model text must not suggest one.
COMMAND_TOKEN = re.compile(r"(?:^|\s)/\w")


def safe_text(value: object, maximum: int = 600) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Invalid display text: type mismatch or length exceeded")
    if any(
        unicodedata.category(char).startswith("C") and char != "\n"
        for char in value
    ):
        raise ValueError("Control characters detected in display text")
    value = value.strip()
    if not value:
        raise ValueError("Empty display text")
    return value


class WelcomeREPL:
    def __init__(
        self,
        model: Optional[NCLLMAdapter] = None,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
    ) -> None:
        self.model = model
        self.read = read
        self.write = write
        self.industry = "research"
        self.style = "direct"
        self.ai_enabled = False
        self.analytics_enabled = False
        self.events: list[dict[str, object]] = []
        self.visited: list[str] = []
        self.index = 0

    def record(self, event: str, step_id: Optional[str] = None) -> None:
        if self.analytics_enabled:
            self.events.append({
                "event": event,
                "step_id": step_id,
                "monotonic_s": time.monotonic(),
            })

    def show_step(self) -> None:
        step = STEPS[self.index]
        content = step.content
        if self.ai_enabled and self.model is not None:
            try:
                proposal = self.model.propose_text({
                    "task": "Rewrite onboarding wording only.",
                    "constraints": (
                        "No commands, authority claims, statistics, "
                        "urgency, certifications, or execution claims."
                    ),
                    "industry": self.industry,
                    "style": self.style,
                    "source_text": step.content,
                })
                content = safe_text(proposal)
                if COMMAND_TOKEN.search(content):
                    raise ValueError("Model text names a command")
                self.write("Wording: AI-generated, unverified")
            except Exception:  # noqa: BLE001 - any adapter failure falls back to the baseline text
                content = step.content
                self.write("Personalization unavailable; using baseline.")

        self.write(f"\n[{self.index + 1}/{len(STEPS)}] {step.title}")
        self.write(content)
        self.write(f"Suggested command: {step.suggested_command}")
        self.write("Nothing runs from here; type it at the osiris prompt after /done.")

        if step.id not in self.visited:
            self.visited.append(step.id)
        self.record("step_viewed", step.id)

    def result(self, status: str) -> WelcomeResult:
        return WelcomeResult(
            status=status,
            industry=self.industry,
            style=self.style,
            visited_steps=tuple(self.visited),
        )

    def run(self) -> WelcomeResult:
        self.write(
            "OSIRIS :: WELCOME\n"
            "Execution authority: not evaluated by this module\n"
            "AI personalization: OFF | Analytics: OFF\n"
            "Type /help or /skip."
        )
        self.show_step()

        while True:
            try:
                parts = self.read("osiris:welcome> ").strip().split()
            except (EOFError, KeyboardInterrupt):
                self.write("\nWelcome dismissed.")
                return self.result("dismissed")

            if not parts:
                continue

            command, *args = parts

            if command == "/help":
                self.write(
                    "/next | /back | /show | /done | /skip\n"
                    f"/industry {'|'.join(INDUSTRIES)}\n"
                    f"/style {'|'.join(STYLES)}\n"
                    "/ai on|off | /analytics on|off|clear|show"
                )
            elif command in {"/next", "/back", "/show"} and not args:
                if command == "/next":
                    self.index = min(self.index + 1, len(STEPS) - 1)
                elif command == "/back":
                    self.index = max(self.index - 1, 0)
                self.show_step()
            elif command == "/industry" and len(args) == 1 and args[0] in INDUSTRIES:
                self.industry = args[0]
                self.show_step()
            elif command == "/style" and len(args) == 1 and args[0] in STYLES:
                self.style = args[0]
                self.show_step()
            elif command == "/ai" and args in [["on"], ["off"]]:
                if args == ["on"] and self.model is None:
                    self.write("No NCLLM adapter configured.")
                else:
                    self.ai_enabled = args == ["on"]
                    self.show_step()
            elif command == "/analytics" and len(args) == 1:
                action = args[0]
                if action == "on":
                    self.analytics_enabled = True
                    self.record("analytics_enabled")
                    self.write("Local in-memory analytics enabled.")
                elif action == "off":
                    self.analytics_enabled = False
                    self.write("Collection stopped; /analytics clear deletes.")
                elif action == "clear":
                    self.events.clear()
                    self.write("Session analytics deleted.")
                elif action == "show":
                    self.write(json.dumps({
                        "enabled": self.analytics_enabled,
                        "event_count": len(self.events),
                        "events": self.events,
                    }, indent=2))
                else:
                    self.write("Use /analytics on|off|clear|show.")
            elif command in {"/done", "/skip"} and not args:
                if command == "/skip":
                    status = "dismissed"
                elif len(self.visited) == len(STEPS):
                    status = "completed"
                else:
                    status = "ended_early"
                self.record(status)
                self.write(f"Welcome {status}. No tasks were executed.")
                return self.result(status)
            else:
                self.write("Unknown welcome command. Type /help.")
