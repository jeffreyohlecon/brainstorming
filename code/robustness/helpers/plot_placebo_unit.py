#!/usr/bin/env python3
"""Plot synthetic control for a single placebo unit.

Usage: python plot_placebo_unit.py ZIP3
Example: python plot_placebo_unit.py 077
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python plot_placebo_unit.py ZIP3")
    print("Example: python plot_placebo_unit.py 077")
    sys.exit(1)

zip3_input = sys.argv[1]
# Handle '077' -> 77
zip3_id = int(zip3_input.lstrip('0')) if zip3_input.lstrip('0') else 0

# Paths
DATA_DIR = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/'
                'unique_users/15to25/all_merchants')
OUT_DIR = DATA_DIR / 'synthetic_placebo_robustness' / 'placebo_sc_plots'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load placebo series
df = pd.read_stata(DATA_DIR / 'placebo_series_long.dta')

# Filter to requested unit
unit = df[df['zip3_id'] == zip3_id].sort_values('month_num')

if len(unit) == 0:
    print(f"ERROR: zip3 {zip3_input} (id={zip3_id}) not in placebo data")
    avail = sorted(df['zip3_id'].unique())[:30]
    print(f"Available (first 30): {avail}")
    sys.exit(1)

print(f"Plotting placebo synth for zip3 {zip3_input} ({len(unit)} months)")

# Plot (mimic Stata style)
fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(unit['month_num'], unit['y_treated'],
        'k-', linewidth=1.5, label='treated unit')
ax.plot(unit['month_num'], unit['y_synthetic'],
        'k--', linewidth=1.5, label='synthetic control unit')

# Treatment line
ax.axvline(x=10, color='black', linestyle=':', alpha=0.7)

ax.set_xlabel('month_num')
ax.set_ylabel('log_users')
ax.legend(loc='upper left', frameon=False)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
outfile = OUT_DIR / f'placebo_zip3_{zip3_input}.png'
plt.savefig(outfile, dpi=150)
print(f"Saved: {outfile}")
plt.show()
