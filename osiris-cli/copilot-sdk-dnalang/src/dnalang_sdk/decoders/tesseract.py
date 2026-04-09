#!/usr/bin/env python3
"""
Minimal Tesseract Resonator + Decoder organism for Omega Runtime.
- TesseractDecoderOrganism: predicate pruning, admissible heuristic, beam pruning, simple A* decoder (pqlimit)
- TesseractResonatorOrganism: resonance_4d_mapping (stub quaternion-like frame) and deploy() to emit dry-run JSON

This is intentionally dependency-free and safe to run as a local dry-run.
"""

import math
import json
import heapq
import time
import random

class TesseractDecoderOrganism:
    """Lightweight implementation of the Tesseract decoder heuristics.

    error_map: dict(error_id -> iterable(detector_id))
    detectors: iterable of detector ids (ints)
    S: observed syndrome set (set of detector ids)
    """

    def __init__(self, error_map, detectors=None, error_weights=None, det_cost=None,
                 beam_width=20, pqlimit=10000000*6, c_detection=1.0, forbidden_mode='at_most_two'):
        if detectors is None:
            detectors = set()
            for ds in error_map.values():
                detectors.update(ds)
        self.detectors = set(detectors)
        self.error_map = {int(e): set(ds) for e, ds in error_map.items()}
        self.detector_to_errors = {}
        for e, ds in self.error_map.items():
            for d in ds:
                self.detector_to_errors.setdefault(d, set()).add(e)
        self.error_weights = error_weights or {e: 1.0 for e in self.error_map}
        self.det_cost = det_cost or {d: 1.0 for d in self.detectors}
        self.beam_width = beam_width
        self.pqlimit = pqlimit
        self.c_detection = c_detection
        self.forbidden_mode = forbidden_mode

    # ----- syndrome / error set helpers -----
    def D(self, F):
        """Detector parity produced by error set F (symmetric difference)."""
        res = set()
        for e in F:
            res ^= self.error_map.get(e, set())
        return res

    def residual_syndrome(self, S, F):
        return set(S).symmetric_difference(self.D(F))

    def errors_touching(self, detector):
        return set(self.detector_to_errors.get(detector, set()))

    # ----- pruning helpers -----
    def precedence_forbidden(self, F, candidates):
        """Two variants: exact (precedence) or approximate (at most two).
        - 'precedence' enforces a simple lexical precedence based on numeric ids
        - 'at_most_two' returns up to two lowest-id candidates to forbid
        """
        if self.forbidden_mode == 'precedence':
            if not F:
                return set()
            max_f = max(F)
            return {e for e in candidates if e <= max_f}
        else:
            # approximate: forbid up to two smallest candidates already in F
            if not F:
                return set()
            return set(sorted(candidates & set(F))[:2])

    def prune_edges(self, F, residual_syndrome):
        """Predicate pruning P(F,e): only errors touching the lowest-index activated detector are allowed,
        minus forbidden errors from precedence rules."""
        if not residual_syndrome:
            return set()
        lowest = min(residual_syndrome)
        candidates = self.errors_touching(lowest)
        forbidden = self.precedence_forbidden(F, candidates)
        return candidates - forbidden

    # ----- costs & heuristic -----
    def heuristic(self, S, F):
        residual = self.residual_syndrome(S, F)
        return sum(self.det_cost.get(d, 1.0) for d in residual)

    def g_cost(self, F):
        return sum(self.error_weights.get(e, 1.0) for e in F)

    def f_priority(self, S, F):
        return self.g_cost(F) + self.heuristic(S, F) + self.c_detection * len(self.residual_syndrome(S, F))

    def beam_prune(self, S, F, r_min):
        return len(self.residual_syndrome(S, F)) <= r_min + self.beam_width

    # ----- simple A* with pruning and beam -----
    def decode(self, S, beam=None, pqlimit=None):
        """Attempt to find a correction F such that residual_syndrome==0.
        Returns a dict with correction (list) or None and statistics.
        """
        beam = self.beam_width if beam is None else beam
        pqlimit = self.pqlimit if pqlimit is None else pqlimit

        start = frozenset()
        pq = []
        start_f = self.f_priority(S, set())
        heapq.heappush(pq, (start_f, 0.0, start))
        visited = {start: 0.0}
        nodes = 0
        r_min = len(S)
        best = None
        best_cost = float('inf')

        while pq and nodes < pqlimit:
            f, g, F = heapq.heappop(pq)
            nodes += 1
            F_set = set(F)
            residual = self.residual_syndrome(S, F_set)
            r = len(residual)
            if r < r_min:
                r_min = r
            # beam pruning
            if not self.beam_prune(S, F_set, r_min):
                continue
            # solution
            if r == 0:
                cost = self.g_cost(F_set)
                if cost < best_cost:
                    best = F_set.copy()
                    best_cost = cost
                    break
            # expand
            allowed = self.prune_edges(F_set, residual)
            for e in allowed:
                if e in F_set:
                    continue
                F2 = frozenset(F_set | {e})
                g2 = self.g_cost(F_set) + self.error_weights.get(e, 1.0)
                if F2 in visited and visited[F2] <= g2:
                    continue
                visited[F2] = g2
                f2 = self.f_priority(S, set(F2))
                heapq.heappush(pq, (f2, g2, F2))
        return {'correction': list(best) if best else None, 'nodes_explored': nodes, 'best_cost': best_cost}


class TesseractResonatorOrganism:
    """Minimal resonator organism that produces a stubbed 4D mapping and a pulse schedule JSON.
    The real implementation would replace the stubs with quaternion optimization and AWG/HW calls.
    """

    def __init__(self, backend='ibm_torino', qubits=40):
        self.backend = backend
        self.qubits = int(qubits)
        self.orientation = None
        self.pulse_schedule = []

    def resonance_4d_mapping(self, embedding_11d=None):
        """Create a deterministic stub of a 4D orientation (normalized 4-vector) and a simple pulse schedule.
        Returns the pulse schedule (list of dicts).
        """
        # deterministic pseudo-quaternion frame
        random.seed(42)
        q = [random.random() for _ in range(4)]
        norm = math.sqrt(sum(x * x for x in q))
        q = [x / norm for x in q]
        self.orientation = q
        # create a minimal schedule describing a global 4D resonance pulse
        self.pulse_schedule = [{
            'name': 'resonance_4d_map',
            'target_qubits': list(range(self.qubits)),
            'orientation': q,
            'amplitude': 0.5,
            'duration_ns': 200
        }]
        return self.pulse_schedule

    def deploy(self, dry_run=True, out_path=None):
        if not self.pulse_schedule:
            self.resonance_4d_mapping()
        result = {
            'backend': self.backend,
            'qubits': self.qubits,
            'orientation': self.orientation,
            'pulses': self.pulse_schedule,
            'timestamp': time.time()
        }
        if out_path:
            with open(out_path, 'w') as fh:
                json.dump(result, fh, indent=2)
        if dry_run:
            print(json.dumps(result, indent=2))
        return result


# ---- Demo utilities ----
def _demo_decoder_run():
    # build a toy error_map for 40 detectors; each error flips two neighboring detectors
    det_count = 40
    error_map = {i: {(i) % det_count, (i + 1) % det_count} for i in range(det_count)}
    S = {0, 3, 7}  # synthetic syndrome
    dec = TesseractDecoderOrganism(detectors=list(range(det_count)), error_map=error_map)
    out = dec.decode(S)
    print('Decoder demo result:', json.dumps(out, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true', help='Deploy resonance mapping locally (dry-run)')
    parser.add_argument('--out', default='tesseract_resonator_deploy.json')
    parser.add_argument('--demo-decode', action='store_true', help='Run a demo decode and exit')
    args = parser.parse_args()

    if args.demo_decode:
        _demo_decoder_run()
    elif args.deploy:
        t = TesseractResonatorOrganism(qubits=40)
        t.deploy(dry_run=True, out_path=args.out)
    else:
        # default: run both demo decode and a dry-run deploy
        _demo_decoder_run()
        TesseractResonatorOrganism(qubits=40).deploy(dry_run=True)
