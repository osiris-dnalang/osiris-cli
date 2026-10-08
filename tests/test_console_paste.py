"""Console regressions from the 2026-10-08 transcript: a long pasted document with no request, an excerpt
reported as if it were the whole message, a cut-off reply shown as complete, "learning from this" on a
paste, a bracketed-paste end marker shown as typing, and model-made status labels.

All fixtures here are synthetic: the original pasted document is not available as a verified local
artifact, and nothing below reconstructs it."""
import json
import socket

import pytest

from osiris_cli import living, osiris_repl
from osiris_cli.living import Held, Osiris

from tests.test_living import FakeCore, ScriptedMentor, make


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted during an offline test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def synthetic_document(target_chars=13000):
    """A long Markdown proposal: numbered sections, a code fence, Unicode, hypothetical overlap,
    negation, and a retracted constant mentioned critically. No request line."""
    sections = [
        "# Synthetic provenance proposal (test fixture)",
        "## 1. Scope\nThis proposal could apply to quantum records. It is not established policy.",
        "## 2. States\n```text\nPA-0 NOT_ASSESSED\nPA-1 POTENTIAL_OVERLAP\n```",
        "## 3. Comparison\nIf two artifacts share a constant, that is a potential technical overlap; it "
        "requires verification and is not an observed copy.",
        "## 4. Cautionary example\nThe 51.843° angle was never a resonance; it is listed only as retracted. "
        "Ψ, ℋ₈ and naïve café text keep their Unicode.",
    ]
    body = "\n\n".join(sections)
    filler = "\n\n## {n}. Background {n}\nParagraph {n} describes a possible procedure, if adopted later."
    n = 5
    while len(body) < target_chars:
        body += filler.format(n=n)
        n += 1
    return body


class LimitMentor(ScriptedMentor):
    """Streams its reply, then reports Ollama-style final-chunk fields."""

    def __init__(self, done=None, **kw):
        super().__init__(**kw)
        self.done = done or {}
        self.last_done = None

    def stream(self, messages, model=None):
        self.last_done = None
        yield from super().stream(messages, model)
        self.last_done = dict(self.done)


# ── a long paste with no request ─────────────────────────────────────────────

def test_a_long_paste_without_a_request_is_acknowledged_by_code(tmp_path):
    core, mentor = FakeCore(), ScriptedMentor()
    o, out = make(tmp_path, core=core, mentor=mentor)
    doc = synthetic_document()
    o.converse(doc, input_transport="bracketed_paste")
    text = "".join(out)
    assert mentor.calls == [] and core.learned == []                      # no model, no learning
    assert f"{len(doc):,} characters" in text and "## 2. States" in text
    assert "haven't reviewed, summarised or adopted" in text
    assert "voice: code, no model" in text and "not approved for learning; not adopted as policy" in text
    row = json.loads(open(o.log_path).read().splitlines()[-1])
    assert row["voice"] == "code" and row["learnable"] is False and row["user"] == doc and row["pasted"] is True
    assert "Claims register" in text and "θ_lock = 51.843° is a resonance" in text   # reference still shown


def test_a_follow_up_request_reaches_the_model_with_the_document(tmp_path):
    mentor = ScriptedMentor()
    o, out = make(tmp_path, mentor=mentor)
    o.converse(synthetic_document(), input_transport="bracketed_paste")
    o.converse("review section 3")
    sent = "".join(m["content"] for m in mentor.calls[0])
    assert "[Pasted document]" in sent and "## 1. Scope" in sent


def test_a_long_paste_with_a_request_goes_to_the_model_and_is_not_learned(tmp_path):
    core, mentor = FakeCore(), ScriptedMentor()
    o, out = make(tmp_path, core=core, mentor=mentor)
    o.converse("warm-up")
    o.converse(synthetic_document() + "\n\nPlease review this.", input_transport="bracketed_paste")
    assert len(mentor.calls) == 2 and core.learned == []
    assert "not learned: pasted transcript" in "".join(out)


@pytest.mark.parametrize("n,acknowledged", [(living.LONG_MESSAGE, False), (living.LONG_MESSAGE + 1, True)])
def test_the_acknowledgement_starts_just_above_the_long_message_boundary(tmp_path, n, acknowledged):
    mentor = ScriptedMentor()
    o, _ = make(tmp_path, mentor=mentor)
    o.converse(("a" * 79 + "\n") * (n // 80) + "a" * (n % 80), input_transport="bracketed_paste")
    assert (mentor.calls == []) is acknowledged


def test_headings_skip_code_blocks():
    doc = "# T\n## 1. A\n```\nPA-0 NOT_ASSESSED\n## not a heading\n```\n## 2. B\n"
    assert living.headings(doc) == ["# T", "## 1. A", "## 2. B"]


def test_request_detection_looks_at_the_ends_only():
    assert living.asks_something("Can you check this?\n" + "x\n" * 50)
    assert living.asks_something("x\n" * 50 + "Thoughts?")
    assert not living.asks_something("# Title\n## 1. Scope\n" + "Should it apply?\n" + "x\n" * 50)


# ── excerpts are reported as excerpts ────────────────────────────────────────

def test_the_footer_says_how_much_of_a_long_message_the_model_saw(tmp_path):
    o, out = make(tmp_path)
    o.converse("x" * 13024)                                               # typed: no acknowledgement
    assert ("long message: an excerpt was sent -- the first 4,000 and last 2,000 of 13,024 characters "
            "(7,024 left out, not read)") in "".join(out)


@pytest.mark.parametrize("n,cut", [(living.MESSAGE_BUDGET, False), (living.MESSAGE_BUDGET + 1, True)])
def test_excerpt_boundary(n, cut):
    text = "y" * n
    head, tail = Osiris.excerpt_sizes(text)
    assert (head + tail < n) is cut and (Osiris.excerpt(text) == text) is (not cut)


def test_the_model_is_told_to_keep_the_documents_hedges(tmp_path):
    mentor = ScriptedMentor()
    o, _ = make(tmp_path, mentor=mentor)
    o.converse(synthetic_document() + "\nPlease summarise it.", input_transport="bracketed_paste")
    assert "a possibility it describes is not a finding" in mentor.calls[0][-1]["content"]


# ── incomplete replies are marked and not learned ────────────────────────────

def test_a_reply_cut_at_the_token_limit_is_marked_and_not_learned(tmp_path):
    core = FakeCore()
    o, out = make(tmp_path, core=core, mentor=LimitMentor(done={"done_reason": "length"}, reply="PA-1 and PA-2 and"))
    o.converse("warm-up")
    o.converse("list the states")
    text = "".join(out)
    assert f"[incomplete: cut off at the {living.MENTOR_MAX_TOKENS}-token reply limit]" in text
    assert "not learned: incomplete reply" in text and core.learned == []
    assert json.loads(open(o.log_path).read().splitlines()[-1])["incomplete"].startswith("cut off")


def test_an_unclosed_code_block_is_marked_incomplete(tmp_path):
    core = FakeCore()
    o, out = make(tmp_path, core=core, mentor=ScriptedMentor(reply="```text PA-0 NOT_ASSESSED"))
    o.converse("warm-up")
    o.converse("show the states")
    assert "ends inside an unclosed code block" in "".join(out) and core.learned == []


def test_where_the_time_went_comes_from_the_models_own_counters(tmp_path):
    done = {"done_reason": "stop", "load_duration": 2.2e9, "prompt_eval_count": 3400,
            "prompt_eval_duration": 23.4e9, "eval_count": 400, "eval_duration": 40.1e9}
    o, out = make(tmp_path, mentor=LimitMentor(done=done))
    o.converse("hello there, how does the gate work")
    assert "(load 2 s, read 3400 tokens in 23 s, wrote 400 tokens in 40 s)" in "".join(out)


# ── labels the model introduces ──────────────────────────────────────────────

def test_status_labels_not_in_the_input_are_flagged(tmp_path):
    o, out = make(tmp_path, mentor=ScriptedMentor(reply="Result: NUMERICAL_OVERLAP = OBSERVED for both."))
    o.converse("is there a potential technical overlap between the two records?")
    assert ("labels in the reply that nothing it was sent contains: NUMERICAL_OVERLAP, OBSERVED"
            in "".join(out))


def test_a_label_the_model_made_up_earlier_is_still_flagged_later(tmp_path):
    mentor = ScriptedMentor(reply="NUMERICAL_OVERLAP = OBSERVED.")
    o, out = make(tmp_path, mentor=mentor)
    o.converse("first question")
    out.clear()
    o.converse("and now?")
    assert "NUMERICAL_OVERLAP" in "".join(m["content"] for m in mentor.calls[-1])   # in the history it was sent
    assert "nothing it was sent contains: NUMERICAL_OVERLAP, OBSERVED" in "".join(out)


def test_labels_that_were_in_the_input_are_not_flagged():
    sent = "states: POTENTIAL_OVERLAP and NOT_ASSESSED"
    assert living.invented_labels("It stays POTENTIAL_OVERLAP.", sent) == []
    assert living.invented_labels("Now OBSERVED_OVERLAP_WITH_EVIDENCE.", sent) == ["OBSERVED_OVERLAP_WITH_EVIDENCE"]


# ── what the learning footer says is what happens ────────────────────────────

def test_the_learning_note_matches_what_the_core_does(tmp_path):
    core = FakeCore()
    o, out = make(tmp_path, core=core)
    o.converse("first question")                                          # exchange 0: held out
    assert "held out: the core is scored on this exchange, not trained on it" in "".join(out)
    assert core.learned == []
    o.converse("second question")
    assert "the core trains on this exchange (your words and this reply)" in "".join(out)
    assert len(core.learned) == 1
    assert "learning from this" not in "".join(out)


def test_without_a_core_nothing_is_said_to_be_learned(tmp_path):
    out = []
    o = Osiris(core=None, mentor=ScriptedMentor(), home=str(tmp_path), out=out.append, background=False,
               knowledge=None, tty=False)
    o.converse("first question")
    o.converse("second question")
    assert "recorded; no core is loaded, so nothing is learned" in "".join(out)


def test_mentor_text_is_never_attributed_to_the_core(tmp_path):
    o, out = make(tmp_path)
    o.converse("what are you")
    text = "".join(out)
    assert "voice: qwen2.5:7b speaking for OSIRIS" in text and "OSIRIS core (" not in text


# ── bracketed paste ──────────────────────────────────────────────────────────

def _holder():
    o = Osiris.__new__(Osiris)
    o.held, out = [], []
    o.out = out.append
    return o, out


def test_a_paste_tail_without_its_start_is_held_as_a_paste_not_shown_as_typing():
    o, out = _holder()
    o._hold(living.keys_typed("last line of the pasted review\n\x1b[201~"))
    assert o.held == ["last line of the pasted review"] and o.held[0].pasted is True
    assert "you were typing" not in "".join(out) and "\\x1b" not in "".join(out)
    assert "arrived apart from the rest" in "".join(out)


def test_held_messages_carry_their_transport():
    o, _ = _holder()
    o._hold(living.keys_typed("typed line\n"))
    o._hold(living.keys_typed("\x1b[200~pasted\nblock\x1b[201~"))
    assert [(m, m.pasted) for m in o.held] == [("typed line", False), ("pasted\nblock", True)]


def _feed(chunks):
    """read/ready over a queue of (arrives_after_idle_wait, bytes)."""
    queue = list(chunks)

    def ready(timeout):
        return bool(queue) and (timeout > 0 or not queue[0][0])

    def read():
        return queue.pop(0)[1]
    return read, ready


def test_a_paste_split_across_reads_is_read_to_its_end_marker():
    read, ready = _feed([(False, b"\x1b[200~first part\n"), (True, b"middle\n"), (True, b"end\x1b[201~")])
    data = living.drain_input(read, ready)
    assert data == b"\x1b[200~first part\nmiddle\nend\x1b[201~"
    o, out = _holder()
    o._hold(living.keys_typed(data.decode()))
    assert o.held == ["first part\nmiddle\nend"] and out == []           # one message, no fragment note


def test_draining_stops_when_input_goes_quiet_or_the_cap_passes():
    read, ready = _feed([(False, b"\x1b[200~partial")])
    assert living.drain_input(read, ready) == b"\x1b[200~partial"         # quiet: returns what arrived
    t = iter(range(0, 1000, 10))
    read, ready = _feed([(False, b"\x1b[200~a")] + [(True, b"b")] * 50)
    data = living.drain_input(read, ready, clock=lambda: next(t), wait_max=15)
    assert data.count(b"b") < 50                                          # bounded by wait_max
    read, ready = _feed([(False, b"plain typing\n"), (True, b"later")])
    assert living.drain_input(read, ready) == b"plain typing\n"           # no paste: no waiting


def test_a_held_multiline_paste_goes_to_the_conversation_not_the_command_router(monkeypatch):
    seen = []
    monkeypatch.setattr(osiris_repl, "handle_livlm_prompt", lambda state, text: seen.append(("talk", text)))
    monkeypatch.setattr(osiris_repl, "safe_dispatch", lambda state, text: seen.append(("dispatch", text)))
    osiris_repl.dispatch_held(None, Held("/apply\nthis is a pasted log, not a command", pasted=True))
    osiris_repl.dispatch_held(None, Held("/status"))
    osiris_repl.dispatch_held(None, Held("/status", pasted=True))           # a one-line paste may be a command
    assert seen == [("talk", "/apply\nthis is a pasted log, not a command"), ("dispatch", "/status"),
                    ("dispatch", "/status")]


def test_ollama_stream_keeps_the_final_chunk(monkeypatch):
    lines = [json.dumps({"message": {"content": "Hi"}, "done": False}).encode(),
             json.dumps({"message": {"content": ""}, "done": True, "done_reason": "length",
                         "eval_count": 700}).encode()]

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __iter__(self):
            return iter(lines)
    monkeypatch.setattr(living.urllib.request, "urlopen", lambda req, timeout=None: Resp())
    m = living.OllamaMentor(model="qwen2.5:1.5b")
    assert "".join(m.stream([{"role": "user", "content": "x"}], model="qwen2.5:1.5b")) == "Hi"
    assert m.last_done == {"done": True, "done_reason": "length", "eval_count": 700}
