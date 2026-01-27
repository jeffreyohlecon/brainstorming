#!/usr/bin/env python3
"""
Time series analysis of AI subscription transactions from Consumer Edge.
Handles ChatGPT/OpenAI and Claude/Anthropic separately.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
OUTPUT_DIR = Path(__file__).parent

# Define analysis groups
ANALYSIS_GROUPS = {
    'chatgpt': {
        'terms': ['chatgpt', 'openai'],
        'title': 'ChatGPT/OpenAI',
        'events': {
            "ChatGPT Plus Launch": "2023-02-01",
            "GPT-4 Launch": "2023-03-14",
            "GPT-4o Launch": "2024-05-13",
        },
        'subscription_price': 20,
    },
    'claude': {
        'terms': ['anthropic'],  # claude.ai appears contaminated
        'title': 'Claude/Anthropic',
        'events': {
            "Claude Pro Launch": "2023-09-07",
            "Claude 3 Launch": "2024-03-04",
            "Claude 3.5 Sonnet": "2024-06-20",
        },
        'subscription_price': 20,
    },
}


def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_transactions():
    """Load all transaction parquets."""
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

    if not dfs:
        raise FileNotFoundError("No transaction files found")

    return pd.concat(dfs, ignore_index=True)


def analyze_group(trans, group_name, config):
    """Run time series analysis for a group of match terms."""
    log(f"\n{'='*60}")
    log(f"Analyzing: {config['title']}")
    log(f"{'='*60}")

    # Find match column
    match_col = [c for c in trans.columns if c not in ['cardid', 'trans_date', 'trans_amount']][0]

    # Filter to this group's terms
    mask = trans[match_col].str.lower().isin(config['terms'])
    df = trans[mask].copy()

    log(f"Transactions: {len(df):,}")
    if len(df) == 0:
        log("No data for this group")
        return None

    # Show breakdown
    print(df[match_col].value_counts())

    # Convert and aggregate
    df['trans_date'] = pd.to_datetime(df['trans_date'])
    df['trans_amount'] = pd.to_numeric(df['trans_amount'], errors='coerce')
    df['month'] = df['trans_date'].dt.to_period('M')

    log(f"Date range: {df['trans_date'].min().date()} to {df['trans_date'].max().date()}")

    monthly = df.groupby('month').agg(
        transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        unique_users=('cardid', 'nunique'),
        median_transaction=('trans_amount', 'median'),
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    print("\nMonthly summary:")
    print(monthly.to_string())

    # Create plot
    log("Creating plot...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{config["title"]} Subscriptions - Time Series', fontsize=14, fontweight='bold')

    date_min, date_max = monthly['month_dt'].min(), monthly['month_dt'].max()

    # Plot 1: Transaction count
    ax = axes[0, 0]
    ax.plot(monthly['month_dt'], monthly['transactions'], marker='o', linewidth=2)
    ax.set_ylabel('Transaction Count')
    ax.set_title('Monthly Transactions')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    for event, date in config['events'].items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=8)

    # Plot 2: Total spend
    ax = axes[0, 1]
    spend_divisor = 1e6 if monthly['total_spend'].max() > 1e6 else 1e3
    spend_label = '$M' if spend_divisor == 1e6 else '$K'
    ax.plot(monthly['month_dt'], monthly['total_spend'] / spend_divisor, marker='o', linewidth=2, color='green')
    ax.set_ylabel(f'Total Spend ({spend_label})')
    ax.set_title('Monthly Total Spend')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    for event, date in config['events'].items():
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
    for event, date in config['events'].items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)

    # Plot 4: Median transaction
    ax = axes[1, 1]
    ax.plot(monthly['month_dt'], monthly['median_transaction'], marker='o', linewidth=2, color='orange')
    ax.axhline(config['subscription_price'], color='gray', linestyle='-', alpha=0.8,
               label=f'${config["subscription_price"]} subscription price')
    ax.set_ylabel('Median Transaction ($)')
    ax.set_title('Median Transaction Amount')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper right')
    for event, date in config['events'].items():
        event_dt = pd.to_datetime(date)
        if date_min <= event_dt <= date_max:
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)

    plt.tight_layout()

    output_path = OUTPUT_DIR / f"{group_name}_timeseries.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    log(f"Saved: {output_path.name}")

    return monthly


def main():
    log("Loading transactions...")
    trans = load_transactions()
    log(f"Total: {len(trans):,} transactions")

    results = {}
    for group_name, config in ANALYSIS_GROUPS.items():
        results[group_name] = analyze_group(trans, group_name, config)

    log("\n" + "="*60)
    log("SUMMARY")
    log("="*60)
    for name, monthly in results.items():
        if monthly is not None:
            latest = monthly.iloc[-1]
            log(f"{ANALYSIS_GROUPS[name]['title']}:")
            log(f"  Latest month: {latest['transactions']:,} transactions, {latest['unique_users']:,} users")

    log("\nDone!")


if __name__ == "__main__":
    main()
