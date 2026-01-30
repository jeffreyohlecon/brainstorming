#!/usr/bin/env python3
"""
Detect potential tax-induced price changes across ZIP3s.

Compares median transaction prices between March 2023 (baseline)
and November 2024 (post-Chicago-tax). ZIP3s with 5%+ price
increases may have local taxes worth investigating.

Creates a funnel/ranked plot showing ZIP3s by price change.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import log
from load_data import load_with_zip3

# ZIP3 to area name mapping (extended for labeling)
ZIP3_NAMES = {
    '606': 'Chicago, IL',
    '337': 'St. Petersburg, FL',
    '100': 'Manhattan, NY',
    '112': 'Brooklyn, NY',
    '210': 'Baltimore, MD',
    '836': 'Brownsville, TX',
    '294': 'Charleston, SC',
    '803': 'Columbia, SC',
    '301': 'Atlanta, GA',
    '220': 'N. Virginia',
    '890': 'Las Vegas, NV',
    '923': 'San Bernardino, CA',
    '900': 'Los Angeles, CA',
    '277': 'Raleigh, NC',
    '303': 'Atlanta, GA',
    '943': 'Palo Alto, CA',
    '077': 'Long Branch, NJ',
}

OUT_DIR = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/exploratory')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Minimum transactions in each period to include ZIP3
MIN_TRANS_PER_PERIOD = 50

# Threshold for "interesting" price change
TAX_THRESHOLD_PCT = 5.0


def main():
    log("Loading transaction data with zip3...")
    trans = load_with_zip3()

    # Define periods
    mar_2023 = (trans['trans_date'] >= '2023-03-01') & \
               (trans['trans_date'] < '2023-04-01')
    nov_2024 = (trans['trans_date'] >= '2024-11-01') & \
               (trans['trans_date'] < '2024-12-01')

    log("Computing median prices by ZIP3...")

    # March 2023 medians
    mar = trans[mar_2023].groupby('zip3')['trans_amount'].agg(
        ['median', 'count']
    ).rename(columns={'median': 'med_mar23', 'count': 'n_mar23'})

    # November 2024 medians
    nov = trans[nov_2024].groupby('zip3')['trans_amount'].agg(
        ['median', 'count']
    ).rename(columns={'median': 'med_nov24', 'count': 'n_nov24'})

    # Merge
    df = mar.join(nov, how='inner')
    log(f"ZIP3s with data in both periods: {len(df)}")

    # Filter by minimum transactions
    df = df[(df['n_mar23'] >= MIN_TRANS_PER_PERIOD) &
            (df['n_nov24'] >= MIN_TRANS_PER_PERIOD)].copy()
    log(f"ZIP3s with >= {MIN_TRANS_PER_PERIOD} trans in each period: {len(df)}")

    # Compute percent change
    df['pct_change'] = 100 * (df['med_nov24'] - df['med_mar23']) / df['med_mar23']

    # Sort by percent change (descending)
    df = df.sort_values('pct_change', ascending=False).reset_index()

    # Print summary
    log("\n=== TOP 20 ZIP3s BY PRICE INCREASE ===")
    print(df.head(20).to_string(index=False))

    log("\n=== BOTTOM 20 ZIP3s (PRICE DECREASE) ===")
    print(df.tail(20).to_string(index=False))

    # Save full results
    csv_path = OUT_DIR / 'zip3_price_changes.csv'
    df.to_csv(csv_path, index=False)
    log(f"\nSaved: {csv_path}")

    # Create funnel plot
    log("\nCreating funnel plot...")
    create_funnel_plot(df)

    # Create focused plot for > 5% changes
    above_threshold = df[df['pct_change'] >= TAX_THRESHOLD_PCT]
    log(f"\nZIP3s with >= {TAX_THRESHOLD_PCT}% price increase: {len(above_threshold)}")
    if len(above_threshold) > 0:
        print(above_threshold.to_string(index=False))


def create_funnel_plot(df):
    """Create ranked bar chart of price changes."""
    fig, ax = plt.subplots(figsize=(12, 10))

    n = len(df)
    y_pos = np.arange(n)

    # Color by magnitude
    colors = []
    for pct in df['pct_change']:
        if pct >= TAX_THRESHOLD_PCT:
            colors.append('red')
        elif pct >= 2:
            colors.append('orange')
        elif pct <= -TAX_THRESHOLD_PCT:
            colors.append('blue')
        elif pct <= -2:
            colors.append('lightblue')
        else:
            colors.append('gray')

    bars = ax.barh(y_pos, df['pct_change'], color=colors, alpha=0.7)

    # Get top 3 and bottom 3 indices
    top3_idx = set(range(3))
    bot3_idx = set(range(n - 3, n))

    # Find Chicago's index
    chicago_idx = None
    for i, zip3 in enumerate(df['zip3']):
        if zip3 == '606':
            chicago_idx = i
            break

    # Indices to label
    label_idx = top3_idx | bot3_idx
    if chicago_idx is not None and chicago_idx not in label_idx:
        label_idx.add(chicago_idx)

    # Add labels with actual names for top 3, bottom 3, and Chicago
    for i, (zip3, pct) in enumerate(zip(df['zip3'], df['pct_change'])):
        if i in label_idx:
            name = ZIP3_NAMES.get(zip3, zip3)
            label_text = f"{zip3} ({name})"
            offset = 0.3 if pct > 0 else -0.3
            ax.text(pct + offset, i, label_text, va='center', fontsize=7,
                    ha='left' if pct > 0 else 'right')

    ax.axvline(0, color='black', linewidth=0.5)
    ax.axvline(TAX_THRESHOLD_PCT, color='red', linestyle='--',
               alpha=0.5, label=f'+{TAX_THRESHOLD_PCT}% threshold')
    ax.axvline(-TAX_THRESHOLD_PCT, color='blue', linestyle='--',
               alpha=0.5, label=f'-{TAX_THRESHOLD_PCT}% threshold')

    ax.set_xlabel('Price Change (%): March 2023 → November 2024')
    ax.set_ylabel(f'ZIP3 (ranked by change, n={n})')
    ax.set_title('Median Transaction Price Change by ZIP3\n'
                 'Red = potential tax increase, Blue = potential tax decrease')

    # Hide y ticks (too many)
    ax.set_yticks([])
    ax.legend(loc='upper right')
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    outpath = OUT_DIR / 'zip3_price_change_funnel.png'
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    log(f"Saved: {outpath}")
    plt.close()

    # Also create a more focused plot of just extremes
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))

    # Top 30 (biggest increases)
    top30 = df.head(30)
    y_top = np.arange(len(top30))
    colors_top = ['red' if p >= TAX_THRESHOLD_PCT else 'orange' if p >= 2
                  else 'gray' for p in top30['pct_change']]
    ax1.barh(y_top, top30['pct_change'], color=colors_top, alpha=0.7)
    ax1.set_yticks(y_top)
    ax1.set_yticklabels(top30['zip3'], fontsize=8)
    ax1.axvline(TAX_THRESHOLD_PCT, color='red', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Price Change (%)')
    ax1.set_title('Top 30: Largest Price Increases\n(potential tax additions)')
    ax1.invert_yaxis()
    ax1.grid(axis='x', alpha=0.3)

    # Bottom 30 (biggest decreases)
    bot30 = df.tail(30).iloc[::-1]  # Reverse for display
    y_bot = np.arange(len(bot30))
    colors_bot = ['blue' if p <= -TAX_THRESHOLD_PCT else 'lightblue' if p <= -2
                  else 'gray' for p in bot30['pct_change']]
    ax2.barh(y_bot, bot30['pct_change'], color=colors_bot, alpha=0.7)
    ax2.set_yticks(y_bot)
    ax2.set_yticklabels(bot30['zip3'], fontsize=8)
    ax2.axvline(-TAX_THRESHOLD_PCT, color='blue', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Price Change (%)')
    ax2.set_title('Bottom 30: Largest Price Decreases\n(potential tax removals or composition)')
    ax2.invert_yaxis()
    ax2.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    outpath = OUT_DIR / 'zip3_price_change_extremes.png'
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    log(f"Saved: {outpath}")
    plt.close()


if __name__ == "__main__":
    main()
