"""Where OSIRIS looks for optional sibling checkouts and where it writes local results.

Earlier versions put one machine's absolute paths (including the whole home directory)
at the *front* of ``sys.path``. That let stale copies in the home directory shadow the
installed package, and made tests import the live working tree. Now:

* the source checkout, entries of ``OSIRIS_EXTRA_PATHS`` (``os.pathsep``-separated) and
  sibling research checkouts that exist under the home directory are *appended*, so
  installed packages always take precedence;
* results go under the checkout's ``results/`` when running from a source checkout,
  otherwise under ``~/.osiris/results/``.
"""

import os
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent

# Separately published research repositories the console can use when checked out
# next to the home directory (each import of them is guarded).
SIBLING_CHECKOUTS = (
    "dnalang-core",
    "organism_sim",
    "bridge",
    "flywheel-2026",
    "qbyte_system",
    "fold",
    "osiris-mobile-termux",
    "osiris-governance/src",
)


def add_optional_paths() -> List[str]:
    """Append (never prepend) existing optional locations to ``sys.path``; return those added."""
    candidates = [str(REPO_ROOT)]
    candidates += [p for p in os.environ.get("OSIRIS_EXTRA_PATHS", "").split(os.pathsep) if p]
    candidates += [str(Path.home() / name) for name in SIBLING_CHECKOUTS]
    added = []
    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.append(path)
            added.append(path)
    return added


def results_dir(*parts: str) -> Path:
    """``<checkout>/results/...`` in a source checkout, else ``~/.osiris/results/...``."""
    if (REPO_ROOT / "pyproject.toml").is_file():
        base = REPO_ROOT / "results"
    else:
        base = Path.home() / ".osiris" / "results"
    return base.joinpath(*parts)
