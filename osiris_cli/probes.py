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
MAX_FILE_CHECKS = 2
RESULTS_DIR = os.path.join("organism_sim", "results")
MAX_VERDICT_CHARS = 1500

# How people name the pre-registered experiments -> the results-file prefix.
EXPERIMENT_ALIASES = (
    (re.compile(r"\bexperiment[\s_-]*zero\b", re.I), "expzero"),
    (re.compile(r"\bexperiment[\s_-]*one\b", re.I), "expone"),
    (re.compile(r"\bsubstrate[\s_-]*opt[\s_-]*([12])\b", re.I), r"substrate_opt\1"),
)
EXPERIMENT_RE = re.compile(r"\b(m[1-7][a-c]?|expzero|expone|substrate_opt[12]|relay(?:_cusum)?|drift|signalling)\b",
                           re.I)

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
    """Recompute the exchange log's hash chain (the same rule Osiris._record writes).

    Every entry must hash to its own content, and its `prev` must be the genesis hash or the hash of an earlier
    entry; otherwise the chain is broken there (an edited, inserted-with-a-false-link or removed entry). A `prev`
    that names an earlier entry other than the one just before is a fork: two writers appended from different heads
    (2026-10-07, before the writer read the file's last entry). Forks are listed, never hidden; they are not breaks,
    because no entry was altered and every link resolves.

    The result names the file it read (``resolved_path``, so a console reading the wrong data home shows it) and a
    ``status`` with an ``exit_code`` (E-24): INTACT 0; EMPTY 0, no log or no entries yet; TAMPERED 1, an entry fails its hash or
    links nowhere; UNREADABLE 2, the file or a line of it cannot be read or parsed."""
    import hashlib
    genesis = "0" * 64
    resolved = os.path.abspath(os.path.expanduser(path))
    n, prev, forks, seen = 0, genesis, [], {genesis}

    def result(status: str, broken_at: Optional[int] = None, error: Optional[str] = None) -> Dict[str, object]:
        return {"resolved_path": resolved, "status": status, "intact": status in ("INTACT", "EMPTY"),
                "exit_code": {"INTACT": 0, "EMPTY": 0, "TAMPERED": 1, "UNREADABLE": 2}[status],
                "entries": n, "broken_at": broken_at, "forks": forks, "head": prev[:12], "error": error}

    if not os.path.exists(resolved):
        return result("EMPTY")
    try:
        with open(resolved, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except ValueError as e:
                    return result("UNREADABLE", i, f"line {i + 1} is not JSON ({e})")
                if not isinstance(entry, dict):
                    return result("TAMPERED", i, f"line {i + 1} is not an entry")
                h = entry.pop("hash", None)
                body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                if hashlib.sha256(body.encode()).hexdigest() != h:
                    return result("TAMPERED", i, f"entry {i} does not hash to its recorded hash")
                if entry.get("prev") not in seen:
                    return result("TAMPERED", i, f"entry {i} links to no earlier entry")
                if entry.get("prev") != prev:
                    forks.append(i)
                seen.add(h)
                prev, n = h, n + 1
    except (OSError, UnicodeDecodeError) as e:
        return result("UNREADABLE", None, f"{type(e).__name__}: {e}")
    return result("INTACT" if n else "EMPTY")


def verify_chain_tail(path: str, tail_lines: int = 20) -> Dict[str, object]:
    """Fast incremental verification of the last N entries of the ledger.
    Reads only the tail bytes under seek/tail semantics, verifying
    internal cryptographic consistency and hash chaining in O(1) time.
    """
    import hashlib
    if not os.path.exists(path):
        return {"tail_count": 0, "intact": True, "head": "0" * 12}

    lines = []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            buffer_size = min(size, max(tail_lines * 8192, 65536))
            f.seek(size - buffer_size, os.SEEK_SET)
            chunk = f.read().decode("utf-8", errors="replace")
            all_lines = [ln for ln in chunk.splitlines() if ln.strip()]
            lines = all_lines[-tail_lines:]
    except Exception as e:
        return {"tail_count": 0, "intact": False, "error": str(e)}

    if not lines:
        return {"tail_count": 0, "intact": True, "head": "0" * 12}

    intact = True
    prev_hash = None
    last_head = None

    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
            h = entry.pop("hash", None)
            body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            calc = hashlib.sha256(body.encode()).hexdigest()
            if calc != h:
                intact = False
                break
            if prev_hash is not None and entry.get("prev") != prev_hash:
                intact = False
                break
            prev_hash = h
            last_head = h
        except Exception:
            intact = False
            break

    return {
        "tail_count": len(lines),
        "intact": intact,
        "head": (last_head[:12] if last_head else "0" * 12),
    }


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
        """The exchange log's chain, naming the file read: two data homes (PRoot's ~/.osiris and Termux's) each
        hold a log, and a console reading the other one is the E-24 failure."""
        resolved_path = os.path.abspath(os.path.expanduser(os.path.join(self.living_home, "exchanges.jsonl")))
        v = verify_chain(resolved_path)
        verdict_str = "PASS" if v["intact"] else f"FAIL ({v['status']})"
        out_lines = [
            f"Data Home:    {resolved_path}",
            f"Status:       {v['status']}",
            f"Integrity:    {verdict_str} (exit code {v['exit_code']})",
            f"Entries:      {v['entries']} verified",
            f"Chain Head:   {v['head']}",
            f"Forks:        {len(v['forks'])}",
        ]
        if v.get("broken_at") is not None:
            out_lines.append(f"Broken At:    entry {v['broken_at']} ({v.get('error', '')})")
        elif v.get("error"):
            out_lines.append(f"Error:        {v['error']}")
        if v["status"] == "EMPTY":
            out_lines.append("Note:         no exchange log here yet; a console that has talked before is "
                             "reading another data home")
        return {
            "name": "ledger",
            "cmd": f"verify {resolved_path} hash chain",
            "out": "\n".join(out_lines),
            "resolved_path": resolved_path,
            "status": str(v["status"]),
            "intact": bool(v["intact"]),
            "exit_code": int(v["exit_code"]),
        }

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

    def evidence(self, msg: str) -> Dict[str, str]:
        """The pre-registered results behind the scorecard: each named experiment's
        results file, its sha256, and the verdict block exactly as the run wrote it.
        With no experiment named, one line per evaluation file."""
        d = os.path.join(self.base, RESULTS_DIR)
        try:
            names = sorted(n for n in os.listdir(d) if n.endswith(".json"))
        except OSError:
            return {"name": "evidence", "cmd": f"ls {RESULTS_DIR}", "out": "(no results directory)"}
        text = msg
        for rx, repl in EXPERIMENT_ALIASES:
            text = rx.sub(repl, text)
        wanted = {m.lower() for m in EXPERIMENT_RE.findall(text)}
        picked = [n for n in names if n.split("_eval")[0].split("_sweep")[0].split("_tuning")[0] in wanted]
        if not wanted:
            picked = [n for n in names if "_eval" in n]
        elif not picked:
            return {"name": "evidence", "cmd": f"ls {RESULTS_DIR}",
                    "out": f"(no results file for {', '.join(sorted(wanted))}: not run, or not recorded)"}
        import hashlib
        parts = []
        for n in picked:
            with open(os.path.join(d, n), "rb") as f:
                raw = f.read()
            head = f"{RESULTS_DIR}/{n} sha256:{hashlib.sha256(raw).hexdigest()[:16]}"
            try:
                verdict = json.loads(raw).get("verdict") if raw.lstrip()[:1] == b"{" else None
            except ValueError:
                verdict = None
            if not wanted:
                if isinstance(verdict, dict):
                    verdict = next((verdict[k] for k in ("outcome", "verdict", "pass", "PASS") if k in verdict),
                                   None)
                if isinstance(verdict, bool):
                    verdict = "PASS" if verdict else "FAIL"
                parts.append(head + (f"  verdict: {str(verdict)[:100]}" if verdict is not None else ""))
                continue
            body = json.dumps(verdict, separators=(",", ":")) if verdict is not None else "(no verdict block)"
            more = "…(truncated)" if len(body) > MAX_VERDICT_CHARS else ""
            parts.append(f"{head}\nverdict: {body[:MAX_VERDICT_CHARS]}{more}")
        cmd = f"sha256sum + verdict of {RESULTS_DIR}/" + ("{" + ",".join(picked) + "}" if wanted else "*_eval*.json")
        return {"name": "evidence", "cmd": cmd, "out": ("\n\n" if wanted else "\n").join(parts)}

    def files(self, msg: str) -> List[Dict[str, str]]:
        found, seen = [], set()
        for raw in re.findall(r"(?:~/|/)?[\w.\-]+(?:/[\w.\-]+)+\.\w+|[\w\-]+\.(?:md|txt|json|py|dna|toml|yaml|yml)\b", msg):
            if raw in seen:
                continue
            seen.add(raw)
            if len(found) >= MAX_FILE_CHECKS:   # read or not: a pasted log names dozens of paths
                break
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
        return found

    # -- routing -----------------------------------------------------------

    ROUTES = (
        ("trainer", re.compile(r"\b(train(ing|er)?|distill\w*|checkpoint|step|bpb|bits.per.byte|gate|learn(ing|ed)?)\b", re.I)),
        ("git", re.compile(r"\b(git|commits?|committed|branch|diff|changes?|changed|repo(sitory|s)?|pushed)\b", re.I)),
        ("ledger", re.compile(r"\b(ledger|hash.?chain|exchanges?|log intact|tamper\w*|audit)\b", re.I)),
        ("evidence", re.compile(r"\b(m[1-7][a-c]?|ablation|pre-?regist\w*|scorecard|evidence|results?|"
                                r"experiment\w*|substrate[\s_-]*opt\w*|relay|drift|signalling|annecs)\b", re.I)),
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
