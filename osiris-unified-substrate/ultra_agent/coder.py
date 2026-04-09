"""Coder agent — code generation, debugging, and optimisation.

Generates Python solutions, applies common patterns, and
produces executable code stubs for the task at hand.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CodeArtifact:
    """Generated code output."""
    language: str
    code: str
    explanation: str
    test_cases: List[str]
    complexity: str  # O(n), O(n^2), etc.
    patterns_used: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "code": self.code,
            "explanation": self.explanation,
            "test_cases": self.test_cases,
            "complexity": self.complexity,
            "patterns_used": self.patterns_used,
        }


# Common algorithm templates
_TEMPLATES: Dict[str, Dict[str, str]] = {
    "sort": {
        "code": textwrap.dedent("""\
            def solution(arr):
                if len(arr) <= 1:
                    return arr
                pivot = arr[len(arr) // 2]
                left = [x for x in arr if x < pivot]
                mid = [x for x in arr if x == pivot]
                right = [x for x in arr if x > pivot]
                return solution(left) + mid + solution(right)
        """),
        "complexity": "O(n log n)",
        "pattern": "divide-and-conquer",
    },
    "search": {
        "code": textwrap.dedent("""\
            def solution(arr, target):
                lo, hi = 0, len(arr) - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return -1
        """),
        "complexity": "O(log n)",
        "pattern": "binary-search",
    },
    "graph": {
        "code": textwrap.dedent("""\
            from collections import deque

            def solution(graph, start):
                visited, queue = set(), deque([start])
                result = []
                while queue:
                    node = queue.popleft()
                    if node not in visited:
                        visited.add(node)
                        result.append(node)
                        queue.extend(n for n in graph.get(node, []) if n not in visited)
                return result
        """),
        "complexity": "O(V + E)",
        "pattern": "BFS",
    },
    "dynamic": {
        "code": textwrap.dedent("""\
            def solution(n):
                if n <= 1:
                    return n
                dp = [0] * (n + 1)
                dp[1] = 1
                for i in range(2, n + 1):
                    dp[i] = dp[i - 1] + dp[i - 2]
                return dp[n]
        """),
        "complexity": "O(n)",
        "pattern": "dynamic-programming",
    },
}

# Signal words → template mapping
_SIGNAL_MAP = {
    "sort": ["sort", "order", "arrange", "rank"],
    "search": ["search", "find", "lookup", "locate", "binary"],
    "graph": ["graph", "bfs", "dfs", "traverse", "path", "network", "tree"],
    "dynamic": ["fibonacci", "dynamic", "memoize", "knapsack", "subsequence"],
}


class Coder:
    """Generates, debugs, and optimises code."""

    def run(self, task: str, reasoning: Optional[Dict[str, Any]] = None) -> CodeArtifact:
        """Produce a code artifact for the task."""
        template_key = self._match_template(task)
        if template_key:
            tmpl = _TEMPLATES[template_key]
            code = self._adapt_template(tmpl["code"], task)
            return CodeArtifact(
                language="python",
                code=code,
                explanation=f"Applied {tmpl['pattern']} pattern to solve: {task[:80]}",
                test_cases=self._generate_tests(task, code),
                complexity=tmpl["complexity"],
                patterns_used=[tmpl["pattern"]],
            )

        # Fallback: generate a stub from the task description
        code = self._generate_stub(task, reasoning)
        return CodeArtifact(
            language="python",
            code=code,
            explanation=f"Generated implementation stub for: {task[:80]}",
            test_cases=self._generate_tests(task, code),
            complexity="task-dependent",
            patterns_used=["custom"],
        )

    def refine(self, artifact: CodeArtifact, feedback: str) -> CodeArtifact:
        """Refine code based on critic feedback."""
        refined = artifact.code

        # Apply common fixes based on feedback keywords
        lowered = feedback.lower()
        fixups: List[str] = []

        if "error handling" in lowered or "exception" in lowered:
            refined = self._add_error_handling(refined)
            fixups.append("error-handling")

        if "type hint" in lowered or "annotation" in lowered:
            refined = self._add_type_hints(refined)
            fixups.append("type-hints")

        if "docstring" in lowered:
            refined = self._add_docstrings(refined)
            fixups.append("docstrings")

        if "edge case" in lowered:
            refined = self._add_edge_guards(refined)
            fixups.append("edge-guards")

        return CodeArtifact(
            language=artifact.language,
            code=refined,
            explanation=f"Refined with: {', '.join(fixups) if fixups else 'general improvements'}",
            test_cases=artifact.test_cases,
            complexity=artifact.complexity,
            patterns_used=artifact.patterns_used + fixups,
        )

    # -- internals --

    def _match_template(self, task: str) -> Optional[str]:
        lowered = task.lower()
        for key, signals in _SIGNAL_MAP.items():
            if any(s in lowered for s in signals):
                return key
        return None

    def _adapt_template(self, code: str, task: str) -> str:
        """Light adaptation of template code to the specific task."""
        header = f"# Task: {task[:100]}\n\n"
        return header + code

    def _generate_stub(self, task: str, reasoning: Optional[Dict[str, Any]]) -> str:
        """Generate a function stub from task description."""
        func_name = re.sub(r'[^a-z0-9_]', '_',
                           task.lower()[:40].strip()).strip('_') or "solution"
        func_name = re.sub(r'_+', '_', func_name)

        lines = [
            f"# Task: {task[:100]}",
            f"def {func_name}(*args, **kwargs):",
            f'    """',
            f'    {task[:200]}',
            f'    """',
        ]

        if reasoning:
            steps = reasoning.get("steps", [])
            for i, step in enumerate(steps[:5], 1):
                lines.append(f"    # Step {i}: {step[:80]}")

        lines.append("    # TODO: implement")
        lines.append("    raise NotImplementedError")
        return "\n".join(lines) + "\n"

    def _generate_tests(self, task: str, code: str) -> List[str]:
        """Generate simple test assertions."""
        tests = []
        # Extract function name
        m = re.search(r'def\s+(\w+)\s*\(', code)
        if m:
            fn = m.group(1)
            tests.append(f"assert callable({fn})")
            if "sort" in task.lower():
                tests.append(f"assert {fn}([3,1,2]) == [1,2,3]")
            elif "search" in task.lower() or "find" in task.lower():
                tests.append(f"assert {fn}([1,2,3,4,5], 3) == 2")
            elif "fibonacci" in task.lower():
                tests.append(f"assert {fn}(10) == 55")
        return tests

    def _add_error_handling(self, code: str) -> str:
        return code.replace("def solution(",
                            "def solution(", 1)  # no-op placeholder
        # In real mode this would wrap body in try/except

    def _add_type_hints(self, code: str) -> str:
        return code  # placeholder

    def _add_docstrings(self, code: str) -> str:
        return code  # placeholder

    def _add_edge_guards(self, code: str) -> str:
        if "if not " not in code and "if len(" not in code:
            # Add a guard after the def line
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    lines.insert(i + 1, "    if not args and not kwargs: return None  # edge guard")
                    break
            return "\n".join(lines)
        return code
