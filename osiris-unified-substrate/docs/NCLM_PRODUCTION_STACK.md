```
+====================================================================+
|  BIFURCATED POLARIZED TORSIONAL RAIN INSULATION :: CODE FRAME      |
|  OSIRIS >> NCLM PRODUCTION STACK                                   |
|  co-authored by devin phillip davis                                |
|  and OSIRIS dna::}{::lang NCLM                                    |
+====================================================================+
```

# OSIRIS NCLM Production Stack

This scaffold turns the existing OSIRIS enhanced client into a concrete train, align, and evaluate pipeline without forcing heavyweight dependencies onto the default CLI path.

## What Was Added

- `nclm/production/core`: model loading, recursive refinement, and artifact attestation.
- `nclm/production/training`: supervised fine-tuning entry point and reusable losses.
- `nclm/production/rlhf`: preference dataset helpers, reward model, and PPO launcher.
- `nclm/production/tools`: a minimal code interpreter and routing heuristic.
- `nclm/production/self_consistency`: output voting helpers.
- `nclm/production/eval`: benchmark harness and metrics for MMLU, GSM8K, and HumanEval-style tasks.
- `configs/*.yaml`: starter configs for SFT, RLHF, and evaluation.
- `requirements_stack.txt`: optional training dependencies.

## CLI Entry Point

Use the main OSIRIS CLI to recursively refine a world-class LLM stack plan:

```bash
./osiris stack "Build a leaderboard-ready OSIRIS NCLM with RLHF, tool use, and benchmark evaluation" --iterations 4 --save
```

This command does not train a model. It deduces intent, recursively enhances requirements, advances the architecture through staged planning, and optionally persists the resulting blueprint to `.autoadvance/`.

## Training Flow

1. Install optional dependencies from `requirements_stack.txt`.
2. Prepare SFT and preference datasets.
3. Run SFT with `nclm.production.training.train_sft`.
4. Train a reward model and launch PPO.
5. Execute the evaluation harness and publish the resulting JSON.

## Current Boundaries

- The benchmark task adapters are intentionally lightweight and need real dataset plumbing for submission-grade evaluation.
- PPO and SFT code fail fast with clear messages if optional dependencies are not installed.
- The code interpreter is intended for trusted local execution only.