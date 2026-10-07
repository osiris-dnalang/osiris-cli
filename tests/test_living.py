"""OSIRIS conversation loop: voices, held-out discipline, the speaking gate."""
import json

from osiris_cli import living
from osiris_cli.living import Osiris


class ScriptedMentor:
    base = "scripted://"

    def __init__(self, reply="Hello Devin.", model="qwen2.5:7b", fail=None):
        self.reply, self._model, self.fail, self.calls = reply, model, fail, []
        self.used = []

    def model(self):
        return self._model

    def set_model(self, name):
        self._model = name

    def stream(self, messages, model=None):
        self.calls.append(messages)
        self.used.append(model)
        if self.fail:
            raise self.fail
        for word in self.reply.split(" "):
            yield word + " "


class TwoVoiceMentor(ScriptedMentor):
    """A slow main voice that can fail, and a fast one, like qwen2.5:7b and 1.5b."""

    def __init__(self, fail_main=None, pinned=False, **kw):
        super().__init__(**kw)
        self.fail_main, self.pinned, self.unloaded = fail_main, pinned, []

    def fast_model(self):
        return None if self.pinned else "qwen2.5:1.5b"

    def unload(self, model=None):
        self.unloaded.append(model)

    def stream(self, messages, model=None):
        self.used.append(model)
        if model == self._model and self.fail_main:
            raise self.fail_main
        yield f"answered by {model}"


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
    # Each prompt starts with the previous one plus the reply, so Ollama re-reads only
    # the new message; the history kept for the core holds only what was said.
    assert mentor.calls[1][:2] == mentor.calls[0] and mentor.calls[1][2]["content"] == "Hello Devin. "
    assert [m["content"] for m in o.history[:2]] == ["hello", "Hello Devin. "]


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


def test_a_long_paste_is_sent_as_a_bounded_excerpt_without_checks(tmp_path):
    from osiris_cli.probes import Probes
    mentor = ScriptedMentor()
    o, out = make(tmp_path)
    o.mentor = mentor
    calls = []
    o.probes = Probes(str(tmp_path), base=str(tmp_path), trainer_status=lambda: calls.append(1) or ["x"])
    paste = "how is training going? read research/a.py and verify/b.py\n" + "log line\n" * 20000
    o.converse(paste)
    sent = mentor.calls[0][-1]["content"]
    assert len(sent) < 9000 and "characters of this" in sent and calls == []
    assert len(o.history[0]["content"]) < 7000
    assert json.loads(open(o.log_path).read().splitlines()[0])["user"] == paste   # ledger keeps it all
    assert "long message: an excerpt" in "".join(out)


def test_a_long_message_is_answered_by_the_fast_voice(tmp_path):
    mentor = TwoVoiceMentor()
    o, out = make(tmp_path, mentor=mentor)
    o.converse("short question")
    o.converse("x " * living.LONG_MESSAGE)
    assert mentor.used == ["qwen2.5:7b", "qwen2.5:1.5b"]
    text = "".join(out)
    assert "voice: qwen2.5:1.5b speaking for OSIRIS (fast voice: long message)" in text
    assert json.loads(open(o.log_path).read().splitlines()[1])["voice"] == "mentor:qwen2.5:1.5b"


def test_a_main_voice_that_fails_before_a_word_hands_over_to_the_fast_voice(tmp_path):
    core = FakeCore()
    mentor = TwoVoiceMentor(fail_main=TimeoutError("timed out"))
    o, out = make(tmp_path, core=core, mentor=mentor)
    o.converse("warm-up")                                # exchange 0 is held out
    reply = o.converse("hello")
    assert reply == "answered by qwen2.5:1.5b" and mentor.used[-2:] == ["qwen2.5:7b", "qwen2.5:1.5b"]
    text = "".join(out)
    assert "asking qwen2.5:1.5b" in text and "(fast voice: the main voice failed)" in text
    assert len(core.learned) == 1                        # a full answer is still a lesson


def test_a_pinned_voice_is_never_swapped(tmp_path):
    mentor = TwoVoiceMentor(pinned=True, fail_main=TimeoutError("timed out"))
    o, out = make(tmp_path, mentor=mentor)
    assert o.converse("x " * living.LONG_MESSAGE) == ""
    assert mentor.used == ["qwen2.5:7b"] and "[mentor qwen2.5:7b failed" in "".join(out)


def test_every_reply_says_why_the_core_is_not_speaking(tmp_path):
    o, out = make(tmp_path)
    o.converse("hello")
    assert "gate closed, not scored yet" in "".join(out)
    scores(o, 2, 5.32, uni=4.70)
    o.converse("again")
    assert "gate closed (5.32 bits/byte held-out; speaks at <= 2.0)" in "".join(out)


def test_finish_unloads_the_voices_this_session_loaded(tmp_path):
    mentor = TwoVoiceMentor()
    o, _ = make(tmp_path, mentor=mentor)
    o.converse("hi")
    o.converse("x " * living.LONG_MESSAGE)
    o.finish()
    assert mentor.unloaded == ["qwen2.5:1.5b", "qwen2.5:7b"]


def test_ollama_mentor_takes_a_model_per_call_and_offers_the_fast_voice_unless_pinned(monkeypatch):
    sent = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __iter__(self):
            return iter([b'{"message": {"content": "hi"}, "done": true}\n'])

    def fake_urlopen(req, timeout=None):
        sent.append(json.loads(req.data))
        return Resp()

    monkeypatch.setattr(living.urllib.request, "urlopen", fake_urlopen)
    m = living.OllamaMentor(model="qwen2.5:7b")
    monkeypatch.setattr(m, "installed", lambda: ["qwen2.5:7b", "qwen2.5:1.5b"])
    assert "".join(m.stream([{"role": "user", "content": "x"}], model="qwen2.5:1.5b")) == "hi"
    assert sent[0]["model"] == "qwen2.5:1.5b"
    assert m.fast_model() is None                        # pinned with model=... / /mentor
    m.set_model(None)
    assert m.fast_model() == living.FAST_MENTOR


def greeter(tmp_path, **kw):
    """make(), with the REPL's small-talk rule: short social messages only."""
    o, out = make(tmp_path, **kw)
    o.small_talk = lambda text: len(text.split()) <= 5
    return o, out


def test_a_greeting_is_answered_by_code_at_once_and_never_learned(tmp_path):
    core, mentor = FakeCore(), ScriptedMentor()
    o, out = greeter(tmp_path, core=core, mentor=mentor)
    reply = o.converse("hello osiris")
    assert reply.startswith("Hello, I'm here.") and "qwen2.5:7b speaks for me" in reply
    assert mentor.calls == [] and core.learned == [] and o.stats["exchanges"] == 0
    assert "voice: code, no model · instant" in "".join(out)
    row = json.loads(open(o.log_path).read().splitlines()[0])
    assert row["voice"] == "code" and row["learnable"] is False and row["heldout"] is False
    assert o.converse("thanks") == "You're welcome."


def test_ok_and_longer_greetings_still_go_to_the_mentor(tmp_path):
    mentor = ScriptedMentor()
    o, _ = greeter(tmp_path, mentor=mentor)
    o.converse("ok")                                    # may answer a question OSIRIS asked
    o.converse("hello, can you explain staggered dynamical decoupling to me?")
    assert len(mentor.calls) == 2


def test_the_greeting_says_how_long_replies_usually_take_here(tmp_path):
    o, _ = greeter(tmp_path)
    o.stats["first_word"]["qwen2.5:7b"] = [50.0, 12.0, 20.0, 18.0]
    assert "start after about 20 s on this machine" in o.converse("hi")
    assert o._typical("qwen2.5:7b") == " · usually ~20 s"


def test_a_reply_records_how_long_its_first_word_took(tmp_path):
    o, _ = make(tmp_path)
    o.converse("what is on record?")
    assert len(o.stats["first_word"]["qwen2.5:7b"]) == 1


def test_an_overflowing_conversation_resends_earlier_turns_plainly_oldest_out(tmp_path, monkeypatch):
    mentor = ScriptedMentor()
    o, _ = make(tmp_path, mentor=mentor)
    budget = len(o.system_prompt()) + 2000                # room for about three plain turns
    monkeypatch.setattr(living, "PROMPT_BUDGET", budget)
    for i in range(6):
        o.converse(f"question {i} " + "word " * 60)
    last = mentor.calls[-1]
    assert sum(len(m["content"]) for m in last) <= budget
    assert last[1]["role"] == "user" and "[Live state" not in last[1]["content"]   # plain, as said
    assert "question 0" not in "".join(m["content"] for m in last[1:])            # oldest out first


def test_prewarm_reads_the_system_prompt_in_the_background_unless_a_trainer_runs(tmp_path):
    class Warmable(ScriptedMentor):
        def __init__(self):
            super().__init__()
            self.warmed = []

        def warm(self, messages, model=None):
            self.warmed.append((model, messages))

    mentor = Warmable()
    o, _ = make(tmp_path, mentor=mentor)
    assert o.prewarm() == "qwen2.5:7b"
    o._warm.join()
    assert mentor.warmed[0][1][0] == {"role": "system", "content": o.system_prompt()}
    o._trainer_running = lambda: True
    assert o.prewarm() is None
    assert make(tmp_path / "b")[0].prewarm() is None      # a mentor that cannot warm


def test_the_waiting_line_counts_seconds_and_clears_for_the_reply():
    out = []
    w = living.Waiting(out.append, lambda: "thinking · qwen2.5:7b", active=True).start()
    w.stop()
    assert "(thinking · qwen2.5:7b · 0 s)" in out[0] and out[-1] == "\r\x1b[KOSIRIS › "
    quiet = []
    living.Waiting(quiet.append, lambda: "x", active=False).start().stop()
    assert quiet == []


def test_recall_leaves_out_greetings(tmp_path):
    o, _ = greeter(tmp_path)
    o.converse("what is on record?")
    o.converse("hello")
    recall = Osiris(core=None, mentor=ScriptedMentor(), home=str(tmp_path), out=lambda s: None,
                    background=False, tty=False).recall
    assert "what is on record?" in recall and "'hello'" not in recall


def test_a_paste_during_a_reply_is_one_message_with_its_last_line():
    raw = "\x1b[200~What you pasted shows two things\nfirst point\nThe central idea may be worth testing\x1b[201~"
    o = Osiris.__new__(Osiris)
    o.held, out = [], []
    o.out = out.append
    o._hold(living.keys_typed(raw))
    assert o.held == ["What you pasted shows two things\nfirst point\nThe central idea may be worth testing"]
    assert out == []


def test_typed_keys_apply_backspace_and_drop_control_bytes():
    assert living.keys_typed("helo\x7flo\x01\r") == "hello\r"
    assert living.keys_typed("\x1b[200~ab\x7f\x1b[201~") == "\x1b[200~a\x1b[201~"


def test_a_named_experiment_gets_its_recorded_verdict_from_code_before_the_model(tmp_path):
    mentor = ScriptedMentor()
    o, out = make(tmp_path / "home", mentor=mentor, knowledge=_knowledge(tmp_path))
    o.converse("what happened with relay-dead?")
    text = "".join(out)
    assert "On record" in text and "relay dead: PASS  (README.md)" in text
    assert text.index("relay dead: PASS") < text.index("OSIRIS ›")              # code first
    assert "state them exactly" in mentor.calls[0][-1]["content"]
    o.converse("tell me about relays in general")                           # names none
    assert "[On record" not in mentor.calls[1][-1]["content"]


def test_the_voice_is_osiris_voice_not_the_architects_chat_model(monkeypatch):
    m = living.OllamaMentor()
    monkeypatch.setattr(m, "installed", lambda: ["qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b"])
    monkeypatch.setenv("OSIRIS_CHAT_MODEL", "qwen2.5:1.5b")             # the console's Architect
    monkeypatch.delenv("OSIRIS_VOICE", raising=False)
    assert m.model() == living.MENTOR_PREFERENCE[0]
    monkeypatch.setenv("OSIRIS_VOICE", "qwen2.5:3b")
    assert m.model() == "qwen2.5:3b"
    m.set_model("qwen2.5:7b")                                            # /mentor wins
    assert m.model() == "qwen2.5:7b"
