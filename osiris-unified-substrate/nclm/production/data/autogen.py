"""Automatic dataset generation at scale for OSIRIS NCLM.

Generates SFT, preference, and benchmark-style training data from:
  - Synthetic templates (math, QA, code)
  - Seed prompts with self-instruct expansion
  - Existing datasets with reformulation

Usage:
    python -m nclm.production.data.autogen --output data/dataset.jsonl --count 500
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional


@dataclass
class GeneratedSample:
    """A single generated training sample with provenance."""
    prompt: str
    response: str
    source: str  # template name / generator
    difficulty: str  # easy, medium, hard
    domain: str  # math, qa, code, reasoning
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sft_record(self) -> Dict[str, str]:
        return {"text": f"User: {self.prompt}\nAssistant: {self.response}"}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---- Math generators ----

def _gen_arithmetic(count: int, difficulty: str = "medium") -> List[GeneratedSample]:
    samples = []
    ranges = {"easy": (1, 100), "medium": (10, 9999), "hard": (100, 999999)}
    lo, hi = ranges.get(difficulty, (10, 9999))
    ops = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("*", lambda a, b: a * b),
    ]
    for _ in range(count):
        a, b = random.randint(lo, hi), random.randint(lo, hi)
        sym, fn = random.choice(ops)
        result = fn(a, b)
        prompt = f"Calculate: {a} {sym} {b}"
        cot = f"Step 1: We need to compute {a} {sym} {b}\nStep 2: {a} {sym} {b} = {result}\n\nThe answer is {result}."
        samples.append(GeneratedSample(
            prompt=prompt, response=cot, source="arithmetic",
            difficulty=difficulty, domain="math",
        ))
    return samples


def _gen_word_problems(count: int) -> List[GeneratedSample]:
    templates = [
        ("A store has {a} apples. {b} more arrive. How many apples total?",
         lambda a, b: a + b, "+"),
        ("{name} reads {a} pages per day for {b} days. Total pages?",
         lambda a, b: a * b, "*"),
        ("A pool has {a} liters. {b} liters drain out. How many remain?",
         lambda a, b: a - b, "-"),
        ("{name} has ${a}. They earn ${b} more. What's the total?",
         lambda a, b: a + b, "+"),
    ]
    names = ["Alice", "Bob", "Charlie", "Diana", "Ethan"]
    samples = []
    for _ in range(count):
        tmpl, fn, op = random.choice(templates)
        a, b = random.randint(5, 500), random.randint(1, 200)
        name = random.choice(names)
        q = tmpl.format(a=a, b=b, name=name)
        ans = fn(a, b)
        cot = f"We need to find the result.\n{a} {op} {b} = {ans}\n\nThe answer is {ans}."
        samples.append(GeneratedSample(
            prompt=q, response=cot, source="word_problem",
            difficulty="medium", domain="math",
        ))
    return samples


# ---- QA generators ----

_KNOWLEDGE_BANK = [
    ("What is the chemical symbol for water?", "H₂O", "chemistry"),
    ("What year did World War II end?", "1945", "history"),
    ("What is the largest planet in our solar system?", "Jupiter", "astronomy"),
    ("What organelle is the powerhouse of the cell?", "Mitochondria", "biology"),
    ("What is Newton's second law?", "F = ma (Force equals mass times acceleration)", "physics"),
    ("What is the capital of Japan?", "Tokyo", "geography"),
    ("What is the Pythagorean theorem?", "a² + b² = c²", "mathematics"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci", "art"),
    ("What is the speed of light approximately?", "3 × 10⁸ meters per second", "physics"),
    ("What programming language was created by Guido van Rossum?", "Python", "computer science"),
    ("What is the derivative of x²?", "2x", "calculus"),
    ("What is the pH of pure water at 25°C?", "7", "chemistry"),
    ("What is Schrödinger's equation used for?", "Describing how quantum states evolve over time", "quantum physics"),
    ("What data structure uses FIFO ordering?", "Queue", "computer science"),
    ("What is the Big O of binary search?", "O(log n)", "algorithms"),
]


def _gen_qa(count: int) -> List[GeneratedSample]:
    samples = []
    for _ in range(count):
        q, a, topic = random.choice(_KNOWLEDGE_BANK)
        samples.append(GeneratedSample(
            prompt=q, response=a, source="knowledge_bank",
            difficulty="easy", domain="qa",
            metadata={"topic": topic},
        ))
    return samples


# ---- Code generators ----

_CODE_TEMPLATES = [
    ("Write a function to reverse a string.",
     "def reverse_string(s: str) -> str:\n    return s[::-1]"),
    ("Write a function to check if a number is prime.",
     "def is_prime(n: int) -> bool:\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True"),
    ("Write a function to flatten a nested list.",
     "def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result"),
    ("Write a function to find the GCD of two numbers.",
     "def gcd(a: int, b: int) -> int:\n    while b:\n        a, b = b, a % b\n    return a"),
    ("Write a function to count vowels in a string.",
     "def count_vowels(s: str) -> int:\n    return sum(1 for c in s.lower() if c in 'aeiou')"),
    ("Write a function to merge two sorted lists.",
     "def merge_sorted(a, b):\n    result, i, j = [], 0, 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i]); i += 1\n        else:\n            result.append(b[j]); j += 1\n    result.extend(a[i:])\n    result.extend(b[j:])\n    return result"),
    ("Write a function to compute the nth Fibonacci number.",
     "def fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b"),
    ("Write a binary search function.",
     "def binary_search(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1"),
]


def _gen_code(count: int) -> List[GeneratedSample]:
    samples = []
    for _ in range(count):
        prompt, code = random.choice(_CODE_TEMPLATES)
        samples.append(GeneratedSample(
            prompt=prompt, response=code, source="code_template",
            difficulty="medium", domain="code",
        ))
    return samples


# ---- Reasoning generators ----

def _gen_reasoning(count: int) -> List[GeneratedSample]:
    tasks = [
        ("If all roses are flowers and all flowers are plants, are all roses plants?",
         "Yes. Since all roses are flowers, and all flowers are plants, by transitivity all roses are plants."),
        ("A bat and ball cost $1.10 total. The bat costs $1 more than the ball. How much does the ball cost?",
         "Let ball = x. Bat = x + 1. So x + (x+1) = 1.10 → 2x = 0.10 → x = 0.05. The ball costs $0.05."),
        ("If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
         "Each machine makes 1 widget in 5 minutes. So 100 machines make 100 widgets in 5 minutes."),
        ("Three boxes: one has apples, one has oranges, one has both. All labels are wrong. You pick one fruit from the 'both' box. How do you label all boxes?",
         "Since all labels are wrong, the 'both' box has only one type. Pick a fruit — that tells you what it actually contains. Then the remaining two labels are also wrong, so you can deduce the rest."),
    ]
    samples = []
    for _ in range(count):
        q, a = random.choice(tasks)
        samples.append(GeneratedSample(
            prompt=q, response=a, source="reasoning",
            difficulty="hard", domain="reasoning",
        ))
    return samples


# ---- Preference pair generators ----

def _gen_preference_pairs(count: int) -> List[Dict[str, str]]:
    """Generate chosen/rejected pairs for RLHF preference training."""
    pairs = []
    for _ in range(count):
        a, b = random.randint(1, 999), random.randint(1, 999)
        result = a + b
        prompt = f"What is {a} + {b}?"
        chosen = f"Let me calculate: {a} + {b} = {result}. The answer is {result}."
        rejected_val = result + random.choice([-3, -2, -1, 1, 2, 3])
        rejected = f"The answer is {rejected_val}."
        pairs.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
    return pairs


# ---- Main generator ----

DOMAIN_GENERATORS = {
    "math": lambda n: _gen_arithmetic(n // 2) + _gen_word_problems(n - n // 2),
    "qa": _gen_qa,
    "code": _gen_code,
    "reasoning": _gen_reasoning,
}


def generate_dataset(
    count: int = 200,
    domains: Optional[List[str]] = None,
    seed: int = 42,
) -> List[GeneratedSample]:
    """Generate a mixed training dataset across multiple domains."""
    random.seed(seed)
    active_domains = domains or list(DOMAIN_GENERATORS.keys())
    per_domain = max(1, count // len(active_domains))
    remainder = count - per_domain * len(active_domains)

    all_samples: List[GeneratedSample] = []
    for i, domain in enumerate(active_domains):
        gen = DOMAIN_GENERATORS.get(domain)
        if gen:
            n = per_domain + (1 if i < remainder else 0)
            all_samples.extend(gen(n))

    random.shuffle(all_samples)
    return all_samples[:count]


def generate_preference_dataset(count: int = 100, seed: int = 42) -> List[Dict[str, str]]:
    """Generate preference pairs for RLHF training."""
    random.seed(seed)
    return _gen_preference_pairs(count)


def save_sft_jsonl(samples: List[GeneratedSample], path: str | Path) -> Path:
    """Save samples as JSONL suitable for SFT training."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(json.dumps(s.to_sft_record(), ensure_ascii=False) + "\n")
    return out


def save_full_jsonl(samples: List[GeneratedSample], path: str | Path) -> Path:
    """Save samples as JSONL with full metadata."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    return out


def save_preference_jsonl(pairs: List[Dict[str, str]], path: str | Path) -> Path:
    """Save preference pairs as JSONL."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    return out
