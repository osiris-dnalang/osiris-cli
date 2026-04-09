"""Self-improving meta-loop for OSIRIS NCLM.

The meta-loop:
  1. Runs the stack planner to produce a blueprint
  2. Evaluates the current model (or a proxy) against benchmarks
  3. Diagnoses weaknesses from evaluation results
  4. Synthesizes targeted training data for the weakest areas
  5. Updates the stack plan and repeats

This is a *deterministic* controller that can drive real training when
torch/transformers are available, or operate in dry-run mode to produce
an improvement plan.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .stack import LLMStackRefiner, StackBlueprint


@dataclass
class MetaIteration:
    """One cycle of the meta-loop."""
    iteration: int
    timestamp: str
    blueprint_summary: str
    eval_scores: Dict[str, float]
    weaknesses: List[str]
    prescribed_actions: List[str]
    data_generated: int
    improved: bool


@dataclass
class MetaLoopState:
    """Persistent state across meta-loop iterations."""
    objective: str
    history: List[MetaIteration] = field(default_factory=list)
    best_scores: Dict[str, float] = field(default_factory=dict)
    total_data_generated: int = 0
    total_train_steps: int = 0
    converged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "history": [asdict(h) for h in self.history],
            "best_scores": self.best_scores,
            "total_data_generated": self.total_data_generated,
            "total_train_steps": self.total_train_steps,
            "converged": self.converged,
        }


# --- Weakness diagnosis ---

WEAKNESS_THRESHOLDS = {
    "mmlu": 0.60,
    "gsm8k": 0.55,
    "humaneval_pass@1": 0.25,
    "consistency_gain": 0.10,
}

WEAKNESS_PRESCRIPTIONS = {
    "mmlu": [
        "Generate more multi-choice QA pairs across STEM/humanities",
        "Add chain-of-thought reasoning examples",
        "Include distractor analysis in training data",
    ],
    "gsm8k": [
        "Generate step-by-step math solutions",
        "Add arithmetic verification chains",
        "Include multi-step word problems with intermediate answers",
    ],
    "humaneval_pass@1": [
        "Generate function-completion examples with test cases",
        "Add code debugging / fix-the-bug samples",
        "Include docstring-to-implementation pairs",
    ],
    "consistency_gain": [
        "Generate self-consistency voting examples",
        "Add multi-path reasoning with agreement scoring",
        "Include samples where multiple approaches converge",
    ],
}


def diagnose_weaknesses(scores: Dict[str, float]) -> List[str]:
    """Identify benchmarks that fall below target thresholds."""
    weak: List[str] = []
    for metric, threshold in WEAKNESS_THRESHOLDS.items():
        try:
            val = float(scores.get(metric, 0.0))
        except (TypeError, ValueError):
            val = 0.0
        if val < threshold:
            weak.append(metric)
    return weak


def prescribe_actions(weaknesses: List[str]) -> List[str]:
    """Return prescribed improvements for each weakness."""
    actions: List[str] = []
    for w in weaknesses:
        actions.extend(WEAKNESS_PRESCRIPTIONS.get(w, [f"Investigate low {w} score"]))
    return actions


# --- Data synthesis stubs ---

def _synth_math_samples(count: int) -> List[Dict[str, str]]:
    """Generate synthetic math training samples."""
    import random
    samples = []
    ops = [("+", lambda a, b: a + b), ("-", lambda a, b: a - b),
           ("*", lambda a, b: a * b)]
    for _ in range(count):
        a, b = random.randint(1, 999), random.randint(1, 999)
        op_sym, op_fn = random.choice(ops)
        question = f"What is {a} {op_sym} {b}?"
        answer = str(op_fn(a, b))
        samples.append({
            "prompt": question,
            "response": f"Let me calculate: {a} {op_sym} {b} = {answer}\n\nThe answer is {answer}.",
        })
    return samples


def _synth_qa_samples(count: int) -> List[Dict[str, str]]:
    """Generate synthetic multi-choice QA training samples."""
    topics = [
        ("What is the capital of France?", "Paris", ["London", "Berlin", "Madrid"]),
        ("Which planet is closest to the Sun?", "Mercury", ["Venus", "Earth", "Mars"]),
        ("What element has atomic number 1?", "Hydrogen", ["Helium", "Lithium", "Carbon"]),
        ("Who wrote 'Hamlet'?", "Shakespeare", ["Dickens", "Tolstoy", "Homer"]),
        ("What is the speed of light in m/s?", "3×10⁸", ["3×10⁶", "3×10⁴", "3×10¹⁰"]),
    ]
    import random
    samples = []
    for _ in range(count):
        q, correct, distractors = random.choice(topics)
        choices = [correct] + distractors
        random.shuffle(choices)
        correct_idx = choices.index(correct)
        labels = "ABCD"
        formatted = q + "\n" + "\n".join(f"{labels[i]}. {c}" for i, c in enumerate(choices))
        samples.append({
            "prompt": formatted,
            "response": f"The answer is {labels[correct_idx]}. {correct}.",
        })
    return samples


def _synth_code_samples(count: int) -> List[Dict[str, str]]:
    """Generate synthetic code completion samples."""
    templates = [
        ("def add(a, b):\n    \"\"\"Return the sum of a and b.\"\"\"",
         "    return a + b"),
        ("def factorial(n):\n    \"\"\"Return n factorial.\"\"\"",
         "    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"),
        ("def is_palindrome(s):\n    \"\"\"Check if string is a palindrome.\"\"\"",
         "    return s == s[::-1]"),
        ("def fibonacci(n):\n    \"\"\"Return the nth Fibonacci number.\"\"\"",
         "    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b"),
    ]
    import random
    samples = []
    for _ in range(count):
        prompt, completion = random.choice(templates)
        samples.append({"prompt": prompt, "response": completion})
    return samples


def synthesize_data(weaknesses: List[str], count_per_weakness: int = 20) -> List[Dict[str, str]]:
    """Generate targeted training data for identified weaknesses."""
    all_samples: List[Dict[str, str]] = []
    for w in weaknesses:
        if w in ("gsm8k",):
            all_samples.extend(_synth_math_samples(count_per_weakness))
        elif w in ("mmlu",):
            all_samples.extend(_synth_qa_samples(count_per_weakness))
        elif w in ("humaneval_pass@1",):
            all_samples.extend(_synth_code_samples(count_per_weakness))
        else:
            all_samples.extend(_synth_qa_samples(count_per_weakness // 2))
    return all_samples


# --- Meta-loop controller ---

class MetaLoop:
    """Self-improving controller that iterates: plan → eval → diagnose → generate → retrain."""

    def __init__(
        self,
        objective: str,
        eval_fn: Optional[Callable[[], Dict[str, float]]] = None,
        train_fn: Optional[Callable[[List[Dict[str, str]]], int]] = None,
        max_iterations: int = 5,
        convergence_threshold: float = 0.02,
        data_per_weakness: int = 50,
    ):
        self.objective = objective
        self.eval_fn = eval_fn or self._default_eval
        self.train_fn = train_fn
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.data_per_weakness = data_per_weakness
        self.refiner = LLMStackRefiner()
        self.state = MetaLoopState(objective=objective)

    def _default_eval(self) -> Dict[str, float]:
        """Return the refiner's benchmark targets as a baseline."""
        return self.refiner.build_benchmark_output()

    def run(self) -> MetaLoopState:
        """Execute the full meta-loop until convergence or max iterations."""
        for iteration in range(1, self.max_iterations + 1):
            ts = datetime.now(timezone.utc).isoformat()

            # 1. Plan
            blueprint = self.refiner.refine(self.objective, iterations=iteration)

            # 2. Evaluate
            scores = self.eval_fn()

            # 3. Diagnose
            weaknesses = diagnose_weaknesses(scores)
            actions = prescribe_actions(weaknesses)

            # 4. Synthesize data
            new_data = synthesize_data(weaknesses, self.data_per_weakness) if weaknesses else []
            data_count = len(new_data)

            # 5. Train (if callback provided and data exists)
            if self.train_fn and new_data:
                steps = self.train_fn(new_data)
                self.state.total_train_steps += steps

            # Check improvement
            improved = False
            for metric, score in scores.items():
                try:
                    score_f = float(score)
                except (TypeError, ValueError):
                    continue
                if score_f > self.state.best_scores.get(metric, 0.0):
                    improved = True
                    self.state.best_scores[metric] = score_f

            # Record
            meta_iter = MetaIteration(
                iteration=iteration,
                timestamp=ts,
                blueprint_summary=blueprint.final_summary[:200],
                eval_scores=scores,
                weaknesses=weaknesses,
                prescribed_actions=actions,
                data_generated=data_count,
                improved=improved,
            )
            self.state.history.append(meta_iter)
            self.state.total_data_generated += data_count

            # Check convergence
            if not weaknesses:
                self.state.converged = True
                break

            # Check if no improvement for 2 consecutive iterations
            if len(self.state.history) >= 2:
                last_two = self.state.history[-2:]
                if not last_two[0].improved and not last_two[1].improved:
                    self.state.converged = True  # Plateau
                    break

        return self.state

    def save(self, path: str = "artifacts/meta_loop_state.json") -> Path:
        """Persist meta-loop state to disk."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.state.to_dict(), indent=2))
        return out


def run_meta_loop(
    objective: str,
    max_iterations: int = 5,
    eval_fn: Optional[Callable[[], Dict[str, float]]] = None,
    train_fn: Optional[Callable[[List[Dict[str, str]]], int]] = None,
) -> Dict[str, Any]:
    """Convenience entry point for the self-improving meta-loop."""
    loop = MetaLoop(
        objective=objective,
        max_iterations=max_iterations,
        eval_fn=eval_fn,
        train_fn=train_fn,
    )
    state = loop.run()
    loop.save()
    return state.to_dict()
