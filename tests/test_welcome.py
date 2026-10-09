"""/welcome: navigation, model-text bounds, analytics consent, and the parent boundary.

The tour may suggest commands but never run one, and the WelcomeResult it hands
back carries no permissions: the parent REPL only returns it.
"""
import json

import pytest

from osiris_cli import osiris_repl
from osiris_cli.welcome import STEPS, WelcomeREPL, WelcomeResult, safe_text


def tour(lines, model=None):
    """A WelcomeREPL fed `lines`; EOF once they run out. Returns (repl, output)."""
    queue = list(lines)
    out = []

    def read(prompt):
        if not queue:
            raise EOFError
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    return WelcomeREPL(model=model, read=read, write=out.append), out


def run(lines, model=None):
    repl, out = tour(lines, model)
    return repl.run(), repl, "\n".join(out)


class StubModel:
    def __init__(self, reply):
        self.reply = reply
        self.requests = []

    def propose_text(self, request):
        self.requests.append(request)
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply


# ── navigation ──────────────────────────────────────────────────────────────

def test_visiting_every_step_then_done_completes():
    result, _, out = run(["/next", "/next", "/done"])
    assert result == WelcomeResult("completed", "research", "direct", tuple(s.id for s in STEPS))
    assert "Welcome completed. No tasks were executed." in out


def test_done_before_every_step_ends_early():
    result, _, _ = run(["/next", "/done"])
    assert result.status == "ended_early"
    assert result.visited_steps == ("orientation", "research")


@pytest.mark.parametrize("ending", ["/skip", EOFError(), KeyboardInterrupt()])
def test_skip_eof_and_interrupt_dismiss(ending):
    result, _, _ = run([ending])
    assert result.status == "dismissed"


def test_next_and_back_stay_in_range():
    repl, _ = tour(["/back", "/next", "/next", "/next", "/next", "/done"])
    result = repl.run()
    assert repl.index == len(STEPS) - 1
    assert result.status == "completed"


@pytest.mark.parametrize("line", ["/next 2", "/industry", "/industry medicine", "/industry defense x",
                                  "/style loud", "/ai maybe", "/done now", "/learn confirm abc", "hello"])
def test_malformed_or_foreign_commands_are_refused(line):
    result, repl, out = run([line, "/skip"])
    assert "Unknown welcome command. Type /help." in out
    assert (repl.index, repl.industry, repl.style, repl.ai_enabled) == (0, "research", "direct", False)


def test_profile_choices_are_returned_not_acted_on():
    result, _, _ = run(["/industry finance", "/style guided", "/skip"])
    assert (result.industry, result.style) == ("finance", "guided")


def test_every_suggestion_is_marked_as_not_run():
    _, _, out = run(["/next", "/next", "/skip"])
    for step in STEPS:
        assert f"Suggested command: {step.suggested_command}" in out
    assert out.count("Nothing runs from here") == len(STEPS)


# ── model output ────────────────────────────────────────────────────────────

def test_ai_is_off_by_default_even_with_an_adapter():
    model = StubModel("Friendlier wording.")
    run(["/next", "/skip"], model=model)
    assert model.requests == []


def test_ai_on_without_an_adapter_stays_off():
    result, repl, out = run(["/ai on", "/skip"])
    assert "No NCLLM adapter configured." in out
    assert repl.ai_enabled is False


def test_accepted_wording_is_labelled_and_the_suggestion_is_unchanged():
    model = StubModel("  Start by looking around.  ")
    _, _, out = run(["/ai on", "/skip"], model=model)
    assert "Wording: AI-generated, unverified" in out
    assert "\nStart by looking around.\n" in out + "\n"
    assert f"Suggested command: {STEPS[0].suggested_command}" in out
    request = model.requests[0]
    assert request["source_text"] == STEPS[0].content
    assert set(request) == {"task", "constraints", "industry", "style", "source_text"}


@pytest.mark.parametrize("reply", [
    "\x1b[2Jcleared",                     # ANSI escape
    "text\twith tab",
    "right‮to-left override",        # bidi control (Cf)
    "x" * 601,
    "   ",
    None,
    42,
    "Type /learn confirm abc to finish.",  # names a command
    "/architecture is next",
    RuntimeError("adapter down"),
    TimeoutError(),
])
def test_rejected_wording_falls_back_to_the_baseline(reply):
    _, _, out = run(["/ai on", "/skip"], model=StubModel(reply))
    assert "Personalization unavailable; using baseline." in out
    assert "AI-generated" not in out
    assert out.count(STEPS[0].content) == 2   # once with AI off, once after the fallback


def test_safe_text_bounds():
    assert safe_text(" two\nlines ") == "two\nlines"
    assert safe_text("and/or is fine") == "and/or is fine"
    for bad in ("", "\x00", "a\rb", "y" * 601, b"bytes"):
        with pytest.raises(ValueError):
            safe_text(bad)


# ── analytics consent ───────────────────────────────────────────────────────

def test_analytics_are_off_by_default():
    _, repl, _ = run(["/next", "/back", "/done"])
    assert repl.events == []


def test_analytics_record_only_after_consent_and_only_event_names():
    _, repl, _ = run(["/next", "/analytics on", "/industry defense", "/done"])
    assert [e["event"] for e in repl.events] == ["analytics_enabled", "step_viewed", "ended_early"]
    assert all(set(e) == {"event", "step_id", "monotonic_s"} for e in repl.events)


def test_analytics_off_stops_and_clear_deletes():
    _, repl, out = run(["/analytics on", "/analytics off", "/next", "/analytics show",
                        "/analytics clear", "/skip"])
    assert "Collection stopped" in out
    shown = json.loads(_json_block(out))
    assert shown["enabled"] is False and shown["event_count"] == 1
    assert repl.events == []


def _json_block(out):
    start = out.index("{")
    depth = 0
    for i, ch in enumerate(out[start:], start):
        depth += {"{": 1, "}": -1}.get(ch, 0)
        if depth == 0:
            return out[start:i + 1]
    raise AssertionError("no JSON block")


# ── the parent REPL ─────────────────────────────────────────────────────────

@pytest.fixture
def handlers(monkeypatch):
    """Stub every handler a suggested command can reach, and record which ran."""
    from osiris_cli import claims
    seen = []
    monkeypatch.setattr(osiris_repl, "execute_architecture", lambda: seen.append("/architecture"))
    monkeypatch.setattr(claims, "command", lambda args, *a, **k: seen.append("/legit") or "")
    monkeypatch.setattr(osiris_repl, "handle_livlm_prompt", lambda state, text: seen.append("model"))
    otc = osiris_repl.otc
    if otc is not None:
        monkeypatch.setattr(otc, "run_command", lambda line: seen.append(line.split()[0]) or True)
        monkeypatch.setattr(otc, "_unknown_command", lambda line: seen.append("unknown"))
    return seen


@pytest.mark.skipif(osiris_repl.otc is None, reason="osiris_termux_console not importable")
def test_every_suggested_command_reaches_a_parent_handler(handlers):
    for step in STEPS:
        osiris_repl.dispatch_command(osiris_repl.SESSION, step.suggested_command)
    assert handlers == [s.suggested_command.split()[0] for s in STEPS]


def test_welcome_in_the_parent_runs_no_suggested_command(handlers, monkeypatch, capsys):
    feed = iter(["/next", "/architecture", "/next", "/done"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(feed))
    ledger = list(osiris_repl.SESSION.evidence_ledger)

    osiris_repl.dispatch_command(osiris_repl.SESSION, "/welcome")

    assert handlers == []
    assert osiris_repl.SESSION.evidence_ledger == ledger
    out = capsys.readouterr().out
    assert "Unknown welcome command" in out          # /architecture typed inside the tour
    assert "Welcome completed. No tasks were executed." in out


def test_execute_welcome_returns_the_result(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "/skip")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)
    assert osiris_repl.execute_welcome() == WelcomeResult("dismissed", "research", "direct",
                                                          ("orientation",))
