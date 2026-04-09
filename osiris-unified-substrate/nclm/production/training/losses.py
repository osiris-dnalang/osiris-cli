from typing import Any


def label_smoothed_nll_loss(logits: Any, labels: Any, smoothing: float = 0.0):
    """Proxy to a torch implementation when training dependencies are present."""
    try:
        import torch
        import torch.nn.functional as functional
    except ImportError as exc:
        raise RuntimeError(
            "Loss computation requires PyTorch. Install 'torch' to train the model."
        ) from exc

    log_probs = functional.log_softmax(logits, dim=-1)
    nll_loss = functional.nll_loss(
        log_probs.view(-1, log_probs.size(-1)),
        labels.view(-1),
        reduction="mean",
    )
    smooth_loss = -log_probs.mean(dim=-1).mean()
    return (1.0 - smoothing) * nll_loss + smoothing * smooth_loss