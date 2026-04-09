"""Run SFT training standalone: python -m nclm.production.training.train_sft --config configs/train.yaml"""

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Supervised Fine-Tuning")
    parser.add_argument("--config", default="configs/train.yaml", help="Path to training config")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    parser.add_argument("--epochs", type=int, default=None, help="Override number of epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override per-device batch size")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--max-length", type=int, default=None, help="Override max sequence length")
    parser.add_argument("--streaming", action="store_true", help="Force streaming dataset mode")
    parser.add_argument("--load-in-4bit", action="store_true", help="Use 4-bit quantization (QLoRA)")
    args = parser.parse_args()

    overrides = {}
    if args.output_dir:
        overrides.setdefault("training", {})["output_dir"] = args.output_dir
    if args.epochs:
        overrides.setdefault("training", {})["epochs"] = args.epochs
    if args.batch_size:
        overrides.setdefault("training", {})["per_device_batch_size"] = args.batch_size
    if args.lr:
        overrides.setdefault("training", {})["learning_rate"] = args.lr
    if args.max_length:
        overrides.setdefault("training", {})["max_length"] = args.max_length
    if args.streaming:
        overrides.setdefault("dataset", {})["streaming"] = True
    if args.load_in_4bit:
        overrides.setdefault("model", {})["load_in_4bit"] = True

    from .train_sft import train
    result = train(config_path=args.config, overrides=overrides)

    print(f"\n{'='*50}")
    print("SFT TRAINING COMPLETE")
    print("=" * 50)
    print(f"  Output: {result.output_dir}")
    print(f"  Epochs: {result.epochs}")
    print(f"  LR:     {result.learning_rate}")


if __name__ == "__main__":
    main()
