#!/usr/bin/env python3
"""
Plot synth results with both treatment line (Oct 2023) and o1 release line (Sep 2024).
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import get_output_dir

# Output directory from settings
outdir = get_output_dir()

# Load synth results
synth = pd.read_stata(outdir / 'synth_results.dta')

# Convert _time (month_num) to date
# month_num 3 = Mar 2023, 10 = Oct 2023, 21 = Sep 2024
synth['date'] = pd.to_datetime('2023-01-01') + pd.to_timedelta(
    (synth['_time'] - 1) * 30.44, unit='D'
)

# Plot
fig, ax = plt.subplots(figsize=(12, 7))

ax.plot(synth['date'], synth['_Y_treated'], 'r-', linewidth=2, label='Chicago (606)')
ax.plot(synth['date'], synth['_Y_synthetic'], 'b--', linewidth=2, label='Synthetic')

# GPT-4 release (Mar 2023)
gpt4_date = pd.Timestamp('2023-03-14')
ax.axvline(gpt4_date, color='green', linestyle=':', linewidth=1.5, label='GPT-4 (Mar 2023)')

# Treatment line (Oct 2023)
tax_date = pd.Timestamp('2023-10-01')
ax.axvline(tax_date, color='black', linestyle='--', linewidth=1.5, label='Tax (Oct 2023)')

# o1 release line (Sep 2024)
o1_date = pd.Timestamp('2024-09-01')
ax.axvline(o1_date, color='red', linestyle=':', linewidth=1.5, label='o1 (Sep 2024)')

# Format
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')

ax.set_ylabel('Log(Unique Users)')
ax.set_title('Chicago vs Synthetic Control')
ax.legend(loc='upper left')

plt.tight_layout()

# Save
out_path = outdir / 'chicago_synth_with_o1.png'
plt.savefig(out_path, dpi=150)
print(f"Saved: {out_path}")

plt.close()
