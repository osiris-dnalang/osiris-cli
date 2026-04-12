import time
from osiris_core.generator import generate_code
from osiris.agents import planner_agent, auditor_agent, refactor_agent, tester_agent
from osiris_learning.memory import store_experience
from osiris_learning.elo import update_elo

from osiris_autonomous.goal_engine import Goal, Agent

def run_autonomous():
    agents = [Agent("planner"), Agent("tester"), Agent("refactor"), Agent("auditor")]
    while True:
        task = generate_task()
        goal = Goal(task)
        while not goal.converged():
            subtask = goal.next_task()
            prompt = planner_agent(subtask)
            code = generate_code(prompt)
            improved = refactor_agent(code)
            tests = tester_agent(improved)
            result = run_tests(tests)
            score = float(result)
            goal.update(improved, score)
            if score < 0.7:
                goal.spawn_subtasks(improved, agents)
            store_experience({
                "task": subtask,
                "code": code,
                "improved": improved,
                "result": result
            })
            update_elo("generator", result)
            print(f"[OSIRIS] Task: {subtask} → {'PASS' if result else 'FAIL'}")
            time.sleep(2)
