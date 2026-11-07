"""Command policy for the OSIRIS execution kernel: normalization and classification.

``classify`` is pure apart from reading the policy file and calling ``shutil.which`` and
``os.path.realpath``. Nothing in this module spawns a process. The rules live in
``osiris_cli/policy/exec_policy.json``; the code here only applies them.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

ORIGINS = ("human", "model", "skill", "claude_code")
AGENT_ORIGINS = ("model", "skill", "claude_code")
TIERS = ("READ", "VERIFY", "MUTATE", "NETWORK", "FORBIDDEN")
DECISIONS = ("ALLOW", "ASK", "DENY")
_TIER_RANK = {tier: rank for rank, tier in enumerate(TIERS)}
_POLICY_PATH = Path(__file__).resolve().parent / "policy" / "exec_policy.json"
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NON_PLAIN_ASCII = re.compile(r"[\x00-\x1f\x7f]|[^\x00-\x7f]")
_PYTHON_NAME = re.compile(r"^python(3(\.\d+)*)?$")


class PolicyError(RuntimeError):
    """The policy file is missing or malformed. Callers must treat this as a refusal."""


@dataclass(frozen=True)
class CommandRequest:
    argv: Tuple[str, ...]
    cwd: str
    origin: str  # "human" | "model" | "skill" | "claude_code"
    timeout_s: Optional[float] = None
    skill: Optional[str] = None  # set when origin == "skill"
    root: Optional[str] = None  # confinement root for cwd; None means the checkout root


@dataclass(frozen=True)
class Classification:
    tier: str  # READ | VERIFY | MUTATE | NETWORK | FORBIDDEN
    decision: str  # ALLOW | ASK | DENY
    reasons: Tuple[str, ...]
    normalized_argv: Tuple[str, ...]
    policy_sha256: str


@dataclass
class _Verdict:
    tier: str = "MUTATE"
    agent_deny: bool = False  # DENY for model/skill/claude_code, ASK for human
    hard: bool = False  # DENY for every origin
    sensitive: bool = False  # output must never be logged; human may ASK
    reasons: List[str] = field(default_factory=list)
    unknown: bool = False  # no rule matched; the default MUTATE


_SYSTEM_DIRS = ("/usr/bin/", "/bin/", "/usr/sbin/", "/sbin/", "/usr/lib/", "/usr/libexec/")


_POLICY_CACHE: Optional[Tuple[dict, str]] = None


def load_policy() -> Tuple[dict, str]:
    """Return (policy dict, sha256 of the policy file bytes). Fails closed with PolicyError."""
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        try:
            raw = _POLICY_PATH.read_bytes()
        except OSError as exc:
            raise PolicyError(f"execution policy unreadable ({_POLICY_PATH.name}): {exc}") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise PolicyError("execution policy is not valid JSON") from exc
        _validate_policy(data)
        _POLICY_CACHE = (data, hashlib.sha256(raw).hexdigest())
    return _POLICY_CACHE


def _validate_policy(data: dict) -> None:
    tiers = data.get("tiers")
    if not isinstance(tiers, dict) or set(tiers) != set(TIERS):
        raise PolicyError("execution policy must define exactly the five tiers")
    for tier, row in tiers.items():
        if not isinstance(row, dict) or set(row) != {"human", "agent"}:
            raise PolicyError(f"tier {tier} must define human and agent decisions")
        for key in ("human", "agent"):
            if row[key] not in ("ALLOW", "ASK", "ASK_ONCE", "DENY"):
                raise PolicyError(f"tier {tier} has an unknown decision: {row[key]!r}")
    for key in ("shell_operator_tokens", "shells", "forbidden_programs", "git", "secrets", "env",
                "wrappers", "output", "grant_ttl_s", "kill_grace_s"):
        if key not in data:
            raise PolicyError(f"execution policy is missing {key!r}")


def default_root() -> str:
    """The checkout root. Commands may only run with a cwd inside it unless the request says otherwise."""
    return os.path.realpath(str(Path(__file__).resolve().parents[1]))


def scrubbed_env(parent: Mapping[str, str]) -> Dict[str, str]:
    """Allowlisted child environment. Secret-shaped names are dropped even when allowlisted."""
    pol, _ = load_policy()
    env_pol = pol["env"]
    allow = set(env_pol["allow"])
    prefixes = tuple(env_pol["allow_prefixes"])
    deny_re = re.compile(env_pol["deny_regex"])
    deny_names = set(env_pol["deny_names"])
    deny_globs = list(env_pol["deny_globs"])
    out: Dict[str, str] = {}
    for name, value in parent.items():
        if not (name in allow or name.startswith(prefixes)):
            continue
        if name in deny_names or deny_re.search(name):
            continue
        if any(fnmatch.fnmatchcase(name, glob) for glob in deny_globs):
            continue
        out[name] = value
    return out


def is_sensitive_argv(argv: Sequence[str]) -> bool:
    """True when the command's output may carry a credential and must not be stored or echoed."""
    pol, _ = load_policy()
    if not argv:
        return False
    if os.path.basename(argv[0]) != "gcloud":
        return False
    return any(tok in pol["gcloud_sensitive_args"] for tok in argv[1:])


def classify(req: CommandRequest) -> Classification:
    """Normalize ``req.argv`` and decide ALLOW, ASK or DENY for its origin. Pure apart from FS reads."""
    pol, sha = load_policy()
    raw = req.argv if isinstance(req.argv, (tuple, list)) else ()

    def refuse(reasons: Sequence[str], normalized: Sequence[str] = ()) -> Classification:
        return Classification("FORBIDDEN", "DENY", tuple(reasons),
                              tuple(normalized) if normalized else tuple(str(t) for t in raw), sha)

    if req.origin not in ORIGINS:
        return refuse([f"unknown origin {req.origin!r}"])
    if not raw or not all(isinstance(t, str) for t in raw):
        return refuse(["argv must be a non-empty list of strings"])
    argv: Tuple[str, ...] = tuple(raw)
    if _NON_PLAIN_ASCII.search(argv[0]):
        return refuse(["argv[0] contains control or non-ASCII characters"])
    if any("\x00" in tok for tok in argv):
        return refuse(["NUL byte in argv"])
    markers = tuple(pol["shell_substitution_markers"])
    if any(tok in pol["shell_operator_tokens"] or any(m in tok for m in markers) for tok in argv):
        return refuse(["one program, no shell: shell operator or substitution token"])
    if _ENV_ASSIGN.match(argv[0]):
        return refuse(["environment assignment before the program is not allowed"])
    if not os.path.isdir(req.cwd):
        return refuse(["cwd is not a directory"])
    root = os.path.realpath(req.root) if req.root else default_root()
    cwd = os.path.realpath(req.cwd)
    if not _inside(cwd, root):
        return refuse([f"cwd {cwd} is outside the execution root"])
    if any(_is_secret(tok, cwd, pol) for tok in argv):
        return refuse(["an argument resolves to a secret path"])
    if any(_is_ledger(tok, pol) for tok in argv):
        return refuse(["writes or reads a ledger database"])

    inner, wrappers, error = _unwrap(argv, pol)
    if error:
        return refuse([error])
    path_env = scrubbed_env(os.environ).get("PATH", "")
    resolved = _resolve_program(inner[0], cwd, path_env)
    given = os.path.basename(inner[0])
    verdict = _rules((given,) + inner[1:], pol)
    if resolved:
        target = os.path.realpath(resolved)
        target_name = os.path.basename(target)
        if target_name != given:
            # A symlink named ls that points at rm must be judged as rm. An unknown name inside a
            # system directory is a distribution alternative (which -> which.debianutils), not a risk.
            current = _rules((target_name,) + inner[1:], pol)
            if not (current.unknown and target.startswith(_SYSTEM_DIRS)):
                verdict = _merge(verdict, current)
    if any(tok in pol["publish_flags"] for tok in inner):
        verdict = _merge(verdict, _Verdict(agent_deny=True, reasons=["publish flag"]))
    if wrappers:
        verdict.reasons.insert(0, "classified the program inside " + " -> ".join(wrappers))
    normalized = ((resolved or inner[0]),) + inner[1:]
    return _decide(verdict, req.origin, pol, sha, normalized)


def _decide(v: _Verdict, origin: str, pol: dict, sha: str, normalized: Tuple[str, ...]) -> Classification:
    reasons = list(v.reasons) or ["no rule matched; unknown program"]
    if v.hard:
        return Classification("FORBIDDEN", "DENY", tuple(reasons), normalized, sha)
    agent = origin in AGENT_ORIGINS
    if v.sensitive:
        decision = "DENY" if agent else "ASK"
        reasons.append("credential-bearing command: output is never logged")
        return Classification("FORBIDDEN", decision, tuple(reasons), normalized, sha)
    if agent and v.agent_deny:
        return Classification(v.tier, "DENY", tuple(reasons), normalized, sha)
    row = pol["tiers"][v.tier]
    setting = row["agent"] if agent else row["human"]
    if setting == "ASK_ONCE":
        reasons.append("ask once per session per program")
        return Classification(v.tier, "ASK", tuple(reasons), normalized, sha)
    return Classification(v.tier, setting, tuple(reasons), normalized, sha)


def _merge(a: _Verdict, b: _Verdict) -> _Verdict:
    tier = a.tier if _TIER_RANK[a.tier] >= _TIER_RANK[b.tier] else b.tier
    if a.hard or b.hard:
        tier = "FORBIDDEN"
    return _Verdict(tier=tier, agent_deny=a.agent_deny or b.agent_deny, hard=a.hard or b.hard,
                    sensitive=a.sensitive or b.sensitive, reasons=a.reasons + b.reasons,
                    unknown=a.unknown and b.unknown)


def _hard(reason: str) -> _Verdict:
    return _Verdict(tier="FORBIDDEN", hard=True, reasons=[reason])


def _agent_deny(tier: str, reason: str) -> _Verdict:
    return _Verdict(tier=tier, agent_deny=True, reasons=[reason])


def _inside(path: str, root: str) -> bool:
    base = root.rstrip(os.sep) + os.sep
    return path == root or path.startswith(base)


def _is_secret(token: str, cwd: str, pol: dict) -> bool:
    sec = pol["secrets"]
    expanded = os.path.expanduser(token)
    base = os.path.basename(expanded.rstrip("/"))
    if re.match(sec["name_regex"], base):
        return True
    if base in sec["names"] or base.endswith(tuple(sec["suffixes"])):
        return True
    if re.search(sec["service_account_regex"], base):
        return True
    resolved = os.path.realpath(expanded if os.path.isabs(expanded) else os.path.join(cwd, expanded))
    parts = resolved.split(os.sep)
    for seq in sec["path_sequences"]:
        n = len(seq)
        if any(parts[i:i + n] == seq for i in range(len(parts) - n + 1)):
            return True
    return any(part in sec["dir_names"] for part in parts)


def _is_ledger(token: str, pol: dict) -> bool:
    return bool(re.search(pol["ledger_regex"], os.path.basename(token)))


def _unwrap(argv: Tuple[str, ...], pol: dict) -> Tuple[Tuple[str, ...], List[str], Optional[str]]:
    wrappers = pol["wrappers"]
    cur = list(argv)
    seen: List[str] = []
    while cur and os.path.basename(cur[0]) in wrappers:
        if len(seen) >= pol["max_wrapper_depth"]:
            return tuple(cur), seen, "wrapper nesting too deep"
        name = os.path.basename(cur[0])
        spec = wrappers[name]
        i = 1
        while i < len(cur) and cur[i].startswith("-") and cur[i] != "--":
            i += 2 if cur[i] in spec["value_options"] else 1
        if i < len(cur) and cur[i] == "--":
            i += 1
        i += spec["positionals"]
        if i >= len(cur):
            return tuple(cur), seen, f"{name} wrapper has no program to run"
        seen.append(name)
        cur = cur[i:]
    if not cur:
        return tuple(argv), seen, "empty command after unwrapping"
    return tuple(cur), seen, None


def _resolve_program(name: str, cwd: str, path_env: str) -> Optional[str]:
    if "/" in name:
        candidate = name if os.path.isabs(name) else os.path.join(cwd, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            # Keep the path as given (not realpath) so venv interpreters keep their pyvenv.cfg.
            return os.path.abspath(candidate)
        return None
    found = shutil.which(name, path=path_env or None)
    return os.path.abspath(found) if found else None


def _rules(args: Tuple[str, ...], pol: dict) -> _Verdict:
    """Rules for one program name plus its arguments. args[0] is the program name."""
    name = os.path.basename(args[0])
    rest = list(args[1:])

    if name in pol["forbidden_programs"]:
        return _hard(f"{name} is forbidden")
    if name in pol["launcher_programs"]:
        if name == "env" and not rest:
            return _hard("bare env prints the environment")
        return _hard(f"{name} is not allowed as a launcher")
    if name in pol["network_scripts"]:
        return _Verdict(tier="NETWORK", reasons=[f"{name} submits to a remote service"])
    if _matches(name, pol["publish_script_patterns"]):
        return _agent_deny("MUTATE", f"{name} is a publish script")
    if name in pol["verify_scripts"]:
        return _Verdict(tier="VERIFY", reasons=[f"{name} verification script"])
    if name in pol["shells"] or name in pol["opaque_builtins"]:
        return _agent_deny("MUTATE", f"{name} is an opaque shell or builtin")
    inline_patterns = pol["inline_flag_patterns"].get(name, [])
    if any(re.match(pat, tok) for tok in rest for pat in inline_patterns):
        return _agent_deny("MUTATE", f"{name} inline code flag is opaque")
    if name == "busybox":
        if rest and os.path.basename(rest[0]) in pol["shells"]:
            return _agent_deny("MUTATE", "busybox shell applet is opaque")
        return _Verdict(tier="MUTATE", reasons=["busybox applet"])
    if _PYTHON_NAME.match(name):
        return _python(rest, pol)
    if name == "pip" or name == "pip3":
        return _pip(rest, pol)
    if name == "git":
        return _git(rest, pol["git"])
    if name == "gh":
        return _gh(rest, pol["gh_read"])
    if name == "gcloud":
        if any(tok in pol["gcloud_sensitive_args"] for tok in rest):
            return _Verdict(tier="FORBIDDEN", sensitive=True, reasons=["gcloud credential print"])
        return _Verdict(tier="NETWORK", reasons=["gcloud reaches a cloud service"])
    if name == "ollama":
        if rest and rest[0] in pol["ollama_network_subcommands"]:
            return _Verdict(tier="NETWORK", reasons=["ollama pull downloads a model"])
        return _Verdict(tier="MUTATE", reasons=["ollama subcommand not on the read list"])
    if name in pol["verify_programs"]:
        return _Verdict(tier="VERIFY", reasons=[f"{name} verification run"])
    if name == "ruff":
        return _ruff(rest, pol)
    if name == "find":
        if any(tok in pol["find_exec_flags"] or any(tok.startswith(p) for p in pol["find_exec_prefixes"])
               for tok in rest):
            return _agent_deny("MUTATE", "find with -exec, -ok, -delete or -fprint runs or writes")
        return _Verdict(tier="READ", reasons=["find without exec or delete"])
    if name in pol["read_with_output_guard"]:
        guards = pol["read_with_output_guard"][name]
        if any(tok.startswith(g) for tok in rest for g in guards):
            return _Verdict(tier="MUTATE", reasons=[f"{name} writes an output file"])
        return _Verdict(tier="READ", reasons=[f"{name} read"])
    if name in pol["read_programs"]:
        return _Verdict(tier="READ", reasons=[f"{name} read"])
    if name in pol["network_programs"]:
        return _Verdict(tier="NETWORK", reasons=[f"{name} reaches a host"])
    if _matches(name, pol["delete_programs"]):
        return _agent_deny("MUTATE", f"{name} deletes or overwrites data")
    if name in pol["mode_programs"]:
        if any(tok in pol["mode_recursive_flags"] for tok in rest):
            return _agent_deny("MUTATE", f"{name} -R changes a whole tree")
        return _Verdict(tier="MUTATE", reasons=[f"{name} changes modes"])
    return _Verdict(tier="MUTATE", reasons=[f"{name} is not on any known list"], unknown=True)


def _matches(name: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pat) for pat in patterns)


def _python(rest: List[str], pol: dict) -> _Verdict:
    inline = re.compile(pol["python_inline_flag_regex"])
    value_flags = set(pol["python_value_flags"])
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "-m":
            module = rest[i + 1] if i + 1 < len(rest) else ""
            return _python_module(module, rest[i + 2:], pol)
        if tok == "-c" or tok == "-" or inline.match(tok):
            return _agent_deny("MUTATE", "inline interpreter code is opaque")
        if tok in ("-V", "--version"):
            return _Verdict(tier="READ", reasons=["python version"])
        if tok in value_flags:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return _script_verdict(tok, pol)
    return _agent_deny("MUTATE", "interactive interpreter is opaque")


def _script_verdict(script: str, pol: dict) -> _Verdict:
    """A repo script run by path. Its name never inherits the tier of a same-named program."""
    base = os.path.basename(script)
    if base in pol["network_scripts"]:
        return _Verdict(tier="NETWORK", reasons=[f"{base} submits to a remote service"])
    if _matches(base, pol["publish_script_patterns"]):
        return _agent_deny("MUTATE", f"{base} is a publish script")
    if base in pol["verify_scripts"]:
        return _Verdict(tier="VERIFY", reasons=[f"{base} verification script"])
    return _Verdict(tier="MUTATE", reasons=[f"{base} is a script run by path"])


def _python_module(module: str, after: List[str], pol: dict) -> _Verdict:
    if module in pol["python_verify_modules"]:
        return _Verdict(tier="VERIFY", reasons=[f"python -m {module}"])
    if module == "pip":
        return _pip(after, pol)
    if module == "ruff":
        return _ruff(after, pol)
    return _Verdict(tier="MUTATE", reasons=[f"python -m {module or '<none>'} is not on the verify list"])


def _pip(rest: List[str], pol: dict) -> _Verdict:
    if rest and rest[0] in pol["pip_read_subcommands"]:
        return _Verdict(tier="READ", reasons=["pip listing"])
    return _Verdict(tier="NETWORK", reasons=["pip may install or download packages"])


def _ruff(rest: List[str], pol: dict) -> _Verdict:
    if rest and rest[0] in pol["ruff_verify_subcommands"]:
        if any(tok.startswith(p) for tok in rest for p in pol["ruff_fix_prefixes"]):
            return _Verdict(tier="MUTATE", reasons=["ruff with a fix flag writes files"])
        return _Verdict(tier="VERIFY", reasons=["ruff check without --fix"])
    return _Verdict(tier="MUTATE", reasons=["ruff subcommand is not check"])


def _gh(rest: List[str], gh_read: Dict[str, List[str]]) -> _Verdict:
    words = [tok for tok in rest if not tok.startswith("-")]
    if len(words) >= 2 and words[1] in gh_read.get(words[0], []):
        return _Verdict(tier="NETWORK", reasons=["gh read-only query"])
    return _Verdict(tier="NETWORK", agent_deny=True, reasons=["gh write or publish operation"])


def _git(rest: List[str], g: dict) -> _Verdict:
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "-c":
            key = rest[i + 1].split("=", 1)[0].lower() if i + 1 < len(rest) else ""
            if not key or any(fnmatch.fnmatchcase(key, pat.lower()) for pat in g["denied_config_keys"]):
                return _hard(f"git -c {key or '<missing>'} can run code")
            i += 2
            continue
        if tok in g["global_value_options"]:
            i += 2
            continue
        if any(tok.startswith(opt + "=") for opt in g["global_value_options"]):
            i += 1
            continue
        if tok in g["global_flag_options"]:
            i += 1
            continue
        break
    if i >= len(rest):
        return _Verdict(tier="READ", reasons=["git with no subcommand"])
    sub = rest[i]
    sargs = rest[i + 1:]
    if sub in g["read"]:
        if sub == "diff":
            if any(tok in g["diff_verify_flags"] for tok in sargs):
                return _Verdict(tier="VERIFY", reasons=["git diff --check"])
            if any(tok.startswith(p) for tok in sargs for p in g["diff_output_prefixes"]):
                return _Verdict(tier="MUTATE", reasons=["git diff --output writes a file"])
        return _Verdict(tier="READ", reasons=[f"git {sub} read"])
    if sub == "branch":
        return _git_branch(sargs, g)
    if sub == "stash" and sargs and sargs[0] in g["stash_read"]:
        return _Verdict(tier="READ", reasons=[f"git stash {sargs[0]}"])
    if sub in g["network"]:
        return _Verdict(tier="NETWORK", reasons=[f"git {sub} reaches a remote"])
    if sub in g["write"]:
        return _agent_deny("MUTATE", f"git write operation: {sub}")
    return _Verdict(tier="MUTATE", reasons=[f"unknown git subcommand {sub} (may be an alias)"])


def _git_branch(sargs: List[str], g: dict) -> _Verdict:
    i = 0
    while i < len(sargs):
        tok = sargs[i]
        if tok in g["branch_list_value_flags"]:
            i += 2
            continue
        if tok in g["branch_list_flags"] or any(tok.startswith(p) for p in g["branch_list_prefixes"]):
            i += 1
            continue
        return _agent_deny("MUTATE", "git branch that creates, renames or deletes")
    return _Verdict(tier="READ", reasons=["git branch listing"])
