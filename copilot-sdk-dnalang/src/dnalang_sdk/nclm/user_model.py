"""
OSIRIS Shadow-You — Persistent User Profile & Filesystem Model.

Learns the user's projects, habits, working hours, and interests
so OSIRIS can greet them by name and personalize every response.

Persists to ~/.osiris/user_profile.json
"""

import os
import json
import pwd
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


_PROFILE_DIR  = os.path.expanduser("~/.osiris")
_PROFILE_PATH = os.path.join(_PROFILE_DIR, "user_profile.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _git(args: list) -> str:
    """Run a git config query, return stdout or ''."""
    try:
        return subprocess.check_output(
            ["git"] + args, stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()
    except Exception:
        return ""


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class ProjectRecord:
    path: str
    name: str
    language: str           # "python" | "javascript" | "rust" | …
    last_opened: str        # ISO timestamp
    git_branch: str         # current branch or ""
    ptype: str              # "quantum" | "standard" | "unknown"


@dataclass
class UserProfile:
    name: str                        = "User"
    projects: List[ProjectRecord]    = field(default_factory=list)
    frequent_commands: Dict[str,int] = field(default_factory=dict)
    working_hours: Dict[str,int]     = field(default_factory=dict)
    preferred_backend: str           = "copilot"
    interests: List[str]             = field(default_factory=list)
    git_repos: List[str]             = field(default_factory=list)
    file_index: Dict[str,str]        = field(default_factory=dict)
    last_seen: str                   = ""

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self):
        os.makedirs(_PROFILE_DIR, exist_ok=True)
        data = {
            "name":              self.name,
            "projects":          [asdict(p) for p in self.projects],
            "frequent_commands": self.frequent_commands,
            "working_hours":     self.working_hours,
            "preferred_backend": self.preferred_backend,
            "interests":         self.interests,
            "git_repos":         self.git_repos,
            "file_index":        self.file_index,
            "last_seen":         self.last_seen,
        }
        with open(_PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "UserProfile":
        if not os.path.exists(_PROFILE_PATH):
            p = cls()
            p.name = p.infer_name()
            return p
        try:
            with open(_PROFILE_PATH) as f:
                data = json.load(f)
            p = cls()
            p.name              = data.get("name", "User")
            p.projects          = [
                ProjectRecord(**pr) for pr in data.get("projects", [])
            ]
            p.frequent_commands = data.get("frequent_commands", {})
            p.working_hours     = data.get("working_hours", {})
            p.preferred_backend = data.get("preferred_backend", "copilot")
            p.interests         = data.get("interests", [])
            p.git_repos         = data.get("git_repos", [])
            p.file_index        = data.get("file_index", {})
            p.last_seen         = data.get("last_seen", "")
            return p
        except Exception:
            p = cls()
            p.name = p.infer_name()
            return p

    # ── Name discovery ────────────────────────────────────────────────────────

    @staticmethod
    def infer_name() -> str:
        # 1. git config
        name = _git(["config", "--global", "user.name"])
        if name:
            return name.split()[0]          # first name only
        # 2. GECOS field in passwd
        try:
            gecos = pwd.getpwuid(os.getuid()).pw_gecos
            if gecos:
                first = gecos.split(",")[0].split()[0]
                if first:
                    return first
        except Exception:
            pass
        # 3. env
        for var in ("USER", "LOGNAME", "USERNAME"):
            v = os.environ.get(var, "")
            if v:
                return v.capitalize()
        return "User"

    # ── Filesystem scan ───────────────────────────────────────────────────────

    def scan_filesystem(self, max_depth: int = 4):
        """Walk ~/ up to max_depth, discover .git repos, Python/JS projects,
        build file_index of basename→fullpath for fast lookup.
        """
        home = os.path.expanduser("~")
        git_repos: List[str] = []
        projects: List[ProjectRecord] = []
        file_index: Dict[str, str] = {}
        seen_repos: set = set()

        _SKIP_DIRS = {
            ".cache", ".local/share/Trash", "__pycache__", "node_modules",
            ".git", ".venv", "venv", ".tox", ".mypy_cache", "dist", "build",
            ".cargo", ".rustup", "snap", ".snap",
        }

        def _lang(path: str) -> str:
            py = js = rs = ts = 0
            try:
                for fn in os.listdir(path):
                    if fn.endswith(".py"):   py += 1
                    if fn.endswith((".js", ".jsx")): js += 1
                    if fn.endswith(".rs"):   rs += 1
                    if fn.endswith((".ts", ".tsx")): ts += 1
            except Exception:
                pass
            for lang, count in [("python",py),("javascript",js),("rust",rs),("typescript",ts)]:
                if count:
                    return lang
            if os.path.exists(os.path.join(path, "package.json")):
                return "javascript"
            return "unknown"

        def _walk(dirpath: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = os.scandir(dirpath)
            except (PermissionError, OSError):
                return

            for entry in entries:
                # Index regular files by basename
                if entry.is_file(follow_symlinks=False):
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in (".py", ".js", ".ts", ".rs", ".go", ".json", ".toml", ".yaml", ".yml"):
                        file_index[entry.name] = entry.path
                    continue

                if not entry.is_dir(follow_symlinks=False):
                    continue

                # Skip known noise dirs
                base = entry.name
                rel  = os.path.relpath(entry.path, home)
                if base.startswith(".") and base not in (".config",):
                    continue
                if any(skip in rel for skip in _SKIP_DIRS):
                    continue

                # Detect .git
                git_dir = os.path.join(entry.path, ".git")
                if os.path.isdir(git_dir) and entry.path not in seen_repos:
                    seen_repos.add(entry.path)
                    git_repos.append(entry.path)

                    # Current branch
                    branch = _git(["-C", entry.path, "rev-parse", "--abbrev-ref", "HEAD"])

                    # Modification time
                    try:
                        mtime = os.path.getmtime(entry.path)
                        last_opened = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                    except Exception:
                        last_opened = datetime.now(timezone.utc).isoformat()

                    lang = _lang(entry.path)
                    ptype = "quantum" if any(
                        q in base.lower()
                        for q in ("quantum","qiskit","dna","osiris","dnalang","aeterna")
                    ) else "standard"

                    projects.append(ProjectRecord(
                        path=entry.path,
                        name=base,
                        language=lang,
                        last_opened=last_opened,
                        git_branch=branch,
                        ptype=ptype,
                    ))

                _walk(entry.path, depth + 1)

        _walk(home, 1)

        # Sort projects by last_opened descending, keep top 20
        projects.sort(key=lambda r: r.last_opened, reverse=True)
        self.projects    = projects[:20]
        self.git_repos   = git_repos[:50]
        self.file_index  = file_index

        # Infer interests from project names / languages
        interests: set = set()
        for pr in self.projects:
            n = pr.name.lower()
            if any(x in n for x in ("quantum","qiskit","ibm","fez","torino")):
                interests.add("quantum")
            if any(x in n for x in ("dna","genome","organism")):
                interests.add("bioinformatics")
            if any(x in n for x in ("sec","sentinel","scimitar","threat","osiris")):
                interests.add("security")
            if any(x in n for x in ("web","react","next","vercel","front")):
                interests.add("webdev")
            if any(x in n for x in ("research","experiment","lab","bench")):
                interests.add("research")
        self.interests = sorted(interests)

    # ── Command observation ───────────────────────────────────────────────────

    def observe_command(self, cmd: str):
        """Increment hit counter for a command and update working hour histogram."""
        if not cmd:
            return
        self.frequent_commands[cmd] = self.frequent_commands.get(cmd, 0) + 1

        hour = str(datetime.now().hour)
        self.working_hours[hour] = self.working_hours.get(hour, 0) + 1

        self.last_seen = datetime.now(timezone.utc).isoformat()
        self.save()

    # ── LLM context blob ─────────────────────────────────────────────────────

    def get_context_blob(self) -> str:
        """Return a short summary for injection into LLM system context."""
        top_cmds = sorted(
            self.frequent_commands.items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_cmd_str = ", ".join(f"{c}({n})" for c, n in top_cmds) if top_cmds else "none yet"

        proj_names = [p.name for p in self.projects[:5]]
        proj_str   = ", ".join(proj_names) if proj_names else "none discovered"

        interests_str = ", ".join(self.interests) if self.interests else "general"

        # Peak working hour
        if self.working_hours:
            peak_hour = max(self.working_hours, key=lambda h: self.working_hours[h])
            hour_int = int(peak_hour)
            ampm = "AM" if hour_int < 12 else "PM"
            peak_str = f"{hour_int % 12 or 12}{ampm}"
        else:
            peak_str = "unknown"

        return (
            f"[USER PROFILE — {self.name}]\n"
            f"Projects ({len(self.projects)} tracked): {proj_str}\n"
            f"Git repos found: {len(self.git_repos)}\n"
            f"Interests: {interests_str}\n"
            f"Most-used commands: {top_cmd_str}\n"
            f"Peak working hour: {peak_str}\n"
            f"Preferred backend: {self.preferred_backend}\n"
            f"Last seen: {self.last_seen or 'first session'}\n"
        )

    # ── Lookup helper ─────────────────────────────────────────────────────────

    def find_file(self, name: str) -> Optional[str]:
        """Fast basename lookup in file_index."""
        return self.file_index.get(name)


# ── Module-level singleton ────────────────────────────────────────────────────

_profile_singleton: Optional[UserProfile] = None


def get_user_profile(scan: bool = False) -> UserProfile:
    """Return the cached UserProfile, optionally triggering a fresh scan."""
    global _profile_singleton
    if _profile_singleton is None:
        _profile_singleton = UserProfile.load()
        if not _profile_singleton.projects and scan:
            _profile_singleton.scan_filesystem()
            _profile_singleton.save()
    return _profile_singleton
