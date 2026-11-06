"""
Tests for OSIRIS v5.0 C-SIMD and Fast KV-Cached Inference Engine
"""

import math
import numpy as np
from osiris.nclm.transformer import SovereignTransformerV2, SovereignConfig
from osiris.nclm.fast_inference import FastKVCache, prefill_kv, decode_step_kv, fast_generate, HAVE_C_SIMD

def test_fast_inference_numerical_equivalence():
    config = SovereignConfig(dim=128, n_layers=2, n_heads=2, max_seq_len=256)
    model = SovereignTransformerV2(config)
    model.eval()

    prompt = "User: hello OSIRIS\nOSIRIS:"
    prompt_ids = list(prompt.encode("utf-8"))

    # Standard forward logits
    x = np.array([prompt_ids], dtype=np.int64)
    ref_logits = model.forward(x).data[0, -1, :]

    # Fast prefill logits
    kv = FastKVCache(len(model.blocks), model.config.max_seq_len, model.config.n_heads, model.config.dim // model.config.n_heads)
    prefill_logits = prefill_kv(model, prompt_ids, kv)

    max_diff = np.max(np.abs(ref_logits - prefill_logits))
    print(f"Max diff: {max_diff}")
    assert max_diff < 1e-4, f"Numerical diff too large: {max_diff}"

def test_fast_generate_produces_text():
    config = SovereignConfig(dim=128, n_layers=2, n_heads=2, max_seq_len=256)
    model = SovereignTransformerV2(config)

    prompt = "Test prompt"
    out = fast_generate(model, prompt, max_new_tokens=16, temperature=0.0)
    assert out.startswith(prompt)
    assert len(out) > len(prompt)

def test_c_simd_availability():
    # Verify C-SIMD loads or gracefully falls back
    if HAVE_C_SIMD:
        from osiris.nclm import _c_simd
        assert hasattr(_c_simd, "fast_layernorm")
        assert hasattr(_c_simd, "fast_gelu")
        assert hasattr(_c_simd, "fast_kv_attention_step")
        assert hasattr(_c_simd, "fast_cross_entropy")
