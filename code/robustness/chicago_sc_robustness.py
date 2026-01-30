#!/usr/bin/env python3
"""
Leave-k-out robustness checks for Chicago synthetic control.
For each k, plots all synthetic control lines on one chart.
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
from itertools import combinations
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import log, get_output_dir, get_filter_title
from load_data import load_with_zip3

TREATED_ZIP = '606'
START_DATE = '2023-03-01'
TREATMENT_DATE = '2023-10-01'
END_DATE = '2024-12-01'
SIZE_WINDOW = 0.1

EVENTS = {
    "9% PPLTT": "2023-10-01",
}


def run_sc_with_donors(pivot_log, donor_list):
    """Run synthetic control with a specific donor list. Returns synthetic series and stats."""
    pre_mask = pivot_log.index < TREATMENT_DATE
    pre_data = pivot_log[pre_mask]

    # Keep donors with complete pre-period
    valid_donors = [z for z in donor_list if z in pre_data.columns and pre_data[z].notna().all()]
    if len(valid_donors) < 2:
        return None, None, None, None

    fit_data = pivot_log[pre_mask][[TREATED_ZIP] + valid_donors].dropna()
    if len(fit_data) < 3:
        return None, None, None, None

    y_treated = fit_data[TREATED_ZIP].values
    X_donors = fit_data[valid_donors].values

    def objective(w):
        synth = X_donors @ w
        return np.mean((y_treated - synth) ** 2)

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0, 1) for _ in valid_donors]
    w0 = np.ones(len(valid_donors)) / len(valid_donors)

    result = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
    weights = result.x
    rmse = np.sqrt(result.fun)

    # Compute synthetic for full period
    full_data = pivot_log[[TREATED_ZIP] + valid_donors].dropna()
    full_data = full_data[full_data.index < END_DATE]
    synth_series = pd.Series(full_data[valid_donors].values @ weights, index=full_data.index)

    # Treatment effect
    pre_gap = full_data[full_data.index < TREATMENT_DATE][TREATED_ZIP].mean() - \
              synth_series[synth_series.index < TREATMENT_DATE].mean()
    post_gap = full_data[full_data.index >= TREATMENT_DATE][TREATED_ZIP].mean() - \
               synth_series[synth_series.index >= TREATMENT_DATE].mean()

    return synth_series, rmse, pre_gap, post_gap


def main():
    # Load data
    trans = load_with_zip3()
    log("Selecting size-matched controls (matching on n_users)...")

    early = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < '2023-07-01')]
    counts = early.groupby('zip3')['cardid'].nunique().reset_index(name='size_metric')

    chicago_size = counts[counts['zip3'] == TREATED_ZIP]['size_metric'].values[0]
    lower = chicago_size * (1 - SIZE_WINDOW)
    upper = chicago_size * (1 + SIZE_WINDOW)

    similar = counts[(counts['size_metric'] >= lower) & (counts['size_metric'] <= upper)]
    similar = similar[similar['zip3'] != TREATED_ZIP]
    similar = similar[similar['zip3'].str.match(r'^\d{3}$')]
    control_zips = similar['zip3'].tolist()

    log(f"Chicago unique users (Mar-Jun 2023): {chicago_size}")
    log(f"Control ZIP3s (within {SIZE_WINDOW*100:.0f}%): {len(control_zips)}")

    # Filter data
    all_zips = [TREATED_ZIP] + control_zips
    trans = trans[trans['zip3'].isin(all_zips)].copy()
    trans = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < END_DATE)].copy()

    # Monthly panel
    trans['month'] = trans['trans_date'].dt.to_period('M')
    monthly = trans.groupby(['zip3', 'month']).agg(
        n_users=('cardid', 'nunique')
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    pivot = monthly.pivot(index='month_dt', columns='zip3', values='n_users')
    pivot_log = np.log(pivot)
    pivot_log = pivot_log.dropna(subset=[TREATED_ZIP])

    # Get Chicago series
    chicago_series = pivot_log[TREATED_ZIP][pivot_log.index < END_DATE]

    # Output directory
    out_dir = get_output_dir() / 'robustness'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run baseline
    log("Running baseline SC...")
    base_synth, base_rmse, base_pre, base_post = run_sc_with_donors(pivot_log, control_zips)
    log(f"Baseline: RMSE={base_rmse:.4f}, pre_gap={base_pre:.4f}, post_gap={base_post:.4f}")

    # Get donors with >1% weight from baseline
    pre_mask = pivot_log.index < TREATMENT_DATE
    pre_data = pivot_log[pre_mask]
    valid_donors = [z for z in control_zips if z in pre_data.columns and pre_data[z].notna().all()]
    fit_data = pivot_log[pre_mask][[TREATED_ZIP] + valid_donors].dropna()

    y_treated = fit_data[TREATED_ZIP].values
    X_donors = fit_data[valid_donors].values

    def objective(w):
        return np.mean((y_treated - X_donors @ w) ** 2)

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0, 1) for _ in valid_donors]
    w0 = np.ones(len(valid_donors)) / len(valid_donors)
    result = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)

    weight_df = pd.DataFrame({'zip3': valid_donors, 'weight': result.x})
    top_donors = weight_df[weight_df['weight'] > 0.01]['zip3'].tolist()
    log(f"Top donors (>1% weight): {len(top_donors)} - {top_donors}")

    # Results storage
    results = []
    results.append({
        'k': 0,
        'removed': '',
        'rmse': base_rmse,
        'pre_gap': base_pre,
        'post_gap': base_post
    })

    # Leave-k-out for k = 1 to len(top_donors)
    max_k = len(top_donors)

    for k in range(1, max_k + 1):
        combos = list(combinations(top_donors, k))
        log(f"Running leave-{k}-out ({len(combos)} combinations)...")

        # Collect all synthetic series for this k
        synth_lines = []
        combo_labels = []

        for removed in combos:
            remaining = [z for z in control_zips if z not in removed]
            synth_series, rmse, pre_gap, post_gap = run_sc_with_donors(pivot_log, remaining)

            if synth_series is not None:
                synth_lines.append(synth_series)
                combo_labels.append(','.join(removed))
                results.append({
                    'k': k,
                    'removed': ','.join(removed),
                    'rmse': rmse,
                    'pre_gap': pre_gap,
                    'post_gap': post_gap
                })

        # Create plot for this k
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot Chicago (thick blue)
        ax.plot(chicago_series.index, chicago_series.values, marker='o', linewidth=2.5,
                color='blue', label='Chicago (606xx)', zorder=10)

        # Plot baseline synthetic (thick orange dashed)
        ax.plot(base_synth.index, base_synth.values, linewidth=2.5,
                color='orange', linestyle='--', label='Baseline SC', zorder=9)

        # Plot all leave-k-out synthetics (thin gray)
        for i, synth in enumerate(synth_lines):
            label = f'Leave-{k}-out' if i == 0 else None
            ax.plot(synth.index, synth.values, linewidth=0.8,
                    color='gray', alpha=0.5, label=label, zorder=1)

        # Shade treatment period
        ax.axvspan(pd.to_datetime(TREATMENT_DATE), chicago_series.index.max(),
                   alpha=0.15, color='red')

        ax.axvline(pd.to_datetime(TREATMENT_DATE), color='red', linestyle='--', alpha=0.7)

        ax.set_xlabel('Month')
        ax.set_ylabel('Log n_users')
        ax.set_title(f'SC Robustness: Leave-{k}-Out ({len(synth_lines)} combinations) {get_filter_title()}')
        ax.legend(loc='upper left')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.tick_params(axis='x', rotation=45)

        # Summary stats in annotation
        post_gaps = [r['post_gap'] for r in results if r['k'] == k]
        note = (f"Baseline post_gap: {base_post:.3f}\n"
                f"Leave-{k}-out post_gap:\n"
                f"  mean={np.mean(post_gaps):.3f}, min={np.min(post_gaps):.3f}, max={np.max(post_gaps):.3f}")
        ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=8,
                verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig(out_dir / f'leave_{k}_out.png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        log(f"  Saved: {out_dir / f'leave_{k}_out.png'}")

    # Save results CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv(out_dir / 'leave_k_out_results.csv', index=False)
    log(f"Saved: {out_dir / 'leave_k_out_results.csv'}")

    # Summary stats by k
    print("\n" + "="*70)
    print("LEAVE-K-OUT ROBUSTNESS SUMMARY")
    print("="*70)
    print(f"\nBaseline treatment effect (post_gap): {base_post:.4f}")

    for k in range(1, max_k + 1):
        subset = results_df[results_df['k'] == k]
        if len(subset) > 0:
            print(f"\nLeave-{k}-out ({len(subset)} combinations):")
            print(f"  post_gap: mean={subset['post_gap'].mean():.4f}, "
                  f"min={subset['post_gap'].min():.4f}, max={subset['post_gap'].max():.4f}")

    # Overall summary
    print("\n" + "="*70)
    all_effects = results_df[results_df['k'] > 0]['post_gap']
    print(f"Across all {len(all_effects)} leave-k-out combinations:")
    print(f"  Treatment effect range: [{all_effects.min():.4f}, {all_effects.max():.4f}]")
    print(f"  Mean: {all_effects.mean():.4f}, Std: {all_effects.std():.4f}")
    print(f"  Baseline: {base_post:.4f}")

    same_sign = (all_effects < 0).sum() if base_post < 0 else (all_effects > 0).sum()
    print(f"  Same sign as baseline: {same_sign}/{len(all_effects)} ({100*same_sign/len(all_effects):.1f}%)")


if __name__ == "__main__":
    main()
