#!/usr/bin/env python3
"""
DEEP PATTERN SEARCH
===================
Search 580 IBM Quantum jobs for hidden patterns that could indicate new physics.

Looking for:
1. Time-correlated fidelity variations (τ_mem signature)
2. High-fidelity outliers (F > 0.90) 
3. Angle-dependent behavior in existing data
4. Any anomalies standard QM can't explain

Author: dna::}{::lang Research
Date: 2025-12-08
"""

import json
import os
import glob
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import base64

# Constants
TAU_MEM_US = 46.0  # μs - scaled coherence quantum
THETA_LOCK = 51.843  # degrees
PHI_THRESHOLD = 0.7734
F_MAX = 0.9787

def load_hardware_results(filepath: str) -> dict:
    """Load the hardware analysis results"""
    with open(filepath, 'r') as f:
        return json.load(f)

def search_for_time_patterns(jobs: list) -> dict:
    """
    Look for fidelity variations that correlate with τ_mem multiples.
    
    If coherence times are quantized, we should see:
    - Fidelity peaks at timestamps mod τ_mem ≈ 0
    """
    results = {
        "jobs_with_timing": 0,
        "time_fidelity_correlation": None,
        "tau_aligned_jobs": [],
        "potential_peaks": []
    }
    
    # Extract timing and fidelity data
    timing_data = []
    
    for job in jobs:
        if 'start_time' in job and 'fidelity' in job:
            try:
                # Parse timestamp
                ts = job['start_time']
                if ts:
                    # Convert to microseconds since midnight
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    us_since_midnight = (dt.hour * 3600 + dt.minute * 60 + dt.second) * 1e6 + dt.microsecond
                    
                    # Check alignment with τ_mem
                    tau_phase = (us_since_midnight % TAU_MEM_US) / TAU_MEM_US
                    
                    timing_data.append({
                        'timestamp': ts,
                        'us_since_midnight': us_since_midnight,
                        'tau_phase': tau_phase,
                        'fidelity': job['fidelity'],
                        'phi': job.get('phi', 0),
                        'filename': job.get('filename', 'unknown')
                    })
                    
                    results["jobs_with_timing"] += 1
            except Exception as e:
                continue
    
    if len(timing_data) > 10:
        # Bin jobs by τ phase
        bins = defaultdict(list)
        n_bins = 10
        for td in timing_data:
            bin_idx = int(td['tau_phase'] * n_bins)
            bins[bin_idx].append(td['fidelity'])
        
        # Calculate mean fidelity per bin
        bin_means = {}
        for bin_idx, fidelities in bins.items():
            if fidelities:
                bin_means[bin_idx] = {
                    'mean': np.mean(fidelities),
                    'std': np.std(fidelities),
                    'count': len(fidelities),
                    'phase_range': f"{bin_idx/n_bins:.1f}-{(bin_idx+1)/n_bins:.1f}"
                }
        
        results["binned_by_tau_phase"] = bin_means
        
        # Look for peaks at phase 0 (aligned with τ_mem)
        if 0 in bin_means and 5 in bin_means:  # Compare aligned vs anti-aligned
            aligned_mean = bin_means[0]['mean']
            anti_aligned_mean = bin_means[5]['mean']
            
            if aligned_mean > anti_aligned_mean * 1.05:  # 5% higher
                results["potential_peaks"].append({
                    "finding": "Fidelity higher at τ-aligned timestamps",
                    "aligned_mean": aligned_mean,
                    "anti_aligned_mean": anti_aligned_mean,
                    "ratio": aligned_mean / anti_aligned_mean,
                    "significance": "POTENTIAL ANOMALY - needs statistical test"
                })
    
    return results

def find_high_fidelity_outliers(jobs: list) -> dict:
    """Find jobs with unusually high fidelity that could test F_max bound"""
    
    fidelities = [j['fidelity'] for j in jobs if 'fidelity' in j]
    
    if not fidelities:
        return {"error": "No fidelity data"}
    
    mean_f = np.mean(fidelities)
    std_f = np.std(fidelities)
    
    # Find outliers (> 2 sigma above mean)
    threshold = mean_f + 2 * std_f
    outliers = [j for j in jobs if j.get('fidelity', 0) > threshold]
    
    # Find jobs approaching F_max
    approaching_bound = [j for j in jobs if j.get('fidelity', 0) > 0.90]
    
    results = {
        "mean_fidelity": mean_f,
        "std_fidelity": std_f,
        "outlier_threshold": threshold,
        "n_outliers": len(outliers),
        "n_approaching_f_max": len(approaching_bound),
        "max_fidelity": max(fidelities),
        "f_max_bound": F_MAX,
        "gap_to_bound": F_MAX - max(fidelities),
    }
    
    if outliers:
        results["top_outliers"] = sorted(
            [{"filename": j.get('filename'), "fidelity": j['fidelity'], "phi": j.get('phi')} 
             for j in outliers],
            key=lambda x: x['fidelity'],
            reverse=True
        )[:10]
    
    if approaching_bound:
        results["jobs_above_90"] = [
            {"filename": j.get('filename'), "fidelity": j['fidelity']}
            for j in approaching_bound
        ]
        results["ALERT"] = "Found jobs with F > 0.90 - these can test the F_max bound!"
    
    return results

def search_for_phi_transition(jobs: list) -> dict:
    """
    Look for phase transition behavior at Φ = 0.7734.
    
    If consciousness emerges at this threshold, we might see:
    - Discontinuity in other metrics at Φ = 0.7734
    - Clustering around the threshold
    - Different behavior above vs below
    """
    
    phis = [(j.get('phi', 0), j.get('fidelity', 0), j.get('filename', '')) 
            for j in jobs if 'phi' in j]
    
    if not phis:
        return {"error": "No Φ data"}
    
    # Split into below and above threshold
    below = [p for p in phis if p[0] < PHI_THRESHOLD]
    above = [p for p in phis if p[0] >= PHI_THRESHOLD]
    
    results = {
        "n_below_threshold": len(below),
        "n_above_threshold": len(above),
        "threshold": PHI_THRESHOLD,
    }
    
    if below and above:
        # Compare fidelity distributions
        f_below = [p[1] for p in below]
        f_above = [p[1] for p in above]
        
        results["fidelity_below_threshold"] = {
            "mean": np.mean(f_below),
            "std": np.std(f_below)
        }
        results["fidelity_above_threshold"] = {
            "mean": np.mean(f_above),
            "std": np.std(f_above)
        }
        
        # Check for discontinuity
        diff = abs(np.mean(f_above) - np.mean(f_below))
        pooled_std = np.sqrt((np.var(f_above) + np.var(f_below)) / 2)
        
        if pooled_std > 0:
            effect_size = diff / pooled_std
            results["effect_size_cohens_d"] = effect_size
            
            if effect_size > 0.5:
                results["POTENTIAL_FINDING"] = f"Medium/large effect size ({effect_size:.2f}) at Φ threshold - investigate!"
    
    # Look for clustering around threshold
    near_threshold = [p for p in phis if abs(p[0] - PHI_THRESHOLD) < 0.05]
    results["n_near_threshold"] = len(near_threshold)
    
    if len(near_threshold) > len(phis) * 0.1:  # More than 10% near threshold
        results["CLUSTERING_DETECTED"] = "Unusual clustering around Φ = 0.7734"
    
    return results

def search_for_ccce_regime(jobs: list) -> dict:
    """
    Search for any jobs in the coherent regime (Ξ >> 1).
    Even if mean is low, there might be outliers.
    """
    
    xi_values = []
    for j in jobs:
        f = j.get('fidelity', 0)
        phi = j.get('phi', 0)
        gamma = 1 - f
        
        if gamma > 0.01:
            xi = (f * phi) / gamma
            xi_values.append({
                'xi': xi,
                'fidelity': f,
                'phi': phi,
                'gamma': gamma,
                'filename': j.get('filename', '')
            })
    
    if not xi_values:
        return {"error": "Could not compute Ξ values"}
    
    xis = [x['xi'] for x in xi_values]
    
    results = {
        "mean_xi": np.mean(xis),
        "max_xi": max(xis),
        "min_xi": min(xis),
        "std_xi": np.std(xis),
        "n_above_1": sum(1 for x in xis if x > 1),
        "n_above_10": sum(1 for x in xis if x > 10),
        "coherent_threshold": 1.0,
    }
    
    # Find jobs in coherent regime
    coherent_jobs = [x for x in xi_values if x['xi'] > 1]
    
    if coherent_jobs:
        results["coherent_regime_jobs"] = sorted(
            coherent_jobs, 
            key=lambda x: x['xi'], 
            reverse=True
        )[:10]
        results["FINDING"] = f"Found {len(coherent_jobs)} jobs with Ξ > 1 (coherent regime)"
    
    return results

def analyze_measurement_distribution(jobs: list) -> dict:
    """
    Look for non-random patterns in measurement outcomes.
    
    ΛΦ framework might predict specific correlations.
    """
    
    results = {
        "jobs_analyzed": 0,
        "all_zeros_excess": [],
        "all_ones_excess": [],
        "correlation_patterns": []
    }
    
    for job in jobs:
        counts = job.get('counts', {})
        if not counts:
            continue
        
        results["jobs_analyzed"] += 1
        total = sum(counts.values())
        
        if total == 0:
            continue
        
        # Check for excess of all-zeros or all-ones states
        num_bits = len(list(counts.keys())[0]) if counts else 0
        
        if num_bits > 0:
            all_zeros = '0' * num_bits
            all_ones = '1' * num_bits
            
            p_zeros = counts.get(all_zeros, 0) / total
            p_ones = counts.get(all_ones, 0) / total
            
            # Expected for maximally mixed state
            expected = 1 / (2 ** num_bits)
            
            if p_zeros > expected * 2:
                results["all_zeros_excess"].append({
                    "filename": job.get('filename'),
                    "p_zeros": p_zeros,
                    "expected": expected,
                    "ratio": p_zeros / expected
                })
            
            if p_ones > expected * 2:
                results["all_ones_excess"].append({
                    "filename": job.get('filename'),
                    "p_ones": p_ones,
                    "expected": expected,
                    "ratio": p_ones / expected
                })
    
    if results["all_zeros_excess"] or results["all_ones_excess"]:
        results["PATTERN_DETECTED"] = "Non-random measurement patterns found"
    
    return results


def main():
    print("=" * 80)
    print("DEEP PATTERN SEARCH")
    print("Looking for Nobel-worthy anomalies in 580 IBM Quantum jobs")
    print("=" * 80)
    
    # Load data
    results_path = "/home/dnalang/PUBLICATION/LAMBDA_PHI_PAPER/hardware_analysis_results.json"
    
    if not os.path.exists(results_path):
        print(f"ERROR: {results_path} not found")
        return
    
    data = load_hardware_results(results_path)
    jobs = data.get('job_details', [])
    
    print(f"\nLoaded {len(jobs)} job records")
    
    # Run all searches
    all_findings = {}
    
    print("\n" + "-" * 40)
    print("1. SEARCHING FOR TIME-CORRELATED PATTERNS...")
    print("-" * 40)
    time_results = search_for_time_patterns(jobs)
    all_findings["time_patterns"] = time_results
    print(f"Jobs with timing data: {time_results.get('jobs_with_timing', 0)}")
    if time_results.get('potential_peaks'):
        print("⚠️  POTENTIAL ANOMALY FOUND!")
        for peak in time_results['potential_peaks']:
            print(f"   {peak}")
    
    print("\n" + "-" * 40)
    print("2. SEARCHING FOR HIGH-FIDELITY OUTLIERS...")
    print("-" * 40)
    fidelity_results = find_high_fidelity_outliers(jobs)
    all_findings["fidelity_outliers"] = fidelity_results
    print(f"Max fidelity: {fidelity_results.get('max_fidelity', 0):.4f}")
    print(f"Gap to F_max bound: {fidelity_results.get('gap_to_bound', 0):.4f}")
    print(f"Outliers (>2σ): {fidelity_results.get('n_outliers', 0)}")
    if fidelity_results.get('ALERT'):
        print(f"⚠️  {fidelity_results['ALERT']}")
    
    print("\n" + "-" * 40)
    print("3. SEARCHING FOR Φ THRESHOLD TRANSITION...")
    print("-" * 40)
    phi_results = search_for_phi_transition(jobs)
    all_findings["phi_transition"] = phi_results
    print(f"Jobs below Φ threshold: {phi_results.get('n_below_threshold', 0)}")
    print(f"Jobs above Φ threshold: {phi_results.get('n_above_threshold', 0)}")
    if phi_results.get('POTENTIAL_FINDING'):
        print(f"⚠️  {phi_results['POTENTIAL_FINDING']}")
    if phi_results.get('CLUSTERING_DETECTED'):
        print(f"⚠️  {phi_results['CLUSTERING_DETECTED']}")
    
    print("\n" + "-" * 40)
    print("4. SEARCHING FOR CCCE COHERENT REGIME...")
    print("-" * 40)
    ccce_results = search_for_ccce_regime(jobs)
    all_findings["ccce_regime"] = ccce_results
    print(f"Mean Ξ: {ccce_results.get('mean_xi', 0):.4f}")
    print(f"Max Ξ: {ccce_results.get('max_xi', 0):.4f}")
    print(f"Jobs with Ξ > 1: {ccce_results.get('n_above_1', 0)}")
    if ccce_results.get('FINDING'):
        print(f"⚠️  {ccce_results['FINDING']}")
    
    print("\n" + "-" * 40)
    print("5. ANALYZING MEASUREMENT DISTRIBUTIONS...")
    print("-" * 40)
    dist_results = analyze_measurement_distribution(jobs)
    all_findings["measurement_patterns"] = dist_results
    print(f"Jobs analyzed: {dist_results.get('jobs_analyzed', 0)}")
    print(f"All-zeros excess: {len(dist_results.get('all_zeros_excess', []))}")
    print(f"All-ones excess: {len(dist_results.get('all_ones_excess', []))}")
    if dist_results.get('PATTERN_DETECTED'):
        print(f"⚠️  {dist_results['PATTERN_DETECTED']}")
    
    # Save detailed results
    output_path = "/home/dnalang/PUBLICATION/LAMBDA_PHI_PAPER/deep_pattern_search_results.json"
    with open(output_path, 'w') as f:
        json.dump(all_findings, f, indent=2, default=str)
    
    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)
    
    anomalies_found = []
    for category, results in all_findings.items():
        for key in results:
            if key.startswith(('POTENTIAL', 'FINDING', 'ALERT', 'CLUSTERING', 'PATTERN')):
                anomalies_found.append(f"{category}: {results[key]}")
    
    if anomalies_found:
        print("\n🔬 POTENTIAL ANOMALIES DETECTED:")
        for a in anomalies_found:
            print(f"   • {a}")
        print("\nThese warrant further investigation!")
    else:
        print("\n❌ No obvious anomalies found in existing data.")
        print("   The discriminating experiment on hardware is still needed.")
    
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
