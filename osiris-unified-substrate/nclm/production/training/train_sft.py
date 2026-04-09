from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import load_config
from ..core.model_loader import load_model_bundle


@dataclass
class SFTTrainingResult:
    output_dir: str
    epochs: int
    learning_rate: float


def train(config_path: str | Path = "configs/train.yaml", overrides: Optional[Dict[str, Any]] = None) -> SFTTrainingResult:
    """Launch supervised fine-tuning via Transformers Trainer."""
    try:
        from datasets import load_dataset
        from transformers import DataCollatorForLanguageModeling, Trainer, TrainingArguments
    except ImportError as exc:
        raise RuntimeError(
            "SFT training requires 'datasets' and 'transformers'. Install optional stack dependencies first."
        ) from exc

    config = load_config(config_path)
    if overrides:
        config.update(overrides)

    model_bundle = load_model_bundle(
        model_name=config["model"]["name"],
        tokenizer_name=config["model"].get("tokenizer"),
        device_map=config["model"].get("device_map", "auto"),
        torch_dtype=config["model"].get("torch_dtype"),
        gradient_checkpointing=config["model"].get("gradient_checkpointing", False),
        attn_implementation=config["model"].get("attn_implementation"),
        trust_remote_code=config["model"].get("trust_remote_code", False),
    )

    dataset_config = config["dataset"]
    dataset = load_dataset(
        dataset_config["path"],
        split=dataset_config.get("split", "train"),
        streaming=dataset_config.get("streaming", False),
    )

    if dataset_config.get("streaming", False):
        dataset = dataset.take(dataset_config.get("max_samples", 1024))
        dataset = list(dataset)

    text_field = dataset_config.get("text_field", "text")

    def tokenize(batch):
        return model_bundle.tokenizer(
            batch[text_field],
            truncation=True,
            max_length=config["training"].get("max_length", 2048),
        )

    tokenized = dataset.map(tokenize, batched=True)
    collator = DataCollatorForLanguageModeling(tokenizer=model_bundle.tokenizer, mlm=False)
    args = TrainingArguments(
        output_dir=config["training"].get("output_dir", "artifacts/sft"),
        num_train_epochs=config["training"].get("epochs", 1),
        per_device_train_batch_size=config["training"].get("per_device_batch_size", 1),
        gradient_accumulation_steps=config["training"].get("gradient_accumulation_steps", 1),
        learning_rate=config["training"].get("learning_rate", 2e-5),
        bf16=config["training"].get("bf16", False),
        logging_steps=config["training"].get("logging_steps", 10),
        save_steps=config["training"].get("save_steps", 200),
        report_to=config["training"].get("report_to", []),
    )

    trainer = Trainer(
        model=model_bundle.model,
        tokenizer=model_bundle.tokenizer,
        args=args,
        train_dataset=tokenized,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(args.output_dir)

    return SFTTrainingResult(
        output_dir=args.output_dir,
        epochs=int(args.num_train_epochs),
        learning_rate=float(args.learning_rate),
    )