"""osiris.nclm — Non-Classical Logic Machine + SovereignTransformer."""

from .core.engine import (
    NCPhysics,
    ManifoldPoint,
    PilotWaveCorrelation,
    ConsciousnessField,
    IntentDeducer,
    CodeSwarm,
    NonCausalLM,
    get_nclm,
)

from .autograd import Tensor, softmax, log_softmax, gelu, cross_entropy_loss, no_grad
from .layers import Module, Embedding, Linear, LayerNorm, GELU, Dropout
from .positions import phase_conjugate_positional_encoding
from .transformer import SovereignTransformer, SovereignConfig
from .optimizer import AdamW, LRSchedule
from .trainer import Trainer, TrainingConfig
from .inference import (
    generate, save_safetensors, load_safetensors,
    load_model_safetensors, export_huggingface,
)

__all__ = [
    # Legacy NCLM
    "NCPhysics", "ManifoldPoint", "PilotWaveCorrelation",
    "ConsciousnessField", "IntentDeducer", "CodeSwarm",
    "NonCausalLM", "get_nclm",
    # Autograd
    "Tensor", "softmax", "log_softmax", "gelu", "cross_entropy_loss", "no_grad",
    # Layers
    "Module", "Embedding", "Linear", "LayerNorm", "GELU", "Dropout",
    # Positions
    "phase_conjugate_positional_encoding",
    # Transformer
    "SovereignTransformer", "SovereignConfig",
    # Optimizer
    "AdamW", "LRSchedule",
    # Trainer
    "Trainer", "TrainingConfig",
    # Inference & Export
    "generate", "save_safetensors", "load_safetensors",
    "load_model_safetensors", "export_huggingface",
]
