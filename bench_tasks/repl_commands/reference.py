import difflib
import re

COMMANDS = ("/apply", "/why", "/ignite", "/sprint plan", "/sprint execute", "/sprint review")


def _norm(text):
    t = re.sub(r"\s+", " ", text.strip().lower()).lstrip("/").rstrip(".!").strip()
    return t


def normalize_command(text):
    t = _norm(text)
    for c in COMMANDS:
        if t == c[1:]:
            return c
    return None


def suggest(text):
    exact = normalize_command(text)
    if exact is not None:
        return exact
    t = _norm(text)
    best, best_ratio = None, 0.0
    for c in COMMANDS:
        r = difflib.SequenceMatcher(None, t, c[1:]).ratio()
        if r > best_ratio:
            best, best_ratio = c, r
    return best if best_ratio >= 0.75 else None
