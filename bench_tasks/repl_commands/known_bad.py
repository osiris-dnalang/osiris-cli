import difflib

COMMANDS = ("/apply", "/why", "/ignite", "/sprint plan", "/sprint execute", "/sprint review")


def normalize_command(text):
    t = text.strip().lower()
    return t if t in COMMANDS else None  # misses "apply", "//APPLY.", extra spaces


def suggest(text):
    m = difflib.get_close_matches(text.strip().lower(), COMMANDS, n=1, cutoff=0.3)
    return m[0] if m else None  # cutoff far too loose: maps unrelated words
