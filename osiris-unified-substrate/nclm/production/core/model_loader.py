from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LoadedModelBundle:
    model: Any
    tokenizer: Any
    config: Any
    backend: str = "transformers"
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_model_bundle(
    model_name: str,
    tokenizer_name: Optional[str] = None,
    revision: Optional[str] = None,
    device_map: str | Dict[str, int] = "auto",
    torch_dtype: Optional[str] = None,
    gradient_checkpointing: bool = False,
    attn_implementation: Optional[str] = None,
    trust_remote_code: bool = False,
    extra_model_kwargs: Optional[Dict[str, Any]] = None,
) -> LoadedModelBundle:
    """Load a Hugging Face model/tokenizer pair with production-friendly toggles."""
    try:
        import torch
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Model loading requires 'torch' and 'transformers'. "
            "Install them before using the production training stack."
        ) from exc

    dtype = getattr(torch, torch_dtype) if torch_dtype else None
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_name or model_name,
        revision=revision,
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    config = AutoConfig.from_pretrained(
        model_name,
        revision=revision,
        trust_remote_code=trust_remote_code,
    )

    model_kwargs = dict(extra_model_kwargs or {})
    model_kwargs.update(
        {
            "revision": revision,
            "device_map": device_map,
            "trust_remote_code": trust_remote_code,
        }
    )
    if dtype is not None:
        model_kwargs["torch_dtype"] = dtype
    if attn_implementation:
        model_kwargs["attn_implementation"] = attn_implementation

    # --- Quantization support (QLoRA / bitsandbytes) ---
    load_in_4bit = model_kwargs.pop("load_in_4bit", False)
    load_in_8bit = model_kwargs.pop("load_in_8bit", False)
    if load_in_4bit or load_in_8bit:
        try:
            from transformers import BitsAndBytesConfig
            quant_config = BitsAndBytesConfig(
                load_in_4bit=load_in_4bit,
                load_in_8bit=load_in_8bit,
                bnb_4bit_compute_dtype=dtype or torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            model_kwargs["quantization_config"] = quant_config
        except ImportError:
            raise RuntimeError(
                "4-bit / 8-bit quantization requires 'bitsandbytes'. "
                "Install it with: pip install bitsandbytes"
            )

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    if gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    return LoadedModelBundle(
        model=model,
        tokenizer=tokenizer,
        config=config,
        metadata={
            "model_name": model_name,
            "tokenizer_name": tokenizer_name or model_name,
            "revision": revision,
            "gradient_checkpointing": gradient_checkpointing,
            "attn_implementation": attn_implementation,
            "torch_dtype": torch_dtype,
        },
    )