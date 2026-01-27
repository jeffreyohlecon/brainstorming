#!/usr/bin/env python3
"""
Time series analysis of ChatGPT/AI subscription transactions from Consumer Edge.

NOTE: Current data does NOT include merchid - only the matched keyword (chatgpt, openai, etc).
To analyze by exact merchant description, need to re-run extraction with updated script
that includes merchid in output, then join with merchants file.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

# Data location
DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
CACHE_FILE = DATA_DIR / "chatgpt_combined_2023_2025.parquet"

# Key dates
EVENTS = {
    "ChatGPT Plus Launch": "2023-02-01",
    "GPT-4 Launch": "2023-03-14",
    "Claude Pro Launch": "2023-09-07",
    "Claude 3 Launch": "2024-03-04",
}

# Only include transactions matching these terms
INCLUDE_TERMS = ['chatgpt', 'openai']


def log(msg):
    """Print with timestamp."""
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_transactions(use_cache=True):
    """Load and combine all transaction parquets, with caching."""

    # Try cache first
    if use_cache and CACHE_FILE.exists():
        log(f"Loading from cache: {CACHE_FILE.name}")
        df = pd.read_parquet(CACHE_FILE)
        log(f"Loaded {len(df):,} rows from cache")
        return df

    # Load from individual files
    files = [
        DATA_DIR / "chatgpt_transactions_2023.parquet",
        DATA_DIR / "chatgpt_transactions_2024.parquet",
        DATA_DIR / "chatgpt_transactions_2025.parquet",
    ]

    dfs = []
    for f in files:
        if f.exists():
            log(f"Loading {f.name}...")
            df = pd.read_parquet(f)
            log(f"  -> {len(df):,} rows")
            dfs.append(df)
        else:
            log(f"Missing: {f.name}")

    if not dfs:
        raise FileNotFoundError("No transaction files found")

    log("Combining dataframes...")
    combined = pd.concat(dfs, ignore_index=True)

    # Save cache
    log(f"Saving cache: {CACHE_FILE.name}")
    combined.to_parquet(CACHE_FILE)
    log("Cache saved")

    return combined


def main():
    # Load data
    log("Starting analysis...")
    trans = load_transactions()

    log(f"Total transactions: {len(trans):,}")
    log(f"Columns: {list(trans.columns)}")

    # Find the match column
    match_col = [c for c in trans.columns if c not in ['cardid', 'trans_date', 'trans_amount']]
    if match_col:
        match_col = match_col[0]
        log(f"By {match_col} (before filtering):")
        print(trans[match_col].value_counts())

        # Filter to only chatgpt/openai
        log(f"Filtering to {INCLUDE_TERMS}...")
        trans = trans[trans[match_col].str.lower().isin(INCLUDE_TERMS)]
        log(f"After filtering: {len(trans):,} transactions")
        print(trans[match_col].value_counts())

    log(f"Date range: {trans['trans_date'].min()} to {trans['trans_date'].max()}")

    # Convert date
    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['month'] = trans['trans_date'].dt.to_period('M')

    # Ensure trans_amount is numeric
    trans['trans_amount'] = pd.to_numeric(trans['trans_amount'], errors='coerce')

    # Monthly aggregation
    log("Computing monthly aggregations...")
    monthly = trans.groupby('month').agg(
        transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        unique_users=('cardid', 'nunique'),
        median_transaction=('trans_amount', 'median'),
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    print("\n" + "="*60)
    print("MONTHLY SUMMARY")
    print("="*60)
    print(monthly.to_string())

    # Data bounds for axis limits
    date_min = monthly['month_dt'].min()
    date_max = monthly['month_dt'].max()

    # Plot
    log("Creating plots...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Transaction count
    ax = axes[0, 0]
    ax.plot(monthly['month_dt'], monthly['transactions'], marker='o', linewidth=2)
    ax.set_ylabel('Transaction Count')
    ax.set_title('Monthly Transactions')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=8)

    # Plot 2: Total spend
    ax = axes[0, 1]
    ax.plot(monthly['month_dt'], monthly['total_spend'] / 1e6, marker='o', linewidth=2, color='green')
    ax.set_ylabel('Total Spend ($M)')
    ax.set_title('Monthly Total Spend')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)

    # Plot 3: Unique users
    ax = axes[1, 0]
    ax.plot(monthly['month_dt'], monthly['unique_users'], marker='o', linewidth=2, color='purple')
    ax.set_ylabel('Unique Users')
    ax.set_title('Monthly Unique Users')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)

    # Plot 4: Median transaction
    ax = axes[1, 1]
    ax.plot(monthly['month_dt'], monthly['median_transaction'], marker='o', linewidth=2, color='orange')
    ax.axhline(20, color='gray', linestyle='-', alpha=0.8, label='$20 subscription price')
    ax.set_ylabel('Median Transaction ($)')
    ax.set_title('Median Transaction Amount')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper right')
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)

    plt.tight_layout()

    output_path = Path(__file__).parent / "chatgpt_timeseries.png"
    log(f"Saving plot to {output_path}...")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    log("Done!")


if __name__ == "__main__":
    main()
