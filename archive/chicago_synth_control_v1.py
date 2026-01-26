#!/usr/bin/env python3
"""
Synthetic control for Chicago (606) ChatGPT subscriptions.
Donor pool: nearby IL zip codes 600, 601, 602, 604, 605.
Pre-period: before Jan 2025.
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
DONOR_ZIPS = ['600', '601', '602', '604', '605']
FIT_CUTOFF = '2023-10-01'  # Fit weights on pre-tax period (before 9% PPLTT on AI)

EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "9% PPLTT": "2023-10-01",
    "11% PPLTT": "2025-01-01",
}

END_DATE = '2025-12-01'  # Stop at November 2025 (incomplete data after)


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

    # Show keyword breakdown
    print("\nKeyword matches in full dataset:")
    print(trans['service'].value_counts())

    # Filter to ChatGPT/OpenAI
    trans = trans[trans['service'].str.lower().isin(['chatgpt', 'openai'])]
    log(f"ChatGPT/OpenAI: {len(trans):,}")

    # Load demographics and merge
    log("Loading demographics...")
    demo = pd.read_csv(DATA_DIR / "chatgpt_demographics_2023_2024_2025.csv", low_memory=False)
    trans = trans.merge(demo[['cardid', 'zip3']], on='cardid', how='left')

    # Filter to relevant zips
    all_zips = [TREATED_ZIP] + DONOR_ZIPS
    trans = trans[trans['zip3'].astype(str).isin(all_zips)].copy()
    trans['zip3'] = trans['zip3'].astype(str)
    log(f"Filtered to zips {all_zips}: {len(trans):,} transactions")

    # Prep data
    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['trans_amount'] = pd.to_numeric(trans['trans_amount'], errors='coerce')
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

    # Pivot to wide format
    pivot_spend = monthly.pivot(index='month_dt', columns='zip3', values='total_spend')
    pivot_price = monthly.pivot(index='month_dt', columns='zip3', values='median_transaction')

    # Compute quantity = spend / price, then take log
    pivot_quantity = pivot_spend / pivot_price
    pivot_quantity_log = np.log(pivot_quantity)
    pivot_spend_log = np.log(pivot_spend)  # Keep for reference

    # Show transaction counts
    counts = monthly.groupby('zip3')['n_transactions'].sum()
    print("\nTransaction counts by zip3:")
    print(counts.sort_values(ascending=False))

    # Drop months where any zip is missing
    pivot_quantity_log = pivot_quantity_log.dropna()
    pivot_quantity = pivot_quantity.loc[pivot_quantity_log.index]
    pivot_spend = pivot_spend.loc[pivot_quantity_log.index]
    pivot_spend_log = pivot_spend_log.loc[pivot_quantity_log.index]
    pivot_price = pivot_price.loc[pivot_quantity_log.index]

    # Filter to end at November 2025 (incomplete data after)
    pivot_quantity_log = pivot_quantity_log[pivot_quantity_log.index < END_DATE]
    pivot_quantity = pivot_quantity.loc[pivot_quantity_log.index]
    pivot_spend = pivot_spend.loc[pivot_quantity_log.index]
    pivot_spend_log = pivot_spend_log.loc[pivot_quantity_log.index]
    pivot_price = pivot_price.loc[pivot_quantity_log.index]
    log(f"Months with complete data (through Nov 2025): {len(pivot_quantity_log)}")

    # Split into fitting period (pre-tax) and evaluation periods
    fit_mask = pivot_quantity_log.index < FIT_CUTOFF
    fit_data_log = pivot_quantity_log[fit_mask]

    log(f"Fitting period months (pre-Oct 2023): {len(fit_data_log)}")

    # Match on LOG QUANTITY (spend / price)
    y_treated = fit_data_log[TREATED_ZIP].values
    X_donors = fit_data_log[DONOR_ZIPS].values

    # Optimize weights to minimize pre-period MSE
    def objective(w):
        synth = X_donors @ w
        return np.mean((y_treated - synth) ** 2)

    # No sum constraint, just non-negative weights
    constraints = []  # No equality constraint
    bounds = [(0, None) for _ in DONOR_ZIPS]  # >= 0, no upper bound

    # Initial guess: equal weights
    w0 = np.ones(len(DONOR_ZIPS)) / len(DONOR_ZIPS)

    result = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
    weights = result.x

    print("\n" + "="*60)
    print("SYNTHETIC CONTROL WEIGHTS (matched on log quantity pre-Oct 2023)")
    print("="*60)
    print("Raw weights (for log quantity matching):")
    for z, w in zip(DONOR_ZIPS, weights):
        print(f"  zip3 {z}: {w:.4f}")
    print(f"  Sum: {weights.sum():.4f}")
    print(f"  Pre-period RMSE (log Q): {np.sqrt(result.fun):.4f}")
    print("\nNormalized weights (for price, sum to 1):")
    weights_norm = weights / weights.sum()
    for z, w in zip(DONOR_ZIPS, weights_norm):
        if w > 0.001:
            print(f"  zip3 {z}: {w:.4f}")

    # Compute synthetic control for full period
    # For log quantity: weighted sum of logs
    synth_quantity_log = pivot_quantity_log[DONOR_ZIPS].values @ weights
    pivot_quantity_log['synthetic'] = synth_quantity_log
    # For levels: exp of synthetic log
    pivot_quantity['synthetic'] = np.exp(synth_quantity_log)

    # Normalize weights for price (so they sum to 1)
    weights_normalized = weights / weights.sum()
    synth_price_normalized = pivot_price[DONOR_ZIPS].values @ weights_normalized
    pivot_price['synthetic_norm'] = synth_price_normalized

    # Build synthetic control description for chart note
    synth_desc_parts = []
    for z, w in zip(DONOR_ZIPS, weights_normalized):
        if w > 0.01:
            synth_desc_parts.append(f"{w*100:.0f}% zip {z}")
    synth_desc = "Synthetic = " + " + ".join(synth_desc_parts)

    # Pivot transactions for out-of-sample test
    pivot_trans = monthly.pivot(index='month_dt', columns='zip3', values='n_transactions')
    pivot_trans = pivot_trans.loc[pivot_quantity_log.index]
    pivot_trans_log = np.log(pivot_trans)

    # Compute synthetic transactions using SAME weights (out-of-sample test)
    synth_trans_log = pivot_trans_log[DONOR_ZIPS].values @ weights
    pivot_trans_log['synthetic'] = synth_trans_log

    # Identify the two donor zips with non-zero weights for price panel
    active_donors = [(z, w) for z, w in zip(DONOR_ZIPS, weights) if w > 0.01]

    # Plot - three panels
    log("Creating plot...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Panel 1: Log Quantity = log(Spend / Price) - this is what we matched on
    ax = axes[0]
    ax.plot(pivot_quantity_log.index, pivot_quantity_log[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606)')
    ax.plot(pivot_quantity_log.index, pivot_quantity_log['synthetic'], marker='s', linewidth=2,
            color='orange', linestyle='--', label='Synthetic Control')
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if pivot_quantity_log.index.min() <= event_dt <= pivot_quantity_log.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')
    ax.set_xlabel('Month')
    ax.set_ylabel('Log Quantity (Spend / Median Price)')
    ax.set_title('Log Quantity (matched pre-Oct 2023)')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    # Add synthetic control note (weights sum > 1)
    weight_note = f"Weights: " + ", ".join([f"{z}={w:.2f}" for z, w in active_donors])
    weight_note += f" (sum={weights.sum():.2f})"
    ax.text(0.02, 0.02, weight_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Panel 2: Price - show raw prices for the 2 active donor zips
    ax = axes[1]
    ax.plot(pivot_price.index, pivot_price[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606)')
    colors = ['green', 'purple']
    for i, (z, w) in enumerate(active_donors):
        ax.plot(pivot_price.index, pivot_price[z], marker='s', linewidth=1.5,
                color=colors[i], linestyle='--', alpha=0.8, label=f'Zip {z}')
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if pivot_price.index.min() <= event_dt <= pivot_price.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')
    ax.axhline(20.00, color='gray', linestyle=':', alpha=0.5, label='$20 (no tax)')
    ax.axhline(21.80, color='blue', linestyle=':', alpha=0.5, label='$21.80 (9%)')
    ax.axhline(22.20, color='green', linestyle=':', alpha=0.5, label='$22.20 (11%)')
    ax.set_xlabel('Month')
    ax.set_ylabel('Median Transaction ($)')
    ax.set_title('Price (raw donor zips)')
    ax.legend(loc='upper left', fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    # Panel 3: Log Transactions (out-of-sample test with same weights)
    ax = axes[2]
    ax.plot(pivot_trans_log.index, pivot_trans_log[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606)')
    ax.plot(pivot_trans_log.index, pivot_trans_log['synthetic'], marker='s', linewidth=2,
            color='orange', linestyle='--', label='Synthetic Control')
    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if pivot_trans_log.index.min() <= event_dt <= pivot_trans_log.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')
    ax.set_xlabel('Month')
    ax.set_ylabel('Log Transactions')
    ax.set_title('Log Transactions (out-of-sample, same weights)')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)
    ax.text(0.02, 0.02, weight_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    output_path = OUTPUT_DIR / "chicago_synth_control.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    log(f"Saved: {output_path.name}")

    # Print comparison by period
    print("\n" + "="*60)
    print("PERIOD COMPARISONS")
    print("="*60)

    periods = [
        ("Pre-tax (before Oct 2023)", pivot_quantity_log.index < FIT_CUTOFF),
        ("9% tax (Oct 2023 - Dec 2024)", (pivot_quantity_log.index >= FIT_CUTOFF) & (pivot_quantity_log.index < '2025-01-01')),
        ("11% tax (Jan 2025+)", pivot_quantity_log.index >= '2025-01-01'),
    ]

    period_diffs = {}
    for period_name, mask in periods:
        qty_log_subset = pivot_quantity_log[mask]
        price_subset = pivot_price[mask]
        if len(qty_log_subset) > 0:
            print(f"\n{period_name}:")
            # Log Quantity
            chicago_log = qty_log_subset[TREATED_ZIP].mean()
            synth_log = qty_log_subset['synthetic'].mean()
            log_diff = chicago_log - synth_log
            period_diffs[period_name] = log_diff
            print(f"  Log Qty   - Chicago: {chicago_log:.2f}, Synthetic: {synth_log:.2f}, Diff: {log_diff:.2f}")
            # Price (using normalized weights)
            chicago_price = price_subset[TREATED_ZIP].mean()
            synth_price = price_subset['synthetic_norm'].mean()
            diff = chicago_price - synth_price
            print(f"  Price     - Chicago: ${chicago_price:.2f}, Synthetic: ${synth_price:.2f}, Diff: ${diff:.2f}")

    # Elasticity calculation
    print("\n" + "="*60)
    print("ELASTICITY ESTIMATE")
    print("="*60)

    # Treatment effect on log quantity: diff during 9% period minus diff during pre-period
    pre_diff = period_diffs.get("Pre-tax (before Oct 2023)", 0)
    tax9_diff = period_diffs.get("9% tax (Oct 2023 - Dec 2024)", 0)

    # Causal effect of 9% tax on log quantity (directly measured now!)
    causal_log_quantity = tax9_diff - pre_diff
    # Price change in logs: ln(1.09) ≈ 0.0862
    log_price_change = np.log(1.09)

    # Elasticity = Δln(Q) / Δln(P)
    elasticity_quantity = causal_log_quantity / log_price_change

    print(f"\nDiff-in-diff on log quantity: {causal_log_quantity:.3f}")
    print(f"  (pre-period diff: {pre_diff:.3f}, 9% tax period diff: {tax9_diff:.3f})")
    print(f"\nLog price change (9% tax): {log_price_change:.3f}")
    print(f"\n*** Elasticity of QUANTITY w.r.t. price: {elasticity_quantity:.2f} ***")
    print(f"    (A 9% price increase caused a {abs(causal_log_quantity)*100:.0f}% decrease in subscriptions)")


if __name__ == "__main__":
    main()
