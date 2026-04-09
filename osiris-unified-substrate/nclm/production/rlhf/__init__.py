"""Run PPO alignment standalone: python -m nclm.production.rlhf.ppo_trainer [--config configs/rlhf.yaml]"""

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="OSIRIS NCLM RLHF (PPO) Training")
    parser.add_argument("--config", default="configs/rlhf.yaml", help="Path to RLHF config")
    parser.add_argument("--model", default=None, help="Base model name/path")
    parser.add_argument("--reward-model", default=None, help="Reward model name/path")
    parser.add_argument("--dataset", default=None, help="Preference dataset path (JSONL)")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--target-kl", type=float, default=None, help="Override target KL")
    parser.add_argument("--load-in-4bit", action="store_true", help="Use 4-bit quantization")
    args = parser.parse_args()

    try:
        from ..config import load_config
        config = load_config(args.config)
    except Exception:
        config = {"ppo": {"batch_size": 4, "learning_rate": 1e-5, "target_kl": 0.1}}

    ppo_cfg = config.get("ppo", {})
    if args.batch_size:
        ppo_cfg["batch_size"] = args.batch_size
    if args.lr:
        ppo_cfg["learning_rate"] = args.lr
    if args.target_kl:
        ppo_cfg["target_kl"] = args.target_kl

    model_name = args.model or config.get("reward", {}).get("base_model", "Qwen/Qwen2.5-7B-Instruct")
    dataset_path = args.dataset or config.get("dataset", {}).get("path", "data/preferences.jsonl")

    print(f"Model:   {model_name}")
    print(f"Dataset: {dataset_path}")
    print(f"PPO Config: {json.dumps(ppo_cfg, indent=2)}")

    from ..core.model_loader import load_model_bundle

    extra_kwargs = {}
    if args.load_in_4bit:
        extra_kwargs["extra_model_kwargs"] = {"load_in_4bit": True}

    bundle = load_model_bundle(model_name, device_map="auto", torch_dtype="bfloat16", **extra_kwargs)

    from ..rlhf.reward_model import RewardModel
    reward_model = RewardModel(bundle.model)

    from ..rlhf.preference_dataset import load_preference_jsonl
    samples = load_preference_jsonl(dataset_path)
    dataset_iter = [{"prompt": s.prompt, "chosen": s.chosen, "rejected": s.rejected} for s in samples]

    from .ppo_trainer import PPOTrainingConfig, run_ppo
    ppo_config = PPOTrainingConfig(**ppo_cfg)
    trainer = run_ppo(bundle.model, bundle.tokenizer, reward_model, dataset_iter, config=ppo_config)

    print("\nPPO training complete.")


if __name__ == "__main__":
    main()
