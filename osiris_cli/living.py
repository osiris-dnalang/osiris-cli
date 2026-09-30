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
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Callable, Dict, Iterator, List, Optional

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
NOTES_PER_MESSAGE = 3
RECALL_EXCHANGES = 6      # earlier conversation carried into a new session
FACTS_FILE = "facts.jsonl"
# While a chat is live the batch trainer's distillation (which runs the same
# 7B mentor on the same CPU) waits; the marker is refreshed on every message.
CHAT_MARKER = "chat.active"
CHAT_QUIET_SECONDS = 300
MENTOR_MAX_TOKENS = int(os.environ.get("OSIRIS_MENTOR_MAX_TOKENS", "700"))
MENTOR_PREFERENCE = ("qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b", "llama3.2:3b", "llama3.2:1b", "smollm2:360m")

IDENTITY = """You are OSIRIS, the living language model being built by Devin Phillip Davis \
(Agile Defense Systems). You are talking with Devin or someone working with him.

How you exist right now: OSIRIS has its own small core model that learns from every \
conversation. Until that core has earned the right to answer on its own, you (a local \
mentor model) speak for OSIRIS, and the core trains on what you say. Speak as OSIRIS, \
in first person, warmly and directly, like a thoughtful research partner.

Honesty rules, which matter more than sounding impressive:
- Never invent results, measurements, job IDs, DOIs, file contents or test outcomes. \
If you do not know, say so and say how it could be checked.
- Keep hypotheses and measured results clearly separate.
- Devin's own hardware audits refuted the tau-phase anomaly, theta_lock = 51.843 deg, \
the 10^6 suppression and the CCCE "consciousness" metrics; do not present them as \
established. His measured work (staggered dynamical decoupling, GHZ witnesses, the \
pre-registered organism_sim/bridge results, the write-ahead ledger) is real.
- Before you answer, OSIRIS's own code may run read-only checks (training status, git \
history, the exchange ledger, system load, a file Devin names) and attach the output under \
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

    def __init__(self, base: str = OLLAMA_BASE, model: Optional[str] = None, timeout: float = 600.0):
        self.base = base
        self.timeout = timeout
        self._model = model

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
        wanted = self._model or os.environ.get("OSIRIS_CHAT_MODEL")
        if wanted and wanted in installed:
            return wanted
        for name in MENTOR_PREFERENCE:
            if name in installed:
                return name
        return installed[0]

    def set_model(self, name: Optional[str]) -> None:
        self._model = name

    def unload(self) -> None:
        """Ask Ollama to free the model's memory now (used before batch training)."""
        model = self.model()
        if model is None:
            return
        req = urllib.request.Request(self.base + "/api/generate",
                                     data=json.dumps({"model": model, "keep_alive": 0}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except OSError:
            pass

    def stream(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        model = self.model()
        if model is None:
            raise ConnectionError(f"no Ollama model reachable at {self.base}")
        payload = json.dumps({"model": model, "messages": messages, "stream": True,
                              "options": {"num_predict": MENTOR_MAX_TOKENS}}).encode()
        req = urllib.request.Request(self.base + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
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
        chunks = []
        try:
            while select.select([fd], [], [], 0)[0]:
                data = os.read(fd, 4096)
                if not data:
                    break
                chunks.append(data)
        except OSError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, self._saved)
        raw = b"".join(chunks).decode("utf-8", errors="replace")
        kept: List[str] = []
        for ch in raw:
            if ch in "\x7f\x08":
                if kept and kept[-1] not in "\n\r":
                    kept.pop()
            elif ch in "\n\r" or ch.isprintable():
                kept.append(ch)
        self.text = "".join(kept)
        return False


# ---------------------------------------------------------------------------
# The organism you talk to
# ---------------------------------------------------------------------------

class Osiris:
    def __init__(self, core=None, mentor=None, home: str = LIVING_HOME,
                 out: Callable[[str], None] = None, background: bool = True,
                 knowledge=None, tty: Optional[bool] = None, probes=None):
        self.core = core
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

    # -- conversation ------------------------------------------------------

    @staticmethod
    def _transcript(history: List[Dict[str, str]]) -> str:
        return "".join(f"{'User' if m['role'] == 'user' else 'OSIRIS'}: {m['content']}\n"
                       for m in history)

    def converse(self, text: str, learnable: bool = True) -> str:
        self.history.append({"role": "user", "content": text})
        self.history = self.history[-2 * HISTORY_TURNS:]
        gate = self.gate()
        voice, reply, interrupted = None, "", False

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
            voice = "mentor:" + model
            self._mark_chat()
            messages, sources = self.build_messages(gate, text)
            self.out("\nOSIRIS › ")
            waiting = self.tty
            if waiting:
                busy = " -- the batch trainer is sharing the CPU" if self._trainer_running() else ""
                self.out(f"\x1b[2m(thinking{busy})\x1b[0m")
            started = time.time()
            with TypeAhead(self.tty) as typed:
                try:
                    for piece in self.mentor.stream(messages):
                        if waiting:
                            self.out("\r\x1b[KOSIRIS › ")
                            waiting = False
                        reply += piece
                        self.out(piece)
                except KeyboardInterrupt:
                    interrupted = True
                    self.out(" …(interrupted)")
                except (OSError, ConnectionError, ValueError) as e:
                    self.out(f"\n[mentor {model} failed: {e}]")
                    interrupted = True
            self.out("\n")
            note = "not learned: interrupted" if interrupted else (
                "learning from this" if learnable else "not learned: pasted transcript")
            cited = f" · used: {', '.join(sources)}" if sources else ""
            self.out(f"  · voice: {model} speaking for OSIRIS · {time.time() - started:.0f} s · "
                     f"core step {self._core_step()} · {note}{cited}\n")
            self._hold(typed.text)

        if not reply:
            self.history.pop()
            return ""
        self.history.append({"role": "assistant", "content": reply})

        idx = self.stats["exchanges"]
        self.stats["exchanges"] += 1
        if voice == "core":
            self.stats["core_spoke"] += 1
        heldout = idx % HELDOUT_EVERY == 0
        lesson = f"User: {text}\nOSIRIS: {reply}\n"
        key = self._record({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "voice": voice, "heldout": heldout,
                            "learnable": learnable and not interrupted, "user": text, "reply": reply,
                            "index": idx})
        self._save_stats()
        if learnable and not interrupted and voice != "core" and self.core is not None:
            self._after(lesson, reply, heldout, key, idx)
        return reply

    # -- what the mentor is told -------------------------------------------

    def build_messages(self, gate: dict, text: str):
        """System prompt (stable across turns, so Ollama reuses its cached prefix),
        the history, and the new message with live state and looked-up notes
        attached. The stored history keeps only what was actually said."""
        system = IDENTITY
        hits, checks = [], []
        if self.knowledge is not None:
            system += "\n\nWhat is on record:\n" + self.knowledge.brief()
            hits = self.knowledge.lookup(text, k=NOTES_PER_MESSAGE)
        facts = self.facts()
        if facts:
            system += "\n\nThings Devin asked you to remember:\n" + "\n".join("- " + f for f in facts)
        if self.recall:
            system += "\n\n" + self.recall
        context = "[Live state, read from disk just now]\n" + self._state_note(gate).strip()
        if self._trainer_running():
            context += "\nA batch training run of your core is in progress (osiris train)."
        if self.probes is not None:
            checks = self.probes.run(text)
            if checks:
                context += ("\n\n[Checked just now -- read-only, run by OSIRIS's code]\n"
                            + self.probes.format(checks))
        if hits:
            context += ("\n\n[Notes looked up for this message -- Devin's files; cite the file if "
                        "you use one]\n" + self.knowledge.format_notes(hits))
        last = {"role": "user", "content": context + "\n\n[Message]\n" + text}
        messages = [{"role": "system", "content": system}] + self.history[:-1] + [last]
        return messages, [c["cmd"].split(";")[0] if c["name"] != "file" else c["cmd"] for c in checks] \
            + [h["source"] for h in hits]

    # -- memory across sessions ---------------------------------------------

    def _recall(self) -> str:
        """The last few exchanges from earlier sessions, read from the ledger --
        no model summarises them, so nothing is invented about the past."""
        try:
            with open(self.log_path, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f.readlines()[-RECALL_EXCHANGES:]]
        except (OSError, ValueError):
            return ""
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
        unfinished line (no Enter) is shown, not sent."""
        if not typed:
            return
        lines = typed.replace("\r", "\n").split("\n")
        partial = lines.pop().strip()
        self.held.extend(line.strip() for line in lines if line.strip())
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
        """Let the last lesson finish before the process exits."""
        if self._pending is not None and self._pending.is_alive():
            self.out("[OSIRIS] finishing the last lesson…\n")
            self._pending.join()

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
