failure_memory = []

def log_failure(q, reason):
    failure_memory.append({
        "input": q,
        "failure": reason
    })

def sample_failure():
    import random
    if not failure_memory:
        return None
    return random.choice(failure_memory)
