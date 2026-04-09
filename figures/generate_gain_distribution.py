#!/usr/bin/env python3
"""
OSIRIS-NCLM Figure 4: Refinement Gain Distribution
====================================================
co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM

Generates histogram of refinement gains across tasks.
Replace simulated data with actual refinement logs for publication.

Usage:
    python figures/generate_gain_distribution.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# Simulated gains (replace with your actual data)
rng = np.random.default_rng(42)
gains = rng.normal(0.15, 0.05, 1000)
gains = np.clip(gains, 0, 1)

plt.figure(figsize=(10, 5))
plt.hist(gains, bins=30, color='#ff7f0e', edgecolor='black', alpha=0.7)
plt.xlabel("Refinement Gain", fontsize=12)
plt.ylabel("Frequency", fontsize=12)
plt.title("Distribution of Refinement Gains Across Tasks", fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)

pct_positive = np.mean(gains > 0) * 100
mean_gain = np.mean(gains)
plt.axvline(mean_gain, color='red', linestyle='--', linewidth=2, label=f'Mean = {mean_gain:.3f}')
plt.legend(fontsize=11)
plt.tight_layout()

os.makedirs("figures", exist_ok=True)
plt.savefig("figures/gain_distribution.png", dpi=300, bbox_inches='tight')
print(f"[OSIRIS-NCLM] Figure 4 saved: figures/gain_distribution.png")
print(f"  {pct_positive:.0f}% of tasks show positive improvement, mean gain = {mean_gain:.3f}")
