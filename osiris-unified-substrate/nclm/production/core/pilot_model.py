from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class PilotModelSpec:
    model_name: str
    max_seq_length: int = 4096
    target_use_cases: List[str] = field(default_factory=list)
    training_objectives: List[str] = field(default_factory=lambda: ["sft", "rlhf", "evaluation"])
    deployment_constraints: Dict[str, str] = field(default_factory=dict)
    benchmark_targets: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def build_pilot_manifest(spec: PilotModelSpec) -> Dict[str, object]:
    """Create a model manifest that downstream training and eval steps can consume."""
    manifest = spec.to_dict()
    manifest["readiness_checks"] = [
        "tokenizer_available",
        "train_config_validated",
        "eval_tasks_selected",
        "observability_enabled",
    ]
    manifest["production_features"] = {
        "gradient_checkpointing": True,
        "flash_attention": True,
        "mixed_precision": "bf16",
        "dataset_streaming": True,
    }
    return manifest