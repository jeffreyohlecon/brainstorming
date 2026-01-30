#!/usr/bin/env python3
"""
Plot median transaction price for any ZIP3.
Use to check if high-RMSPE areas show tax-induced price jumps.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from load_chatgpt_data import load_with_zip3, log

OUT_DIR = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/exploratory')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Reference lines
BASE_PRICE = 20.00
FULL_PASSTHROUGH_9PCT = 21.80

# Top RMSPE ratio ZIP3s from placebo test
TOP_RMSPE_ZIP3S = {
    '100': 'Manhattan, NY',
    '223': 'Arlington/Alexandria, VA',
    '606': 'Chicago, IL',
    '189': 'New Brunswick, NJ',
    '286': 'Raleigh, NC',
    '200': 'Washington, DC',
}


def plot_median_price(trans, zip3, label, ax):
    """Plot median price for a single ZIP3."""
    subset = trans[trans['zip3'] == zip3].copy()
    if len(subset) == 0:
        print(f"  No data for ZIP3 {zip3}")
        return None

    subset['month'] = subset['trans_date'].dt.to_period('M')
    monthly = subset.groupby('month').agg(
        median=('trans_amount', 'median'),
        p25=('trans_amount', lambda x: x.quantile(0.25)),
        p75=('trans_amount', lambda x: x.quantile(0.75)),
        n=('trans_amount', 'count'),
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    ax.plot(monthly['month_dt'], monthly['median'],
            marker='o', linewidth=2, markersize=4)
    ax.fill_between(monthly['month_dt'], monthly['p25'], monthly['p75'],
                    alpha=0.2)

    return monthly


def main():
    log("Loading transaction data...")
    trans = load_with_zip3()
    trans = trans[trans['trans_date'] < '2025-12-01'].copy()

    # Create figure with subplots
    n_zip3s = len(TOP_RMSPE_ZIP3S)
    fig, axes = plt.subplots(3, 2, figsize=(14, 12), sharex=True, sharey=True)
    axes = axes.flatten()

    for i, (zip3, label) in enumerate(TOP_RMSPE_ZIP3S.items()):
        ax = axes[i]
        log(f"Plotting ZIP3 {zip3} ({label})...")

        monthly = plot_median_price(trans, zip3, label, ax)

        if monthly is not None:
            # Reference lines
            ax.axhline(BASE_PRICE, color='gray', linestyle='-',
                       alpha=0.5, linewidth=1)
            ax.axhline(FULL_PASSTHROUGH_9PCT, color='blue',
                       linestyle='--', alpha=0.5, linewidth=1)

            # Oct 2023 line (Chicago tax date)
            ax.axvline(pd.to_datetime('2023-10-01'), color='red',
                       linestyle=':', alpha=0.7)

        ax.set_title(f'{zip3}: {label}')
        ax.set_ylim(19, 24)
        ax.grid(True, alpha=0.3)

        if i >= 4:
            ax.set_xlabel('Month')
        if i % 2 == 0:
            ax.set_ylabel('Median Transaction ($)')

    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.tick_params(axis='x', rotation=45)

    fig.suptitle('Median Transaction Price: Top RMSPE Ratio ZIP3s\n'
                 '(Gray=$20 base, Blue=$21.80 full 9% pass-through, '
                 'Red=Oct 2023)', fontsize=11)
    plt.tight_layout()

    outpath = OUT_DIR / 'median_price_top_rmspe_zip3s.png'
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    log(f"Saved: {outpath}")
    plt.close()

    # Also create individual plots for each
    for zip3, label in TOP_RMSPE_ZIP3S.items():
        fig, ax = plt.subplots(figsize=(10, 6))
        monthly = plot_median_price(trans, zip3, label, ax)

        if monthly is not None:
            ax.axhline(BASE_PRICE, color='gray', linestyle='-',
                       alpha=0.5, label='$20 (no tax)')
            ax.axhline(FULL_PASSTHROUGH_9PCT, color='blue',
                       linestyle='--', alpha=0.7,
                       label='$21.80 (full 9% pass-through)')
            ax.axvline(pd.to_datetime('2023-10-01'), color='red',
                       linestyle=':', alpha=0.7, label='Oct 2023')

            ax.set_title(f'ZIP3 {zip3} ({label}): Median Transaction')
            ax.set_ylabel('Median Transaction ($)')
            ax.set_xlabel('Month')
            ax.set_ylim(19, 24)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.tick_params(axis='x', rotation=45)
            ax.legend(loc='upper left', fontsize=9)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(OUT_DIR / f'median_price_{zip3}.png',
                        dpi=150, bbox_inches='tight')
            plt.close()
            log(f"Saved: median_price_{zip3}.png")


if __name__ == "__main__":
    main()
