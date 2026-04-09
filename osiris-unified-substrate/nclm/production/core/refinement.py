from dataclasses import dataclass
from typing import Dict, List


FOUNDATIONAL_CAPABILITIES = [
    "supervised fine-tuning",
    "preference modeling",
    "policy optimization",
    "benchmark evaluation",
    "tool routing",
    "self-consistency",
    "observability",
    "artifact attestation",
]


@dataclass
class RefinementPass:
    iteration: int
    added_capabilities: List[str]
    refined_prompt: str


def recursive_refine(requirements: str, iterations: int = 3) -> List[RefinementPass]:
    """Expand a high-level goal into increasingly concrete engineering requirements."""
    prompt = requirements.strip()
    missing = FOUNDATIONAL_CAPABILITIES[:]
    passes: List[RefinementPass] = []

    for iteration in range(1, max(iterations, 1) + 1):
        batch_size = max(1, len(missing) // max(iterations - iteration + 1, 1))
        added = missing[:batch_size]
        missing = missing[batch_size:]
        if added:
            prompt = (
                f"{prompt}\n\nIteration {iteration} engineering constraints:\n"
                + "\n".join(f"- Include {capability}" for capability in added)
            )
        passes.append(RefinementPass(iteration=iteration, added_capabilities=added, refined_prompt=prompt))

    return passes


def summarize_refinement(passes: List[RefinementPass]) -> Dict[str, object]:
    return {
        "iterations": len(passes),
        "capabilities_added": [capability for item in passes for capability in item.added_capabilities],
        "final_prompt": passes[-1].refined_prompt if passes else "",
    }