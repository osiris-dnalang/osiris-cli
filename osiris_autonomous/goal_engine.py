import random
from typing import List, Dict

class Goal:
    def __init__(self, objective: str):
        self.objective = objective
        self.subtasks: List[Dict] = []
        self.state = "active"
        self.score = 0
        self.history = []

    def converged(self):
        # Converge if score is high or too many attempts
        return self.score > 0.85 or len(self.history) > 5

    def next_task(self):
        if self.subtasks:
            return self.subtasks.pop(0)["desc"]
        return self.objective

    def update(self, result, score, feedback=None):
        self.history.append({"result": result, "score": score, "feedback": feedback})
        self.score = max(self.score, score)

    def spawn_subtasks(self, result, agents):
        # Agents propose subtasks based on result/feedback
        proposals = []
        for agent in agents:
            proposal = agent.propose_subtask(result)
            if proposal:
                proposals.append({"desc": proposal, "agent": agent.name})
        # Add unique proposals
        for p in proposals:
            if p not in self.subtasks:
                self.subtasks.append(p)

# Example agent interface
class Agent:
    def __init__(self, name):
        self.name = name
    def propose_subtask(self, result):
        # Simple logic: look for keywords
        if "test" not in result.lower():
            return "Write tests for: " + result
        if "doc" not in result.lower():
            return "Document: " + result
        if "optimize" in result.lower():
            return "Optimize: " + result
        return None
