from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass
class PPOTrainingConfig:
    batch_size: int = 4
    learning_rate: float = 1e-5
    mini_batch_size: int = 1
    gradient_accumulation_steps: int = 1
    target_kl: float = 0.1
    log_with: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_ppo(model, tokenizer, reward_model, dataset: Iterable[Dict[str, Any]], config: Optional[PPOTrainingConfig] = None):
    """Execute PPO alignment with TRL when available."""
    try:
        from trl import PPOConfig, PPOTrainer
    except ImportError as exc:
        raise RuntimeError(
            "PPO training requires the 'trl' package. Install the optional stack dependencies first."
        ) from exc

    training_config = config or PPOTrainingConfig()
    trainer = PPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=PPOConfig(**training_config.to_dict()),
    )

    for batch in dataset:
        query = batch["prompt"]
        generated = trainer.generate(query)
        reward_inputs = tokenizer(generated, return_tensors="pt", truncation=True)
        reward = reward_model(**reward_inputs).item()
        trainer.step([query], [generated], [reward])

    return trainer