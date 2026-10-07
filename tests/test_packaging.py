"""Everything the console and the osiris_cli package import from the repository root must
ship in the distribution, and none of it may carry one machine's home directory.

Before 4.3.1 a clean install reported "bench evidence unreadable (ModuleNotFoundError)":
ten modules the console imports existed only in one working copy, and the entry point put
hard-coded home-directory paths at the front of sys.path, which hid the gap locally."""
import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _py_modules():
    text = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    block = re.search(r"py-modules\s*=\s*\[(.*?)\]", text, re.S).group(1)
    return set(re.findall(r'"([^"]+)"', block))


def _root_modules():
    """Top-level .py files, minus names shadowed by a package directory (the package wins)."""
    packages = {d for d in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, d, "__init__.py"))}
    return {f[:-3] for f in os.listdir(ROOT) if f.endswith(".py")} - packages


def _imports(path):
    names = set()
    for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _closure():
    local = _root_modules()
    cli = os.path.join(ROOT, "osiris_cli")
    queue = ["osiris_termux_console"]
    queue += [m for f in os.listdir(cli) if f.endswith(".py") for m in _imports(os.path.join(cli, f)) if m in local]
    needed = set()
    while queue:
        mod = queue.pop()
        if mod not in needed:
            needed.add(mod)
            queue += [m for m in _imports(os.path.join(ROOT, mod + ".py")) if m in local and m not in needed]
    return needed


def test_every_imported_repository_module_is_packaged():
    missing = sorted(_closure() - _py_modules())
    assert not missing, f"imported by the console or osiris_cli but not in py-modules: {missing}"


def test_packaged_modules_exist():
    absent = sorted(m for m in _py_modules() if not os.path.isfile(os.path.join(ROOT, m + ".py")))
    assert not absent, f"listed in py-modules but missing: {absent}"


def test_no_home_directory_literals_in_shipped_entry_code():
    home_literal = re.compile(r"""["']/home/\w+/""")
    files = [os.path.join(ROOT, m + ".py") for m in _closure()]
    cli = os.path.join(ROOT, "osiris_cli")
    files += [os.path.join(cli, f) for f in os.listdir(cli) if f.endswith(".py")]
    offenders = sorted(os.path.relpath(f, ROOT) for f in files
                       if home_literal.search(open(f, encoding="utf-8").read()))
    assert not offenders, f"hard-coded home-directory paths in: {offenders}"


def test_scripts_the_console_runs_by_path_are_packaged():
    """The console runs some of its own modules as scripts, located next to itself
    (os.path.join(<console dir>, "<name>.py")); those must ship alongside it."""
    src = open(os.path.join(ROOT, "osiris_termux_console.py"), encoding="utf-8").read()
    # Only joins rooted at the console's own directory; files it writes into temporary
    # sandbox directories are generated at run time, not shipped.
    own_dir = re.compile(r'os\.path\.join\((?:os\.path\.dirname\(os\.path\.abspath\(__file__\)\)|BIN_DIR|bin_dir),'
                         r'\s*"([A-Za-z_][A-Za-z0-9_]*)\.py"')
    scripts = set(own_dir.findall(src))
    assert scripts, "expected the console to run at least one script by path"
    missing = sorted(scripts - _py_modules())
    assert not missing, f"run by path from the console but not in py-modules: {missing}"


def test_bench_results_land_where_the_console_reads():
    import osiris_bench
    import protege
    assert osiris_bench.DEFAULT_OUT == protege.BENCH_DIR
