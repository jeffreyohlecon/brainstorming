#!/usr/bin/env python3
"""
Run all placebo robustness plots for a given threshold.

Usage: python run_placebo_plots.py [THRESHOLD_MULT]
Example: python run_placebo_plots.py 2   # 2x threshold
         python run_placebo_plots.py 5   # 5x threshold (default)

Generates:
  - placebo_histogram_{N}x.png
  - rmspe_vs_population_{N}x.png
  - rmspe_vs_pre_users_{N}x.png
  - gap_ratio_vs_pre_users_{N}x.png
  - placebo_spaghetti_{N}x.png
"""

import subprocess
import sys
from pathlib import Path

THRESHOLD = sys.argv[1] if len(sys.argv) > 1 else '5'

helpers_dir = Path(__file__).parent / 'helpers'

print(f"=== Running placebo plots with {THRESHOLD}x threshold ===\n")

# Run main robustness plots
print("Running plot_placebo_robustness.py...")
subprocess.run([sys.executable, helpers_dir / 'plot_placebo_robustness.py', THRESHOLD],
               check=True)

print("\nRunning plot_placebo_spaghetti.py...")
subprocess.run([sys.executable, helpers_dir / 'plot_placebo_spaghetti.py', THRESHOLD],
               check=True)

print(f"\n=== Done! All {THRESHOLD}x plots generated. ===")
