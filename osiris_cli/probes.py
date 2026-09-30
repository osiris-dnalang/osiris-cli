"""Read-only checks OSIRIS runs before answering, so answers rest on what is
on disk now rather than on the mentor model's memory.

Code chooses and runs them (keyword routing on the message, or /check), never
the model: a local 7B model asked to emit tool calls on this CPU is slow and
unreliable, and a model must not decide what runs. Every probe only reads.
Each result carries the command-equivalent it ran, so an answer can say
where a number came from.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Callable, Dict, List, Optional

HOME = os.path.expanduser("~")
REPOS = ("osiris-cli", "organism_sim", "dnalang-core", "bridge")
MAX_FILE_CHARS = 2500

# Never read, whatever is asked: credentials and private keys.
SECRET_RE = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.env|\.ssh|\.gnupg|\.aws|\.config/gcloud|\.netrc|"
                       r"[^/]*(token|secret|credential|passw|apikey|api_key)[^/]*|id_[a-z0-9]+|[^/]*\.pem|[^/]*\.key)$",
                       re.I)


def _run(args: List[str], timeout: float = 10.0) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"(failed: {type(e).__name__})"


def verify_chain(path: str) -> Dict[str, object]:
    """Recompute the exchange log's hash chain (the same rule Osiris._record writes)."""
    import hashlib
    n, prev, broken = 0, "0" * 64, None
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                entry = json.loads(line)
                h = entry.pop("hash", None)
                body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                if entry.get("prev") != prev or hashlib.sha256(body.encode()).hexdigest() != h:
                    broken = i
                    break
                prev, n = h, n + 1
    except FileNotFoundError:
        return {"entries": 0, "intact": True, "head": prev}
    except (OSError, ValueError) as e:
        return {"entries": n, "intact": False, "error": type(e).__name__}
    return {"entries": n, "intact": broken is None, "broken_at": broken, "head": prev[:12]}


def safe_path(raw: str, base: str = HOME) -> Optional[str]:
    """A readable text file under the home directory that is not a secret."""
    p = os.path.realpath(os.path.expanduser(raw if raw.startswith(("~", "/")) else os.path.join(base, raw)))
    if not (p == base or p.startswith(base.rstrip("/") + "/")):
        return None
    rel = os.path.relpath(p, base)
    if any(SECRET_RE.search("/".join(rel.split(os.sep)[: i + 1])) for i in range(len(rel.split(os.sep)))):
        return None
    return p if os.path.isfile(p) else None


class Probes:
    def __init__(self, living_home: str, base: str = HOME,
                 trainer_status: Optional[Callable[[], List[str]]] = None):
        self.living_home = living_home
        self.base = base
        self.trainer_status = trainer_status

    # -- the probes --------------------------------------------------------

    def trainer(self, _msg: str = "") -> Dict[str, str]:
        lines = self.trainer_status() if self.trainer_status else ["(trainer status unavailable)"]
        return {"name": "trainer", "cmd": "osiris train --status", "out": "\n".join(lines)}

    def ledger(self, _msg: str = "") -> Dict[str, str]:
        v = verify_chain(os.path.join(self.living_home, "exchanges.jsonl"))
        return {"name": "ledger", "cmd": "verify ~/.osiris/living/exchanges.jsonl hash chain",
                "out": json.dumps(v)}

    def git(self, _msg: str = "") -> Dict[str, str]:
        parts = []
        for repo in REPOS:
            d = os.path.join(self.base, repo)
            if not os.path.isdir(os.path.join(d, ".git")):
                continue
            branch = _run(["git", "-C", d, "branch", "--show-current"])
            log = _run(["git", "-C", d, "log", "--oneline", "-3", "--format=%h %ad %s", "--date=short"])
            dirty = _run(["git", "-C", d, "status", "--short", "--untracked-files=no"])
            n = len([x for x in dirty.splitlines() if x.strip()])
            parts.append(f"{repo} ({branch}, {n} modified tracked files):\n{log}")
        return {"name": "git", "cmd": "git log --oneline -3; git status --short (per repo)",
                "out": "\n\n".join(parts) or "(no repos found)"}

    def system(self, _msg: str = "") -> Dict[str, str]:
        out = [_run(["uptime"]), _run(["free", "-h"]).splitlines()[1] if _run(["free", "-h"]) else ""]
        try:
            import urllib.request
            base = os.environ.get("OSIRIS_OLLAMA", "http://localhost:11434").rstrip("/")
            with urllib.request.urlopen(base + "/api/ps", timeout=2.0) as r:
                loaded = [m["name"] for m in json.load(r).get("models", [])]
            out.append("ollama models in memory: " + (", ".join(loaded) or "none"))
        except (OSError, ValueError, KeyError):
            out.append("ollama: not reachable")
        return {"name": "system", "cmd": "uptime; free -h; ollama ps", "out": "\n".join(x for x in out if x)}

    def files(self, msg: str) -> List[Dict[str, str]]:
        found = []
        for raw in re.findall(r"(?:~/|/)?[\w.\-]+(?:/[\w.\-]+)+\.\w+|[\w\-]+\.(?:md|txt|json|py|dna|toml|yaml|yml)\b", msg):
            p = safe_path(raw, self.base)
            if not p and "/" not in raw:
                continue
            if p is None:
                found.append({"name": "file", "cmd": f"read {raw}",
                              "out": "(not read: missing, outside home, or a credentials file)"})
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read(MAX_FILE_CHARS + 1)
            more = "\n…(truncated)" if len(text) > MAX_FILE_CHARS else ""
            found.append({"name": "file", "cmd": f"read {os.path.relpath(p, self.base)}",
                          "out": text[:MAX_FILE_CHARS] + more})
            if len(found) >= 2:
                break
        return found

    # -- routing -----------------------------------------------------------

    ROUTES = (
        ("trainer", re.compile(r"\b(train(ing|er)?|distill\w*|checkpoint|step|bpb|bits.per.byte|gate|learn(ing|ed)?)\b", re.I)),
        ("git", re.compile(r"\b(git|commits?|committed|branch|diff|changes?|changed|repo(sitory|s)?|pushed)\b", re.I)),
        ("ledger", re.compile(r"\b(ledger|hash.?chain|exchanges?|log intact|tamper\w*|audit)\b", re.I)),
        ("system", re.compile(r"\b(cpu|ram|memory usage|load|slow|ollama|system|machine|resources?)\b", re.I)),
    )
    SELF_RE = re.compile(r"\b(about yourself|who are you|what are you|status|how are you doing|what do you know)\b", re.I)

    def select(self, msg: str) -> List[str]:
        names = [n for n, rx in self.ROUTES if rx.search(msg)]
        if self.SELF_RE.search(msg) and "trainer" not in names:
            names.insert(0, "trainer")
        return names

    def run(self, msg: str, names: Optional[List[str]] = None) -> List[Dict[str, str]]:
        results = []
        for name in (names if names is not None else self.select(msg)):
            try:
                results.append(getattr(self, name)(msg))
            except Exception as e:  # noqa: BLE001 - a failed probe is reported, never invented
                results.append({"name": name, "cmd": name, "out": f"(probe failed: {type(e).__name__})"})
        try:
            results.extend(self.files(msg))
        except OSError:
            pass
        return results

    @staticmethod
    def format(results: List[Dict[str, str]]) -> str:
        return "\n\n".join(f"$ {r['cmd']}\n{r['out']}" for r in results)
