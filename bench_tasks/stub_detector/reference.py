import ast


def _is_stub_stmt(s):
    if isinstance(s, ast.Pass):
        return True
    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
        return True
    if isinstance(s, ast.Raise) and s.exc is not None:
        exc = s.exc.func if isinstance(s.exc, ast.Call) else s.exc
        return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"
    if isinstance(s, ast.Return):
        return s.value is None or (isinstance(s.value, ast.Constant) and s.value.value is None)
    return False


def find_stubs(source):
    tree = ast.parse(source)
    out = []
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for fn in sorted(funcs, key=lambda n: (n.lineno, n.col_offset)):
        body = fn.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        if all(_is_stub_stmt(s) for s in body):
            out.append(fn.name)
    return out
