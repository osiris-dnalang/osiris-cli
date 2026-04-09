"""
Arxiv watcher disabled for offline-only NCLM build (no external network access).
"""

class ArxivWatcher:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: arxiv_watcher disabled")

    def scan(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: arxiv_watcher disabled")

    def start_daemon(self, *args, **kwargs):
        raise RuntimeError("Offline NCLM build: arxiv_watcher disabled")

