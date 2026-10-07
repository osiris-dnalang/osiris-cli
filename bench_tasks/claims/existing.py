"""claims -- sanity checks on a proposed claim before a human reviews it."""


def check_claim(text, evidence):
    """Returns a list of problems with a proposed claim. `evidence` is the text
    of the file the claim cites."""
    problems = []
    if not evidence or not evidence.strip():
        problems.append("no evidence cited")
    return problems
