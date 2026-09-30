#!/usr/bin/env python3
"""
genome_ledger.py -- append-only, hash-chained record of OSIRIS's own state
changes (applied writes, generation bumps), stored as JSON Lines at
~/.osiris/genome_ledger.jsonl.

A thin wrapper over dnalang-core's Ledger (canonical JSON, SHA-256 over
prev + entry, one line per entry, written with "a" so earlier lines are
never rewritten), plus an exclusive file lock around each append.

Replaces the story #22 version (commit e8efa5e), which kept its chain in
memory and rewrote the whole file on every save: a new GenomeLedger on an
existing path started empty, so the next append silently erased all prior
history -- and load() still reported the result as valid (reproduced
2026-09-23). append(), verify(), load() and .chain keep their names; save() is
gone because every append is already durable.

Tamper-evidence limit: a hash chain only proves internal consistency. Anyone
who can write the file can rewrite it and recompute every hash, so the tip
hash must also be recorded somewhere outside the device. zenodo_packager.py
writes it to each deposit's MANIFEST.json, but that only becomes an external
anchor once the archive is stored or published off the phone.

A torn final line (e.g. power loss mid-append) makes verify() False and every
later append raise, so /apply fails closed rather than extending a damaged
chain.
"""
import fcntl
import importlib.util
import json
import os

HOME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Same convention as genome.json and the backlog (~/.osiris); the dnalang
# source below is located from this file instead.
DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "genome_ledger.jsonl")
_LEDGER_CANDIDATES = [
    os.path.join(HOME_DIR, ".osiris", "src", "dnalang-core", "dnalang", "ledger.py"),
    os.path.join(os.path.expanduser("~"), "dnalang-core", "dnalang", "ledger.py"),
    "/home/enki/dnalang-core/dnalang/ledger.py",
]
LEDGER_SRC = next((c for c in _LEDGER_CANDIDATES if os.path.exists(c)), _LEDGER_CANDIDATES[0])
GENESIS = "0" * 64

_ledger_mod = None


class LedgerAppendUnknown(OSError):
    """An append failed AND removing its partial/unacknowledged line also
    failed: the ledger may now contain a record that was never committed.
    Callers must stop writing until a human reconciles the file."""


def _dnalang_ledger():
    global _ledger_mod
    if _ledger_mod is None:
        if not os.path.exists(LEDGER_SRC):
            raise FileNotFoundError(f"dnalang-core ledger not found at {LEDGER_SRC}")
        spec = importlib.util.spec_from_file_location("_genome_dnalang_ledger", LEDGER_SRC)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _ledger_mod = module
    return _ledger_mod


class GenomeLedger:
    def __init__(self, filepath=None):
        self.filepath = filepath or DEFAULT_PATH
        parent = os.path.dirname(os.path.abspath(self.filepath))
        os.makedirs(parent, exist_ok=True)
        if os.path.exists(self.filepath):
            with open(self.filepath, encoding="utf-8") as f:
                head = f.read(1)
            if head == "[":
                raise ValueError(f"{self.filepath} is a story #22 JSON-array ledger, not JSON Lines; "
                                 f"move it aside rather than appending to it")
        self._ledger = _dnalang_ledger().Ledger(self.filepath)

    @property
    def chain(self):
        """Every entry currently on disk, oldest first (re-read on each access)."""
        return list(self._ledger)

    def append(self, entry_type, payload):
        """Appends one entry {prev, ts, kind, payload, hash} and returns it.
        The lock keeps two processes from both reading the same tip and
        forking the chain."""
        with open(self.filepath + ".lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                size_before = os.path.getsize(self.filepath)
                try:
                    entry = self._ledger.append(entry_type, {"payload": payload})
                    # Durable before it is acknowledged: /apply treats a returned
                    # entry as the commit point of the write it records.
                    with open(self.filepath, "a", encoding="utf-8") as f:
                        os.fsync(f.fileno())
                except BaseException as append_error:
                    # The line may already be in the file even though the append
                    # failed (e.g. fsync raised). An unacknowledged entry must not
                    # survive: /apply rolls its write back on this exception, and
                    # a leftover record would claim a change that was undone.
                    try:
                        os.truncate(self.filepath, size_before)
                        with open(self.filepath, "a", encoding="utf-8") as f:
                            os.fsync(f.fileno())
                    except BaseException as truncate_error:
                        raise LedgerAppendUnknown(
                            f"append failed ({type(append_error).__name__}: {append_error}) and removing "
                            f"its line failed ({type(truncate_error).__name__}: {truncate_error}); "
                            f"expected size {size_before}, actual "
                            f"{os.path.getsize(self.filepath) if os.path.exists(self.filepath) else 'missing'}"
                        ) from append_error
                    raise
                return entry
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def verify(self):
        """True if every entry's prev/hash re-derive correctly, False otherwise
        (including a file that is not valid JSON Lines)."""
        try:
            return self._ledger.verify() is None
        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    def problem(self):
        """None if intact, else dnalang's description of the first bad entry."""
        try:
            return self._ledger.verify()
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return f"unreadable ledger: {type(e).__name__}: {e}"

    def tip(self):
        """Hash of the newest entry (GENESIS for an empty ledger)."""
        entries = self.chain
        return entries[-1]["hash"] if entries else GENESIS

    def load(self):
        """Kept from the story #22 API: the chain is always read from disk, so
        this only verifies."""
        return self.verify()
