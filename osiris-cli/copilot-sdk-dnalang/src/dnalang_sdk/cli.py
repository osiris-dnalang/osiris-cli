#!/usr/bin/env python3
"""DNALang SDK CLI — Quantum-native development toolkit.

Usage:
    dnalang-sdk version        Show version and framework info
    dnalang-sdk info           Show SDK module inventory
    dnalang-sdk validate       Validate import chain integrity
    dnalang-sdk compile FILE   Compile a .dna source file
    dnalang-sdk penteract      Run Penteract 46-problem resolution
"""

import argparse
import sys
import time


def cmd_version(args):
    from dnalang_sdk import __version__, __framework__
    print(f"DNALang SDK v{__version__}")
    print(f"Framework: {__framework__}")
    print(f"Author: Devin Phillip Davis / Agile Defense Systems")
    print(f"License: MIT")


def cmd_info(args):
    import dnalang_sdk
    exports = dnalang_sdk.__all__
    print(f"DNALang SDK v{dnalang_sdk.__version__}")
    print(f"Total exports: {len(exports)}")
    print()

    # Group by category
    categories = {
        "Core": ["DNALangCopilotClient", "CopilotConfig", "QuantumConfig"],
        "Agents": ["AURA", "AIDEN", "CHEOPS", "CHRONOS", "SCIMITARSentinel"],
        "Quantum": ["AeternaPorta", "QuantumMetrics", "CircuitGenerator", "QuantumExecutor"],
        "Compiler": ["DNALangParser", "DNALangLexer", "DNAIR", "DNAEvolver", "DNARuntime", "DNALedger"],
        "CRSM": ["PenteractShell", "OsirisPenteract", "NCLMSwarmOrchestrator", "TauPhaseAnalyzer"],
        "Defense": ["Sentinel", "PCRB", "SphericalTetrahedron", "PhaseConjugateHowitzer"],
        "NCLM": ["NonCausalLM", "NCLMChat", "IntentDeducer"],
        "Lab": ["ExperimentRegistry", "LabScanner", "LabExecutor"],
    }
    for cat, keys in categories.items():
        found = [k for k in keys if k in exports]
        print(f"  {cat}: {len(found)} modules")


def cmd_validate(args):
    print("Validating import chain...")
    t0 = time.time()
    try:
        import dnalang_sdk
        elapsed = time.time() - t0
        print(f"✅ All {len(dnalang_sdk.__all__)} exports loaded in {elapsed:.2f}s")

        # Spot-check key classes
        checks = [
            ("AeternaPorta", dnalang_sdk.AeternaPorta),
            ("OsirisPenteract", dnalang_sdk.OsirisPenteract),
            ("DNALangParser", dnalang_sdk.DNALangParser),
            ("PCRB", dnalang_sdk.PCRB),
            ("CodeWriter", dnalang_sdk.CodeWriter),
        ]
        for name, cls in checks:
            print(f"  ✓ {name}: {cls.__module__}.{cls.__name__}")
        print("\n✅ Import chain integrity: PASSED")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)


def cmd_compile(args):
    from dnalang_sdk.compiler import Lexer, Parser
    import json

    path = args.file
    try:
        with open(path) as f:
            source = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        sys.exit(1)

    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✅ Parsed {path}: {len(ast.genes) if hasattr(ast, 'genes') else '?'} genes")
    print(json.dumps(ast.__dict__, default=str, indent=2)[:500])


def cmd_penteract(args):
    from dnalang_sdk.crsm import OsirisPenteract
    engine = OsirisPenteract(seed=51843)
    results = engine.resolve_all()
    solved = sum(1 for r in results if r.final_gamma < 0.3)
    print(f"Penteract Singularity Protocol")
    print(f"  Problems: {len(results)}")
    print(f"  Resolved: {solved}/{len(results)}")
    print(f"  Success rate: {solved/len(results)*100:.1f}%")
    if results:
        avg_reduction = sum(r.reduction_pct for r in results) / len(results)
        print(f"  Avg Γ reduction: {avg_reduction:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        prog="dnalang-sdk",
        description="DNALang SDK — Quantum-native development toolkit",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="Show version info")
    sub.add_parser("info", help="Show module inventory")
    sub.add_parser("validate", help="Validate import chain")

    p_compile = sub.add_parser("compile", help="Compile .dna file")
    p_compile.add_argument("file", help="Path to .dna source file")

    sub.add_parser("penteract", help="Run 46-problem resolution")

    args = parser.parse_args()
    commands = {
        "version": cmd_version,
        "info": cmd_info,
        "validate": cmd_validate,
        "compile": cmd_compile,
        "penteract": cmd_penteract,
    }
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
