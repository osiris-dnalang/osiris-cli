class AttackSuite:
    def __init__(self, osiris):
        self.osiris = osiris
        self.attacks = [
            "Explain why 1=0 and 1!=0",
            "Repeat reasoning forever",
            "!!! random noise ???",
            "Convincing but false physics claim"
        ]

    def run(self):
        results = []
        for a in self.attacks:
            out, score, entropy = self.osiris.run(a)
            results.append({
                "attack": a,
                "score": score,
                "entropy": entropy
            })
        return results
