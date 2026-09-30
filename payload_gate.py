#!/usr/bin/env python3
"""
payload_gate.py -- static placeholder/complexity gate for Engine 2 output.

Closes a real gap (2026-09-23): the sandbox gate only asked "does the
model's OWN test pass?", so a stub module plus an assert-free test could
pass, and run_synergy_pipeline (no sandbox at all) stamped a module whose
methods all returned {"parameter1": None} as AST_VERIFIED_AND_LOCKED.
AST-clean is not the same claim as "implements something".

Scope: this rejects placeholder SHAPES only. It does not judge relevance --
off-topic but real code (e.g. the court-record UI stories that passed on
2026-09-23) is filtered upstream in vision_indexer, not here.

Pure AST/regex inspection, no execution, no model call. Returns None if
the payload looks like real logic, else a short human-readable reason.
Deliberately conservative in what it calls a stub (see _is_stub_body) --
it rejects placeholder shapes, it does not judge code quality.
"""
import ast
import re

# Literal markers local models emit instead of real code. Matched against
# comments/strings too, since that's exactly where they appear.
_PLACEHOLDER_MARKERS_RE = re.compile(
    r"your (code|logic|implementation) here|"
    r"\bTODO:?\s*implement|"
    r"\bimplement (this|me|here)\b|"
    r"repeat for (the )?other|"
    r"\bplaceholder (code|logic|implementation|function|method)\b|"
    r"\bthis is a placeholder\b|"
    r"adjust accordingly in your codebase|"
    r"initialize your .* here if needed",
    re.IGNORECASE,
)

# Node types that mean a function actually computes something, rather than
# just returning a literal.
_LOGIC_NODES = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BinOp,
                ast.BoolOp, ast.Compare, ast.Call, ast.Subscript, ast.comprehension,
                ast.AugAssign, ast.IfExp)

_EXEMPT_DECORATORS = {"abstractmethod", "overload"}


def _is_docstring(stmt):
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
        and isinstance(stmt.value.value, str)


def _literal_contains_none(node):
    """True if node is a pure literal (constant / container of literals)
    containing at least one None -- the {"key": None} / return None shape."""
    if isinstance(node, ast.Constant):
        return node.value is None
    if isinstance(node, ast.Dict):
        parts = [k for k in node.keys if k is not None] + node.values
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        parts = node.elts
    else:
        return False
    if not all(isinstance(p, (ast.Constant, ast.Dict, ast.List, ast.Tuple, ast.Set)) for p in parts):
        return False
    return any(_literal_contains_none(p) for p in parts)


def _is_stub_body(body):
    """pass / ... / raise NotImplementedError / return <literal with None>,
    optionally after a docstring, and nothing else."""
    stmts = [s for s in body if not _is_docstring(s)]
    if not stmts:
        return True
    for s in stmts:
        if isinstance(s, ast.Pass):
            continue
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
            continue
        if isinstance(s, ast.Raise) and s.exc is not None:
            exc = s.exc.func if isinstance(s.exc, ast.Call) else s.exc
            if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                continue
        if isinstance(s, ast.Return) and (s.value is None or _literal_contains_none(s.value)):
            continue
        return False
    return True


def _decorator_names(fn):
    names = set()
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def check_payload(source: str):
    """Returns None if source looks like a real implementation, else a reason."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"syntax error: {e}"

    m = _PLACEHOLDER_MARKERS_RE.search(source)
    if m:
        return f"placeholder marker in source: {m.group(0)!r}"

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    stubs = []
    has_logic = False
    for fn in funcs:
        if _decorator_names(fn) & _EXEMPT_DECORATORS:
            continue
        if _is_stub_body(fn.body):
            # An empty __init__ is harmless boilerplate, not a missing implementation.
            if fn.name != "__init__":
                stubs.append(fn.name)
            continue
        if any(isinstance(n, _LOGIC_NODES) for stmt in fn.body for n in ast.walk(stmt)):
            has_logic = True
    if stubs:
        return f"stub function(s) with no implementation: {', '.join(stubs[:5])}"

    if not has_logic:
        # No function computes anything -- allow a script whose real work is
        # at module level, but not a module of empty class shells.
        top_logic = any(
            isinstance(n, _LOGIC_NODES)
            for stmt in tree.body
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                     ast.Import, ast.ImportFrom))
            for n in ast.walk(stmt)
        )
        if not top_logic:
            return "no function or top-level statement performs any computation"
    return None


def check_test(test_code: str):
    """A test with no assert can't fail, so it proves nothing. Returns None
    if test_proposal() contains at least one assert, else a reason."""
    try:
        tree = ast.parse(test_code)
    except SyntaxError as e:
        return f"test code has a syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "test_proposal":
            if any(isinstance(n, ast.Assert) for n in ast.walk(node)):
                return None
            return "test_proposal() contains no assert statement"
    return "no test_proposal() function defined"
