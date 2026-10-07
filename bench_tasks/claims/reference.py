"""claims -- sanity checks on a proposed claim before a human reviews it."""
import re

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def check_claim(text, evidence):
    """Returns a list of problems with a proposed claim. `evidence` is the text
    of the file the claim cites."""
    problems = []
    if not evidence or not evidence.strip():
        problems.append("no evidence cited")
        return problems
    present = set(_NUMBER_RE.findall(evidence))
    for n in _NUMBER_RE.findall(text):
        if n not in present:
            problems.append(f"number {n} not found in the cited evidence")
    return problems
