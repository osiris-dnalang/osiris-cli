#!/usr/bin/env python3
"""
OSIRIS-NCLM Figure 5: Strategy Usage Frequency
================================================
co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM

Generates bar chart of strategy usage during inference.
Replace simulated data with actual inference logs for publication.

Usage:
    python figures/generate_strategy_usage.py
"""

import os
import matplotlib.pyplot as plt

# Simulated strategy usage (replace with your actual data)
strategies = ["Decompose", "Verify", "Optimize", "Self-Reflect"]
counts = [1200, 850, 620, 480]
colors = ['#2ca02c', '#d62728', '#9467bd', '#8c564b']

plt.figure(figsize=(10, 5))
bars = plt.bar(strategies, counts, color=colors, edgecolor='black', linewidth=0.8)

for bar, count in zip(bars, counts):
    plt.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 20,
             str(count), ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.xlabel("Strategy Type", fontsize=12)
plt.ylabel("Usage Count", fontsize=12)
plt.title("Strategy Usage Frequency During Inference", fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3, axis='y')
plt.tight_layout()

os.makedirs("figures", exist_ok=True)
plt.savefig("figures/strategy_usage.png", dpi=300, bbox_inches='tight')
print("[OSIRIS-NCLM] Figure 5 saved: figures/strategy_usage.png")
