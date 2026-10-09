"""The PIPELINE panel and /architecture: every layer drawn from a real check."""
import json

import pytest

import osiris_ui
from osiris_cli import architecture as arch
from osiris_cli.living import Osiris

genome_ledger = pytest.importorskip("genome_ledger")


class Mentor:
    base = "scripted://"

    def model(self):
        return "qwen2.5:7b"

    def fast_model(self):
        return "qwen2.5:1.5b"


class Console:
    CHAT_MODEL = "qwen2.5:7b"
    _pending_write = {"path": None}

    class research:
        @staticmethod
        def sources():
            return [1, 2, 3]

    @staticmethod
    def _next_best():
        return {"label": "Capture what you want OSIRIS to do next"}

    @staticmethod
    def _check_ollama_reachable(timeout=0.5):
        return True, "http://localhost:11434"

    @staticmethod
    def _synth_chain():
        return "qwen2.5:1.5b"

    @staticmethod
    def _integrity():
        return "verified", "genome ledger valid (1 entries) · bench evidence 9 files verified"


FIXTURE_LEDGER = str(__import__("pathlib").Path(__file__).parent / "fixtures" / "dnalang_ledger_v0_2_0.py")


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "genome_ledger.jsonl"
    monkeypatch.setattr(genome_ledger, "DEFAULT_PATH", str(path))
    if not __import__("os").path.exists(genome_ledger.LEDGER_SRC):   # no dnalang-core: use the pinned copy
        monkeypatch.setattr(genome_ledger, "LEDGER_SRC", FIXTURE_LEDGER)
        monkeypatch.setattr(genome_ledger, "_ledger_mod", None)
    return path


def living(tmp_path):
    return Osiris(core=None, mentor=Mentor(), home=str(tmp_path / "living"), out=lambda s: None,
                  background=False, tty=False)


def test_compact_panel_has_one_row_per_layer_and_states_the_gate(tmp_path, ledger):
    state = arch.live_state(living(tmp_path), Console)
    text = arch.compact(osiris_ui.Canvas("plain", 100), state)
    for layer in arch.LAYERS:
        assert f"{layer.key} {layer.name}" in text
    assert "0 exchanges, hash chain intact" in text
    assert "gate closed: not scored on held-out text yet" in text
    assert state["L4"][1].endswith("voice qwen2.5:7b (fast: qwen2.5:1.5b)")   # wraps in the panel
    assert "draft proposer qwen2.5:1.5b (unpromoted)" in state["L4"][1]
    assert "Synthesizer" not in state["L4"][1]
    assert "bench evidence 9 files verified" in text and "genome ledger empty" in text


def test_full_view_lists_what_is_not_built(tmp_path, ledger):
    text = arch.full(osiris_ui.Canvas("plain", 100), arch.live_state(living(tmp_path), Console))
    assert "not built: an independent critic that tries to falsify a candidate" in text
    assert text.count("not built:") == sum(len(ly.missing) for ly in arch.LAYERS) + \
        sum(len(s[2]) for s in arch.SUBSYSTEMS)


def test_a_broken_genome_ledger_is_named_and_explained_not_repaired(tmp_path, ledger):
    led = genome_ledger.GenomeLedger()
    led.append("A", {"x": 1})
    led.append("B", {"x": 2})
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[1]["payload"] = {"payload": {"x": 3}}           # edited after it was written
    before = "\n".join(json.dumps(r) for r in rows) + "\n"
    ledger.write_text(before)
    state = arch.live_state(living(tmp_path), Console)
    assert state["L8"] == ("blocked", "genome ledger BROKEN (2 entries): entry 1: hash mismatch "
                                      "-- see /architecture")
    detail = arch.ledger_detail()
    assert "written or edited outside GenomeLedger.append" in detail[0]
    assert ledger.read_text() == before                  # nothing rewritten


def test_a_failing_check_is_reported_and_the_panel_still_draws(tmp_path, ledger):
    class Broken(Console):
        @staticmethod
        def _next_best():
            raise RuntimeError("boom")

    state = arch.live_state(living(tmp_path), Broken)
    assert state["L2"] == ("review", "check failed (RuntimeError)")
    assert "L8 Ledger" in arch.compact(osiris_ui.Canvas("access", 72), state)


def test_without_living_or_console_every_layer_still_has_a_state(ledger):
    state = arch.live_state(None, None)
    assert set(state) == {layer.key for layer in arch.LAYERS}
