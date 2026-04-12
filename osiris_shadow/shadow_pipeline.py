import os
import time
import json

from osiris.agents.planner import planner_agent
from osiris.agents.auditor import auditor_agent
from osiris.agents.refactor import refactor_agent
from osiris.agents.tester import tester_agent

from osiris_learning.memory import store_experience
from osiris_learning.elo import update_elo

WATCH_PATH = os.getcwd()

class ShadowPipeline:
    def __init__(self):
        self.file_state = {}

    def watch(self):
        while True:
            for root, _, files in os.walk(WATCH_PATH):
                for f in files:
                    if not f.endswith(".py"):
                        continue

                    path = os.path.join(root, f)
                    mtime = os.path.getmtime(path)

                    if path not in self.file_state or self.file_state[path] != mtime:
                        self.file_state[path] = mtime
                        self.process_file(path)

            time.sleep(1)

    def process_file(self, path):
        print(f"[OSIRIS] Processing change: {path}")

        with open(path, "r") as f:
            original = f.read()

        plan = planner_agent(original)
        audit_score = auditor_agent(original)
        improved = refactor_agent(original)
        tests = tester_agent(improved)

        with open(path, "w") as f:
            f.write(improved)

        test_path = path.replace(".py", "_test.py")
        with open(test_path, "w") as f:
            f.write(tests)

        result = self.run_tests(test_path)

        store_experience({
            "file": path,
            "original": original,
            "improved": improved,
            "audit": audit_score,
            "result": result
        })

        update_elo("refactor_agent", result)

    def run_tests(self, test_path):
        try:
            return os.system(f"python3 {test_path}") == 0
        except:
            return False
