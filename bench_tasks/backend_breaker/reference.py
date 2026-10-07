class Breaker:
    FATAL = {401, 402, 403}
    LIMIT = 3

    def __init__(self):
        self._fatal = set()
        self._streak = {}

    def record(self, backend, status):
        if status in self.FATAL:
            self._fatal.add(backend)
        elif status is None or status == 429 or 500 <= status <= 599:
            self._streak[backend] = self._streak.get(backend, 0) + 1
        elif 200 <= status <= 299:
            self._streak[backend] = 0

    def available(self, backend):
        return backend not in self._fatal and self._streak.get(backend, 0) < self.LIMIT
