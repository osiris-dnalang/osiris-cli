"""OSIRIS as a conversation: the living language model you talk to.

Every plain-text message goes here. OSIRIS answers in one of two voices, and
always says which:

  core    OSIRIS's own model (osiris.nclm, the same checkpoint the phone's
          Engine 3 trains in ~/.osiris/nclm_organism). It speaks only after it
          has earned it on held-out conversation (the speaking gate below).
  mentor  a local Ollama model, streaming, with the conversation history.
          Used while the core has not earned the gate, or when it fails.

Every exchange is a lesson. After a mentor reply, a background thread first
measures how well the core would have predicted that reply (bits per byte,
teacher-forced) and then trains the core on it. Every HELDOUT_EVERY-th
exchange is held out: measured, never trained on, so the gate is judged on
text the core has not seen -- the same discipline as NCLM-1 and nclm_eval.py.

Nothing here is simulated. If no voice can answer, OSIRIS says so.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Any, Callable, Dict, Iterator, List, Optional

LIVING_HOME = os.path.join(os.path.expanduser("~"), ".osiris", "living")
OLLAMA_BASE = os.environ.get("OSIRIS_OLLAMA", "http://localhost:11434").rstrip("/")

# Speaking gate: the core answers in its own voice only when, over the last
# GATE_WINDOW held-out exchanges, its mean bits/byte is at or below
# SPEAK_BPB and below the unigram baseline scored on the same text. A byte
# unigram sits near 4.5 bpb on English; ~2.0 is where byte models start to
# produce readable text. Changing these numbers changes what "earned" means,
# so change them deliberately, not to make the gate open.
GATE_WINDOW = 30
SPEAK_BPB = 2.0
HELDOUT_EVERY = 5
TRAIN_STEPS_PER_EXCHANGE = 3
SCORE_WINDOWS = 2
HISTORY_TURNS = 12
# One note per message: each costs ~230 tokens, and the 7B reads new tokens at ~14/s here
# (measured 2026-10-02), so three notes alone held a reply back ~50 s. The pre-registered
# results are already in the system prompt (knowledge.brief). OSIRIS_NOTES raises it.
NOTES_PER_MESSAGE = int(os.environ.get("OSIRIS_NOTES", "1"))
RECALL_EXCHANGES = 6      # earlier conversation carried into a new session
FACTS_FILE = "facts.jsonl"
# While a chat is live the batch trainer's distillation (which runs the same
# 7B mentor on the same CPU) waits; the marker is refreshed on every message.
CHAT_MARKER = "chat.active"
CHAT_QUIET_SECONDS = 300
MENTOR_MAX_TOKENS = int(os.environ.get("OSIRIS_MENTOR_MAX_TOKENS", "700"))
MENTOR_TIMEOUT = float(os.environ.get("OSIRIS_MENTOR_TIMEOUT", "180"))
CLAIMS_PER_MESSAGE = 3          # registered claims shown before a reply
MENTOR_NUM_CTX = int(os.environ.get("OSIRIS_MENTOR_NUM_CTX", "4096"))
# A local 7B model on a CPU reads a few thousand tokens per minute and Ollama keeps only
# num_ctx tokens: a 100k-character paste timed out twice (601 s, 406 s) on 2026-10-01.
# Long messages go to the mentor as a bounded excerpt; the ledger keeps the full text.
LONG_MESSAGE = 3000
MESSAGE_BUDGET = 6000
# The voice: /mentor NAME, else OSIRIS_VOICE, else the first of these that is installed.
# OSIRIS_CHAT_MODEL is the console's Architect (intent -> spec), not the voice: it is
# exported in the shell for the Architect, so reading it here pinned the voice too.
# qwen2.5:3b first, measured 2026-10-03 on this desktop with notes and probes attached as
# in the REPL: first words at 47, 26 and 47 s over a three-question conversation, where
# qwen2.5:7b timed out (180 s) on two of the three and took 140 s on the third. The 3B adds
# new prompt tokens at ~30/s against the 7B's ~14/s. Both misstate recorded results at
# times, which is why named verdicts and the claims register are printed by code first.
MENTOR_PREFERENCE = ("qwen2.5:3b", "qwen2.5:7b", "qwen2.5:1.5b", "llama3.2:3b", "llama3.2:1b", "smollm2:360m")
# Measured 2026-10-02 on the 8-core WSL desktop: qwen2.5:7b reads a prompt at ~26 tokens/s
# after a 17 s cold load; qwen2.5:1.5b at ~146 tokens/s. With the system prompt a long
# message is ~14k characters (~4k tokens): ~170 s before the 7B says anything, so both
# pastes on 2026-10-01 hit the 180 s timeout. Long messages go to the fast voice, and a
# mentor that fails before its first word hands the message to it. A voice pinned with
# /mentor NAME is never swapped; OSIRIS_FAST_MENTOR= (empty) turns the fast voice off.
FAST_MENTOR = os.environ.get("OSIRIS_FAST_MENTOR", "qwen2.5:1.5b")
# Ollama keeps what it last read and re-reads only what changed, but each new token is
# slow: measured 2026-10-02, 150 words after a cached 1,400-token system prompt took 4.5 s
# on qwen2.5:1.5b and ~5x that on the 7B. So the conversation is re-sent exactly as it
# was sent (each turn adds only its own message) and the system prompt is read once at
# start-up (prewarm). PROMPT_BUDGET is what one prompt may hold, at ~3.5 characters per
# token (the 5,356-character system prompt is ~1,420 tokens), leaving room for the reply.
PROMPT_BUDGET = int((MENTOR_NUM_CTX - MENTOR_MAX_TOKENS) * 3.5)
FIRST_WORD_SAMPLES = 10
# Greetings and thanks are answered by code at once. "ok", "cool" and "great" are not:
# after a question from OSIRIS they are answers, and a canned "Okay." would drop them.
# Bracketed paste (DECSET 2004, turned on by the REPL): a paste arrives between these.
PASTE_START, PASTE_END = "\x1b[200~", "\x1b[201~"
# A paste still arriving when a reply ends is read to its end marker: input must go quiet for
# PASTE_IDLE seconds (or PASTE_WAIT_MAX pass) before the rest is left for the prompt to read.
PASTE_IDLE, PASTE_WAIT_MAX = 1.0, 15.0


class Held(str):
    """A message typed or pasted while OSIRIS was answering, sent next. `pasted` travels with
    it so the REPL does not classify it by the previous prompt's input (2026-10-08: a document
    pasted during a reply was dispatched as typed and trained on)."""
    pasted: bool = False

    def __new__(cls, text: str, pasted: bool = False):
        s = super().__new__(cls, text)
        s.pasted = pasted
        return s


# A long paste with no request in its first or last lines is acknowledged by code, not restated
# by a model (2026-10-08: a pasted policy proposal was "restated" from an excerpt, cut off, and
# a "potential overlap" came back as NUMERICAL_OVERLAP = OBSERVED).
REQUEST = re.compile(r"\?|\b(?:review|summari[sz]e|rewrite|compare|check|critique|evaluate|assess|explain|"
                     r"analy[sz]e|adopt|apply|translate|what do you think|thoughts|tell me|can you|could you|"
                     r"please)\b", re.IGNORECASE)
HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s+\S.*|(?:\d+(?:\.\d+)*[.)]|[A-Z]{1,4}-\d+[:.)]?)\s+\S.*)$")
# Status-like labels (NUMERICAL_OVERLAP, "= OBSERVED") a reply uses that nothing it was sent contains.
LABEL = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|(?<==\s)[A-Z][A-Z_]{3,}\b")


def asks_something(text: str) -> bool:
    """Whether a pasted document carries a request: in its first two or last three non-empty lines."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return any(REQUEST.search(ln) for ln in lines[:2] + lines[-3:])


def headings(text: str, limit: int = 12) -> List[str]:
    """Section headings of a pasted document, outside code blocks."""
    out, fenced = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and HEADING.match(ln):
            out.append(ln.strip()[:70])
    return out[:limit]


def invented_labels(reply: str, sent: str) -> List[str]:
    """Labels in a reply that appear nowhere in what the model was sent. Not a fact check: a
    flag that the model introduced status names of its own."""
    known = set(re.findall(r"[A-Za-z0-9_]+", sent))
    return sorted({m.group(0) for m in LABEL.finditer(reply)} - known)


def drain_input(read: Callable[[], bytes], ready: Callable[[float], bool], clock: Callable[[], float] = time.time,
                idle: float = PASTE_IDLE, wait_max: float = PASTE_WAIT_MAX) -> bytes:
    """Everything waiting on input now; and if a bracketed paste has started but not ended, keep
    reading until its end marker, a quiet `idle`, or `wait_max` -- so one paste stays one message."""
    data = b""
    try:
        while ready(0):
            chunk = read()
            if not chunk:
                return data
            data += chunk
        start, end = PASTE_START.encode(), PASTE_END.encode()
        t0 = clock()
        while data.count(start) > data.count(end) and clock() - t0 < wait_max:
            if not ready(idle):
                break
            chunk = read()
            if not chunk:
                break
            data += chunk
    except OSError:
        pass                                    # keep what was read
    return data
SMALL_TALK = re.compile(r"^\s*(?:(?P<hello>hi|hello|hey|yo|gm|good (?:morning|afternoon|evening))|"
                        r"(?P<thanks>thanks|thank you))\b", re.IGNORECASE)

IDENTITY = """You are OSIRIS, the living language model being built by Devin Phillip Davis \
(Agile Defense Systems). You are talking with Devin or someone working with him.

How you exist right now: OSIRIS has its own small core model that records every \
exchange; learns only from eligible material you explicitly approve. Until that \
core has earned the right to answer on its own, you (a local mentor model) speak \
for OSIRIS, and the core trains on what you say. Speak as OSIRIS, in first \
person, warmly and directly, like a thoughtful research partner.

Honesty rules, which matter more than sounding impressive:
- Never invent results, measurements, job IDs, DOIs, file contents or test outcomes. \
If you do not know, say so and say how it could be checked.
- Keep hypotheses and measured results clearly separate.
- Don't say you have learned, remembered or kept up with Devin's work unless a note, a recall \
line or a check in this message shows it. What is measured about your learning (pilot, \
2026-10-01): training on conversations lowers the core's error on held-out replies by about \
0.07 bits/byte, and the core is still worse than a simple letter-frequency model.
- Devin's own hardware audits refuted the tau-phase anomaly, theta_lock = 51.843 deg, \
the 10^6 suppression and the CCCE "consciousness" metrics; do not present them as \
established. His measured work (staggered dynamical decoupling, GHZ witnesses, the \
pre-registered organism_sim/bridge results, the write-ahead ledger) is real.
- Before you answer, OSIRIS's own code may run read-only checks (training status, git \
history, the exchange ledger, system load, the pre-registered results files with their \
hashes, a file Devin names) and attach the output under \
[Checked just now]. That output is real: quote it and say which check it came from. You \
cannot change files, run experiments or submit jobs yourself; for those, name the command \
Devin would run.
- Facts about Devin's work come from the brief below and from the notes attached to a \
message. When you use a note, name its file. If neither covers the question, say you \
don't have it on record rather than guessing.

How to talk:
- Answer the question that was asked, first, in plain words. Default to a few short \
paragraphs; go longer only when asked.
- Greet once at most. Don't repeat Devin's name every turn, don't thank him for his work, \
and don't end with offers like "How can I assist you today?" or a list of topics to explore.
- "What do you know" or "tell me about yourself" means: say concretely what you are right \
now (your core's step and gate, who is speaking) and what is on record (the results below)."""


# ---------------------------------------------------------------------------
# Mentor voice (Ollama)
# ---------------------------------------------------------------------------

class OllamaMentor:
    """Streams chat replies from a local Ollama model."""

    def __init__(self, base: str = OLLAMA_BASE, model: Optional[str] = None, timeout: float = MENTOR_TIMEOUT):
        self.base = base
        self.timeout = timeout
        self._model = model
        # Ollama's final chunk of the last stream: done_reason ("stop" or "length") and its
        # timings (load_duration, prompt_eval_count/_duration, eval_count/_duration, in ns).
        self.last_done: Optional[Dict[str, Any]] = None

    def installed(self) -> List[str]:
        try:
            with urllib.request.urlopen(self.base + "/api/tags", timeout=2.0) as r:
                return [m["name"] for m in json.load(r).get("models", [])]
        except (OSError, ValueError, KeyError):
            return []

    def model(self) -> Optional[str]:
        installed = self.installed()
        if not installed:
            return None
        wanted = self._model or os.environ.get("OSIRIS_VOICE")
        if wanted and wanted in installed:
            return wanted
        for name in MENTOR_PREFERENCE:
            if name in installed:
                return name
        return installed[0]

    def set_model(self, name: Optional[str]) -> None:
        self._model = name

    def fast_model(self) -> Optional[str]:
        """The quicker voice (FAST_MENTOR) if installed and no voice is pinned."""
        if self._model or not FAST_MENTOR:
            return None
        return FAST_MENTOR if FAST_MENTOR in self.installed() else None

    def unload(self, model: Optional[str] = None) -> None:
        """Ask Ollama to free the model's memory now (used before batch training)."""
        model = model or self.model()
        if model is None:
            return
        req = urllib.request.Request(self.base + "/api/generate",
                                     data=json.dumps({"model": model, "keep_alive": 0}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except OSError:
            pass

    def warm(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> None:
        """Loads the model and reads `messages` into its cache, generating one token.
        Same num_ctx as stream(): a different one makes Ollama reload the model."""
        model = model or self.model()
        if model is None:
            return
        payload = json.dumps({"model": model, "messages": messages, "stream": False,
                              "options": {"num_predict": 1, "num_ctx": MENTOR_NUM_CTX}}).encode()
        req = urllib.request.Request(self.base + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=max(self.timeout, 300)).read()

    def stream(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Iterator[str]:
        model = model or self.model()
        if model is None:
            raise ConnectionError(f"no Ollama model reachable at {self.base}")
        payload = json.dumps({"model": model, "messages": messages, "stream": True,
                              "options": {"num_predict": MENTOR_MAX_TOKENS, "num_ctx": MENTOR_NUM_CTX}}).encode()
        req = urllib.request.Request(self.base + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
        self.last_done = None
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise ConnectionError(chunk["error"])
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if chunk.get("done"):
                    self.last_done = {k: v for k, v in chunk.items() if k != "message"}
                    return


# ---------------------------------------------------------------------------
# Core voice (osiris.nclm organism)
# ---------------------------------------------------------------------------

class NclmCore:
    """OSIRIS's own model: the shared Engine 3 checkpoint, trained per exchange.

    Uses the console's build/load/save and lock so the desktop and the phone
    train one organism with one checkpoint format.
    """

    name = "osiris.nclm"

    def __init__(self, console):
        self._otc = console

    def _paths(self):
        return self._otc._organism_checkpoint_paths()

    def _disk_step(self) -> int:
        try:
            with open(self._paths()[1], encoding="utf-8") as f:
                return int(json.load(f).get("step", 0))
        except (OSError, ValueError):
            return 0

    def _model(self):
        """The in-memory organism, reloaded if a trainer has saved a newer one."""
        st = self._otc._organism_state
        if st["model"] is None or self._disk_step() > st["step"]:
            model, optimizer = self._otc._organism_build()
            step, history = self._otc._organism_load(model, optimizer)
            st.update(model=model, optimizer=optimizer, step=step, history=history)
        return st

    def lock_path(self) -> str:
        return os.path.join(os.path.dirname(self._paths()[0]), "train.lock")

    def training_locked(self) -> bool:
        """True while a batch trainer owns the checkpoint (a live pid in train.lock)."""
        try:
            with open(self.lock_path(), encoding="utf-8") as f:
                pid = int(json.load(f)["pid"])
            os.kill(pid, 0)
            return pid != os.getpid()
        except (OSError, ValueError, KeyError):
            return False

    def step(self) -> int:
        with self._otc._organism_lock:
            return int(self._model()["step"])

    def _windows(self, text: str, limit: int):
        import numpy as np
        data = np.frombuffer(text.encode("utf-8", errors="ignore"), dtype=np.uint8).astype(np.int64)
        span = self._otc.ORGANISM_GEOMETRY["max_seq_len"]
        out = []
        for start in range(0, max(0, len(data) - 1), span - 1):
            chunk = data[start:start + span]
            if len(chunk) >= 8:
                out.append((chunk[:-1][None, :], chunk[1:][None, :]))
            if len(out) >= limit:
                break
        return out

    def bits_per_byte(self, text: str) -> Optional[float]:
        from osiris.nclm import cross_entropy_loss
        from osiris.nclm.autograd import no_grad
        with self._otc._organism_lock:
            model = self._model()["model"]
            total, n = 0.0, 0
            with no_grad():
                for x, y in self._windows(text, SCORE_WINDOWS):
                    total += float(cross_entropy_loss(model.forward(x), y).data) * y.shape[1]
                    n += y.shape[1]
        return total / n / math.log(2) if n else None

    def learn(self, text: str, steps: int) -> Optional[float]:
        import random
        from osiris.nclm import cross_entropy_loss
        from osiris.nclm.autograd import clip_grad_norm
        windows = self._windows(text, 64)
        if not windows or self.training_locked():
            return None  # the lesson stays in the exchange log; the batch trainer replays it
        with self._otc._organism_lock:
            st = self._model()
            model, opt = st["model"], st["optimizer"]
            loss = None
            for _ in range(steps):
                x, y = random.choice(windows)
                opt.zero_grad()
                out = cross_entropy_loss(model.forward(x), y)
                out.backward()
                clip_grad_norm(model.parameters(), 1.0)
                opt.step()
                loss = float(out.data)
                st["step"] += 1
                st["history"].append(loss)
            self._otc._organism_save(model, opt, st["step"], st["history"], rotate=(st["step"] % 25 == 0))
        return loss

    # -- batch training (osiris_cli.train) --------------------------------

    def restart_schedule(self, total_steps: int, warmup_steps: int = 50) -> None:
        """Warm restart of the cosine schedule for one batch run."""
        from osiris.nclm import LRSchedule
        with self._otc._organism_lock:
            opt = self._model()["optimizer"]
            opt.schedule = LRSchedule(warmup_steps=opt.step_count + warmup_steps,
                                      total_steps=opt.step_count + max(total_steps, warmup_steps + 1))

    def train_batch(self, x, y) -> float:
        from osiris.nclm import cross_entropy_loss
        from osiris.nclm.autograd import clip_grad_norm
        with self._otc._organism_lock:
            st = self._model()
            model, opt = st["model"], st["optimizer"]
            opt.zero_grad()
            out = cross_entropy_loss(model.forward(x), y)
            out.backward()
            clip_grad_norm(model.parameters(), 1.0)
            opt.step()
            st["step"] += 1
            st["history"].append(float(out.data))
            return float(out.data)

    def eval_batch(self, x, y) -> float:
        """Mean loss in nats per byte, no training."""
        from osiris.nclm import cross_entropy_loss
        from osiris.nclm.autograd import no_grad
        with self._otc._organism_lock:
            model = self._model()["model"]
            with no_grad():
                return float(cross_entropy_loss(model.forward(x), y).data)

    def save(self, rotate: bool = False) -> None:
        with self._otc._organism_lock:
            st = self._model()
            self._otc._organism_save(st["model"], st["optimizer"], st["step"], st["history"], rotate=rotate)

    def _best_paths(self):
        ckpt, meta = self._paths()
        return ckpt[:-4] + ".best.npz", meta[:-5] + ".best.json"

    def save_best(self) -> None:
        """Keep a copy of the current weights as the best held-out checkpoint."""
        import shutil
        self.save()
        with self._otc._organism_lock:
            for src, dst in zip(self._paths(), self._best_paths()):
                shutil.copy2(src, dst)

    def restore_best(self) -> Optional[int]:
        """Make the best held-out checkpoint the live one again. It is written as a
        newer step so any process holding the worse weights in memory reloads it
        instead of saving over it. Returns the step the weights came from."""
        import shutil
        best_ckpt, best_meta = self._best_paths()
        if not (os.path.exists(best_ckpt) and os.path.exists(best_meta)):
            return None
        newer = max(self._disk_step(), self.step()) + 1   # before the lock: step() takes it
        with self._otc._organism_lock:
            ckpt, meta = self._paths()
            with open(best_meta, encoding="utf-8") as f:
                info = json.load(f)
            best_step = int(info.get("step", 0))
            shutil.copy2(best_ckpt, ckpt)
            info.update(step=newer, restored_from_step=best_step)
            with open(meta, "w", encoding="utf-8") as f:
                json.dump(info, f)
            self._otc._organism_state["model"] = None
        return best_step

    def current_lr(self) -> float:
        opt = self._model()["optimizer"]
        sched = getattr(opt, "schedule", None)
        return sched.get_lr(opt.step_count, opt.base_lr) if sched else opt.base_lr

    def draft(self, prompt: str, max_bytes: int = 160) -> str:
        with self._otc._organism_lock:
            model = self._model()["model"]
            text = model.generate(prompt, max_new_tokens=max_bytes, temperature=0.7, top_k=40)
        reply = text[len(prompt):] if text.startswith(prompt) else text
        return reply.split("\nUser:")[0].strip()


def printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    ok = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
    return ok / len(text)


class TypeAhead:
    """While a reply streams, keys typed are captured instead of echoed into the
    reply (2026-09-29: questions typed during a slow reply appeared after
    'OSIRIS ›' and each answer looked one turn late). Ctrl-C still works.
    Not a terminal: does nothing."""

    def __init__(self, active: bool):
        self.active, self.text, self._saved = active, "", None

    def __enter__(self):
        if self.active:
            try:
                import termios
                fd = sys.stdin.fileno()
                self._saved = termios.tcgetattr(fd)
                new = termios.tcgetattr(fd)
                new[3] &= ~(termios.ECHO | termios.ICANON)
                termios.tcsetattr(fd, termios.TCSANOW, new)
            except (ImportError, OSError, ValueError, AttributeError):
                self._saved = None
        return self

    def __exit__(self, *exc):
        if self._saved is None:
            return False
        import select
        import termios
        fd = sys.stdin.fileno()
        data = b""
        try:
            data = drain_input(lambda: os.read(fd, 4096), lambda t: bool(select.select([fd], [], [], t)[0]))
        except OSError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, self._saved)
        self.text = keys_typed(data.decode("utf-8", errors="replace"))
        return False


def keys_typed(raw: str) -> str:
    """What raw terminal input says was typed: backspaces applied, control bytes
    dropped, bracketed-paste markers kept so a paste can be told from typing."""
    kept: List[str] = []
    i = 0
    while i < len(raw):
        marker = next((m for m in (PASTE_START, PASTE_END) if raw.startswith(m, i)), None)
        if marker:
            kept.append(marker)
            i += len(marker)
            continue
        ch = raw[i]
        i += 1
        if ch in "\x7f\x08":
            if kept and kept[-1] not in ("\n", "\r", PASTE_START, PASTE_END):
                kept.pop()
        elif ch in "\n\r" or ch.isprintable():
            kept.append(ch)
    return "".join(kept)


class Waiting:
    """'(thinking · qwen2.5:7b · usually ~20 s · 12 s)', redrawn each second until
    the first word arrives, so a slow reply is visibly one. Not a terminal: does nothing."""

    def __init__(self, out: Callable[[str], None], label: Callable[[], str], active: bool):
        self.out, self.label, self.active = out, label, active
        self.started = time.time()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "Waiting":
        self.started = time.time()
        if self.active:
            self._stop.clear()
            self._draw()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def _draw(self) -> None:
        self.out(f"\r\x1b[KOSIRIS › \x1b[2m({self.label()} · {time.time() - self.started:.0f} s)\x1b[0m")

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            self._draw()

    def stop(self) -> None:
        """Back to a bare 'OSIRIS › ' for the reply."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            self._thread = None
            self.out("\r\x1b[KOSIRIS › ")


# ---------------------------------------------------------------------------
# The organism you talk to
# ---------------------------------------------------------------------------

class Osiris:
    def __init__(self, core=None, mentor=None, home: str = LIVING_HOME,
                 out: Callable[[str], None] = None, background: bool = True,
                 knowledge=None, tty: Optional[bool] = None, probes=None, claims_register: bool = True,
                 small_talk: Optional[Callable[[str], bool]] = None):
        self.core = core
        self.small_talk = small_talk   # True for a message that is only a greeting or thanks
        self.claims_register = claims_register
        self._claims_hit: list = []
        self._on_record: List[str] = []
        self.mentor = mentor or OllamaMentor()
        self.home = home
        self.out = out or (lambda s: print(s, end="", flush=True))
        self.background = background
        self.knowledge = knowledge
        self.probes = probes
        self.tty = sys.stdout.isatty() and sys.stdin.isatty() if tty is None else tty
        self.held: List[str] = []   # lines typed while OSIRIS was answering, sent next
        self.history: List[Dict[str, str]] = []
        os.makedirs(home, exist_ok=True)
        self.stats_path = os.path.join(home, "stats.json")
        self.log_path = os.path.join(home, "exchanges.jsonl")
        self.stats = self._load_stats()
        self.recall = self._recall()   # fixed for the session: keeps the system prompt stable
        self._pending: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._voices: set = set()   # mentor models this session used; finish() unloads them
        self._sent: List[Dict[str, str]] = []   # earlier turns exactly as the mentor was sent them
        self._warm: Optional[threading.Thread] = None
        self.last_paste: Optional[Dict[str, Any]] = None

    # -- persistence -------------------------------------------------------

    def _load_stats(self) -> dict:
        try:
            with open(self.stats_path, encoding="utf-8") as f:
                s = json.load(f)
        except (OSError, ValueError):
            s = {}
        s.setdefault("exchanges", 0)
        s.setdefault("core_spoke", 0)
        # exchange hash -> [core_bpb, unigram_bpb, core_step, exchange_index]; a
        # batch trainer rescoring with newer weights replaces an entry (higher step).
        s.setdefault("heldout_scores", {})
        s.pop("heldout", None)
        s.setdefault("unigram", {})       # byte -> count, train text only
        s.setdefault("last_head", "0" * 64)
        s.setdefault("first_word", {})    # model -> seconds to its first word, latest last
        return s

    def _save_stats(self) -> None:
        with self._lock:
            try:  # merge scores another process (the batch trainer) wrote meanwhile
                with open(self.stats_path, encoding="utf-8") as f:
                    disk = json.load(f).get("heldout_scores", {})
            except (OSError, ValueError):
                disk = {}
            mine = self.stats["heldout_scores"]
            for key, val in disk.items():
                if key not in mine or val[2] > mine[key][2]:
                    mine[key] = val
            tmp = self.stats_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.stats, f)
            os.replace(tmp, self.stats_path)

    def _record(self, entry: dict) -> str:
        entry["prev"] = self.stats["last_head"]
        body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(body.encode()).hexdigest()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.stats["last_head"] = entry["hash"]
        return entry["hash"]

    # -- the gate ----------------------------------------------------------

    def unigram_bpb(self, text: str) -> float:
        counts = self.stats["unigram"]
        total = sum(counts.values()) + 256
        data = text.encode("utf-8", errors="ignore")
        if not data:
            return 8.0
        nats = sum(-math.log((counts.get(str(b), 0) + 1) / total) for b in data)
        return nats / len(data) / math.log(2)

    def gate(self) -> dict:
        recent = sorted(self.stats["heldout_scores"].values(), key=lambda r: r[3])[-GATE_WINDOW:]
        n = len(recent)
        core = sum(r[0] for r in recent) / n if n else None
        uni = sum(r[1] for r in recent) / n if n else None
        open_ = n >= GATE_WINDOW and core is not None and core <= SPEAK_BPB and core < uni
        return {"open": open_, "n": n, "core_bpb": core, "unigram_bpb": uni}

    @staticmethod
    def gate_note(gate: dict) -> str:
        """Why the core is or is not speaking, in one clause."""
        if gate["open"]:
            return "gate open"
        if not gate["n"]:
            return "gate closed: not scored on held-out text yet"
        return (f"gate closed: {gate['core_bpb']:.2f} bits/byte on {gate['n']}/{GATE_WINDOW} held-out "
                f"(unigram {gate['unigram_bpb']:.2f}; speaks at <= {SPEAK_BPB})")

    @staticmethod
    def gate_brief(gate: dict) -> str:
        if gate["open"]:
            return "gate open"
        if not gate["n"]:
            return "gate closed, not scored yet"
        return f"gate closed ({gate['core_bpb']:.2f} bits/byte held-out; speaks at <= {SPEAK_BPB})"

    # -- how long replies take ---------------------------------------------

    def typical_first_word(self, model: str) -> Optional[float]:
        """Median seconds to this model's first word over its recent replies here."""
        times = sorted(self.stats["first_word"].get(model, []))
        return times[len(times) // 2] if len(times) >= 3 else None

    def _typical(self, model: str) -> str:
        t = self.typical_first_word(model)
        return f" · usually ~{t:.0f} s" if t is not None else ""

    def _note_first_word(self, model: str, seconds: float) -> None:
        times = self.stats["first_word"].get(model, []) + [round(seconds, 1)]
        self.stats["first_word"][model] = times[-FIRST_WORD_SAMPLES:]

    def prewarm(self) -> Optional[str]:
        """Loads the mentor and reads the system prompt into its cache in the
        background, so the first reply re-reads only its own message (~1,400 tokens
        fewer: ~50 s on this machine's 7B). Not while a batch trainer runs. Returns
        the model being warmed, or None."""
        warm = getattr(self.mentor, "warm", None)
        model = self.mentor.model() if warm is not None and not self._trainer_running() else None
        if model is None:
            return None
        messages = [{"role": "system", "content": self.system_prompt()}, {"role": "user", "content": "hello"}]

        def work():
            try:
                warm(messages, model)
            except (OSError, ValueError):
                pass   # the first reply just reads everything itself
        self._voices.add(model)
        self._warm = threading.Thread(target=work, daemon=True)
        self._warm.start()
        return model

    # -- conversation ------------------------------------------------------

    @staticmethod
    def _transcript(history: List[Dict[str, str]]) -> str:
        return "".join(f"{'User' if m['role'] == 'user' else 'OSIRIS'}: {m['content']}\n"
                       for m in history)

    @staticmethod
    def excerpt_sizes(text: str, budget: int = MESSAGE_BUDGET):
        """(head, tail): how many characters of a message the model is given from each end."""
        if len(text) <= budget:
            return len(text), 0
        return budget * 2 // 3, budget // 3

    @staticmethod
    def excerpt(text: str, budget: int = MESSAGE_BUDGET) -> str:
        """Head and tail of a long message, with what was left out stated in it."""
        if len(text) <= budget:
            return text
        h, t = Osiris.excerpt_sizes(text, budget)
        head, tail = text[:h], text[-t:]
        return (f"{head}\n\n[... {len(text) - len(head) - len(tail):,} characters of this {len(text):,}-character "
                f"message omitted: too long for the local model ...]\n\n{tail}")

    @staticmethod
    def timing_detail(done: Dict[str, Any]) -> str:
        """Where the time went, from Ollama's own final-chunk counters (absent: nothing said)."""
        ns = 1e9
        parts = []
        if done.get("load_duration"):
            parts.append(f"load {done['load_duration'] / ns:.0f} s")
        if done.get("prompt_eval_duration"):
            parts.append(f"read {done.get('prompt_eval_count', '?')} tokens in {done['prompt_eval_duration'] / ns:.0f} s")
        if done.get("eval_duration"):
            parts.append(f"wrote {done.get('eval_count', '?')} tokens in {done['eval_duration'] / ns:.0f} s")
        return f" ({', '.join(parts)})" if parts else ""

    def _document_reply(self, text: str, gate: dict) -> str:
        """A long paste with no request: acknowledged by code, with nothing reviewed, restated,
        adopted or learned. The excerpt stays in the conversation, so a follow-up request
        ("review it") reaches the model with it."""
        heads = headings(text)
        shown = "".join(f"\n    {h}" for h in heads)
        more = " (first 12)" if len(heads) == 12 else ""
        reply = (f"I have your pasted document: {len(text):,} characters, {len(text.splitlines()):,} lines"
                 + (f", sections{more}:{shown}\n" if heads else ".\n")
                 + "You didn't say what to do with it, so I haven't reviewed, summarised or adopted any of it. "
                   "Tell me which: review it, summarise it, compare it with something on record, or something "
                   f"else. A local model reads at most {MESSAGE_BUDGET:,} characters of it at once "
                   "(the beginning and the end); say if you want a particular section.")
        self.out(f"\nOSIRIS › {reply}\n  · voice: code, no model · instant · recorded; pasted, not approved "
                 f"for learning; not adopted as policy · core step {self._core_step()}, {self.gate_brief(gate)}\n")
        user = {"role": "user", "content": "[Pasted document]\n" + self.excerpt(text)}
        self.history.append({"role": "assistant", "content": reply})
        self._sent += [user, {"role": "assistant", "content": reply}]
        self._record({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "voice": "code", "heldout": False,
                      "learnable": False, "user": text, "reply": reply, "index": None,
                      "input_transport": "bracketed_paste", "source_type": "bracketed_paste", "pasted": True,
                      "char_count": len(text), "line_count": len(text.splitlines())})
        self._save_stats()
        return reply

    def converse(self, text: str, learnable: bool = True,
                 source_type: Optional[str] = None,
                 input_transport: Optional[str] = None) -> str:
        self.history.append({"role": "user", "content": self.excerpt(text)})
        self.history = self.history[-2 * HISTORY_TURNS:]
        gate = self.gate()
        voice, reply, interrupted = None, "", False
        self._claims_hit = []
        if self.claims_register:
            # Code answers first: a registered claim's verdict needs no model, so it is shown at
            # once, and the model (if one speaks) is held to it.
            from osiris_cli import claims as claims_mod
            self._claims_hit = claims_mod.match(text, limit=CLAIMS_PER_MESSAGE)
            if self._claims_hit:
                self.out("\n" + claims_mod.console_block(self._claims_hit))

        self._on_record = self.knowledge.on_record(text[:LONG_MESSAGE]) \
            if self.knowledge is not None and hasattr(self.knowledge, "on_record") else []
        if self._on_record:
            # Code states a named experiment's recorded verdict at once; the model is held to it.
            self.out("\nOn record (pre-registered scorecard, generated from results/ and test-guarded):\n"
                     + "\n".join("  " + r for r in self._on_record) + "\n")

        if not self._claims_hit and self.small_talk is not None and SMALL_TALK.match(text) \
                and self.small_talk(text):
            return self._small_talk_reply(text, gate)

        resolved_transport = input_transport or (
            source_type if source_type in ("bracketed_paste", "typed", "unknown") else (
                "bracketed_paste" if source_type == "paste" else (
                    "typed" if source_type is None else "unknown"
                )
            )
        )
        is_multiline = "\n" in text.strip()
        char_count = len(text)
        line_count = len(text.splitlines()) if text else 0

        # If true transport metadata is unavailable ('unknown') or bracketed paste,
        # conservatively require review before any training promotion.
        if resolved_transport in ("bracketed_paste", "unknown"):
            effective_learnable = False
        else:
            effective_learnable = bool(learnable)

        if resolved_transport == "bracketed_paste" and len(text) > LONG_MESSAGE and not asks_something(text):
            return self._document_reply(text, gate)

        sent_user = None
        incomplete = ""
        if gate["open"] and self.core is not None:
            self.out("\nOSIRIS › ")
            try:
                draft = self.core.draft(self._transcript(self.history[-6:]) + "OSIRIS:")
            except Exception as e:  # noqa: BLE001 - any core failure falls back to a mentor
                draft = ""
                self.out(f"(core failed: {type(e).__name__}) ")
            if draft and printable_ratio(draft) >= 0.95:
                voice, reply = "core", draft
                self.out(draft + "\n")
                self.out(f"  · voice: OSIRIS core ({self.core.name}, own weights)\n")

        if voice is None:
            model = self.mentor.model()
            if model is None:
                self.out("\nOSIRIS › I can't answer yet: my core hasn't earned its own voice and no "
                         f"mentor model is reachable at {self.mentor.base}. Start one with `ollama serve`.\n")
                self.history.pop()
                return ""
            fast = getattr(self.mentor, "fast_model", lambda: None)()
            fast = fast if fast != model else None
            why = ""
            if fast and len(text) > LONG_MESSAGE:
                model, fast, why = fast, None, "fast voice: long message"
            self._mark_chat()
            messages, sources = self.build_messages(gate, text)
            sent_user = messages[-1]
            busy = " · the batch trainer is sharing the CPU" if self._trainer_running() else ""
            if self._warm is not None and self._warm.is_alive():
                busy += " · still reading my notes from start-up"
            self.out("\nOSIRIS › ")
            started, first_word = time.time(), None
            waiting = Waiting(self.out, lambda: f"thinking · {model}{busy}{self._typical(model)}", self.tty)
            with TypeAhead(self.tty) as typed:
                while True:
                    self._voices.add(model)
                    waiting.start()
                    try:
                        for piece in self.mentor.stream(messages, model=model):
                            if first_word is None:
                                waiting.stop()
                                first_word = time.time() - waiting.started
                            reply += piece
                            self.out(piece)
                    except KeyboardInterrupt:
                        waiting.stop()
                        interrupted = True
                        self.out(" …(interrupted)")
                    except (OSError, ConnectionError, ValueError) as e:
                        waiting.stop()
                        if fast and not reply:
                            self.out(f"[{model} failed after {time.time() - started:.0f} s: {e} -- "
                                     f"asking {fast}]\nOSIRIS › ")
                            model, fast, why = fast, None, "fast voice: the main voice failed"
                            continue
                        self.out(f"\n[mentor {model} failed: {e}]")
                        interrupted = True
                    break
            voice = "mentor:" + model
            if first_word is not None:
                self._note_first_word(model, first_word)
            done = getattr(self.mentor, "last_done", None) or {}
            if not interrupted and done.get("done_reason") == "length":
                incomplete = f"cut off at the {MENTOR_MAX_TOKENS}-token reply limit"
            elif not interrupted and reply.count("```") % 2:
                incomplete = "ends inside an unclosed code block"
            if incomplete:
                self.out(f" …[incomplete: {incomplete}]")
            self.out("\n")
            idx = self.stats["exchanges"]
            if interrupted:
                note = "not learned: interrupted"
            elif incomplete:
                note = "not learned: incomplete reply"
            elif effective_learnable and self.core is None:
                note = "recorded; no core is loaded, so nothing is learned"
            elif effective_learnable and idx % HELDOUT_EVERY == 0:
                note = "held out: the core is scored on this exchange, not trained on it"
            elif effective_learnable:
                note = "the core trains on this exchange (your words and this reply)"
            elif resolved_transport == "bracketed_paste" or not learnable:
                note = "not learned: pasted transcript (ledger-only; use /learn last to propose)"
            elif resolved_transport == "unknown":
                note = "not learned: unverified transport (ledger-only; use /learn last to propose)"
            else:
                note = "not learned: review required (ledger-only; use /learn last to propose)"

            cited = f" · used: {', '.join(sources)}" if sources else ""
            if len(text) > MESSAGE_BUDGET:
                head, tail = self.excerpt_sizes(text)
                cited += (f" · long message: an excerpt was sent -- the first {head:,} and last {tail:,} of "
                          f"{len(text):,} characters ({len(text) - head - tail:,} left out, not read)")
            # sources are what OSIRIS and Devin sent, not earlier replies: a label the model made
            # up once must not become "known" on the next turn
            invented = invented_labels(reply, "\n".join(m["content"] for m in messages if m["role"] != "assistant"))
            if invented:
                cited += (f" · labels in the reply that nothing it was sent contains: {', '.join(invented)} "
                          "(the model's own, not recorded states)")
            timing = (f"first word {first_word:.0f} s, done {time.time() - started:.0f} s"
                      if first_word is not None else f"{time.time() - started:.0f} s")
            timing += self.timing_detail(done)
            self.out(f"  · voice: {model} speaking for OSIRIS{f' ({why})' if why else ''} · {timing} · "
                     f"core step {self._core_step()}, {self.gate_brief(gate)} · {note}{cited}\n")
            self._hold(typed.text)

        if not reply:
            self.history.pop()
            return ""
        self.history.append({"role": "assistant", "content": reply})
        self._sent += [sent_user or self.history[-2], {"role": "assistant", "content": reply}]

        idx = self.stats["exchanges"]
        self.stats["exchanges"] += 1
        if voice == "core":
            self.stats["core_spoke"] += 1
        heldout = idx % HELDOUT_EVERY == 0
        lesson = f"User: {text}\nOSIRIS: {reply}\n"
        rec_data = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "voice": voice,
            "heldout": heldout,
            "learnable": effective_learnable and not interrupted and not incomplete,
            "incomplete": incomplete or None,
            "user": text,
            "reply": reply,
            "index": idx,
            "input_transport": resolved_transport,
            "is_multiline": is_multiline,
            "char_count": char_count,
            "line_count": line_count,
            "source_type": resolved_transport,
            "pasted": (resolved_transport == "bracketed_paste"),
        }
        key = self._record(rec_data)
        if (resolved_transport in ("bracketed_paste", "unknown")) or not effective_learnable:
            self.last_paste = dict(rec_data, hash=key)
        self._save_stats()
        if effective_learnable and not interrupted and not incomplete and voice != "core" and self.core is not None:
            self._after(lesson, reply, heldout, key, idx)
        return reply

    def _small_talk_reply(self, text: str, gate: dict) -> str:
        """A greeting or thanks, answered by code at once with what is true right now.
        Recorded in the ledger but never learned: the core should not train on templates."""
        if SMALL_TALK.match(text).group("thanks"):
            reply = "You're welcome."
        else:
            voice = self.mentor.model()
            if gate["open"]:
                who = "My own core answers in its own voice now."
            elif voice:
                typical = self.typical_first_word(voice)
                who = (f"My own core (step {self._core_step()}) hasn't earned its voice yet, so {voice} "
                       f"speaks for me" + (f"; its replies start after about {typical:.0f} s on this "
                                           f"machine." if typical is not None else "."))
            else:
                who = ("My own core hasn't earned its voice yet and no mentor model is reachable, so only "
                       "code can answer for now -- start one with `ollama serve`.")
            reply = f"Hello, I'm here. {who} Ask me anything, or type /architecture to see how I'm put together."
        self.out(f"\nOSIRIS › {reply}\n  · voice: code, no model · instant · core step {self._core_step()}, "
                 f"{self.gate_brief(gate)}\n")
        self.history.append({"role": "assistant", "content": reply})
        self._sent += [self.history[-2], {"role": "assistant", "content": reply}]
        self._record({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "voice": "code", "heldout": False,
                      "learnable": False, "user": text, "reply": reply, "index": None})
        self._save_stats()
        return reply

    # -- what the mentor is told -------------------------------------------

    def system_prompt(self) -> str:
        """Stable across turns, so Ollama keeps it read; it changes only when a fact is
        remembered (/remember applies from the next message)."""
        system = IDENTITY
        if self.knowledge is not None:
            system += "\n\nWhat is on record:\n" + self.knowledge.brief()
        facts = self.facts()
        if facts:
            system += "\n\nThings Devin asked you to remember:\n" + "\n".join("- " + f for f in facts)
        if self.recall:
            system += "\n\n" + self.recall
        return system

    def build_messages(self, gate: dict, text: str):
        """The system prompt, the earlier turns exactly as they were sent (so a turn
        adds only its own message and Ollama re-reads nothing else), and the new
        message with live state and looked-up notes attached. The history kept for
        the core and the ledger holds only what was actually said."""
        system = self.system_prompt()
        hits, checks = [], []
        long_message = len(text) > LONG_MESSAGE   # a paste: no per-path checks, one note at most
        if self.knowledge is not None:
            hits = self.knowledge.lookup(text[:LONG_MESSAGE], k=1 if long_message else NOTES_PER_MESSAGE)
        context = "[Live state, read from disk just now]\n" + self._state_note(gate).strip()
        if self._trainer_running():
            context += "\nA batch training run of your core is in progress (osiris train)."
        if self.probes is not None and not long_message:
            checks = self.probes.run(text)
            if checks:
                context += ("\n\n[Checked just now -- read-only, run by OSIRIS's code]\n"
                            + self.probes.format(checks))
        if self._claims_hit:
            from osiris_cli import claims as claims_mod
            context += "\n\n" + claims_mod.context_block(self._claims_hit)
        if self._on_record:
            context += ("\n\n[On record for this message -- the scorecard's own verdicts, already shown to "
                        "Devin; state them exactly, do not re-describe them]\n" + "\n".join(self._on_record))
        if hits:
            context += ("\n\n[Notes looked up for this message -- Devin's files; cite the file if "
                        "you use one]\n" + self.knowledge.format_notes(hits))
        if long_message:
            context += (f"\n\n[This message is {len(text):,} characters; you are given an excerpt. Say what "
                        "you can from it, and that you saw only part of it. Do not describe the parts you "
                        "were not given. Keep its own hedges (could, if, potential, not established): a "
                        "possibility it describes is not a finding.]")
        last = {"role": "user", "content": context + "\n\n[Message]\n" + self.excerpt(text)}
        self._fit(len(system) + len(last["content"]))
        messages = [{"role": "system", "content": system}] + self._sent + [last]
        return messages, [c["cmd"].split(";")[0] if c["name"] != "file" else c["cmd"] for c in checks] \
            + [h["source"] for h in hits]

    def _fit(self, fixed: int) -> None:
        """Keeps the prompt inside the model's context. When it would overflow, the
        earlier turns are re-sent as plainly said (their notes and live state dropped),
        oldest out first: one full re-read, instead of Ollama truncating every turn."""
        def size():
            return fixed + sum(len(m["content"]) for m in self._sent)
        if size() <= PROMPT_BUDGET:
            return
        self._sent = [dict(m) for m in self.history[:-1]]
        while self._sent and (size() > PROMPT_BUDGET or self._sent[0]["role"] != "user"):
            del self._sent[0]

    # -- memory across sessions ---------------------------------------------

    def _recall(self) -> str:
        """The last few exchanges from earlier sessions, read from the ledger --
        no model summarises them, so nothing is invented about the past."""
        try:
            with open(self.log_path, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f.readlines()[-4 * RECALL_EXCHANGES:]]
        except (OSError, ValueError):
            return ""
        rows = [r for r in rows if r.get("voice") != "code"][-RECALL_EXCHANGES:]   # not greetings
        if not rows:
            return ""
        lines = [f"- {r.get('t', '?')[:16]} Devin: {r.get('user', '')[:200]!r} -> you: "
                 f"{r.get('reply', '')[:200]!r}" for r in rows]
        return ("Your most recent earlier exchanges (from the exchange ledger; earlier sessions "
                "included):\n" + "\n".join(lines))

    def facts(self) -> List[str]:
        try:
            with open(os.path.join(self.home, FACTS_FILE), encoding="utf-8") as f:
                return [json.loads(line)["fact"] for line in f if line.strip()][-40:]
        except (OSError, ValueError, KeyError):
            return []

    def remember(self, fact: str) -> str:
        fact = " ".join(fact.split())[:500]
        if not fact:
            return "Nothing to remember -- use /remember <fact>."
        with open(os.path.join(self.home, FACTS_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "fact": fact},
                               ensure_ascii=False) + "\n")
        return f"Remembered (in {FACTS_FILE}; applies from the next message): {fact}"

    def forget(self, needle: str) -> str:
        path = os.path.join(self.home, FACTS_FILE)
        try:
            with open(path, encoding="utf-8") as f:
                rows = [line for line in f if line.strip()]
        except OSError:
            rows = []
        keep = [r for r in rows if needle.lower() not in json.loads(r).get("fact", "").lower()]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(keep)
        return f"Forgot {len(rows) - len(keep)} fact(s) matching {needle!r}."

    def _trainer_running(self) -> bool:
        try:
            return bool(self.core is not None and self.core.training_locked())
        except Exception:  # noqa: BLE001
            return False

    def _mark_chat(self) -> None:
        try:
            with open(os.path.join(self.home, CHAT_MARKER), "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except OSError:
            pass

    def _hold(self, typed: str) -> None:
        """Lines typed during the reply become the next messages, visibly; an
        unfinished line (no Enter) is shown, not sent. A paste is one message,
        whole, its last line too (2026-10-01: the end of a pasted review was
        reported as "you were typing" and dropped)."""
        if not typed:
            return
        if PASTE_START in typed or PASTE_END in typed:
            # A paste, whole -- or, with only its end marker here, the tail of a paste whose start
            # was read before this reply. The markers are terminal syntax, never "typing".
            whole = PASTE_START in typed and typed.count(PASTE_START) == typed.count(PASTE_END)
            message = typed.replace(PASTE_START, "").replace(PASTE_END, "").replace("\r", "\n").strip()
            if message:
                self.held.append(Held(message, pasted=True))
                if not whole:
                    self.out(f"  · part of a paste ({len(message):,} characters) arrived apart from the rest; held as "
                             "its own pasted message (not learned)\n")
            return
        lines = typed.replace("\r", "\n").split("\n")
        partial = lines.pop().strip()
        self.held.extend(Held(line.strip()) for line in lines if line.strip())
        if partial:
            self.out(f"  · you were typing {partial!r} while I answered -- not sent; retype it to send\n")

    def _core_step(self) -> str:
        try:
            return str(self.core.step()) if self.core is not None else "n/a"
        except Exception:  # noqa: BLE001
            return "?"

    def _state_note(self, gate: dict) -> str:
        who = (f"\nYour core ({getattr(self.core, 'name', 'none')}) is at training step "
               f"{self._core_step()}; {self.stats['exchanges']} exchanges so far, "
               f"{self.stats['core_spoke']} answered by the core itself.")
        if gate["n"]:
            return who + (f"\nYour core's current state: {gate['n']} held-out exchanges scored, "
                    f"{gate['core_bpb']:.2f} bits/byte vs {gate['unigram_bpb']:.2f} for a unigram "
                    f"baseline; it speaks on its own at <= {SPEAK_BPB} bits/byte.")
        return who + "\nYour core has not been scored on held-out conversation yet."

    def _after(self, lesson: str, reply: str, heldout: bool, key: str, idx: int) -> None:
        def work():
            try:
                core_bpb = self.core.bits_per_byte(reply)
                uni_bpb = self.unigram_bpb(reply)
                trained = False
                if not heldout:
                    trained = self.core.learn(lesson, TRAIN_STEPS_PER_EXCHANGE) is not None
                with self._lock:
                    if heldout and core_bpb is not None:
                        self.stats["heldout_scores"][key] = [round(core_bpb, 4), round(uni_bpb, 4),
                                                             int(self.core.step()), idx]
                    if trained:
                        for b, c in Counter(lesson.encode("utf-8", errors="ignore")).items():
                            self.stats["unigram"][str(b)] = self.stats["unigram"].get(str(b), 0) + c
                self._save_stats()
            except Exception:  # noqa: BLE001 - learning must never break the conversation
                pass
        if self.background:
            if self._pending is not None and self._pending.is_alive():
                self._pending.join()
            self._pending = threading.Thread(target=work, daemon=True)
            self._pending.start()
        else:
            work()

    def finish(self) -> None:
        """Let the last lesson finish before the process exits, and free the
        mentor models this session used: a resident 7B slows batch training ~25x."""
        if self._pending is not None and self._pending.is_alive():
            self.out("[OSIRIS] finishing the last lesson…\n")
            self._pending.join()
        unload = getattr(self.mentor, "unload", None)
        for model in sorted(self._voices) if unload else ():
            unload(model)
        self._voices.clear()

    # -- other voices ------------------------------------------------------

    def speak_raw(self, prompt: str) -> str:
        """The core's own voice on demand, gate or not, labelled as such."""
        if self.core is None:
            self.out("\n[OSIRIS core unavailable]\n")
            return ""
        self.out("\nOSIRIS core (raw, not gated) › ")
        draft = self.core.draft(self._transcript(self.history[-4:]) + f"User: {prompt}\nOSIRIS:")
        self.out(repr(draft) if printable_ratio(draft) < 0.95 else draft)
        self.out("\n")
        return draft

    def status_lines(self) -> List[str]:
        g = self.gate()
        s = self.stats
        spoke = f"{s['core_spoke']}/{s['exchanges']}" if s["exchanges"] else "0/0"
        lines = [
            f"core          {getattr(self.core, 'name', 'none')} · step {self._core_step()}",
            f"exchanges     {s['exchanges']} · spoken by the core itself {spoke}",
            f"mentor        {self.mentor.model() or 'none reachable'}",
        ]
        if g["n"]:
            lines.append(f"held-out      {g['n']}/{GATE_WINDOW} scored · core {g['core_bpb']:.2f} bpb · "
                         f"unigram {g['unigram_bpb']:.2f} bpb")
        else:
            lines.append(f"held-out      none scored yet (every {HELDOUT_EVERY}th exchange is held out)")
        lines.append("gate          " + ("OPEN: the core answers in its own voice" if g["open"] else
                     f"closed: needs {GATE_WINDOW} held-out exchanges at <= {SPEAK_BPB} bpb and below unigram"))
        return lines
