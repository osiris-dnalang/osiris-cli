#!/usr/bin/env python3
"""
OSIRIS-NCLM Figure 3: Distillation Training Curve
==================================================
co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM

Generates training curve showing reward vs. iteration during distillation.
Replace simulated data with actual training logs for publication.

Usage:
    python figures/generate_training_curve.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# Simulated rewards (replace with your actual data from training logs)
rewards = np.array([0.12, 0.18, 0.22, 0.27, 0.31, 0.34, 0.36, 0.38, 0.40, 0.41])

plt.figure(figsize=(10, 5))
plt.plot(rewards, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=8)
plt.xlabel("Training Iteration", fontsize=12)
plt.ylabel("Average Reward", fontsize=12)
plt.title("Distillation Training Curve: Reward vs. Iteration", fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.tight_layout()

os.makedirs("figures", exist_ok=True)
plt.savefig("figures/training_curve.png", dpi=300, bbox_inches='tight')
print("[OSIRIS-NCLM] Figure 3 saved: figures/training_curve.png")
