"""Run the evaluation harness standalone: python -m nclm.production.eval.harness [--config configs/eval.yaml]"""

import argparse
import json
import sys
from pathlib import Path


def _dummy_predict(prompt: str) -> str:
    """Placeholder predict_fn used when no model is loaded (dry-run mode)."""
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Evaluation Harness")
    parser.add_argument("--config", default="configs/eval.yaml", help="Path to eval config")
    parser.add_argument("--output", default=None, help="Write results JSON to this path")
    parser.add_argument("--model", default=None, help="HuggingFace model to evaluate (omit for dry-run)")
    parser.add_argument("--tasks", nargs="*", default=None, help="Task names to run (default: all)")
    parser.add_argument("--max-samples", type=int, default=200, help="Max samples per task")
    parser.add_argument("--streaming", action="store_true", help="Use streaming dataset loading")
    args = parser.parse_args()

    # Load config
    try:
        from ..config import load_config
        config = load_config(args.config)
    except Exception:
        config = {"tasks": ["mmlu", "gsm8k", "humaneval"], "output_path": "artifacts/eval/results.json"}

    tasks = args.tasks or config.get("tasks", ["mmlu", "gsm8k", "humaneval"])
    output_path = args.output or config.get("output_path", "artifacts/eval/results.json")

    # Build predict function
    if args.model:
        try:
            from ..core.model_loader import load_model_bundle
            print(f"Loading model: {args.model} ...")
            bundle = load_model_bundle(args.model, device_map="auto", torch_dtype="bfloat16")
            model, tokenizer = bundle.model, bundle.tokenizer

            def predict_fn(prompt: str) -> str:
                inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
                outputs = model.generate(**inputs, max_new_tokens=256, do_sample=False)
                return tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        except Exception as exc:
            print(f"Failed to load model: {exc}. Falling back to dry-run.")
            predict_fn = _dummy_predict
    else:
        print("No --model specified. Running dry-run (all scores will be 0).")
        predict_fn = _dummy_predict

    # Build datasets
    datasets: dict = {}
    for task in tasks:
        try:
            from datasets import load_dataset as hf_load
            if task == "mmlu":
                ds = hf_load("cais/mmlu", "all", split="test", streaming=args.streaming, trust_remote_code=True)
                if args.streaming:
                    ds = list(ds.take(args.max_samples))
                else:
                    ds = list(ds.select(range(min(len(ds), args.max_samples))))
                datasets["mmlu"] = [{"question": row["question"], "answer": row["answer"]} for row in ds]
            elif task == "gsm8k":
                ds = hf_load("openai/gsm8k", "main", split="test", streaming=args.streaming)
                if args.streaming:
                    ds = list(ds.take(args.max_samples))
                else:
                    ds = list(ds.select(range(min(len(ds), args.max_samples))))
                datasets["gsm8k"] = [{"question": row["question"], "answer": row["answer"]} for row in ds]
            elif task == "humaneval":
                ds = hf_load("openai/openai_humaneval", split="test", streaming=args.streaming)
                if args.streaming:
                    ds = list(ds.take(args.max_samples))
                else:
                    ds = list(ds.select(range(min(len(ds), args.max_samples))))
                datasets["humaneval"] = [{"prompt": row["prompt"], "tests": row.get("test", "")} for row in ds]
        except Exception as exc:
            print(f"Could not load dataset for {task}: {exc}")
            datasets[task] = []

    # Run evaluation
    from . import harness as _h
    results = _h.run_all(predict_fn=predict_fn, datasets=datasets, tasks=tasks)

    print(f"\n{'='*50}")
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(json.dumps(results, indent=2))

    # Save
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
