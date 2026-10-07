class Breaker:
    # Plausible but too eager: any single non-2xx disables the backend for good.
    def __init__(self):
        self._down = set()

    def record(self, backend, status):
        if status is None or not (200 <= status <= 299):
            self._down.add(backend)

    def available(self, backend):
        return backend not in self._down
