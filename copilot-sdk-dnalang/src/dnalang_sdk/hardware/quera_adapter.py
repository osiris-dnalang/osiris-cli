#!/usr/bin/env python3
"""
QuEra Correlated Decoder Adapter

Integrates the Tesseract A* decoder (from tesseract_resonator.py) into a simple
correlated-decoder wrapper and runs a 256-atom dry-run. This is a minimal, dependency-free
adapter for dry-run and PR purposes.
"""

import argparse
import json
import random
import time
import logging

# Import the lightweight Tesseract decoder implemented in this repo
from dnalang_sdk.decoders.tesseract import TesseractDecoderOrganism, TesseractResonatorOrganism

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuEraCorrelatedAdapter:
    def __init__(self, atoms=256, rounds=3, beam_width=20, pqlimit=2500000, forbidden_mode='at_most_two', seed=None):
        try:
            self.atoms = int(atoms)
            self.rounds = int(rounds)
            self.seed = seed
            if seed is not None:
                random.seed(seed)
            self.error_map = self.build_error_map()
            self.decoder = TesseractDecoderOrganism(
                detectors=list(range(self.atoms)),
                error_map=self.error_map,
                beam_width=beam_width,
                pqlimit=pqlimit,
                forbidden_mode=forbidden_mode,
            )
            logger.debug(f"QuEraCorrelatedAdapter initialized: atoms={self.atoms} rounds={self.rounds}")
        except Exception:
            logger.exception('Failed to initialize QuEraCorrelatedAdapter')
            raise

    def build_error_map(self):
        """Construct a simple local error_map for N detectors.
        Each error touches two neighboring detectors (ring topology).
        """
        N = self.atoms
        emap = {}
        for i in range(N):
            emap[i] = {i, (i + 1) % N}
        return emap

    def inject_logical_errors(self, k=3):
        k = min(self.atoms, max(1, int(k)))
        return set(random.sample(range(self.atoms), k))

    def generate_round_syndromes(self, logical_errors=None, per_detector_noise=0.02):
        """Generate `rounds` noisy syndrome rounds from an underlying logical error set.
        Returns: (rounds_list, logical_errors, S_true)
        """
        try:
            if logical_errors is None:
                logical_errors = self.inject_logical_errors(k=max(1, self.atoms // 128))
            S_true = self.decoder.D(logical_errors)
            rounds = []
            for r in range(self.rounds):
                S = set(S_true)
                # flip each detector with small probability to simulate measurement noise
                for d in range(self.atoms):
                    if random.random() < per_detector_noise:
                        if d in S:
                            S.remove(d)
                        else:
                            S.add(d)
                rounds.append(S)
            return rounds, logical_errors, S_true
        except Exception:
            logger.exception('Error generating round syndromes')
            raise

    def correlated_merge_rounds(self, S_rounds, threshold=None):
        """Simple majority-vote merge across rounds to produce a single merged syndrome."""
        try:
            R = len(S_rounds)
            if R == 0:
                return set()
            counts = [0] * self.atoms
            for S in S_rounds:
                for d in S:
                    counts[d] += 1
            if threshold is None:
                threshold = (R // 2) + 1
            merged = {i for i, c in enumerate(counts) if c >= threshold}
            return merged
        except Exception:
            logger.exception('Error merging rounds')
            raise

    def decode_merged(self, merged_syndrome, beam=None, pqlimit=None):
        return self.decoder.decode(merged_syndrome, beam=beam, pqlimit=pqlimit)

    def run_dry(self, per_detector_noise=0.02):
        """Run a complete dry-run: generate syndromes, merge, decode. Returns result dict."""
        S_rounds, logical_errors, S_true = self.generate_round_syndromes(
            per_detector_noise=per_detector_noise)
        merged = self.correlated_merge_rounds(S_rounds)
        try:
            decode_result = self.decode_merged(merged)
        except Exception:
            logger.exception('Decoder failed during dry run')
            decode_result = {'error': 'decoder_failed'}
        return {
            'atoms': self.atoms,
            'rounds': self.rounds,
            'logical_errors': sorted(logical_errors),
            'S_true': sorted(S_true),
            'merged': sorted(merged),
            'decoded': decode_result,
            'timestamp': time.time(),
        }


def load_config():
    """Load configuration from environment variables with sensible defaults."""
    import os

    cfg = {
        'atoms': int(os.getenv('Q_ADAPTER_ATOMS', '256')),
        'rounds': int(os.getenv('Q_ADAPTER_ROUNDS', '3')),
        'seed': os.getenv('Q_ADAPTER_SEED', None),
        'out': os.getenv('Q_ADAPTER_OUT', 'quera_256_dryrun.json'),
        'beam': int(os.getenv('Q_ADAPTER_BEAM', '64')),
        'pqlimit': int(os.getenv('Q_ADAPTER_PQLIMIT', '500000')),
    }
    # convert seed to int if present
    if cfg['seed'] is not None:
        try:
            cfg['seed'] = int(cfg['seed'])
        except ValueError:
            logger.warning('Invalid Q_ADAPTER_SEED value, ignoring')
            cfg['seed'] = None
    return cfg


def main():
    parser = argparse.ArgumentParser(description='QuEra correlated decoder adapter dry-run')
    parser.add_argument('--atoms', type=int, default=None)
    parser.add_argument('--rounds', type=int, default=None)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--out', default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    cfg = load_config()
    atoms = args.atoms if args.atoms is not None else cfg['atoms']
    rounds = args.rounds if args.rounds is not None else cfg['rounds']
    seed = args.seed if args.seed is not None else cfg['seed']
    out_path = args.out if args.out is not None else cfg['out']
    beam = cfg['beam']
    pqlimit = cfg['pqlimit']

    logger.info(f"Running adapter with atoms={atoms} rounds={rounds} seed={seed} beam={beam} pqlimit={pqlimit}")

    adapter = QuEraCorrelatedAdapter(atoms=atoms, rounds=rounds, seed=seed, pqlimit=pqlimit)
    S_rounds, logical_errors, S_true = adapter.generate_round_syndromes(per_detector_noise=0.02)
    merged = adapter.correlated_merge_rounds(S_rounds)

    # decode with moderate resource limits for a dry-run
    try:
        decode_result = adapter.decode_merged(merged, beam=beam, pqlimit=pqlimit)
    except Exception:
        logger.exception('Decoder failed')
        decode_result = {'error': 'decoder_failed'}

    out = {
        'atoms': atoms,
        'rounds': rounds,
        'seed': seed,
        'logical_errors': sorted(list(logical_errors)),
        'S_true': sorted(list(S_true)),
        'S_rounds': [sorted(list(s)) for s in S_rounds],
        'merged': sorted(list(merged)),
        'decoder_result': decode_result,
        'timestamp': time.time(),
    }

    try:
        with open(out_path, 'w') as fh:
            json.dump(out, fh, indent=2)
        logger.info(f"Wrote dry-run output to {out_path}")
    except Exception:
        logger.exception('Failed to write output file')


if __name__ == '__main__':
    main()
