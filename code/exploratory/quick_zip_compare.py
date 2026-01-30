#!/usr/bin/env python3
"""Quick DiD plot comparing any two zip3s.

Usage: python quick_zip_compare.py ZIP1 ZIP2
Example: python quick_zip_compare.py 606 077
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: python quick_zip_compare.py ZIP1 ZIP2")
    print("Example: python quick_zip_compare.py 606 077")
    sys.exit(1)

zip1, zip2 = sys.argv[1], sys.argv[2]

# Paths
ROOT = Path(__file__).parent.parent.parent
DATA = ROOT / 'data' / 'synth_panel.dta'
OUT = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/exploratory')
OUT.mkdir(parents=True, exist_ok=True)

# Load data
df = pd.read_stata(DATA)

# Filter
d1 = df[df['zip3'] == zip1].sort_values('month_num').reset_index()
d2 = df[df['zip3'] == zip2].sort_values('month_num').reset_index()

print(f"{zip1}: {len(d1)} months")
print(f"{zip2}: {len(d2)} months")

if len(d1) == 0 or len(d2) == 0:
    print("ERROR: One or both zips not found in data")
    sys.exit(1)

# Compute difference
merged = d1[['month_num', 'log_users']].merge(
    d2[['month_num', 'log_users']],
    on='month_num', suffixes=('_1', '_2'))
merged['diff'] = merged['log_users_1'] - merged['log_users_2']

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Panel 1: Levels
ax1.plot(d1['month_num'], d1['log_users'],
         'b-o', label=zip1, linewidth=2, markersize=5)
ax1.plot(d2['month_num'], d2['log_users'],
         'r-o', label=zip2, linewidth=2, markersize=5)
ax1.axvline(x=10, color='black', linestyle='--', alpha=0.7,
            label='Chicago tax (Oct 2023)')
ax1.set_ylabel('Log unique users')
ax1.set_title(f'{zip1} vs {zip2}')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Panel 2: Difference
ax2.plot(merged['month_num'], merged['diff'],
         'g-o', linewidth=2, markersize=5)
ax2.axvline(x=10, color='black', linestyle='--', alpha=0.7)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax2.set_xlabel('Month (3=Mar 2023, 10=Oct 2023, 23=Nov 2024)')
ax2.set_ylabel(f'Difference ({zip1} - {zip2})')
ax2.set_title(f'{zip1} minus {zip2}')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
outfile = OUT / f'quick_{zip1}_vs_{zip2}.png'
plt.savefig(outfile, dpi=150)
print(f"Saved to {outfile}")
plt.show()
