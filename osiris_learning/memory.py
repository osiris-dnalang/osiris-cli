import json
import os

class Memory:
    """
    Persistent memory for agent state, beliefs, and identity.
    """
    def __init__(self, state_file="osiris_state.json"):
        self.history = []
        self.beliefs = {}
        self.identity = {
            "beliefs": [],
            "skills": [],
            "failures": [],
            "style": {}
        }
        self.state_file = state_file
        self.load()

    def store(self, item):
        """Store an item in history and update beliefs."""
        self.history.append(item)
        key = item["q"]
        self.beliefs[key] = item["score"].get("confidence", 0.0)

    def dominant_source(self):
        """Return the most frequent source in history, or None if empty."""
        if not self.history:
            return None
        sources = [h.get("source", "mentor") for h in self.history]
        return max(set(sources), key=sources.count)

    def update_identity(self, reflection, score):
        """Update identity with a reflection based on confidence score."""
        if score["confidence"] > 0.75:
            self.identity["skills"].append(reflection)
        else:
            self.identity["failures"].append(reflection)

    def save(self):
        """Save memory state to disk."""
        with open(self.state_file, "w") as f:
            json.dump({
                "history": self.history,
                "beliefs": self.beliefs,
                "identity": self.identity
            }, f, indent=2)

    def load(self):
        """Load memory state from disk if available."""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self.history = data.get("history", [])
                self.beliefs = data.get("beliefs", {})
                self.identity = data.get("identity", self.identity)
