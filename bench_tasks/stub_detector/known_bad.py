import ast


def find_stubs(source):
    # Plausible but incomplete: only catches a body that is exactly `pass`.
    tree = ast.parse(source)
    return [n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and len(n.body) == 1 and isinstance(n.body[0], ast.Pass)]
