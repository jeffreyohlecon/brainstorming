#!/usr/bin/env python3
"""Plot transactions vs unique users time series for Chicago (zip3 606)."""

import sys
sys.path.insert(0, '/Users/jeffreyohl/Documents/GitHub/brainstorming')
from config import get_output_dir
from load_data import load_with_zip3
import matplotlib.pyplot as plt
import pandas as pd

# Load data
trans = load_with_zip3()

# Filter to Chicago
chicago = trans[trans['zip3'] == '606'].copy()
chicago['month'] = chicago['trans_date'].dt.to_period('M')

# Aggregate by month
monthly = chicago.groupby('month').agg(
    n_transactions=('cardid', 'count'),
    n_users=('cardid', 'nunique')
).reset_index()
monthly['month'] = monthly['month'].dt.to_timestamp()

# Plot
fig, ax1 = plt.subplots(figsize=(10, 6))

color1 = 'tab:blue'
ax1.set_xlabel('Month')
ax1.set_ylabel('Transactions', color=color1)
ax1.plot(monthly['month'], monthly['n_transactions'],
         color=color1, marker='o', label='Transactions')
ax1.tick_params(axis='y', labelcolor=color1)

ax2 = ax1.twinx()
color2 = 'tab:orange'
ax2.set_ylabel('Unique Users', color=color2)
ax2.plot(monthly['month'], monthly['n_users'],
         color=color2, marker='s', label='Unique Users')
ax2.tick_params(axis='y', labelcolor=color2)

# Treatment line
ax1.axvline(pd.Timestamp('2023-10-01'), color='red',
            linestyle='--', alpha=0.7, label='PPLTT (Oct 2023)')

plt.title('Chicago (ZIP3 606): Transactions vs Unique Users\n'
          '($15-25 filter, constant panel)')

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.tight_layout()

# Save
out_dir = get_output_dir() / 'exploratory'
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / 'chicago_trans_vs_users.png'
plt.savefig(out_path, dpi=150)
print(f"Saved: {out_path}")

# Print summary stats
print(f"\nChicago monthly summary:")
print(f"  Avg transactions/month: {monthly['n_transactions'].mean():.0f}")
print(f"  Avg users/month: {monthly['n_users'].mean():.0f}")
print(f"  Avg trans per user: {monthly['n_transactions'].sum() / monthly['n_users'].sum():.2f}")
