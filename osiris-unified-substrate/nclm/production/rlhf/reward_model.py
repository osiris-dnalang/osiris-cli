from typing import Any


try:
    import torch.nn as nn
except ImportError:
    nn = None


if nn is None:
    class RewardModel:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError(
                "RewardModel requires PyTorch. Install 'torch' before using RLHF components."
            )
else:
    class RewardModel(nn.Module):
        """Minimal scalar reward head for preference learning."""

        def __init__(self, base_model: Any):
            super().__init__()
            self.base = base_model
            self.head = nn.Linear(base_model.config.hidden_size, 1)

        def forward(self, input_ids, attention_mask):
            outputs = self.base(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
            )
            last_hidden = outputs.hidden_states[-1][:, -1, :]
            return self.head(last_hidden)