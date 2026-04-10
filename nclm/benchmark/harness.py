"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              NCLMBenchmark — Performance Harness                             ║
║              ═══════════════════════════════                                 ║
║                                                                              ║
║    Benchmarks the NCLM text generation pipeline:                            ║
║    ├── Generation speed (chars/sec)                                         ║
║    ├── N-gram coherence (linguistic structure)                              ║
║    ├── CCCE metrics (Ξ, Φ, Λ, Γ)                                           ║
║    ├── Corpus likelihood (match to codebase statistics)                     ║
║    └── Printable ratio (fraction of usable output)                          ║
║                                                                              ║
║    Outputs JSON compatible with osiris_benchmark_suite.py format.           ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional

import numpy as np

from osiris_livlm import LivLM, LivLMConfig, PhaseMemory

logger = logging.getLogger("NCLM")


class NCLMBenchmark:
    """
    Benchmark harness for NCLM text generation.

    Runs a suite of tests and collects metrics:
    - Speed: characters per second
    - Coherence: n-gram entropy analysis
    - Physics: CCCE metrics from generation
    - Quality: printable ratio, corpus match

    Usage:
        bench = NCLMBenchmark()
        results = bench.run_suite()
        bench.print_report(results)
    """

    # Benchmark prompts
    PROMPTS = [
        ("code", "def fibonacci(n):"),
        ("prose", "The quantum field "),
        ("comment", "# This function "),
        ("blank", ""),
    ]

    # Lengths to test
    LENGTHS = [32, 64, 128]

    def __init__(self, config: Optional[LivLMConfig] = None):
        self._config = config or LivLMConfig(
            max_generations=10,     # fast evolution for benchmarks
            population_size=15,
            sample_length=16,
        )

    def run_suite(self, evolve_first: bool = True,
                  verbose: bool = False) -> Dict[str, Any]:
        """
        Run the full benchmark suite.

        Args:
            evolve_first: Run evolution before generation benchmarks
            verbose: Print progress

        Returns:
            Complete benchmark results dict
        """
        livlm = LivLM(self._config)

        # Load corpus
        t0 = time.monotonic()
        livlm.load_corpus()
        corpus_time = time.monotonic() - t0

        results: Dict[str, Any] = {
            'model': 'NCLM (Non-Causal Living Model)',
            'architecture': 'Phase-Conjugate qByte Circuit',
            'n_params': livlm.gen_circuit.n_params,
            'corpus_size': livlm.corpus.size,
            'corpus_load_sec': round(corpus_time, 3),
            'tests': [],
        }

        # Evolution benchmark
        if evolve_first:
            if verbose:
                print("  Evolving circuit parameters...")
            t0 = time.monotonic()
            evo_result = livlm.evolve(verbose=verbose)
            evo_time = time.monotonic() - t0
            results['evolution'] = {
                'generations': evo_result['generations'],
                'best_fitness': round(evo_result['best_fitness'], 6),
                'best_phi': round(evo_result['best_phi'], 6),
                'consciousness_state': evo_result['consciousness_state'],
                'elapsed_sec': round(evo_time, 3),
            }

        # Generation benchmarks
        for prompt_name, prompt_text in self.PROMPTS:
            for length in self.LENGTHS:
                test_result = self._benchmark_generation(
                    livlm, prompt_name, prompt_text, length, verbose,
                )
                results['tests'].append(test_result)

        # Aggregate stats
        results['summary'] = self._aggregate(results['tests'])
        results['timestamp'] = time.time()

        return results

    def _benchmark_generation(self, livlm: LivLM, prompt_name: str,
                               prompt_text: str, length: int,
                               verbose: bool) -> Dict[str, Any]:
        """Benchmark a single generation run."""
        t0 = time.monotonic()
        output = livlm.generate(prompt=prompt_text, length=length)
        elapsed = time.monotonic() - t0

        # Compute metrics
        printable_count = sum(1 for c in output if 32 <= ord(c) < 127
                              or c in '\t\n\r')
        printable_ratio = printable_count / max(len(output), 1)

        # N-gram coherence via PhaseMemory
        mem = PhaseMemory(capacity=len(output) + 8)
        for ch in prompt_text:
            mem.record(ord(ch))
        for ch in output:
            mem.record(ord(ch))
        coherence_2gram = mem.ngram_coherence(n=2)
        coherence_3gram = mem.ngram_coherence(n=3)

        # Status metrics
        status = livlm.status()

        result = {
            'prompt_type': prompt_name,
            'prompt': prompt_text[:30],
            'length': length,
            'output_length': len(output),
            'output_preview': output[:80],
            'elapsed_sec': round(elapsed, 4),
            'chars_per_sec': round(len(output) / max(elapsed, 1e-9), 1),
            'printable_ratio': round(printable_ratio, 4),
            'coherence_2gram': round(coherence_2gram, 4),
            'coherence_3gram': round(coherence_3gram, 4),
            'consciousness_state': status['consciousness_state'],
        }

        if verbose:
            print(f"  {prompt_name:10s} len={length:3d}  "
                  f"{result['chars_per_sec']:>8.1f} c/s  "
                  f"coh={coherence_2gram:.3f}  "
                  f"print={printable_ratio:.2%}")

        return result

    def _aggregate(self, tests: List[Dict]) -> Dict[str, Any]:
        """Compute aggregate statistics across all tests."""
        if not tests:
            return {}

        speeds = [t['chars_per_sec'] for t in tests]
        coherences = [t['coherence_2gram'] for t in tests]
        printables = [t['printable_ratio'] for t in tests]

        return {
            'total_tests': len(tests),
            'avg_chars_per_sec': round(float(np.mean(speeds)), 1),
            'min_chars_per_sec': round(float(np.min(speeds)), 1),
            'max_chars_per_sec': round(float(np.max(speeds)), 1),
            'avg_coherence_2gram': round(float(np.mean(coherences)), 4),
            'avg_printable_ratio': round(float(np.mean(printables)), 4),
        }

    @staticmethod
    def print_report(results: Dict[str, Any]):
        """Print a formatted benchmark report."""
        print("\n" + "=" * 70)
        print("  NCLM BENCHMARK REPORT")
        print("=" * 70)
        print(f"  Model:      {results['model']}")
        print(f"  Parameters: {results['n_params']}")
        print(f"  Corpus:     {results['corpus_size']:,} bytes")

        if 'evolution' in results:
            evo = results['evolution']
            print(f"\n  Evolution:")
            print(f"    Generations:  {evo['generations']}")
            print(f"    Best Ξ:       {evo['best_fitness']:.6f}")
            print(f"    Best Φ:       {evo['best_phi']:.6f}")
            print(f"    State:        {evo['consciousness_state']}")
            print(f"    Time:         {evo['elapsed_sec']:.1f}s")

        print(f"\n  Generation Benchmarks:")
        print(f"  {'Prompt':<10} {'Len':>4} {'Speed':>10} {'Coherence':>10} {'Printable':>10}")
        print(f"  {'-'*10} {'-'*4} {'-'*10} {'-'*10} {'-'*10}")
        for t in results.get('tests', []):
            print(f"  {t['prompt_type']:<10} {t['length']:>4} "
                  f"{t['chars_per_sec']:>8.1f}/s "
                  f"{t['coherence_2gram']:>9.4f} "
                  f"{t['printable_ratio']:>9.2%}")

        if 'summary' in results:
            s = results['summary']
            print(f"\n  Summary:")
            print(f"    Avg speed:      {s['avg_chars_per_sec']:.1f} chars/sec")
            print(f"    Avg coherence:  {s['avg_coherence_2gram']:.4f}")
            print(f"    Avg printable:  {s['avg_printable_ratio']:.2%}")

        print("=" * 70)

    @staticmethod
    def save_results(results: Dict[str, Any], path: str):
        """Save benchmark results to JSON."""
        with open(path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
