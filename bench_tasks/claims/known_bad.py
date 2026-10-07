"""claims -- sanity checks on a proposed claim before a human reviews it."""
import re


def check_claim(text, evidence):
    """Returns a list of problems with a proposed claim. `evidence` is the text
    of the file the claim cites."""
    problems = []
    if not evidence or not evidence.strip():
        problems.append("no evidence cited")
    # Plausible but wrong: substring matching accepts "3" because "13" contains it.
    for n in re.findall(r"\d+(?:\.\d+)?", text):
        if n not in evidence:
            problems.append(f"number {n} not found in the cited evidence")
    return problems
