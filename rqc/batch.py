"""S2 amendment 5 (draft): run many seeds' search loops in lockstep so that one job carries one round of every
participant, instead of one job per sampler call.

Why lockstep works for the frozen search code (`rqc/experiment.py` at 06761071, unchanged):
  - each arm makes exactly k + 1 sampler calls (k search rounds, then the "final" re-measurement);
  - the adaptive arm's call r depends on the results of calls 0..r-1 (accept/reject), and both arms' "final" call
    depends on all k earlier results; no call depends on another participant;
  - so call r of every participant can be made at the same barrier, and a block of P participants needs exactly
    k + 1 jobs of P pubs. That number is not assumed here: the coordinator fires a job whenever every live
    participant is waiting, and tests count the jobs this actually produces.

Each participant runs the frozen `run_random` / `run_adaptive` in its own thread (the frozen functions take a
blocking `sampler(circuit, shots)` callable, so a thread per participant is the smallest way to suspend them without
editing them). Concurrency is bounded by `max_participants`; the threads only wait on one condition variable and do
NumPy work between calls. When every live participant is waiting:

  1. `preflight(requests)` may refuse the job (budget, authorization). Its RQC_SUBMIT rows are dropped, an
     RQC_BATCH_REFUSED row is written, and every participant is aborted.
  2. Every participant's buffered ledger rows are written to the real ledger in participant-key order, then one
     RQC_BATCH_SUBMIT row (pub order, circuit digests, shots, protocol hash). Each RQC_SUBMIT row is on disk
     (fsynced) before the job that measures it.
  3. `run_batch(requests)` runs one job outside the lock. Its results are validated (count, order echo, shots per
     pub) and handed back; RQC_BATCH_DONE is written. Any error after step 2 writes RQC_BATCH_FAILED and aborts:
     nothing is retried here (the job may have run; reconciliation is the dispatcher's job, see rqc.control).

Errors in any participant, a barrier timeout, `cancel()`, or a participant making more calls than registered
abort the whole gather; no participant is replaced and no extra round is run.
"""
import json
import math
import threading
import time

from .hardware import BudgetExhausted


class GatherAborted(RuntimeError):
    """Raised in a participant when the gather was aborted by another participant, a timeout or cancel()."""


class GatherTimeout(GatherAborted):
    """The barrier did not fill within the timeout while no job was in flight."""


class ResultMismatch(RuntimeError):
    """A job returned missing, extra, reordered or wrongly sized results."""


class _BufferedLedger:
    def __init__(self, buf):
        self._buf = buf

    def append(self, kind, payload):
        # snapshot now, as Ledger.append serializes at call time: the frozen _remeasure_best adds fields to the
        # result dict after appending it, and those must not leak into the buffered row
        self._buf.append((kind, json.loads(json.dumps(payload))))


def _jsonable(key):
    return list(key) if isinstance(key, tuple) else key


class GatheringSampler:
    """run(tasks) with tasks = [(key, fn)], fn(sampler, ledger) -> result. Keys must be unique, sortable and
    JSON-encodable.

    run_batch(requests) -> (results, meta): results[i] is the index array for requests[i]; if meta contains
    "circuit_sha256" it must echo the request digests in order. preflight(requests) may raise before anything about
    that job is written."""

    def __init__(self, run_batch, ledger, preflight=None, max_participants=160, max_calls=None,
                 barrier_timeout_s=600.0, protocol_sha256=None, clock=time.monotonic):
        self._run_batch, self._ledger, self._preflight = run_batch, ledger, preflight
        self._max_participants, self._max_calls = max_participants, max_calls
        self._timeout, self._protocol, self._clock = barrier_timeout_s, protocol_sha256, clock
        self._cond = threading.Condition()
        self.batches = []                                   # key lists, in job order
        self.aborted = None

    # ---- called with the lock held ------------------------------------------------------------------------
    def _set_abort(self, e):
        if self._abort is None:
            self._abort = e
        self._cond.notify_all()

    def _take_batch(self):
        if (self._abort is not None or self._in_flight or not self._live
                or set(self._pending) != self._live):
            return None
        keys = sorted(self._pending)
        reqs = [self._pending[k] for k in keys]
        self._pending.clear()
        self._in_flight = True
        return len(self.batches), keys, reqs

    # ---- called without the lock; only the thread that took the batch runs it --------------------------------
    def _flush(self):
        for key in sorted(self._buffers):
            for kind, payload in self._buffers[key]:
                self._ledger.append(kind, payload)
            self._buffers[key].clear()

    def _execute(self, batch):
        n, keys, reqs = batch
        try:
            if self._preflight is not None:
                self._preflight(reqs)
        except BaseException as e:                          # noqa: BLE001
            # refused before submission: the trailing RQC_SUBMIT rows describe a job that was never sent
            for k in keys:
                if self._buffers[k] and self._buffers[k][-1][0] == "RQC_SUBMIT":
                    self._buffers[k].pop()
            self._flush()
            self._ledger.append("RQC_BATCH_REFUSED", {"batch": n, "reason": repr(e)})
            with self._cond:
                self._in_flight = False
                self._set_abort(e)
            return
        try:
            self._flush()
            digests = [c.digest() for c, _ in reqs]
            self._ledger.append("RQC_BATCH_SUBMIT", {
                "batch": n, "pubs": [_jsonable(k) for k in keys], "circuit_sha256": digests,
                "shots": [s for _, s in reqs], "protocol_sha256": self._protocol})
            out, meta = self._run_batch(reqs)
            meta = dict(meta or {})
            if len(out) != len(reqs):
                raise ResultMismatch(f"batch {n}: {len(out)} results for {len(reqs)} pubs")
            if "circuit_sha256" in meta and list(meta["circuit_sha256"]) != digests:
                raise ResultMismatch(f"batch {n}: results are not in request order")
            for (c, shots), o in zip(reqs, out):
                if len(o) != shots:
                    raise ResultMismatch(f"batch {n}: {len(o)} samples for a {shots}-shot pub")
            meta.pop("circuit_sha256", None)
            self._ledger.append("RQC_BATCH_DONE", dict({"batch": n}, **meta))
        except BaseException as e:                          # noqa: BLE001 - every error aborts every participant
            self._ledger.append("RQC_BATCH_FAILED", {"batch": n, "error": repr(e)})
            with self._cond:
                self._in_flight = False
                self._set_abort(e)
            return
        with self._cond:
            self.batches.append(keys)
            for k, o in zip(keys, out):
                self._results[k] = o
            self._in_flight = False
            self._progress = self._clock()
            self._cond.notify_all()

    def _raise_abort(self):
        e = self._abort
        if isinstance(e, BudgetExhausted):
            raise BudgetExhausted(*e.args)
        if isinstance(e, GatherAborted):
            raise e.__class__(*e.args)
        raise GatherAborted(repr(e))

    def _sampler_for(self, key):
        def call(circuit, shots):
            with self._cond:
                if self._abort is not None:
                    self._raise_abort()
                self._calls[key] += 1
                if self._max_calls is not None and self._calls[key] > self._max_calls:
                    self._set_abort(GatherAborted(f"{key} made call {self._calls[key]} of {self._max_calls}"))
                    self._raise_abort()
                if key in self._pending:
                    self._set_abort(GatherAborted(f"{key} has two outstanding calls"))
                    self._raise_abort()
                self._pending[key] = (circuit, shots)
                self._progress = self._clock()
                batch = self._take_batch()
            if batch is not None:
                self._execute(batch)
            with self._cond:
                while key not in self._results and self._abort is None:
                    if self._in_flight:
                        self._cond.wait()
                        continue
                    left = self._timeout - (self._clock() - self._progress)
                    if left <= 0:
                        self._set_abort(GatherTimeout(f"barrier not filled in {self._timeout:.0f}s; waiting: "
                                                      f"{sorted(self._pending)}; live: {sorted(self._live)}"))
                        break
                    self._cond.wait(min(left, 1.0))
                if key in self._results:
                    return self._results.pop(key)
                self._raise_abort()
        return call

    def cancel(self, reason="cancelled"):
        with self._cond:
            self._set_abort(GatherAborted(reason))

    def run(self, tasks):
        """Returns {key: result or the exception that ended that participant}. Never re-raises; `aborted` holds
        the gather-wide error (None when every participant finished)."""
        keys = [k for k, _ in tasks]
        if len(set(keys)) != len(keys):
            raise ValueError("participant keys must be unique")
        if len(keys) > self._max_participants:
            raise ValueError(f"{len(keys)} participants exceed the bound of {self._max_participants}")
        with self._cond:
            self._live, self._pending, self._results, self._abort = set(keys), {}, {}, None
            self._calls = {k: 0 for k in keys}
            self._in_flight, self._progress = False, self._clock()
        self._buffers = {k: [] for k in keys}
        out = {}

        def worker(key, fn):
            try:
                out[key] = fn(self._sampler_for(key), _BufferedLedger(self._buffers[key]))
            except BaseException as e:                      # noqa: BLE001
                out[key] = e
            with self._cond:
                self._live.discard(key)
                if isinstance(out[key], BaseException):
                    self._set_abort(out[key])
                batch = self._take_batch()
                self._cond.notify_all()
            if batch is not None:
                self._execute(batch)

        threads = [threading.Thread(target=worker, args=(k, fn), daemon=True, name=f"rqc-{k}") for k, fn in tasks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self._flush()                                       # rows written after the last job (final RQC_RESULTs)
        self.aborted = self._abort
        return out


# Planning constants (amendment 5), from this account's billed jobs observed 2026-10-08 (see
# docs/rqc/S2/budget_audit.json): 2,048 shots of a ~45-CZ circuit executed 0.537 s and billed 3 s; 20 pubs x 512
# shots executed 2.95 s and billed 5 s. Locally observed on 10 jobs, not provider-documented.
RATE_S_PER_SHOT = 0.27e-3
PER_PUB_S = 0.015
PER_JOB_S = 3.0


def projected_seconds(requests, rate=RATE_S_PER_SHOT, per_pub=PER_PUB_S, per_job=PER_JOB_S):
    """Billed-seconds projection for one job, rounded up to whole seconds."""
    return math.ceil(per_job + len(requests) * per_pub + rate * sum(s for _, s in requests))
