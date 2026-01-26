#!/usr/bin/env python3
"""
Pipeline to regenerate all Chicago PPLTT analysis figures.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "chicago_chatgpt_analysis.py",
    "chicago_did.py",
    "chicago_synth_control.py",
    "national_price_buckets.py",
]

# Inline script for raw counts comparison
RAW_COUNTS_SCRIPT = '''
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path('/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data')
OUTPUT_DIR = Path('/Users/jeffreyohl/Documents/GitHub/brainstorming')
TREATED_ZIP = '606'
SIZE_WINDOW = 0.5
END_DATE = '2025-12-01'

EVENTS = {
    'ChatGPT Plus': '2023-02-01',
    '9% PPLTT': '2023-10-01',
    '11% PPLTT': '2025-01-01',
}

dfs = []
for year in [2023, 2024, 2025]:
    f = DATA_DIR / f'chatgpt_transactions_{year}.parquet'
    if f.exists():
        dfs.append(pd.read_parquet(f))
trans = pd.concat(dfs, ignore_index=True)
trans = trans[trans['service'].str.lower().isin(['chatgpt', 'openai'])]

demo = pd.read_csv(DATA_DIR / 'chatgpt_demographics_2023_2024_2025.csv', low_memory=False)
trans = trans.merge(demo[['cardid', 'zip3']], on='cardid', how='left')
trans['zip3'] = trans['zip3'].astype(str)
trans['trans_date'] = pd.to_datetime(trans['trans_date'])
trans = trans[trans['trans_date'] < END_DATE].copy()

early = trans[(trans['trans_date'] >= '2023-01-01') & (trans['trans_date'] < '2023-07-01')]
counts = early.groupby('zip3').size().reset_index(name='n_trans')
chicago_size = counts[counts['zip3'] == TREATED_ZIP]['n_trans'].values[0]
lower, upper = chicago_size * (1 - SIZE_WINDOW), chicago_size * (1 + SIZE_WINDOW)
similar = counts[(counts['n_trans'] >= lower) & (counts['n_trans'] <= upper)]
similar = similar[(similar['zip3'] != TREATED_ZIP) & (similar['zip3'].str.match(r'^\\d{3}$'))]
control_zips = similar['zip3'].tolist()
print(f'Chicago size: {chicago_size}, Controls: {len(control_zips)}')

all_zips = [TREATED_ZIP] + control_zips
trans = trans[trans['zip3'].isin(all_zips)].copy()
trans['month'] = trans['trans_date'].dt.to_period('M')

monthly = trans.groupby(['zip3', 'month']).size().reset_index(name='n_trans')
monthly['month_dt'] = monthly['month'].dt.to_timestamp()
monthly['log_trans'] = np.log(monthly['n_trans'])

pivot = monthly.pivot(index='month_dt', columns='zip3', values='log_trans')
pivot['control_mean'] = pivot[control_zips].mean(axis=1)

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(pivot.index, pivot[TREATED_ZIP], marker='o', linewidth=2, color='blue', label='Chicago (606)')
ax.plot(pivot.index, pivot['control_mean'], marker='s', linewidth=2, color='gray', linestyle='--',
        label=f'Control mean ({len(control_zips)} ZIP3s)')

ax.axvspan(pd.to_datetime('2023-10-01'), pd.to_datetime('2025-01-01'), alpha=0.15, color='red')
ax.axvspan(pd.to_datetime('2025-01-01'), pivot.index.max(), alpha=0.30, color='red')

for event, date in EVENTS.items():
    event_dt = pd.to_datetime(date)
    if pivot.index.min() <= event_dt <= pivot.index.max():
        ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
        ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

ax.set_xlabel('Month')
ax.set_ylabel('Log(Transactions)')
ax.set_title('Raw Time Series: Chicago vs Control Mean (log transactions)')
ax.legend(loc='upper left')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.tick_params(axis='x', rotation=45)

note = f'Controls: {len(control_zips)} ZIP3s within 50% of Chicago size in Jan-Jun 2023'
ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=8,
        verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'chicago_raw_counts.png', dpi=150, bbox_inches='tight')
print('Saved: chicago_raw_counts.png')
'''


def main():
    script_dir = Path(__file__).parent

    print("="*60)
    print("REGENERATING ALL FIGURES")
    print("="*60)

    for script in SCRIPTS:
        print(f"\n>>> Running {script}...")
        result = subprocess.run(
            [sys.executable, script_dir / script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR in {script}:")
            print(result.stderr)
        else:
            # Print last few lines of output
            lines = result.stdout.strip().split('\n')
            for line in lines[-5:]:
                print(f"  {line}")

    print(f"\n>>> Running raw counts script...")
    result = subprocess.run(
        [sys.executable, "-c", RAW_COUNTS_SCRIPT],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR in raw counts:")
        print(result.stderr)
    else:
        print(f"  {result.stdout.strip()}")

    print("\n" + "="*60)
    print("DONE")
    print("="*60)


if __name__ == "__main__":
    main()
