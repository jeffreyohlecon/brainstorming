#!/usr/bin/env python3
"""
Raw time series: Chicago vs control mean (log outcome).
Uses shared data loading from load_chatgpt_data.py.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from load_chatgpt_data import load_with_zip3, log, get_output_dir, get_filter_title, get_outcome_column

TREATED_ZIP = '606'
START_DATE = '2023-02-01'
END_DATE = '2024-12-01'  # Exclude ChatGPT Pro period
SIZE_WINDOW = 0.5

EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "9% PPLTT": "2023-10-01",
}


def main():
    trans = load_with_zip3()

    # Select size-matched controls
    log("Selecting size-matched controls...")
    early = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < '2023-07-01')]
    counts = early.groupby('zip3').size().reset_index(name='n_trans')

    chicago_size = counts[counts['zip3'] == TREATED_ZIP]['n_trans'].values[0]
    lower = chicago_size * (1 - SIZE_WINDOW)
    upper = chicago_size * (1 + SIZE_WINDOW)

    similar = counts[(counts['n_trans'] >= lower) & (counts['n_trans'] <= upper)]
    similar = similar[similar['zip3'] != TREATED_ZIP]
    similar = similar[similar['zip3'].str.match(r'^\d{3}$')]

    control_zips = similar['zip3'].tolist()
    log(f"Chicago size: {chicago_size}, Controls: {len(control_zips)}")

    # Filter to relevant ZIPs and date range
    all_zips = [TREATED_ZIP] + control_zips
    trans = trans[trans['zip3'].isin(all_zips)].copy()
    trans = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < END_DATE)].copy()
    trans['month'] = trans['trans_date'].dt.to_period('M')

    # Monthly aggregation
    outcome_col = get_outcome_column()
    monthly = trans.groupby(['zip3', 'month']).agg(
        n_transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum')
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()
    monthly['log_y'] = np.log(monthly[outcome_col])

    # Pivot for plotting
    pivot = monthly.pivot(index='month_dt', columns='zip3', values='log_y')
    pivot['control_mean'] = pivot[control_zips].mean(axis=1)

    # Plot
    log("Creating plot...")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(pivot.index, pivot[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606xx Zip codes)')
    ax.plot(pivot.index, pivot['control_mean'], marker='s', linewidth=2,
            color='gray', linestyle='--', label=f'Control mean ({len(control_zips)} ZIP3s)')

    # Shade treatment period
    ax.axvspan(pd.to_datetime('2023-10-01'), pivot.index.max(), alpha=0.15, color='red')

    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if pivot.index.min() <= event_dt <= pivot.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

    ax.set_xlabel('Month')
    ax.set_ylabel(f'Log({outcome_col})')
    ax.set_title(f'Raw Time Series: Chicago vs Control Mean {get_filter_title()}')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    note = f'Controls: {len(control_zips)} ZIP3s within 50% of Chicago size in Feb-Jun 2023'
    ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    out_dir = get_output_dir()
    plt.savefig(out_dir / "chicago_raw_counts.png", dpi=150, bbox_inches='tight')
    log(f"Saved: {out_dir / 'chicago_raw_counts.png'}")


if __name__ == "__main__":
    main()
