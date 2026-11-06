"""
OSIRIS v5.0 NCLM Core SIMD & KV-Cache Acceleration Benchmark
=============================================================
Measures generation throughput, forward pass latency, and C-SIMD
vectorization speedup.
"""

import time
import numpy as np
from osiris_cli.osiris_repl import get_living
from osiris.nclm.fast_inference import HAVE_C_SIMD

def main():
    print("=" * 70)
    print(" OSIRIS v5.0 NCLM Living Core Acceleration Benchmark")
    print("=" * 70)
    print(f"AVX2 C-SIMD Extension: {'ACTIVE' if HAVE_C_SIMD else 'FALLBACK (NumPy)'}")

    living = get_living()
    model = living.core._model()["model"]
    print(f"Model Architecture: {type(model).__name__}")
    print(f"Model Parameters  : {sum(p.data.size for p in model.parameters()):,}")
    print(f"Context Window    : {model.config.max_seq_len} bytes")
    print(f"Layers / Heads    : {model.config.n_layers} layers / {model.config.n_heads} heads")

    print("\n[1] Forward Pass Latency across Context Lengths:")
    for seq_len in [64, 128, 256, 512]:
        x = np.random.randint(0, 256, (1, seq_len))
        t0 = time.time()
        n_iters = 10
        for _ in range(n_iters):
            _ = model.forward(x)
        t1 = time.time()
        ms = (t1 - t0) * 1000 / n_iters
        print(f"  · Sequence Length {seq_len:3d}: {ms:6.2f} ms per forward pass")

    print("\n[2] Autoregressive Generation Throughput (KV-Cache + AVX2):")
    for tokens in [32, 64, 128]:
        t0 = time.time()
        res = model.generate("User: what have you learned\nOSIRIS:", max_new_tokens=tokens, temperature=0.7)
        t1 = time.time()
        elapsed = t1 - t0
        rate = tokens / elapsed if elapsed > 0 else 0
        print(f"  · {tokens:3d} tokens generated in {elapsed:.3f} s ({rate:6.1f} tokens/s)")

    print("\n[3] Living REPL Core Draft Benchmark:")
    t0 = time.time()
    draft = living.core.draft("User: who are you\nOSIRIS:", max_bytes=96)
    t1 = time.time()
    print(f"  · Core Draft Latency: {(t1-t0)*1000:.1f} ms ({len(draft)} characters generated)")
    print(f"  · Output Excerpt    : {repr(draft[:70])}")
    print("=" * 70)

if __name__ == "__main__":
    main()
