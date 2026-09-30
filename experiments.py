"""
experiments.py -- simulator-first experiment briefs (drafts).

A research request ("compare two error-mitigation methods on a shallow
circuit") becomes a brief that someone could reproduce and critique:

  question      what is being tested
  hypothesis    what outcome would support or weaken it
  system        circuit family / system under test
  variables     what is varied (at least one)
  metric        how outcomes are measured (METRICS, or your own)
  controls      seeds, shots, noise model -- what is held fixed

Every brief is a draft with execution fixed to a LOCAL SIMULATOR and
hardware DISABLED: nothing here runs, submits or spends anything. The
brief is the plan a later, separately reviewed run must follow; a model
never claims a result from it.
"""
import json
import os
import time

STORE = os.path.join(os.path.expanduser("~"), ".osiris", "experiments.json")
METRICS = ("expectation-value error vs. exact", "state fidelity", "success probability",
           "variance across seeds", "runtime / cost")


def _load():
    try:
        with open(STORE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("briefs"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"next_id": 1, "briefs": []}


def _save(data):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, STORE)


def new_brief(question="", hypothesis="", system="", variables=(), metric="", controls=()):
    clean = lambda s: " ".join(str(s).split())
    return {"question": clean(question), "hypothesis": clean(hypothesis), "system": clean(system),
            "variables": [clean(v) for v in variables if str(v).strip()], "metric": clean(metric),
            "controls": [clean(c) for c in controls if str(c).strip()],
            "execution": "local simulator only", "hardware": "disabled -- needs a separate reviewed request"}


# field -> (check on a brief, what is missing). problems() and the form's
# per-answer check (field_problem) use the same rules.
RULES = {
    "question": (lambda b: len(b["question"].split()) >= 6,
                 "Question: state what is being tested in a sentence (6+ words)."),
    "hypothesis": (lambda b: len(b["hypothesis"].split()) >= 6,
                   "Hypothesis: say what outcome would support or weaken it (6+ words)."),
    "system": (lambda b: len(b["system"]) >= 3,
               "System: name the circuit family or system under test."),
    "variables": (lambda b: bool(b["variables"]), "Variables: name at least one thing that is varied."),
    "metric": (lambda b: bool(b["metric"]), "Metric: pick how outcomes are measured."),
    "controls": (lambda b: any(w in " ".join(b["controls"]).lower() for w in ("seed", "shot", "noise")),
                 "Controls: fix at least a seed, a shot count or a noise model, or runs cannot be compared."),
}
EXAMPLES = {
    "question": "Does zero-noise extrapolation reduce expectation-value error on a 3-qubit GHZ circuit?",
    "hypothesis": "ZNE gives lower mean error than no mitigation at the same shot count.",
    "system": "3-qubit GHZ circuit, depth 2-10",
    "variables": "mitigation method (none, ZNE) -- then circuit depth",
    "metric": "type a number from the list above",
    "controls": "seed 7 -- then 4000 shots -- then depolarizing noise p=0.01",
}


def problems(b):
    """What keeps a brief from being reproducible ([] = complete)."""
    return [msg for check, msg in RULES.values() if not check(b)]


def field_problem(field, value):
    """RULES[field]'s message if this one answer fails it, else None -- so the
    form can say so at once (on-device, "screenshots", "demo" and "r" were
    only flagged after all six answers, 2026-09-24)."""
    check, msg = RULES[field]
    return None if check(new_brief(**{field: value})) else msg


def save(b):
    data = _load()
    b = dict(b, id=data["next_id"], status="draft", created=time.strftime("%Y-%m-%dT%H:%M:%S"))
    data["briefs"].append(b)
    data["next_id"] += 1
    _save(data)
    return b


def briefs():
    return _load()["briefs"]
