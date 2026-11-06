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

NCLM = NonCausalLM

from .autograd import Tensor, softmax, log_softmax, gelu, cross_entropy_loss, no_grad
from .layers import Module, Embedding, Linear, LayerNorm, GELU, Dropout
from .positions import phase_conjugate_positional_encoding, standard_sinusoidal_positional_encoding
from .transformer import SovereignTransformer, SovereignTransformerV2, SovereignConfig
from .sovereign_mechanics import (
    TorsionLockedAttention, PhaseConjugateCorrector,
    FractalAntennaEmbedding, SovereignBlock, NegentropicTracker,
)
from .bidirectional import (
    BidirectionalAttention, OnlineNegentropicTracker,
    IntrospectiveGovernor, GovernorAction, AnomalyReceipt,
    EpistemicIntrospector, IntrospectionProfile,
)
from .optimizer import AdamW, LRSchedule
from .trainer import Trainer, TrainingConfig
from .inference import (
    generate, save_safetensors, load_safetensors,
    load_model_safetensors, export_huggingface,
)

# The version of the forward pass held-out scores come from (osiris_cli.living.FORWARD, the forward its
# SCORER is defined on). 2 = v4.5.2: the phase-conjugate corrector runs with gradients off as it does in
# training. A copy of this package without the constant (older code, e.g. a stale checkout on PYTHONPATH or
# the phone) scores as 1, never counted.
SCORING_FORWARD = 2

__all__ = [
    "SCORING_FORWARD",
    # Legacy NCLM
    "NCPhysics", "ManifoldPoint", "PilotWaveCorrelation",
    "ConsciousnessField", "IntentDeducer", "CodeSwarm",
    "NonCausalLM", "NCLM", "get_nclm",
    # Autograd
    "Tensor", "softmax", "log_softmax", "gelu", "cross_entropy_loss", "no_grad",
    # Layers
    "Module", "Embedding", "Linear", "LayerNorm", "GELU", "Dropout",
    # Positions
    "phase_conjugate_positional_encoding", "standard_sinusoidal_positional_encoding",
    # Transformer
    "SovereignTransformer", "SovereignTransformerV2", "SovereignConfig",
    # 11D-CRSM Mechanics
    "TorsionLockedAttention", "PhaseConjugateCorrector",
    "FractalAntennaEmbedding", "SovereignBlock", "NegentropicTracker",
    # OSIRIS v5.0 Bidirectional & Introspection
    "BidirectionalAttention", "OnlineNegentropicTracker",
    "IntrospectiveGovernor", "GovernorAction", "AnomalyReceipt",
    "EpistemicIntrospector", "IntrospectionProfile",
    # Optimizer
    "AdamW", "LRSchedule",
    # Trainer
    "Trainer", "TrainingConfig",
    # Inference & Export
    "generate", "save_safetensors", "load_safetensors",
    "load_model_safetensors", "export_huggingface",
]
