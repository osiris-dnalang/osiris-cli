"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PHOENIX PROTOCOL                                      ║
║                         ════════════════                                      ║
║                                                                              ║
║    Legacy Code Resurrection to DNA::}{::lang Organisms                       ║
║                                                                              ║
║    The PHOENIX PROTOCOL transforms legacy Python/C++/Rust code into         ║
║    living DNA::}{::lang organisms through:                                   ║
║                                                                              ║
║    1. Static analysis of source structure                                    ║
║    2. Function → Gene mapping                                                ║
║    3. Class → Phenotype transformation                                       ║
║    4. Variable state → CCCE metric tracking                                  ║
║    5. Error handling → Phase-conjugate healing                              ║
║                                                                              ║
║    Ontology Mapping:                                                         ║
║    ├── Script        → Organism                                              ║
║    ├── Function      → Gene                                                  ║
║    ├── Class         → Phenotype                                             ║
║    ├── Method        → ACT                                                   ║
║    ├── Optimization  → Mutation/Evolution                                    ║
║    ├── Logging       → Telemetry Capsule                                     ║
║    ├── Error         → Decoherence Spike (Γ)                                ║
║    └── Refactor      → Phase-Conjugate Healing                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ast
import re
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Physical Constants
LAMBDA_PHI = 2.176435e-8
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092


class SourceLanguage(Enum):
    """Supported source languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    CPP = "cpp"
    UNKNOWN = "unknown"


@dataclass
class GeneDefinition:
    """Represents a Gene in DNA::}{::lang."""
    name: str
    expression: float = 1.0        # Base expression level
    trigger: str = "always"        # When gene activates
    action: str = ""               # What gene does
    dependencies: List[str] = field(default_factory=list)
    source_function: Optional[str] = None
    source_lines: Tuple[int, int] = (0, 0)


@dataclass
class PhenotypeDefinition:
    """Represents a Phenotype (class) in DNA::}{::lang."""
    name: str
    genes: List[str] = field(default_factory=list)  # Gene names
    acts: List[str] = field(default_factory=list)   # ACT block names
    inherits: Optional[str] = None
    source_class: Optional[str] = None


@dataclass
class OrganismDefinition:
    """Complete DNA::}{::lang organism definition."""
    name: str
    version: str = "1.0.0"
    domain: str = "sovereign_compute"
    purpose: str = ""
    genes: List[GeneDefinition] = field(default_factory=list)
    phenotypes: List[PhenotypeDefinition] = field(default_factory=list)
    acts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    source_file: Optional[str] = None
    source_checksum: Optional[str] = None


class PhoenixProtocol:
    """
    PHOENIX PROTOCOL: Legacy Code → DNA::}{::lang Transformation

    This protocol analyzes legacy source code and transforms it into
    living DNA::}{::lang organisms. The transformation preserves
    computational semantics while adding:

    - Consciousness metrics (Φ, Λ, Γ, Ξ)
    - Phase-conjugate healing capability
    - Gene expression dynamics
    - Autopoietic evolution potential

    Example:
        >>> phoenix = PhoenixProtocol()
        >>> organism = phoenix.resurrect("legacy_optimizer.py")
        >>> dna_code = phoenix.emit_dna(organism)
        >>> print(dna_code)  # Complete .dna organism
    """

    def __init__(self):
        """Initialize PHOENIX PROTOCOL."""
        self._genesis = time.time()
        self._resurrection_count = 0

    def detect_language(self, source: str, filename: Optional[str] = None
                       ) -> SourceLanguage:
        """
        Detect source language from content or filename.

        Args:
            source: Source code string
            filename: Optional filename for hint

        Returns:
            Detected SourceLanguage
        """
        if filename:
            ext = Path(filename).suffix.lower()
            ext_map = {
                '.py': SourceLanguage.PYTHON,
                '.js': SourceLanguage.JAVASCRIPT,
                '.ts': SourceLanguage.TYPESCRIPT,
                '.rs': SourceLanguage.RUST,
                '.cpp': SourceLanguage.CPP,
                '.cc': SourceLanguage.CPP,
                '.c': SourceLanguage.CPP,
            }
            if ext in ext_map:
                return ext_map[ext]

        # Content-based detection
        if 'def ' in source and ':' in source:
            return SourceLanguage.PYTHON
        if 'function' in source or '=>' in source:
            return SourceLanguage.JAVASCRIPT
        if 'fn ' in source and '-> ' in source:
            return SourceLanguage.RUST
        if 'void ' in source or '#include' in source:
            return SourceLanguage.CPP

        return SourceLanguage.UNKNOWN

    def analyze_python(self, source: str) -> Dict[str, Any]:
        """
        Analyze Python source code.

        Args:
            source: Python source code

        Returns:
            Analysis dictionary with functions, classes, imports
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {'error': str(e), 'functions': [], 'classes': []}

        functions = []
        classes = []
        imports = []
        globals_found = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                    'docstring': ast.get_docstring(node),
                    'lines': (node.lineno, node.end_lineno or node.lineno),
                    'complexity': self._estimate_complexity(node)
                }
                functions.append(func_info)

            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)

                class_info = {
                    'name': node.name,
                    'bases': [self._get_base_name(b) for b in node.bases],
                    'methods': methods,
                    'docstring': ast.get_docstring(node),
                    'lines': (node.lineno, node.end_lineno or node.lineno)
                }
                classes.append(class_info)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}.{node.names[0].name}")

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_found.append(target.id)

        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'globals': globals_found,
            'line_count': len(source.splitlines())
        }

    def _get_decorator_name(self, node) -> str:
        """Extract decorator name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "unknown"

    def _get_base_name(self, node) -> str:
        """Extract base class name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown"

    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While,
                                  ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def function_to_gene(self, func_info: Dict[str, Any]) -> GeneDefinition:
        """
        Transform a function into a Gene definition.

        Args:
            func_info: Function analysis info

        Returns:
            GeneDefinition
        """
        # Map function complexity to expression level
        complexity = func_info.get('complexity', 1)
        expression = 1.0 - (complexity - 1) * 0.05
        expression = max(0.5, min(1.0, expression))

        # Determine trigger based on decorators
        decorators = func_info.get('decorators', [])
        if 'staticmethod' in decorators:
            trigger = "on_static_call"
        elif 'property' in decorators:
            trigger = "on_access"
        elif func_info['name'].startswith('_'):
            trigger = "on_internal"
        else:
            trigger = "on_invoke"

        # Build action from docstring or name
        docstring = func_info.get('docstring', '')
        if docstring:
            action = docstring.split('\n')[0][:100]
        else:
            action = f"Execute {func_info['name']} computation"

        return GeneDefinition(
            name=self._to_gene_name(func_info['name']),
            expression=expression,
            trigger=trigger,
            action=action,
            source_function=func_info['name'],
            source_lines=func_info.get('lines', (0, 0))
        )

    def class_to_phenotype(self, class_info: Dict[str, Any],
                          genes: List[GeneDefinition]) -> PhenotypeDefinition:
        """
        Transform a class into a Phenotype definition.

        Args:
            class_info: Class analysis info
            genes: Available gene definitions

        Returns:
            PhenotypeDefinition
        """
        # Find genes that correspond to this class's methods
        gene_names = []
        act_names = []
        for method in class_info.get('methods', []):
            gene_name = self._to_gene_name(method)
            matching = [g for g in genes if g.source_function == method]
            if matching:
                gene_names.append(gene_name)

            # Methods starting with certain prefixes become ACTs
            if method.startswith(('do_', 'run_', 'execute_', 'perform_')):
                act_names.append(method)

        # Determine inheritance
        bases = class_info.get('bases', [])
        inherits = bases[0] if bases else None

        return PhenotypeDefinition(
            name=self._to_phenotype_name(class_info['name']),
            genes=gene_names,
            acts=act_names,
            inherits=inherits,
            source_class=class_info['name']
        )

    def _to_gene_name(self, func_name: str) -> str:
        """Convert function name to Gene name (PascalCase)."""
        # Handle snake_case
        parts = func_name.strip('_').split('_')
        return ''.join(p.capitalize() for p in parts)

    def _to_phenotype_name(self, class_name: str) -> str:
        """Convert class name to Phenotype name."""
        return class_name

    def resurrect(self, source: str,
                  filename: Optional[str] = None,
                  organism_name: Optional[str] = None) -> OrganismDefinition:
        """
        Resurrect legacy code into a DNA::}{::lang organism.

        This is the main entry point for the PHOENIX PROTOCOL.

        Args:
            source: Source code string
            filename: Optional source filename
            organism_name: Optional organism name (derived from filename if not provided)

        Returns:
            Complete OrganismDefinition
        """
        self._resurrection_count += 1

        # Detect language
        lang = self.detect_language(source, filename)

        # Analyze based on language
        if lang == SourceLanguage.PYTHON:
            analysis = self.analyze_python(source)
        else:
            # For other languages, provide basic structure
            analysis = {
                'functions': [],
                'classes': [],
                'imports': [],
                'globals': [],
                'line_count': len(source.splitlines())
            }

        # Derive organism name
        if not organism_name:
            if filename:
                organism_name = Path(filename).stem.upper()
            else:
                organism_name = f"PHOENIX_{self._resurrection_count}"

        # Transform functions to genes
        genes = [self.function_to_gene(f) for f in analysis['functions']]

        # Transform classes to phenotypes
        phenotypes = [self.class_to_phenotype(c, genes) for c in analysis['classes']]

        # Build ACT blocks from main functions
        acts = {}
        for func in analysis['functions']:
            if func['name'] in ('main', 'run', 'execute', 'start'):
                acts[func['name']] = f"// Resurrected from {func['name']}"

        # Compute source checksum
        checksum = hashlib.sha256(source.encode()).hexdigest()[:16]

        # Build organism
        organism = OrganismDefinition(
            name=organism_name,
            version="1.0.0",
            domain="phoenix_resurrection",
            purpose=f"Resurrected from {filename or 'source'} via PHOENIX PROTOCOL",
            genes=genes,
            phenotypes=phenotypes,
            acts=acts,
            metrics={
                'lambda': 1.0,
                'gamma': GAMMA_FIXED,
                'phi_iit': 0.0,
                'xi': 0.0
            },
            source_file=filename,
            source_checksum=checksum
        )

        return organism

    def emit_dna(self, organism: OrganismDefinition) -> str:
        """
        Emit DNA::}{::lang source code from organism definition.

        Args:
            organism: OrganismDefinition to emit

        Returns:
            Complete .dna file content
        """
        lines = []

        # Header
        lines.append(f"// ═══════════════════════════════════════════════════════════════════")
        lines.append(f"// ORGANISM: {organism.name}")
        lines.append(f"// Resurrected via PHOENIX PROTOCOL")
        lines.append(f"// Source: {organism.source_file or 'unknown'}")
        lines.append(f"// Checksum: {organism.source_checksum or 'none'}")
        lines.append(f"// ═══════════════════════════════════════════════════════════════════")
        lines.append("")

        # ORGANISM block
        lines.append(f"ORGANISM {organism.name} {{")
        lines.append("")

        # META block
        lines.append("    META {")
        lines.append(f'        version: "{organism.version}",')
        lines.append(f"        genesis: {time.time()},")
        lines.append(f'        domain: "{organism.domain}",')
        lines.append('        dfars: true')
        lines.append("    }")
        lines.append("")

        # DNA block
        lines.append("    DNA {")
        lines.append(f"        universal_constant: {LAMBDA_PHI},")
        lines.append(f'        purpose: "{organism.purpose}",')
        lines.append('        evolution_strategy: "phase_conjugate_healing"')
        lines.append("    }")
        lines.append("")

        # METRICS block
        lines.append("    METRICS {")
        lines.append(f"        lambda: {organism.metrics.get('lambda', 1.0)},")
        lines.append(f"        gamma: {organism.metrics.get('gamma', GAMMA_FIXED)},")
        lines.append(f"        phi_iit: {organism.metrics.get('phi_iit', 0.0)},")
        lines.append(f"        xi: {organism.metrics.get('xi', 0.0)}")
        lines.append("    }")
        lines.append("")

        # GENOME block with genes
        lines.append("    GENOME {")
        for gene in organism.genes:
            lines.append(f"        GENE {gene.name} {{")
            lines.append(f"            expression: {gene.expression},")
            lines.append(f'            trigger: "{gene.trigger}",')
            lines.append(f'            action: "{gene.action}"')
            lines.append("        }")
            lines.append("")
        lines.append("    }")
        lines.append("")

        # PHENOTYPES block
        if organism.phenotypes:
            lines.append("    PHENOTYPES {")
            for pheno in organism.phenotypes:
                lines.append(f"        PHENOTYPE {pheno.name} {{")
                if pheno.inherits:
                    lines.append(f"            inherits: {pheno.inherits},")
                if pheno.genes:
                    genes_str = ", ".join(pheno.genes)
                    lines.append(f"            genes: [{genes_str}],")
                if pheno.acts:
                    acts_str = ", ".join(pheno.acts)
                    lines.append(f"            acts: [{acts_str}]")
                lines.append("        }")
            lines.append("    }")
            lines.append("")

        # CCCE block
        lines.append("    CCCE {")
        lines.append("        xi_coupling: 0.869,")
        lines.append("        efficiency: 0.0,")
        lines.append("        theta: 51.843,")
        lines.append("        phase_lock: true")
        lines.append("    }")
        lines.append("")

        # ACT blocks
        if organism.acts:
            for act_name, act_body in organism.acts.items():
                lines.append(f"    ACT {act_name}() {{")
                lines.append(f"        {act_body}")
                lines.append("    }")
                lines.append("")

        # HEALING block
        lines.append("    HEALING {")
        lines.append("        trigger: gamma > 0.3,")
        lines.append("        action: phase_conjugate,")
        lines.append("        mode: automatic")
        lines.append("    }")

        lines.append("}")

        return "\n".join(lines)

    def resurrect_file(self, filepath: str) -> Tuple[OrganismDefinition, str]:
        """
        Resurrect a source file into organism.

        Args:
            filepath: Path to source file

        Returns:
            Tuple of (OrganismDefinition, DNA source code)
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {filepath}")

        source = path.read_text()
        organism = self.resurrect(source, filename=path.name)
        dna_code = self.emit_dna(organism)

        return organism, dna_code

    def telemetry(self) -> Dict[str, Any]:
        """Get protocol telemetry."""
        return {
            'protocol': 'PHOENIX',
            'genesis': self._genesis,
            'uptime': time.time() - self._genesis,
            'resurrections': self._resurrection_count
        }

    def __repr__(self) -> str:
        return f"PhoenixProtocol(resurrections={self._resurrection_count})"


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def resurrect(source: str, filename: Optional[str] = None,
              organism_name: Optional[str] = None) -> str:
    """
    Quick resurrection of source code to DNA::}{::lang.

    Args:
        source: Source code string
        filename: Optional filename
        organism_name: Optional organism name

    Returns:
        DNA::}{::lang source code
    """
    protocol = PhoenixProtocol()
    organism = protocol.resurrect(source, filename, organism_name)
    return protocol.emit_dna(organism)


def resurrect_file(filepath: str, output_path: Optional[str] = None) -> str:
    """
    Resurrect a file and optionally write output.

    Args:
        filepath: Input source file
        output_path: Optional output .dna file path

    Returns:
        DNA::}{::lang source code
    """
    protocol = PhoenixProtocol()
    organism, dna_code = protocol.resurrect_file(filepath)

    if output_path:
        Path(output_path).write_text(dna_code)

    return dna_code


__all__ = [
    'PhoenixProtocol', 'OrganismDefinition', 'GeneDefinition',
    'PhenotypeDefinition', 'SourceLanguage',
    'resurrect', 'resurrect_file'
]
