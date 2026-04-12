import random

class MutationEngine:
    def mutate(self, config):
        new_config = config.copy()
        new_config["epsilon"] += random.uniform(-0.05, 0.05)
        new_config["epsilon"] = max(0.01, min(1.0, new_config["epsilon"]))
        return new_config
