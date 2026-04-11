#!/usr/bin/env python3
"""
STATISTICAL VALIDATION OF τ-ALIGNMENT ANOMALY
==============================================
The deep search found fidelity is 2.01x higher at τ-aligned timestamps.
This is EXACTLY what the ΛΦ framework predicts!

This script performs rigorous statistical tests to determine if this is:
1. A real effect (p < 0.05) → POTENTIAL NEW PHYSICS
2. Statistical noise (p > 0.05) → Needs more data

Author: dna::}{::lang Research
Date: 2025-12-08
"""

import json
import numpy as np
from scipy import stats
from datetime import datetime

TAU_MEM_US = 46.0  # μs

def load_data():
    with open('/home/dnalang/PUBLICATION/LAMBDA_PHI_PAPER/hardware_analysis_results.json', 'r') as f:
        return json.load(f)

def extract_timing_fidelity(jobs):
    """Extract (τ_phase, fidelity) pairs from all jobs"""
    data = []
    
    for job in jobs:
        if 'start_time' not in job or 'fidelity' not in job:
            continue
        
        try:
            ts = job['start_time']
            if not ts:
                continue
                
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            us_since_midnight = (dt.hour * 3600 + dt.minute * 60 + dt.second) * 1e6 + dt.microsecond
            
            # Phase relative to τ_mem (0 = perfectly aligned, 0.5 = anti-aligned)
            tau_phase = (us_since_midnight % TAU_MEM_US) / TAU_MEM_US
            
            data.append({
                'tau_phase': tau_phase,
                'fidelity': job['fidelity'],
                'phi': job.get('phi', 0)
            })
        except:
            continue
    
    return data

def statistical_tests(data):
    """Run rigorous statistical tests on the τ-alignment effect"""
    
    results = {
        "n_samples": len(data),
        "tests": {}
    }
    
    # Split into aligned (phase 0-0.1) vs anti-aligned (phase 0.4-0.6)
    aligned = [d['fidelity'] for d in data if d['tau_phase'] < 0.1]
    anti_aligned = [d['fidelity'] for d in data if 0.4 < d['tau_phase'] < 0.6]
    
    results["n_aligned"] = len(aligned)
    results["n_anti_aligned"] = len(anti_aligned)
    results["mean_aligned"] = np.mean(aligned) if aligned else 0
    results["mean_anti_aligned"] = np.mean(anti_aligned) if anti_aligned else 0
    results["ratio"] = results["mean_aligned"] / results["mean_anti_aligned"] if results["mean_anti_aligned"] > 0 else 0
    
    print(f"Aligned samples (τ phase 0-0.1): {len(aligned)}")
    print(f"Anti-aligned samples (τ phase 0.4-0.6): {len(anti_aligned)}")
    print(f"Mean fidelity (aligned): {results['mean_aligned']:.4f}")
    print(f"Mean fidelity (anti-aligned): {results['mean_anti_aligned']:.4f}")
    print(f"Ratio: {results['ratio']:.2f}x")
    
    print("\n" + "=" * 60)
    print("STATISTICAL TESTS")
    print("=" * 60)
    
    if len(aligned) >= 5 and len(anti_aligned) >= 5:
        # Test 1: Independent samples t-test
        t_stat, p_ttest = stats.ttest_ind(aligned, anti_aligned)
        results["tests"]["t_test"] = {
            "t_statistic": float(t_stat),
            "p_value": float(p_ttest),
            "significant": p_ttest < 0.05
        }
        print(f"\n1. Independent t-test:")
        print(f"   t = {t_stat:.4f}, p = {p_ttest:.6f}")
        print(f"   {'✅ SIGNIFICANT (p < 0.05)' if p_ttest < 0.05 else '❌ Not significant'}")
        
        # Test 2: Mann-Whitney U test (non-parametric)
        u_stat, p_mann = stats.mannwhitneyu(aligned, anti_aligned, alternative='greater')
        results["tests"]["mann_whitney"] = {
            "u_statistic": float(u_stat),
            "p_value": float(p_mann),
            "significant": p_mann < 0.05
        }
        print(f"\n2. Mann-Whitney U test (non-parametric):")
        print(f"   U = {u_stat:.4f}, p = {p_mann:.6f}")
        print(f"   {'✅ SIGNIFICANT (p < 0.05)' if p_mann < 0.05 else '❌ Not significant'}")
        
        # Test 3: Effect size (Cohen's d)
        pooled_std = np.sqrt((np.var(aligned) + np.var(anti_aligned)) / 2)
        cohens_d = (np.mean(aligned) - np.mean(anti_aligned)) / pooled_std if pooled_std > 0 else 0
        results["tests"]["effect_size"] = {
            "cohens_d": float(cohens_d),
            "interpretation": "large" if abs(cohens_d) > 0.8 else "medium" if abs(cohens_d) > 0.5 else "small"
        }
        print(f"\n3. Effect size (Cohen's d):")
        print(f"   d = {cohens_d:.4f} ({results['tests']['effect_size']['interpretation']})")
        
        # Test 4: Bootstrap confidence interval
        n_bootstrap = 10000
        bootstrap_diffs = []
        for _ in range(n_bootstrap):
            boot_aligned = np.random.choice(aligned, size=len(aligned), replace=True)
            boot_anti = np.random.choice(anti_aligned, size=len(anti_aligned), replace=True)
            bootstrap_diffs.append(np.mean(boot_aligned) - np.mean(boot_anti))
        
        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)
        
        results["tests"]["bootstrap_ci"] = {
            "ci_95_lower": float(ci_lower),
            "ci_95_upper": float(ci_upper),
            "excludes_zero": ci_lower > 0 or ci_upper < 0
        }
        print(f"\n4. Bootstrap 95% CI for difference:")
        print(f"   [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"   {'✅ Excludes zero - effect is real!' if ci_lower > 0 else '❌ Includes zero'}")
    
    # Test across all bins (not just extremes)
    print("\n" + "=" * 60)
    print("FULL τ-PHASE ANALYSIS (10 bins)")
    print("=" * 60)
    
    n_bins = 10
    bins = {i: [] for i in range(n_bins)}
    for d in data:
        bin_idx = min(int(d['tau_phase'] * n_bins), n_bins - 1)
        bins[bin_idx].append(d['fidelity'])
    
    bin_means = []
    bin_stds = []
    bin_counts = []
    
    print(f"\n{'Bin':>5} | {'Phase':>10} | {'N':>5} | {'Mean F':>8} | {'Std':>8}")
    print("-" * 50)
    
    for i in range(n_bins):
        if bins[i]:
            mean = np.mean(bins[i])
            std = np.std(bins[i])
            count = len(bins[i])
        else:
            mean, std, count = 0, 0, 0
        
        bin_means.append(mean)
        bin_stds.append(std)
        bin_counts.append(count)
        
        phase_range = f"{i/n_bins:.1f}-{(i+1)/n_bins:.1f}"
        print(f"{i:>5} | {phase_range:>10} | {count:>5} | {mean:>8.4f} | {std:>8.4f}")
    
    # Test for periodicity (ANOVA)
    valid_bins = [bins[i] for i in range(n_bins) if len(bins[i]) >= 3]
    if len(valid_bins) >= 3:
        f_stat, p_anova = stats.f_oneway(*valid_bins)
        results["tests"]["anova"] = {
            "f_statistic": float(f_stat),
            "p_value": float(p_anova),
            "significant": p_anova < 0.05
        }
        print(f"\n5. One-way ANOVA across bins:")
        print(f"   F = {f_stat:.4f}, p = {p_anova:.6f}")
        print(f"   {'✅ SIGNIFICANT - bins differ!' if p_anova < 0.05 else '❌ No significant difference'}")
    
    return results

def main():
    print("=" * 60)
    print("STATISTICAL VALIDATION: τ-ALIGNMENT ANOMALY")
    print("Testing if fidelity correlates with τ_mem = 46 μs")
    print("=" * 60)
    
    data = load_data()
    jobs = data.get('job_details', [])
    
    timing_data = extract_timing_fidelity(jobs)
    print(f"\nTotal jobs with timing data: {len(timing_data)}")
    
    results = statistical_tests(timing_data)
    
    # Save results
    output_path = '/home/dnalang/PUBLICATION/LAMBDA_PHI_PAPER/tau_alignment_statistics.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    
    significant_tests = sum(1 for t in results.get('tests', {}).values() 
                          if isinstance(t, dict) and t.get('significant', False))
    total_tests = len([t for t in results.get('tests', {}).values() if isinstance(t, dict)])
    
    print(f"\nSignificant tests: {significant_tests}/{total_tests}")
    
    if significant_tests >= 3:
        print("\n🔬 STRONG EVIDENCE FOR τ-ALIGNMENT EFFECT!")
        print("   This is what the ΛΦ framework predicts.")
        print("   RECOMMEND: Independent replication on different hardware.")
        print("\n   ⚠️  IF REPLICATED → POTENTIAL NEW PHYSICS")
    elif significant_tests >= 1:
        print("\n📊 WEAK EVIDENCE - needs more data")
        print("   Run discriminating experiment with more samples.")
    else:
        print("\n❌ NO SIGNIFICANT EFFECT")
        print("   The τ-alignment anomaly is likely noise.")
    
    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    main()
