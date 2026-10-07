#!/usr/bin/env python3
"""
gemini_bridge.py -- optional cloud-burst synthesis backend for OSIRIS Engine 2.

Talks to Google's Gemini REST API (stdlib only, no SDK dependency) as a
fast alternative to local deepseek-coder on slow ARM64/Termux hardware. Used
only when GEMINI_API_KEY is set in the environment; every caller must fall
back to the local Ollama path on any failure (missing key, network error,
non-200 response, malformed JSON).

Every request goes through osiris_cli.gemini_gateway, which picks the backend
(Gemini Developer API with GEMINI_API_KEY, else Vertex AI with GOOGLE_API_KEY),
redacts secrets from the outbound text, enforces the token budget and writes a
hash-chained ledger row before and after the call. Keys are sent only in the
x-goog-api-key header and never appear in an exception, log line or return value.
"""
import json
import os
import time

# GEMINI_MODEL lets the user point this at whatever model their key/plan
# actually has access to. gemini-1.5-flash and gemini-2.5-flash were both
# retired for new callers by 2026-09-23; the live API's own 404 error on
# gemini-2.5-flash explicitly named gemini-3.6-flash as its replacement,
# confirmed working via a real authenticated call on that date.
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_TIMEOUT = 45  # seconds -- this is meant to be the FAST path
NETWORK_RETRY_ATTEMPTS = 2  # only for transient network errors, never for auth failures
NETWORK_RETRY_BACKOFF = 1.5  # seconds, applied before each retry
DEFAULT_LIBRARY_PATH = os.path.expanduser("~/.osiris/operands/library.json")


class GeminiUnavailable(Exception):
    """Raised whenever Gemini can't be used right now; callers should catch
    this and fall back to the local model. Never carries the API key."""


def _gateway():
    from osiris_cli import gemini_gateway
    return gemini_gateway


def model_name() -> str:
    """The model the next request will use: the backend's model variable
    ($GEMINI_MODEL for the Developer API, $GEMINI_VERTEX_MODEL for Vertex) or its default."""
    gw = _gateway()
    backend = gw.choose_backend()
    return gw.model_for(backend) if backend else (os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL)


def is_configured() -> bool:
    """True when either Gemini key is available (environment or ~/.env)."""
    return _gateway().choose_backend() is not None


_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def resolve_storage_path(path: str) -> str:
    """Resolve Android/Termux storage paths and expand user symbols gracefully.

    Handles missing termux-setup-storage permissions or non-existent storage
    paths by raising GeminiUnavailable with actionable guidance.
    """
    if not path:
        raise GeminiUnavailable("Image path cannot be empty")

    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded):
        candidates = []
        if expanded.startswith("/sdcard/"):
            candidates.append(expanded.replace("/sdcard/", "/storage/emulated/0/"))
        elif expanded.startswith("/storage/emulated/0/"):
            candidates.append(
                os.path.expanduser("~/storage/shared/") + expanded[len("/storage/emulated/0/"):].lstrip("/")
            )

        termux_storage = os.path.expanduser("~/storage/shared")
        candidates.append(os.path.join(termux_storage, path.lstrip("/")))

        found = None
        for cand in candidates:
            if os.path.exists(cand):
                found = cand
                break

        if found:
            expanded = found
        else:
            raise GeminiUnavailable(
                f"Storage path not found or termux-setup-storage permissions missing: {path}"
            )

    if not os.access(expanded, os.R_OK):
        raise GeminiUnavailable(
            f"Permission denied reading image path (run termux-setup-storage): {path}"
        )

    return os.path.abspath(expanded)


def query(system_prompt: str, user_prompt: str, timeout: int = DEFAULT_TIMEOUT,
          response_schema: dict = None, google_search: bool = False) -> str:
    """Query Gemini with a system + user prompt, return the synthesized text.
    With response_schema (OpenAPI-subset schema), decoding is constrained to
    JSON matching it. google_search=True lets Gemini ground its answer with
    Google Search (read-only, run on Google's side; nothing runs here).
    Raises GeminiUnavailable (key-safe message) on any failure -- callers
    must catch this and fall back to query_model()/local Ollama."""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
    }
    if google_search:
        payload["tools"] = [{"google_search": {}}]
    if response_schema:
        payload["generationConfig"] = {"responseMimeType": "application/json",
                                       "responseSchema": response_schema}
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    return _send(payload, timeout)


def query_with_image(system_prompt: str, user_prompt: str, image_path: str,
                      timeout: int = DEFAULT_TIMEOUT) -> str:
    """Same as query(), but attaches one local image file as inline multimodal
    data (Gemini REST format: parts[].inlineData.{mimeType,data}, base64).
    query() is left completely unchanged for every existing text-only caller
    (/auto-enhance, Stage 2 hot-swap, etc.) -- this is a separate function,
    not a signature change."""
    import base64

    resolved_path = resolve_storage_path(image_path)
    ext = os.path.splitext(resolved_path)[1].lower()
    mime = _MIME_BY_EXT.get(ext)
    if not mime:
        raise GeminiUnavailable(f"Unsupported image type: {ext or '(none)'}")

    try:
        with open(resolved_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
    except OSError as e:
        raise GeminiUnavailable(f"Could not read image: {type(e).__name__}") from None

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": user_prompt},
                {"inlineData": {"mimeType": mime, "data": b64}},
            ],
        }],
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    return _send(payload, timeout)


def query_with_images(system_prompt: str, user_prompt: str, image_paths: list,
                       timeout: int = DEFAULT_TIMEOUT) -> str:
    """Batch version of query_with_image() -- attaches MULTIPLE local images as
    separate inlineData parts in one real request (Gemini's multimodal format
    genuinely supports several images per call, this isn't N separate calls
    stitched together). Used by vision_indexer.py for incremental screenshot
    batches; query_with_image() is untouched for its existing single-image
    caller (/vision latest)."""
    import base64

    parts = [{"text": user_prompt}]
    for image_path in image_paths:
        resolved_path = resolve_storage_path(image_path)
        ext = os.path.splitext(resolved_path)[1].lower()
        mime = _MIME_BY_EXT.get(ext)
        if not mime:
            raise GeminiUnavailable(f"Unsupported image type: {ext or '(none)'}")
        try:
            with open(resolved_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError as e:
            raise GeminiUnavailable(f"Could not read image: {type(e).__name__}") from None
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})

    payload = {"contents": [{"role": "user", "parts": parts}]}
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    return _send(payload, timeout)


def ingest_vision(
    image_path: str,
    user_prompt: str = "Analyze this image for software engineering context.",
    system_prompt: str = "",
    library_path: str = DEFAULT_LIBRARY_PATH,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Ingest an image, resolve storage path, query Gemini vision API, and write
    digested vision output directly into library.json for the next /suggest REPL loop."""
    resolved_path = resolve_storage_path(image_path)
    digested_text = query_with_image(system_prompt, user_prompt, resolved_path, timeout=timeout)

    try:
        data = {}
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {"raw": data}
            except Exception:
                data = {}

        data["digested_vision"] = digested_text
        data["vision"] = digested_text
        data["latest_image"] = resolved_path
        data["vision_timestamp"] = time.time()

        parent_dir = os.path.dirname(os.path.abspath(library_path))
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(library_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise GeminiUnavailable(f"Failed to update library file {library_path}: {e}") from None

    return digested_text


def _send(payload: dict, timeout: int) -> str:
    """Shared request/response handling for query() and query_with_image(); the
    request itself goes through the gateway (redaction, budget, ledger)."""
    import inspect
    gw = _gateway()
    caller = next((f.function for f in inspect.stack()[1:4] if f.function not in ("_send",)), "query")
    status, data = None, None
    for attempt in range(1 + NETWORK_RETRY_ATTEMPTS):
        try:
            data, _meta = gw.send(payload, purpose=f"gemini_bridge.{caller}", timeout=timeout)
            status = 200
            break
        except gw.BudgetExceeded as e:
            raise GeminiUnavailable(str(e)) from None
        except gw.GatewayError as e:
            msg = str(e)
            # only transport failures are retried; HTTP errors and missing keys fail fast
            if msg.startswith("Gemini request failed") and attempt < NETWORK_RETRY_ATTEMPTS:
                time.sleep(NETWORK_RETRY_BACKOFF)
                continue
            raise GeminiUnavailable(msg) from None

    if status != 200 or not isinstance(data, dict):
        raise GeminiUnavailable(f"Gemini returned HTTP {status}")

    # A 200 can still carry no text: the prompt or output was blocked
    # (promptFeedback.blockReason, e.g. OTHER -- reproduced 2026-09-23 on
    # ignite story prompts), or generation stopped early (finishReason
    # SAFETY/RECITATION/MAX_TOKENS). Name the reason instead of a KeyError.
    raw = json.dumps(data)[:500]  # raw excerpt so the actual rejection is visible
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise GeminiUnavailable(f"Gemini blocked the request (blockReason={block}) raw={raw}")
    try:
        candidate = data["candidates"][0]
        text = "".join(p.get("text", "") for p in candidate["content"]["parts"]
                       if not p.get("thought"))
    except (KeyError, IndexError, TypeError, AttributeError):
        reason = ((data.get("candidates") or [{}])[0] or {}).get("finishReason", "unknown")
        raise GeminiUnavailable(f"Gemini returned no text (finishReason={reason}) raw={raw}") from None

    if not text or not text.strip():
        raise GeminiUnavailable("Gemini returned empty text")

    return text


if __name__ == "__main__":
    if not is_configured():
        print("GEMINI_API_KEY not set; nothing to test.")
    else:
        try:
            out = query("You are a terse test responder.", "Say 'ok' and nothing else.")
            print(f"Gemini responded ({len(out)} chars): {out[:80]!r}")
        except GeminiUnavailable as e:
            print(f"Gemini unavailable: {e}")
