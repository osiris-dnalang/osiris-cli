import random
import math

class SpinSystem:
    """
    Spintronics-inspired agent interaction system (Ising model).
    Each agent is a spin node. J matrix encodes interaction strengths.
    Epsilon is the chaos/noise parameter.
    """
    def __init__(self, agent_names=None, J=None, epsilon=0.3):
        if agent_names is None:
            agent_names = ["student", "mentor", "critic", "judge"]
        self.spins = {name: 1 for name in agent_names}
        self.J = J or {
            ("student","mentor"): 1.0,
            ("student","critic"): -1.2,
            ("student","judge"): 0.8
        }
        self.epsilon = epsilon
        self.history = []

    def step(self):
        new_spins = {}
        for i in self.spins:
            influence = 0
            for (a,b), w in self.J.items():
                if a == i:
                    influence += w * self.spins[b]
            noise = self.epsilon * random.uniform(-1,1)
            new_spins[i] = 1 if (influence + noise) >= 0 else -1
        self.spins = new_spins
        self.history.append(dict(self.spins))

    def get_state(self):
        return dict(self.spins)

    def entropy(self):
        weights = [abs(v) for v in self.spins.values()]
        total = sum(weights)
        if total == 0:
            return 0.0
        probs = [w/total for w in weights if w > 0]
        return -sum(p * math.log(p) for p in probs)

    def tune_chaos(self, Hmin=0.3, Hmax=1.2):
        H = self.entropy()
        if H < Hmin:
            self.epsilon += 0.05
        elif H > Hmax:
            self.epsilon = max(0.01, self.epsilon - 0.05)
        # Clamp epsilon
        self.epsilon = min(max(self.epsilon, 0.01), 1.0)
        return self.epsilon

    def converged(self, threshold=0.01):
        if len(self.history) < 2:
            return False
        prev = sum(self.history[-2].values())
        curr = sum(self.history[-1].values())
        return abs(curr - prev) < threshold
