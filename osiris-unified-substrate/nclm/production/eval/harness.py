from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Mapping

from .tasks import gsm8k, humaneval, mmlu


TaskDatasetMap = Mapping[str, Iterable[Dict[str, object]]]


@dataclass
class EvalHarness:
    task_registry: Dict[str, Callable[[Callable[[str], str], Iterable[Dict[str, object]]], float]] = field(
        default_factory=lambda: {
            "mmlu": mmlu.evaluate,
            "gsm8k": gsm8k.evaluate,
            "humaneval": humaneval.evaluate,
        }
    )

    def run_all(self, predict_fn: Callable[[str], str], datasets: TaskDatasetMap, tasks: Iterable[str] | None = None) -> Dict[str, float]:
        selected = list(tasks or self.task_registry.keys())
        results: Dict[str, float] = {}
        for task_name in selected:
            evaluator = self.task_registry[task_name]
            results[task_name] = evaluator(predict_fn, datasets.get(task_name, []))
        return results


def run_all(predict_fn: Callable[[str], str], datasets: TaskDatasetMap, tasks: Iterable[str] | None = None) -> Dict[str, float]:
    return EvalHarness().run_all(predict_fn=predict_fn, datasets=datasets, tasks=tasks)