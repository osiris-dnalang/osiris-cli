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
               home=str(tmp_path), out=out.append, background=False,
               knowledge=kw.pop("knowledge", None), tty=False)
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


def _knowledge(tmp_path):
    from osiris_cli.knowledge import Knowledge
    doc = tmp_path / "README.md"
    doc.write_text("# Results\n\n<!-- scorecard:start -->\n| experiment | verdict | number |\n|---|---|---|\n"
                   "| relay dead | PASS | median 100 |\n| concept drift | FAIL | ratio 0.8 |\n"
                   "<!-- scorecard:end -->\n\n## Relay recovery\n\nThe organism reroutes around a "
                   "dead relay in a median of 100 trials.\n\n## Drift\n\nConcept drift failed.\n")
    return Knowledge(base=str(tmp_path), sources=[str(doc)])


def test_mentor_is_told_what_is_on_record_and_notes_are_cited(tmp_path):
    mentor = ScriptedMentor()
    o, out = make(tmp_path / "home", mentor=mentor, knowledge=_knowledge(tmp_path))
    o.converse("did the relay reroute work?")
    system, last = mentor.calls[0][0]["content"], mentor.calls[0][-1]["content"]
    assert "relay dead: PASS" in system and "concept drift: FAIL" in system
    assert "reroutes around a dead relay" in last and last.endswith("did the relay reroute work?")
    assert "used: README.md" in "".join(out)
    # history and the training lesson keep only what was said, not the attached notes
    assert o.history[0]["content"] == "did the relay reroute work?"
    assert json.loads(open(o.log_path).read().splitlines()[0])["user"] == "did the relay reroute work?"


def test_system_prompt_is_stable_across_turns(tmp_path):
    mentor = ScriptedMentor()
    o, _ = make(tmp_path / "home", mentor=mentor, knowledge=_knowledge(tmp_path))
    o.converse("hello")
    o.converse("what drift results are there?")
    assert mentor.calls[0][0] == mentor.calls[1][0]
    assert [m["content"] for m in mentor.calls[1][1:3]] == ["hello", "Hello Devin. "]


def test_chat_marks_itself_active_for_the_trainer(tmp_path):
    from osiris_cli import train
    o, _ = make(tmp_path)
    assert not train.chat_active(str(tmp_path))
    o.converse("hi")
    assert train.chat_active(str(tmp_path))


def test_lines_typed_during_a_reply_are_queued_and_partial_ones_reported(tmp_path):
    o, out = make(tmp_path)
    o._hold("tell me about yourself\nwhat do you know\nhalf a thou")
    assert o.held == ["tell me about yourself", "what do you know"]
    assert "'half a thou'" in "".join(out) and "not sent" in "".join(out)


def test_checks_are_attached_to_the_message_and_listed(tmp_path):
    from osiris_cli.probes import Probes
    mentor = ScriptedMentor()
    o, out = make(tmp_path)
    o.mentor = mentor
    o.probes = Probes(str(tmp_path), base=str(tmp_path), trainer_status=lambda: ["run 7 · step 120"])
    o.converse("how is training going?")
    last = mentor.calls[0][-1]["content"]
    assert "[Checked just now" in last and "$ osiris train --status\nrun 7 · step 120" in last
    assert "used: osiris train --status" in "".join(out)


def test_new_session_recalls_earlier_exchanges_and_remembered_facts(tmp_path):
    o, _ = make(tmp_path)
    o.converse("my cat is called Qubit")
    print(o.remember("Devin prefers short answers"))
    mentor = ScriptedMentor()
    o2, _ = make(tmp_path, mentor=mentor)          # a new session, same home
    o2.converse("hi again")
    system = mentor.calls[0][0]["content"]
    assert "my cat is called Qubit" in system and "- Devin prefers short answers" in system
    assert "Forgot 1" in o2.forget("short answers") and o2.facts() == []


def test_restore_best_makes_best_weights_live_as_a_newer_step(tmp_path):
    import threading

    from osiris_cli.living import NclmCore

    class Console:
        _organism_lock = threading.Lock()

        def __init__(self):
            self._organism_state = {"model": object(), "optimizer": None, "step": 0, "history": []}

        def _organism_checkpoint_paths(self):
            return str(tmp_path / "organism.npz"), str(tmp_path / "organism.json")

        def _organism_save(self, model, optimizer, step, history, rotate=False):
            (tmp_path / "organism.npz").write_text(f"weights@{step}")
            (tmp_path / "organism.json").write_text(json.dumps({"step": step}))

    con = Console()
    core = NclmCore(con)
    con._organism_state["step"] = 20
    core.save_best()
    con._organism_state["step"] = 90                       # training went on and got worse
    core.save()
    assert core.restore_best() == 20
    assert (tmp_path / "organism.npz").read_text() == "weights@20"
    meta = json.loads((tmp_path / "organism.json").read_text())
    assert meta == {"step": 91, "restored_from_step": 20}
    assert con._organism_state["model"] is None             # reloads from disk next use
