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
import hashlib
import importlib.util
import json
import os

HOME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Same convention as genome.json and the backlog (~/.osiris); the dnalang
# source below is located from this file instead.
DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "genome_ledger.jsonl")


def _find_ledger_src():
    """dnalang-core's ledger.py: $OSIRIS_DNALANG_LEDGER if set, then the source
    checkouts OSIRIS has always looked in, then an installed `dnalang` package
    (located without importing it)."""
    candidates = [os.environ["OSIRIS_DNALANG_LEDGER"]] if os.environ.get("OSIRIS_DNALANG_LEDGER") else []
    candidates += [
        os.path.join(HOME_DIR, ".osiris", "src", "dnalang-core", "dnalang", "ledger.py"),
        os.path.join(os.path.expanduser("~"), "dnalang-core", "dnalang", "ledger.py"),
    ]
    try:
        spec = importlib.util.find_spec("dnalang")
    except (ImportError, ValueError):
        spec = None
    if spec is not None and spec.submodule_search_locations:
        candidates += [os.path.join(p, "ledger.py") for p in spec.submodule_search_locations]
    return next((c for c in candidates if os.path.exists(c)), candidates[0])


LEDGER_SRC = _find_ledger_src()
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


SUPERSESSION_KIND = "LEDGER_SUPERSEDED_CORRECTION"


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dnalang_hash(prev, entry):
    """The hash dnalang's Ledger gives an entry: sha256(prev + canonical body without prev/hash)."""
    body = {k: v for k, v in entry.items() if k not in ("prev", "hash")}
    return hashlib.sha256((prev + _canon(body)).encode()).hexdigest()


def _antigravity_inline_hash(entry):
    """The inline script an Antigravity session used on 2026-10-01 to append its Zenodo-draft entry:
    sha256(json.dumps({kind, prev, payload, ts}, sort_keys=True)) -- default separators, prev inside."""
    return hashlib.sha256(json.dumps({"kind": entry["kind"], "prev": entry["prev"], "payload": entry["payload"],
                                      "ts": entry["ts"]}, sort_keys=True).encode()).hexdigest()


# Hash formulas used by writers that bypassed this module. A superseded entry is accepted only if its
# stored hash reproduces under one of them, i.e. its content is exactly what that writer hashed.
FOREIGN_FORMULAS = {"antigravity-inline-2026-10-01": _antigravity_inline_hash}

# Facts about specific entries that the chain itself cannot record (it is append-only).
ENTRY_ERRATA = {
    "102140262b00fd2ea2b7c5b20695a43c94ac94076f320c28ac01e7f5a90b0008":
        "its ts 2026-10-02T07:37:20Z is the local (UTC-4) approval time labelled UTC; it was written about 11:40Z",
}


def _correction_payload(entry):
    p = entry.get("payload")
    if isinstance(p, dict) and set(p) == {"payload"} and isinstance(p["payload"], dict):
        p = p["payload"]                      # appended through GenomeLedger.append
    return p if isinstance(p, dict) else {}


def check_chain(entries):
    """(problem, notes): problem is None when the chain is intact.

    dnalang's rule, plus one exception for attested format corrections. An entry whose hash does not
    match the canonical formula is accepted only when ALL hold: (1) a LATER entry of kind
    LEDGER_SUPERSEDED_CORRECTION names its index and its exact stored hash; (2) that correction's
    corrected_canonical_hash equals the canonical hash recomputed from the entry as it is now; (3) the
    stored hash reproduces under a known foreign formula, so the content is what its writer hashed --
    an entry edited afterwards still fails; (4) the correction itself has a valid canonical hash (a
    correction can never be superseded). Every prev link is checked against the stored hashes.
    """
    corrections = {}
    for j, e in enumerate(entries):
        if e.get("kind") == SUPERSESSION_KIND:
            p = _correction_payload(e)
            corrections.setdefault(p.get("superseded_block_index"), []).append((j, p))
    prev, notes = GENESIS, []
    for i, e in enumerate(entries):
        if e.get("prev") != prev:
            return f"entry {i}: prev-hash mismatch", notes
        want = _dnalang_hash(prev, e)
        if e.get("hash") != want:
            accepted = None
            if e.get("kind") != SUPERSESSION_KIND:
                for j, p in corrections.get(i, []):
                    if j <= i or p.get("superseded_observed_hash") != e.get("hash") \
                            or p.get("corrected_canonical_hash") != want:
                        continue
                    formula = next((name for name, f in FOREIGN_FORMULAS.items() if _safe_hash(f, e) == e.get("hash")),
                                   None)
                    if formula:
                        accepted = (j, formula)
                        break
            if accepted is None:
                return f"entry {i}: hash mismatch", notes
            notes.append(f"entry {i} ({e.get('kind')}) was hashed in the '{accepted[1]}' format by a writer that "
                         f"bypassed this module; superseded by entry {accepted[0]}, content verified unchanged")
        if e.get("hash") in ENTRY_ERRATA:
            notes.append(f"entry {i}: {ENTRY_ERRATA[e['hash']]}")
        prev = e["hash"]
    return None, notes


def _safe_hash(formula, entry):
    try:
        return formula(entry)
    except (KeyError, TypeError, ValueError):
        return None


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
        """True if every entry's prev/hash re-derive correctly (see check_chain for the one attested
        exception), False otherwise -- including a file that is not valid JSON Lines."""
        return self.problem() is None

    def problem(self):
        """None if intact, else a description of the first bad entry."""
        try:
            return check_chain(self.chain)[0]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return f"unreadable ledger: {type(e).__name__}: {e}"

    def notes(self):
        """Superseded entries and errata on an otherwise intact chain (empty when there are none)."""
        try:
            return check_chain(self.chain)[1]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def tip(self):
        """Hash of the newest entry (GENESIS for an empty ledger)."""
        entries = self.chain
        return entries[-1]["hash"] if entries else GENESIS

    def load(self):
        """Kept from the story #22 API: the chain is always read from disk, so
        this only verifies."""
        return self.verify()
