"""OSIRIS conversation loop: voices, held-out discipline, the speaking gate."""
import json

from osiris_cli import living
from osiris_cli.living import Osiris


class ScriptedMentor:
    base = "scripted://"

    def __init__(self, reply="Hello Devin.", model="qwen2.5:7b", fail=None):
        self.reply, self._model, self.fail, self.calls = reply, model, fail, []

    def model(self):
        return self._model

    def set_model(self, name):
        self._model = name

    def stream(self, messages):
        self.calls.append(messages)
        if self.fail:
            raise self.fail
        for word in self.reply.split(" "):
            yield word + " "


class FakeCore:
    name = "fake"

    def __init__(self, bpb=5.0, draft="I am OSIRIS."):
        self.bpb, self._draft, self.learned, self._step = bpb, draft, [], 0

    def step(self):
        return self._step

    def bits_per_byte(self, text):
        return self.bpb

    def learn(self, text, steps):
        self.learned.append(text)
        self._step += steps
        return 1.0

    def draft(self, prompt, max_bytes=160):
        return self._draft


def scores(o, n, core_bpb, uni=4.5):
    o.stats["heldout_scores"] = {f"h{i}": [core_bpb, uni, 0, i] for i in range(n)}


def make(tmp_path, **kw):
    out = []
    o = Osiris(core=kw.pop("core", FakeCore()), mentor=kw.pop("mentor", ScriptedMentor()),
               home=str(tmp_path), out=out.append, background=False)
    return o, out


def test_plain_text_is_answered_by_mentor_while_gate_closed(tmp_path):
    o, out = make(tmp_path)
    reply = o.converse("hello osiris, im devin")
    assert reply.strip() == "Hello Devin."
    text = "".join(out)
    assert "OSIRIS ›" in text and "voice: qwen2.5:7b speaking for OSIRIS" in text
    rec = json.loads(open(o.log_path).read().splitlines()[0])
    assert rec["voice"] == "mentor:qwen2.5:7b" and rec["user"] == "hello osiris, im devin"


def test_every_fifth_exchange_is_heldout_and_never_trained(tmp_path):
    core = FakeCore()
    o, _ = make(tmp_path, core=core)
    for i in range(10):
        o.converse(f"message {i}")
    assert len(o.stats["heldout_scores"]) == 2           # exchanges 0 and 5
    assert len(core.learned) == 8
    assert not any("message 0\n" in t or "message 5\n" in t for t in core.learned)


def test_gate_opens_only_after_enough_good_heldout_scores(tmp_path):
    o, _ = make(tmp_path)
    scores(o, living.GATE_WINDOW - 1, 1.5)
    assert not o.gate()["open"]
    scores(o, living.GATE_WINDOW, 1.5)
    assert o.gate()["open"]
    scores(o, living.GATE_WINDOW, 3.0)
    assert not o.gate()["open"]


def test_open_gate_lets_the_core_speak_and_it_is_not_trained_on_itself(tmp_path):
    core = FakeCore(draft="I remember you.")
    mentor = ScriptedMentor()
    o, out = make(tmp_path, core=core, mentor=mentor)
    scores(o, living.GATE_WINDOW, 1.2)
    assert o.converse("do you remember me?") == "I remember you."
    assert mentor.calls == [] and core.learned == []
    assert o.stats["core_spoke"] == 1 and "own weights" in "".join(out)


def test_garbled_core_draft_falls_back_to_mentor(tmp_path):
    o, _ = make(tmp_path, core=FakeCore(draft="\x00\x01\x02\x7f\x03"))
    scores(o, living.GATE_WINDOW, 1.2)
    assert o.converse("hi").strip() == "Hello Devin."


def test_pasted_transcripts_are_answered_but_not_learned(tmp_path):
    core = FakeCore()
    o, out = make(tmp_path, core=core)
    o.converse("warm-up")                                # exchange 0 is held out
    o.converse("╭─ ENGINE COUNCIL ─╮", learnable=False)
    assert core.learned == [] and "pasted transcript" in "".join(out)


def test_interrupted_or_failed_mentor_is_not_learned(tmp_path):
    core = FakeCore()
    o, out = make(tmp_path, core=core, mentor=ScriptedMentor(fail=ConnectionError("down")))
    o.converse("warm-up")
    o.converse("hello")
    assert core.learned == [] and o.stats["exchanges"] == 0


def test_no_voice_available_says_so_instead_of_faking(tmp_path):
    o, out = make(tmp_path, mentor=ScriptedMentor(model=None))
    assert o.converse("hello") == ""
    assert "can't answer yet" in "".join(out)


def test_exchange_log_is_hash_chained(tmp_path):
    o, _ = make(tmp_path)
    o.converse("one")
    o.converse("two")
    rows = [json.loads(line) for line in open(o.log_path)]
    assert rows[1]["prev"] == rows[0]["hash"] and rows[0]["prev"] == "0" * 64


def test_newer_rescoring_on_disk_wins_when_stats_are_saved(tmp_path):
    o, _ = make(tmp_path)
    o.stats["heldout_scores"] = {"a": [9.0, 8.0, 3, 0]}
    o._save_stats()
    disk = json.load(open(o.stats_path))
    disk["heldout_scores"]["a"] = [2.5, 4.4, 900, 0]      # a trainer rescored with newer weights
    json.dump(disk, open(o.stats_path, "w"))
    o._save_stats()                                       # a stale in-memory copy must not win
    assert json.load(open(o.stats_path))["heldout_scores"]["a"][2] == 900
