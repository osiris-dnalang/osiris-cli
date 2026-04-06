#!/usr/bin/env python3
"""
Sovereign Task Manifold (STM) — Agile Defense Systems
======================================================
Non-local, non-causal project management mesh.

AURA  (Φ) — Product Owner / Architect: deconstructs intent, plans geometry.
AIDEN (Λ) — Scrum Master / Executor:   manifests physical directory substrate.

Ledger: Phase-Conjugate Replay Buffer (PCRB) — SHA-256 hash-chained JSONL.

DNA::}{::lang v51.843 | CAGE 9HUP5
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import uuid
import hashlib
import textwrap
import readline  # noqa: F401 — enables arrow keys in interactive mode
from pathlib import Path
from typing import Optional, Dict, List, Any

# ── ANSI colour palette (mirrors C class in tools.py) ─────────────────────────
_R  = "\033[0m"
_H  = "\033[1m"
_D  = "\033[2m"
_CY = "\033[96m"
_MG = "\033[95m"
_GR = "\033[92m"
_YE = "\033[93m"
_RD = "\033[91m"
_BL = "\033[94m"
_WH = "\033[97m"

# ── Physics constants ──────────────────────────────────────────────────────────
LAMBDA_PHI   = 2.176435e-8
THETA_LOCK   = 51.843
STM_VERSION  = "1.0.0"

# ── LLM helper (uses existing tool_llm cascade) ────────────────────────────────
def _llm(prompt: str, system: str = "") -> str:
    try:
        from .tools import tool_llm
        return tool_llm(prompt, system).strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  PCRB  — Phase-Conjugate Replay Buffer (immutable ledger)
# ══════════════════════════════════════════════════════════════════════════════

class PCRBLedger:
    """SHA-256 hash-chained append-only ledger for all STM events."""

    def __init__(self, ledger_path: Path) -> None:
        self.path = ledger_path
        self._prev_hash = "0" * 64

        # Replay existing entries to get the tip hash
        if self.path.exists():
            try:
                for line in self.path.read_text().splitlines():
                    if line.strip():
                        entry = json.loads(line)
                        self._prev_hash = entry.get("hash", self._prev_hash)
            except Exception:
                pass

    def append(self, action: str, data: Dict[str, Any]) -> str:
        entry = {
            "ts":        round(time.time(), 4),
            "action":    action,
            "data":      data,
            "lambda_phi": LAMBDA_PHI,
            "prev":      self._prev_hash,
            "hash":      "",
        }
        canonical = json.dumps({k: v for k, v in entry.items() if k != "hash"},
                               sort_keys=True)
        entry["hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        self._prev_hash = entry["hash"]
        with open(self.path, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry["hash"]

    def tail(self, n: int = 10) -> List[Dict]:
        if not self.path.exists():
            return []
        lines = [l for l in self.path.read_text().splitlines() if l.strip()]
        results = []
        for line in lines[-n:]:
            try:
                results.append(json.loads(line))
            except Exception:
                pass
        return results


# ══════════════════════════════════════════════════════════════════════════════
#  Sprint  —  JSON-serialised sprint/project state
# ══════════════════════════════════════════════════════════════════════════════

class Sprint:
    STATUS_VALUES = ("planned", "in_progress", "blocked", "done")
    TASK_STATUS   = ("pending", "in_progress", "done", "blocked")

    def __init__(self, data: Dict) -> None:
        self._d = data

    # ── getters ───────────────────────────────────────────────────────────────
    @property
    def id(self)       -> str: return self._d["id"]
    @property
    def name(self)     -> str: return self._d["name"]
    @property
    def path(self)     -> Path: return Path(self._d["path"])
    @property
    def status(self)   -> str: return self._d.get("status", "planned")
    @property
    def backlog(self)  -> List[Dict]: return self._d.get("backlog", [])
    @property
    def dirs(self)     -> List[str]: return self._d.get("directories", [])
    @property
    def files(self)    -> Dict[str, str]: return self._d.get("files", {})
    @property
    def tags(self)     -> List[str]: return self._d.get("tags", [])
    @property
    def created(self)  -> float: return self._d.get("created", 0)

    # ── mutators ──────────────────────────────────────────────────────────────
    def set_status(self, s: str) -> None:
        if s in self.STATUS_VALUES:
            self._d["status"] = s

    def add_task(self, title: str, agent: str = "AIDEN") -> Dict:
        task = {
            "id":     len(self.backlog) + 1,
            "task":   title,
            "status": "pending",
            "agent":  agent,
            "created": round(time.time(), 2),
        }
        self._d["backlog"].append(task)
        return task

    def update_task(self, task_id: int, **kwargs) -> bool:
        for t in self._d["backlog"]:
            if t["id"] == task_id:
                t.update(kwargs)
                return True
        return False

    def to_dict(self) -> Dict:
        return self._d

    # ── factory ───────────────────────────────────────────────────────────────
    @classmethod
    def new(cls, name: str, path: str,
            directories: List[str], files: Dict[str, str],
            tags: List[str] = None, llm_plan: str = "") -> "Sprint":
        data = {
            "id":          str(uuid.uuid4())[:8],
            "name":        name,
            "path":        str(path),
            "status":      "planned",
            "created":     round(time.time(), 2),
            "tags":        tags or [],
            "llm_plan":    llm_plan,
            "directories": directories,
            "files":       files,
            "backlog": [
                {"id": 1, "task": "Scaffold directory geometry",
                 "status": "pending", "agent": "AIDEN", "created": round(time.time(),2)},
                {"id": 2, "task": "Inject ΛΦ constants and manifest",
                 "status": "pending", "agent": "AIDEN", "created": round(time.time(),2)},
                {"id": 3, "task": "Wire NCLM inference hooks",
                 "status": "pending", "agent": "AURA",  "created": round(time.time(),2)},
                {"id": 4, "task": "Define acceptance criteria",
                 "status": "pending", "agent": "AURA",  "created": round(time.time(),2)},
            ],
        }
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict) -> "Sprint":
        return cls(data)


# ══════════════════════════════════════════════════════════════════════════════
#  Display helpers (rich-free)
# ══════════════════════════════════════════════════════════════════════════════

def _box(title: str, body: str, colour: str = _CY, width: int = 68) -> str:
    top = f"  {colour}{_H}┌─ {title} {'─' * max(0, width - len(title) - 4)}┐{_R}"
    lines = []
    for line in body.splitlines():
        pad = width - len(line) - 2
        lines.append(f"  {colour}{_H}│{_R} {line}{' ' * max(0, pad)} {colour}{_H}│{_R}")
    bot = f"  {colour}{_H}└{'─' * (width + 1)}┘{_R}"
    return "\n".join([top] + lines + [bot])


def _status_icon(s: str) -> str:
    return {
        "planned":     f"{_YE}◷{_R}",
        "in_progress": f"{_CY}▶{_R}",
        "done":        f"{_GR}✓{_R}",
        "blocked":     f"{_RD}✗{_R}",
        "pending":     f"{_D}·{_R}",
    }.get(s, f"{_D}?{_R}")


def _agent_colour(agent: str) -> str:
    return {
        "AURA":    f"{_MG}AURA{_R}",
        "AIDEN":   f"{_CY}AIDEN{_R}",
        "CHEOPS":  f"{_YE}CHEOPS{_R}",
        "CHRONOS": f"{_BL}CHRONOS{_R}",
    }.get(agent.upper(), agent)


def _dir_tree(name: str, dirs: List[str], files: Dict[str, str]) -> str:
    lines = [f"  {_H}📁 {name}/{_R}"]
    for d in dirs:
        lines.append(f"     {_CY}├── {d}/{_R}")
    for fname in files:
        lines.append(f"     {_GR}├── {fname}{_R}")
    return "\n".join(lines)


def _header(title: str, sub: str = "", colour: str = _MG) -> str:
    bar = "─" * 68
    lines = [f"\n  {colour}{_H}{title}{_R}"]
    if sub:
        lines.append(f"  {_D}{sub}{_R}")
    lines.append(f"  {_D}{bar}{_R}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  AgileMesh — core engine
# ══════════════════════════════════════════════════════════════════════════════

class AgileMesh:
    """
    Sovereign Task Manifold engine.

    workspace/
      .osiris/
        sprints/          — sprint_<id>.json files
        pcrb_ledger.jsonl — hash-chained event log
    """

    _SYSTEM_PROMPT = textwrap.dedent("""\
        You are AURA, the sovereign project architect for the OSIRIS system.
        Given a plain-English intent, produce a concrete project plan as JSON with
        exactly these keys:
          name        : slug (snake_case)
          description : one sentence
          tags        : list of relevant tags
          directories : list of relative directory paths to create
          files       : dict mapping relative file paths to initial content strings
          tasks       : list of task title strings for the sprint backlog
        Return ONLY the JSON object, no markdown, no explanation.
    """)

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace   = Path(workspace_root or os.getcwd()).resolve()
        self._osiris_dir = self.workspace / ".osiris"
        self._sprints    = self._osiris_dir / "sprints"
        self._sprints.mkdir(parents=True, exist_ok=True)
        self._ledger     = PCRBLedger(self._osiris_dir / "pcrb_ledger.jsonl")

    # ── internal helpers ──────────────────────────────────────────────────────

    def _sprint_path(self, sprint_id: str) -> Path:
        return self._sprints / f"sprint_{sprint_id}.json"

    def _load_sprint(self, sprint_id: str) -> Optional[Sprint]:
        p = self._sprint_path(sprint_id)
        if not p.exists():
            # Try by name
            for f in self._sprints.glob("sprint_*.json"):
                try:
                    d = json.loads(f.read_text())
                    if d.get("name") == sprint_id or d.get("id") == sprint_id:
                        return Sprint.from_dict(d)
                except Exception:
                    pass
            return None
        return Sprint.from_dict(json.loads(p.read_text()))

    def _save_sprint(self, sprint: Sprint) -> None:
        self._sprint_path(sprint.id).write_text(json.dumps(sprint.to_dict(), indent=2))

    def _all_sprints(self) -> List[Sprint]:
        result = []
        for f in sorted(self._sprints.glob("sprint_*.json"),
                        key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                result.append(Sprint.from_dict(json.loads(f.read_text())))
            except Exception:
                pass
        return result

    def _parse_llm_plan(self, raw: str, fallback_name: str) -> Dict:
        """Extract JSON from LLM response (handles markdown fences)."""
        raw = raw.strip()
        # Strip markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
        # Find first {...} block
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    def _default_scaffold(self, intent: str) -> Dict:
        """Fallback plan when LLM is unavailable."""
        name = re.sub(r"[^\w]", "_",
                      "_".join(intent.lower().split()[:4])).strip("_") or "project"
        return {
            "name":        name,
            "description": intent,
            "tags":        ["osiris", "auto"],
            "directories": ["src", "src/agents", "tests", "docs", "scripts"],
            "files": {
                "README.md":          f"# {name}\n{intent}\n",
                "src/__init__.py":    "# OSIRIS NCLM — 6D-CRSM Initialized\n",
                "src/main.py":        (
                    "\"\"\"Entry point.\"\"\"\n\n"
                    "LAMBDA_PHI = 2.176435e-8\n"
                    "THETA_LOCK = 51.843\n\n"
                    "def ignite():\n"
                    "    print(f'Λ={LAMBDA_PHI}  θ={THETA_LOCK}°')\n\n"
                    "if __name__ == '__main__':\n"
                    "    ignite()\n"
                ),
                "tests/__init__.py":  "",
                "docs/architecture.md": f"# Architecture\n\nProject: {name}\n",
            },
            "tasks": [
                "Define API surface and data contracts",
                "Implement core logic module",
                "Write unit tests",
                "Document architecture decisions",
            ],
        }

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def plan(self, intent: str, use_llm: bool = True) -> Sprint:
        """
        AURA Phase: deconstruct intent → project geometry → Sprint object.
        """
        print(_header("Φ AURA — Product Owner", f"Synthesizing intent: {intent}", _MG))

        scaffold = {}
        if use_llm:
            print(f"\n  {_D}Querying NCLM for project architecture…{_R}")
            raw = _llm(intent, self._SYSTEM_PROMPT)
            if raw:
                scaffold = self._parse_llm_plan(raw, intent)

        if not scaffold or "name" not in scaffold:
            print(f"  {_YE}⚙ Using deterministic scaffold (LLM not available){_R}")
            scaffold = self._default_scaffold(intent)

        name    = scaffold["name"]
        proj_path = self.workspace / name

        # Merge LLM-provided tasks into backlog if present
        sprint = Sprint.new(
            name        = name,
            path        = str(proj_path),
            directories = scaffold.get("directories", ["src", "tests", "docs"]),
            files       = scaffold.get("files", {}),
            tags        = scaffold.get("tags", []),
            llm_plan    = scaffold.get("description", intent),
        )

        # Add LLM-generated tasks
        for t in scaffold.get("tasks", []):
            sprint.add_task(t, agent="AIDEN")

        self._save_sprint(sprint)
        h = self._ledger.append("AURA_PLAN", {
            "sprint_id": sprint.id,
            "name":      name,
            "intent":    intent,
        })

        # ── Print proposed geometry ──
        print(f"\n  {_MG}{_H}Sprint ID:{_R}  {sprint.id}")
        print(f"  {_MG}{_H}Project:{_R}    {name}")
        print(f"  {_MG}{_H}Path:{_R}       {proj_path}")
        if scaffold.get("description"):
            print(f"  {_MG}{_H}Desc:{_R}       {scaffold['description']}")
        print()
        print(_dir_tree(name, sprint.dirs, sprint.files))
        print()

        # Backlog table
        print(f"  {_H}Sprint Backlog{_R}")
        print(f"  {'─'*60}")
        for t in sprint.backlog:
            icon  = _status_icon(t["status"])
            agent = _agent_colour(t.get("agent", "AIDEN"))
            print(f"  {icon} [{t['id']:>2}] {t['task']:<44} {agent}")
        print(f"  {'─'*60}")
        print(f"\n  {_D}PCRB: {h[:16]}…{_R}")
        print(f"\n  {_GR}Run: osiris agile create {sprint.id}{_R}\n")
        return sprint

    def create(self, sprint_id: str) -> bool:
        """
        AIDEN Phase: physically manifest the planned directory substrate.
        """
        sprint = self._load_sprint(sprint_id)
        if sprint is None:
            print(f"\n  {_RD}✗ Sprint '{sprint_id}' not found in STM.{_R}")
            print(f"  {_D}Run 'osiris agile list' to see active sprints.{_R}\n")
            return False

        print(_header("Λ AIDEN — Scrum Master / Executor",
                      f"Manifesting substrate: {sprint.name}", _CY))

        base = sprint.path
        errors = []

        # Create directories
        for d in sprint.dirs:
            target = base / d
            try:
                target.mkdir(parents=True, exist_ok=True)
                print(f"  {_GR}✓{_R} dir   {_D}{d}/{_R}")
            except Exception as e:
                print(f"  {_RD}✗{_R} dir   {d}/ — {e}")
                errors.append(str(e))

        # Write files
        for fname, content in sprint.files.items():
            fpath = base / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            try:
                fpath.write_text(content)
                print(f"  {_GR}✓{_R} file  {_D}{fname}{_R}")
            except Exception as e:
                print(f"  {_RD}✗{_R} file  {fname} — {e}")
                errors.append(str(e))

        # Write .osiris_manifest.json
        manifest = {
            **sprint.to_dict(),
            "manifested_at": round(time.time(), 2),
            "lambda_phi":    LAMBDA_PHI,
            "theta_lock":    THETA_LOCK,
        }
        try:
            (base / ".osiris_manifest.json").write_text(
                json.dumps(manifest, indent=2))
            print(f"  {_GR}✓{_R} file  {_D}.osiris_manifest.json{_R}")
        except Exception as e:
            errors.append(str(e))

        # Update sprint state
        sprint.set_status("in_progress")
        sprint.update_task(1, status="done")  # directory geometry established
        sprint.update_task(2, status="done")  # ΛΦ constants injected
        self._save_sprint(sprint)

        h = self._ledger.append("AIDEN_MANIFEST", {
            "sprint_id": sprint.id,
            "name":      sprint.name,
            "path":      str(base),
            "errors":    errors,
        })

        if errors:
            print(f"\n  {_YE}⚠ {len(errors)} error(s) during manifest.{_R}")
        else:
            print(f"\n  {_GR}{_H}✓ Substrate locked.{_R}  PCRB: {h[:16]}…")

        # Shadow swarm: queue completion passes for all manifested Python files
        try:
            from .shadow_swarm import get_swarm
            from .apprentice import get_apprentice
            # Observe task decomposition
            get_apprentice().observe_task_decomposition(
                goal=sprint.name,
                subtasks=[t["task"] for t in sprint.backlog],
                agent_map={t["task"]: t.get("agent", "AIDEN") for t in sprint.backlog},
                outcome="in_progress",
                source="agile_plan",
            )
            # Queue swarm for all Python files
            get_swarm().observe_sprint(str(base), intent=sprint.name, sprint_id=sprint.id)
        except Exception:
            pass

        print(f"\n  {_CY}cd {base}{_R}")
        print(f"  {_D}Run 'osiris agile status' to track progress.{_R}")
        print(f"  {_D}Run 'osiris swarm status' to see completion queue.{_R}\n")
        return not errors

    def status(self, sprint_id: Optional[str] = None) -> None:
        """Display kanban board for one sprint or all sprints."""
        sprints = ([self._load_sprint(sprint_id)]
                   if sprint_id else self._all_sprints())
        sprints = [s for s in sprints if s is not None]

        if not sprints:
            print(f"\n  {_D}No active sprints in STM. Run 'osiris agile plan <intent>'.{_R}\n")
            return

        print(_header("◈ Sovereign Task Manifold (STM)",
                      f"Workspace: {self.workspace}", _MG))

        for sprint in sprints:
            s_icon = _status_icon(sprint.status)
            print(f"\n  {_H}{sprint.name}{_R}  {s_icon} {_D}{sprint.status}{_R}"
                  f"  {_D}[{sprint.id}]{_R}  {_D}{Path(sprint.path).as_posix()}{_R}")
            if sprint.tags:
                print(f"  {_D}tags: {', '.join(sprint.tags)}{_R}")

            # Kanban columns
            cols: Dict[str, List] = {"pending": [], "in_progress": [], "done": [], "blocked": []}
            for t in sprint.backlog:
                cols.get(t["status"], cols["pending"]).append(t)

            col_w = 20
            header_row = (
                f"  {_YE}{_H}{'PENDING':<{col_w}}{_R}"
                f"  {_CY}{_H}{'IN PROGRESS':<{col_w}}{_R}"
                f"  {_GR}{_H}{'DONE':<{col_w}}{_R}"
                f"  {_RD}{_H}{'BLOCKED':<{col_w}}{_R}"
            )
            print(f"\n{header_row}")
            print(f"  {'─'*col_w}  {'─'*col_w}  {'─'*col_w}  {'─'*col_w}")

            max_rows = max(len(v) for v in cols.values()) if cols else 0
            col_keys = ["pending", "in_progress", "done", "blocked"]
            for i in range(max_rows):
                row = ""
                for k in col_keys:
                    if i < len(cols[k]):
                        t   = cols[k][i]
                        txt = f"[{t['id']}] {t['task']}"
                        txt = txt[:col_w - 1] if len(txt) > col_w - 1 else txt
                        row += f"  {txt:<{col_w}}"
                    else:
                        row += f"  {' ':<{col_w}}"
                print(row)

        # PCRB tail
        print(f"\n  {_D}{'─'*68}{_R}")
        entries = self._ledger.tail(5)
        if entries:
            print(f"  {_D}PCRB (last {len(entries)} events):{_R}")
            for e in entries:
                t = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
                print(f"  {_D}{t}  {e['action']:<28}  {e['hash'][:12]}…{_R}")
        print()

    def update(self, sprint_id: str, task_id: int, new_status: str,
               note: str = "") -> bool:
        """Update a task's status within a sprint."""
        sprint = self._load_sprint(sprint_id)
        if sprint is None:
            print(f"  {_RD}Sprint '{sprint_id}' not found.{_R}")
            return False
        if new_status not in Sprint.TASK_STATUS:
            print(f"  {_RD}Invalid status. Use: {', '.join(Sprint.TASK_STATUS)}{_R}")
            return False

        ok = sprint.update_task(task_id, status=new_status,
                                note=note, updated=round(time.time(), 2))
        if ok:
            self._save_sprint(sprint)
            h = self._ledger.append("TASK_UPDATE", {
                "sprint_id": sprint.id,
                "task_id":   task_id,
                "status":    new_status,
                "note":      note,
            })
            print(f"  {_GR}✓{_R} Task {task_id} → {new_status}  PCRB: {h[:12]}…")
        else:
            print(f"  {_RD}Task {task_id} not found.{_R}")
        return ok

    def add_task(self, sprint_id: str, title: str, agent: str = "AIDEN") -> bool:
        """Add a new task to an existing sprint's backlog."""
        sprint = self._load_sprint(sprint_id)
        if sprint is None:
            print(f"  {_RD}Sprint '{sprint_id}' not found.{_R}")
            return False
        task = sprint.add_task(title, agent=agent.upper())
        self._save_sprint(sprint)
        h = self._ledger.append("TASK_ADDED", {
            "sprint_id": sprint.id,
            "task_id":   task["id"],
            "title":     title,
            "agent":     agent,
        })
        print(f"  {_GR}✓{_R} Task [{task['id']}] added → {title}  {_agent_colour(agent)}"
              f"  PCRB: {h[:12]}…")
        return True

    def deploy(self, sprint_id: str, target: str = "vercel") -> str:
        """Trigger deployment of the project via existing OSIRIS deploy tools."""
        sprint = self._load_sprint(sprint_id)
        if sprint is None:
            return f"{_RD}Sprint '{sprint_id}' not found.{_R}"
        try:
            from .tools import tool_vercel_deploy, tool_shell
            print(_header(f"Deploying {sprint.name}", f"Target: {target}", _BL))
            if target == "vercel":
                result = tool_vercel_deploy(cwd=str(sprint.path))
            else:
                result = tool_shell(f"cd {sprint.path} && {target}", timeout=120)
            self._ledger.append("DEPLOY", {
                "sprint_id": sprint.id,
                "target":    target,
            })
            return result
        except Exception as e:
            return f"{_RD}Deploy error: {e}{_R}"

    def scan(self, root: Optional[str] = None) -> List[Dict]:
        """
        Discover existing projects under root that have an .osiris_manifest.json.
        Register them in STM if not already present.
        """
        search_root = Path(root or self.workspace)
        found = []
        existing_ids = {s.id for s in self._all_sprints()}
        existing_names = {s.name for s in self._all_sprints()}

        for manifest_path in search_root.rglob(".osiris_manifest.json"):
            try:
                data = json.loads(manifest_path.read_text())
                proj = Sprint.from_dict(data)
                if proj.id not in existing_ids and proj.name not in existing_names:
                    self._save_sprint(proj)
                    self._ledger.append("SCAN_IMPORT", {
                        "sprint_id": proj.id,
                        "name":      proj.name,
                        "path":      str(manifest_path.parent),
                    })
                    found.append(data)
                    print(f"  {_GR}✓{_R} Imported: {proj.name} [{proj.id}]")
            except Exception:
                pass

        if not found:
            print(f"  {_D}No new projects found under {search_root}{_R}")
        return found

    def ledger(self, n: int = 20) -> None:
        """Print last N PCRB entries."""
        entries = self._ledger.tail(n)
        print(_header("◈ PCRB Ledger", f"{self._ledger.path}", _CY))
        if not entries:
            print(f"  {_D}No entries yet.{_R}")
        for e in entries:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["ts"]))
            print(f"  {_D}{t}{_R}  {_CY}{e['action']:<30}{_R}  "
                  f"{_D}{e['hash'][:16]}…{_R}")
        print()

    # ── Interactive REPL ──────────────────────────────────────────────────────

    _HELP = f"""\
  {_H}STM Interactive Commands{_R}
  {'─'*56}
  {_CY}plan{_R}   <intent>          AURA: plan a new project
  {_CY}create{_R} <id|name>         AIDEN: manifest the directory substrate
  {_CY}status{_R} [id]              Show kanban board
  {_CY}update{_R} <id> <task#> <status>  Update task status
  {_CY}add{_R}    <id> <task title> Add task to sprint
  {_CY}deploy{_R} <id> [target]     Deploy project
  {_CY}scan{_R}   [path]            Discover existing OSIRIS projects
  {_CY}ledger{_R} [n]               Show PCRB audit trail
  {_CY}list{_R}                     List all sprints
  {_CY}help{_R}                     This menu
  {_CY}exit{_R}  / quit / q        Exit STM
"""

    def interactive(self) -> None:
        """Non-local interactive agent session."""
        print(_header(
            "∮ Sovereign Task Manifold — Interactive",
            f"Workspace: {self.workspace}  |  STM v{STM_VERSION}",
            _MG,
        ))
        print(f"  {_D}Type 'help' for commands. Ctrl-C or 'exit' to quit.{_R}\n")

        while True:
            try:
                try:
                    raw = input(f"  {_MG}{_H}STM{_R}{_CY}❯{_R} ").strip()
                except EOFError:
                    break
                if not raw:
                    continue

                parts = raw.split(None, 1)
                verb  = parts[0].lower()
                rest  = parts[1] if len(parts) > 1 else ""

                if verb in ("exit", "quit", "q"):
                    break
                elif verb == "help":
                    print(self._HELP)
                elif verb == "plan":
                    if rest:
                        self.plan(rest)
                    else:
                        print(f"  {_YE}Usage: plan <intent>{_R}")
                elif verb == "create":
                    if rest:
                        self.create(rest.split()[0])
                    else:
                        print(f"  {_YE}Usage: create <sprint-id|name>{_R}")
                elif verb == "status":
                    self.status(rest.split()[0] if rest else None)
                elif verb == "list":
                    self.status()
                elif verb == "update":
                    p = rest.split(None, 2)
                    if len(p) >= 3:
                        note = p[3] if len(p) > 3 else ""
                        try:
                            self.update(p[0], int(p[1]), p[2], note)
                        except ValueError:
                            print(f"  {_RD}task# must be an integer.{_R}")
                    else:
                        print(f"  {_YE}Usage: update <sprint-id> <task#> <status>{_R}")
                elif verb == "add":
                    p = rest.split(None, 1)
                    if len(p) == 2:
                        self.add_task(p[0], p[1])
                    else:
                        print(f"  {_YE}Usage: add <sprint-id> <task title>{_R}")
                elif verb == "deploy":
                    p = rest.split(None, 1)
                    if p:
                        target = p[1] if len(p) > 1 else "vercel"
                        print(self.deploy(p[0], target))
                    else:
                        print(f"  {_YE}Usage: deploy <sprint-id> [vercel|docker|...]{_R}")
                elif verb == "scan":
                    self.scan(rest.strip() or None)
                elif verb == "ledger":
                    n = int(rest.strip()) if rest.strip().isdigit() else 20
                    self.ledger(n)
                else:
                    print(f"  {_D}Unknown command '{verb}'. Type 'help'.{_R}")

            except KeyboardInterrupt:
                print(f"\n  {_D}(Ctrl-C — type 'exit' to quit){_R}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLI entry-point  (also called from osiris binary)
# ══════════════════════════════════════════════════════════════════════════════

def main(args: Optional[List[str]] = None) -> None:
    args = args if args is not None else sys.argv[1:]
    mesh = AgileMesh()

    if not args:
        mesh.interactive()
        return

    verb = args[0].lower()
    rest = args[1:]

    if verb == "plan":
        intent = " ".join(rest)
        if not intent:
            print(f"  {_YE}Usage: osiris agile plan <intent>{_R}")
            return
        mesh.plan(intent)

    elif verb == "create":
        if not rest:
            print(f"  {_YE}Usage: osiris agile create <sprint-id|name>{_R}")
            return
        mesh.create(rest[0])

    elif verb in ("status", "board"):
        mesh.status(rest[0] if rest else None)

    elif verb == "list":
        mesh.status()

    elif verb == "update":
        if len(rest) < 3:
            print(f"  {_YE}Usage: osiris agile update <sprint-id> <task#> <status>{_R}")
            return
        try:
            mesh.update(rest[0], int(rest[1]), rest[2],
                        note=" ".join(rest[3:]) if len(rest) > 3 else "")
        except ValueError:
            print(f"  {_RD}task# must be an integer.{_R}")

    elif verb == "add":
        if len(rest) < 2:
            print(f"  {_YE}Usage: osiris agile add <sprint-id> <task title>{_R}")
            return
        mesh.add_task(rest[0], " ".join(rest[1:]))

    elif verb == "deploy":
        if not rest:
            print(f"  {_YE}Usage: osiris agile deploy <sprint-id> [target]{_R}")
            return
        target = rest[1] if len(rest) > 1 else "vercel"
        print(mesh.deploy(rest[0], target))

    elif verb == "scan":
        mesh.scan(rest[0] if rest else None)

    elif verb == "ledger":
        n = int(rest[0]) if rest and rest[0].isdigit() else 20
        mesh.ledger(n)

    elif verb in ("interact", "interactive", "repl"):
        mesh.interactive()

    elif verb in ("help", "--help", "-h"):
        print(AgileMesh._HELP)

    else:
        print(f"  {_RD}Unknown subcommand: {verb}{_R}")
        print(f"  {_D}Use: plan | create | status | update | add | deploy | scan | ledger | interact{_R}")


if __name__ == "__main__":
    main()
