def generate_stream_kv(model, tokenizer, prompt, max_tokens=100, temperature=1.0):
    from osiris_ncllm.model import KVCache
    import numpy as np
    tokens = tokenizer.encode(prompt)
    cache = KVCache()
    for t in tokens:
        _ = model.forward([t])  # prime cache if needed
    for _ in range(max_tokens):
        logits = model.forward(tokens)
        probs = np.exp(logits[-1]) / np.sum(np.exp(logits[-1]))
        next_token = np.random.choice(len(probs), p=probs)
        tokens.append(next_token)
        yield tokenizer.decode([next_token])
