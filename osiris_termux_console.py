#!/usr/bin/env python3
"""
OSIRIS Sovereign Dual-Engine REPL v9.4 (Resilient)
- Strips terminal artifacts and ANSI codes from input buffer
- Detects and intercepts LLM safety/refusal responses before AST
- Tighter prompt constraints to prevent mock-code hallucination
"""

import sys
import os
import time
import urllib.request
import json
import ast
import re
import threading
import shutil
import glob
import difflib
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osiris_ast_bridge import build_context
import gemini_bridge
import db_ledger
import vision_indexer
import sprint_manager
import genome
import payload_gate
import structured_proposal
import verify_loop
import genome_ledger
import run_record
import research
import osiris_ui
import gaps
import intent_router
import experiments
import session_state
import hashlib


def _load_dotenv():
    """Load KEY=VALUE pairs from a .env at the project root into os.environ,
    without overwriting a variable that's already set for real (the shell
    always wins over the file). Silent no-op if .env doesn't exist -- it's
    optional. Never logs or prints any value it loads."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # the checkout's parent (a source checkout in ~/osiris-cli reads ~/.env), then ~/.env
    # itself: an installed wheel lives in site-packages, whose parent holds no .env
    paths = [os.path.join(project_root, ".env"), os.path.join(os.path.expanduser("~"), ".env")]
    for env_path in dict.fromkeys(paths):
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[len("export "):].strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError:
            pass
    # keys kept in Google Secret Manager (opt-in: OSIRIS_SECRETS_SOURCE=gcp + OSIRIS_GCP_PROJECT)
    try:
        from osiris_cli import gcp_secrets
        if gcp_secrets.wanted():
            gcp_secrets.load_into_environ()
    except Exception:  # noqa: BLE001 - optional; never blocks startup
        pass


_load_dotenv()

OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
CHAT_MODEL = os.environ.get("OSIRIS_CHAT_MODEL", "llama3.2:1b")
CODE_MODEL = os.environ.get("OSIRIS_CODE_MODEL", "deepseek-coder")

ARCHITECT_PREFERENCES = (
    "qwen2.5:7b",
    "qwen2.5-coder:7b",
    "qwen2.5:1.5b",
    "llama3.2:1b",
    "llama3.2:3b",
    "smollm2:360m",
    "smollm2:135m",
)

SYNTHESIZER_PREFERENCES = (
    "qwen2.5-coder:7b",
    "deepseek-coder",
    "qwen2.5:7b",
    "qwen2.5:1.5b",
    "llama3.2:1b",
    "smollm2:360m",
)

def _detect_installed_ollama_models(timeout: float = 1.0) -> list:
    base = OLLAMA_GEN_URL.rsplit("/api/", 1)[0]
    try:
        req = urllib.request.Request(f"{base}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []

def _resolve_active_models():
    global CHAT_MODEL, CODE_MODEL
    # If user explicitly specified via env var, honor it
    if os.environ.get("OSIRIS_CHAT_MODEL") and os.environ.get("OSIRIS_CODE_MODEL"):
        return
    installed = _detect_installed_ollama_models(timeout=1.0)
    if not installed:
        return
    if not os.environ.get("OSIRIS_CHAT_MODEL"):
        for pref in ARCHITECT_PREFERENCES:
            matched = next((m for m in installed if pref in m or m.startswith(pref.split(":")[0])), None)
            if matched:
                CHAT_MODEL = matched
                break
        else:
            CHAT_MODEL = installed[0]

    if not os.environ.get("OSIRIS_CODE_MODEL"):
        for pref in SYNTHESIZER_PREFERENCES:
            matched = next((m for m in installed if pref in m or m.startswith(pref.split(":")[0])), None)
            if matched:
                CODE_MODEL = matched
                break
        else:
            CODE_MODEL = installed[0]

try:
    _resolve_active_models()
except Exception:
    pass

# --- Engine 3: The Organism (real osiris.nclm.SovereignTransformerV2, online-learning
# from every REPL exchange). Same ~726K-param geometry as osiris-mobile-termux's mobile
# default so checkpoints stay shape-compatible with that harness.
_here = os.path.dirname(os.path.abspath(__file__))
ORGANISM_SRC = _here if os.path.exists(os.path.join(_here, "osiris")) else "/data/data/com.termux/files/home/crsm/osiris-cli"
# OSIRIS_ORGANISM_HOME isolates an experiment's checkpoint from the live core.
ORGANISM_HOME = os.environ.get("OSIRIS_ORGANISM_HOME") or os.path.join(os.path.expanduser("~"), ".osiris", "nclm_organism")
TELEMETRY_HOME = os.path.join(os.path.expanduser("~"), ".osiris", "telemetry")
TELEMETRY_LOG = os.path.join(TELEMETRY_HOME, "nclm_loss.log")
PROMPT_LIBRARY_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "prompt_library.json")
ORGANISM_GEOMETRY = dict(dim=128, n_layers=4, n_heads=4, ff_dim=256, max_seq_len=128)
ORGANISM_MAX_BACKUPS = 5
OLLAMA_STARTUP_TIMEOUT = 2.5
_organism_lock = threading.Lock()
_organism_state = {"model": None, "optimizer": None, "step": 0, "history": []}
# Guards actual terminal output, not model state (_organism_lock's job). Engine
# 3's background thread prints its own step/drift/failure lines at unpredictable
# times relative to the main thread's live token streaming in query_model() --
# without this, the two interleave mid-line (confirmed from a real garbled
# transcript on-device: box-drawing header characters and words split apart
# mid-token). Both sides hold this for their whole logical block of output.
_stdout_lock = threading.Lock()

# --- Engine 1 adaptive confidence: closes the loop "route -> real outcome ->
# adjusted future confidence" -- ported in spirit (not copied verbatim) from
# osiris-cli's osiris_intent_engine.py IntentEngine.receive_swarm_feedback()/
# get_adaptive_confidence(), rolling-window + discrete-bucket design, adapted
# to this file's simpler regex-based routing (two real categories: "modify"
# and "synthesis", keyed off which branch of run_synergy_pipeline actually
# fired). In-session only (module-level dict, not checkpointed) -- a real,
# observable, working mechanism; persisting it across restarts is a natural
# follow-up, not required for this to be genuinely functional.
_intent_quality_log = {}       # intent_type -> [quality scores...], rolling
_intent_confidence_adj = {}    # intent_type -> current adjustment


def _record_intent_feedback(intent_type: str, quality: float):
    """quality in [0,1]: did this routing branch actually produce a usable
    real outcome? (a parsed WRITE_FILE proposal, clean AST-compiled code,
    etc. -- real signals already computed by run_synergy_pipeline, not
    invented ones)."""
    history = _intent_quality_log.setdefault(intent_type, [])
    history.append(quality)
    recent = history[-10:]
    avg = sum(recent) / len(recent)
    if avg < 0.4:
        _intent_confidence_adj[intent_type] = -0.15
    elif avg < 0.6:
        _intent_confidence_adj[intent_type] = -0.05
    elif avg > 0.8:
        _intent_confidence_adj[intent_type] = 0.05
    else:
        _intent_confidence_adj[intent_type] = 0.0


def _get_intent_confidence(intent_type: str, base: float = 0.7) -> float:
    adj = _intent_confidence_adj.get(intent_type, 0.0)
    return max(0.1, min(0.99, base + adj))


def _log_prompt_library(raw_text: str, modify_intent: bool, codebase_intent: bool):
    """Append-only JSONL record of every real conversational turn (not slash
    commands) -- local file write only, no model calls, always-on. Truncates
    long prompts the same way architect_prompt already does (raw_text[:7500])
    so the library stays consistent with what Engine 1 actually saw."""
    try:
        os.makedirs(os.path.dirname(PROMPT_LIBRARY_PATH), exist_ok=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "prompt": raw_text[:2000],
            "truncated": len(raw_text) > 2000,
            "modify_intent": bool(modify_intent),
            "codebase_intent": bool(codebase_intent),
        }
        with open(PROMPT_LIBRARY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # best-effort logging must never break the REPL turn


_pending_suggestions = {}  # "1"/"2" -> full command text, valid for exactly one turn


# The ONLY things a /suggest number can run: fixed, read-only or drafting
# commands owned by this code. /suggest used to register the model's "exact
# text to type next" as the command itself (a model-written /ignite,
# /sprint plan or /bench ... now ran on one keypress). BENCH opens the
# preflight card only; GAPS lists drafts (activating asks first).
SUGGEST_ACTIONS = {
    "STATUS": ("Full status", "/status"),
    "CHECK": ("Check ledger, runs and bench", "/check"),
    "MENTORS": ("Mentor evidence", "/mentors"),
    "BENCH": ("Benchmark preflight (starts nothing yet)", "/bench"),
    "GAP": ("Draft a capability gap", "/gap"),
    "GAPS": ("Review gap drafts", "/gaps"),
    "EXPERIMENT": ("Draft an experiment brief", "/experiment"),
    "RUNS": ("Run statistics", "/runs stats"),
    "WHY": ("Why the last sandbox run passed or failed", "/why"),
    "HELP": ("Every command", "/help"),
}


def _suggest(command: str = ""):
    """'/suggest': on-demand only, never automatic. Reads recent prompt-library
    + telemetry activity and asks Engine 1 to PICK 1-2 action IDs from
    SUGGEST_ACTIONS. Only a listed ID gets a number, and the number runs that
    ID's fixed command; any other model text is shown unnumbered."""
    recent_prompts = []
    try:
        if os.path.exists(PROMPT_LIBRARY_PATH):
            with open(PROMPT_LIBRARY_PATH, encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            for ln in lines[-8:]:
                try:
                    e = json.loads(ln)
                    recent_prompts.append(f"- {e.get('prompt', '')[:150]}")
                except Exception:
                    continue
    except Exception:
        pass

    recent_telemetry = []
    try:
        if os.path.exists(TELEMETRY_LOG):
            with open(TELEMETRY_LOG, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            recent_telemetry = lines[-8:]
    except Exception:
        pass

    context = "Recent user prompts:\n" + ("\n".join(recent_prompts) or "(none yet)")
    context += "\n\nRecent telemetry:\n" + ("\n".join(recent_telemetry) or "(none yet)")

    catalog = "\n".join(f"{k}: {label}" for k, (label, _cmd) in SUGGEST_ACTIONS.items())
    prompt = f"""{context}

Based on this recent activity, pick 1 or 2 of these actions the user could take next.
Use ONLY an ID from this list:
{catalog}
Output EXACTLY in this format and nothing else:
SUGGESTION 1: <ID> -- <one short reason>
SUGGESTION 2: <ID> -- <one short reason, or omit this line>
"""
    print("\n[*] Thinking of suggestions based on recent activity (Engine 1)...")
    raw = query_model(prompt, CHAT_MODEL, stream=False, timeout=420)
    _pending_suggestions.clear()
    found = re.findall(r"^SUGGESTION\s+(\d+):\s*(.+)$", raw, re.MULTILINE)
    if not found:
        print("[!] No parseable suggestions came back this time.\n")
        return
    ui = osiris_ui.Canvas()
    print(" 💡 Suggested next steps (the model picks an action; OSIRIS decides what it runs):")
    n = 0
    for _num, line in found[:3]:
        action_id, _sep, reason = line.strip().partition("--")
        action_id = action_id.strip().upper()
        if action_id in SUGGEST_ACTIONS:
            n += 1
            label, cmd = SUGGEST_ACTIONS[action_id]
            _pending_suggestions[str(n)] = cmd
            print(f"   [{n}] {label}" + (ui.dim(f"  (model's reason: {reason.strip()[:100]})") if reason.strip() else ""))
        else:
            # Model text is never a command: shown for reading, no number.
            print("   " + ui.dim(f"(not an OSIRIS action, not selectable) {line.strip()[:100]}"))
    print("   (type a number to run it, or type anything else as usual)\n")


def _find_latest_screenshot():
    """Searches broadly under Termux's shared-storage picture trees (not one
    hardcoded 'Screenshots' subfolder name, since that varies by device/OEM)
    for the most recently modified image file. Returns (path, None) or
    (None, reason) -- reason is a clear, user-facing string, never an
    exception, since this is a discovery helper callers show directly."""
    storage_root = os.path.join(os.path.expanduser("~"), "storage")
    if not os.path.isdir(storage_root):
        return None, ("~/storage not found -- run 'termux-setup-storage' first "
                       "and grant the permission prompt, then retry.")

    search_roots = [os.path.join(storage_root, d) for d in ("pictures", "dcim")]
    search_roots = [p for p in search_roots if os.path.isdir(p)]
    if not search_roots:
        return None, "~/storage exists but has neither a pictures/ nor dcim/ link."

    exts = (".png", ".jpg", ".jpeg", ".webp")
    best_path, best_mtime = None, -1.0
    for root in search_roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(exts):
                    fp = os.path.join(dirpath, fn)
                    try:
                        mtime = os.path.getmtime(fp)
                    except OSError:
                        continue
                    if mtime > best_mtime:
                        best_mtime, best_path = mtime, fp

    if best_path is None:
        return None, "No image files found under ~/storage/pictures or ~/storage/dcim."
    return best_path, None


def _vision_latest():
    """'/vision latest': finds the newest screenshot, sends it to Gemini
    (Gemini-only by design -- local models here are text-only), digests it
    into a prompt_library.json entry using the SAME writer/schema every
    normal conversational turn uses, so it's immediately visible to
    /suggest afterward."""
    if not gemini_bridge.is_configured():
        print("[!] /vision needs GEMINI_API_KEY set (local models can't do vision "
              "on this hardware) -- add it to .env and retry.\n")
        return

    path, reason = _find_latest_screenshot()
    if path is None:
        print(f"[!] {reason}\n")
        return

    print(f"\n[*] Sending latest image to Gemini vision ({os.path.basename(path)})...")
    try:
        digest = gemini_bridge.query_with_image(
            "You are OSIRIS Engine 1's vision digestion step. Analyze this "
            "screenshot: extract any code traceback, UI state, or hand-drawn "
            "architectural diagram it contains. Respond with a concise plain-"
            "text description a developer could act on -- no markdown, no "
            "preamble.",
            "Digest this screenshot.",
            path,
            timeout=60,
        )
    except gemini_bridge.GeminiUnavailable as e:
        print(f"[!] Vision call failed: {e}\n")
        return

    print(f" 👁  {digest.strip()}\n")
    _log_prompt_library(
        f"[vision:{os.path.basename(path)}] {digest.strip()}",
        bool(MODIFY_INTENT_RE.search(digest)),
        bool(CODEBASE_INTENT_RE.search(digest)),
    )
    print("[*] Logged to prompt_library.json -- available to /suggest now.\n")


def _vision_sync_sprint():
    """'/vision sync-sprint': runs the incremental hash-based indexer over
    any new/unprocessed screenshots, parses the real digest into backlog
    stories, and prints the top 2. Registers them with the same numbered-
    shortcut mechanism /suggest uses, so typing the digit re-runs it as a
    normal conversational request (falls through to run_synergy_pipeline)."""
    print("\n[*] /vision sync-sprint: scanning for new screenshots...")
    digest, processed, error = vision_indexer.run_incremental()
    if error and not processed:
        print(f"[!] {error}\n")
        return
    if error:
        print(f"[!] (partial run) {error}")
    print(f"[*] Digested {len(processed)} new image(s).")

    added = sprint_manager.parse_digest(digest)  # untrusted: shown, never saved as backlog
    if not added:
        if vision_indexer.NO_CONTEXT_SENTINEL in digest:
            print("[*] No architectural context in these screenshots (unrelated images "
                  "skipped) -- no stories added.\n")
        else:
            print("[!] No parseable STORY lines came back from this batch.\n")
        return

    # A vision model's reading of screenshots is untrusted reference: it used to
    # become backlog stories that /sprint plan could activate, skipping the
    # structured-gap checks. Now an idea can only start a /gap draft you review.
    print(" 📋 Ideas read from the screenshots (untrusted reference -- nothing was saved):")
    _pending_suggestions.clear()
    for i, (text, complexity) in enumerate(added[:5], start=1):
        _pending_suggestions[str(i)] = "/gap " + " ".join(text.split())[:240]
        print(f"   [{i}] (complexity {complexity}) {text}")
    if len(added) > 5:
        print(f"   ...and {len(added) - 5} more not shown.")
    print("   A number opens a /gap draft pre-filled with that idea, for you to check and complete.\n")


def _sprint_plan(command: str = ""):
    """'/sprint plan': deterministically promotes the top backlog stories
    (lowest complexity first -- see sprint_manager.top_priority()'s
    docstring for why this doesn't need a model call) to 'active'."""
    n_match = re.search(r"--count\s+(\d+)", command)
    n = int(n_match.group(1)) if n_match else 3
    picks = sprint_manager.top_priority(n=n, status="backlog", plannable_only=True)
    skipped = [st for st in sprint_manager.get_backlog()["stories"]
               if st["status"] == "backlog" and not sprint_manager.plannable(st)]
    if skipped:
        print(f"\n[*] /sprint plan: {len(skipped)} backlog stor{'y' if len(skipped) == 1 else 'ies'} from untrusted "
              f"sources ({', '.join(sorted({st.get('source', '?') for st in skipped}))}) left alone -- "
              f"capture one with /gap to make it work.")
    if not picks:
        print("\n[!] /sprint plan: no backlog story from an activated gap. /gap, /gaps, then /ignite.\n")
        return
    for s in picks:
        sprint_manager.set_status(s["id"], "active")
    print(f"\n[*] /sprint plan: {len(picks)} stor{'y' if len(picks) == 1 else 'ies'} now active:")
    for s in picks:
        print(f"   #{s['id']} (complexity {s['complexity']}) {s['text']}")
    print()


def _resolve_ignite_target(trait_text: str):
    """The module an ignite trait is actually about, e.g. 'gemini_bridge.py'
    in "requiring diffs for gemini_bridge.py to ...". Resolved against this
    bin/ directory (where osiris's own modules live). Returns an absolute path
    (existing or not -- a trait may name a new module), or None if the trait
    names no .py file, in which case the story gets a scratch osiris_story_N.py
    that can never count as a metamorphosis (see _apply_pending_write)."""
    m = re.search(r"([\w\-]+\.py)\b", trait_text)
    if not m:
        return None
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), m.group(1))


def _public_names(source: str) -> set:
    """Top-level public function/class names defined in source (empty set if
    it doesn't parse -- the sandbox gate reports the syntax error itself)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not n.name.startswith("_")}


SPRINT_DEFAULT_K = 3  # candidates per story; override with /sprint execute --k N


def _record_sprint_run(command, started_at, story, trait, write_path, prompt, k, attempts, trace, outcome):
    """Writes ~/.osiris/runs/<run_id>/ (see run_record.py) for one story's
    k-candidate loop and appends its hash to the genome ledger. Raises on any
    failure: the caller proposes nothing it could not record. Returns
    (run_id, sha256 of the proposed module or None)."""
    writer = run_record.RunWriter()
    rows = []
    for a, t in zip(attempts, trace):
        cand = a["candidate"]
        rows.append({
            # model is what OSIRIS requested (env override or default), not a
            # provider-confirmed identity: no version/digest is recorded yet.
            "n": a["n"], "backend": t["backend"], "model_requested": t["model"],
            "stage": t["stage"], "ok": a["ok"],
            "reason": (a["reason"] or "").strip()[-500:],
            "module_sha256": writer.artifact(f"cand-{a['n']}.module.py", cand["module"]) if cand else None,
            "test_sha256": writer.artifact(f"cand-{a['n']}.test.py", cand["test"]) if cand else None,
            "sandbox_log": os.path.basename(t["sandbox_log"]) if t["sandbox_log"] else None,
        })
    head, dirty = _git_state()
    proposed = next((r for r in rows if r["ok"]), None) if outcome == "proposed" else None
    base_path = os.path.realpath(write_path)
    base_text = None
    if os.path.exists(base_path):
        with open(base_path, encoding="utf-8", errors="replace") as f:
            base_text = f.read()
    record = {
        "command": command.strip(),
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "code": {"commit": head, "dirty": dirty},
        "story": {"id": story["id"], "text": story["text"], "source": story["source"], "trait": trait},
        "target": {"path": write_path, "base_sha256": _sha256_of(base_path)},
        # The target's text at record time, so /run show can count changed
        # lines after the file has moved on (e.g. once a candidate is applied).
        "base_text_sha256": writer.artifact("base.txt", base_text) if base_text is not None else None,
        "k": k,
        "prompt_sha256": writer.artifact("prompt.txt", prompt),
        "attempts": rows,
        "outcome": outcome,
        "proposed_candidate": proposed["n"] if proposed else None,
    }
    record_sha = writer.finish(record)
    genome_ledger.GenomeLedger().append("sprint_run", {
        "run_id": writer.run_id, "record_sha256": record_sha, "story_id": story["id"],
        "outcome": outcome, "candidate_sha256": proposed["module_sha256"] if proposed else None,
    })
    return writer.run_id, (proposed["module_sha256"] if proposed else None)


def _sprint_execute(command: str = ""):
    """'/sprint execute': for each active story, asks Engine 2 for a real
    WRITE_FILE + TEST_FUNCTION pair addressing it, then routes through the
    SAME real sandbox gate /auto-enhance uses (_run_sandboxed_test).

    Stops at the FIRST proposal that passes the sandbox: there is only one
    _pending_write slot, so continuing used to overwrite an earlier proposal
    before the user could /apply it (2026-09-23: story #14 was marked 'done'
    but its file never existed). A passing story is marked 'proposed', and
    only becomes 'done' when /apply actually lands it -- a discard sends it
    back to 'active'. Remaining active stories run on the next /sprint execute.

    Each story gets up to k candidates (default SPRINT_DEFAULT_K, or
    --k N): each failure's real output is fed back into the next attempt, and
    the first candidate that passes the path/API checks and the sandbox is
    proposed (verify_loop.first_passing).

    Ignite stories whose trait names a module (e.g. gemini_bridge.py) target
    THAT module with its current content in the prompt, instead of a scratch
    file. Pass --allow-self-modify to permit a protected osiris script, same
    override every other write path uses -- off by default."""
    blocked = _apply_block_reason()
    if blocked:
        # Each story's run record is hashed into the genome ledger, which is
        # what the block is about -- and nothing proposed could be applied.
        print(f"\n[!] /sprint execute refused: /apply is blocked ({blocked}). Run /status.\n")
        return
    allow_self_modify = SELF_MODIFY_OVERRIDE in command
    k_match = re.search(r"--k\s+(\d+)", command)
    k = max(1, int(k_match.group(1))) if k_match else SPRINT_DEFAULT_K
    # main() discards any pending write before dispatching a command, so a
    # 'proposed' story here is stale (e.g. the REPL exited before /apply).
    for s in sprint_manager.get_backlog()["stories"]:
        if s["status"] == "proposed":
            sprint_manager.set_status(s["id"], "active")
    backlog = sprint_manager.get_backlog()
    active = [s for s in backlog["stories"] if s["status"] == "active" and sprint_manager.plannable(s)]
    pick = re.search(r"#(\d+)", command)
    if pick:
        # "/sprint execute #24": that story only, instead of the oldest active one.
        sid = int(pick.group(1))
        chosen = next((s for s in backlog["stories"] if s["id"] == sid), None)
        if chosen is None:
            print(f"\n[!] /sprint execute: no story #{sid}.\n")
            return
        if not sprint_manager.plannable(chosen):
            print(f"\n[!] /sprint execute: story #{sid} came from '{chosen.get('source')}' -- untrusted reference, "
                  f"not sprint work. Capture it with /gap, activate it, then /ignite.\n")
            return
        if chosen["status"] != "active":
            print(f"\n[!] /sprint execute: story #{sid} is '{chosen['status']}', not active"
                  f"{' -- /sprint plan activates backlog stories' if chosen['status'] == 'backlog' else ''}.\n")
            return
        active = [chosen]
    if not active:
        print("\n[!] /sprint execute: no active stories. Run /sprint plan first.\n")
        return

    content_limit = 60000 if gemini_bridge.is_configured() else 6000
    for story in active:
        print(f"\n[*] /sprint execute: story #{story['id']} -- {story['text']}")
        is_ignite = story["source"] == "ignite"
        m = IGNITE_STORY_RE.match(story["text"]) if is_ignite else None
        trait = m.group(1) if m else story["text"]
        target = _resolve_ignite_target(trait) if is_ignite else None

        current_block = ""
        current = None
        if target:
            write_path = os.path.relpath(target, os.getcwd())
            if write_path.startswith(".."):
                print(f"[!] story #{story['id']}: target {target} is outside the current directory "
                      f"(the write safe root) -- run osiris from {os.path.dirname(os.path.dirname(target))}. "
                      f"Leaving story active.")
                continue
            if os.path.exists(target):
                with open(target, encoding="utf-8", errors="replace") as f:
                    current = f.read()
                if len(current) > content_limit:
                    # A truncated file in the prompt comes back as a truncated
                    # rewrite -- refuse rather than propose a destructive diff.
                    print(f"[!] story #{story['id']}: {write_path} is {len(current)} chars, over the "
                          f"{content_limit}-char limit for the current backend. Leaving story active.")
                    continue
                current_block = f"""
CURRENT CONTENT OF {write_path} (modify THIS file; output the COMPLETE updated file,
preserving every existing public function unless the story requires changing it):
{current}
"""
        else:
            write_path = f"osiris_story_{story['id']}.py"
        module_name = os.path.splitext(os.path.basename(write_path))[0]
        # Ignite stories send the trait itself, not the internal "[structural]
        # implement dormant trait:" label -- with the label, Gemini blocked 5/6
        # otherwise-identical prompts (blockReason=OTHER), without it 0/2.
        prompt = f"""You are OSIRIS Sovereign Synthesizer implementing one Agile user story.

USER STORY: {trait if is_ignite else story['text']}
{current_block}
Propose a small, real, self-contained Python module implementing this, AND a discrete
test that proves it works (assert statements exercising the specific behavior this
story requires).
{structured_proposal.instructions(write_path, module_name)}
"""
        if is_ignite:
            # Display-only, from values OSIRIS already knows -- the model is no
            # longer asked to print it (its output is schema-constrained JSON).
            print(f"\n  [LOCUS]       {write_path}")
            print(f"  [OPERATION]   {'SPLICE' if current is not None else 'NEW MODULE'}")
            print(f"  [CONSTRAINT]  proot_sandbox_pass (enforced below unconditionally, not a toggle)")
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        trace = []  # per attempt: backend, and the stage verify() reached

        def generate(feedback, prompt=prompt, trace=trace):
            raw = _synthesize(prompt + (verify_loop.feedback_block(feedback) if feedback else ""),
                              structured=True)
            trace.append({"backend": _last_backend.get("name"), "model": _last_backend.get("model"),
                          "stage": "generate", "sandbox_log": None})
            proposal = structured_proposal.parse_proposal(raw)
            if proposal is None:
                return None, f"backend {_last_backend['name']} returned no usable proposal (empty or malformed)"
            return proposal, ""

        def verify(proposal, write_path=write_path, current=current, trace=trace):
            trace[-1]["stage"] = "path"
            if os.path.normpath(proposal["path"]) != os.path.normpath(write_path):
                return False, f"proposed '{proposal['path']}' instead of the assigned '{write_path}'"
            if current is not None:
                trace[-1]["stage"] = "api"
                # Modifying a live module: the model's own test can pass on a file
                # that silently dropped the functions the rest of osiris imports.
                dropped = _public_names(current) - _public_names(proposal["module"])
                if dropped:
                    return False, f"drops existing public name(s) {sorted(dropped)}"
            trace[-1]["stage"] = "sandbox"
            result = _run_sandboxed_test(os.path.basename(write_path), proposal["module"], proposal["test"])
            trace[-1]["sandbox_log"] = _last_sandbox["path"]
            return result

        def on_attempt(a, sid=story["id"]):
            if a["ok"]:
                print(f"[*] story #{sid}: candidate {a['n']}/{k} PASSED the sandbox.")
            else:
                print(f"[!] story #{sid}: candidate {a['n']}/{k} failed: {a['reason'].strip()[-150:]}")

        proposal, attempts = verify_loop.first_passing(generate, verify, k, on_attempt)
        write_error = _check_write_safety(write_path, allow_self_modify)[1] if proposal else None
        outcome = "write_rejected" if write_error else "proposed" if proposal else "no_candidate_passed"
        try:
            run_id, candidate_sha = _record_sprint_run(
                command, started_at, story, trait, write_path, prompt, k, attempts, trace, outcome)
        except Exception as e:
            print(f"[!] story #{story['id']}: the run could not be recorded ({type(e).__name__}: {e}) -- "
                  f"nothing proposed; story left active.")
            _notify("OSIRIS sprint", f"Story #{story['id']}: run could not be recorded -- nothing proposed")
            if isinstance(e, genome_ledger.LedgerAppendUnknown):
                _block_apply_persistently(f"a sprint_run ledger append for story #{story['id']} "
                                          f"may be half-committed: {e}")
            break
        print(f"[*] Run recorded: {run_id}")
        if proposal is None:
            last = attempts[-1]["reason"].strip()
            print(f"[!] story #{story['id']}: no candidate passed in {k} -- marking failed.")
            if _last_sandbox["path"]:
                print(f"[*] Last sandbox log: /why  ({_last_sandbox['path']})")
            sprint_manager.set_status(story["id"], "failed")
            _notify("OSIRIS sprint", f"Story #{story['id']}: no candidate passed in {k} -- nothing proposed")
            _organism_telemetry(
                f"SPRINT_STORY_FAILED id={story['id']} candidates={k} "
                f"reason={last[-150:].replace(chr(10), ' ')} [PROVENANCE: COMPUTED]"
            )
            continue
        content = proposal["module"]

        story_meta = {"id": story["id"], "source": story["source"], "trait": trait,
                      "target": os.path.realpath(target) if target else None,
                      "run_id": run_id, "candidate_sha256": candidate_sha}
        if not _propose_write(write_path, content, allow_self_modify, story_meta):
            sprint_manager.set_status(story["id"], "failed")
            _notify("OSIRIS sprint", f"Story #{story['id']}: candidate passed but its write path was rejected")
            continue
        _notify("OSIRIS sprint", f"Story #{story['id']}: candidate {len(attempts)}/{k} passed the sandbox -- "
                                 f"review it; nothing is written until /apply")
        print(f"[*] story #{story['id']}: candidate {len(attempts)}/{k} passed -- marked 'proposed'; "
              f"becomes 'done' only on /apply.")
        sprint_manager.set_status(story["id"], "proposed")
        _organism_telemetry(
            f"SPRINT_STORY_PROPOSED id={story['id']} complexity={story['complexity']} "
            f"candidate={len(attempts)} k={k} [PROVENANCE: VERIFIED_LOGIC]"
        )
        remaining = len(active) - active.index(story) - 1
        if remaining:
            print(f"[*] Halting here so this proposal isn't overwritten -- {remaining} active "
                  f"stor{'y' if remaining == 1 else 'ies'} left for the next /sprint execute.")
        break

    _sprint_log_velocity()


def _sprint_log_velocity():
    """Real per-run velocity/pass-rate, mirrored to Neon like every other
    real recorded outcome this session -- COMPUTED, not a new provenance
    tag (this describes a real local computation over the backlog, same
    epistemic status as any other locally-computed number, regardless of
    which subsystem produced it)."""
    counts, _stories = sprint_manager.summary()
    done = counts.get("done", 0)
    failed = counts.get("failed", 0)
    total = done + failed
    rate = (done / total) if total else 0.0
    line = f"SPRINT_VELOCITY done={done} failed={failed} pass_rate={rate:.2f} [PROVENANCE: COMPUTED]"
    _organism_telemetry(line)


def _sprint_review():
    """'/sprint review': real summary from the actual backlog state."""
    counts, stories = sprint_manager.summary()
    print("\n" + "─" * 65)
    print(" 📋 Sprint review")
    print("─" * 65)
    if not stories:
        print("  (backlog is empty -- run /vision sync-sprint to seed it)")
    for status in ("backlog", "active", "proposed", "done", "failed"):
        print(f"  {status:<10} {counts.get(status, 0)}")
    done_or_failed = [s for s in stories if s["status"] in ("done", "failed")]
    if done_or_failed:
        print("\n  Recent outcomes:")
        for s in done_or_failed[-5:]:
            print(f"   #{s['id']} [{s['status']}] {s['text']}")
    print()


# --- /ignite ("Metamorphosis trigger"): Engine 1 reads genome.json, syncs
# dormant_traits from the operator's /gap entries in prompt_library.json,
# and promotes mutation_rate-scaled structural targets straight to 'active'
# in the SAME backlog /sprint plan|execute already use -- there is no
# parallel execution path. /sprint execute still runs the sandbox gate and
# still needs /apply per file; a target that resolves to a protected osiris
# script is still rejected by _check_write_safety unless re-run with
# --allow-self-modify, same as every other write. genome.json's generation
# only increments once a structural story's code has actually landed on
# disk (see _apply_pending_write), never merely on a sandbox pass.
IGNITE_STORY_RE = re.compile(r"^\[structural\] implement dormant trait: (.+)$")

ACTIVE_TRAITS_SEED = [
    "dual_engine_repl",                # Engine 1 regex router + Engine 2 local/cloud synthesis
    "organism_nclm_online_learning",   # Engine 3: real gradient step per exchange
    "cusum_drift_detection",           # Engine 3 loss change-point detector
    "gemini_vision_ingestion",         # /vision latest: real Gemini multimodal calls
    "vision_sync_sprint_indexer",      # /vision sync-sprint: incremental hash-based digest
    "agile_sprint_loop",               # sprint_manager: /sprint plan|execute|review
    "test_driven_auto_enhance",        # sandbox-verify before any diff is ever shown
    "proot_sandboxed_execution",       # _run_sandboxed_test's proot-contained test runs
    "provenance_ledger",               # [PROVENANCE: ...] tagging on every telemetry line
    "supabase_telemetry_mirror",       # db_ledger.sync_line
    "neon_postgres_telemetry_mirror",  # db_ledger.sync_line_neon
    "consensus_cross_check",           # /consensus
    "adaptive_intent_confidence",      # Engine 1's routing-outcome feedback loop
    "deterministic_dd_generator",      # algorithmic_dd_generator.py
    "ai_gateway_bridge",               # gateway_bridge.py
]


def _ignite_in_flight():
    """Traits already queued, in flight, or done -- never promoted again
    (2026-09-23: two /ignite calls queued the same trait as #14 and #15)."""
    in_flight = set()
    for s in sprint_manager.get_backlog()["stories"]:
        m = IGNITE_STORY_RE.match(s["text"])
        if m and s["source"] == "ignite" and s["status"] in ("backlog", "active", "proposed", "done"):
            in_flight.add(m.group(1))
    return in_flight


def _ignite_eligible(g) -> int:
    """How many traits /ignite could promote now: trusted dormant traits not
    already queued/done, plus /gap entries not yet scanned into the genome.
    A trait whose story is done but that named no target module stays
    dormant without being eligible -- counting it made /status recommend an
    /ignite that then found nothing (2026-09-24, trait stale-home-test)."""
    known = {e["text"] for e in g["dormant_traits"]} | set(g["active_traits"])
    queued = _ignite_in_flight()
    eligible = sum(1 for e in g["dormant_traits"]
                   if e.get("source") == genome.CAPABILITY_GAP_SOURCE and e["text"] not in queued)
    return eligible + len(genome._recorded_gaps() - known)


def _ignite(command: str = ""):
    """'/ignite' (alias '/metamorphosis'). See module comment above."""
    genome.init_if_missing(ACTIVE_TRAITS_SEED)
    new_gaps = genome.refresh_dormant_traits()
    g = genome.get()
    targets = genome.pick_ignite_targets(exclude=_ignite_in_flight())
    untrusted = genome.untrusted_dormant_count()

    print("\n" + "─" * 65)
    print(" 🧬 /ignite -- Metamorphosis trigger")
    print("─" * 65)
    print(f"  organism_id   {g['organism_id']}")
    print(f"  generation    {g['generation']}")
    print(f"  mutation_rate {g['mutation_rate']}")
    if new_gaps:
        print(f"  +{len(new_gaps)} new dormant trait(s) found in prompt_library.json")
    if untrusted:
        print(f"  !{untrusted} dormant_trait entr{'y' if untrusted == 1 else 'ies'} present but NOT "
              f"eligible for promotion (not recorded with /gap -- inspect genome.json)")
    if not targets:
        print("\n  (no eligible dormant traits to ignite yet. A gap becomes eligible only "
              "when you draft it with /gap and activate it from /gaps.)\n")
        return

    print(f"\n  Promoting {len(targets)} structural target(s) to the sprint backlog:")
    for trait in targets:
        story = sprint_manager.add_story(
            f"[structural] implement dormant trait: {trait}", complexity=3, source="ignite"
        )
        sprint_manager.set_status(story["id"], "active")
        print(f"   #{story['id']} {trait}")

    _organism_telemetry(
        f"IGNITE_TRIGGER generation={g['generation']} promoted={len(targets)} "
        f"mutation_rate={g['mutation_rate']} [PROVENANCE: COMPUTED]"
    )
    print("\n  Run /sprint execute to attempt these (sandbox-gated, needs /apply per "
          "file same as always). Generation only bumps once a story's code actually "
          "lands on disk, not merely on sandbox pass.\n")


def _code_fingerprint():
    """SHA-256 over bin/osiris and every bin/*.py, to detect code that changed
    on disk after this REPL started (it keeps running the old code)."""
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for p in sorted(glob.glob(os.path.join(here, "*.py")) + [os.path.abspath(__file__)]):
        try:
            with open(p, "rb") as f:
                h.update(p.encode() + f.read())
        except OSError:
            pass
    return h.hexdigest()


_STARTUP_FINGERPRINT = _code_fingerprint()


def _git_state():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        import subprocess
        head = subprocess.run(["git", "-C", here, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", here, "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return head or "?", bool(dirty)
    except Exception:
        return "?", False


def _synth_chain():
    """Engine 2's fallback chain as it will actually run: Gemini if it has a
    key, then the local model. (The AI Gateway was removed on the operator's
    request, 2026-09-24.)"""
    return " → ".join((["gemini"] if gemini_bridge.is_configured() else []) + [CODE_MODEL])


def _last_bench_run():
    """The newest bench round as one dict. Old rounds are one "bench_run"
    entry; since cb3e4d2 a round is bench_run_start / bench_task... /
    bench_run_end sharing a run_id, and the last line alone (the end) has no
    backend, model, k or suite -- /status printed "None k=None ... suite None"
    (on-device, 2026-09-24). Merged here: identity from the start, summary
    and status from the end; a start with no end is status "unfinished"."""
    path = os.path.join(os.path.expanduser("~"), ".osiris", "bench", "results.ledger.jsonl")
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return None
    if not entries:
        return None
    last = entries[-1]
    if last.get("kind") not in ("bench_run_start", "bench_task", "bench_run_end"):
        return last
    rid = last.get("run_id")
    start = next((e for e in reversed(entries) if e.get("kind") == "bench_run_start" and e.get("run_id") == rid), {})
    end = next((e for e in reversed(entries) if e.get("kind") == "bench_run_end" and e.get("run_id") == rid), None)
    merged = dict(start)
    if end:
        merged.update(summary=end.get("summary") or {}, status=end.get("status"))
    else:
        done = sum(1 for e in entries if e.get("kind") == "bench_task" and e.get("run_id") == rid)
        merged.update(summary={"tasks": done}, status="unfinished")
    return merged


PASTE_START, PASTE_END = "\x1b[200~", "\x1b[201~"  # bracketed paste (DECSET 2004)


def _read_unit():
    """One unit of input: (text, pasted). A typed line, or -- when the
    terminal brackets pastes -- the WHOLE paste, however many lines, ending
    at the paste-end marker plus whatever was typed after it before Enter.
    A paste without a final newline therefore waits for Enter instead of
    merging its last line into the next thing typed (2026-09-24: "... cancel
    the draft." + "2" arrived as one message and was answered)."""
    line = sys.stdin.readline()
    if not line:
        raise EOFError("stdin closed")
    if PASTE_START not in line:
        return line, False
    buf = line
    while PASTE_END not in buf:
        more = sys.stdin.readline()
        if not more:
            break
        buf += more
    before, _, rest = buf.partition(PASTE_START)
    body, _, after = rest.partition(PASTE_END)
    typed = after.strip()
    if not before.strip() and "\n" not in body.strip() and re.fullmatch(r"\d{1,2}|[A-Za-z]|/\S.*", typed):
        # Termux sends a long paste as several bracketed pieces; a last piece with
        # no newline waits in the line until Enter, so a menu key typed next
        # arrived glued to it: "### Research brief was draft-only" + "4" became
        # one new request (on-device, 2026-09-24). The piece rejoins its paste;
        # the key runs on the card on screen.
        _rejoin_paste_tail(body, typed)
        return after, False
    return before + body + after, True


def _rejoin_paste_tail(piece: str, key: str):
    piece = piece.strip("\n")
    if _intent_state.get("pasted") and _intent_state.get("text"):
        _intent_state["text"] = _intent_state["text"].rstrip("\n") + "\n" + piece
        print(f"[*] The end of your last paste arrived with your key -- added it to that paste; running {key}.")
    else:
        print(f"[*] A pasted fragment arrived with your key -- set aside, not used; running {key}.")


def _ask(prompt: str) -> str:
    """One line for a form field. A multi-line or very long paste is refused
    (and asked again) instead of being spread across the following fields
    (2026-09-24: a pasted 25-line answer filled a whole /gap draft)."""
    while True:
        print(prompt, end="", flush=True)
        text, pasted = _read_unit()
        text = text.strip()
        tty = getattr(sys.stdin, "isatty", lambda: False)()
        burst = not pasted and tty and _more_input_waiting(0.05)  # unbracketed paste still arriving
        if burst:
            while _more_input_waiting(0.05):
                text += "\n" + sys.stdin.readline().rstrip("\n")
        if "\n" in text or len(text) > 400:
            n = text.count("\n") + 1
            print(f"\n[!] This answer takes one line; that was {n} line(s), {len(text)} characters -- "
                  f"not used. Type it again (0 cancels).")
            continue
        return "0" if text.lower() == "/cancel" else text  # /cancel leaves any form, like 0


_TTY_SAVED = {"attrs": None}


def _terminal_setup(on: bool):
    """Bracketed paste on (and ECHOCTL off, so its markers are not echoed as
    ^[[200~) while the REPL runs; everything restored on exit. Terminals only."""
    if not (getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)()):
        return
    try:
        import termios
        fd = sys.stdin.fileno()
        if on:
            _TTY_SAVED["attrs"] = termios.tcgetattr(fd)
            attrs = termios.tcgetattr(fd)
            attrs[3] &= ~getattr(termios, "ECHOCTL", 0)
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        elif _TTY_SAVED["attrs"] is not None:
            termios.tcsetattr(fd, termios.TCSANOW, _TTY_SAVED["attrs"])
    except Exception:
        pass
    sys.stdout.write("\x1b[?2004h" if on else "\x1b[?2004l")
    sys.stdout.flush()


def _ask_list(prompt: str):
    """Lines until an empty one; None if the operator types 0 (cancel)."""
    print(prompt)
    items = []
    while True:
        line = _ask("   + ")
        if not line:
            return items
        if line == "0":
            return None
        items.append(line)


def _gap_card(d, ui):
    probs = gaps.problems(d)
    rows = [("current", "Outcome", d["outcome"] or "(none)"),
            ("current", "Area", d["area"] or "(none)")]
    rows += [("research", "Accept", a) for a in d["acceptance"]] or [("review", "Accept", "(none)")]
    rows += [("idle", "Scope", s) for s in d["scope"]] or [("idle", "Scope", "unknown -- investigation needed")]
    rows += [("idle", "Must not", c) for c in d["constraints"]]
    target = gaps.target_module(d)
    rows.append(("model", "Ignite", f"story targets {target}" if target else "nothing: no .py target yet"))
    rows += [("review", "Not ready", p) for p in probs] or [("verified", "Ready", "can be activated from /gaps")]
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    return ui.panel(f"GAP{' #' + str(d['id']) if d.get('id') else ''} · {d.get('status', 'draft').upper()}",
                    inner.facts(rows).split("\n"), tone="model")


def _gap(text: str = ""):
    """'/gap [outcome]': a guided capability-gap DRAFT. Five short answers,
    then a review card. A saved draft is inert; only activating it from
    /gaps makes it a trusted gap that /ignite can turn into a story (the old
    one-line /gap recorded it at once -- see gaps.py, story #25)."""
    ui = osiris_ui.Canvas()
    print("\n" + ui.panel("CAPABILITY GAP · DRAFT", [
        "Five short answers. 0 cancels at any step.",
        ui.dim("A saved draft starts nothing: activate it from /gaps when it is ready.")], tone="model"))
    try:
        outcome = text.strip()
        if outcome:
            print(f" Outcome so far: {outcome}")
            a = _ask(" 1/5 [Enter] keep it, or type a clearer one: ")
            if a == "0":
                raise KeyboardInterrupt
            outcome = a or outcome
        else:
            outcome = _ask(" 1/5 What must become true? ")
            if outcome in ("", "0"):
                raise KeyboardInterrupt
        print(" 2/5 Area:")
        for i, name in enumerate(gaps.AREAS, start=1):
            print(f"   [{i}] {name}")
        a = _ask("   number: ")
        if a == "0":
            raise KeyboardInterrupt
        area = gaps.AREAS[int(a) - 1] if a.isdigit() and 1 <= int(a) <= len(gaps.AREAS) else None
        acceptance = _ask_list(" 3/5 How will OSIRIS check it? One per line, empty line when done.")
        if acceptance is None:
            raise KeyboardInterrupt
        scope = _ask_list(" 4/5 Target files (e.g. bin/replay.py). Empty line = unknown.")
        if scope is None:
            raise KeyboardInterrupt
        constraints = _ask_list(" 5/5 Must NOT change (optional). Empty line to skip.")
        if constraints is None:
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("[*] Gap draft cancelled -- nothing saved.\n")
        return
    d = gaps.new_draft(outcome, area, acceptance, scope, constraints)
    print(_gap_card(d, ui))
    if _ask(" [1] Save draft  [0] Discard: ") != "1":
        print("[*] Discarded -- nothing saved.\n")
        return
    d = gaps.save(d)
    session_state.set_focus(d["outcome"], "engineering", f"gap draft #{d['id']}")
    ready = not gaps.problems(d)
    print(f"\n[*] Saved gap draft #{d['id']} ({'ready to activate' if ready else 'not ready yet'}). "
          f"It starts nothing until you activate it: /gaps (I on /home).")
    _home()  # state changed: a fresh menu, so the next key is not refused as out of date


def _gaps(command: str = "/gaps"):
    """'/gaps': the gap drafts, numbered; '/gaps activate N' makes a READY
    draft a trusted gap (asks first); '/gaps delete N' removes a draft."""
    ui = osiris_ui.Canvas()
    parts = command.split()
    if len(parts) == 3 and parts[1] in ("activate", "delete") and parts[2].isdigit():
        d = gaps.get(int(parts[2]))
        if d is None:
            print(f"\n[!] No gap draft #{parts[2]}.\n")
            return
        print("\n" + _gap_card(d, ui))
        if parts[1] == "delete":
            if _ask_yes(f"Delete gap draft #{d['id']}?"):
                print("[*] Deleted." if gaps.delete(d["id"]) else "[!] Only drafts can be deleted.")
                _home()
            return
        if d["status"] != "draft":
            print(f"[!] Gap #{d['id']} is already {d['status']}.\n")
            return
        if gaps.problems(d):
            print("[!] Not ready -- fix the points above in a new /gap draft.\n")
            return
        print(f" /ignite will receive exactly: {gaps.trait_text(d)}")
        if not _ask_yes(f"Activate gap #{d['id']}? It becomes a trusted gap /ignite can turn into a sprint story."):
            print("[*] Left as a draft.\n")
            return
        genome.init_if_missing(ACTIVE_TRAITS_SEED)
        ok, message = gaps.activate(d["id"], genome.record_gap)
        print(f"\n[*] Gap #{d['id']} active. /ignite will promote it." if ok else f"\n[!] Not activated: {message}")
        _home()
        return
    items = gaps.drafts()
    if not items:
        print("\n[*] No gap drafts. /gap (H on /home) starts one.\n")
        return
    _pending_suggestions.clear()
    entries, n = [], 0
    for d in items:
        ready = not gaps.problems(d)
        state = d["status"] if d["status"] != "draft" else ("draft, ready" if ready else "draft, not ready")
        entries.append(("·", f"#{d['id']} [{state}] {d['outcome'][:60]}"))
        if d["status"] == "draft":
            n += 1
            _pending_suggestions[str(n)] = f"/gaps {'activate' if ready else 'delete'} {d['id']}"
            entries.append((str(n), f"{'Activate' if ready else 'Delete'} #{d['id']}"))
    lines = [f"{ui.key(k)} {l}" if k != "·" else f"    {l}" for k, l in entries]
    print("\n" + ui.panel("GAP DRAFTS", lines + ["", ui.dim("Activating asks first. A not-ready draft cannot be "
                                                         "activated: start a clearer /gap.")]) + "\n")


def _status_next_step(pending, counts, dormant, stale):
    """Exactly one recommended command, from fixed rules in priority order."""
    if _apply_block_reason():
        if os.path.exists(APPLY_BLOCK_FILE):
            return f"reconcile the genome ledger (see {APPLY_INCIDENT_LOG}), then delete {APPLY_BLOCK_FILE}"
        return f"read {APPLY_INCIDENT_LOG}, fix the ledger, then restart osiris"
    if stale:
        return "exit and restart osiris -- it is running code that changed on disk"
    if pending:
        return "/apply (or any other input to be asked about discarding it)"
    if counts.get("active"):
        return "/sprint execute"
    if counts.get("backlog"):
        return "/sprint plan"
    if dormant:
        return "/ignite"
    return "/gap (a guided capability-gap draft), or G to benchmark a mentor"


NOTIFY_TIMEOUT = 5  # seconds; termux-notification can hang when the Termux:API app is missing


def _notify(title: str, content: str, timeout: float = NOTIFY_TIMEOUT) -> bool:
    """Best-effort Android notification through Termux:API, for results you
    may have switched apps while waiting on. Callers pass only facts OSIRIS
    computed (story id, outcome) -- never code, prompts or model text.
    Returns False, silently, if termux-notification is absent, fails or
    exceeds timeout; OSIRIS_NO_NOTIFY=1 turns it off."""
    if os.environ.get("OSIRIS_NO_NOTIFY") == "1":
        return False
    exe = shutil.which("termux-notification")
    if not exe:
        return False
    import subprocess
    try:
        subprocess.run([exe, "--id", "osiris", "--title", title, "--content", content],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=timeout)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


BIN_DIR = os.path.dirname(os.path.abspath(__file__))
# (label, argv, timeout seconds). Both only read state and call no model; the
# bench does run its reference solutions in the sandbox (and so writes
# sandbox logs). Bench exit 3 = the sandbox cannot run here, e.g. inside
# proot-distro -- reported as such, not as a failure.
CHECK_COMMANDS = [
    ("Ledger and runs", [sys.executable, os.path.join(BIN_DIR, "run_record.py")], 120),
    ("Bench suite", [sys.executable, os.path.join(BIN_DIR, "osiris_bench.py"), "--check"], 900),
]


def _run_show(command: str = ""):
    """'/run show [run] [n]': run_record.show() for the newest run, or the run
    whose id contains <run>; with n, candidate n's code and test. Read-only."""
    args = command.split()[2:]
    try:
        run_id = run_record.resolve(args[0] if args else None)
    except LookupError as e:
        print(f"\n[!] /run show: {e}\n")
        return
    n = None
    if len(args) > 1:
        if not args[1].isdigit():
            print(f"\n[!] /run show: candidate must be a number, not {args[1]!r}\n")
            return
        n = int(args[1])
    try:
        led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        entries = led.chain if led else []
    except Exception as e:
        print(f"[!] genome ledger unreadable ({type(e).__name__}: {e}) -- run shown unverified")
        entries = []
    print("\n" + run_record.show(run_id, entries, n, root=os.getcwd()) + "\n")


def _runs_stats():
    """'/runs stats' (or '/runs'): run_record.stats() -- counts over every
    ledger-vouched run that verifies. Read-only."""
    try:
        led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        entries = led.chain if led else []
    except Exception as e:
        print(f"\n[!] /runs stats: genome ledger unreadable ({type(e).__name__}: {e}) -- no run can be "
              f"counted as verified.\n")
        return
    print("\n" + run_record.stats(entries) + "\n")


def _check():
    """'/check': runs CHECK_COMMANDS, prints their output, then one summary
    line, also sent as a notification. No model call; nothing proposed."""
    import subprocess
    parts, ok = [], True
    for label, argv, timeout in CHECK_COMMANDS:
        print(f"\n[*] /check: {label}")
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            print((r.stdout + r.stderr).rstrip())
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = None
        except OSError as e:
            print(f"[!] could not run: {e}")
            code = -1
        if code == 0:
            parts.append(f"{label} OK")
        elif code == 3 and label == "Bench suite":
            parts.append(f"{label} not run (sandbox unavailable here)")
        else:
            ok = False
            parts.append(f"{label} FAILED ({'timed out' if code is None else f'exit {code}'})")
    summary = " · ".join(parts)
    print(f"\n{'✅' if ok else '[!]'} {summary}\n")
    _notify("OSIRIS check " + ("passed" if ok else "FAILED"), summary)


# What the last /home menu was built from, and the entries it registered: a
# number from that menu is refused once this state differs (the menu is
# redrawn instead), since menu numbers otherwise outlive other commands.
_home_menu = {"fingerprint": None, "entries": {}, "labels": {}}


def _home_fingerprint():
    """The state /home's entries depend on: story ids/statuses, the pending
    write, the /apply block, and the genome's dormant traits and recorded gaps."""
    _counts, stories = sprint_manager.summary()
    try:
        g = genome.get()
        traits = (g["generation"], sorted(e["text"] for e in g["dormant_traits"]), sorted(g["active_traits"]))
    except Exception:
        traits = None
    try:
        recorded = sorted(genome._recorded_gaps())
    except Exception:
        recorded = None
    drafts = [(d["id"], d["status"]) for d in gaps.drafts()]
    return json.dumps([[(s["id"], s["status"]) for s in stories], _pending_write["path"],
                       _apply_block_reason(), traits, recorded, drafts], default=str)


TAP_TIMEOUT = 300  # seconds to wait for a tap before falling back to typing
# queue: numbers tapped, fed to the main loop as if typed. again: redraw the
# sheet after the tapped action finishes (cancelling the sheet stops that).
_tap_state = {"queue": [], "again": False}


def _tap(redraw: bool = True):
    """'/tap': redraws /home and shows its entries as an Android bottom sheet
    (termux-dialog, Termux:API app). The tapped entry is queued as its NUMBER,
    so it goes through exactly the checks a typed number does -- fixed
    commands only, stale-menu refusal, never /apply. Returns that number, or
    None on cancel, timeout, a missing termux-dialog or an unexpected reply.
    redraw=False (the sheet reopening after a tapped action) rebuilds the menu
    without printing it, so that action's output stays in view above the
    sheet -- on-device, a reprinted menu pushed short output under it."""
    _home(quiet=not redraw)
    labels = _home_menu["labels"]
    exe = shutil.which("termux-dialog")
    if not exe:
        print("[!] /tap: termux-dialog not found (pkg install termux-api, plus the Termux:API app) -- "
              "type the number instead.\n")
        return None
    nums = sorted(labels, key=int)
    values = [labels[n].replace(",", " ·") for n in nums]  # -v is comma-delimited
    import subprocess
    try:
        r = subprocess.run([exe, "sheet", "-t", "OSIRIS", "-v", ",".join(values)], capture_output=True,
                           text=True, timeout=TAP_TIMEOUT, stdin=subprocess.DEVNULL)
        reply = json.loads(r.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        print("[*] /tap: no selection (dialog failed or timed out) -- type a number or /tap.\n")
        return None
    idx = reply.get("index") if isinstance(reply, dict) else None
    same = lambda a, b: " ".join(str(a).split()) == " ".join(str(b).split())  # dialogs may reflow spaces
    if not isinstance(idx, int) or not 0 <= idx < len(nums) or not same(reply.get("text"), values[idx]):
        print("[*] /tap: nothing selected -- type a number or /tap.\n")
        return None
    return nums[idx]


def _home(command: str = "", quiet: bool = False):
    """'/home': the phone menu. A few facts, then numbered actions -- each one
    a fixed command template filled only with a story id read from the
    backlog, registered for the next input like /suggest's numbers. Unlike
    /suggest, no model writes any of it, and no number ever means /apply:
    writing a proposal stays a typed /apply. '/home stories' lists every
    active story by number. Read-only."""
    say = (lambda *a, **k: None) if quiet else print  # quiet: register the menu, print nothing
    _pending_suggestions.clear()
    counts, stories = sprint_manager.summary()
    active = [s for s in stories if s["status"] == "active" and sprint_manager.plannable(s)]
    if command.strip().lower() == "/home stories":
        if not active:
            say("\n[!] No active stories. Run /sprint plan to activate backlog stories.\n")
            return
        labels = {}
        for i, s in enumerate(active[:9], start=1):
            _pending_suggestions[str(i)] = f"/sprint execute #{s['id']}"
            labels[str(i)] = f"#{s['id']} {s['text'][:50]}"
        ui = osiris_ui.Canvas()
        say("\n" + ui.actions("ACTIVE STORIES", [(k, f"#{s['id']} {s['text'][:70]}")
                                                for k, s in zip(labels, active[:9])],
                               "A number runs that story in the sandbox: a proposal, never applied.") + "\n")
        _home_menu.update(fingerprint=_home_fingerprint(), entries=dict(_pending_suggestions), labels=labels)
        return

    try:
        g = genome.get()
        gen = f"generation {g['generation']}"
    except Exception:
        g, gen = None, "genome not initialized"
    pending = _pending_write["path"]
    blocked = _apply_block_reason()
    ui = osiris_ui.Canvas()
    say("\n" + ui.header("LIVING LANGUAGE CONSOLE",
                         f"{gen} · {counts.get('active', 0)} active, {counts.get('backlog', 0)} backlog"))
    facts = []
    if pending:
        facts.append(("review", "Pending write", pending))
    if blocked:
        facts.append(("blocked", "/apply", f"BLOCKED: {blocked[:140]}"))
    ikind, itext = _integrity()
    facts.append((ikind, "Integrity", itext))
    f = session_state.get_focus()
    facts.append(("current", "Focus", f"{f['goal']} · {f['kind']} · since {f['since']}" if f else
                  "none yet -- say what you are working on, or /focus <text>"))
    say(ui.facts(facts))
    nb = _next_best()
    say(ui.panel("NEXT BEST ACTION", [f"{ui.key('N')} {nb['label']}", ui.dim(f"why: {nb['why']}"),
                                      ui.dim(f"will: {nb['will']}"), ui.dim(f"won't: {nb['wont']}")], tone="rich"))

    options = []
    has_runs = os.path.isdir(run_record.RUNS_DIR) and bool(os.listdir(run_record.RUNS_DIR))
    if pending:
        options += [("This proposal's run: every candidate", "/run show"),
                    ("Why did the last sandbox run pass or fail", "/why"), ("Full status", "/status")]
    elif not blocked:
        if active:
            s = active[0]
            options.append((f"Run story #{s['id']}: {s['text'][:40]}", f"/sprint execute #{s['id']}"))
        if len(active) > 1:
            options.append((f"Pick one of {len(active)} active stories", "/home stories"))
        if not active and any(st["status"] == "backlog" and sprint_manager.plannable(st) for st in stories):
            options.append(("Plan a sprint (activate backlog stories)", "/sprint plan"))
        if g is not None:
            eligible = _ignite_eligible(g)
            if eligible:
                options.append((f"Ignite ({eligible} recorded gap{'s' if eligible != 1 else ''})", "/ignite"))
        if has_runs:
            options.append(("Last run: candidates and outcome", "/run show"))
            options.append(("Run statistics: models, outcomes, failures", "/runs stats"))
        options.append(("Full status", "/status"))
        options.append(("Check everything (ledger, runs, bench)", "/check"))
    else:
        options.append(("Full status (explains the block)", "/status"))
        options.append(("Check everything (ledger, runs, bench)", "/check"))
    for i, (label, cmd) in enumerate(options, start=1):
        _pending_suggestions[str(i)] = cmd
    labels = {str(i): label for i, (label, _cmd) in enumerate(options, start=1)}
    # Letters: the same read-only tools in every state, always on the same key.
    # Only numbers go on the /tap sheet (labels); both pass the stale-menu check.
    letters = _home_letters(pending)
    for k, _label, cmd in letters:
        _pending_suggestions[k] = cmd
    say(ui.actions("NEXT MOVES", [(str(i), l) for i, (l, _c) in enumerate(options, start=1)]
                   + [(k, l) for k, l, _c in letters if k not in LETTERS_NOT_LISTED],
                   "Type a number or letter -- or just talk to OSIRIS: questions are answered, "
                   "requests get a card of fixed next steps. Letters work from any screen · Enter sends · "
                   "a paste stays together · forms take one line · /cancel goes back · /tap for buttons"))
    if pending:
        say("   Type /apply to write it; anything else asks before discarding.")
    say()
    _home_menu.update(fingerprint=_home_fingerprint(), entries=dict(_pending_suggestions), labels=labels)


LETTERS_NOT_LISTED = {"N", "W"}  # N has its own card on /home; W is offered where it applies


def _integrity():
    """(marker kind, one line): whether OSIRIS's records agree with themselves,
    recomputed each time from the genome ledger chain, the /apply block, the
    bench ledger chain and every bench artifact hash, and any pending write.
    verified = consistent; review = something waits on you; blocked = broken."""
    parts, kind = [], "verified"
    try:
        if os.path.exists(genome_ledger.DEFAULT_PATH):  # constructing a Ledger would create the file
            led = genome_ledger.GenomeLedger()
            ok = led.verify()
            # The count is entries, not failures: "BROKEN (3)" was read as three
            # broken records when one entry of three was (2026-10-02).
            parts.append(f"genome ledger valid ({len(led.chain)} entries)" if ok else
                         f"genome ledger BROKEN ({len(led.chain)} entries): {led.problem()}")
            kind = kind if ok else "blocked"
    except Exception as e:
        parts.append(f"genome ledger unreadable ({type(e).__name__})")
        kind = "blocked"
    if _apply_block_reason():
        parts.append("/apply BLOCKED")
        kind = "blocked"
    try:
        import protege
        entries, problem = protege.load_ledger()
        if problem and "does not exist" not in problem:
            parts.append("bench evidence BROKEN")
            kind = "blocked"
        elif not problem:
            cands, _ = protege.candidates(entries)
            checked, bad = protege.verify_artifacts(cands)
            parts.append(f"bench evidence {checked} files verified" if not bad else
                         f"bench evidence: {len(bad)} files missing or altered")
            kind = kind if not bad else ("blocked" if kind == "blocked" else "review")
    except Exception as e:
        parts.append(f"bench evidence unreadable ({type(e).__name__})")
        kind = "blocked"
    if _pending_write["path"]:
        parts.append("a write awaits /apply")
        kind = "review" if kind == "verified" else kind
    return kind, " · ".join(parts) or "nothing recorded yet"


def _home_letters(pending=None):
    """The lettered tools: fixed commands, the same in every state, so a letter
    works from any screen unless the menu on screen uses it (see main loop)."""
    pending = _pending_write["path"] if pending is None else pending
    letters = []
    if not pending and glob.glob(os.path.join(SANDBOX_LOG_DIR, "*.log")):
        letters.append(("A", "Why the last sandbox run passed or failed", "/why"))
    letters += [("B", "Engine 1: intent-routing confidence", "/intent status"),
                ("C", "Engine 3 (NCLM): training status", "/organism status"),
                ("D", "Appearance: rich · plain · accessible", "/ui"),
                ("E", "Help: every command", "/help"),
                ("F", "Mentors: which model the evidence favors", "/mentors"),
                ("G", f"Benchmark a mentor ({BENCH_DEFAULT_MODEL}, 3 tasks)", "/bench"),
                ("H", "Capture a capability gap (guided draft)", "/gap")]
    n_drafts = sum(1 for d in gaps.drafts() if d["status"] == "draft")
    if n_drafts:
        letters.append(("I", f"Gap drafts ({n_drafts}): review, activate", "/gaps"))
    letters.append(("J", "Draft a quantum / research experiment brief", "/experiment"))
    n_src, n_hyp = len(research.sources()), len(research.hypotheses())
    letters.append(("L", f"Research lab: papers, links, concept map, hypotheses ({n_src} sources, {n_hyp} "
                         f"hypotheses)", "/lab"))
    nb = _next_best()
    letters.append(("N", f"Next best action: {nb['label']}", nb["cmd"]))
    letters.append(("W", "Wrong route? Re-route the last message", "/reroute"))
    return letters


_intent_state = {"text": None}  # the input the last intent card describes; /engage sends it


ANSWER_MODEL = os.environ.get("OSIRIS_ANSWER_MODEL")  # default: CHAT_MODEL (the Architect)


def _grounded_facts():
    """Short, verified lines about OSIRIS's real state -- what an answer may
    state as fact. Read from disk; nothing here comes from a model."""
    facts = []
    counts, _stories = sprint_manager.summary()
    try:
        g = genome.get()
        facts.append(f"OSIRIS genome generation {g['generation']}; {counts.get('active', 0)} active and "
                     f"{counts.get('backlog', 0)} backlog sprint stories.")
    except Exception:
        facts.append("The OSIRIS genome is not initialized yet.")
    if _pending_write["path"]:
        facts.append(f"A proposed file write is waiting for /apply: {_pending_write['path']}.")
    if _apply_block_reason():
        facts.append(f"/apply is BLOCKED: {_apply_block_reason()[:120]}")
    ds = gaps.drafts()
    if ds:
        ready = sum(1 for d in ds if d["status"] == "draft" and not gaps.problems(d))
        facts.append(f"Capability gaps: {sum(d['status'] == 'draft' for d in ds)} drafts ({ready} ready), "
                     f"{sum(d['status'] == 'active' for d in ds)} active.")
    bs = experiments.briefs()
    if bs:
        facts.append(f"Experiment briefs: {len(bs)} saved (simulator-only plans; none has been run).")
    try:
        import protege
        entries, problem = protege.load_ledger()
        if problem:
            facts.append("Mentor benchmark: no verified rounds yet, so no model has been measured.")
        else:
            cands, _ = protege.candidates(entries, protege.current_suite(), protege.current_runner())
            card = protege.scorecard(cands)
            best = max(card.items(), key=lambda kv: kv[1]["ci"][0]) if card else None
            facts.append(f"Mentor benchmark: {sum(m['candidates'] for m in card.values())} scored candidates"
                         + (f"; highest hidden-test pass rate so far {best[0]} ({best[1]['verified']}/"
                            f"{best[1]['candidates']})" if best else "") + ". Routing advice is advisory only.")
    except Exception as e:
        facts.append(f"Mentor evidence unreadable ({type(e).__name__}).")
    ok, _base = _check_ollama_reachable(timeout=1.0)
    facts.append(f"Local models via Ollama: {'reachable' if ok else 'unreachable'}; Architect {CHAT_MODEL}, "
                 f"code model {CODE_MODEL}.")
    facts.append("Menu keys: G benchmark a mentor model, F mentor evidence, H capture a capability gap, "
                 "I review gap drafts, J draft a quantum/research experiment brief, 3/Full status on /home.")
    return facts


KNOWLEDGE_MODEL_PREFERENCE = ("qwen2.5-coder:7b",)  # better instruction-following than the 1B Architect


def _knowledge_model():
    """OSIRIS_ANSWER_MODEL, else the first installed preferred model, else the Architect."""
    if ANSWER_MODEL:
        return ANSWER_MODEL
    try:
        with urllib.request.urlopen(OLLAMA_GEN_URL.rsplit("/api/", 1)[0] + "/api/tags", timeout=2) as r:
            names = {m.get("name") for m in json.load(r).get("models", [])}
        return next((m for m in KNOWLEDGE_MODEL_PREFERENCE if m in names), CHAT_MODEL)
    except Exception:
        return CHAT_MODEL


def _next_best():
    """The one recommended move, from fixed rules over real state:
    label, command, why, what it will do, what it will not do."""
    if _pending_write["path"]:
        return dict(label="Review the pending proposal", cmd="/run show",
                    why=f"a proposed write to {os.path.basename(_pending_write['path'])} is waiting",
                    will="show its candidates and verdicts", wont="write it -- only a typed /apply does")
    ds = gaps.drafts()
    ready = [d for d in ds if d["status"] == "draft" and not gaps.problems(d)]
    if ready:
        return dict(label=f"Review gap draft #{ready[0]['id']}", cmd="/gaps",
                    why=f"gap draft #{ready[0]['id']} is complete and ready to activate",
                    will="list gap drafts; activating asks you first", wont="start any sprint work")
    counts, stories = sprint_manager.summary()
    active = [st for st in stories if st["status"] == "active" and sprint_manager.plannable(st)]
    if active:
        return dict(label=f"Run story #{active[0]['id']} in the sandbox", cmd=f"/sprint execute #{active[0]['id']}",
                    why="an active sprint story is waiting", will="ask the engines for candidates, test them in "
                    "the sandbox, and propose the passing one", wont="write or apply anything")
    try:
        if _ignite_eligible(genome.get()):
            return dict(label="Turn active gaps into sprint stories", cmd="/ignite",
                        why="an activated gap is waiting", will="add backlog stories from active gaps",
                        wont="run or write any code")
    except Exception:
        pass
    try:
        import protege
        if protege.load_ledger()[1]:
            return dict(label=f"Benchmark {BENCH_DEFAULT_MODEL} on 3 tasks", cmd="/bench",
                        why="no model has been measured yet, so no model advice is possible",
                        will="3 local tasks, 1 attempt each, scored by hidden tests (minutes on a phone)",
                        wont="change code, use cloud quota, or change which model OSIRIS calls")
        nb = _next_mentor_round(protege)
        if nb:
            return nb
    except Exception:
        pass
    return dict(label="Capture what you want OSIRIS to do next", cmd="/gap",
                why="nothing is pending, ready or waiting", will="open the 5-step gap form",
                wont="start any work until you activate the draft")


BENCH_LOCAL_MENTORS = ("qwen2.5-coder:7b", "deepseek-coder", "llama3.2:1b")


def _ollama_models():
    """Installed Ollama model names, or None when Ollama cannot be asked."""
    try:
        with urllib.request.urlopen(OLLAMA_GEN_URL.rsplit("/api/", 1)[0] + "/api/tags", timeout=2) as r:
            return {m.get("name") for m in json.load(r).get("models", [])}
    except Exception:
        return None


def _next_mentor_round(protege):
    """The evidence the mentor comparison most needs next: first every
    installed local mentor on the same 3 quick tasks (3 scored candidates
    each), then each on all tasks until it has the 9 the scorecard needs to
    name anything. None when every installed local mentor has that."""
    entries, problem = protege.load_ledger()
    if problem:
        return None
    card = protege.scorecard(protege.candidates(entries, protege.current_suite(), protege.current_runner())[0])
    installed = _ollama_models()
    have = lambda m: installed is None or m in installed or f"{m}:latest" in installed
    n = lambda m: card.get(f"ollama/{m}", {}).get("candidates", 0)
    measured = [f"{m} {card[f'ollama/{m}']['verified']}/{n(m)}" for m in BENCH_LOCAL_MENTORS if n(m)]
    done = ("measured so far: " + ", ".join(measured) + " hidden-test passes") if measured else "nothing measured"
    for need, scope, cmd_tail, will in ((3, "the same 3 tasks", "", "3 local tasks, 1 attempt each"),
                                        (MIN_EVIDENCE_PER_MENTOR, "all 9 tasks", " all", "9 local tasks, 1 attempt each")):
        for m in BENCH_LOCAL_MENTORS:
            if have(m) and n(m) < need:
                return dict(label=f"Benchmark {m} on {scope}", cmd=f"/bench {m}{cmd_tail}".replace(
                            f"/bench {BENCH_DEFAULT_MODEL}", "/bench"),
                            why=f"{done}; {m} has {n(m)} of the {need} candidates a fair comparison needs",
                            will=f"{will}, scored by the same hidden tests (minutes to tens of minutes on a phone)",
                            wont="change code, use cloud quota, or change which model OSIRIS calls")
    return None


MIN_EVIDENCE_PER_MENTOR = 9  # protege.MIN_MENTOR_CANDIDATES


def _next_step_advice():
    """One recommended next move, as a sentence (for code-built answers)."""
    nb = _next_best()
    return f"{nb['why']}: press N to {nb['label'][0].lower() + nb['label'][1:]}"


def _state_counts():
    """Counts of real state, for the since-last-session digest."""
    counts, _ = sprint_manager.summary()
    try:
        gen = genome.get()["generation"]
    except Exception:
        gen = None
    ds = gaps.drafts()
    bench_candidates = bench_runs = 0
    try:
        import protege
        entries, problem = protege.load_ledger()
        if not problem:
            cands, _ = protege.candidates(entries, protege.current_suite(), protege.current_runner())
            bench_candidates = len(cands)
            bench_runs = sum(protege.run_status(entries).values()) + sum(e.get("kind") == "bench_run" for e in entries)
    except Exception:
        pass
    f = session_state.get_focus()
    return {"generation": gen, "active_stories": counts.get("active", 0), "backlog_stories": counts.get("backlog", 0),
            "gap_drafts": sum(d["status"] == "draft" for d in ds), "active_gaps": sum(d["status"] == "active" for d in ds),
            "briefs": len(experiments.briefs()), "bench_candidates": bench_candidates, "bench_runs": bench_runs,
            "corrections": len(session_state.corrections()), "focus": f["goal"] if f else ""}


CLASS_HELP = {"conversation": "just talking -- answer from OSIRIS's state",
              "question": "a question -- answered, nothing created",
              "status": "what is OSIRIS doing -- the facts",
              "benchmark": "measure a model -- bench or mentor evidence",
              "research": "a research idea -- experiment brief, design, arXiv",
              "engineering": "build or change something -- gap, plan, or engines",
              "session_log": "a pasted terminal session -- a digest of what happened"}


def _reroute(command: str = "/reroute"):
    """'/reroute [class]' (W): the operator says the last message was routed
    wrong. Re-routes it as the chosen class and appends the correction to
    ~/.osiris/intent_feedback.jsonl -- feedback for evaluating the router,
    never applied to routing automatically."""
    ui = osiris_ui.Canvas()
    text, orig = _intent_state.get("text"), _intent_state.get("cls")
    if not text:
        print("\n[*] Nothing to re-route yet -- say something first.\n")
        return
    parts = command.split()
    if len(parts) == 2 and parts[1] in intent_router.CLASSES:
        cls = parts[1]
        if cls != orig:
            session_state.record_correction(text, orig, cls)
            print(f"[*] Re-routed as {cls}. Your correction is saved as routing feedback "
                  f"(it does not change the router by itself).")
        _route(text, forced=cls)
        return
    _pending_suggestions.clear()
    entries = []
    for i, cls in enumerate([c for c in intent_router.CLASSES if c != orig], start=1):
        _pending_suggestions[str(i)] = f"/reroute {cls}"
        entries.append((str(i), f"{cls}: {CLASS_HELP[cls]}"))
    _pending_suggestions["0"] = "/home"
    entries.append(("0", "Keep it as it was"))
    excerpt = " ".join(text.split())[:70]
    print("\n" + ui.actions(f"RE-ROUTE · was {orig}", entries, f"Message: {excerpt}") + "\n")


def _focus(command: str = "/focus"):
    """'/focus' shows it, '/focus <text>' sets it, '/focus clear' clears it.
    Display only: the focus never runs or changes anything."""
    arg = command[len("/focus"):].strip()
    if arg.lower() == "clear":
        print("\n[*] Focus cleared.\n" if session_state.clear_focus() else "\n[*] No focus was set.\n")
    elif arg:
        f = session_state.set_focus(arg, "operator", "/focus")
        print(f"\n[*] Focus: {f['goal']}\n" if f else
              f"\n[!] A focus is one short goal (up to {session_state.FOCUS_MAX_WORDS} words) -- not set.\n")
    else:
        f = session_state.get_focus()
        print(f"\n[*] Focus: {f['goal']} ({f['kind']}, since {f['since']}, from {f['source']})\n" if f else
              "\n[*] No focus yet. /focus <what you are working on> sets one; saving a gap or brief does too.\n")


def _short(mentor):
    return mentor.split("/", 1)[-1]


def _reason(r):
    return (r or "").replace("AssertionError: ", "").strip().rstrip(".") or "no reason recorded"


def _english_evidence(want_round=True):
    """Plain-English paragraphs about the mentor evidence, composed by code
    from the verified bench ledger (never by a model)."""
    import protege
    entries, problem = protege.load_ledger()
    if problem:
        return ["Nothing to compare yet: no model has been measured, so OSIRIS cannot say which model writes "
                "better code. Press N (or G) to run the first round."]
    card = protege.scorecard(protege.candidates(entries, protege.current_suite(), protege.current_runner())[0])
    paras = []
    if not card:
        paras.append("No round on the current benchmark has finished a task yet.")
    for m, v in sorted(card.items()):
        s_ = f"{_short(m)} passed {v['verified']} of {v['candidates']} hidden tests."
        if v["false_confidence"]:
            s_ += (f" {v['false_confidence']} time{'s' if v['false_confidence'] != 1 else ''} its own test passed "
                   f"on code the hidden test then rejected (false confidence).")
        if v["no_output"]:
            s_ += f" {v['no_output']} time{'s' if v['no_output'] != 1 else ''} it produced nothing usable."
        paras.append(s_)
    _picks, overall = protege.route(card)
    if overall:
        paras.append(f"On this evidence {_short(overall)} leads -- as advice only; OSIRIS has not changed which "
                     f"model it calls.")
    elif len(card) >= 2:
        paras.append("That is too little evidence to call either model better; more rounds on the same tasks "
                     "are needed.")
    elif card:
        paras.append("There is no second model measured on the same tasks yet, so there is nothing to compare.")
    rnd = protege.latest_round(entries) if want_round else None
    if rnd and rnd["tasks"]:
        lines = []
        for t in rnd["tasks"]:
            if t["delivered"]:
                lines.append(f"{t['task']} passed the hidden test")
            elif t["false_confidence"]:
                lines.append(f"on {t['task']} its own test passed but the hidden test failed: {_reason(t['hidden_reason'])}")
            elif not t["proposed"]:
                lines.append(f"on {t['task']} no candidate passed even its own test")
            else:
                lines.append(f"{t['task']} failed the hidden test: {_reason(t['hidden_reason'])}")
        when = (rnd.get("started") or "")[:16].replace("T", " ")
        state = {"complete": "", "partial": " (stopped early)", "unterminated": " (never finished)"}.get(rnd["status"], "")
        paras.append(f"In the latest round ({_short(rnd['mentor'])}, {when} UTC{state}), " + "; ".join(lines) + ".")
    return paras


def _english_state(text: str, cls: str):
    """Plain-English paragraphs answering a question about OSIRIS itself,
    composed by code from verified records, chosen by what was asked."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    # A pasted block is chosen by its first line (as intent_router does): a
    # rerouted 569-line paste matched gap/brief/focus/help words in its body
    # and got every topic at once (on-device, 2026-09-24).
    low = (lines[0] if len(lines) > 5 else text).lower()
    paras = []
    greeting = cls == "conversation" and re.match(r"\s*(hi|hello|hey|yo|gm|good )", low)
    if re.search(r"false confidence", low):
        paras.append("False confidence means a model's own test passed on code that OSIRIS's hidden test then "
                     "rejected: the model believed its answer was right when it was not. It is why hidden tests, "
                     "not a model's own tests, decide the score.")
        paras += _english_evidence(want_round=True)
    elif re.search(r"bench|mentor|models?\b|qwen|deepseek|llama|fail|round|score|evidence|result|happen|compare|best",
                   low):
        paras += _english_evidence(want_round=True)
    if re.search(r"\bgaps?\b", low):
        ds = gaps.drafts()
        ready = [d for d in ds if d["status"] == "draft" and not gaps.problems(d)]
        paras.append(f"You have {sum(d['status'] == 'draft' for d in ds)} gap draft(s), {len(ready)} ready to activate, "
                     f"and {sum(d['status'] == 'active' for d in ds)} active gap(s)." if ds else
                     "There are no capability gaps yet. H starts one.")
    if re.search(r"brief|experiment|research", low):
        bs = experiments.briefs()
        paras.append(f"There {'is' if len(bs) == 1 else 'are'} {len(bs)} experiment brief(s); none has been run -- "
                     f"briefs are simulator-only plans." if bs else "There are no experiment briefs yet. J drafts one.")
    if re.search(r"focus|working on", low):
        f = session_state.get_focus()
        paras.append(f"Your focus is: {f['goal']} (since {f['since']})." if f else "No focus is set.")
    if re.search(r"what can (you|i) do|help", low):
        paras.append("Talk in plain words: questions are answered, requests get a short card of fixed next steps. "
                     "G benchmarks a model, H captures a capability gap, J drafts an experiment brief, "
                     "N runs the next best action, and E lists every command.")
    if not paras or greeting or cls == "status":
        counts, _ = sprint_manager.summary()
        try:
            gen = f"genome generation {genome.get()['generation']}"
        except Exception:
            gen = "an uninitialized genome"
        opener = "Hello. " if greeting else ""
        summary = [f"{opener}OSIRIS is at {gen}, with {counts.get('active', 0)} active and "
                   f"{counts.get('backlog', 0)} backlog sprint stories."]
        ev = _english_evidence(want_round=False)
        if not any(p in paras for p in ev):  # the full evidence is already there: no second copy
            summary.append(ev[0] if len(ev) == 1 else " ".join(ev[:2]))
        paras = summary + paras
    ikind, itext = _integrity()
    paras.append(("Your records check out: " if ikind == "verified" else "Records need attention: ") + itext + ".")
    paras.append("Next: " + _next_step_advice() + ".")
    return paras


def _state_answer(text: str, cls: str):
    """Answers about OSIRIS itself, in plain English written by code from
    verified records -- no model is asked, so none can misstate them."""
    ui = osiris_ui.Canvas()
    inner = ui.cols - 4
    lines = []
    for i, para in enumerate(_english_state(text, cls)):
        if i:
            lines.append("")
        lines += ui._wrap(para, inner)
    print("\n" + ui.panel("VERIFIED OSIRIS ANSWER · written by code from your records", lines))


def _answer(text: str, cls: str = None):
    """'/ask <text>': questions about OSIRIS are answered by code from
    verified state (_state_answer); knowledge questions by a local model
    that is given NO state facts, so it cannot misstate them. Read-only;
    the fixed next actions for the message's intent class follow."""
    cls = cls or intent_router.classify(text)[0]
    if cls in ("conversation", "status") or intent_router.about_osiris(text):
        _state_answer(text, cls)
        _next_actions(text, cls, answered=True)
        return
    ui = osiris_ui.Canvas()
    ok, _base = _check_ollama_reachable(timeout=1.0)
    if not ok:
        print("\n" + osiris_ui.notice(ui, "review", "ANSWER", "Ollama is not reachable, so no model can answer "
                                     "this. Start it with 'ollama serve'."))
    else:
        model = _knowledge_model()
        print(f"\n{ui.marker('model')} MODEL KNOWLEDGE · {ui.style(model, '1')} "
              f"{ui.dim('· from its training, not verified by OSIRIS · read-only')}")
        simpler = re.match(r"\s*more simply:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        if simpler:
            prompt = ("Explain this in plain words a curious 12-year-old could follow, in at most 3 short "
                      "sentences, with one everyday comparison. No code.\n\nQuestion: " + simpler.group(1)[:2000]
                      + "\nAnswer:")
        else:
            prompt = ("Answer the question accurately in at most 5 plain sentences. If you are not sure, say so. "
                      "Do not write code unless asked.\n\nQuestion: " + text[:2000] + "\nAnswer:")
        reply = query_model(prompt, model, stream=True, timeout=300)
        if reply.strip():
            _spawn_organism_learn(text + "\n" + reply)  # Engine 3 learns from every exchange, as before
        print(ui.dim("A model's answer from its training, not verified by OSIRIS."))
    research = "research" in intent_router.classify(text)[1]
    plain = re.sub(r"^\s*more simply:\s*", "", text, flags=re.IGNORECASE)
    _next_actions(text, "research" if research else cls, answered=True,
                  extra=[("Explain it more simply", "/ask more simply: " + " ".join(plain.split())[:240])])


def _next_actions(text: str, cls: str, answered: bool = False, extra=()):
    """The fixed actions for an intent class, as numbers (0 = home)."""
    ui = osiris_ui.Canvas()
    _pending_suggestions.clear()
    entries, hint = [], ""
    n = 0
    for label, cmd in intent_router.actions_for(cls, text):
        if cmd is None:
            hint = label
            continue
        if answered and cmd.startswith("/ask"):
            continue
        n += 1
        _pending_suggestions[str(n)] = cmd
        entries.append((str(n), label))
    for label, cmd in extra:
        n += 1
        _pending_suggestions[str(n)] = cmd
        entries.append((str(n), label))
    _pending_suggestions["0"] = "/home"
    entries.append(("0", "Home menu"))
    print(ui.actions("NEXT", entries, (hint + " · " if hint else "") +
                     "W if this was routed wrong · or just type what you want next."))
    print()


_last_input = {"pasted": False}


# ------------------------------------------------------------------ research lab
# research.py holds the data and rules; these print it and ask for it. Every
# number registered here is a fixed command; sources are data only.

def _lab(command: str = "/lab"):
    """'/lab' (L): the Research Lab menu. '/lab dna' exports it as DNA::}AI{::Lang."""
    if command.strip().lower() == "/lab dna":
        return _lab_dna()
    ui = osiris_ui.Canvas()
    srcs, hyps = research.sources(), research.hypotheses()
    decided = sum(1 for h in hyps if h.get("outcome"))
    lines = [f"{len(srcs)} source(s) · {len(hyps)} hypothesis(es), {decided} decided by verified evidence",
             ui.dim("Sources are data only: nothing in a paper, link or log runs or changes anything.")]
    last = _intent_state.get("text") if _intent_state.get("pasted") else None
    entries = []
    if last:
        entries.append(("Save the last paste as a source", "/import"))
    entries += [("Sources", "/sources"), ("Concept map across fields", "/map"),
                ("New hypothesis (guided)", "/hypothesis"), ("Hypotheses and outcomes", "/hypotheses"),
                ("Prompt-strategy trial: measure a hypothesis on the bench", "/trial"),
                ("Organism run: evolve a pulse sequence (local simulator)", "/evolve"),
                ("Discover cross-field links (Gemini proposes, code verifies)", "/discover"),
                ("Export as DNA::}AI{::Lang", "/lab dna")]
    _pending_suggestions.clear()
    keys = []
    for i, (label, cmd) in enumerate(entries, start=1):
        _pending_suggestions[str(i)] = cmd
        keys.append((str(i), label))
    _pending_suggestions["0"] = "/home"
    keys.append(("0", "Home menu"))
    print("\n" + ui.panel("RESEARCH LAB", lines, tone="model"))
    print(ui.actions("NEXT", keys, "Paste a paper, notes or a chat log, or /import <url>.") + "\n")


def _import(command: str = "/import"):
    """'/import <url>' fetches a page; '/import' saves the last pasted message.
    Either way the text is stored as a source with its hash and trust label."""
    arg = command.split(None, 1)[1].strip() if len(command.split(None, 1)) > 1 else ""
    try:
        if arg:
            text, title = research.fetch_url(arg)
            kind = "paper" if "arxiv.org" in arg else "url"
            rec = research.add_source(text, kind=kind, uri=arg, title=title)
        else:
            text = _intent_state.get("text") if _intent_state.get("pasted") else None
            if not text:
                print("\n[*] /import: nothing pasted yet. Paste the paper, notes or chat log first (then pick "
                      "'Save it to the research lab'), or give a link: /import <url>\n")
                return
            rec = research.add_source(text)
    except (ValueError, OSError) as e:
        print(f"\n[!] /import: {e}\n")
        return
    _source(f"/source {rec['id']}", note="already in the lab -- same text, same hash" if rec.get("duplicate")
            else "saved")


def _sources(command: str = "/sources"):
    ui = osiris_ui.Canvas()
    srcs = research.sources()
    if not srcs:
        print("\n[*] No sources yet. Paste a paper, notes or a chat log, or /import <url>.\n")
        return
    _pending_suggestions.clear()
    keys = []
    for i, s in enumerate(srcs[-9:], start=1):
        _pending_suggestions[str(i)] = f"/source {s['id']}"
        keys.append((str(i), f"{s['id']} [{s['kind']}] {research.title_of(s)[:50]}"))
    _pending_suggestions["0"] = "/lab"
    keys.append(("0", "Research lab"))
    print("\n" + ui.actions(f"SOURCES · {len(srcs)}", keys, "Newest last. Each is stored with its SHA-256.") + "\n")


def _source(command: str, note: str = None):
    ui = osiris_ui.Canvas()
    sid = command.split()[1] if len(command.split()) > 1 else ""
    s = next((x for x in research.sources() if x["id"] == sid), None)
    if s is None:
        print(f"\n[!] No source {sid!r}. /sources lists them.\n")
        return
    text = research.source_text(sid)
    inner = ui.cols - 4
    lines = [f"{s['kind']} · {s['trust']} · {s['chars']} chars · sha256 {s['sha256'][:16]}"]
    if s.get("uri"):
        lines.append(s["uri"])
    if note:
        lines.append(note)
    if text is None:
        lines.append("STORED TEXT MISSING OR CHANGED -- it no longer matches its hash; left off the map.")
    else:
        for field, cs in sorted(research.concepts(text).items()):
            lines.append("")
            lines.append(f"{field}: {', '.join(sorted(cs))}")
            for concept, line in list(sorted(cs.items()))[:2]:
                lines.extend(ui._wrap(f"  “{line}”", inner))
    print("\n" + ui.panel(f"SOURCE {sid} · {s['title'][:40]}", lines, tone="model"))
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": "/map", "2": "/hypothesis", "0": "/lab"})
    print(ui.actions("NEXT", [("1", "Concept map across fields"), ("2", "New hypothesis (guided)"),
                              ("0", "Research lab")]) + "\n")


def _map(command: str = "/map"):
    """'/map': the concepts shared by 2+ sources, rarest first, each with the
    sources' titles and quoted lines; concepts in most sources are only
    counted as background (on-device every "bridge" was "experiment" or
    "qubit", found in 10-11 of 12 sources). Read by code."""
    ui = osiris_ui.Canvas()
    srcs = research.sources()
    if not srcs:
        print("\n[*] /map: no sources yet. Paste a paper, notes or a chat log, or /import <url>.\n")
        return
    m = research.concept_map()
    title = {s["id"]: research.title_of(s) for s in srcs}
    inner = ui.cols - 4
    lines = [f"{len(srcs) - len(m['skipped'])} source(s) mapped" +
             (f" · {len(m['skipped'])} skipped (text no longer matches its hash)" if m["skipped"] else "")]
    bridged = {(f, c) for f, c, _s, _j in m["bridges"]}
    lines += ["", "Specific links -- a concept in only some of your sources, rarest first:"]
    if not m["shared"]:
        lines.append("  none yet: no specific concept is shared by two sources.")
    for f, c, sids in m["shared"][:6]:
        across = " · across fields" if (f, c) in bridged else ""
        lines.extend(ui._wrap(f"  {c} ({f}){across}", inner))
        for sid, line in m["concepts"][(f, c)][:3]:
            lines.extend(ui._wrap(f"    {sid} {title.get(sid, '')[:32]}: \u201c{line[:80]}\u201d", inner))
    if m["background"]:
        lines += [""] + ui._wrap("Background (in most sources, so no link): " + ", ".join(
            f"{c} {k}/{len(srcs)}" for _f, c, k in m["background"][:10]), inner)
    print("\n" + ui.panel("CONCEPT MAP · read by code from your sources", lines, tone="model"))
    _pending_suggestions.clear()
    keys = []
    if m["shared"]:
        _pending_suggestions["1"] = "/hypotheses draft"
        keys.append(("1", "Draft 3 hypotheses from these links (model draft, checked by code)"))
    _pending_suggestions[str(len(keys) + 1)] = "/hypothesis"
    keys.append((str(len(keys) + 1), "New hypothesis (guided)"))
    _pending_suggestions["0"] = "/lab"
    keys.append(("0", "Research lab"))
    print(ui.actions("NEXT", keys) + "\n")


_hyp_drafts = []  # the last drafted hypotheses (research.parse_drafts), for /hypothesis adopt N


def _draft_hypotheses():
    """'/hypotheses draft': asks the knowledge model for 3 hypotheses built on
    the map's 3 most specific links, giving it the quoted lines (not bare
    words) and a strict format; research.parse_drafts checks every field and
    flags overclaims. Nothing is saved: a draft becomes a hypothesis only
    through /hypothesis adopt N, which walks the guided form."""
    ui = osiris_ui.Canvas()
    srcs = {s["id"]: s for s in research.sources()}
    m = research.concept_map()
    if not m["shared"]:
        print("\n[*] No specific link to draft from yet -- /map shows why.\n")
        return
    evidence = []
    for f, c, sids in m["shared"][:3]:
        evidence.append(f"LINK: {c} ({f})")
        for sid, line in m["concepts"][(f, c)][:3]:
            evidence.append(f'  {sid} "{srcs[sid]["title"][:60]}": "{line[:160]}"')
    ok, _base = _check_ollama_reachable(timeout=1.0)
    if not ok:
        print("\n" + osiris_ui.notice(ui, "review", "DRAFT", "Ollama is not reachable -- start 'ollama serve'.") + "\n")
        return
    model = _knowledge_model()
    prompt = ("You design falsifiable experiments. From the quoted source lines below, write exactly 3 "
              "hypotheses that a local simulator or a local benchmark could test. Use ONLY what the quotes say.\n\n"
              + "\n".join(evidence) + "\n\n"
              "Answer in exactly this format, nothing else:\n"
              "HYPOTHESIS 1\nQuestion: <one sentence>\nPrediction: <the expected outcome, specific enough to be "
              "wrong>\nVaried: <what changes between conditions>\nMetric: <how it is measured>\n"
              "Controls: <held fixed>; <held fixed>\nRefuted if: <the result that would show it is wrong>\n"
              "Sources: <src ids from the quotes>\n\nHYPOTHESIS 2 ... HYPOTHESIS 3 ...\n\n"
              "Do not claim quantum advantage, new physics, consciousness, or that a language model has "
              "qubits or quantum abilities.")
    print(f"\n{ui.marker('model')} {ui.style(model, '1')} {ui.dim('· drafting from quoted lines · nothing is saved')}")
    reply = query_model(prompt, model, stream=False, timeout=300) or ""
    _hyp_drafts[:] = research.parse_drafts(reply, list(srcs))
    if not _hyp_drafts:
        print(ui.dim("No hypothesis came back in the required format. The model's text, unchecked:"))
        print(reply.strip()[:1500] or "(empty)")
        print()
        return
    _pending_suggestions.clear()
    keys = []
    for i, d in enumerate(_hyp_drafts, start=1):
        h = d["hypothesis"]
        inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
        rows = [("research", research.FIELD_LABELS[f], h[f] if f != "controls" else "; ".join(h[f]) or "")
                for f in research.FIELD_LABELS]
        rows.append(("research", "Sources", ", ".join(h["sources"]) or "(none)"))
        rows += [("review", "Problem", p) for p in d["problems"]] or [("verified", "Checks", "every field passes")]
        print(ui.panel(f"DRAFT {i} · model text, checked by code", inner.facts(rows).split("\n"), tone="model"))
        _pending_suggestions[str(i)] = f"/hypothesis adopt {i}"
        keys.append((str(i), f"Adopt draft {i} (guided form, pre-filled)" +
                     ("" if not d["problems"] else f" -- {len(d['problems'])} to fix")))
    _pending_suggestions["0"] = "/lab"
    keys.append(("0", "Research lab"))
    print(ui.actions("NEXT", keys, "A draft is model text: adopting walks each field so you keep or fix it.") + "\n")


def _hypothesis(command: str = "/hypothesis", question: str = None):
    """'/hypothesis' drafts one (guided, each answer checked); '/hypothesis hyp-N' shows one;
    '/hypothesis adopt N' walks the form pre-filled from /hypotheses draft's draft N."""
    parts = command.split()
    prefill = {}
    if parts[1:2] == ["adopt"]:
        n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        if not 1 <= n <= len(_hyp_drafts):
            print("\n[!] No such draft -- /hypotheses draft makes them.\n")
            return
        prefill = _hyp_drafts[n - 1]["hypothesis"]
    elif len(parts) == 4 and parts[2] == "tests":
        try:
            h = research.set_evidence_kind(parts[1], parts[3])
        except ValueError as e:
            print(f"\n[!] {e}\n")
            return
        print(f"\n[*] {h['id']} is decided only by {research._with_article(research.EVIDENCE_KINDS[h['evidence_kind']])}.\n")
        return
    elif len(parts) > 1:
        return _hypothesis_card(parts[1])
    ui = osiris_ui.Canvas()
    print("\n" + ui.panel("HYPOTHESIS · DRAFT", [
        "Seven short answers; 0 cancels. A hypothesis is decided only by verified evidence."], tone="model"))
    srcs = research.sources()[-9:]

    def field(name, prompt, is_list=False):
        """A pre-filled (adopted) field is shown to keep with Enter or replace;
        otherwise asked. Either way checked by research.RULES."""
        if prefill.get(name):
            print(f" {prompt.strip()} {'; '.join(prefill[name]) if is_list else prefill[name]}")

            def keep_or_replace():
                a = _ask("   [Enter] keep it, or type a better one: ")
                return "0" if a == "0" else (prefill[name] if not a else ([a] if is_list else a))
            return _ask_brief_field(name, keep_or_replace, research)
        if is_list:
            return _ask_brief_field(name, lambda: _ask_list(f" {prompt.strip()} One per line, empty line when "
                                                            f"done."), research)
        return _ask_brief_field(name, lambda: _ask(f" {prompt.strip()} ") or ("0" if name == "question" else ""),
                                research)
    try:
        if question and not research.field_problem("question", question):
            q = question
            print(f" 1/7 Question: {q}")
        else:
            q = field("question", "1/7 What question does it test?")
        pred = field("prediction", "2/7 Prediction -- what do you expect?")
        var = field("variable", "3/7 What is varied?")
        metric = field("metric", "4/7 Metric -- how is it measured?")
        controls = field("controls", "5/7 Held fixed.", is_list=True)
        refuted = field("refuted_if", "6/7 Refuted if -- which result proves it wrong?")
        chosen = []
        if prefill.get("sources"):
            print(f" 7/7 Sources it rests on: {', '.join(prefill['sources'])}")
            a = _ask("   [Enter] keep them, or type numbers/ids: ")
            if a == "0":
                raise KeyboardInterrupt
            chosen = list(prefill["sources"]) if not a else []
            if a:
                for tok in re.split(r"[\s,]+", a.strip()):
                    if tok.isdigit() and 1 <= int(tok) <= len(srcs):
                        chosen.append(srcs[int(tok) - 1]["id"])
                    elif tok in {s["id"] for s in research.sources()}:
                        chosen.append(tok)
        elif srcs:
            print(" 7/7 Sources it rests on:")
            for i, s in enumerate(srcs, start=1):
                print(f"   [{i}] {s['id']} {s['title'][:50]}")
            a = _ask("   numbers (e.g. 1,3), or Enter for none: ")
            if a == "0":
                raise KeyboardInterrupt
            for tok in re.split(r"[\s,]+", a.strip()):
                if tok.isdigit() and 1 <= int(tok) <= len(srcs):
                    chosen.append(srcs[int(tok) - 1]["id"])
                elif tok in {s["id"] for s in research.sources()}:
                    chosen.append(tok)
    except KeyboardInterrupt:
        print("[*] Hypothesis cancelled -- nothing saved.\n")
        return
    h = research.new_hypothesis(q, pred, var, metric, controls, refuted, list(dict.fromkeys(chosen)))
    probs = research.problems(h)
    if _ask(f" [1] Save hypothesis{' (incomplete: ' + str(len(probs)) + ' missing)' if probs else ''}"
            f"  [0] Discard: ") != "1":
        print("[*] Discarded -- nothing saved.\n")
        return
    h = research.save_hypothesis(h)
    session_state.set_focus(h["question"], "research", f"hypothesis {h['id']}")
    _hypothesis_card(h["id"])


def _hypothesis_card(hid: str):
    ui = osiris_ui.Canvas()
    h = next((x for x in research.hypotheses() if x["id"] == hid), None)
    if h is None:
        print(f"\n[!] No hypothesis {hid!r}. /hypotheses lists them.\n")
        return
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    rows = [("research", "Question", h["question"]), ("research", "Predicts", h["prediction"]),
            ("research", "Varies", h["variable"]), ("research", "Metric", h["metric"])]
    rows += [("research", "Fixed", c) for c in h["controls"]]
    rows += [("research", "Refuted if", h["refuted_if"]),
             ("research", "Rests on", ", ".join(h["sources"]) or "no source (ungrounded)")]
    rows += [("review", "Missing", p) for p in research.problems(h)]
    o = h.get("outcome")
    rows.append(("verified", "Outcome", f"{o['result'].upper()} -- {o['evidence_description']}") if o else
                ("review", "Outcome", "undecided -- needs verified evidence"))
    print("\n" + ui.panel(f"HYPOTHESIS {h['id']}", inner.facts(rows).split("\n"), tone="model"))
    _pending_suggestions.clear()
    entries = [("1", "Draft an experiment brief from it", f"/experiment {h['question']}"),
               ("2", "Grow OSIRIS: capture it as a capability gap (sprint path)", f"/gap {h['prediction']}"),
               ("3", "Ask the Architect to challenge it (text only)",
                f"/plan Challenge this hypothesis -- confounds, a missing control, the result that would refute "
                f"it: {h['prediction']} Refuted if: {h['refuted_if']}"),
               ("4", "Measure it: prompt-strategy trial against a baseline round", "/trial")]
    for key, _label, cmd in entries:
        _pending_suggestions[key] = cmd
    _pending_suggestions["0"] = "/lab"
    hint = "" if o else (f"Decide it with evidence: /outcome {h['id']} supported|refuted|inconclusive "
                         f"<run-... | bench-... | trial-bench-... | evo-...>")
    print(ui.actions("NEXT", [(k, l) for k, l, _c in entries] + [("0", "Research lab")], hint) + "\n")


def _hypotheses(command: str = "/hypotheses"):
    if command.split()[1:2] == ["draft"]:
        return _draft_hypotheses()
    ui = osiris_ui.Canvas()
    hs = research.hypotheses()
    if not hs:
        print("\n[*] No hypotheses yet. /hypothesis drafts one (or L, then 'New hypothesis').\n")
        return
    _pending_suggestions.clear()
    keys = []
    for i, h in enumerate(hs[-9:], start=1):
        _pending_suggestions[str(i)] = f"/hypothesis {h['id']}"
        keys.append((str(i), f"{h['id']} [{h['status']}] {h['question'][:50]}"))
    _pending_suggestions["0"] = "/lab"
    keys.append(("0", "Research lab"))
    print("\n" + ui.actions(f"HYPOTHESES · {len(hs)}", keys, "Status changes only with verified evidence.") + "\n")


def _verify_evidence(ref: str):
    """(ok, description, sha256) for an evidence id: a sprint run the genome
    ledger vouches for and whose files verify, or a bench round that
    finished in an intact bench ledger."""
    if ref.startswith("run-"):
        try:
            led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        except Exception as e:
            return False, f"genome ledger unreadable ({type(e).__name__})", None
        if led is None or led.problem():
            return False, "the genome ledger is missing or broken", None
        vouch = next((e["payload"] for e in led.chain
                      if e.get("kind") == "sprint_run" and (e.get("payload") or {}).get("run_id") == ref), None)
        if vouch is None:
            return False, "no sprint_run entry in the genome ledger names it", None
        problem = run_record.verify(ref, vouch.get("record_sha256"))
        if problem:
            return False, problem, None
        rec = run_record.load(ref)
        story = (rec.get("story") or {}).get("id")
        return True, f"sprint run {ref} (story #{story}, {rec.get('outcome')}), verified in the ledger", \
            vouch["record_sha256"]
    if ref.startswith("evo-"):
        import evolve
        try:
            end = next((e for s, e in evolve.runs() if s["run_id"] == ref), None)
        except ValueError as e:
            return False, str(e), None
        if end is None:
            return False, "no finished organism run with that id", None
        return True, evolve.describe(end), end["hash"]
    if ref.startswith("trial-bench-"):
        import protege
        import trials
        entries, problem = protege.load_ledger()
        if problem:
            return False, f"bench ledger: {problem}", None
        try:
            c = trials.compare(entries, ref[len("trial-"):])
        except ValueError as e:
            return False, str(e), None
        return True, trials.describe(c), c["treatment_hash"]
    if ref.startswith("bench-"):
        import protege
        entries, problem = protege.load_ledger()
        if problem:
            return False, f"bench ledger: {problem}", None
        end = next((e for e in entries if e.get("kind") == "bench_run_end" and e.get("run_id") == ref), None)
        if end is None:
            return False, "no finished bench round with that id", None
        if end.get("status") != "complete":
            return False, f"that bench round is {end.get('status')}, not complete", None
        start = next((e for e in entries if e.get("kind") == "bench_run_start" and e.get("run_id") == ref), {})
        if start.get("strategy"):
            return False, (f"that round is a {start['strategy']} trial: cite it as trial-{ref} so it is judged "
                           f"against its control round"), None
        s_ = end.get("summary") or {}
        return True, (f"bench round {ref} ({start.get('model', '?')}: delivered {s_.get('delivered')}/"
                      f"{s_.get('tasks')}, false confidence {s_.get('false_confidence')})"), end["hash"]
    return False, ("evidence must be a sprint run id (run-...), a bench round id (bench-...), a trial "
                   "(trial-bench-...) or an organism run (evo-...)"), None


def _outcome(command: str):
    """'/outcome hyp-N supported|refuted|inconclusive <run-... | bench-...>'."""
    parts = command.split()
    if len(parts) != 4:
        print("\n[!] Usage: /outcome hyp-N supported|refuted|inconclusive <run-... or bench-...>\n"
              "    The evidence must verify: a sprint run in the ledger, or a finished bench round.\n")
        return
    if parts[3].startswith("evo-"):
        import evolve
        import trials
        try:
            end = next((e for s, e in evolve.runs() if s["run_id"] == parts[3]), None)
        except ValueError:
            end = None
        allowed = trials.allowed_outcomes(end["verdict"]) if end else None
        if allowed and parts[2].lower() not in allowed:
            print(f"\n[!] Outcome NOT recorded: that organism run measured a result that allows only "
                  f"{' or '.join(allowed)} -- not {parts[2].lower()}.\n")
            return
    if parts[3].startswith("trial-bench-"):
        import protege
        import trials
        entries, _problem = protege.load_ledger()
        try:
            allowed = trials.allowed_outcomes(trials.compare(entries, parts[3][len("trial-"):])["verdict"])
        except ValueError:
            allowed = None  # the verifier below says why
        if allowed and parts[2].lower() not in allowed:
            print(f"\n[!] Outcome NOT recorded: that trial measured a result that allows only "
                  f"{' or '.join(allowed)} -- not {parts[2].lower()}.\n")
            return
    try:
        h = research.record_outcome(parts[1], parts[2].lower(), parts[3], _verify_evidence)
    except ValueError as e:
        print(f"\n[!] Outcome NOT recorded: {e}\n")
        return
    print(f"\n[*] {h['id']} recorded as {h['outcome']['result']}, on {h['outcome']['evidence_description']}.")
    _hypothesis_card(h["id"])


def _lab_dna():
    import dna_lang
    try:
        g = genome.get()
    except Exception:
        g = {}
    try:
        ir = dna_lang.validate_ir(research.to_dna(g))
    except dna_lang.Invalid as e:
        print(f"\n[!] The research lab does not form a valid DNA::}}AI{{::Lang document: {e}\n")
        return
    data = dna_lang.canonical_bytes(ir)
    path = os.path.join(research.ROOT, "research.dna.json")
    os.makedirs(research.ROOT, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    kinds = {}
    for ev in ir["evidence"].values():
        kinds[ev["kind"]] = kinds.get(ev["kind"], 0) + 1
    print(f"\n[*] Exported {path}\n    content id {dna_lang.content_id(ir)}\n    "
          + " · ".join(f"{n} {k}" for k, n in sorted(kinds.items())) + " -- validated as DNA::}AI{::Lang 0.1\n")


LAB_COMMANDS = {"/lab": _lab, "/import": _import, "/sources": _sources, "/source": _source, "/map": _map,
                "/hypothesis": _hypothesis, "/hypotheses": _hypotheses, "/outcome": _outcome,
                "/trial": lambda c: _trial(c), "/evolve": lambda c: _evolve(c), "/capabilities": lambda c: _capabilities(),
                "/discover": lambda c: _discover(c)}


def _reference_card(text: str):
    """A pasted AI answer or paper is reference material, not the operator's
    request: on-device (2026-09-24) a pasted Perplexity answer became a gap
    outcome, an Architect prompt and an /engage with a 40-file scan. Here it
    is described by code and offered only as material: save it, or start a
    hypothesis or a gap in the operator's own words. W re-routes it as a
    request if that is what it was."""
    ui = osiris_ui.Canvas()
    kind = research.guess_kind(text)
    inner = ui.cols - 4
    lines = [f"{'an AI answer or review' if kind == 'chat_log' else 'a paper'} · "
             f"{len(text.splitlines())} lines · {len(text)} chars",
             f"Title: {research._title(text, kind, None)}"]
    for field, cs in sorted(research.concepts(text).items()):
        lines.extend(ui._wrap(f"{field}: {', '.join(sorted(cs)[:5])}", inner))
    lines += ["", ui.dim("Reference material: its text is not taken as your request, sent to a model, or used "
                         "to scan your files.")]
    print("\n" + ui.dim("routed: reference (a pasted " + ("AI answer" if kind == "chat_log" else "paper")
                        + ") · read by code · read-only"))
    print(ui.panel("PASTED REFERENCE · read by code, nothing in it runs", lines, tone="model"))
    _pending_suggestions.clear()
    entries = [("1", "Save it to the research lab as a source", "/import"),
               ("2", "Draft a hypothesis (guided, your words)", "/hypothesis"),
               ("3", "Capture a capability gap (guided, your words)", "/gap")]
    for k, _l, c in entries:
        _pending_suggestions[k] = c
    _pending_suggestions["0"] = "/home"
    print(ui.actions("NEXT", [(k, l) for k, l, _c in entries] + [("0", "Home menu")],
                     "Or type what you want done with it · W if it was meant as a request") + "\n")


def _capabilities(command: str = "/capabilities"):
    """'/capabilities': what an autonomous organism is allowed to call -- the
    whole list. Anything not here (shell, files, network, hardware) it cannot do."""
    import capabilities
    ui = osiris_ui.Canvas()
    lines = [f"code sha256 {capabilities.code_sha256()[:16]} ({', '.join(capabilities.AUDITED_FILES)})", ""]
    for c in capabilities.REGISTRY.values():
        lines += [f"{c.name} v{c.version} · {c.authority} · {c.max_seconds}s limit", f"  {c.about}"]
        for k, (kind, rule) in c.params.items():
            rule_s = (f"{rule['min']}-{rule['max']} of {'/'.join(rule['of'])}" if kind == "seq" else
                      "/".join(rule) if kind == "enum" else f"{rule[0]}..{rule[1]}")
            lines.append(f"    {k}: {kind} {rule_s}")
    lines += ["", ui.dim("Not callable by any organism: shell commands, file paths, network, hardware, "
                         "model-written code. A new capability is a reviewed code change.")]
    print("\n" + ui.panel("CAPABILITIES · the only things an organism can call", lines, tone="model") + "\n")


def _evolve(command: str = "/evolve"):
    """'/evolve [quasistatic|ou_slow|ou_fast]': preflight, then (with 'now') one
    bounded run of evolve.py -- an organism that may only call simulate_dd_v2,
    judged on held-out seeds against idle, CPMG, XY4 and random search.
    '/evolve last' shows the latest result. Writes only the evolve ledger."""
    import capabilities
    import dd_sim
    import evolve
    ui = osiris_ui.Canvas()
    words = command.split()[1:]
    if words[:1] == ["last"]:
        return _evolve_result(None, ui)
    noises = tuple(capabilities.REGISTRY[evolve.CAPABILITY].params["noise"][1])
    noise = next((w for w in words if w in noises), "ou_slow")
    if "now" not in words:
        rows = [("research", "Organism", f"a {evolve.LENGTH}-slot pulse sequence (I idle, X/Y pi pulses), "
                                         f"evolved by fixed code: selection, crossover, mutation"),
                ("research", "May call", f"{evolve.CAPABILITY} only -- /capabilities shows it and its limits"),
                ("research", "Noise", f"{noise} dephasing; every pi pulse over-rotates by "
                                      f"{dd_sim.FLIP_ERROR:.0%} (X and Y are different axes)"),
                ("current", "Budget", "400 evaluations or 300 s, whichever first; it cannot raise them"),
                ("current", "Judged", f"on {len(evolve.HOLDOUT_SEEDS)} held-out seeds vs idle, CPMG, XY4 and "
                                      f"random search with the same budget"),
                ("verified", "Writes", "the evolve ledger only (hash-chained)"),
                ("blocked", "Will not", "run shell commands, open files or the network, touch hardware, or "
                                        "use a model")]
        inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
        print("\n" + ui.panel("ORGANISM RUN · PREFLIGHT", inner.facts(rows).split("\n")))
        _pending_suggestions.clear()
        keys = [("1", f"Run it ({noise})")]
        _pending_suggestions["1"] = f"/evolve {noise} now"
        for n in noises:
            if n != noise:
                keys.append((str(len(keys) + 1), f"Use {n} noise instead"))
                _pending_suggestions[str(len(keys))] = f"/evolve {n}"
        _pending_suggestions["0"] = "/home"
        print(ui.actions("NEXT", keys + [("0", "Home menu")]) + "\n")
        return
    print(f"\n{ui.marker('research')} ORGANISM RUN · {noise} · each generation is recorded as it finishes")
    try:
        end = evolve.evolve(noise, on_generation=lambda g, best, f, used: print(
            f"  gen {g:>2}  best {best}  fitness {f:.3f}  evaluations {used}"))
    except (OSError, RuntimeError, ValueError) as e:
        print(f"\n[!] Organism run stopped: {e}\n")
        return
    _notify("OSIRIS organism run", f"{noise}: {end['verdict']} vs {end['best_baseline']}")
    _evolve_result(end["run_id"], ui)


_discover_pending = {}  # the one preflight an approval may run: {"sha256", "question"}


def _discover(command: str = "/discover"):
    """'/discover <question>': preflight showing exactly what leaves the device;
    '/discover approve' runs that one session (Gemini proposes, arXiv and code
    verify, fixed gates, ranked); '/discover last'; '/discover adopt <session> <n>'
    makes a passing candidate an untested hypothesis. Gemini runs nothing here."""
    import discover
    ui = osiris_ui.Canvas()
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    words = command.split()
    sub = words[1].lower() if len(words) > 1 else ""
    try:
        if sub == "last":
            return _discover_result(discover.load(), ui)
        if sub == "adopt" and len(words) == 4 and words[3].isdigit():
            h = discover.adopt(words[2], int(words[3]))
            print(f"\n[+] {h['id']} saved as an UNTESTED hypothesis with its bridge contract; its arXiv papers are "
                  f"lab sources ({', '.join(h['sources'])}).\n    Only a measured run decides it: "
                  f"{'/evolve' if h['bridge']['test_with'].startswith('simulate_dd') else '/trial'} then /outcome.\n")
            _pending_suggestions.clear()
            _pending_suggestions.update({"1": "/hypotheses", "2": "/lab dna", "0": "/lab"})
            print(ui.actions("NEXT", [("1", "Hypotheses"), ("2", "Export the lab as DNA::}AI{::Lang"),
                                      ("0", "Research lab")]) + "\n")
            return
        if sub == "approve":
            if not _discover_pending:
                print("\n[!] Nothing to approve: /discover <question> shows the preflight first.\n")
                return
            pending = dict(_discover_pending)
            _discover_pending.clear()  # one approval, one session
            print(f"\n{ui.marker('research')} DISCOVERY · asking Gemini once, then checking every source on arXiv ...")
            s = discover.run(pending["sha256"], pending["question"])
            _notify("OSIRIS discovery", f"{len(s['ranking'])} of {len(s['results'])} candidate links passed")
            return _discover_result(s, ui)
    except discover.DiscoveryError as e:
        print(f"\n[!] {e}\n")
        return
    if not gemini_bridge.is_configured():
        print("\n[!] Discovery needs GEMINI_API_KEY in ~/.env; nothing else in the lab needs it.\n")
        return
    question = " ".join(words[1:])
    if not question:
        lines = ["Ask a research question. Gemini proposes up to "
                 f"{discover.MAX_CANDIDATES} links between fields; OSIRIS checks every cited paper on arXiv "
                 "(title and quoted abstract words), applies fixed gates, and ranks what passes.",
                 "", "Example: /discover can evolutionary search find pulse sequences that tolerate "
                 "over-rotated pulses better than XY4"]
        print("\n" + ui.panel("DISCOVER · cross-field links", lines, tone="model"))
        _pending_suggestions.clear()
        _pending_suggestions.update({"1": "/discover last", "0": "/lab"})
        print(ui.actions("NEXT", [("1", "Last discovery session"), ("0", "Research lab")],
                         "Type /discover <your question>") + "\n")
        return
    try:
        ob = discover.outbound(question)
        used = discover.sessions_today()
    except discover.DiscoveryError as e:
        print(f"\n[!] {e}\n")
        return
    rows = [("review", "Sends to", f"Gemini ({gemini_bridge.model_name()}), one request, with Google Search"),
            ("review", "Question", ob["question"]),
            ("review", "Also sent", f"{len(ob['fields'])} field names; titles of {len(ob['titles'])} paper(s)/link(s) "
                                    f"in the lab ({len(ob['prompt'])} chars in all)"),
            ("verified", "Not sent", "notes, chat or terminal logs, files, code, keys, ledgers, run results"),
            ("current", "Then", f"one arXiv lookup (up to {discover.MAX_LOOKUPS} ids); fixed gates; ranking"),
            ("current", "Budget", f"{discover.MAX_CANDIDATES} candidates · session {used + 1} of "
                                  f"{discover.MAX_SESSIONS_PER_DAY} today · no automatic retries"),
            ("blocked", "Gemini cannot", "run anything, write files, change OSIRIS, or decide a hypothesis")]
    print("\n" + ui.panel("DISCOVERY · PREFLIGHT · what leaves the device", inner.facts(rows).split("\n")))
    _discover_pending.clear()
    _discover_pending.update(sha256=ob["sha256"], question=ob["question"])
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": "/discover approve", "0": "/lab"})
    print(ui.actions("NEXT", [("1", "Approve this one session"), ("0", "Cancel")],
                     f"prompt sha256 {ob['sha256'][:12]}") + "\n")


def _discover_result(s, ui):
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    by_n = {r["n"]: r for r in s["results"]}
    head = [f"{s['question']}", ui.dim(f"{len(s['results'])} proposed · {len(s['ranking'])} passed · "
                                       f"{s['lookups']} arXiv ids checked · {s['model']}")]
    for err in (s.get("parse_error"), s.get("lookup_error")):
        if err:
            head.append(f"[!] {err}")
    print("\n" + ui.panel(f"DISCOVERY · {s['id']}", head, tone="model"))
    keys = []
    _pending_suggestions.clear()
    for rank, n in enumerate(s["ranking"][:3], start=1):
        r = by_n[n]
        c = r["candidate"]
        rows = [("research", "Fields", " / ".join(c["fields"])), ("research", "Mechanism", c["mechanism"])]
        rows += [("verified", "Source", f"arXiv:{v['record']['id']} {v['record']['title']}") for v in r["verified"]]
        rows += [("current", "Predicts", c["prediction"]), ("current", "Refuted if", c["refuted_if"]),
                 ("current", "Test with", c["test_with"]),
                 ("blocked", "Does not show", "; ".join(c["forbidden_inferences"])),
                 ("review", "Score", f"{r['score']:.2f}  " + " ".join(f"{k} {v}" for k, v in r["parts"].items()))]
        print(ui.panel(f"#{n} · {c['title'][:60]} · untested", inner.facts(rows).split("\n")))
        keys.append((str(rank), f"Adopt #{n} as an untested hypothesis"))
        _pending_suggestions[str(rank)] = f"/discover adopt {s['id']} {n}"
    failed = [r for r in s["results"] if r["problems"]]
    if failed:
        lines = [f"#{r['n']} {str(r['candidate'].get('title', ''))[:50]}: {r['problems'][0]}"
                 + (f" (+{len(r['problems']) - 1} more)" if len(r["problems"]) > 1 else "") for r in failed]
        lines += [ui.dim("Rejected by code: a wrong source, an undefined word or a missing control keeps a link "
                         "out, however good it sounds.")]
        print(ui.panel("REJECTED", lines, tone="model"))
    k = str(len(keys) + 1)
    _pending_suggestions.update({k: "/hypotheses", "0": "/lab"})
    print(ui.actions("NEXT", keys + [(k, "Hypotheses"), ("0", "Research lab")],
                     "Adopting saves the papers as sources; nothing is decided until a run measures it") + "\n")


def _evolve_result(run_id, ui):
    import evolve
    try:
        runs = evolve.runs()
    except ValueError as e:
        print(f"\n[!] {e}\n")
        return
    done = [(s, e) for s, e in runs if e and (run_id is None or s["run_id"] == run_id)]
    if not done:
        print("\n[*] No finished organism run yet. /evolve shows the preflight.\n")
        return
    start, end = done[-1]
    t = end["holdout"]
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    rows = [("research", "Noise", f"{start['noise']} · stopped: {end['stop_reason']} · "
                                  f"{end['generations']} generations, {end['evaluations']} evaluations")]
    for name, v in sorted(t.items(), key=lambda kv: -kv[1]["fidelity"]):
        rows.append(("verified" if name == "organism" else "current", name, f"{v['genome']}  {v['fidelity']:.3f}"))
    rows.append(("verified" if end["verdict"] == "better" else "review", "Verdict",
                 f"{end['verdict']} vs {end['best_baseline']} ({end['difference']:+.3f}) -- preliminary: one "
                 f"simulator ({start.get('capability', '?')}), one noise model"))
    print("\n" + ui.panel(f"ORGANISM RUN · RESULT · {end['run_id']}", inner.facts(rows).split("\n")))
    import trials
    allowed = trials.allowed_outcomes(end["verdict"])
    open_h = research.open_hypotheses_for(end["run_id"])
    hint = (f"/outcome {open_h[-1]['id']} {allowed[0]} {end['run_id']}" if open_h else
            f"No open hypothesis is decided by an organism run: /hypothesis hyp-N tests evo, then "
            f"/outcome hyp-N {allowed[0]} {end['run_id']}")
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": f"/evolve {start['noise']}", "2": "/hypotheses", "0": "/home"})
    print(ui.actions("NEXT", [("1", "Run again (another seed of evidence)"), ("2", "Hypotheses"),
                              ("0", "Home menu")], f"Record it: {hint}") + "\n")


def _digest():
    """'/digest': what the last pasted terminal session says happened --
    commands typed, results, problems, run ids, an appended AI review --
    read by paste_digest with fixed patterns. No model; nothing in the paste
    runs or is recorded."""
    import paste_digest
    text = _intent_state.get("text")
    ui = osiris_ui.Canvas()
    if not text or not paste_digest.looks_like_session(text):
        print("\n[*] /digest: no pasted terminal session yet -- paste one first.\n")
        return
    d = paste_digest.digest(text)
    inner = ui.cols - 4
    lines = [f"{d['lines']} lines" + (f" · {d['sessions']} Termux session(s)" if d["sessions"] else "")
             + (f" · ends with an AI review ({d['review_sections']} sections) -- reference only"
                if d["review"] else "")]

    def block(title, items, more):
        if not items:
            return
        lines.append("")
        lines.append(title)
        for it in items:
            lines.extend(ui._wrap("  " + it, inner))
        if more:
            lines.append(f"  ...and {more} more")
    block("Typed at osiris>:", d["osiris_commands"], d["osiris_more"])
    block("Typed at the shell:", d["shell_commands"], d["shell_more"])
    block("Results:", d["results"], d["results_more"])
    block("Problems:", d["problems"], d["problems_more"])
    if d["run_ids"] or d["bench_ids"]:
        lines += ["", "Mentioned: " + ", ".join(d["run_ids"] + d["bench_ids"])]
    print("\n" + ui.panel("PASTED SESSION · read by code, nothing in it runs", lines))


def _route(text: str, forced: str = None):
    """Free-form text -> intent_router class -> read-only answer (conversation,
    question, status) or an intent card with that class's fixed actions.
    Code decides the class and the actions; no model output becomes a command."""
    cls, cues = intent_router.classify(text)
    if forced:
        cls, cues = forced, dict(cues, **{forced: ["your correction"]})
    if cls == intent_router.UNCLEAR:
        token = " ".join(text.split())
        keys = [c for c in token.upper() if c in _pending_suggestions or c.lower() in _pending_suggestions]
        hint = f" Did you mean {keys[0]}?" if keys else ""
        print(f"\n[?] '{token}' is not a command, a menu key or a sentence OSIRIS can use -- nothing was run.{hint}\n"
              f"    Type a menu number or letter, a /command (E lists them), or say what you want in words.\n")
        return
    pasted = _last_input["pasted"] or "\n" in text.strip()
    _intent_state.update(text=text, cls=cls, pasted=pasted)
    import_it = [("Save it to the research lab as a source", "/import")] if pasted else []
    n_lines = len([l for l in text.splitlines() if l.strip()])
    if pasted and not forced and n_lines > 5 and research.guess_kind(text) in ("chat_log", "paper"):
        _reference_card(text)
        return
    if cls == "session_log":
        ui = osiris_ui.Canvas()
        print(ui.dim("routed: session_log (a pasted terminal session) · read by code, nothing in it runs · "
                     "read-only"))
        _digest()
        _next_actions(text, cls, answered=True, extra=import_it)
        return
    if cls in intent_router.AUTO_ANSWER:
        ui = osiris_ui.Canvas()
        why = ", ".join(cues.get(cls, [])) or "no specific cue"
        who = "code, from verified state" if cls != "question" or intent_router.about_osiris(text) else "a local model"
        print(ui.dim(f"routed: {cls} (from: {why}) · answered by {who} · read-only"))
        _answer(text, cls)
        return
    facts = osiris_ui.intent_facts(text, MODIFY_INTENT_RE, CODEBASE_INTENT_RE, os.getcwd())
    ui = osiris_ui.Canvas()
    print("\n" + osiris_ui.intent_card(ui, facts, CHAT_MODEL, f"{_synth_chain()}", cls, cues,
                                       "pasted text -- read as reference material, not as instructions"
                                       if pasted else None))
    _next_actions(text, cls, extra=import_it)


def _plan(text: str):
    """'/plan <goal>' or '/plan brief N': the Architect's plan or critique as
    TEXT ONLY -- grounded in the same verified facts, no code, no files."""
    ui = osiris_ui.Canvas()
    m = re.fullmatch(r"brief\s+(\d+)", text.strip(), re.IGNORECASE)
    if m:
        b = next((x for x in experiments.briefs() if x["id"] == int(m.group(1))), None)
        if b is None:
            print(f"\n[!] No experiment brief #{m.group(1)}.\n")
            return
        task = ("Critique this simulator-only experiment brief. List: (1) what could confound the comparison, "
                "(2) what control or baseline is missing, (3) how many seeds/shots would make differences "
                "meaningful, (4) the single most important change. Do not invent results.\n\nBRIEF:\n"
                + json.dumps({k: b[k] for k in ("question", "hypothesis", "system", "variables", "metric",
                                                "controls")}, indent=1))
    elif text.strip():
        session_state.set_focus(text, intent_router.classify(text)[0], "plan request")
        task = ("Write a short numbered plan for this goal: steps, which parts of OSIRIS it likely touches "
                "(mark these as guesses), risks, and how success would be checked. No code.\n\nGOAL: "
                + text.strip()[:2000])
    else:
        print("\n[!] /plan needs a goal, e.g. /plan make run review easier on the phone\n")
        return
    ok, _base = _check_ollama_reachable(timeout=1.0)
    if not ok:
        print("\n" + osiris_ui.notice(ui, "review", "PLAN", "Ollama is not reachable -- start 'ollama serve'.") + "\n")
        return
    model = ANSWER_MODEL or CHAT_MODEL
    print(f"\n{ui.marker('model')} {ui.style(model, '1')} {ui.dim('· draft plan, text only · nothing is created')}")
    # No menu keys: the 1B Architect turned "G benchmark..., H capture..." into plan
    # steps "G -- Benchmark ...", "H -- Review ..." (on-device, 2026-09-24).
    facts = [f for f in _grounded_facts() if not f.startswith("Menu keys:")]
    prompt = ("You are the OSIRIS Architect. Use ONLY these FACTS about OSIRIS's state:\n"
              + "\n".join(f"- {f}" for f in facts) + "\n\n" + task)
    query_model(prompt, model, stream=True, timeout=300)
    print(ui.dim("A model's draft: nothing was run, created or changed."))
    cls = "research" if m else intent_router.classify(text)[0]
    _next_actions(text if not m else b["question"], cls if cls in ("research", "engineering") else "engineering")


def _ask_brief_field(field, ask, rules=None):
    """One brief answer, checked at once: on a problem, say it with an
    example and ask once more; the second answer is kept either way (the
    review still lists what is missing). '0' / None cancels the brief."""
    for attempt in (1, 2):
        value = ask()
        if value is None or value == "0":
            raise KeyboardInterrupt
        rules = rules or experiments
        problem = rules.field_problem(field, value)
        if not problem or attempt == 2:
            return value
        print(f"   ▲ {problem}\n     e.g. {rules.EXAMPLES[field]}  (0 cancels)")


def _experiment(text: str = ""):
    """'/experiment [question]': a guided, simulator-first experiment brief
    (experiments.py). Six short answers; 0 cancels. Saved as a draft plan --
    nothing runs, submits or spends anything; hardware stays disabled."""
    ui = osiris_ui.Canvas()
    print("\n" + ui.panel("EXPERIMENT BRIEF · DRAFT", [
        f"{ui.marker('research')} Simulator first. Six short answers; 0 cancels.",
        ui.dim("Nothing runs from a brief: it is the plan a later, reviewed run must follow.")], tone="model"))
    try:
        question = text.strip()
        if question:
            print(f" Question so far: {question}")
            a = _ask(" 1/6 [Enter] keep it, or type a sharper one: ")
            if a == "0":
                raise KeyboardInterrupt
            question = a or question
            if experiments.field_problem("question", question):
                question = _ask_brief_field("question", lambda: _ask(" 1/6 What are you testing? "))
        else:
            question = _ask_brief_field("question", lambda: _ask(" 1/6 What are you testing? ") or "0")
        if not research.concepts(question).get("quantum"):
            # This form is for simulator-first quantum experiments; a question about
            # OSIRIS, a UI or a model was pushed through qubits and shots (on-device,
            # brief #2, 2026-09-24).
            print("   ▲ This form is for simulator-first quantum experiments (circuits, shots, noise), and "
                  "your question names no quantum concept.\n"
                  "     [1] Use a Research Lab hypothesis instead (what is varied, metric, controls, what would "
                  "refute it)  [2] Continue here  [0] Cancel")
            pick = _ask("   choice: ")
            if pick == "1":
                return _hypothesis("/hypothesis", question=question)
            if pick != "2":
                raise KeyboardInterrupt
        hypothesis = _ask_brief_field("hypothesis", lambda: _ask(" 2/6 What outcome would support or weaken it? "))
        system = _ask_brief_field("system", lambda: _ask(" 3/6 System under test (e.g. 3-qubit GHZ circuit, "
                                                         "depth 2-10): "))
        variables = _ask_brief_field("variables", lambda: _ask_list(" 4/6 What is varied? One per line, "
                                                                    "empty line when done."))
        print(" 5/6 Metric:")
        for i, name in enumerate(experiments.METRICS, start=1):
            print(f"   [{i}] {name}")

        def pick_metric():
            a = _ask("   number, or type your own: ")
            if a == "0":
                return "0"
            return experiments.METRICS[int(a) - 1] if a.isdigit() and 1 <= int(a) <= len(experiments.METRICS) else a
        metric = _ask_brief_field("metric", pick_metric)
        controls = _ask_brief_field("controls", lambda: _ask_list(" 6/6 Held fixed (seed, shots, noise model). "
                                                                  "One per line, empty line when done."))
    except KeyboardInterrupt:
        print("[*] Brief cancelled -- nothing saved.\n")
        return
    b = experiments.new_brief(question, hypothesis, system, variables, metric, controls)
    probs = experiments.problems(b)
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    rows = [("research", "Question", b["question"] or "(none)"), ("research", "Hypothesis", b["hypothesis"] or "(none)"),
            ("research", "System", b["system"] or "(none)")]
    rows += [("research", "Varies", v) for v in b["variables"]]
    rows += [("research", "Metric", b["metric"] or "(none)")] + [("research", "Fixed", c) for c in b["controls"]]
    rows += [("verified", "Runs on", b["execution"]), ("blocked", "Hardware", b["hardware"])]
    rows += [("review", "Missing", p) for p in probs] or [("verified", "Complete", "reproducible as written")]
    print(ui.panel("EXPERIMENT BRIEF", inner.facts(rows).split("\n"), tone="model"))
    if _ask(" [1] Save brief  [0] Discard: ") != "1":
        print("[*] Discarded -- nothing saved.\n")
        return
    b = experiments.save(b)
    session_state.set_focus(b["question"], "research", f"experiment brief #{b['id']}")
    print(f"\n[*] Saved experiment brief #{b['id']}{' (incomplete)' if probs else ''}. Nothing was run.")
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": f"/plan brief {b['id']}", "2": "/experiments", "0": "/home"})
    print(ui.actions("NEXT", [("1", "Ask the Architect to critique it (text only)"),
                              ("2", "All experiment briefs"), ("0", "Home menu")]) + "\n")


def _experiments():
    ui = osiris_ui.Canvas()
    bs = experiments.briefs()
    if not bs:
        print("\n[*] No experiment briefs yet. J on /home (or /experiment) drafts one.\n")
        return
    _pending_suggestions.clear()
    lines = []
    for i, b in enumerate(bs[-9:], start=1):
        _pending_suggestions[str(i)] = f"/plan brief {b['id']}"
        state = "complete" if not experiments.problems(b) else "incomplete"
        lines.append(f"{ui.key(str(i))} #{b['id']} [{state}] {b['question'][:60]}")
    print("\n" + ui.panel("EXPERIMENT BRIEFS", lines + ["", ui.dim("A number asks the Architect to critique that "
                                                                 "brief (text only). Nothing here has been run.")]) + "\n")


def _facts():
    ui = osiris_ui.Canvas()
    print("\n" + ui.panel("VERIFIED FACTS (what answers are grounded in)",
                          [f"{ui.marker('verified')} {f}" for f in _grounded_facts()]) + "\n")


def _engage():
    """'/engage': runs the pipeline on the text of the last intent card, once."""
    text, _intent_state["text"] = _intent_state["text"], None
    if not text:
        print("\n[!] /engage: no intent card to send -- type what you want first.\n")
        return
    run_synergy_pipeline(text)


def _ui(command: str = ""):
    """'/ui [rich|plain|access]': the appearance. Saved to ~/.osiris/ui.json;
    it changes how screens look, never what any key or command does."""
    arg = command.strip().lower().split()[1:2]
    if arg:
        if not osiris_ui.save_mode(arg[0]):
            print(f"\n[!] /ui: unknown appearance {arg[0]!r} -- rich, plain or access.\n")
            return
        effective = osiris_ui.mode()
        note = "" if effective == arg[0] else f" (showing {effective}: this output is not a color terminal)"
        print(f"\n[*] Appearance: {arg[0]}{note}.")
        _home()
        return
    ui = osiris_ui.Canvas()
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": "/ui rich", "2": "/ui plain", "3": "/ui access", "0": "/home"})
    print("\n" + ui.actions(f"APPEARANCE · now {ui.mode}", [
        ("1", "Rich: panels, color, glyph markers"),
        ("2", "Plain: ASCII only, no color"),
        ("3", "Accessible: no boxes, every marker spelled out"),
        ("0", "Back")], "OSIRIS_UI=rich|plain|access overrides this for one session.") + "\n")


HELP_SECTIONS = (
    ("Look (read-only)", ["/home  the menu", "/status  every fact on one screen", "/check  ledger, runs, bench",
                          "/run show [id] [n]  a run's candidates", "/runs stats  verified run history",
                          "/why  last sandbox log", "/intent status  Engine 1", "/organism status  Engine 3",
                          "/mentors  which model the hidden tests favor (protege.py)",
                          "/bench [model|gemini] [all|task,task] [k=N]  score a mentor (G) · /bench log",
                          "/ledger verify [path]"]),
    ("Talk", ["<plain words>  questions answered at once; requests get fixed next steps",
              "/ask <question>  grounded answer (read-only)", "/facts  what answers are grounded in",
              "/plan <goal>  the Architect's plan, text only",
              "N  the next best action (its card is on /home)", "W  re-route the last message (saved as feedback)",
              "/focus [text|clear]  what you are working on"]),
    ("Research", ["/experiment [question]  simulator-first brief (J)", "/experiments  briefs; critique one",
                  "/research <topic>  recent arXiv abstracts",
                  "/lab  research lab (L): sources, concept map, hypotheses",
                  "/import [url]  save the last paste, or a link, as a source",
                  "/sources · /source <id> · /map  sources and the cross-field concept map",
                  "/hypothesis [hyp-N] · /hypotheses  draft or show hypotheses",
                  "/outcome hyp-N supported|refuted|inconclusive <run-...|bench-...>  verified evidence only",
                  "/lab dna  export the lab as DNA::}AI{::Lang",
                  "/trial [strategy] [model] · /trial last · /trial text  prompt-strategy trial vs. its control",
                  "/evolve [noise] · /evolve last  a bounded organism run on the local simulator",
                  "/discover <question> · /discover last  Gemini proposes cross-field links; arXiv and code verify",
                  "/capabilities  the only functions an organism may call"]),
    ("Plan and build", [
                        "/gap [outcome]  guided capability-gap draft (H)",
                        "/gaps  review and activate drafts (I)", "/ignite  active gaps -> backlog stories",
                        "/sprint plan · /sprint execute [#id] · /sprint review",
                        "/auto-enhance · /research · /consensus · /dd ..."]),
    ("Decide", ["/apply  write the pending proposal (typed, never a menu key)"]),
    ("Interface", ["/tap  menu as Android buttons", "/ui  appearance", "exit  quit"]),
)


def _mentors():
    """'/mentors': protege.py's scorecard and routing, from the verified bench
    ledger only. Read-only; changes no backend order."""
    import protege
    entries, problem = protege.load_ledger()
    ui = osiris_ui.Canvas()
    if problem:
        print("\n" + osiris_ui.notice(ui, "review", "MENTORS", problem + " -- press G (/bench) to score "
                                     "a mentor.") + "\n")
        return
    suite = protege.current_suite()
    cands, skipped = protege.candidates(entries, suite, protege.current_runner())
    card = protege.scorecard(cands)
    st = protege.run_status(entries)
    runs = (f"\nRuns: {st['complete']} complete, {st['partial']} partial, {st['unterminated']} unterminated"
            if any(st.values()) else "")
    print("\n" + protege.format_scorecard(card, skipped, suite) + runs + "\n\n" + protege.format_route(card) + "\n")


BENCH_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osiris_bench.py")
BENCH_DEFAULT_MODEL = "qwen2.5-coder:7b"
BENCH_QUICK_TASKS = ("gaps", "claims", "backlog")
BENCH_EXIT = {0: ("passed", "round complete"), 130: ("review", "stopped early -- finished tasks were saved"),
              3: ("blocked", "the sandbox cannot run here (proot-distro) -- run osiris from native Termux"),
              1: ("blocked", "recording or suite problem -- see the output above"),
              2: ("blocked", "bad benchmark arguments")}


def _bench_argv(command: str):
    """'/bench [MODEL|gemini] [all|TASK,TASK] [k=N]' -> (argv, label) or (None, error).
    Defaults: the local qwen2.5-coder:7b mentor, 3 quick tasks, one attempt each."""
    backend, model, tasks, k = "ollama", BENCH_DEFAULT_MODEL, list(BENCH_QUICK_TASKS), 1
    tasks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench_tasks")
    known = sorted(d for d in os.listdir(tasks_dir) if not d.startswith((".", "_"))
                   and os.path.isdir(os.path.join(tasks_dir, d))) if os.path.isdir(tasks_dir) else []
    for w in command.split()[1:]:
        lw = w.lower()
        if lw == "gateway":
            return None, "the AI Gateway is removed from OSIRIS -- use gemini or a local model"
        if lw == "gemini":
            backend, model = lw, None
        elif lw == "all":
            tasks = None
        elif lw == "now":
            continue  # skip the preflight card (the card's [1] adds it)
        elif re.fullmatch(r"k=[1-5]", lw):
            k = int(lw[2:])
        elif "," in lw or lw in known:
            names = [t for t in lw.split(",") if t]
            bad = [t for t in names if t not in known]
            if bad:
                return None, f"unknown task(s) {bad}; known: {', '.join(known)}"
            tasks = names
        elif re.fullmatch(r"[a-z0-9][a-z0-9._/-]*(:[a-z0-9._-]+)?", lw) and len(lw) <= 64:
            backend, model = "ollama", w
        else:
            return None, f"not understood: {w!r} -- try /bench, /bench all, /bench deepseek-coder, k=3"
    argv = [sys.executable, BENCH_SCRIPT, "--backend", backend, "--k", str(k)]
    argv += ["--model", model] if model else []
    argv += ["--tasks", ",".join(tasks)] if tasks else []
    label = f"{backend}{'/' + model if model else ''} · {len(tasks) if tasks else len(known)} task(s) · k={k}"
    return argv, label


BENCH_EVENT_PREFIX = "@@OSIRIS_EVENT "  # osiris_bench.EVENT_PREFIX
BENCH_LOG = os.path.join(os.path.expanduser("~"), ".osiris", "bench", "last_round.log")


class _RoundView:
    """The live MENTOR ROUND card, drawn from osiris_bench --events. On a
    terminal it is redrawn in place; otherwise one line per finished task
    and the final card. Every "saved" shown is an event the benchmark sent
    only after that task's ledger entry was written."""

    def __init__(self, ui, label, live):
        self.ui, self.label, self.live = ui, label, live
        self.tasks, self.status, self.attempt = [], {}, None
        self.started, self.drawn, self.note, self.end = time.monotonic(), 0, None, None
        self.note_final = False

    def event(self, e):
        kind = e.get("kind")
        if kind == "run_start":
            self.tasks = list(e.get("tasks") or [])
        elif kind == "task_start":
            self.status[e["task"]] = {"state": "running"}
            self.attempt = None
            if e["task"] not in self.tasks:
                self.tasks.append(e["task"])
        elif kind == "attempt":
            self.attempt = f"attempt {e['n']}/{e['k']}: own test {'passed' if e['own_ok'] else 'failed'}"
        elif kind == "task_done":
            self.status[e["task"]] = dict(e, state="done")
            if not self.live:
                print(self._task_line(e["task"]))
        elif kind == "run_end":
            self.end = e
        if self.live:
            self.draw()

    def _task_line(self, t):
        ui, st = self.ui, self.status.get(t)
        if not st:
            return f"{ui.marker('idle')} {t:<15} {'not run' if self.end or self.note_final else 'waiting'}"
        if st["state"] == "running":
            if self.end or self.note_final:  # the round ended with this task unfinished
                return f"{ui.marker('idle')} {t:<15} stopped -- not scored, not saved"
            return f"{ui.marker('iterate')} {t:<15} running · {self.attempt or 'model writing a candidate'}"
        secs = f"{st.get('seconds', 0):.0f}s"
        if st.get("delivered"):
            return f"{ui.marker('passed')} {t:<15} hidden test PASS · {secs} · saved"
        if st.get("false_confidence"):
            what = "FALSE CONFIDENCE (own test passed)"
        elif not st.get("proposed"):
            what = "no candidate passed its own test"
        else:
            what = "hidden test FAIL"
        return f"{ui.marker('review' if st.get('false_confidence') else 'blocked')} {t:<15} {what} · {secs} · saved"

    def lines(self):
        ui = self.ui
        done = [v for v in self.status.values() if v.get("state") == "done"]
        el = int(time.monotonic() - self.started)
        out = [f"{ui.marker('research')} {self.label} · advisory evidence",
               f"{ui.marker('current')} {len(done)} of {len(self.tasks) or '?'} tasks done · "
               f"{sum(bool(v.get('delivered')) for v in done)} hidden-test pass · "
               f"{sum(v.get('false_confidence', 0) for v in done)} false confidence · {el // 60}:{el % 60:02d}"]
        for t in self.tasks:
            out.append(self._task_line(t))
            st = self.status.get(t) or {}
            if st.get("state") == "done" and st.get("hidden_reason"):
                out.append("   " + ui.dim("hidden test: " + st["hidden_reason"][:110]))
        out.append(ui.dim(self.note or "Ctrl-C stops safely: finished tasks are already saved."))
        return out

    def render(self):
        return self.ui.panel("MENTOR ROUND", self.lines(), tone="rich")

    def draw(self):
        card = self.render()
        if self.drawn:
            sys.stdout.write(f"\x1b[{self.drawn}F\x1b[J")  # back to the card's first line, clear below
        sys.stdout.write(card + "\n")
        sys.stdout.flush()
        self.drawn = card.count("\n") + 1


def _bench_preflight(command, argv, label, ui):
    """One card before a round: what runs, for how long (from the last round's
    real task times), what it is compared with, and what it will not do.
    [1] starts it; nothing has run yet."""
    import protege
    tasks = argv[argv.index("--tasks") + 1].split(",") if "--tasks" in argv else ["all 9 tasks"]
    k = int(argv[argv.index("--k") + 1])
    mentor = f"{argv[3]}/{argv[argv.index('--model') + 1]}" if "--model" in argv else argv[3]
    est, base = "a few minutes per task on a phone", "no earlier round to compare with"
    entries, problem = protege.load_ledger()
    if not problem:
        rnd = protege.latest_round(entries)
        secs = [t["seconds"] for t in (rnd or {}).get("tasks", []) if t.get("seconds")]
        if secs:
            n = len(tasks) if tasks != ["all 9 tasks"] else 9
            total = sum(secs) / len(secs) * n * k
            est = f"about {max(1, round(total / 60))} min (last round averaged {sum(secs) / len(secs):.0f}s per task)"
        card = protege.scorecard(protege.candidates(entries, protege.current_suite(), protege.current_runner())[0])
        others = [f"{_short(m)} {v['verified']}/{v['candidates']}" for m, v in card.items() if m != mentor]
        mine = card.get(mentor)
        base = ("compared with " + ", ".join(others) + " -- same suite and runner") if others else base
        if mine:
            base += f"; {_short(mentor)} already has {mine['verified']}/{mine['candidates']}"
    rows = [("research", "Runs", f"{_short(mentor)} · {', '.join(tasks)} · {k} attempt(s) each"),
            ("current", "Takes", est), ("current", "Baseline", base),
            ("verified", "Writes", "benchmark evidence only (ledger + hashed files)"),
            ("blocked", "Will not", "change code, apply anything, or change which model OSIRIS calls"
                                    + ("" if argv[3] in ("gemini", "gateway") else ", or use cloud quota"))]
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    print("\n" + ui.panel("MENTOR ROUND · PREFLIGHT", inner.facts(rows).split("\n") + [
        "", ui.dim("Plug in the charger: the phone works hard for the whole round.")]))
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": command.strip() + " now", "0": "/home"})
    print(ui.actions("START?", [("1", "Start the round"), ("0", "Not now")]) + "\n")


TRIAL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench_trial.py")


def _trial(command: str = "/trial"):
    """'/trial [STRATEGY] [MODEL]': a prompt-strategy trial -- the same mentor
    round with one declared change to how tasks are asked, judged against the
    latest matching baseline round by trials.py. Preflight first ([1] runs it);
    '/trial last' shows the latest result; '/trial text [STRATEGY]' the exact
    strategy text. Writes only bench evidence."""
    import prompt_strategies
    import protege
    import trials
    ui = osiris_ui.Canvas()
    words = command.split()[1:]
    if words[:1] == ["last"]:
        return _trial_result(None, ui)
    if words[:1] == ["text"]:
        sid = words[1] if len(words) > 1 else "invariant-first-v1"
        try:
            st = prompt_strategies.get(sid)
        except KeyError as e:
            print(f"\n[!] {e.args[0]}\n")
            return
        print(f"\n{sid} (sha256 {prompt_strategies.sha256(sid)[:16]}) -- {st['about']}\n\n{st['text']}")
        return
    now = "now" in words
    words = [w for w in words if w != "now"]
    strategy = next((w for w in words if w in prompt_strategies.STRATEGIES), "invariant-first-v1")
    model = next((w for w in words if w not in prompt_strategies.STRATEGIES), BENCH_DEFAULT_MODEL)
    tasks, k = sorted(BENCH_QUICK_TASKS), 1
    entries, problem = protege.load_ledger()
    key = ("ollama", model, k, tuple(tasks), protege.current_suite(), protege.current_runner())
    controls = [] if problem else [r for r in trials.rounds(entries).values()
                                   if not r["start"].get("strategy") and trials._complete(r)
                                   and trials._key(r["start"]) == key]
    if not now:
        st = prompt_strategies.get(strategy)
        if controls:
            c = controls[-1]
            s_ = c["end"].get("summary") or {}
            base = (f"{c['start']['run_id']} -- hidden passes {s_.get('delivered')}/{s_.get('tasks')}, "
                    f"false confidence {s_.get('false_confidence')}")
        else:
            base = "none yet -- a baseline round on the same model and tasks is needed first"
        rows = [("research", "Tests", f"{strategy}: {st['about']}"),
                ("research", "Model", f"ollama/{model} · {', '.join(tasks)} · k={k}"),
                ("current", "Control", base),
                ("current", "Judged", "hidden passes and false confidence vs. the control, by a fixed rule"),
                ("verified", "Writes", "benchmark evidence only (ledger + hashed files)"),
                ("blocked", "Will not", "change code or the default prompt, apply anything, or use cloud quota")]
        inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
        print("\n" + ui.panel("PROMPT-STRATEGY TRIAL · PREFLIGHT", inner.facts(rows).split("\n") + [
            "", ui.dim("Same tasks, hidden tests and runner as the control; only the prompt's preamble differs.")]))
        _pending_suggestions.clear()
        if controls:
            _pending_suggestions.update({"1": f"/trial {strategy} {model} now", "2": f"/trial text {strategy}",
                                         "0": "/home"})
            keys = [("1", "Run the trial round"), ("2", "Show the exact strategy text"), ("0", "Home menu")]
        else:
            _pending_suggestions.update({"1": f"/bench {model}", "2": f"/trial text {strategy}", "0": "/home"})
            keys = [("1", f"Run the control first: a baseline round on {_short(model)}"),
                    ("2", "Show the exact strategy text"), ("0", "Home menu")]
        print(ui.actions("NEXT", keys) + "\n")
        return
    if not controls:
        print("\n[!] /trial: no control round -- run the baseline round first (/trial shows how).\n")
        return
    argv = [sys.executable, TRIAL_SCRIPT, "--strategy", strategy, "--backend", "ollama", "--model", model,
            "--k", str(k), "--tasks", ",".join(tasks)]
    label = f"trial {strategy} · ollama/{model} · {len(tasks)} task(s) · k={k}"
    rc, text = _bench_run(argv, label, ui)
    _notify("OSIRIS trial", f"{label}: {text}")
    if rc in (0, 130):
        _trial_result(None, ui)


def _trial_result(run_id, ui):
    """The latest (or given) trial against its control, and which hypothesis
    outcomes it can back."""
    import protege
    import trials
    entries, problem = protege.load_ledger()
    if problem:
        print(f"\n[!] bench ledger: {problem}\n")
        return
    if run_id is None:
        starts = [e for e in entries if e.get("kind") == "bench_run_start" and e.get("strategy")]
        if not starts:
            print("\n[*] No trial has run yet. /trial (or L, then the trial) shows the preflight.\n")
            return
        run_id = starts[-1]["run_id"]
    try:
        c = trials.compare(entries, run_id)
    except ValueError as e:
        print(f"\n[!] Trial {run_id} cannot be judged: {e}\n")
        return
    cm, tm = c["control_m"], c["treatment_m"]
    rows = [("research", "Strategy", f"{c['strategy']} on {_short(c['model'])}, {len(c['tasks'])} tasks"),
            ("current", "Control", f"hidden passes {cm['hidden_passes']}/{cm['tasks']} · false confidence "
                                   f"{cm['false_confidence']} · {c['control']}"),
            ("current", "Trial", f"hidden passes {tm['hidden_passes']}/{tm['tasks']} · false confidence "
                                 f"{tm['false_confidence']} · {c['treatment']}"),
            ("verified" if c["verdict"] == "better" else "review", "Verdict",
             c["verdict"] + (" -- preliminary: under 9 attempts per condition" if c["preliminary"] else ""))]
    inner = osiris_ui.Canvas(ui.mode, ui.cols - 4)
    allowed = trials.allowed_outcomes(c["verdict"])
    print("\n" + ui.panel("PROMPT-STRATEGY TRIAL · RESULT", inner.facts(rows).split("\n") + [
        "", f"Backs a hypothesis outcome of: {' or '.join(allowed)}. Nothing changed which prompt OSIRIS uses."]))
    open_h = research.open_hypotheses_for("trial-" + c["treatment"])
    hint = (f"/outcome {open_h[-1]['id']} {allowed[0]} trial-{c['treatment']}" if open_h else
            "No open hypothesis is decided by a trial: /hypothesis hyp-N tests trial-bench, then "
            "/outcome hyp-N ... trial-" + c["treatment"])
    _pending_suggestions.clear()
    _pending_suggestions.update({"1": f"/trial {c['strategy']} {c['model']}", "2": "/hypotheses", "0": "/home"})
    print(ui.actions("NEXT", [("1", "Repeat the trial (more evidence)"), ("2", "Hypotheses"), ("0", "Home menu")],
                     "Record it: " + hint) + "\n")


def _bench_run(argv, label, ui):
    """Runs one round (osiris_bench.py or bench_trial.py argv) with --events under a
    wake lock, drawing the live card; returns (exit code, verdict text). Shared by
    /bench and /trial."""
    import subprocess
    live = getattr(sys.stdout, "isatty", lambda: False)()
    view = _RoundView(ui, label, live)
    print()
    if live:
        view.draw()
    else:
        print(f"{ui.marker('research')} MENTOR ROUND · {label} · each task is saved when it finishes")
    lock = shutil.which("termux-wake-lock")
    if lock:
        subprocess.run([lock], timeout=10, stdin=subprocess.DEVNULL, capture_output=True)
    os.makedirs(os.path.dirname(BENCH_LOG), exist_ok=True)
    proc = subprocess.Popen(argv + ["--events"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    stopping = False
    try:
        with open(BENCH_LOG, "w", encoding="utf-8") as log:
            while True:
                try:
                    line = proc.stdout.readline()
                except KeyboardInterrupt:
                    # The terminal sent SIGINT to the round too; keep reading while it saves.
                    if stopping:
                        proc.kill()
                        break
                    stopping = True
                    view.note = "Stopping -- saving what finished (Ctrl-C again kills it)..."
                    if live:
                        view.draw()
                    else:
                        print("[*] Stopping the round -- saving what finished...")
                    continue
                if not line:
                    break
                log.write(line)
                log.flush()
                if line.startswith(BENCH_EVENT_PREFIX):
                    try:
                        view.event(json.loads(line[len(BENCH_EVENT_PREFIX):]))
                    except ValueError:
                        pass
        try:
            rc = proc.wait(timeout=60)
        except (KeyboardInterrupt, subprocess.TimeoutExpired):
            proc.kill()
            rc = proc.wait()
    finally:
        unlock = shutil.which("termux-wake-unlock")
        if lock and unlock:
            subprocess.run([unlock], timeout=10, stdin=subprocess.DEVNULL, capture_output=True)
    kind, text = BENCH_EXIT.get(rc, ("blocked", f"benchmark exited {rc}"))
    view.note, view.note_final = f"{text} · raw output: /bench log", True
    if live:
        view.draw()
    else:
        print(view.render())
    if rc not in (0, 130):
        try:  # show why, from the raw output
            with open(BENCH_LOG, encoding="utf-8", errors="replace") as f:
                tail = [l.rstrip() for l in f if not l.startswith(BENCH_EVENT_PREFIX) and l.strip()][-6:]
            print("\n".join("   " + l for l in tail))
        except OSError:
            pass
    return rc, text


def _bench(command: str = "/bench"):
    """'/bench': one mentor round inside the REPL. Runs osiris_bench.py --events
    (hidden tests score every candidate; each task is saved as it finishes)
    under a Termux wake lock and shows a live card: per task, the hidden-test
    verdict, false confidence and that it was saved. The raw output goes to
    ~/.osiris/bench/last_round.log ('/bench log'). Ctrl-C stops the round,
    not the REPL. Writes only the bench ledger, artifacts and that log."""
    import subprocess
    ui = osiris_ui.Canvas()
    if command.split()[1:] == ["log"]:
        try:
            with open(BENCH_LOG, encoding="utf-8", errors="replace") as f:
                text = "".join(l for l in f if not l.startswith(BENCH_EVENT_PREFIX))
            print("\n" + (text.rstrip() or "(empty)") + "\n")
        except OSError:
            print("\n[*] No round has run yet -- G runs one.\n")
        return
    argv, label = _bench_argv(command)
    if argv is None:
        print("\n" + osiris_ui.notice(ui, "review", "BENCH", label) + "\n")
        return
    if "now" not in command.lower().split()[1:]:
        _bench_preflight(command, argv, label, ui)
        return
    if argv[3] in ("gemini", "gateway"):
        print("\n" + osiris_ui.notice(ui, "review", "CLOUD MENTOR ROUND",
                                     f"{label} -- uses {argv[3]} API quota; prompts (task specs) leave the phone."))
        if _ask(" Type run to continue, anything else cancels: ").lower() != "run":
            print("[*] Cancelled -- nothing sent.\n")
            return
    rc, text = _bench_run(argv, label, ui)
    _notify("OSIRIS mentor round", f"{label}: {text}")
    if rc in (0, 130):
        _mentors()  # auto-advance: what the evidence says now


def _help():
    ui = osiris_ui.Canvas()
    lines = []
    for title, cmds in HELP_SECTIONS:
        if lines:
            lines.append("")
        lines.append(ui.style(title, "1"))
        lines += [f"  {c}" for c in cmds]
    print("\n" + ui.panel("COMMANDS", lines) + "\n")


def _status():
    """'/status': one read-only screen of facts read from disk -- no model
    call, no writes, no invented numbers. Anything unavailable says so."""
    rows = []
    g = None
    try:
        g = genome.get()
        rows.append(("Genome", f"generation {g['generation']} · {len(g['active_traits'])} active, "
                               f"{len(g['dormant_traits'])} dormant traits"))
    except Exception:
        rows.append(("Genome", "not initialized (run /ignite)"))
    head, dirty = _git_state()
    rows.append(("Workspace", f"{head} · {'UNCOMMITTED tracked changes' if dirty else 'clean'}"))
    stale = _code_fingerprint() != _STARTUP_FINGERPRINT
    rows.append(("Code", "CHANGED on disk since this session started -- restart" if stale else "current"))
    try:
        # Check existence first: constructing a Ledger creates the file, and
        # /status must not write anything.
        led = genome_ledger.GenomeLedger() if os.path.exists(genome_ledger.DEFAULT_PATH) else None
        entries = led.chain if led else []
        if entries:
            ok = led.verify()
            rows.append(("Genome ledger", f"{'valid' if ok else 'BROKEN: ' + str(led.problem())} · "
                                          f"{len(entries)} entries · tip {entries[-1]['hash'][:12]}"))
        else:
            rows.append(("Genome ledger", "no entries yet (the first /sprint execute or /apply creates one)"))
    except Exception as e:
        entries = None
        rows.append(("Genome ledger", f"unavailable: {type(e).__name__}: {e}"))
    if os.path.isdir(run_record.RUNS_DIR):
        n_runs = len(os.listdir(run_record.RUNS_DIR))
        if entries is None:
            rows.append(("Runs", f"{n_runs} on disk · ledger unreadable, not checked"))
        else:
            lost = run_record.orphans(entries)
            rows.append(("Runs", f"{n_runs} on disk" + (f" · {len(lost)} NOT in the ledger (unattested; "
                                                          f"newest {lost[-1]})" if lost else "")))
    counts, _stories = sprint_manager.summary()
    rows.append(("Backlog", " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "empty"))
    pending = _pending_write["path"]
    rows.append(("Pending write", pending or "none"))
    if _apply_block_reason():
        rows.append(("Apply", f"BLOCKED: {_apply_block_reason()}"))
    logs = sorted(glob.glob(os.path.join(SANDBOX_LOG_DIR, "*.log")))
    rows.append(("Last sandbox", os.path.basename(logs[-1]) if logs else "none yet"))
    try:
        # Not _organism_checkpoint_paths(): it creates the directory.
        with open(os.path.join(ORGANISM_HOME, "organism.json"), encoding="utf-8") as f:
            m = json.load(f)
        loss = f" · last loss {m['history'][-1]:.4f}" if m.get("history") else ""
        rows.append(("Engine 3", f"update step {m['step']}{loss} · level L1 not yet evaluated"))
    except (OSError, ValueError, KeyError):
        rows.append(("Engine 3", "no checkpoint yet"))
    bench = _last_bench_run()
    if bench:
        s_ = bench.get("summary") or {}
        who = "/".join(x for x in (bench.get("backend"), bench.get("model")) if x) or "model not recorded"
        if bench.get("status") == "unfinished":
            result = f"UNFINISHED after {s_.get('tasks', 0)} task(s)"
        else:
            result = (f"delivered {s_.get('delivered', '?')}/{s_.get('tasks', '?')} · "
                      f"false confidence {s_.get('false_confidence', '?')}")
        if bench.get("strategy"):
            who += f" · trial {bench['strategy']}"
        rows.append(("Last bench", f"{who} · k={bench.get('k', '?')} · {result}"
                                   + (f" · suite {bench['suite_sha256'][:12]}" if bench.get("suite_sha256") else "")))
    else:
        rows.append(("Last bench", "never run (python3 ~/bin/osiris_bench.py)"))
    ok, _base = _check_ollama_reachable(timeout=1.0)
    rows.append(("Backends", f"gemini {'key set' if gemini_bridge.is_configured() else 'no key'} · "
                             f"ollama {'reachable' if ok else 'unreachable'}"))
    dormant = _ignite_eligible(g) if g else 0
    rows.append(("Next", _status_next_step(pending, counts, dormant, stale)))

    print("\n" + "─" * 65)
    print(" 🧭 OSIRIS status")
    print("─" * 65)
    for label, value in rows:
        print(f"  {label:<14} {value}")
    print()


def _intent_status():
    """/intent status -- surfaces Engine 1's adaptive confidence per
    category so the feedback loop is observable, not invisible."""
    print("\n" + "─" * 65)
    print(" 🧭 Engine 1 adaptive confidence")
    print("─" * 65)
    if not _intent_quality_log:
        print("  (no routing feedback recorded yet this session)")
    for intent_type, history in _intent_quality_log.items():
        recent = history[-10:]
        avg = sum(recent) / len(recent)
        conf = _get_intent_confidence(intent_type)
        print(f"  {intent_type:<12} n={len(history):<4} recent_avg={avg:.2f}  "
              f"adjustment={_intent_confidence_adj.get(intent_type, 0.0):+.2f}  "
              f"confidence={conf:.2f}")
    print()


def _organism_checkpoint_paths():
    target_dir = ORGANISM_HOME
    try:
        os.makedirs(target_dir, exist_ok=True)
        test_file = os.path.join(target_dir, ".test_write")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    except OSError:
        fallback_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".osiris_data", "nclm_organism")
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            target_dir = fallback_dir
        except OSError:
            import tempfile
            target_dir = os.path.join(tempfile.gettempdir(), ".osiris", "nclm_organism")
            os.makedirs(target_dir, exist_ok=True)
    return (os.path.join(target_dir, "organism.npz"),
            os.path.join(target_dir, "organism.json"))


_PROVENANCE_RE = re.compile(r"\[PROVENANCE:\s*([A-Z_]+)\s*\]")


def _sync_telemetry_to_db(line: str) -> None:
    """Best-effort, fire-and-forget Supabase/Neon mirrors of one telemetry
    line. Runs off the main thread; each backend is independent -- one
    failing (not configured, network, missing table) never skips or blocks
    the other. The local flat-file write is the primary, always-succeeding
    path and already happened before this is ever called. Never blocks or
    slows down the organism's own loop."""
    match = _PROVENANCE_RE.search(line)
    provenance = match.group(1) if match else "PLACEHOLDER"

    try:
        if db_ledger.is_configured():
            db_ledger.sync_line(line, provenance)
    except Exception:
        pass  # supplementary mirror only; local log is already the record of truth

    try:
        if db_ledger.is_configured_neon():
            db_ledger.sync_line_neon(line, provenance)
    except Exception:
        pass  # supplementary mirror only; local log is already the record of truth


def _organism_telemetry(line: str):
    """Append one telemetry line to ~/.osiris/telemetry/nclm_loss.log for `tail -f` monitors.
    Also fires an optional, non-blocking Supabase mirror in the background --
    the local write below is unaffected by whether that succeeds."""
    try:
        os.makedirs(TELEMETRY_HOME, exist_ok=True)
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {line}\n")
            f.flush()
    except Exception:
        pass  # telemetry is best-effort; never let logging break the organism
    threading.Thread(target=_sync_telemetry_to_db, args=(line,), daemon=True).start()


def _organism_build():
    if ORGANISM_SRC not in sys.path:
        sys.path.insert(0, ORGANISM_SRC)
    from osiris.nclm import AdamW, LRSchedule, SovereignConfig, SovereignTransformerV2
    cfg = SovereignConfig(vocab_size=256, dropout=0.0, torsion_lock=True,
                           phase_conjugate=True, fractal_embedding=False,
                           **ORGANISM_GEOMETRY)
    model = SovereignTransformerV2(cfg)
    optimizer = AdamW(params=model.parameters(), lr=3e-4, weight_decay=0.01,
                       schedule=LRSchedule(warmup_steps=50, total_steps=10000))
    return model, optimizer


def _organism_load(model, optimizer):
    import numpy as np
    ckpt, meta = _organism_checkpoint_paths()
    if not (os.path.exists(ckpt) and os.path.exists(meta)):
        return 0, []
    try:
        with open(meta, encoding="utf-8") as f:
            m = json.load(f)
        with np.load(ckpt) as blob:
            for i, p in enumerate(model.parameters()):
                p.data[...] = blob[f"p{i}"]
                optimizer._m[i][...] = blob[f"m{i}"]
                optimizer._v[i][...] = blob[f"v{i}"]
        optimizer.step_count = int(m.get("step_count", 0))
        return int(m.get("step", 0)), list(m.get("history", []))
    except Exception as e:
        print(f"[!] Organism checkpoint unreadable ({e}); starting fresh.")
        return 0, []


def _organism_rotate_backup():
    """Copy the on-disk checkpoint (if any) to a numbered backup, labeled by the step
    it represents, before it gets overwritten -- gives a way to roll back if learning
    visibly degrades. Keeps only the ORGANISM_MAX_BACKUPS most recent."""
    ckpt, meta = _organism_checkpoint_paths()
    base_dir = os.path.dirname(ckpt)
    if not (os.path.exists(ckpt) and os.path.exists(meta)):
        return
    try:
        with open(meta, encoding="utf-8") as f:
            prev_step = int(json.load(f).get("step", 0))
    except Exception:
        prev_step = int(time.time())  # fallback unique label if meta is unreadable
    bckpt = os.path.join(base_dir, f"organism.step{prev_step}.npz")
    bmeta = os.path.join(base_dir, f"organism.step{prev_step}.json")
    try:
        shutil.copy2(ckpt, bckpt)
        shutil.copy2(meta, bmeta)
    except Exception:
        return
    backups = sorted(
        glob.glob(os.path.join(base_dir, "organism.step*.npz")),
        key=lambda p: int(re.search(r"step(\d+)\.npz$", p).group(1)),
    )
    for old in backups[:-ORGANISM_MAX_BACKUPS]:
        n = re.search(r"step(\d+)\.npz$", old).group(1)
        for p in (old, os.path.join(base_dir, f"organism.step{n}.json")):
            try:
                os.remove(p)
            except OSError:
                pass


def _organism_save(model, optimizer, step, history, rotate=True):
    import numpy as np
    ckpt, meta = _organism_checkpoint_paths()
    if rotate:
        _organism_rotate_backup()
    arrays = {}
    for i, p in enumerate(model.parameters()):
        arrays[f"p{i}"] = p.data
        arrays[f"m{i}"] = optimizer._m[i]
        arrays[f"v{i}"] = optimizer._v[i]
    tmp = ckpt + ".tmp"
    with open(tmp, "wb") as f:
        np.savez(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ckpt)
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({"step": step, "step_count": optimizer.step_count,
                    "history": history[-200:]}, f)


def _organism_learn(text: str):
    """Engine 3 online-update: one real gradient step on this exchange's bytes.
    Runs off the main thread so a slow/crashing step never blocks the REPL."""
    try:
        import numpy as np
        with _organism_lock:
            if _organism_state["model"] is None:
                model, optimizer = _organism_build()
                step, history = _organism_load(model, optimizer)
                _organism_state.update(model=model, optimizer=optimizer,
                                        step=step, history=history)
            model = _organism_state["model"]
            optimizer = _organism_state["optimizer"]

            from osiris.nclm import cross_entropy_loss
            from osiris.nclm.autograd import clip_grad_norm

            raw = text.encode("utf-8", errors="ignore")
            seq_len = min(ORGANISM_GEOMETRY["max_seq_len"] - 1, len(raw) - 1)
            if seq_len < 4:
                return
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.int64)
            x, y = data[:seq_len][None, :], data[1:seq_len + 1][None, :]

            optimizer.zero_grad()
            logits = model.forward(x)
            loss = cross_entropy_loss(logits, y)
            loss.backward()
            clip_grad_norm(model.parameters(), 1.0)
            optimizer.step()

            step = _organism_state["step"] + 1
            history = _organism_state["history"]
            history.append(float(loss.data))
            _organism_state["step"] = step
            # Persist every step: saving only on step % 5 == 0 meant no session
            # (max 4 steps each) ever saved, so every session restarted from
            # random weights (found 2026-09-23: 17 steps total, no organism.npz).
            try:
                _organism_save(model, optimizer, step, history, rotate=(step % 5 == 0))
            except OSError as e:
                pass
            recent = history[-20:]
            roll = sum(recent) / len(recent)
            with _stdout_lock:
                # "update step", not "learned": nothing has yet shown held-out
                # loss beats a unigram byte baseline (story S1, nclm_eval.py).
                print(f"\n🧬 [Organism {CHAT_MODEL}->NCLM] update step {step}  loss {float(loss.data):.4f}  "
                      f"(roll{len(recent)}={roll:.4f})")
            _organism_telemetry(
                f"OK step={step} loss={float(loss.data):.4f} roll{len(recent)}={roll:.4f} "
                f"exchange_len={len(text)} [PROVENANCE: COMPUTED]"
            )
            last_alert_step = _organism_state.get("last_drift_alert_step", -CUSUM_COOLDOWN_STEPS)
            if step - last_alert_step >= CUSUM_COOLDOWN_STEPS:
                drift = _cusum_detect(history)
                if drift:
                    direction, stat, h, avg_delta, dsigma = drift
                    _organism_state["last_drift_alert_step"] = step
                    with _stdout_lock:
                        print(f"\n⚠️  [Organism DRIFT] step {step}  direction={direction}  "
                              f"S={stat:.4f} > h={h:.4f}  (ref step-delta={avg_delta:.4f} sigma={dsigma:.4f})")
                    _organism_telemetry(
                        f"DRIFT step={step} direction={direction} S={stat:.4f} h={h:.4f} "
                        f"avg_delta={avg_delta:.4f} sigma={dsigma:.4f} [PROVENANCE: COMPUTED]"
                    )
    except Exception as e:
        with _stdout_lock:
            print(f"\n[!] Organism step failed (non-fatal, REPL continues): {type(e).__name__}: {e}")
        _organism_telemetry(
            f"FAIL error={type(e).__name__}: {e} exchange_len={len(text)} [PROVENANCE: COMPUTED]"
        )


CUSUM_WINDOW = 10
CUSUM_MIN_HISTORY = CUSUM_WINDOW * 2
CUSUM_COOLDOWN_STEPS = CUSUM_WINDOW


def _cusum_detect(history):
    """Two-sided Page's CUSUM change-point check on the loss history's FIRST
    DIFFERENCES, ported from organism_sim's agent.py poisoned-relay detector
    (same recurrence: S = max(0, S + (x - mu0 - k)), fire when S > h, reset
    after firing).

    Engine 3's loss is non-stationary by design -- it's SUPPOSED to trend down
    as it learns, so CUSUM can't run on raw values (or on values detrended by
    linear-regression extrapolation, which was tried and rejected: it still
    false-fired repeatedly in testing because out-of-sample extrapolation
    variance exceeds in-sample residual variance, especially near the edge of a
    short fitting window). Running on first differences (step-to-step change)
    instead sidesteps this: a steady decline has a roughly CONSTANT step size,
    so its differences are stationary even though the raw loss isn't, and only
    a genuine change in step size (a spike, a stall, a reversal) shows up as a
    shift in the difference series. k=0.5*sigma, h=5*sigma is the standard
    Page's-CUSUM heuristic (organism_sim's own 0.05/0.10/3.0 constants were
    calibrated to its pressure/error signal's scale, not loss magnitude, so
    they don't transfer directly). Verified in testing: 0 false positives on
    both a smooth and a noisy synthetic decline, fires promptly on a sudden
    level shift, a collapse, and a spike breaking an otherwise steady decline."""
    if len(history) < CUSUM_MIN_HISTORY:
        return None
    diffs = [history[i] - history[i - 1] for i in range(1, len(history))]
    if len(diffs) < CUSUM_WINDOW * 2:
        return None
    reference = diffs[-CUSUM_WINDOW * 2:-CUSUM_WINDOW]
    test = diffs[-CUSUM_WINDOW:]
    mu0 = sum(reference) / len(reference)
    var = sum((d - mu0) ** 2 for d in reference) / len(reference)
    sigma = var ** 0.5
    if sigma < 1e-6:
        return None
    k = 0.5 * sigma
    h = 5.0 * sigma
    s_pos = s_neg = 0.0
    peak_pos = peak_neg = 0.0
    for d in test:
        s_pos = max(0.0, s_pos + (d - mu0 - k))
        s_neg = min(0.0, s_neg + (d - mu0 + k))
        peak_pos = max(peak_pos, s_pos)
        peak_neg = min(peak_neg, s_neg)
    if peak_pos > h:
        return ("up", peak_pos, h, mu0, sigma)
    if -peak_neg > h:
        return ("down", -peak_neg, h, mu0, sigma)
    return None


def _organism_alerts(n=10):
    """Show the most recent drift-alert lines from nclm_loss.log."""
    if not os.path.exists(TELEMETRY_LOG):
        print("\n[*] No telemetry log yet -- no alerts.\n")
        return
    try:
        with open(TELEMETRY_LOG, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if " DRIFT " in l]
    except Exception as e:
        print(f"\n[!] Could not read telemetry log: {e}\n")
        return
    print("\n" + "─" * 65)
    print(" ⚠️  ORGANISM DRIFT ALERTS")
    print("─" * 65)
    if not lines:
        print("  (none recorded)")
    else:
        for line in lines[-n:]:
            print(f"  {line}")
    print()


def _spawn_organism_learn(text: str):
    if not text or not text.strip():
        return
    threading.Thread(target=_organism_learn, args=(text,), daemon=True).start()


def _format_age(mtime_epoch):
    if mtime_epoch is None:
        return "never"
    delta = time.time() - mtime_epoch
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def _organism_status():
    """Print step count, recent-loss trend, and checkpoint age without touching Ollama."""
    ckpt, meta = _organism_checkpoint_paths()
    if _organism_state["model"] is not None:
        step, history = _organism_state["step"], _organism_state["history"]
    else:
        step, history = 0, []
        if os.path.exists(meta):
            try:
                with open(meta, encoding="utf-8") as f:
                    m = json.load(f)
                step = int(m.get("step", 0))
                history = list(m.get("history", []))
            except Exception:
                pass
    recent = history[-10:]
    mtime = os.path.getmtime(ckpt) if os.path.exists(ckpt) else None
    print("\n" + "─" * 65)
    print(" 🧬 ORGANISM STATUS")
    print("─" * 65)
    print(f"  step:           {step}")
    print(f"  recent losses:  {', '.join(f'{v:.3f}' for v in recent) if recent else '(none yet)'}")
    if recent:
        print(f"  mean(last {len(recent)}):  {sum(recent) / len(recent):.4f}")
    print(f"  checkpoint:     {_format_age(mtime)}")
    print()


def _ledger_verify(command: str):
    """Run verify_ledger.py against a ledger file and print its audit output.
    `command` is the full '/ledger verify [path]' input; an optional trailing
    path overrides the default ~/.osiris/telemetry/nclm_loss.log."""
    import subprocess
    parts = command.split(maxsplit=2)
    path_arg = parts[2] if len(parts) > 2 else None
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_ledger.py")
    cmd = [sys.executable, script] + ([path_arg] if path_arg else [])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print()
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
    except Exception as e:
        print(f"\n[!] Could not run ledger verify: {type(e).__name__}: {e}")


_PROVENANCE_RE = re.compile(r"\[PROVENANCE:\s*([A-Z_]+)\]")
_NUMERIC_DATA_RE = re.compile(r"=\s*-?\d")


def _consensus(n: int = 15):
    """'/consensus': a fast, local, honest cross-reference of recent activity
    against the provenance ledger -- NOT the real 9-persona cognitive_mesh.py
    deliberation system (deliberately not invoked here: running that on every
    turn was rejected earlier this session as making the REPL unusable given
    known local-model latency). Pure file reads, no LLM/network calls, so this
    completes in well under a second by design -- that's the whole point of
    making it on-demand instead of automatic."""
    logs = [
        ("Engine 3 / telemetry", TELEMETRY_LOG),
        ("DD search", os.path.join(TELEMETRY_HOME, "dd_search.log")),
    ]

    print("\n" + "-" * 65)
    print(" ⚖️  /consensus -- recent activity vs. provenance ledger")
    print("-" * 65)

    all_recent = []  # (timestamp, source_label, line, tag_or_None, has_numeric_data)
    for label, path in logs:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                lines = [ln.rstrip("\n") for ln in f if ln.strip()]
        except OSError:
            continue
        for ln in lines[-n:]:
            ts = ln.split(" ", 1)[0] if " " in ln else ""
            m = _PROVENANCE_RE.search(ln)
            tag = m.group(1) if m else None
            has_numeric = bool(_NUMERIC_DATA_RE.search(ln))
            all_recent.append((ts, label, ln, tag, has_numeric))

    if not all_recent:
        print("  No telemetry yet -- nothing to cross-reference.")
        print()
        return

    all_recent.sort(key=lambda row: row[0])
    window = all_recent[-n:]

    tag_counts = {}
    untagged_numeric = []
    placeholder_hits = []
    for ts, label, ln, tag, has_numeric in window:
        if tag:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            if tag == "PLACEHOLDER":
                placeholder_hits.append((ts, label, ln))
        elif has_numeric:
            untagged_numeric.append((ts, label, ln))

    print(f"  Window: last {len(window)} event(s) across {len([l for l, p in logs if os.path.exists(p)])} log(s)")
    print()
    print("  Provenance breakdown:")
    if tag_counts:
        for tag, count in sorted(tag_counts.items(), key=lambda kv: -kv[1]):
            marker = "  ⚠️ " if tag == "PLACEHOLDER" else "    "
            print(f"{marker}{tag:<16} {count}")
    else:
        print("    (no tagged events in this window)")

    if placeholder_hits:
        print()
        print("  ⚠️  PLACEHOLDER data in this window -- never treat as a real result:")
        for ts, label, ln in placeholder_hits[-5:]:
            print(f"    [{label}] {ln}")

    if untagged_numeric:
        print()
        print(f"  ⚠️  {len(untagged_numeric)} numeric-bearing line(s) with NO provenance tag "
              f"(same integrity gap /ledger verify catches):")
        for ts, label, ln in untagged_numeric[-5:]:
            print(f"    [{label}] {ln}")

    last_ts, last_label, last_ln, last_tag, _ = window[-1]
    print()
    if last_tag:
        print(f"  Most recent event ({last_label}, {last_ts}): tagged [PROVENANCE: {last_tag}] -- accounted for.")
    else:
        print(f"  Most recent event ({last_label}, {last_ts}): NOT tagged -- not accounted for.")
    print()


# Qiskit/Qiskit Aer have no usable build on Termux's native ARM64/Android Python
# (no manylinux wheel, and the Rust toolchain reports an Android target that
# maturin refuses to cross-compile against). Standard Linux gets real prebuilt
# wheels, so Aer is installed instead inside the `debian` proot-distro container
# (already present on this device) at /root/aer_venv, and invoked through
# `proot-distro login debian`. This path is checked from the HOST filesystem
# view (the container's rootfs is a real directory tree), so osiris can detect
# availability without needing to enter the container just to check.
PROOT_DISTRO_BIN = "/data/data/com.termux/files/usr/bin/proot-distro"
# NOTE: checking .../aer_venv/bin/python3 directly is wrong -- venv's python3
# is always a symlink, here recorded as the absolute path "/usr/bin/python3"
# (valid only once resolved from INSIDE the container's virtualized root).
# os.path.exists() follows that target against whichever root is doing the
# checking, so this silently gives different answers on different hosts: any
# environment that happens to also have a real /usr/bin/python3 at its own
# root (this session's own sandbox, coincidentally) reports the bridge as
# present even when checked from the HOST side without entering the
# container -- while genuine native Termux (no such path at its true root)
# correctly reports it absent, exactly the false negative seen in real
# on-device testing. pyvenv.cfg is a real regular file, not a symlink, so it
# reflects "this venv was actually created here" without that ambiguity.
DEBIAN_AER_VENV_HOST_PATH = (
    "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/"
    "rootfs/root/aer_venv/pyvenv.cfg"
)
# Path as seen FROM INSIDE the container -- proot-distro's default (non-isolated)
# mode auto-binds /data/data/com.termux at the same absolute path, so this is
# identical to the host path, just resolved from the other side of the bind mount.
DEBIAN_AER_VENV_CONTAINER_PATH = "/root/aer_venv/bin/python3"


def _dd_search(command: str):
    """Run nclm_aer_evaluator.py (NCLM-vs-baseline DD-sequence pilot, see
    DD_SEARCH_PREREGISTRATION.md) and print its output. `command` is the full
    '/dd search [--budget N]' input.

    Prefers evaluating through the `debian` proot-distro container's Aer venv
    (real Qiskit Aer available there); falls back to running natively under
    Termux's own Python if that bridge isn't set up yet, which still exercises
    generation but will hit the known missing-qiskit_aer message on evaluation."""
    import subprocess
    budget_match = re.search(r"--budget\s+(\d+)", command)
    budget = budget_match.group(1) if budget_match else "8"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nclm_aer_evaluator.py")

    use_bridge = os.path.exists(DEBIAN_AER_VENV_HOST_PATH)
    if use_bridge:
        # -e HOME=... is required: proot-distro login does NOT inherit the
        # outer Termux HOME by default, it sets the container's own (/root).
        # Without this, os.path.expanduser("~") inside the evaluator would
        # resolve against the WRONG home and silently write telemetry/
        # checkpoints into the container's own /root/.osiris/ instead of the
        # shared Termux-visible one that /organism status, /ledger verify,
        # and the tmux monitor pane all read from. Found by testing this
        # exact failure mode, not by inspection.
        cmd = [PROOT_DISTRO_BIN, "login", "debian",
               "-e", "HOME=/data/data/com.termux/files/home", "--",
               DEBIAN_AER_VENV_CONTAINER_PATH, script, "--budget", budget]
    else:
        cmd = [sys.executable, script, "--budget", budget]

    try:
        where = "via the debian proot Aer bridge" if use_bridge else "natively (no Aer bridge found)"
        print(f"\n[*] Running NCLM DD-search pilot (budget={budget}) {where} -- this "
              f"simulates each candidate on Qiskit Aer and can take a while...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print(result.stdout, end="")
        if "ModuleNotFoundError: No module named 'qiskit" in result.stderr:
            print("[!] Qiskit/Qiskit Aer isn't installed on this device -- "
                  "see DD_SEARCH_PREREGISTRATION.md. Set up the debian proot bridge "
                  "with:\n"
                  "    bash bin/setup_aer_debian.sh\n"
                  "(runs OUTSIDE any existing proot session -- e.g. from a fresh "
                  "native Termux shell; installing from inside an already-proot'd "
                  "shell hits a nested-proot exec failure, a known proot-distro "
                  "limitation, not a bug in this script.)\n")
        elif result.stderr:
            print(result.stderr, end="")
    except subprocess.TimeoutExpired:
        print("\n[!] DD search timed out after 600s -- try a smaller --budget.")
    except Exception as e:
        print(f"\n[!] Could not run DD search: {type(e).__name__}: {e}")


def _dd_programmatic(command: str):
    """Run '/dd programmatic [--count N]': generate N DD sequences deterministically
    via algorithmic_dd_generator.py (no NCLM involved -- see that file's docstring for
    why this exists), then evaluate them through the SAME real Aer evaluator entry
    point /dd search uses (nclm_aer_evaluator.py --sequences-file, source=algorithmic),
    not a duplicated evaluation path."""
    import subprocess
    import tempfile

    count_match = re.search(r"--count\s+(\d+)", command)
    count = count_match.group(1) if count_match else "10"
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    gen_script = os.path.join(bin_dir, "algorithmic_dd_generator.py")
    eval_script = os.path.join(bin_dir, "nclm_aer_evaluator.py")

    print(f"\n[*] Generating {count} algorithmic DD sequence(s) (deterministic, no NCLM)...")
    try:
        gen_result = subprocess.run(
            [sys.executable, gen_script, "--count", count],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as e:
        print(f"[!] Could not run algorithmic_dd_generator.py: {type(e).__name__}: {e}")
        return

    sequences = [ln for ln in gen_result.stdout.splitlines() if ln.strip()]
    if not sequences:
        print(f"[!] Generator produced no sequences.\n{gen_result.stderr}")
        return
    print(f"[*] Generated {len(sequences)} valid sequence(s).")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write("\n".join(sequences) + "\n")
        seq_path = tf.name

    try:
        use_bridge = os.path.exists(DEBIAN_AER_VENV_HOST_PATH)
        if use_bridge:
            cmd = [PROOT_DISTRO_BIN, "login", "debian",
                   "-e", "HOME=/data/data/com.termux/files/home", "--",
                   DEBIAN_AER_VENV_CONTAINER_PATH, eval_script,
                   "--sequences-file", seq_path, "--source", "algorithmic"]
        else:
            cmd = [sys.executable, eval_script,
                   "--sequences-file", seq_path, "--source", "algorithmic"]

        where = "via the debian proot Aer bridge" if use_bridge else "natively (no Aer bridge found)"
        print(f"[*] Evaluating {where} against real Aer -- this can take a while...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print(result.stdout, end="")
        if "ModuleNotFoundError: No module named 'qiskit" in result.stderr:
            print("[!] Qiskit/Qiskit Aer isn't installed on this device -- "
                  "see DD_SEARCH_PREREGISTRATION.md. Set up the debian proot bridge "
                  "with:\n"
                  "    bash bin/setup_aer_debian.sh\n"
                  "(run OUTSIDE any existing proot session.)\n")
        elif result.stderr:
            print(result.stderr, end="")
    except subprocess.TimeoutExpired:
        print("\n[!] Evaluation timed out after 600s -- try a smaller --count.")
    except Exception as e:
        print(f"\n[!] Could not evaluate sequences: {type(e).__name__}: {e}")
    finally:
        try:
            os.remove(seq_path)
        except OSError:
            pass


def _dd_pretrain(command: str):
    """Run pretrain_nclm.py (trains the DD-focused checkpoint on the Aer-filtered elite
    corpus from build_dd_corpus.py, see DD_SEARCH_PREREGISTRATION.md). No Aer/proot bridge
    needed -- pure classical gradient descent, runs natively under Termux's own Python.
    `command` is the full '/dd pretrain [--steps-per-text N]' input."""
    import subprocess
    steps_match = re.search(r"--steps-per-text\s+(\d+)", command)
    steps = steps_match.group(1) if steps_match else "40"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pretrain_nclm.py")
    cmd = [sys.executable, script, "--steps-per-text", steps]
    try:
        print(f"\n[*] Pretraining DD checkpoint on the elite corpus (steps-per-text={steps})...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
    except subprocess.TimeoutExpired:
        print("\n[!] DD pretrain timed out after 300s.")
    except Exception as e:
        print(f"\n[!] Could not run DD pretrain: {type(e).__name__}: {e}")


def _check_ollama_reachable(timeout=OLLAMA_STARTUP_TIMEOUT):
    base = OLLAMA_GEN_URL.rsplit("/api/", 1)[0]
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{base}/api/tags"), timeout=timeout):
            try:
                _resolve_active_models()
            except Exception:
                pass
            return True, base
    except Exception:
        return False, base

CODEBASE_INTENT_RE = re.compile(
    r"\b(code\s*base|repo|repository|architecture|grok\w*|source\s*code|"
    r"scan\s+(the\s+)?(entire\s+|whole\s+|current\s+)?(dir|directory|project|code))\b",
    re.IGNORECASE,
)

# --- Phase 2: gated filesystem writes for Engine 2. Deliberately NOT autonomous --
# a small local model that has already hallucinated once this session, writing
# unreviewed to disk with no rollback but git, is not a safe default. Every write
# requires an explicit human /apply after seeing a real preview/diff.
MODIFY_INTENT_RE = re.compile(
    r"\b(write|create)\s+(a\s+|the\s+)?file\b|\b(modify|patch|update|fix)\b.*\b(file|code|function|script)\b|"
    r"\badd\s+(a\s+)?function\b",
    re.IGNORECASE,
)
WRITE_FILE_RE = re.compile(r'<WRITE_FILE\s+path="([^"]+)"\s*>(.*?)</WRITE_FILE>', re.DOTALL)
TEST_FUNCTION_RE = re.compile(r'<TEST_FUNCTION>(.*?)</TEST_FUNCTION>', re.DOTALL)
SELF_MODIFY_OVERRIDE = "--allow-self-modify"  # required in the user's own input to
                                               # target a live osiris script itself

_pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}


def _protected_script_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    names = ("osiris", "osiris_ast_bridge.py", "verify_ledger.py", "launch_fold.sh")
    protected = set()
    for base in (here, "/data/data/com.termux/files/home/bin", "/data/data/com.termux/files/usr/bin"):
        for n in names:
            protected.add(os.path.realpath(os.path.join(base, n)))
    return protected


def _check_write_safety(raw_path: str, allow_self_modify: bool):
    """Resolve raw_path against the safe root (cwd at invocation) and reject
    anything that escapes it via traversal/absolute-path, or targets a live
    osiris script, unless the user's own input explicitly opted in."""
    root = os.path.realpath(os.getcwd())
    candidate = os.path.realpath(os.path.join(root, raw_path))
    if not (candidate == root or candidate.startswith(root + os.sep)):
        return None, f"path '{raw_path}' resolves outside the safe root ({root}); refusing."
    if candidate in _protected_script_paths() and not allow_self_modify:
        return None, (f"path '{raw_path}' targets a live osiris script; refusing without "
                       f"the explicit '{SELF_MODIFY_OVERRIDE}' override in your request.")
    return candidate, None


def _propose_write(raw_path: str, content: str, allow_self_modify: bool, story_meta: dict = None):
    global _pending_write
    candidate, err = _check_write_safety(raw_path, allow_self_modify)
    if err:
        print(f"\n[!] WRITE_FILE rejected: {err}\n")
        return False
    existed = os.path.exists(candidate)
    print("\n" + "─" * 65)
    print(f" ✍️  PROPOSED FILE WRITE: {candidate}")
    print("─" * 65)
    if existed:
        try:
            with open(candidate, encoding="utf-8", errors="replace") as f:
                old_lines = f.read().splitlines(keepends=True)
        except Exception as e:
            old_lines = []
            print(f"[!] Could not read existing file for diff: {e}")
        new_lines = content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines,
                                          fromfile=candidate, tofile=candidate + " (proposed)"))
        print("".join(diff) if diff else "(no changes -- proposed content is identical to disk)")
    else:
        preview_lines = content.splitlines()
        print("(new file)")
        for line in preview_lines[:40]:
            print(line)
        if len(preview_lines) > 40:
            print(f"... ({len(preview_lines) - 40} more lines)")
    # What the diff above was computed against: /apply refuses if the target
    # no longer matches it (see _apply_pending_write).
    _pending_write = {"path": candidate, "content": content, "existed": existed, "raw_path": raw_path,
                       "story_meta": story_meta, "base_sha256": _sha256_of(candidate)}
    print(f"\n[?] Apply this write to {candidate}? Type /apply to confirm "
          "(anything else asks before discarding).")
    return True


APPLY_INCIDENT_LOG = os.path.join(os.path.expanduser("~"), ".osiris", "apply_incidents.log")
# Present only when the genome ledger itself may hold an uncommitted record.
# Survives restarts; a human deletes it after reconciling the ledger.
APPLY_BLOCK_FILE = os.path.join(os.path.expanduser("~"), ".osiris", "APPLY_BLOCKED")
_apply_blocked = {"reason": None}


def _apply_block_reason():
    """This session's block, else a persistent one from APPLY_BLOCK_FILE."""
    if _apply_blocked["reason"]:
        return _apply_blocked["reason"]
    try:
        with open(APPLY_BLOCK_FILE, encoding="utf-8") as f:
            return "persistent block: " + (f.read().strip() or "reason not recorded")
    except OSError:
        return None


def _atomic_write_bytes(path, data):
    """Write to a temp file in the same directory, fsync, then os.replace: the
    target is either the old bytes or the new bytes, never half-written."""
    tmp = f"{path}.osiris-tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _sha256_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def _log_incident(record):
    """Independent fallback sink for when the genome ledger itself failed:
    plain JSON Lines, best effort, never raises."""
    try:
        os.makedirs(os.path.dirname(APPLY_INCIDENT_LOG), exist_ok=True)
        with open(APPLY_INCIDENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


def _apply_pending_write():
    """Fail-closed apply: decide -> atomic write -> append the ledger record ->
    only then mark the story done and bump the generation. A written file
    with no ledger record is an unprovable state change, so if the append
    fails the write is rolled back byte-for-byte and further /apply is
    blocked for this session (a ledger that failed once will fail again)."""
    global _pending_write
    blocked = _apply_block_reason()
    if blocked:
        how = (f"reconcile the genome ledger, then delete {APPLY_BLOCK_FILE}"
               if os.path.exists(APPLY_BLOCK_FILE) else "fix the cause, then restart osiris")
        print(f"\n[!] /apply refused: {blocked}\n"
              f"    To continue: {how}. Incidents: {APPLY_INCIDENT_LOG}\n")
        _pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}
        return
    path, content, existed = _pending_write["path"], _pending_write["content"], _pending_write["existed"]
    story_meta = _pending_write.get("story_meta")
    if "base_sha256" in _pending_write and _sha256_of(path) != _pending_write["base_sha256"]:
        # The target changed (edited, created or deleted) after the diff was
        # shown: applying now would overwrite changes nobody reviewed.
        was, now = _pending_write["base_sha256"], _sha256_of(path)
        print(f"\n[!] /apply refused: {path} changed since this proposal was shown "
              f"({'absent' if was is None else 'sha256 ' + was[:12]} then, "
              f"{'absent' if now is None else 'sha256 ' + now[:12]} now). Nothing written.")
        _organism_telemetry(f"APPLY_REFUSED_TARGET_CHANGED path={path} [PROVENANCE: COMPUTED]")
        if story_meta:
            print(f"    Story #{story_meta['id']} goes back to active: /sprint execute #{story_meta['id']} "
                  f"proposes against the current file.")
        _discard_pending_write()
        return
    new_bytes = content.encode("utf-8")
    try:
        before = None
        if existed:
            with open(path, "rb") as f:
                before = f.read()
            shutil.copy2(path, f"{path}.bak.{int(time.time())}")
        sha_before = hashlib.sha256(before).hexdigest() if before is not None else None
        unchanged = before == new_bytes
        # Decided BEFORE the write so the ledger record can state it. A
        # generation bump means the trait's actual target module changed on
        # disk -- not that a scratch osiris_story_N.py was written (2026-09-23:
        # generation 2 was claimed while gemini_bridge.py was untouched).
        gen_before = genome.get()["generation"] if os.path.exists(genome.GENOME_PATH) else None
        target = (story_meta or {}).get("target")
        is_ignite = bool(story_meta) and story_meta.get("source") == "ignite"
        metamorphosis = is_ignite and bool(target) and os.path.realpath(path) == target and not unchanged
        gen_after = gen_before + 1 if metamorphosis and gen_before is not None else gen_before
        _atomic_write_bytes(path, new_bytes)
    except Exception as e:
        print(f"\n[!] Write failed, nothing changed: {type(e).__name__}: {e}\n")
        _organism_telemetry(f"WRITE_FAIL path={path} error={type(e).__name__}: {e} [PROVENANCE: COMPUTED]")
        _pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}
        return

    try:
        entry = _record_state_change(path, new_bytes, existed, sha_before, story_meta,
                                     gen_before, gen_after, metamorphosis)
    except Exception as e:
        _fail_closed(path, before, sha_before, e)
        _pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}
        return

    try:
        kind = "overwrite" if existed else "new file"
        print(f"\n✅ Applied and recorded: {path} ({kind}{', backup made' if existed else ''}) "
              f"-- genome ledger tip {entry['hash'][:12]}\n")
        _organism_telemetry(f"WRITE path={path} kind={kind} backup={existed} [PROVENANCE: COMPUTED]")
        if story_meta:
            sprint_manager.set_status(story_meta["id"], "done")
        if is_ignite and not metamorphosis:
            reason = ("trait names no target module" if not target else
                      "content identical to what was on disk" if unchanged else
                      f"wrote {path}, not the target {target}")
            print(f"[*] No metamorphosis: {reason}. Generation unchanged.\n")
        elif metamorphosis:
            new_gen = genome.complete_metamorphosis(story_meta["trait"])
            print(f"🧬 Metamorphosis complete -- generation {new_gen}.\n")
            if new_gen != gen_after:
                print(f"[!] genome.json reports generation {new_gen}, the ledger recorded {gen_after}.\n")
            _organism_telemetry(
                f"METAMORPHOSIS_COMPLETE generation={new_gen} trait={story_meta['trait']} "
                # A generation bump is still a real, deterministically-computed
                # state change -- COMPUTED already covers it, same as every
                # other real local computation this session. The event LABEL
                # (METAMORPHOSIS_COMPLETE, above) carries the "what happened"
                # meaning; the tag stays in the fixed 8-value taxonomy so
                # verify_ledger.py never has to special-case a 9th value.
                f"story_id={story_meta.get('id')} [PROVENANCE: COMPUTED]"
            )
    finally:
        _pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}


def _block_apply_persistently(message):
    """Writes APPLY_BLOCK_FILE (best effort) and blocks this session too."""
    _apply_blocked["reason"] = message
    try:
        os.makedirs(os.path.dirname(APPLY_BLOCK_FILE), exist_ok=True)
        with open(APPLY_BLOCK_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}\n")
    except OSError:
        pass


def _fail_closed(path, before, sha_before, error):
    """The file was written but its ledger record could not be appended:
    restore the exact prior bytes (or remove a new file), then block /apply."""
    reason = f"genome ledger append failed ({type(error).__name__}: {error})"
    ledger_unknown = isinstance(error, genome_ledger.LedgerAppendUnknown)
    if ledger_unknown:
        # The ledger may hold a record of the write being undone below: block
        # across restarts until a human reconciles it.
        _block_apply_persistently(f"ledger may contain an uncommitted record for {path}: {error}")
    try:
        if before is None:
            os.remove(path)
        else:
            _atomic_write_bytes(path, before)
        restored = _sha256_of(path) == sha_before
    except Exception as restore_error:
        restored = False
        reason += f"; rollback failed ({type(restore_error).__name__}: {restore_error})"
    _apply_blocked["reason"] = reason
    actual = _sha256_of(path)
    if restored:
        print(f"\n[!] Apply NOT committed: {reason}.\n"
              f"    {path} was rolled back byte-for-byte "
              f"({'removed' if before is None else 'sha256 ' + sha_before[:12]}). /apply is blocked "
              f"for this session.\n")
        _log_incident({"event": "ledger_append_unknown" if ledger_unknown else "apply_rolled_back",
                       "path": path, "reason": reason, "sha256_before": sha_before})
        if ledger_unknown:
            print(f"[!!] The genome ledger may still contain a record of this undone write. /apply "
                  f"stays blocked across restarts until you reconcile it and delete {APPLY_BLOCK_FILE}.\n")
    else:
        print(f"\n[!!] Apply outcome UNKNOWN: {reason}.\n"
              f"    {path}: expected sha256 {sha_before or '(absent)'}, actual {actual or '(absent)'}.\n"
              f"    Reconcile this file by hand. /apply is blocked for this session.\n")
        _log_incident({"event": "apply_outcome_unknown", "path": path, "reason": reason,
                       "sha256_expected": sha_before, "sha256_actual": actual})
    _organism_telemetry(f"APPLY_FAIL_CLOSED path={path} restored={restored} [PROVENANCE: COMPUTED]")


def _record_state_change(path, new_bytes, existed, sha_before, story_meta, gen_before, gen_after,
                         metamorphosis):
    """Appends the applied write to ~/.osiris/genome_ledger.jsonl: what changed
    (path, before/after SHA-256), why (story, trait), how it was produced
    (backend) and its effect on the genome. Raises on failure -- the caller
    rolls the write back rather than leave an unrecorded change."""
    home = os.path.expanduser("~")
    return genome_ledger.GenomeLedger().append("file_change", {
        "path": os.path.relpath(path, home) if path.startswith(home + os.sep) else path,
        "action": "modify" if existed else "create",
        "sha256_before": sha_before,
        "sha256_after": hashlib.sha256(new_bytes).hexdigest(),
        "story_id": (story_meta or {}).get("id"),
        "story_source": (story_meta or {}).get("source"),
        "trait": (story_meta or {}).get("trait"),
        "backend": _last_backend.get("name"),
        "approved_via": "/apply",
        "run_id": (story_meta or {}).get("run_id"),
        "candidate_sha256": (story_meta or {}).get("candidate_sha256"),
        "metamorphosis": metamorphosis,
        "generation_before": gen_before,
        "generation_after": gen_after,
    })


def _is_apply(text: str) -> bool:
    """'/apply', 'apply', 'Apply.', '//apply' -- all the same intent."""
    return text.strip().lower().strip("/ .!") == "apply"


def _looks_like_apply(text: str) -> bool:
    """A near-miss such as 'aply' or 'appy' -- asked about, never auto-applied."""
    norm = text.strip().lower().strip("/ .!")
    return 0 < len(norm) <= 8 and " " not in norm and \
        difflib.SequenceMatcher(None, norm, "apply").ratio() >= 0.75


def _ask_yes(question: str) -> bool:
    print(f"[?] {question} (y/N) ", end="", flush=True)
    return sys.stdin.readline().strip().lower() in ("y", "yes")


def _discard_pending_write():
    global _pending_write
    print(f"\n[*] Discarded proposed write to {_pending_write['path']}.\n")
    story_meta = _pending_write.get("story_meta")
    if story_meta:
        sprint_manager.set_status(story_meta["id"], "active")
    _pending_write = {"path": None, "content": None, "existed": None, "raw_path": None, "story_meta": None}

# --- /auto-enhance: command-triggered, NOT a background thread. An always-on
# loop firing Ollama calls has real battery/thermal cost on a phone; a command
# the user explicitly runs gets the same capability without that cost. Every
# proposal still goes through the SAME gate above -- this never writes on its
# own, it only ever produces a pending write for /apply to accept or anything
# else to discard, identical to a normal modify-intent flow.
AUTO_ENHANCE_EXCLUDE_NAMES = {"consciousness.py", "osiris_bootstrap.py"}
AUTO_ENHANCE_EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules"}


def _detect_proot() -> str:
    custom = os.environ.get("PROOT_BIN")
    if custom and os.path.exists(custom):
        return custom
    which = shutil.which("proot")
    if which:
        return which
    termux_bin = "/data/data/com.termux/files/usr/bin/proot"
    if os.path.exists(termux_bin):
        return termux_bin
    # Desktop Linux / WSL runner fallback shim
    shim_dir = os.path.join(os.path.expanduser("~"), ".osiris", "bin")
    try:
        os.makedirs(shim_dir, exist_ok=True)
        shim_path = os.path.join(shim_dir, "proot_shim")
        if not os.path.exists(shim_path):
            with open(shim_path, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n"
                        "while [ $# -gt 0 ]; do\n"
                        "    case \"$1\" in\n"
                        "        -b) shift 2 ;;\n"
                        "        *) break ;;\n"
                        "    esac\n"
                        "done\n"
                        "exec \"$@\"\n")
            os.chmod(shim_path, 0o755)
        return shim_path
    except OSError:
        import tempfile
        t_shim = os.path.join(tempfile.gettempdir(), "osiris_proot_shim")
        if not os.path.exists(t_shim):
            try:
                with open(t_shim, "w", encoding="utf-8") as f:
                    f.write("#!/bin/sh\n"
                            "while [ $# -gt 0 ]; do\n"
                            "    case \"$1\" in\n"
                            "        -b) shift 2 ;;\n"
                            "        *) break ;;\n"
                            "    esac\n"
                            "done\n"
                            "exec \"$@\"\n")
                os.chmod(t_shim, 0o755)
            except OSError:
                pass
        return t_shim

PROOT_BIN = _detect_proot()
SANDBOX_PROTECTED_PREFIX = (
    "/data/data/com.termux/files/home"
    if os.path.exists("/data/data/com.termux/files/home")
    else os.path.expanduser("~")
)

_UNSAFE_IMPORT_MODULES = {"subprocess", "socket", "ctypes"}
_UNSAFE_BUILTIN_CALLS = {"eval", "exec", "__import__"}
_WRITE_METHODS = {"write_text", "write_bytes", "unlink", "rmdir", "rename", "replace"}


def _static_ast_check(test_code: str):
    """Defense-in-depth pre-check on Engine 2's proposed TEST_FUNCTION source,
    run BEFORE any subprocess execution. Rejects test code that has no
    legitimate reason to exist in a unit test for a code-review proposal:
    process/network/ctypes access, eval/exec/__import__, os.system, or an
    absolute-path string literal handed to a known filesystem-writing call.

    This is a real but evadable-by-more-effort static scan (e.g. a determined
    proposal could still build a path via string concatenation rather than a
    literal) -- it is a SECOND layer, not a replacement for the proot-based
    path containment in _run_sandboxed_test. Returns None if clean, else a
    short human-readable rejection reason."""
    try:
        tree = ast.parse(test_code)
    except SyntaxError as e:
        return f"test code has a syntax error: {e}"

    def is_abs_str(node):
        return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _UNSAFE_IMPORT_MODULES:
                    return f"disallowed import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _UNSAFE_IMPORT_MODULES:
                return f"disallowed import: {node.module}"
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _UNSAFE_BUILTIN_CALLS:
                return f"disallowed call: {func.id}()"
            if isinstance(func, ast.Attribute):
                # os.system(...)
                if func.attr == "system" and isinstance(func.value, ast.Name) and func.value.id == "os":
                    return "disallowed call: os.system()"
                # os.remove/unlink/rename/replace(<abs literal>, ...)
                if (isinstance(func.value, ast.Name) and func.value.id == "os"
                        and func.attr in {"remove", "unlink", "rename", "replace"}):
                    if any(is_abs_str(a) for a in node.args):
                        return f"disallowed absolute-path write: os.{func.attr}(...)"
                # shutil.rmtree/move/copy*(<abs literal>, ...)
                if (isinstance(func.value, ast.Name) and func.value.id == "shutil"
                        and (func.attr == "rmtree" or func.attr == "move" or func.attr.startswith("copy"))):
                    if any(is_abs_str(a) for a in node.args):
                        return f"disallowed absolute-path write: shutil.{func.attr}(...)"
                # open(<abs literal>, mode=...) in a write/append/exclusive mode
                if func.attr == "open" or (isinstance(func, ast.Name) and False):
                    pass  # handled below for bare open()
                # Path(<abs literal>).write_text/write_bytes/unlink/rmdir/rename/replace(...)
                if func.attr in _WRITE_METHODS and isinstance(func.value, ast.Call):
                    inner = func.value.func
                    inner_name = inner.attr if isinstance(inner, ast.Attribute) else getattr(inner, "id", "")
                    if inner_name == "Path" and any(is_abs_str(a) for a in func.value.args):
                        return f"disallowed absolute-path write: Path(...).{func.attr}(...)"
            if isinstance(func, ast.Name) and func.id == "open":
                if node.args and is_abs_str(node.args[0]):
                    mode = ""
                    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                        mode = node.args[1].value
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            mode = kw.value.value
                    if any(c in mode for c in "wax+"):
                        return "disallowed absolute-path write: open(..., mode with w/a/x)"
    return None


def _get_sandbox_log_dir() -> str:
    target = os.path.join(os.path.expanduser("~"), ".osiris", "sandbox_logs")
    try:
        os.makedirs(target, exist_ok=True)
        test_file = os.path.join(target, ".test_write")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return target
    except OSError:
        fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".osiris_data", "sandbox_logs")
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except OSError:
            import tempfile
            t = os.path.join(tempfile.gettempdir(), "osiris_sandbox_logs")
            os.makedirs(t, exist_ok=True)
            return t

SANDBOX_LOG_DIR = _get_sandbox_log_dir()
_last_sandbox = {"path": None, "passed": None}


def _sandbox_probe(timeout: int = 20):
    """Runs a trivial script through the same proot command the gate uses.
    Returns None if the sandbox works, else a one-line reason. Inside a
    proot-distro session proot cannot start a nested proot ("the loader was
    not found"), so every candidate -- references included -- 'fails'; a
    caller that scores candidates must probe first, or it reports an
    environment problem as a code regression (2026-09-23: osiris_bench --check
    said "Suite INVALID" in proot-distro, "Suite valid." in native Termux)."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="osiris_probe_")
    decoy_home = os.path.join(tmpdir, "_decoy_home")
    os.makedirs(decoy_home, exist_ok=True)
    try:
        cmd = [PROOT_BIN, "-b", f"{decoy_home}:{SANDBOX_PROTECTED_PREFIX}",
               sys.executable, "-c", "print('SANDBOX_PROBE_OK')"]
        try:
            returncode, output, timed_out = _run_limited(cmd, tmpdir, _sandbox_env(tmpdir), timeout)
        except OSError as e:
            return f"cannot start {PROOT_BIN}: {e}"
        if timed_out:
            return f"probe timed out after {timeout}s"
        if returncode == 0 and "SANDBOX_PROBE_OK" in output:
            return None
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        return f"proot exited {returncode}: {' / '.join(lines[-2:]) or 'no output'}"[:200]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _run_sandboxed_test(module_basename: str, patched_content: str, test_code: str, timeout: int = 20):
    """Runs _run_sandboxed_test_inner and writes the COMPLETE outcome (proposed
    module, test, full output) to ~/.osiris/sandbox_logs/, so a failure can be
    diagnosed with /why -- callers only print the first 150 chars, which left
    story #21's failure (2026-09-23) undiagnosable. Logging never changes the
    verdict; a log write failure is reported and ignored."""
    passed, output = _run_sandboxed_test_inner(module_basename, patched_content, test_code, timeout)
    try:
        os.makedirs(SANDBOX_LOG_DIR, exist_ok=True)
        name = f"{time.strftime('%Y%m%dT%H%M%S')}_{module_basename}_{'pass' if passed else 'fail'}.log"
        path = os.path.join(SANDBOX_LOG_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"module: {module_basename}\nverdict: {'PASS' if passed else 'FAIL'}\n\n")
            f.write(f"=== output ===\n{output}\n\n=== test ===\n{test_code}\n\n"
                    f"=== proposed module ===\n{patched_content}\n")
        _last_sandbox.update(path=path, passed=passed)
    except OSError as e:
        print(f"[!] Could not write sandbox log: {e}")
    return passed, output


def _why():
    """'/why': prints the most recent sandbox log in full (this session's, or
    the newest on disk if none ran this session)."""
    path = _last_sandbox["path"]
    if path is None:
        logs = sorted(glob.glob(os.path.join(SANDBOX_LOG_DIR, "*.log")))
        path = logs[-1] if logs else None
    if path is None or not os.path.exists(path):
        print("\n[!] /why: no sandbox log yet.\n")
        return
    print("\n" + "─" * 65)
    print(f" 🔎 {path}")
    print("─" * 65)
    with open(path, encoding="utf-8", errors="replace") as f:
        print(f.read())


# Environment variables a sandboxed child may inherit. Everything else --
# including every API key _load_dotenv() put in os.environ -- is dropped:
# before 2026-09-23 the child inherited the full environment, so model-written
# module code (which, unlike the test, gets no static check) could read the
# Gemini/gateway/database keys, and Termux cannot block its network access.
_SANDBOX_ENV_KEEP = ("PATH", "PREFIX", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "LD_PRELOAD",
                     "TERM", "SHELL", "USER", "LOGNAME")
_SANDBOX_ENV_KEEP_PREFIXES = ("ANDROID_", "TERMUX_", "PROOT_")
# Defense in depth: even an allowed prefix (TERMUX_, PROOT_, ...) never passes a
# variable whose name looks like a credential.
_SECRET_NAME_RE = re.compile(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL|AUTH|DATABASE|_URL$", re.IGNORECASE)
SANDBOX_CPU_SECONDS = 60
SANDBOX_MAX_FILE_BYTES = 50 * 1024 * 1024


def _sandbox_env(tmpdir: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if (k in _SANDBOX_ENV_KEEP or k.startswith(_SANDBOX_ENV_KEEP_PREFIXES))
           and not _SECRET_NAME_RE.search(k)}
    home = os.path.join(tmpdir, "_home")
    os.makedirs(home, exist_ok=True)
    env.update(HOME=home, TMPDIR=tmpdir, PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    return env


def _sandbox_limits():
    """preexec_fn for the sandboxed child: CPU-time and file-size ceilings.
    (No memory or process-count limit: proot's ptrace tracing and Android's
    per-uid process accounting make those unsafe to set here.)"""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (SANDBOX_CPU_SECONDS, SANDBOX_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (SANDBOX_MAX_FILE_BYTES, SANDBOX_MAX_FILE_BYTES))


def _run_limited(cmd, cwd, env, timeout):
    """Runs cmd in its own session/process group so a timeout kills every
    descendant, not just the direct child. Returns (returncode, output, timed_out)."""
    import signal
    import subprocess
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True, preexec_fn=_sandbox_limits)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out or "", False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
        return proc.returncode, out or "", True


def _run_sandboxed_test_inner(module_basename: str, patched_content: str, test_code: str, timeout: int = 20):
    """Test-driven auto-enhance gate: apply a proposed diff to a TEMP COPY of the
    target (the real file is never touched here) plus the proposed test function,
    and execute the test in a SEPARATE SUBPROCESS with its own tempdir as cwd, so
    a relative-path write from the test lands in the tempdir, not the real repo,
    and a hang is bounded by `timeout` rather than freezing the REPL.

    Two containment layers, in order:
    1. _static_ast_check() rejects obviously-unsafe test code before anything
       runs at all (no subprocess/socket/ctypes, no eval/exec/os.system, no
       absolute-path literal handed to a known write call).
    2. Real OS-level path virtualization via `proot`: a throwaway decoy
       directory is bind-mounted OVER the real home-directory prefix
       (SANDBOX_PROTECTED_PREFIX) for the duration of the subprocess, so an
       absolute-path write the static check didn't catch (e.g. a path built
       via string concatenation, or os.path.expanduser("~")) lands in the
       decoy, not the real repo/checkpoints/secrets. This is the actual fix
       for the previously-confirmed gap: an absolute-path write used to reach
       the real filesystem unchanged; it no longer does for anything under
       the home prefix. Paths entirely outside that prefix (e.g. /etc) are
       not remapped by this measure -- combined with the static check above,
       this is real, verified defense in depth, not a claim of a full
       container/seccomp sandbox.

    Returns (passed: bool, output: str)."""
    static_reason = _static_ast_check(test_code)
    if static_reason:
        return False, f"static safety check rejected proposal: {static_reason}"
    # Placeholder gate: a stub module plus an assert-free test used to pass
    # here, since the only question asked was "does the model's own test pass".
    payload_reason = payload_gate.check_payload(patched_content)
    if payload_reason:
        return False, f"placeholder gate rejected proposal: {payload_reason}"
    test_reason = payload_gate.check_test(test_code)
    if test_reason:
        return False, f"placeholder gate rejected test: {test_reason}"

    import subprocess
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="osiris_sandbox_")
    decoy_home = os.path.join(tmpdir, "_decoy_home")
    os.makedirs(decoy_home, exist_ok=True)
    try:
        with open(os.path.join(tmpdir, module_basename), "w", encoding="utf-8") as f:
            f.write(patched_content)
        with open(os.path.join(tmpdir, "test_proposal.py"), "w", encoding="utf-8") as f:
            f.write(test_code)
        runner = os.path.join(tmpdir, "_sandbox_runner.py")
        with open(runner, "w", encoding="utf-8") as f:
            f.write(
                "import sys, traceback\n"
                "try:\n"
                "    from test_proposal import test_proposal\n"
                "except Exception:\n"
                "    traceback.print_exc()\n"
                "    print('SANDBOX_IMPORT_ERROR')\n"
                "    sys.exit(2)\n"
                "try:\n"
                "    test_proposal()\n"
                "except Exception:\n"
                "    traceback.print_exc()\n"
                "    print('SANDBOX_TEST_FAIL')\n"
                "    sys.exit(1)\n"
                "print('SANDBOX_TEST_PASS')\n"
                "sys.exit(0)\n"
            )
        cmd = [
            PROOT_BIN, "-b", f"{decoy_home}:{SANDBOX_PROTECTED_PREFIX}",
            sys.executable, "_sandbox_runner.py",
        ]
        returncode, output, timed_out = _run_limited(cmd, tmpdir, _sandbox_env(tmpdir), timeout)
        if timed_out:
            return False, f"sandbox test timed out after {timeout}s (process group killed)"
        passed = returncode == 0 and "SANDBOX_TEST_PASS" in output
        return passed, output.strip()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _auto_enhance_verify(write_path: str, module_basename: str, content: str, test_code: str,
                          command: str, prompt: str, attempt: int = 1):
    """Runs the sandbox gate on a proposed (content, test_code) pair. On pass,
    tags [PROVENANCE: VERIFIED_LOGIC] and hands off to the normal _propose_write
    diff/`/apply` gate -- this ADDS a verification stage before the human sees a
    proposal, it does not remove the existing human confirmation gate. On fail,
    allows exactly ONE self-correction round-trip to Engine 2 (attempt 2), then
    discards quietly with a telemetry record rather than showing a broken diff."""
    passed, output = _run_sandboxed_test(module_basename, content, test_code)
    if passed:
        print(f"[*] /auto-enhance: sandbox test PASSED (attempt {attempt}).")
        _organism_telemetry(
            f"AUTO_ENHANCE_VERIFIED path={write_path} attempt={attempt} [PROVENANCE: VERIFIED_LOGIC]"
        )
        allow_self_modify = SELF_MODIFY_OVERRIDE in command
        _propose_write(write_path, content, allow_self_modify)
        return

    print(f"[!] /auto-enhance: sandbox test FAILED (attempt {attempt}).")
    if attempt >= 2:
        print("[!] /auto-enhance: second attempt also failed; discarding proposal without "
              "showing it (nothing was ever written).\n")
        reason = output[:200].replace("\n", " ")
        _organism_telemetry(
            f"AUTO_ENHANCE_DISCARD path={write_path} attempts=2 reason={reason} [PROVENANCE: COMPUTED]"
        )
        return

    correction_prompt = f"""{prompt}

Your previous proposal's test FAILED when actually run in a sandbox. Real output:
{output[:3000]}

Fix the WRITE_FILE content and/or the TEST_FUNCTION so the test genuinely passes. Output
the same two blocks, corrected, and nothing else."""
    raw_code = _synthesize(correction_prompt)
    write_match = WRITE_FILE_RE.search(raw_code)
    test_match = TEST_FUNCTION_RE.search(raw_code)
    if not write_match or not test_match:
        print("[!] /auto-enhance: correction attempt did not return valid blocks; discarding.\n")
        _organism_telemetry(
            f"AUTO_ENHANCE_DISCARD path={write_path} attempts=2 reason=malformed_correction "
            f"[PROVENANCE: COMPUTED]"
        )
        return
    new_path, new_content = write_match.group(1).strip(), write_match.group(2)
    new_test = test_match.group(1)
    _auto_enhance_verify(new_path, os.path.basename(new_path), new_content, new_test,
                          command, prompt, attempt=2)


def _auto_enhance_candidates(root):
    protected = _protected_script_paths()
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in AUTO_ENHANCE_EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".py") or fn in AUTO_ENHANCE_EXCLUDE_NAMES:
                continue
            full = os.path.join(dirpath, fn)
            if os.path.realpath(full) in protected:
                continue
            candidates.append(full)
    return candidates


def _auto_enhance(command: str):
    """'/auto-enhance' -- pick a random real .py file under cwd, ask Engine 2
    (deepseek-coder) for a narrow, reviewable improvement, and route the result
    through the exact same _propose_write() gate a normal modify-intent write
    uses. Nothing is written until the user explicitly types /apply."""
    root = os.path.realpath(os.getcwd())
    candidates = _auto_enhance_candidates(root)
    if not candidates:
        print(f"\n[!] /auto-enhance: no eligible .py files found under {root} "
              f"(excluding {sorted(AUTO_ENHANCE_EXCLUDE_DIRS)} and "
              f"{sorted(AUTO_ENHANCE_EXCLUDE_NAMES)}).\n")
        return

    target = random.choice(candidates)
    rel_path = os.path.relpath(target, root)
    try:
        with open(target, encoding="utf-8", errors="replace") as f:
            original = f.read()
    except Exception as e:
        print(f"\n[!] /auto-enhance: could not read {target}: {e}\n")
        return

    print(f"\n[*] /auto-enhance: reviewing {rel_path} ...")
    # 6000 chars was sized for local deepseek-coder's practical working context on
    # this hardware. Cloud backends have far larger documented context windows, so
    # when one is active a real file can go in closer to whole -- still bounded
    # (60000 chars, not "unlimited") so an absurdly large file still gets capped.
    content_limit = 60000 if gemini_bridge.is_configured() else 6000
    module_basename = os.path.basename(rel_path)
    module_name = os.path.splitext(module_basename)[0]
    prompt = f"""You are OSIRIS Sovereign Synthesizer performing a narrow code review.
Review the following file for: error-handling robustness, missing/incorrect type hints,
and structural-decoding opportunities (places where a rigid expected format is currently
parsed/generated loosely and could be enforced more strictly).
Propose ONE improved version of this SAME file, AND a discrete test that proves the
change actually works. Output EXACTLY these two blocks and nothing else:
<WRITE_FILE path="{rel_path}">
...the complete improved file content...
</WRITE_FILE>
<TEST_FUNCTION>
import {module_name}
def test_proposal():
    ...assert statements that exercise the specific change you made...
</TEST_FUNCTION>
Rule 1: DO NOT write conversational filler, explanations, or warnings outside the tags.
Rule 2: Preserve the file's existing public behavior -- this is a narrow review, not a rewrite.
Rule 3: If the file is already solid on these three axes, propose it unchanged rather than
inventing busywork, but still include a TEST_FUNCTION that exercises real behavior.
Rule 4: The test function must be named exactly test_proposal, take no arguments, use plain
assert statements (no pytest/unittest required), and include any imports it needs (e.g.
"import {module_name}") at the top of the block -- it will run standalone in its own
directory alongside a file named {module_basename}.

FILE: {rel_path}
CONTENT:
{original[:content_limit]}
"""
    raw_code = _synthesize(prompt)
    write_match = WRITE_FILE_RE.search(raw_code)
    test_match = TEST_FUNCTION_RE.search(raw_code)
    if not write_match or not test_match:
        print("[!] /auto-enhance: model did not return both WRITE_FILE and TEST_FUNCTION "
              "blocks; nothing proposed.\n")
        return
    write_path, content = write_match.group(1).strip(), write_match.group(2)
    test_code = test_match.group(1)
    _auto_enhance_verify(write_path, os.path.basename(write_path), content, test_code,
                          command, prompt, attempt=1)


def _research(command: str):
    """'/research <topic>' -- fetch up to 3 real recent ArXiv abstracts on
    <topic> via ArxivWatcher and feed each into Engine 3's background
    conversational learning loop (same checkpoint as ordinary REPL chat --
    prose abstracts are close enough in character to conversation that this
    doesn't need the hard checkpoint split DD-sequence work required).

    Provenance is kept as two separate, correctly-tagged facts, not one:
    ArxivWatcher.scan() already logs the fetch itself to research.log as
    [PROVENANCE: EXTERNAL_API]. The resulting gradient-descent loss values
    stay [PROVENANCE: COMPUTED] in nclm_loss.log exactly as every other
    Engine 3 step already is -- a real computed loss is still a real
    computed loss no matter what text produced it; relabeling it
    EXTERNAL_API just because the INPUT came from outside would mislabel
    the number itself, not its source."""
    topic = command[len("/research"):].strip()
    if not topic:
        print("\n[!] /research needs a topic, e.g. /research dynamical decoupling\n")
        return

    watcher_path = os.path.join(ORGANISM_SRC, "copilot-sdk-dnalang", "src",
                                 "dnalang_sdk", "nclm", "arxiv_watcher.py")
    if not os.path.exists(watcher_path):
        print(f"\n[!] /research: arxiv_watcher.py not found at {watcher_path}\n")
        return

    # Loaded directly by path, bypassing dnalang_sdk/__init__.py -- that
    # package currently has an unrelated real syntax error in code_writer.py
    # (duplicate argument 'new_text') that breaks the normal package import
    # chain. Fixing that file is out of scope here; this sidesteps it
    # without touching it.
    import importlib.machinery
    import importlib.util
    try:
        loader = importlib.machinery.SourceFileLoader("_osiris_arxiv_watcher", watcher_path)
        spec = importlib.util.spec_from_loader("_osiris_arxiv_watcher", loader)
        watcher_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(watcher_mod)
    except Exception as e:
        print(f"\n[!] /research: could not load arxiv_watcher.py: {e}\n")
        return

    print(f"\n[*] /research: querying ArXiv for '{topic}' ...")
    try:
        papers = watcher_mod.ArxivWatcher().scan(topic, max_results=3)
    except Exception as e:
        print(f"[!] /research: ArXiv query failed: {e}\n")
        return

    if not papers:
        print("[!] /research: no results (or a network error -- see "
              "~/.osiris/telemetry/research.log for the [PROVENANCE: EXTERNAL_API] "
              "failure record ArxivWatcher already wrote).\n")
        return

    print(f"[*] /research: fetched {len(papers)} paper(s), feeding each to the "
          f"organism's background learning loop:")
    for p in papers:
        arxiv_id = p["id"].rsplit("/", 1)[-1] or p["id"]
        print(f"  - [{arxiv_id}] {p['title']}")
        _spawn_organism_learn(f"{p['title']}\n\n{p['summary']}")
    print(f"[*] Queued for background learning -- real [PROVENANCE: COMPUTED] loss "
          f"values land in ~/.osiris/telemetry/nclm_loss.log (or /organism status) "
          f"as each step completes; the fetch itself is already logged "
          f"[PROVENANCE: EXTERNAL_API] in ~/.osiris/telemetry/research.log.\n")


def sanitize_input(text: str) -> str:
    """Removes ANSI escape codes and terminal prompt artifacts."""
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    clean = ansi_escape.sub('', text)
    clean = re.sub(r'osiris>\s*', '', clean)
    clean = clean.replace('', '')
    return clean.strip()

def query_model(prompt: str, model: str, stream: bool = True, timeout: int = 420,
                fmt: dict = None) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_predict": 1536}
    }
    if fmt:
        payload["format"] = fmt  # Ollama constrains decoding to this JSON schema
    
    req = urllib.request.Request(
        OLLAMA_GEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    full_text = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if stream:
                # Held for the whole streamed response, not per-token -- a per-
                # token acquire/release would still let Engine 3's background
                # thread slip a print() in between two of our tokens. This is
                # the other half of the fix paired with _stdout_lock's uses in
                # _organism_learn(); holding it for the whole block is what
                # actually prevents interleaving, not just reduces it.
                with _stdout_lock:
                    for line in resp:
                        if line:
                            chunk = json.loads(line.decode("utf-8", errors="ignore"))
                            token = chunk.get("response", "")
                            sys.stdout.write(token)
                            sys.stdout.flush()
                            full_text.append(token)
                            if chunk.get("done", False):
                                break
                    print()
            else:
                body = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return body.get("response", "")
    except Exception as e:
        with _stdout_lock:
            installed = _detect_installed_ollama_models(timeout=1.0)
            if installed and model not in installed:
                fallback_model = installed[0]
                print(f"\n[!] Model '{model}' not found in Ollama (HTTP 404). Switching to installed model '{fallback_model}'...")
                return query_model(prompt, fallback_model, stream=stream, timeout=timeout, fmt=fmt)
            print(f"\n[!] Ollama connection error with {model}: {e}")
            if stream: print()
            
    return "".join(full_text)

_last_backend = {"name": None, "model": None}


def _synthesize(prompt: str, system_prompt: str = "", structured: bool = False,
                only: str = None, ollama_model: str = None) -> str:
    """Engine 2 hot-swap chain: Gemini cloud-burst -> local
    Ollama/deepseek-coder (the AI Gateway tier was removed 2026-09-24). The
    cloud tier is skipped/falls through on any
    failure (missing key, network, billing/auth). Only this function's
    callers (auto-enhance and Stage 2 synthesis) are affected -- Engine 1
    (intent routing) and Engine 3 (the NCLM organism) never go through here.

    structured=True constrains Gemini and Ollama to the proposal JSON schema
    (structured_proposal.py). _last_backend records which tier
    answered, for the benchmark and telemetry.

    only="gemini"|"ollama" uses that tier alone with no fallback ("gateway" answers "" -- removed)
    (a failure returns "" and is recorded in _last_backend["error"]) -- the
    benchmark uses this to measure one backend at a time. ollama_model
    overrides CODE_MODEL for the local tier."""
    _last_backend.update(name=None, error=None, model=None)
    if only is not None:
        return _synthesize_only(only, prompt, system_prompt, structured, ollama_model)
    # The AI Gateway tier was removed on the operator's request (2026-09-24):
    # it answered every call with HTTP 403 and wasted one request per candidate.
    if gemini_bridge.is_configured():
        try:
            text = gemini_bridge.query(
                system_prompt, prompt,
                response_schema=structured_proposal.GEMINI_PROPOSAL_SCHEMA if structured else None)
            _last_backend.update(name="gemini", model=gemini_bridge.model_name())
            print("[Engine 2: Gemini cloud-burst]")
            _organism_telemetry(
                f"OK backend=gemini_cloud chars={len(text)} [PROVENANCE: GEMINI_CLOUD]"
            )
            return text
        except gemini_bridge.GeminiUnavailable as e:
            print(f"[Engine 2: Gemini unavailable ({e}), falling back to local deepseek-coder]")
    else:
        print("[Engine 2: local deepseek-coder]")
    _last_backend.update(name="ollama", model=ollama_model or CODE_MODEL)
    return query_model(prompt, ollama_model or CODE_MODEL, stream=False,
                       fmt=structured_proposal.PROPOSAL_SCHEMA if structured else None)


def _synthesize_only(backend: str, prompt: str, system_prompt: str, structured: bool,
                     ollama_model: str = None) -> str:
    _last_backend.update(name=backend, model={"gemini": gemini_bridge.model_name(),
                                              "ollama": ollama_model or CODE_MODEL}.get(backend))
    if backend == "gateway":
        _last_backend["error"] = "the AI Gateway is removed from OSIRIS"
        return ""
    try:
        if backend == "gemini":
            return gemini_bridge.query(
                system_prompt, prompt,
                response_schema=structured_proposal.GEMINI_PROPOSAL_SCHEMA if structured else None)
        if backend == "ollama":
            full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return query_model(full, ollama_model or CODE_MODEL, stream=False,
                               fmt=structured_proposal.PROPOSAL_SCHEMA if structured else None)
    except gemini_bridge.GeminiUnavailable as e:
        _last_backend["error"] = str(e)
        return ""
    raise ValueError(f"unknown backend {backend!r} (expected gemini or ollama)")


def extract_code(raw: str) -> str:
    """Extracts code, explicitly rejecting LLM refusal templates."""
    refusal_flags = ["I'm sorry", "I cannot fulfill", "As an AI", "I can't assist"]
    if any(flag in raw for flag in refusal_flags):
        print("\n[!] Engine Refusal Detected. Bypassing AST.")
        return ""

    matches = re.findall(r"```(?:python)?\s*(.*?)\s*```", raw, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()
    
    # Strict fallback: only return if it actually looks like Python
    lines = [l for l in raw.strip().splitlines() if not l.strip().startswith("```")]
    code = "\n".join(lines).strip()
    if "def " in code or "class " in code or "import " in code:
        return code
    return ""

# First words that submit on <Enter> with no EOF line. Matched on the first
# word only, so a pasted log that happens to begin with a path such as
# /data/... is still collected as multi-line input.
IMMEDIATE_COMMANDS = {
    "/apply", "/why", "/status", "/home", "/tap", "/check", "/run", "/runs", "/gap", "/ignite", "/metamorphosis", "/sprint", "/organism", "/ledger",
    "/dd", "/auto-enhance", "/research", "/intent", "/consensus", "/suggest", "/vision",
    "/engage", "/ui", "/help", "/mentors", "/bench", "/gaps", "/ask", "/plan", "/experiment",
    "/experiments", "/facts", "/cancel", "/reroute", "/focus", "/digest", "/lab", "/import", "/sources",
    "/source", "/map", "/hypothesis", "/hypotheses", "/outcome", "/trial", "/evolve", "/capabilities", "/discover",
    "exit", "quit",
}


# Read-only: run while a write is pending without asking to discard it --
# /status even has a "Pending write" row for exactly that moment.
READ_ONLY_COMMANDS = {"/status", "/why", "/home", "/runs", "/runs stats", "/help", "/ui", "/mentors", "/digest",
                      "/lab", "/sources", "/map", "/hypotheses",
                      "/ui rich", "/ui plain", "/ui access", "/intent", "/intent status",
                      "/organism", "/organism status"}

# OSIRIS_INTENT_CARD=0 sends free-form input straight to the models, as before.
INTENT_CARD = os.environ.get("OSIRIS_INTENT_CARD", "1") != "0"


def _is_menu_letter(text: str) -> bool:
    """A menu letter, either case. Letters are only ever registered keys."""
    return bool(re.fullmatch(r"[A-Za-z]", text))


def _is_freeform(text: str) -> bool:
    """Input headed for the models: not a one-line command, number, letter, exit
    or anything /apply-like (those keep their own handling)."""
    t = text.strip()
    return bool(t) and not (t.startswith("/") and "\n" not in t) and not t.isdigit() and \
        not _is_menu_letter(t) and t.lower() not in ("exit", "quit") and \
        not _is_apply(t) and not _looks_like_apply(t)


def _is_read_only(text: str) -> bool:
    """READ_ONLY_COMMANDS, plus "/run show ..." with any arguments. /bench also
    keeps a pending write: it writes only the bench ledger, never the workspace."""
    t = text.strip().lower()
    return t in READ_ONLY_COMMANDS or t.split()[:2] == ["/run", "show"] or \
        t.split()[:1] in (["/bench"], ["/gap"], ["/gaps"], ["/ask"], ["/plan"], ["/experiment"], ["/experiments"],
                          ["/facts"], ["/cancel"], ["/reroute"], ["/focus"])  # none writes the workspace: bench ledger, drafts, briefs, answers


def _is_unknown_command(text: str) -> bool:
    """One line whose first word starts with '/' but is no command. Such input
    used to reach run_synergy_pipeline: on 2026-09-24 "/status/status" (an
    unterminated pasted line plus a typed one) became a model prompt, which
    invented Status/StatusLogger classes and wrote osiris_organism_*.py.
    Multi-line text starting with '/' (a pasted log) still goes to the model."""
    stripped = text.strip()
    if not stripped.startswith("/") or "\n" in stripped:
        return False
    return stripped.split()[0].lower() not in IMMEDIATE_COMMANDS


def _unknown_command(text: str):
    first = text.strip().split()[0].lower()
    head = "/" + first.lstrip("/").split("/")[0]
    close = difflib.get_close_matches(head, sorted(c for c in IMMEDIATE_COMMANDS if c.startswith("/")),
                                      n=3, cutoff=0.6)
    hint = f" Did you mean {' or '.join(close)}?" if close else ""
    print(f"\n[!] Unknown command: {text.strip()[:80]!r} -- not sent to the model.{hint}\n"
          f"    (Text starting with '/' reaches the model only as multi-line input ending in EOF.)\n")


def _submits_immediately(first_line: str) -> bool:
    stripped = first_line.strip()
    if not stripped:
        return False
    word = stripped.split()[0].lower()
    # A bare /word (a mistyped command such as /statsu) also submits, and is
    # then rejected as unknown; it used to wait for EOF and merge with the
    # next lines into a model prompt. Paths (/data/x.log) have '/' or '.'.
    return bool(word in IMMEDIATE_COMMANDS or re.fullmatch(r"/[a-z][a-z-]*", word) or stripped.isdigit()
                or _is_menu_letter(stripped) or _is_apply(stripped)
            or (stripped in _pending_suggestions))


PASTE_GAP = 0.35  # seconds: a pasted block's lines arrive faster than this; typing does not


def _more_input_waiting(timeout: float = PASTE_GAP) -> bool:
    """On a terminal, whether more input arrives within `timeout` -- i.e. the
    line just read is part of a paste. A canonical-mode terminal hands over
    one line per read, so the rest of a paste is still queued on stdin.
    Not a terminal (tests, pipes): False is never assumed -- see caller."""
    import select
    try:
        return bool(select.select([sys.stdin], [], [], timeout)[0])
    except (OSError, ValueError, TypeError):
        return False


def collect_multiline_input() -> str:
    """Known commands (IMMEDIATE_COMMANDS, bare 'apply', a pending suggestion
    number) submit on <Enter>. On a terminal, anything else submits when
    input pauses: a typed line on Enter, a pasted block once the paste ends
    -- no EOF line needed (2026-09-24: typing 'EOF' after every message on a
    phone). From a pipe, text is still collected until a line containing
    only EOF, as before. A typed EOF line still works and is not kept."""
    buffer = []
    tty = getattr(sys.stdin, "isatty", lambda: False)()
    while True:
        try:
            if not buffer:
                unit, pasted = _read_unit()
                _last_input["pasted"] = pasted
                if pasted:
                    return sanitize_input(unit)  # a bracketed paste is one message, whole
                line = unit
            else:
                line = sys.stdin.readline()
            if not line:
                if not buffer:
                    raise EOFError("stdin closed")
                break
            if line.strip() == "EOF":
                break
            buffer.append(line)
            if len(buffer) == 1 and _submits_immediately(line):
                break
            if tty and "".join(buffer).strip() and not _more_input_waiting():
                break
        except (KeyboardInterrupt, EOFError):
            raise
    return sanitize_input("".join(buffer))

def run_synergy_pipeline(raw_text: str):
    timestamp = int(time.time())
    organism_file = f"osiris_organism_{timestamp}.py"

    print("\n" + "─" * 65)
    print(f" 🧠 MODEL 1 [{CHAT_MODEL}]: INTENT DEDUCTION & ARCHITECTURE")
    print("─" * 65)

    repo_context_block = ""
    if CODEBASE_INTENT_RE.search(raw_text):
        cwd = os.getcwd()
        context_json = build_context(cwd)
        file_count = json.loads(context_json).get("file_count", 0)
        if file_count:
            print(f"[*] FS_SCAN: found {file_count} Python file(s) under {cwd} -> injecting real AST context.")
            repo_context_block = f"""
REAL REPOSITORY CONTEXT (ground truth -- extracted via AST from {cwd}, do not invent classes/functions outside this list):
{context_json}
"""
        else:
            print(f"[*] FS_SCAN: no Python files found under {cwd}. Not fabricating an architecture.")
            repo_context_block = f"""
REAL REPOSITORY CONTEXT: no Python source files were found under {cwd}.
Do NOT invent a generic architecture. State plainly that no codebase was detected in this directory
and suggest the user re-run osiris from inside the actual project directory.
"""

    _log_prompt_library(raw_text, bool(MODIFY_INTENT_RE.search(raw_text)), bool(CODEBASE_INTENT_RE.search(raw_text)))

    architect_prompt = f"""You are OSIRIS Systems Architect.
Extract the core engineering parameters from the following text and write a STRICT technical specification for a Python developer.
DO NOT write example code. DO NOT include conversational filler. List the classes, methods, and exact math required.
Base your specification ONLY on the REAL REPOSITORY CONTEXT below when one is provided -- never invent classes,
methods, or files that are not present in it.
{repo_context_block}
INPUT LOG:
{raw_text[:7500]}
"""
    enhanced_spec = query_model(architect_prompt, CHAT_MODEL, stream=True)
    if not enhanced_spec.strip():
        print("[*] Stage 1 output empty or Ollama model unavailable. Routing to Sovereign NCLM Transformer...")
        _spawn_organism_learn(raw_text)
        return False

    print("\n" + "─" * 65)
    print(f" 🦠 MODEL 2 [{CODE_MODEL}]: PRODUCTION CODE SYNTHESIS")
    print("─" * 65)
    print(f"[*] Dispatching specification -> {organism_file}...")

    modify_intent = MODIFY_INTENT_RE.search(raw_text)
    allow_self_modify = SELF_MODIFY_OVERRIDE in raw_text

    if modify_intent:
        coder_prompt = f"""You are OSIRIS Sovereign Synthesizer. Based strictly on this specification, propose ONE
file to write or modify on disk. Output EXACTLY one block in this exact format and nothing else:
<WRITE_FILE path="relative/path/to/file.py">
...the complete new file content...
</WRITE_FILE>
Rule 1: DO NOT write conversational filler, explanations, or warnings outside the tag.
Rule 2: path must be a relative path (no leading /, no ..).
Rule 3: Ensure strict typing and imports are present in the content.

SPECIFICATION:
{enhanced_spec}
"""
    else:
        coder_prompt = f"""You are OSIRIS Sovereign Synthesizer. Write complete, runnable Python code based strictly on this specification.
Rule 1: DO NOT write conversational filler, explanations, or warnings.
Rule 2: Enclose code in a single markdown Python fence.
Rule 3: Ensure strict typing and imports are present.

SPECIFICATION:
{enhanced_spec}
"""
    raw_code = _synthesize(coder_prompt)

    if modify_intent:
        write_match = WRITE_FILE_RE.search(raw_code)
        if write_match:
            target_path, content = write_match.group(1).strip(), write_match.group(2)
            if target_path.endswith(".py"):
                payload_reason = payload_gate.check_payload(content)
                if payload_reason:
                    _record_intent_feedback("modify", 0.0)
                    print(f"[!] WRITE_FILE rejected by placeholder gate: {payload_reason}\n")
                    _spawn_organism_learn(raw_text + "\n" + enhanced_spec)
                    return
            _record_intent_feedback("modify", 1.0)
            _propose_write(target_path, content, allow_self_modify)
            _spawn_organism_learn(raw_text + "\n" + enhanced_spec + "\n" + raw_code)
            return
        _record_intent_feedback("modify", 0.0)
        print("[!] Modify-intent detected but no WRITE_FILE block found; falling back to plain synthesis.\n")

    code = extract_code(raw_code)

    if not code:
        _record_intent_feedback("synthesis", 0.0)
        print("[!] Synthesis failed or model refused the prompt.\n")
        _spawn_organism_learn(raw_text + "\n" + enhanced_spec)
        return

    try:
        tree = ast.parse(code, filename=organism_file)
        compile(tree, organism_file, 'exec')
        # AST-clean only proves it parses; refuse to stamp stub code as locked.
        payload_reason = payload_gate.check_payload(code)
        if payload_reason:
            _record_intent_feedback("synthesis", 0.1)
            print(f"[!] Placeholder gate: {payload_reason} -- nothing written.\n")
            _spawn_organism_learn(raw_text + "\n" + enhanced_spec)
            return

        # Proposed, not written: this path used to save the file at once with
        # no /apply (2026-09-24: "hello osiris" -> an invented OSIRISSystems
        # class in osiris_organism_*.py), plus a sprint_backlog_*.json that
        # nothing read. Now it is a pending write like every other one.
        _record_intent_feedback("synthesis", 1.0)
        print(f"[*] Candidate parses and passes the placeholder gate -- proposed, not written.")
        _propose_write(organism_file, code, allow_self_modify)
        _spawn_organism_learn(raw_text + "\n" + enhanced_spec + "\n" + code)

    except SyntaxError as se:
        _record_intent_feedback("synthesis", 0.3)
        print(f"[!] AST Syntax Fracture at line {se.lineno}: {se.msg}")
        print(f"[!] Offending line: {se.text}\n")
        _spawn_organism_learn(raw_text + "\n" + enhanced_spec)
    except Exception as e:
        _record_intent_feedback("synthesis", 0.0)
        print(f"[!] Compilation / File Error: {e}\n")
        _spawn_organism_learn(raw_text + "\n" + enhanced_spec)

def _council_engines(ollama_ok: bool):
    """The startup council card's rows, each state read from a real check."""
    local = ("verified", "ollama reachable") if ollama_ok else ("review", "ollama UNREACHABLE")
    clouds = ["gemini"] if gemini_bridge.is_configured() else []
    try:
        with open(os.path.join(ORGANISM_HOME, "organism.json"), encoding="utf-8") as f:
            nclm = ("memory", f"checkpoint at step {json.load(f)['step']}")
    except (OSError, ValueError, KeyError):
        nclm = ("idle", "no checkpoint yet")
    synth = ("verified" if clouds or ollama_ok else "review",
             " · ".join(clouds + [local[1]]) if clouds else local[1])
    return [(local[0], "Architect", f"{CHAT_MODEL} · intent → spec", local[1]),
            (synth[0], "Synthesizer", f"{_synth_chain()} · spec → code", synth[1]),
            (nclm[0], "NCLM", "osiris.nclm · learns from every exchange", nclm[1]),
            ("current", "Verifier", "sandbox · placeholder gate · genome ledger", "deterministic, no model")]


def run_command(user_input: str) -> bool:
    """Runs one console command and returns True, or returns False when the
    input is not one. The one router for both front ends: main() below and
    the `osiris` REPL (osiris_cli/osiris_repl.py), whose own copy of this
    table drifted (2026-10-02: F crashed calling _mentors(line) and J opened
    the brief with "/experiment" as its question)."""
    if user_input.strip().lower() in ("/organism", "/organism status"):
        _organism_status()
        return True
    if user_input.strip().lower() == "/organism alerts":
        _organism_alerts()
        return True
    if user_input.strip().lower().startswith("/ledger verify"):
        _ledger_verify(user_input.strip())
        return True
    if user_input.strip().lower().startswith("/dd search"):
        _dd_search(user_input.strip())
        return True
    if user_input.strip().lower().startswith("/dd pretrain"):
        _dd_pretrain(user_input.strip())
        return True
    if user_input.strip().lower().startswith("/dd programmatic"):
        _dd_programmatic(user_input.strip())
        return True
    if user_input.strip().lower().startswith("/auto-enhance"):
        _auto_enhance(user_input.strip())
        return True
    if user_input.strip().lower().startswith("/research"):
        _research(user_input.strip())
        return True
    if user_input.strip().lower() in ("/intent", "/intent status"):
        _intent_status()
        return True
    if user_input.strip().lower() == "/consensus":
        _consensus()
        return True
    first = user_input.strip().split()[0].lower() if user_input.strip() else ""
    if first == "/ask":
        _answer(user_input.strip()[4:].strip() or "What can you do?")
        return True
    if first == "/plan":
        _plan(user_input.strip()[5:])
        return True
    if first == "/experiment":
        _experiment(user_input.strip()[len("/experiment"):])
        return True
    if first == "/experiments":
        _experiments()
        return True
    if first == "/reroute":
        _reroute(user_input.strip())
        return True
    if first == "/focus":
        _focus(user_input.strip())
        return True
    if first == "/cancel":
        print("[*] Cancelled.")
        _home()
        return True
    if first == "/facts":
        _facts()
        return True
    if user_input.strip().lower().split()[:1] == ["/gaps"]:
        _gaps(user_input.strip())
        return True
    if user_input.strip().lower().split()[:1] == ["/gap"]:
        _gap(user_input.strip()[4:])
        return True
    if user_input.strip().lower() == "/status":
        _status()
        return True
    if user_input.strip().lower().split()[:2] == ["/run", "show"]:
        _run_show(user_input.strip())
        return True
    if user_input.strip().lower() in ("/runs", "/runs stats"):
        _runs_stats()
        return True
    if user_input.strip().lower() == "/check":
        _check()
        return True
    if user_input.strip().lower() in ("/home", "/home stories"):
        _home(user_input.strip())
        return True
    if user_input.strip().lower() == "/why":
        _why()
        return True
    if user_input.strip().lower() == "/engage":
        _engage()
        return True
    if user_input.strip().lower().split()[:1] == ["/ui"]:
        _ui(user_input.strip())
        return True
    if user_input.strip().lower().split()[:1] == ["/bench"]:
        _bench(user_input.strip())
        return True
    if user_input.strip().lower() == "/mentors":
        _mentors()
        return True
    if user_input.strip().lower() == "/digest":
        _digest()
        return True
    _word = user_input.strip().split()[0].lower() if user_input.strip() else ""
    if _word in LAB_COMMANDS:
        LAB_COMMANDS[_word](user_input.strip())
        return True
    if user_input.strip().lower() == "/help":
        _help()
        return True
    if user_input.strip().lower() == "/suggest":
        _suggest()
        return True
    if user_input.strip().lower() == "/vision latest":
        _vision_latest()
        return True
    if user_input.strip().lower() == "/vision sync-sprint":
        _vision_sync_sprint()
        return True
    if user_input.strip().lower().startswith("/sprint plan"):
        _sprint_plan(user_input.strip())
        return True
    # Word match, not ==: "/sprint execute --k 1" and "--allow-self-modify"
    # used to fall through to run_synergy_pipeline as a chat prompt.
    if user_input.strip().lower().split()[:2] == ["/sprint", "execute"]:
        _sprint_execute(user_input.strip())
        return True
    if user_input.strip().lower() == "/sprint review":
        _sprint_review()
        return True
    if user_input.strip().lower() in ("/ignite", "/metamorphosis"):
        _ignite(user_input.strip())
        return True
    return False


def main():
    _terminal_setup(True)
    import atexit
    atexit.register(_terminal_setup, False)
    ok, base = _check_ollama_reachable()
    print(osiris_ui.council(osiris_ui.Canvas(), _council_engines(ok)))
    try:
        d = session_state.digest(_state_counts())
        if d and d["changes"]:
            ui = osiris_ui.Canvas()
            print(ui.panel(f"SINCE LAST SESSION ({d['since']})", [f"{ui.marker('iterate')} {c}" for c in d["changes"]]))
    except Exception as e:
        print(f"[!] Session digest unavailable: {type(e).__name__}: {e}")
    print(" Talk to OSIRIS in plain words, or use a menu key. Enter sends; a paste is sent whole.\n")
    if not ok:
        print(f"[!] Ollama not reachable at {base} -- start it with 'ollama serve' before using "
              f"osiris. Continuing anyway; commands will fail until it's up.\n")
    try:
        _home()
    except Exception as e:
        print(f"[!] /home unavailable: {type(e).__name__}: {e}\n")
    if os.environ.get("OSIRIS_TAP") == "1":
        _tap_state["again"] = True  # the loop's first turn opens /home as a sheet

    while True:
        try:
            if _tap_state["again"] and not _tap_state["queue"]:
                _tap_state["again"] = False
                print("─" * 45 + "  (tap an item, or cancel to type)")
                picked = _tap(redraw=False)
                if picked:
                    _tap_state["queue"].append(picked)
            print("osiris::}{> ", end="", flush=True)
            if _tap_state["queue"]:
                user_input = _tap_state["queue"].pop(0)
                print(f"{user_input}  (tapped)")
                _tap_state["again"] = True
            else:
                user_input = collect_multiline_input()
            if not user_input: continue
            if user_input.strip().lower() == "/tap":
                picked = _tap()
                if picked:
                    _tap_state["queue"].append(picked)
                continue
            if user_input.lower() in ("exit", "quit"):
                print("\n[*] Engine hibernating. Goodbye.")
                break
            if _pending_suggestions:
                stripped = user_input.strip()
                if _is_menu_letter(stripped):
                    stripped = stripped.upper()
                mapped = _pending_suggestions.pop(stripped, None)
                if mapped is not None:
                    # Consumed -- clear the rest of this batch too. A NEW
                    # suggestion list (registration sites already .clear()
                    # first) is what should supersede a stale one, not
                    # merely running an unrelated command in between: real
                    # on-device testing showed a suggestion list getting
                    # silently wiped by the very next slash command before
                    # the user ever got to act on it, contradicting the
                    # "type the number to work on it now" text printed
                    # alongside the list.
                    _pending_suggestions.clear()
                    from_home = _home_menu["entries"].get(stripped) == mapped
                    if from_home:
                        # A /home menu stays usable after a pick (on-device: after
                        # 1, a 2 went to the model); the fingerprint below retires
                        # it once the state it was built from changes.
                        _pending_suggestions.update(_home_menu["entries"])
                    if from_home and \
                            _home_menu["fingerprint"] != _home_fingerprint():
                        print(f"[!] [{stripped}] not run: the /home menu is out of date (state changed "
                              f"since it was shown). Current menu:")
                        _home()
                        continue
                    if SELF_MODIFY_OVERRIDE in mapped:
                        # Suggestions are model-written; the override must be
                        # typed by the user (reachable since 48411a0 made
                        # /sprint execute accept options).
                        print(f"[!] Suggestion [{stripped}] not run: it contains {SELF_MODIFY_OVERRIDE}, "
                              f"which only counts when you type it yourself.\n")
                        continue
                    print(f"[*] Running [{stripped}]: {mapped}")
                    user_input = mapped
                # else: not a matching digit -- leave pending_suggestions
                # intact and fall through, process user_input normally
                # else: not a matching digit -- fall through, process user_input normally
            if _is_apply(user_input) and _pending_write["path"] is None:
                print("\n[!] /apply: nothing pending.\n")
                continue
            if _is_menu_letter(user_input.strip()):
                key = user_input.strip().upper()
                cmd = next((c for k, _l, c in _home_letters() if k == key), None)
                if cmd:
                    # Not on the current menu, but a lettered tool: fixed and state-free.
                    print(f"[*] Running [{key}]: {cmd}")
                    user_input = cmd
            if user_input.strip().isdigit() or _is_menu_letter(user_input.strip()):
                # A number that is no current menu item (else it was mapped above).
                print(f"\n[!] No menu item {user_input.strip().upper()} right now -- not sent to the model. "
                      f"Type /home for the menu.\n")
                continue
            if _is_unknown_command(user_input):
                # Checked before the discard prompt: a typo keeps the proposal.
                _unknown_command(user_input)
                continue
            if INTENT_CARD and _is_freeform(user_input):
                # Before the discard prompt too: routing, answering and cards
                # write nothing, so a pending proposal is only at stake once
                # the engines are asked for code.
                _route(user_input)
                continue
            if _pending_write["path"] is not None and not _is_read_only(user_input):
                # A typo used to silently discard a sandbox-passed proposal
                # (2026-09-23: "apply" without the slash). Now: normalized
                # "apply" applies, a near-miss asks, anything else confirms
                # the discard first.
                if _is_apply(user_input) or (
                        _looks_like_apply(user_input) and _ask_yes(f"Did you mean /apply?")):
                    _apply_pending_write()
                    continue
                if not _ask_yes(f"Discard the pending write to {_pending_write['path']} "
                                f"and run your input instead?"):
                    print("[*] Kept. Type /apply to write it.\n")
                    continue
                _discard_pending_write()
                # fall through -- process user_input normally below
            if run_command(user_input):
                continue
            if user_input.strip().startswith("/") and "\n" not in user_input.strip():
                # A known first word with an unknown rest, e.g. "/sprint exectue".
                _unknown_command(user_input)
                continue
            run_synergy_pipeline(user_input)  # only with OSIRIS_INTENT_CARD=0
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Session terminated.")
            break

if __name__ == "__main__":
    main()
