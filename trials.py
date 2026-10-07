#!/usr/bin/env python3
"""
trials.py -- a prompt-strategy trial judged against its control, by code.

A trial is a benchmark round with a declared strategy (bench_trial.py). Its
CONTROL is the latest complete baseline round (no strategy) with the same
backend, model, k, task set, suite and runner -- the only allowed
difference is the strategy. compare() puts the two side by side on those
tasks and gives a verdict by a fixed rule, on hidden-test passes (higher is
better) and false confidence (lower is better):

  better         one improves and the other does not get worse
  worse          one gets worse and the other does not improve
  mixed          one improves, the other gets worse
  no difference  neither changes

With one round each (3 tasks) a verdict is preliminary, and says so. A
hypothesis may be marked supported only by a "better" trial and refuted
only by a "worse" one (allowed_outcomes); anything may be inconclusive.
"""

VERDICTS = ("better", "worse", "mixed", "no difference")


def rounds(entries):
    """run_id -> {"start", "end", "tasks": {task: result}} from write-ahead entries."""
    out = {}
    for e in entries:
        kind, rid = e.get("kind"), e.get("run_id")
        if kind == "bench_run_start":
            out[rid] = {"start": e, "end": None, "tasks": {}}
        elif kind == "bench_task" and rid in out and e.get("task") not in out[rid]["tasks"]:
            out[rid]["tasks"][e.get("task")] = e.get("result") or {}
        elif kind == "bench_run_end" and rid in out:
            out[rid]["end"] = e
    return out


def _key(start):
    return (start.get("backend"), start.get("model"), start.get("k"), tuple(sorted(start.get("planned") or [])),
            start.get("suite_sha256"), start.get("runner_sha256"))


def _complete(r):
    return r["end"] is not None and r["end"].get("status") == "complete"


def control_for(entries, treatment_id):
    """(control round, None) or (None, why not) for a trial round."""
    rs = rounds(entries)
    t = rs.get(treatment_id)
    if t is None:
        return None, "no round with that id"
    if not t["start"].get("strategy"):
        return None, "that round has no declared strategy -- it is a baseline round, not a trial"
    key = _key(t["start"])
    controls = [r for rid, r in rs.items() if not r["start"].get("strategy") and _complete(r)
                and _key(r["start"]) == key and r["start"].get("ts", "") <= t["start"].get("ts", "")]
    if not controls:
        return None, ("no complete baseline round with the same model, backend, k, tasks, suite and runner -- "
                      "run G (the same mentor round) first")
    return controls[-1], None


def _measure(r, tasks):
    passes = sum(1 for t in tasks if (r["tasks"].get(t) or {}).get("delivered"))
    fc = sum(int((r["tasks"].get(t) or {}).get("false_confidence") or 0) for t in tasks)
    return {"hidden_passes": passes, "false_confidence": fc, "tasks": len(tasks)}


def verdict(control, treatment):
    dp = treatment["hidden_passes"] - control["hidden_passes"]
    dfc = treatment["false_confidence"] - control["false_confidence"]
    up = (dp > 0) + (dfc < 0)
    down = (dp < 0) + (dfc > 0)
    if up and down:
        return "mixed"
    if up:
        return "better"
    if down:
        return "worse"
    return "no difference"


def compare(entries, treatment_id):
    """{"treatment", "control", "strategy", "model", "tasks", "control_m",
    "treatment_m", "verdict", "preliminary", "treatment_hash"} or raises
    ValueError saying why the trial cannot be judged."""
    rs = rounds(entries)
    t = rs.get(treatment_id)
    if t is None:
        raise ValueError("no round with that id")
    if not _complete(t):
        raise ValueError(f"the trial round is {(t['end'] or {}).get('status', 'unfinished')}, not complete")
    control, why = control_for(entries, treatment_id)
    if control is None:
        raise ValueError(why)
    tasks = sorted(t["start"].get("planned") or [])
    missing = [x for x in tasks if x not in t["tasks"] or x not in control["tasks"]]
    if missing:
        raise ValueError(f"task(s) {missing} missing from the trial or its control")
    cm, tm = _measure(control, tasks), _measure(t, tasks)
    return {"treatment": treatment_id, "control": control["start"]["run_id"],
            "strategy": t["start"]["strategy"], "strategy_sha256": t["start"].get("strategy_sha256"),
            "model": t["start"].get("model") or t["start"].get("backend"), "tasks": tasks,
            "control_m": cm, "treatment_m": tm, "verdict": verdict(cm, tm),
            "preliminary": len(tasks) * int(t["start"].get("k") or 1) < 9,
            "treatment_hash": t["end"]["hash"]}


def allowed_outcomes(v):
    """Hypothesis outcomes a trial with verdict v can back."""
    return {"better": ("supported", "inconclusive"), "worse": ("refuted", "inconclusive")}.get(v, ("inconclusive",))


def describe(c):
    cm, tm = c["control_m"], c["treatment_m"]
    return (f"trial {c['treatment']}: {c['strategy']} vs baseline {c['control']} on {c['model']}, "
            f"{len(c['tasks'])} tasks -- hidden passes {tm['hidden_passes']}/{tm['tasks']} vs "
            f"{cm['hidden_passes']}/{cm['tasks']}, false confidence {tm['false_confidence']} vs "
            f"{cm['false_confidence']}: {c['verdict']}{' (preliminary: under 9 attempts per condition)' if c['preliminary'] else ''}")
