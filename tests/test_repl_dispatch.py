"""The `osiris` REPL routes console commands through the console's own router.

On 2026-10-02 the REPL's copy of that table had drifted: F crashed with
"_mentors() takes 0 positional arguments but 1 was given", J opened the
experiment brief with "/experiment" as its question, and seven commands called
functions that do not exist.
"""
import inspect
import re
from pathlib import Path

import pytest

from osiris_cli import osiris_repl

otc = osiris_repl.otc
pytestmark = pytest.mark.skipif(otc is None, reason="osiris_termux_console not importable")

REPL_SRC = Path(osiris_repl.__file__).read_text(encoding="utf-8")


def test_every_console_call_in_the_repl_exists_and_binds():
    for name, args in sorted(set(re.findall(r"otc\.(\w+)\(([^)]*)\)", REPL_SRC))):
        fn = getattr(otc, name, None)
        assert fn is not None, f"otc.{name} does not exist"
        if "=" not in args:
            n = len([a for a in args.split(",") if a.strip()])
            inspect.signature(fn).bind(*([None] * n))


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def rec(name):
        return lambda *a, **k: seen.append((name, a))

    for name in ("_mentors", "_experiment", "_experiments", "_gap", "_gaps", "_facts", "_consensus",
                 "_plan", "_runs_stats", "_run_show", "_organism_status", "_intent_status",
                 "_sprint_review", "_home", "_unknown_command", "_apply_pending_write",
                 "_discard_pending_write"):
        monkeypatch.setattr(otc, name, rec(name))
    monkeypatch.setattr(otc, "_pending_suggestions", {})
    monkeypatch.setattr(otc, "_home_letters", lambda pending=None: [
        ("C", "Engine 3 (NCLM): training status", "/organism status"),
        ("F", "Mentors: which model the evidence favors", "/mentors"),
        ("J", "Draft a quantum / research experiment brief", "/experiment")])
    monkeypatch.setattr(osiris_repl, "handle_livlm_prompt", lambda state, text: seen.append(("model", text)))
    monkeypatch.setattr(osiris_repl, "execute_osiris_status", lambda: seen.append(("nclm_status", ())))
    return seen


def run(line):
    osiris_repl.dispatch_command(osiris_repl.SESSION, line)


@pytest.mark.parametrize("line, expected", [
    ("f", ("_mentors", ())),
    ("/mentors", ("_mentors", ())),
    ("j", ("_experiment", ("",))),
    ("/experiment does DD help at 16 qubits", ("_experiment", (" does DD help at 16 qubits",))),
    ("/experiments", ("_experiments", ())),
    ("/gap add a quarantine queue", ("_gap", (" add a quarantine queue",))),
    ("/gaps", ("_gaps", ("/gaps",))),
    ("/facts", ("_facts", ())),
    ("/consensus", ("_consensus", ())),
    ("/plan a bell test", ("_plan", (" a bell test",))),
    ("/runs", ("_runs_stats", ())),
    ("/run show 3", ("_run_show", ("/run show 3",))),
    ("c", ("_organism_status", ())),
    ("/intent", ("_intent_status", ())),
    ("/nclm", ("nclm_status", ())),
    ("/sprint review", ("_sprint_review", ())),
])
def test_console_commands_reach_the_right_function_with_the_right_argument(calls, line, expected):
    run(line)
    assert calls == [expected]


def test_apply_and_discard_with_nothing_pending_say_so(calls, monkeypatch, capsys):
    monkeypatch.setattr(otc, "_pending_write", {"path": None})
    run("/apply")
    run("/discard")
    assert calls == [] and capsys.readouterr().out.count("nothing pending") == 2


def test_keys_and_typos_never_reach_the_model(calls, capsys):
    run("q")            # a letter no menu uses
    run("7")
    run("/stauts")
    assert ("model", "q") not in calls and ("model", "7") not in calls
    assert calls == [("_unknown_command", ("/stauts",))]
    assert capsys.readouterr().out.count("No menu item") == 2


def test_plain_text_still_goes_to_osiris(calls):
    run("hello osiris")
    run("/home/enki/log.txt line 1\nline 2")          # a pasted log is conversation
    assert calls == [("model", "hello osiris"), ("model", "/home/enki/log.txt line 1\nline 2")]


def test_a_suggestion_carrying_the_self_modify_override_is_not_run(calls, monkeypatch, capsys):
    monkeypatch.setattr(otc, "_pending_suggestions", {"1": "/sprint execute --allow-self-modify"})
    run("1")
    assert calls == [] and "only counts when you type it yourself" in capsys.readouterr().out
