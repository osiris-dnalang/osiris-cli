"""osiris.tui — Rich TUI, Textual TUI, integrated console."""

import importlib as _il


def __getattr__(name):
    _map = {
        "rich_tui": "osiris.tui.rich_tui",
        "textual_tui": "osiris.tui.textual_tui",
        "integrated": "osiris.tui.integrated",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.tui' has no attribute {name!r}")
