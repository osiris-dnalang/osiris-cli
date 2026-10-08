"""The only path from OSIRIS to Google's model APIs.

Every Gemini request -- the Synthesizer, /lab discovery, vision, /gemini -- goes through
send(), which:
  * picks a backend: Vertex AI in your own GCP project with your gcloud login (when
    OSIRIS_GCP_PROJECT is set; no API key needed), else the Gemini Developer API with an
    AIza-type key, else Vertex AI express mode with an AQ-type key; keys and tokens come from the
    environment, ~/.env (parsed, never sourced) or gcloud, and are never logged, printed or returned;
  * redacts every outbound text part first (any value held in ~/.env, and secret-shaped
    strings: Google/GitHub/AWS/sk- keys, private keys, database URLs with passwords);
  * enforces a persistent token budget, refusing a call that would exceed it;
  * writes a hash-chained ledger row BEFORE the call and a result row after it (hashes and
    counts only, never prompt or response text).
It is advisory plumbing: no verifier, scoring or training-label path may depend on it.
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
DEFAULT_TOKEN_BUDGET = int(os.environ.get("OSIRIS_GEMINI_TOKEN_BUDGET", "2000000"))
GENESIS = "0" * 64

BACKENDS = {
    # name: (key variable, URL template, default model, model variable)
    "vertex-project": (None, "https://{host}/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent",
                       "gemini-3.6-flash", "OSIRIS_GCP_MODEL"),
    "developer": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  "gemini-3.6-flash", "GEMINI_MODEL"),
    "vertex": ("GOOGLE_API_KEY", "https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent",
               "gemini-2.5-flash", "GEMINI_VERTEX_MODEL"),
}
MODEL_RE = re.compile(r"^gemini-[0-9A-Za-z.\-]+$")

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


class GatewayError(RuntimeError):
    """Any reason a request was not sent or did not succeed. Never carries a key."""


class BudgetExceeded(GatewayError):
    pass


def load_env(path=ENV_PATH):
    """KEY=VALUE lines of ~/.env (no shell evaluation; commented lines ignored)."""
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


def _secret_values(env):
    vals = {k: v for k, v in env.items() if len(v) >= 8}
    for k, v in os.environ.items():
        if len(v) >= 8 and re.search(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL", k):
            vals.setdefault(k, v)
    return vals


def redact(text, env=None):
    """(clean_text, findings); findings are names/kinds with counts, never values."""
    findings = {}
    for name, val in _secret_values(load_env() if env is None else env).items():
        if val in text:
            findings[f"env:{name}"] = text.count(val)
            text = text.replace(val, f"[REDACTED:{name}]")
    for rx, kind in _SECRET_SHAPES:
        text, n = rx.subn(f"[REDACTED:{kind}]", text)
        if n:
            findings[kind] = findings.get(kind, 0) + n
    return text, findings


def _redact_payload(payload, env):
    """Redact every text part in contents and systemInstruction (images are left as is)."""
    found = {}
    p = json.loads(json.dumps(payload))
    blocks = list(p.get("contents", [])) + ([p["systemInstruction"]] if "systemInstruction" in p else [])
    for block in blocks:
        for part in block.get("parts", []):
            if isinstance(part.get("text"), str):
                part["text"], f = redact(part["text"], env)
                for k, v in f.items():
                    found[k] = found.get(k, 0) + v
    return p, found


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path=None):
        self.path = path or LEDGER_PATH

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
        if not os.path.exists(self.path):
            return True, "ok"
        for i, line in enumerate(open(self.path, encoding="utf-8")):
            e = json.loads(line)
            body = {k: e[k] for k in ("kind", "payload", "prev", "ts")}
            if e["prev"] != prev or e["hash"] != _sha(_canon(body)):
                return False, f"entry {i}: chain broken"
            prev = e["hash"]
        return True, "ok"


class Budget:
    def __init__(self, path=None, limit=None):
        self.path, self.limit = path or BUDGET_PATH, limit or DEFAULT_TOKEN_BUDGET

    def used(self):
        try:
            return int(json.load(open(self.path))["tokens"])
        except (OSError, ValueError, KeyError):
            return 0

    def add(self, n):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        total = self.used() + int(n)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"tokens": total, "limit": self.limit}, f)

    def check(self, planned):
        if self.used() + planned > self.limit:
            raise BudgetExceeded(f"Gemini token budget {self.limit} would be exceeded "
                                 f"(used {self.used()}, this call up to {planned})")


def _key(name, env):
    return (os.environ.get(name, "") or env.get(name, "")).strip()


_TOKEN = {"value": "", "until": 0.0}


def gcp_settings(env=None):
    """(project, location) for the vertex-project backend; project None when not configured."""
    env = load_env() if env is None else env
    project = _key("OSIRIS_GCP_PROJECT", env) or None
    return project, _key("OSIRIS_GCP_LOCATION", env) or "global"


def _gcloud():
    import shutil
    return shutil.which("gcloud") or next((p for p in (os.path.join(HOME, "google-cloud-sdk", "bin", "gcloud"),)
                                           if os.access(p, os.X_OK)), None)


def _gcp_token():
    """An OAuth access token from your gcloud login, cached for 45 minutes. '' if unavailable."""
    import subprocess
    if _TOKEN["value"] and time.time() < _TOKEN["until"]:
        return _TOKEN["value"]
    exe = _gcloud()
    if not exe:
        return ""
    try:
        out = subprocess.run([exe, "auth", "print-access-token"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    tok = out.stdout.strip() if out.returncode == 0 else ""
    _TOKEN.update(value=tok, until=time.time() + 45 * 60 if tok else 0.0)
    return tok


def backend_key(backend, env):
    """The key that works on this backend. Developer API keys look like 'AIza...'; Vertex
    express / agent-platform keys look like 'AQ....' and are rejected by the Developer API
    (401), so an AQ-type GEMINI_API_KEY is used on Vertex instead."""
    if backend == "vertex-project":
        return "gcloud" if gcp_settings(env)[0] and _gcloud() else ""     # the token is fetched at send time
    gem, goog = _key("GEMINI_API_KEY", env), _key("GOOGLE_API_KEY", env)
    if backend == "developer":
        return next((k for k in (gem, goog) if k.startswith("AIza")), "")
    return next((k for k in (goog, gem) if k and not k.startswith("AIza")), "")


def choose_backend(env=None, backend=None):
    """The Developer API when an AIza-type key is available, else Vertex when an AQ-type key
    is; OSIRIS_GEMINI_BACKEND or the argument forces one. None when no usable key exists."""
    env = load_env() if env is None else env
    wanted = backend or os.environ.get("OSIRIS_GEMINI_BACKEND", "").strip() or "auto"
    order = [wanted] if wanted in BACKENDS else ["vertex-project", "developer", "vertex"]
    for name in order:
        if backend_key(name, env):
            return name
    return None


def model_for(backend, model=None):
    var_default, var_name = BACKENDS[backend][2], BACKENDS[backend][3]
    m = model or os.environ.get(var_name, "").strip() or var_default
    if not MODEL_RE.match(m):
        raise GatewayError(f"model {m!r} is not a Gemini model name")
    return m


def _post(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def send(payload, *, purpose, model=None, backend=None, timeout=60, transport=_post,
         ledger=None, budget=None, env=None):
    """Send one generateContent payload; returns (response_json, meta). Raises GatewayError
    (or BudgetExceeded) for no key, budget, transport failure or a non-200 status."""
    if not str(purpose).strip():
        raise GatewayError("a purpose is required")
    env = load_env() if env is None else env
    name = choose_backend(env, backend)
    if name is None:
        raise GatewayError("no Gemini key: set GEMINI_API_KEY or GOOGLE_API_KEY in ~/.env")
    url_tmpl = BACKENDS[name][1]
    if name == "vertex-project":
        project, location = gcp_settings(env)
        token = _gcp_token()
        if not token:
            raise GatewayError("vertex-project: no gcloud access token (run: gcloud auth login)")
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        url_tmpl = url_tmpl.replace("{host}", host).replace("{project}", project).replace("{location}", location)
        headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project, "Content-Type": "application/json"}
    else:
        headers = {"x-goog-api-key": backend_key(name, env), "Content-Type": "application/json"}
    model = model_for(name, model)
    clean, found = _redact_payload(payload, env)
    text_chars = sum(len(p.get("text", "")) for b in clean.get("contents", []) for p in b.get("parts", []))
    max_out = int((clean.get("generationConfig") or {}).get("maxOutputTokens", 8192))
    planned = text_chars // 3 + max_out
    ledger, budget = ledger or Ledger(), budget or Budget()
    budget.check(planned)
    body_sha = _sha(_canon(clean))
    meta = {"backend": name, "model": model, "purpose": str(purpose)[:200], "payload_sha256": body_sha,
            "text_chars": text_chars, "redactions": found}
    ledger.append("GEMINI_CALL_SENT", meta)                      # written before the network call
    try:
        status, resp = transport(url_tmpl.format(model=model), headers, clean, timeout)
    except Exception as e:  # noqa: BLE001 - recorded, then re-raised without any key material
        ledger.append("GEMINI_CALL_RESULT", {"payload_sha256": body_sha, "http": None, "error": type(e).__name__})
        raise GatewayError(f"Gemini request failed: {type(e).__name__}") from None
    usage = resp.get("usageMetadata", {}) if isinstance(resp, dict) else {}
    budget.add(int(usage.get("totalTokenCount", 0)))
    text = "".join(p.get("text", "") for c in resp.get("candidates", []) or []
                   for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
    ledger.append("GEMINI_CALL_RESULT", {"payload_sha256": body_sha, "http": status, "response_sha256": _sha(text),
                                         "tokens": usage, "model_version": resp.get("modelVersion"),
                                         "finish": [c.get("finishReason") for c in resp.get("candidates", []) or []]})
    if status == 401 and name == "vertex-project":
        _TOKEN.update(value="", until=0.0)                       # expired: fetch a new one next time
    if status != 200:
        msg = str((resp.get("error") or {}).get("message", ""))[:200] if isinstance(resp, dict) else ""
        raise GatewayError(f"Gemini HTTP {status} ({name}): {msg}")
    meta.update(model_version=resp.get("modelVersion"), tokens=usage)
    return resp, meta


def generate(prompt, *, purpose, model=None, backend=None, system=None, max_output_tokens=2048,
             temperature=0.0, dry_run=False, **kw):
    """Text in, text out. dry_run returns what would be sent (sizes, redactions) and sends nothing."""
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": temperature}}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if dry_run:
        env = kw.get("env") or load_env()
        name = choose_backend(env, backend)
        clean, found = _redact_payload(payload, env)
        return {"dry_run": True, "backend": name, "model": model_for(name, model) if name else None,
                "prompt_chars": len(clean["contents"][0]["parts"][0]["text"]), "redactions": found}
    resp, meta = send(payload, purpose=purpose, model=model, backend=backend, **kw)
    text = "".join(p.get("text", "") for c in resp.get("candidates", []) or []
                   for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
    return {"text": text, "backend": meta["backend"], "model_version": meta.get("model_version"),
            "tokens": meta.get("tokens"), "redactions": meta["redactions"]}


def run_command(arg):
    """REPL `/gemini [--dry] [--pro] <prompt>`: explicit, user-invoked, advisory output only."""
    words = arg.split()
    dry, pro = "--dry" in words, "--pro" in words
    prompt = " ".join(w for w in words if w not in ("--dry", "--pro"))
    if not prompt:
        return "[gemini] usage: /gemini [--dry] [--pro] <prompt>  (advisory only; redacted, budgeted, ledgered)"
    try:
        backend = choose_backend()
        model = {"vertex": "gemini-2.5-pro", "vertex-project": "gemini-3.1-pro-preview"}.get(backend) if pro else None
        r = generate(prompt, purpose="interactive /gemini command", model=model, max_output_tokens=4096, dry_run=dry)
    except GatewayError as e:
        return f"[gemini] refused: {e}"
    if r.get("dry_run"):
        return (f"[gemini] dry run: {r['backend']} {r['model']}, {r['prompt_chars']} chars, "
                f"redactions={r['redactions'] or 'none'} (nothing sent)")
    red = f" (redacted: {', '.join(r['redactions'])})" if r["redactions"] else ""
    return f"[gemini {r['backend']} {r['model_version']}{red} - advisory, not evidence]\n{r['text']}"


def status_line():
    """One line for /status: which backend would be used, budget and ledger state."""
    name = choose_backend()
    if name is None:
        return "Gemini         : not configured (GEMINI_API_KEY or GOOGLE_API_KEY in ~/.env)"
    ok, _ = Ledger().verify()
    where = f" ({gcp_settings()[0]}/{gcp_settings()[1]})" if name == "vertex-project" else ""
    line = (f"Gemini         : {name}{where} {model_for(name)} · budget {Budget().used():,}/{Budget().limit:,} tokens · "
            f"ledger {'intact' if ok else 'BROKEN'}")
    try:
        from osiris_cli import gcp_secrets
        if gcp_secrets.wanted():
            r = gcp_secrets.last_result
            line += f" · secrets: {len(r['loaded'])} from Secret Manager" + (f" ({r['error']})" if r["error"] else "")
    except Exception:  # noqa: BLE001
        pass
    return line
