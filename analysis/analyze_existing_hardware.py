#!/usr/bin/env python3
"""
Analyze Existing IBM Quantum Hardware Data (v2 - with decompression)
=====================================================================
Extract timestamps, fidelities, and τ-phase correlations from
locally stored IBM job files WITHOUT needing an API token.

Nobel Protocol v1.1 - Offline Analysis Module
"""

import json
import base64
import numpy as np
import zlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

# Physical constants
TAU_0 = 46e-6  # τ₀ = 46 μs
LAMBDA_PHI = 2.176435e-8  # Universal Memory Constant

def decode_bitarray(bitarray_data, num_shots):
    """Decode BitArray from IBM result format to shot outcomes."""
    try:
        array_data = bitarray_data.get('array', {})
        num_bits = bitarray_data.get('num_bits', 2)
        
        if isinstance(array_data, dict) and array_data.get('__type__') == 'ndarray':
            encoded = array_data.get('__value__', '')
            raw_bytes = base64.b64decode(encoded)
            
            # Try zlib decompression first
            try:
                decompressed = zlib.decompress(raw_bytes)
                arr = np.frombuffer(decompressed, dtype=np.uint8)
            except:
                arr = np.frombuffer(raw_bytes, dtype=np.uint8)
            
            return arr, num_bits
    except Exception as e:
        return None, 0
    return None, 0

def extract_counts_from_bitarray(arr, num_bits, num_shots):
    """Extract measurement counts from decoded BitArray."""
    if arr is None:
        return None

    bytes_per_shot = (num_bits + 7) // 8
    counts = defaultdict(int)

    for i in range(min(num_shots, len(arr) // bytes_per_shot)):
        start_idx = i * bytes_per_shot
        outcome = 0
        for j in range(bytes_per_shot):
            if start_idx + j < len(arr):
                outcome |= arr[start_idx + j] << (8 * j)
        outcome &= (1 << num_bits) - 1
        bitstring = format(outcome, f'0{num_bits}b')
        counts[bitstring] += 1

    return dict(counts)

def calculate_fidelity(counts, num_bits=2):
    """Calculate Bell state fidelity F = P(00) + P(11)."""
    if not counts:
        return None

    total = sum(counts.values())
    if total == 0:
        return None

    p00 = counts.get('0' * num_bits, 0) / total
    p11 = counts.get('1' * num_bits, 0) / total if num_bits == 2 else 0

    return {
        'P00': p00,
        'P11': p11,
        'fidelity': p00 + p11,
        'total_shots': total,
        'counts': counts
    }

def parse_datetime(dt_obj):
    """Parse datetime from various IBM formats."""
    if isinstance(dt_obj, dict) and dt_obj.get('__type__') == 'datetime':
        dt_str = dt_obj.get('__value__', '')
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None
    elif isinstance(dt_obj, str):
        try:
            return datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
        except:
            return None
    return None

def calculate_tau_phase(timestamp):
    """Calculate τ-phase from timestamp."""
    if timestamp is None:
        return None

    unix_ts = timestamp.timestamp()
    phase = (unix_ts % TAU_0) / TAU_0
    return phase

def analyze_job_file(info_path, result_path):
    """Analyze a single job from its info and result files."""
    try:
        with open(info_path) as f:
            info = json.load(f)
        with open(result_path) as f:
            result = json.load(f)
    except Exception as e:
        return None

    job_id = info.get('id', 'unknown')
    backend = info.get('backend', 'unknown')
    created = info.get('created', '')
    status = info.get('status', '')

    if isinstance(created, str):
        try:
            timestamp = datetime.fromisoformat(created.replace('Z', '+00:00'))
        except:
            timestamp = None
    else:
        timestamp = None

    shots = 2048
    params = info.get('params', {})
    pubs = params.get('pubs', [])
    if pubs and len(pubs) > 0:
        if isinstance(pubs[0], list) and len(pubs[0]) >= 3:
            shots = pubs[0][2]

    circuit_name = None
    circuit_desc = None

    result_value = result.get('__value__', result)
    pub_results = result_value.get('pub_results', [])

    fidelity_data = None
    execution_start = None
    execution_stop = None

    for pub in pub_results:
        pub_value = pub.get('__value__', pub) if isinstance(pub, dict) else pub

        metadata = pub_value.get('metadata', {})
        circuit_meta = metadata.get('circuit_metadata', {})
        circuit_name = circuit_meta.get('name', circuit_name)
        circuit_desc = circuit_meta.get('description', circuit_desc)

        data = pub_value.get('data', {})
        data_value = data.get('__value__', data) if isinstance(data, dict) else data

        if isinstance(data_value, dict):
            fields = data_value.get('fields', {})
            c_field = fields.get('c', {})
            if isinstance(c_field, dict) and c_field.get('__type__') == 'BitArray':
                bitarray = c_field.get('__value__', {})
                arr, num_bits = decode_bitarray(bitarray, shots)
                if arr is not None:
                    counts = extract_counts_from_bitarray(arr, num_bits, shots)
                    fidelity_data = calculate_fidelity(counts, num_bits)

    # Get execution spans
    metadata = result_value.get('metadata', {})
    execution = metadata.get('execution', {})
    spans = execution.get('execution_spans', {})
    if isinstance(spans, dict) and spans.get('__type__') == 'ExecutionSpans':
        spans_value = spans.get('__value__', {})
        span_list = spans_value.get('spans', [])
        for span in span_list:
            if isinstance(span, dict):
                span_value = span.get('__value__', span)
                execution_start = parse_datetime(span_value.get('start'))
                execution_stop = parse_datetime(span_value.get('stop'))
                break

    effective_timestamp = execution_start or timestamp
    tau_phase = calculate_tau_phase(effective_timestamp)

    return {
        'job_id': job_id,
        'backend': backend,
        'created': created,
        'timestamp': effective_timestamp.isoformat() if effective_timestamp else None,
        'execution_start': execution_start.isoformat() if execution_start else None,
        'execution_stop': execution_stop.isoformat() if execution_stop else None,
        'status': status,
        'shots': shots,
        'circuit_name': circuit_name,
        'circuit_description': circuit_desc,
        'tau_phase': tau_phase,
        'fidelity': fidelity_data
    }

def main():
    """Main analysis routine."""
    job_dir = Path('/home/dnalang')
    output_dir = Path('/home/dnalang/PUBLICATION/LAMBDA_PHI_PAPER')

    info_files = sorted(job_dir.glob('job-*-info.json'))

    print(f"Found {len(info_files)} job info files")

    results = []
    backends = defaultdict(list)

    for info_path in info_files:
        job_id = info_path.stem.replace('-info', '').replace('job-', '')
        result_path = job_dir / f'job-{job_id}-result.json'

        if not result_path.exists():
            continue

        analysis = analyze_job_file(info_path, result_path)
        if analysis and analysis['fidelity']:
            results.append(analysis)
            backends[analysis['backend']].append(analysis)
            sys.stdout.write(f"\rAnalyzed {len(results)} jobs...")
            sys.stdout.flush()

    print(f"\n\nSuccessfully analyzed {len(results)} jobs")
    print(f"\nBackends: {dict((k, len(v)) for k, v in backends.items())}")

    # Filter to Bell state jobs only (high fidelity)
    bell_results = [r for r in results if r['fidelity']['fidelity'] > 0.5]
    print(f"\nBell state jobs (F > 0.5): {len(bell_results)}")

    print("\n" + "="*60)
    print("τ-PHASE CORRELATION ANALYSIS (Bell State Jobs)")
    print("="*60)

    aligned_fidelities = []
    antialigned_fidelities = []
    phase_bins = defaultdict(list)

    for r in bell_results:
        if r['tau_phase'] is not None and r['fidelity']:
            phase = r['tau_phase']
            fid = r['fidelity']['fidelity']  # Use Bell fidelity

            bin_idx = int(phase * 10) % 10
            phase_bins[bin_idx].append(fid)

            if phase < 0.5:
                aligned_fidelities.append(fid)
            else:
                antialigned_fidelities.append(fid)

    if aligned_fidelities and antialigned_fidelities:
        aligned_mean = np.mean(aligned_fidelities)
        antialigned_mean = np.mean(antialigned_fidelities)
        aligned_std = np.std(aligned_fidelities)
        antialigned_std = np.std(antialigned_fidelities)

        ratio = aligned_mean / antialigned_mean if antialigned_mean > 0 else float('inf')

        n1, n2 = len(aligned_fidelities), len(antialigned_fidelities)
        pooled_se = np.sqrt(aligned_std**2/n1 + antialigned_std**2/n2)
        t_stat = (aligned_mean - antialigned_mean) / pooled_se if pooled_se > 0 else 0

        pooled_std = np.sqrt(((n1-1)*aligned_std**2 + (n2-1)*antialigned_std**2) / (n1+n2-2))
        cohens_d = (aligned_mean - antialigned_mean) / pooled_std if pooled_std > 0 else 0

        print(f"\nτ-aligned (phase 0-0.5):     N={n1}, Mean={aligned_mean:.4f} ± {aligned_std:.4f}")
        print(f"τ-anti-aligned (phase 0.5-1): N={n2}, Mean={antialigned_mean:.4f} ± {antialigned_std:.4f}")
        print(f"\nRatio: {ratio:.4f}×")
        print(f"t-statistic: {t_stat:.3f}")
        print(f"Cohen's d: {cohens_d:.3f}")

        print("\n" + "-"*60)
        print("10-BIN τ-PHASE FIDELITY DISTRIBUTION")
        print("-"*60)
        print(f"{'Bin':>4} {'Phase Range':>15} {'N':>6} {'Mean F':>10} {'Std':>10}")
        print("-"*60)

        bin_stats = []
        for i in range(10):
            if phase_bins[i]:
                mean_f = np.mean(phase_bins[i])
                std_f = np.std(phase_bins[i])
                bin_stats.append({
                    'bin': i,
                    'phase_start': i/10,
                    'phase_end': (i+1)/10,
                    'n': len(phase_bins[i]),
                    'mean': mean_f,
                    'std': std_f
                })
                print(f"{i:>4} {i/10:.1f}-{(i+1)/10:.1f}         {len(phase_bins[i]):>6} {mean_f:>10.4f} {std_f:>10.4f}")

        # ANOVA
        all_fids = [r['fidelity']['fidelity'] for r in bell_results if r['tau_phase'] is not None]
        overall_mean = np.mean(all_fids)

        ssb = sum(len(phase_bins[i]) * (np.mean(phase_bins[i]) - overall_mean)**2
                  for i in range(10) if phase_bins[i])
        ssw = sum(sum((f - np.mean(phase_bins[i]))**2 for f in phase_bins[i])
                  for i in range(10) if phase_bins[i])

        k = sum(1 for i in range(10) if phase_bins[i])
        n_total = len(all_fids)
        msb = ssb / (k - 1) if k > 1 else 0
        msw = ssw / (n_total - k) if n_total > k else 0
        f_stat = msb / msw if msw > 0 else 0

        print("\n" + "-"*60)
        print(f"ANOVA: F-statistic = {f_stat:.3f}")

        # Backend-specific analysis
        print("\n" + "="*60)
        print("BACKEND-SPECIFIC ANALYSIS")
        print("="*60)

        for backend, backend_results in backends.items():
            bell_backend = [r for r in backend_results if r['fidelity']['fidelity'] > 0.5]
            if not bell_backend:
                continue
                
            backend_aligned = [r['fidelity']['fidelity'] for r in bell_backend
                             if r['tau_phase'] is not None and r['tau_phase'] < 0.5]
            backend_anti = [r['fidelity']['fidelity'] for r in bell_backend
                          if r['tau_phase'] is not None and r['tau_phase'] >= 0.5]

            if backend_aligned and backend_anti:
                b_ratio = np.mean(backend_aligned) / np.mean(backend_anti)
                print(f"\n{backend}:")
                print(f"  Aligned:     N={len(backend_aligned)}, Mean={np.mean(backend_aligned):.4f} ± {np.std(backend_aligned):.4f}")
                print(f"  Anti-aligned: N={len(backend_anti)}, Mean={np.mean(backend_anti):.4f} ± {np.std(backend_anti):.4f}")
                print(f"  Ratio: {b_ratio:.4f}×")

        # Save results
        output_file = output_dir / 'hardware_analysis_results.json'
        output_data = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_jobs_analyzed': len(results),
            'bell_state_jobs': len(bell_results),
            'backends': {k: len(v) for k, v in backends.items()},
            'tau_phase_statistics': {
                'aligned_mean': float(aligned_mean),
                'aligned_std': float(aligned_std),
                'aligned_n': len(aligned_fidelities),
                'antialigned_mean': float(antialigned_mean),
                'antialigned_std': float(antialigned_std),
                'antialigned_n': len(antialigned_fidelities),
                'ratio': float(ratio),
                't_statistic': float(t_stat),
                'cohens_d': float(cohens_d),
                'f_statistic_anova': float(f_stat)
            },
            'bin_statistics': bin_stats,
            'jobs': results
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        print(f"\n\nResults saved to: {output_file}")

        # Nobel protocol assessment
        print("\n" + "="*60)
        print("NOBEL PROTOCOL v1.1 ASSESSMENT")
        print("="*60)

        criteria = {
            'tau_phase_ratio_significant': abs(ratio - 1.0) > 0.05,  # >5% difference
            'cohens_d_measurable': abs(cohens_d) > 0.2,  # At least small effect
            'multiple_backends': len([b for b in backends.values() if any(r['fidelity']['fidelity'] > 0.5 for r in b)]) >= 2,
            'sample_size_adequate': len(bell_results) >= 10,
            't_stat_significant': abs(t_stat) > 2.0
        }

        print("\nCriteria Assessment:")
        for criterion, met in criteria.items():
            status = "✓ MET" if met else "✗ NOT MET"
            print(f"  {criterion}: {status}")

        criteria_met = sum(criteria.values())
        print(f"\nTotal: {criteria_met}/{len(criteria)} criteria met")

        if criteria_met >= 4:
            print("\n>>> STRONG EVIDENCE FOR τ-PHASE ANOMALY <<<")
        elif criteria_met >= 3:
            print("\n>>> SUGGESTIVE EVIDENCE - REQUIRES PROSPECTIVE VALIDATION <<<")
        else:
            print("\n>>> INSUFFICIENT EVIDENCE - PROSPECTIVE EXPERIMENT NEEDED <<<")

if __name__ == '__main__':
    main()
