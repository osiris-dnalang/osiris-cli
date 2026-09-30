#!/usr/bin/env python3
"""
structured_proposal.py -- schema-constrained Engine 2 proposals.

Engine 2 used to be asked for <WRITE_FILE>/<TEST_FUNCTION> tags and parsed
with regexes; "model did not return both blocks" was a recurring failure
(stories #16, #18, 2026-09-23). Backends that support it now decode against
a JSON schema, so a malformed proposal cannot be produced at all:
  - Gemini: generationConfig.responseMimeType + responseSchema
  - Ollama: the "format" field (JSON schema)
Constrained decoding guarantees the SHAPE only -- a verified live call had
llama3.2:1b return {"module": "add"} -- so content still goes through the
placeholder gate and the sandbox exactly as before.

parse_proposal() also accepts the old tag format, so a backend without
schema support (the AI Gateway path) still works.
"""
import json
import re

FIELDS = ("path", "module", "test")

# JSON Schema, as Ollama's "format" takes it.
PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {f: {"type": "string"} for f in FIELDS},
    "required": list(FIELDS),
}

# Gemini's responseSchema uses the OpenAPI subset with upper-case type names.
GEMINI_PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {f: {"type": "STRING"} for f in FIELDS},
    "required": list(FIELDS),
}

_WRITE_FILE_RE = re.compile(r'<WRITE_FILE\s+path="([^"]+)"\s*>(.*?)</WRITE_FILE>', re.DOTALL)
_TEST_FUNCTION_RE = re.compile(r'<TEST_FUNCTION>(.*?)</TEST_FUNCTION>', re.DOTALL)
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def instructions(path: str, module_name: str) -> str:
    """The output contract appended to a synthesis prompt."""
    return f"""Respond with ONLY a JSON object with exactly these string fields:
  "path":   "{path}"
  "module": the complete Python source of the module
  "test":   Python source that does `import {module_name}` and defines test_proposal(),
            taking no arguments and using plain assert statements
No markdown, no commentary."""


def parse_proposal(raw: str):
    """Returns {"path", "module", "test", "format"} or None. Accepts the JSON
    object (optionally inside a ```json fence) or the legacy tag format."""
    if not raw:
        return None
    text = raw.strip()
    fence = _FENCE_RE.match(text)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and all(isinstance(data.get(f), str) and data[f].strip() for f in FIELDS):
        return {"path": data["path"].strip(), "module": data["module"], "test": data["test"],
                "format": "json"}
    w, t = _WRITE_FILE_RE.search(raw), _TEST_FUNCTION_RE.search(raw)
    if w and t:
        return {"path": w.group(1).strip(), "module": w.group(2), "test": t.group(1), "format": "tags"}
    return None
