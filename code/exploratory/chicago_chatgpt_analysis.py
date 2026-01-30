#!/usr/bin/env python3
"""
ChatGPT subscription analysis for Chicago (zip3 606) showing PPLTT tax effects.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import log, get_output_dir, get_filter_title
from load_data import load_with_zip3

# Key events
EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "9% PPLTT": "2023-10-01",
    "11% PPLTT": "2025-01-01",
}

# Price levels
BASE_PRICE = 20.00
FULL_PASSTHROUGH_9PCT = 21.80   # $20 * 1.09
FULL_PASSTHROUGH_11PCT = 22.20  # $20 * 1.11

END_DATE = '2025-12-01'  # Include 11% period for context


def main():
    trans = load_with_zip3()

    # Filter to Chicago (zip3 = 606)
    chicago = trans[trans['zip3'] == '606'].copy()
    log(f"Chicago (606xx Zip codes): {len(chicago):,} transactions")

    # Filter to date range
    chicago = chicago[chicago['trans_date'] < END_DATE].copy()
    chicago['month'] = chicago['trans_date'].dt.to_period('M')

    log(f"Date range: {chicago['trans_date'].min().date()} to {chicago['trans_date'].max().date()}")

    # Monthly aggregation
    monthly = chicago.groupby('month').agg(
        transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        unique_users=('cardid', 'nunique'),
        median_transaction=('trans_amount', 'median'),
        p25=('trans_amount', lambda x: x.quantile(0.25)),
        p75=('trans_amount', lambda x: x.quantile(0.75)),
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    print("\nMonthly summary:")
    print(monthly.to_string())

    # Create separate plots
    log("Creating plots...")
    out_dir = get_output_dir()
    date_min, date_max = monthly['month_dt'].min(), monthly['month_dt'].max()

    def add_event_lines(ax):
        for event, date in EVENTS.items():
            event_dt = pd.to_datetime(date)
            if date_min <= event_dt <= date_max:
                ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
                ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

    # Figure 1: Transaction count
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(monthly['month_dt'], monthly['transactions'], marker='o', linewidth=2)
    ax.set_ylabel('Transaction Count')
    ax.set_title('Chicago (606xx Zip codes) ChatGPT: Monthly Transactions')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    add_event_lines(ax)
    plt.tight_layout()
    plt.savefig(out_dir / "chicago_chatgpt_transactions.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_chatgpt_transactions.png")
    plt.close()

    # Figure 2: Total spend
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(monthly['month_dt'], monthly['total_spend'] / 1e3, marker='o', linewidth=2, color='green')
    ax.set_ylabel('Total Spend ($K)')
    ax.set_title('Chicago (606xx Zip codes) ChatGPT: Monthly Total Spend')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    add_event_lines(ax)
    plt.tight_layout()
    plt.savefig(out_dir / "chicago_chatgpt_spend.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_chatgpt_spend.png")
    plt.close()

    # Figure 3: Unique users
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(monthly['month_dt'], monthly['unique_users'], marker='o', linewidth=2, color='purple')
    ax.set_ylabel('Unique Users')
    ax.set_title('Chicago (606xx Zip codes) ChatGPT: Monthly Unique Users')
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    add_event_lines(ax)
    plt.tight_layout()
    plt.savefig(out_dir / "chicago_chatgpt_users.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_chatgpt_users.png")
    plt.close()

    # Figure 4: Median transaction with pass-through lines
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(monthly['month_dt'], monthly['median_transaction'], marker='o', linewidth=2, color='orange')
    ax.fill_between(monthly['month_dt'], monthly['p25'], monthly['p75'], alpha=0.2, color='orange', label='IQR')

    # Base price and full pass-through lines
    ax.axhline(BASE_PRICE, color='gray', linestyle='-', alpha=0.5, label=f'${BASE_PRICE:.0f} (no tax)')
    ax.axhline(FULL_PASSTHROUGH_9PCT, color='blue', linestyle='--', alpha=0.7,
               label=f'${FULL_PASSTHROUGH_9PCT:.2f} (full pass-through @ 9%)')
    ax.axhline(FULL_PASSTHROUGH_11PCT, color='red', linestyle='--', alpha=0.7,
               label=f'${FULL_PASSTHROUGH_11PCT:.2f} (full pass-through @ 11%)')

    # Event vlines
    ax.axvline(pd.to_datetime('2023-02-01'), color='gray', linestyle='--', alpha=0.7)
    ax.text(pd.to_datetime('2023-02-01'), 24, 'ChatGPT Plus', rotation=90, va='top', fontsize=9, color='gray')
    ax.axvline(pd.to_datetime('2023-10-01'), color='blue', linestyle=':', alpha=0.7)
    ax.text(pd.to_datetime('2023-10-01'), 24, '9% PPLTT', rotation=90, va='top', fontsize=9, color='blue')
    ax.axvline(pd.to_datetime('2025-01-01'), color='red', linestyle=':', alpha=0.7)
    ax.text(pd.to_datetime('2025-01-01'), 24, '11% PPLTT', rotation=90, va='top', fontsize=9, color='red')

    ax.set_ylabel('Median Transaction ($)')
    ax.set_title('Chicago (606xx Zip codes) ChatGPT: Median Transaction Amount')
    ax.set_xlim(date_min, date_max)
    ax.set_ylim(19, 25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "chicago_chatgpt_median_price.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_chatgpt_median_price.png")
    plt.close()

    # Print key comparisons
    print("\n" + "="*60)
    print("TAX EFFECT COMPARISON (PASS-THROUGH)")
    print("="*60)
    print(f"Base ChatGPT Plus price: ${BASE_PRICE:.2f}")
    print(f"Full pass-through @ 9%:  ${FULL_PASSTHROUGH_9PCT:.2f}")
    print()

    # 9% tax period
    mask = monthly['month_dt'] >= '2023-10-01'
    subset = monthly[mask]
    if len(subset) > 0:
        med = subset['median_transaction'].median()
        diff = med - FULL_PASSTHROUGH_9PCT
        print(f"9% tax period (Oct 2023 - Dec 2024):")
        print(f"  Expected (full pass-through): ${FULL_PASSTHROUGH_9PCT:.2f}")
        print(f"  Observed median:              ${med:.2f} ({diff:+.2f})")


if __name__ == "__main__":
    main()
