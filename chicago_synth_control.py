#!/usr/bin/env python3
"""
Synthetic control for Chicago (606) ChatGPT subscriptions.
Donor pool: all ZIP3s with similar transaction volume to Chicago in Feb-Jun 2023.
Pre-period: Feb 2023 - Sep 2023 (before Oct 2023 tax).
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
OUTPUT_DIR = Path(__file__).parent

TREATED_ZIP = '606'
START_DATE = '2023-02-01'  # ChatGPT Plus launch
FIT_CUTOFF = '2023-10-01'
END_DATE = '2025-01-01'  # Exclude 11% period
SIZE_WINDOW = 0.5  # Donors must be within 50% of Chicago's size

EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "9% PPLTT": "2023-10-01",
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

    trans = trans[trans['service'].str.lower().isin(['chatgpt', 'openai'])]
    log(f"ChatGPT/OpenAI: {len(trans):,}")

    log("Loading demographics...")
    demo = pd.read_csv(DATA_DIR / "chatgpt_demographics_2023_2024_2025.csv", low_memory=False)
    trans = trans.merge(demo[['cardid', 'zip3']], on='cardid', how='left')
    trans['zip3'] = trans['zip3'].astype(str)
    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['trans_amount'] = pd.to_numeric(trans['trans_amount'], errors='coerce')

    # Select donors based on Feb-Jun 2023 size (post ChatGPT Plus launch)
    log("Selecting size-matched donors...")
    early = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < '2023-07-01')]
    counts = early.groupby('zip3').size().reset_index(name='n_trans')

    chicago_size = counts[counts['zip3'] == TREATED_ZIP]['n_trans'].values[0]
    lower = chicago_size * (1 - SIZE_WINDOW)
    upper = chicago_size * (1 + SIZE_WINDOW)

    similar = counts[(counts['n_trans'] >= lower) & (counts['n_trans'] <= upper)]
    similar = similar[similar['zip3'] != TREATED_ZIP]
    similar = similar[similar['zip3'].str.match(r'^\d{3}$')]  # Valid ZIP3s only

    donor_zips = similar['zip3'].tolist()
    log(f"Chicago size (Feb-Jun 2023): {chicago_size}")
    log(f"Donor ZIP3s (within {SIZE_WINDOW*100:.0f}%): {len(donor_zips)}")

    # Filter to relevant ZIPs and date range
    all_zips = [TREATED_ZIP] + donor_zips
    trans = trans[trans['zip3'].isin(all_zips)].copy()
    trans = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < END_DATE)].copy()

    # Prep data
    trans['month'] = trans['trans_date'].dt.to_period('M')

    # Monthly aggregations by zip3
    log("Computing monthly aggregations by zip3...")
    monthly = trans.groupby(['zip3', 'month']).agg(
        median_transaction=('trans_amount', 'median'),
        total_spend=('trans_amount', 'sum'),
        n_transactions=('trans_amount', 'count'),
        unique_users=('cardid', 'nunique'),
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    # Pivot to wide format - use log transactions
    pivot_trans = monthly.pivot(index='month_dt', columns='zip3', values='n_transactions')
    pivot_trans_log = np.log(pivot_trans)

    # Drop months where Chicago is missing
    pivot_trans_log = pivot_trans_log.dropna(subset=[TREATED_ZIP])

    # Filter to end date
    pivot_trans_log = pivot_trans_log[pivot_trans_log.index < END_DATE]

    # Only keep donors with complete data in pre-period
    pre_mask = pivot_trans_log.index < FIT_CUTOFF
    pre_data = pivot_trans_log[pre_mask]
    valid_donors = [z for z in donor_zips if z in pre_data.columns and pre_data[z].notna().all()]
    log(f"Donors with complete pre-period data: {len(valid_donors)}")

    # Split into fitting period and full period
    fit_data = pivot_trans_log[pre_mask][[TREATED_ZIP] + valid_donors].dropna()

    log(f"Fitting period months (pre-Oct 2023): {len(fit_data)}")

    # Match on log transactions
    y_treated = fit_data[TREATED_ZIP].values
    X_donors = fit_data[valid_donors].values

    # Optimize weights to minimize pre-period MSE
    # Constrain weights to sum to 1 and be non-negative (convex combination)
    def objective(w):
        synth = X_donors @ w
        return np.mean((y_treated - synth) ** 2)

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0, 1) for _ in valid_donors]

    # Initial guess: equal weights
    w0 = np.ones(len(valid_donors)) / len(valid_donors)

    result = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
    weights = result.x

    print("\n" + "="*60)
    print("SYNTHETIC CONTROL WEIGHTS")
    print("="*60)
    print(f"Pre-period RMSE (log transactions): {np.sqrt(result.fun):.4f}")
    print("\nTop donors by weight:")
    weight_df = pd.DataFrame({'zip3': valid_donors, 'weight': weights})
    weight_df = weight_df[weight_df['weight'] > 0.01].sort_values('weight', ascending=False)
    for _, row in weight_df.iterrows():
        print(f"  {row['zip3']}: {row['weight']:.3f}")
    print(f"\nTotal donors with weight > 1%: {len(weight_df)}")

    # Compute synthetic control for full period (only for months where all top donors have data)
    top_donors = weight_df['zip3'].tolist()
    top_weights = weight_df['weight'].values

    # Filter to months where all top donors have data
    full_data = pivot_trans_log[[TREATED_ZIP] + top_donors].dropna()
    full_data = full_data[full_data.index < END_DATE]

    synth_log = full_data[top_donors].values @ top_weights
    full_data['synthetic'] = synth_log

    # Plot
    log("Creating plot...")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(full_data.index, full_data[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606)')
    ax.plot(full_data.index, full_data['synthetic'], marker='s', linewidth=2,
            color='orange', linestyle='--', label='Synthetic Control')

    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if full_data.index.min() <= event_dt <= full_data.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

    ax.set_xlabel('Month')
    ax.set_ylabel('Log Transactions')
    ax.set_title(f'Synthetic Control: Chicago vs {len(weight_df)} size-matched ZIP3s')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    # Add weight note
    top3 = weight_df.head(3)
    weight_note = "Top weights: " + ", ".join([f"{r['zip3']}={r['weight']:.2f}" for _, r in top3.iterrows()])
    ax.text(0.02, 0.02, weight_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chicago_synth_control.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_synth_control.png")

    # Print comparison by period
    print("\n" + "="*60)
    print("PERIOD COMPARISONS")
    print("="*60)

    periods = [
        ("Pre-tax (Feb-Sep 2023)", full_data.index < FIT_CUTOFF),
        ("9% tax (Oct-Dec 2024)", full_data.index >= FIT_CUTOFF),
    ]

    for period_name, mask in periods:
        subset = full_data[mask]
        if len(subset) > 0:
            chicago_log = subset[TREATED_ZIP].mean()
            synth_log = subset['synthetic'].mean()
            diff = chicago_log - synth_log
            print(f"\n{period_name}:")
            print(f"  Chicago: {chicago_log:.3f}, Synthetic: {synth_log:.3f}, Diff: {diff:.3f}")


if __name__ == "__main__":
    main()
