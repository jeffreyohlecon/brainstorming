#!/usr/bin/env python3
"""
National time series showing % of ChatGPT transactions by price bucket.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
OUTPUT_DIR = Path(__file__).parent

EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "ChatGPT Pro": "2024-12-05",
}


def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("Loading transactions...")
    dfs = []
    for year in [2023, 2024, 2025]:
        f = DATA_DIR / f"chatgpt_transactions_{year}.parquet"
        if f.exists():
            dfs.append(pd.read_parquet(f))
    trans = pd.concat(dfs, ignore_index=True)
    log(f"Total transactions: {len(trans):,}")

    # Filter to ChatGPT/OpenAI only
    trans = trans[trans['service'].str.lower().isin(['chatgpt', 'openai'])]
    log(f"ChatGPT/OpenAI: {len(trans):,}")

    # Prep data
    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['trans_amount'] = pd.to_numeric(trans['trans_amount'], errors='coerce')
    trans['month'] = trans['trans_date'].dt.to_period('M')

    # Define price buckets
    def bucket(amt):
        if pd.isna(amt):
            return 'Other'
        elif 20 <= amt <= 25:
            return '$20-25 (Plus)'
        elif 200 <= amt <= 250:
            return '$200-250 (Pro)'
        else:
            return 'Other'

    trans['bucket'] = trans['trans_amount'].apply(bucket)

    # Monthly counts by bucket
    monthly = trans.groupby(['month', 'bucket']).size().unstack(fill_value=0)
    monthly['total'] = monthly.sum(axis=1)

    # Compute percentages
    for col in ['$20-25 (Plus)', '$200-250 (Pro)', 'Other']:
        if col in monthly.columns:
            monthly[f'{col} %'] = monthly[col] / monthly['total'] * 100

    monthly = monthly.reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    print("\nMonthly breakdown:")
    print(monthly[['month', '$20-25 (Plus)', '$200-250 (Pro)', 'Other', 'total']].tail(12).to_string())

    # Stacked area plot
    log("Creating plot...")
    fig, ax = plt.subplots(figsize=(12, 6))

    cols = ['$20-25 (Plus) %', '$200-250 (Pro) %', 'Other %']
    colors = ['#2ecc71', '#e74c3c', '#95a5a6']
    labels = ['$20-25 (Plus)', '$200-250 (Pro)', 'Other']

    # Filter to columns that exist
    existing_cols = [c for c in cols if c in monthly.columns]
    existing_colors = [colors[cols.index(c)] for c in existing_cols]
    existing_labels = [labels[cols.index(c)] for c in existing_cols]

    ax.stackplot(monthly['month_dt'],
                 [monthly[c] for c in existing_cols],
                 labels=existing_labels,
                 colors=existing_colors,
                 alpha=0.8)

    # Event lines
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if monthly['month_dt'].min() <= event_dt <= monthly['month_dt'].max():
            ax.axvline(event_dt, color='black', linestyle='--', alpha=0.7)
            ax.text(event_dt, 95, event, rotation=90, va='top', fontsize=9)

    ax.set_xlabel('Month')
    ax.set_ylabel('% of Transactions')
    ax.set_title('National ChatGPT Transactions by Price Bucket')
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "national_price_buckets.png", dpi=150, bbox_inches='tight')
    log("Saved: national_price_buckets.png")

    # Print summary stats
    print("\n" + "="*60)
    print("SUMMARY BY PERIOD")
    print("="*60)

    periods = [
        ("Pre-Pro (before Dec 2024)", monthly['month_dt'] < '2024-12-01'),
        ("Post-Pro (Dec 2024+)", monthly['month_dt'] >= '2024-12-01'),
    ]

    for name, mask in periods:
        subset = monthly[mask]
        if len(subset) > 0:
            print(f"\n{name}:")
            for col in existing_cols:
                print(f"  {col}: {subset[col].mean():.1f}%")


if __name__ == "__main__":
    main()
