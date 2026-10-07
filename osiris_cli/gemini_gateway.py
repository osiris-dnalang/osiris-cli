"""Gemini (Vertex express) gateway: the only path from OSIRIS work to the Google API.

Rules it enforces:
  * the key comes from ~/.env (parsed, never sourced) and is never logged or returned;
  * every outbound prompt is redacted first (secret-shaped strings, and any value held in ~/.env);
  * only allow-listed models; a hard token budget persisted across runs;
  * a hash-chained ledger row is written BEFORE the call and a result row AFTER it;
  * it is advisory tooling: nothing here may sit in a verifier, scoring or training-label path.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
ENV_PATH = os.path.join(HOME, ".env")
STATE_DIR = os.path.join(HOME, ".osiris")
LEDGER_PATH = os.path.join(STATE_DIR, "gemini_gateway_ledger.jsonl")
BUDGET_PATH = os.path.join(STATE_DIR, "gemini_gateway_budget.json")
ENDPOINT = "https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"
ALLOWED_MODELS = ("gemini-2.5-pro", "gemini-2.5-flash")   # probed 2026-10-07; 3.x returned 404
DEFAULT_TOKEN_BUDGET = 2_000_000                            # total tokens (prompt + output + thinking)
GENESIS = "0" * 64

_SECRET_SHAPES = [
    (re.compile(r"AIza[0-9A-Za-z_-]{20,}"), "google-api-key"),
    (re.compile(r"\bAQ\.[0-9A-Za-z_-]{20,}"), "google-agent-key"),
    (re.compile(r"\bgh[pousr]_[0-9A-Za-z]{20,}"), "github-token"),
    (re.compile(r"\bsk-[0-9A-Za-z_-]{20,}"), "sk-key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws-access-key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private-key"),
    (re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s'\"]+:[^\s'\"@]+@[^\s'\"]+"), "db-url-with-password"),
    (re.compile(r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSW\w*|CREDENTIAL)[A-Z0-9_]*\s*=\s*\S{8,}"), "secret-assignment"),
]


def load_env(path=ENV_PATH):
    """Parse KEY=VALUE lines (no shell evaluation). Commented-out lines are ignored."""
    out = {}
    try:
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.rstrip("\n"))
            if m:
                v = m.group(2).strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                    v = v[1:-1]
                out[m.group(1)] = v
    except OSError:
        pass
    return out


def redact(text, env=None):
    """Return (clean_text, findings). Findings carry type and count only, never values."""
    findings = {}
    env = load_env() if env is None else env
    for name, val in env.items():
        if len(val) >= 8 and val in text:
            findings[f"env:{name}"] = text.count(val)
            text = text.replace(val, f"[REDACTED:{name}]")
    for rx, kind in _SECRET_SHAPES:
        text, n = rx.subn(f"[REDACTED:{kind}]", text)
        if n:
            findings[kind] = findings.get(kind, 0) + n
    return text, findings


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path=LEDGER_PATH):
        self.path = path

    def _tip(self):
        tip = GENESIS
        try:
            for line in open(self.path, encoding="utf-8"):
                if line.strip():
                    tip = json.loads(line)["hash"]
        except OSError:
            pass
        return tip

    def append(self, kind, payload):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        entry = {"kind": kind, "payload": payload, "prev": self._tip(),
                 "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        entry["hash"] = _sha(_canon({k: entry[k] for k in ("kind", "payload", "prev", "ts")}))
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry

    def verify(self):
        prev = GENESIS
        for i, line in enumerate(open(self.path, encoding="utf-8")) if os.path.exists(self.path) else []:
            e = json.loads(line)
            body = {k: e[k] for k in ("kind", "payload", "prev", "ts")}
            if e["prev"] != prev or e["hash"] != _sha(_canon(body)):
                return False, f"entry {i}: chain broken"
            prev = e["hash"]
        return True, "ok"


class Budget:
    def __init__(self, path=BUDGET_PATH, limit=DEFAULT_TOKEN_BUDGET):
        self.path, self.limit = path, limit

    def used(self):
        try:
            return int(json.load(open(self.path))["tokens"])
        except (OSError, ValueError, KeyError):
            return 0

    def add(self, n):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"tokens": self.used() + int(n), "limit": self.limit}, f)

    def check(self, planned):
        if self.used() + planned > self.limit:
            raise BudgetExceeded(f"token budget {self.limit} would be exceeded (used {self.used()}, planned {planned})")


class BudgetExceeded(RuntimeError):
    pass


class GatewayError(RuntimeError):
    pass


def _post(url, headers, body, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def generate(prompt, *, purpose, model="gemini-2.5-flash", system=None, max_output_tokens=2048,
             temperature=0.0, dry_run=False, transport=_post, ledger=None, budget=None, env=None):
    """One audited call. `purpose` is a required free-text reason recorded in the ledger."""
    if model not in ALLOWED_MODELS:
        raise GatewayError(f"model {model!r} not allow-listed: {ALLOWED_MODELS}")
    if not purpose.strip():
        raise GatewayError("a purpose is required")
    env = load_env() if env is None else env
    ledger, budget = ledger or Ledger(), budget or Budget()
    clean, found = redact(prompt, env)
    clean_sys, found_sys = (redact(system, env) if system else (None, {}))
    for k, v in found_sys.items():
        found[k] = found.get(k, 0) + v
    body = {"contents": [{"role": "user", "parts": [{"text": clean}]}],
            "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": temperature}}
    if clean_sys:
        body["systemInstruction"] = {"parts": [{"text": clean_sys}]}
    planned = len(clean) // 3 + max_output_tokens          # deliberately pessimistic
    meta = {"model": model, "purpose": purpose, "prompt_sha256": _sha(clean),
            "prompt_chars": len(clean), "redactions": found, "max_output_tokens": max_output_tokens}
    if dry_run:
        return {"dry_run": True, "request_meta": meta, "planned_tokens": planned}
    key = env.get("GOOGLE_API_KEY")
    if not key:
        raise GatewayError("GOOGLE_API_KEY not found in ~/.env")
    budget.check(planned)
    ledger.append("GEMINI_CALL_SENT", meta)                  # written before the network call
    status, resp = transport(ENDPOINT.format(model=model),
                             {"x-goog-api-key": key, "Content-Type": "application/json"}, body)
    text = "".join(p.get("text", "") for c in resp.get("candidates", [])
                   for p in c.get("content", {}).get("parts", []))
    usage = resp.get("usageMetadata", {})
    spent = int(usage.get("totalTokenCount", planned if status != 200 else 0))
    budget.add(spent)
    ledger.append("GEMINI_CALL_RESULT", {"prompt_sha256": meta["prompt_sha256"], "http": status,
                                         "response_sha256": _sha(text), "tokens": usage,
                                         "finish": [c.get("finishReason") for c in resp.get("candidates", [])],
                                         "model_version": resp.get("modelVersion")})
    if status != 200:
        raise GatewayError(f"HTTP {status}: {str(resp.get('error', {}).get('message', ''))[:200]}")
    return {"text": text, "tokens": usage, "model_version": resp.get("modelVersion"), "redactions": found}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--purpose", required=True)
    ap.add_argument("--model", default="gemini-2.5-flash", choices=ALLOWED_MODELS)
    ap.add_argument("--max-output-tokens", type=int, default=2048)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", help="read the prompt from a file (default: stdin)")
    a = ap.parse_args()
    prompt = open(a.file).read() if a.file else __import__("sys").stdin.read()
    r = generate(prompt, purpose=a.purpose, model=a.model, max_output_tokens=a.max_output_tokens, dry_run=a.dry_run)
    print(json.dumps({k: v for k, v in r.items() if k != "text"}, indent=2))
    if "text" in r:
        print(r["text"])


def run_command(arg):
    """REPL `/gemini [--dry] [--pro] <prompt>`: explicit, user-invoked, advisory output only."""
    words = arg.split()
    dry = "--dry" in words
    model = "gemini-2.5-pro" if "--pro" in words else "gemini-2.5-flash"
    prompt = " ".join(w for w in words if w not in ("--dry", "--pro"))
    if not prompt:
        return "[gemini] usage: /gemini [--dry] [--pro] <prompt>  (advisory only; redacted, budgeted, ledgered)"
    try:
        r = generate(prompt, purpose="interactive /gemini command", model=model, max_output_tokens=2048, dry_run=dry)
    except (GatewayError, BudgetExceeded) as e:
        return f"[gemini] refused: {e}"
    if r.get("dry_run"):
        m = r["request_meta"]
        return f"[gemini] dry run: {m['model']}, {m['prompt_chars']} chars, redactions={m['redactions'] or 'none'}, ~{r['planned_tokens']} tokens (nothing sent)"
    red = f" (redacted: {', '.join(r['redactions'])})" if r["redactions"] else ""
    return f"[gemini {r['model_version']}{red} - advisory, not evidence]\n{r['text']}"
