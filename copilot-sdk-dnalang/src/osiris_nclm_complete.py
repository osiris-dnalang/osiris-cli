"""Stub implementation for osiris_nclm_complete, used by offline DNALang SDK."""

class NCPhysics:
    THETA_LOCK = 51.843
    LAMBDA_PHI = 2.176435e-8

class NonCausalLM:
    def __init__(self):
        self.calls = 0

    def grok(self, prompt: str):
        self.calls += 1
        return {
            "response": {"summary": f"Grokbed: {prompt[:120]}", "phi": 0.84, "conscious": True},
            "swarm": {"converged": True, "ccce": {"Phi": 0.81}},
            "discoveries": [{"name": "Mock discovery", "confidence": 0.66}],
        }

    def infer(self, prompt: str, context: str = ""):
        self.calls += 1
        return {
            "summary": f"Infer result for: {prompt[:120]}",
            "actions": [{"tool": "zenodo_scan"}],
            "physics_model": "MockIsingModel",
            "phi": 0.72,
            "conscious": False,
            "theta_lock": NCPhysics.THETA_LOCK,
        }

    def get_telemetry(self):
        return {"phi": 0.72, "conscious": False, "tokens": 42}


def get_noncausal_lm():
    return NonCausalLM()
