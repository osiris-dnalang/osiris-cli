"""
OSIRIS Sovereign Truth Architecture - Universal CLI Package
"""

__version__ = "6.0.0"


def main(*args, **kwargs):
    """Lazy loader for REPL main to eliminate runpy RuntimeWarning."""
    from .osiris_repl import main as _main
    return _main(*args, **kwargs)


__all__ = ["main", "__version__"]
