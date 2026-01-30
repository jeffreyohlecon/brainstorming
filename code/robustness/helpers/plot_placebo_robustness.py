#!/usr/bin/env python3
"""
Generate placebo robustness plots (histogram, scatter plots).

NOTE: Don't run directly. Use run_placebo_plots.py instead:
    python code/robustness/run_placebo_plots.py 2
"""

import sys
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import get_output_dir

DATA_DIR = get_output_dir()
OUT_DIR = DATA_DIR / 'synthetic_placebo_robustness'
DERIVED_DIR = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/derived_data')

# Threshold multiplier for pre-RMSPE filter (Abadie uses 2x, 5x, 20x)
THRESHOLD_MULT = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def get_chicago_stats():
    """Compute Chicago stats from synth_results.dta (no hardcoding)."""
    results = pd.read_stata(DATA_DIR / 'synth_results.dta')
    results['gap'] = results['_Y_treated'] - results['_Y_synthetic']
    results['gap_sq'] = results['gap'] ** 2

    pre = results[results['_time'] < 10]
    post = results[results['_time'] >= 10]

    pre_rmspe = np.sqrt(pre['gap_sq'].mean())
    post_rmspe = np.sqrt(post['gap_sq'].mean())
    ratio = post_rmspe / pre_rmspe
    post_gap = post['gap'].mean()

    return {
        'pre_rmspe': pre_rmspe,
        'post_rmspe': post_rmspe,
        'ratio': ratio,
        'post_gap': post_gap,
    }


def parse_log():
    """Parse completed units from log file, including zip3_id and signed gaps."""
    results = []

    with open('chicago_synth_placebo_topq.log', 'r') as f:
        content = f.read()

    # Remove line continuations (> at start of line) for wrapped output
    content = re.sub(r'\n> ?', '', content)

    # Pattern includes post_gap (signed mean post-period gap)
    # "Placebo N: zip3_id = X" then "  pre=..., post=..., ratio=..., post_gap=..."
    pattern = (r'Placebo \d+: zip3_id = (\d+)\s+'
               r'pre=([\d.]+), post=([\d.]+), ratio=([\d.]+), post_gap=([-\d.]+)')

    for match in re.finditer(pattern, content):
        zip3_id = int(match.group(1))
        pre = float(match.group(2))
        post = float(match.group(3))
        ratio = float(match.group(4))
        post_gap = float(match.group(5))
        results.append({
            'zip3_id': zip3_id,
            'pre_rmspe': pre,
            'post_rmspe': post,
            'ratio': ratio,
            'post_gap': post_gap  # signed mean post-period gap
        })

    return pd.DataFrame(results)


def load_placebo_results():
    """Load placebo results from .dta if available, else parse log."""
    dta_path = DERIVED_DIR / 'placebo_results_topq.dta'

    if dta_path.exists():
        print(f"Loading from {dta_path}")
        return pd.read_stata(dta_path)
    else:
        print("No .dta file found, parsing log...")
        return parse_log()


def main():
    # Get Chicago stats from synth_results.dta (no hardcoding)
    chi = get_chicago_stats()
    print(f"Chicago: pre_rmspe={chi['pre_rmspe']:.4f}, "
          f"ratio={chi['ratio']:.2f}, post_gap={chi['post_gap']:.3f}")

    # Try .dta first, fall back to log parsing
    placebo = load_placebo_results()
    print(f"Loaded {len(placebo)} placebo results")

    if len(placebo) == 0:
        print("No results yet. Run placebo tests first.")
        return

    # Load panel for population, zip3 codes, and pre-period users
    panel = pd.read_stata('data/synth_panel.dta')

    # Pre-period mean users (month_num < 10 is pre-treatment)
    pre_users = panel[panel['month_num'] < 10].groupby('zip3_id').agg(
        pre_users=('n_users', 'mean')
    ).reset_index()

    pop = panel.groupby('zip3_id').agg(
        zip3=('zip3', 'first'),
        population=('population', 'first')
    ).reset_index()

    pop = pop.merge(pre_users, on='zip3_id', how='left')

    # Merge
    df = placebo.merge(pop, on='zip3_id', how='left')

    # Add Chicago
    chicago_pop = pop[pop['zip3'] == '606']['population'].values[0]
    chicago_pre_users = pop[pop['zip3'] == '606']['pre_users'].values[0]
    chicago_row = pd.DataFrame([{
        'zip3_id': 606,
        'zip3': '606',
        'pre_rmspe': chi['pre_rmspe'],
        'post_rmspe': chi['post_rmspe'],
        'ratio': chi['ratio'],
        'post_gap': chi['post_gap'],
        'population': chicago_pop,
        'pre_users': chicago_pre_users,
        'is_chicago': True
    }])
    df['is_chicago'] = False
    df = pd.concat([df, chicago_row], ignore_index=True)

    # Compute signed gap ratio: post_gap / pre_rmspe
    # This is treatment effect as a fraction of pre-period noise
    df['gap_ratio'] = df['post_gap'] / df['pre_rmspe']
    chicago_gap_ratio = chi['post_gap'] / chi['pre_rmspe']

    # Filter to good pre-fit
    threshold = chi['pre_rmspe'] * THRESHOLD_MULT
    good = df[df['pre_rmspe'] < threshold].copy()
    thresh_label = f"{THRESHOLD_MULT}x"

    # Ensure output dirs exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Units with good pre-fit (<{threshold:.3f}): {len(good)}")
    print(f"Chicago population: {chicago_pop:,.0f}")

    # =========================================================
    # Plot 1: RMSPE ratio vs population
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 7))

    # Filter to good pre-fit
    good_plac = good[~good['is_chicago']].dropna(subset=['population', 'ratio'])
    ax.scatter(good_plac['population']/1e6, good_plac['ratio'],
               alpha=0.5, s=50, c='gray', label='Placebo units (good fit)')

    # Regression line
    slope2, intercept2, r2, p2, se2 = stats.linregress(
        good_plac['population']/1e6, good_plac['ratio'])
    x_line2 = np.linspace(0, good_plac['population'].max()/1e6, 100)
    ax.plot(x_line2, slope2 * x_line2 + intercept2, 'b-', linewidth=2,
            label=f'OLS: β={slope2:.2f}, r={r2:.2f}, p={p2:.3f}')

    # Chicago
    ax.scatter(chicago_pop/1e6, chi['ratio'],
               s=200, c='red', marker='*', zorder=10,
               label=f'Chicago (ratio={chi['ratio']:.2f})')

    ax.set_xlabel('Population (millions)')
    ax.set_ylabel('Post/Pre RMSPE Ratio')
    ax.set_title('Placebo Test: RMSPE Ratio vs Population\n'
                 f'(pre-RMSPE < {threshold:.3f}, n={len(good)})')
    ax.legend(loc='upper right')

    # Annotate high-ratio large cities
    for _, row in good.iterrows():
        if row['ratio'] > 2.5 or row['population'] > 2e6:
            label = 'Chicago' if row['is_chicago'] else row['zip3']
            ax.annotate(label,
                       (row['population']/1e6, row['ratio']),
                       textcoords="offset points", xytext=(5, 5),
                       fontsize=8, alpha=0.8)

    plt.tight_layout()
    fname = f'rmspe_vs_population_{thresh_label}.png'
    plt.savefig(OUT_DIR / fname, dpi=150)
    print(f"Saved: {OUT_DIR / fname}")
    plt.close()
    print(f"  Ratio vs population: slope={slope2:.3f}, r={r2:.3f}, p={p2:.4f}")

    # =========================================================
    # Plot 3: RMSPE ratio vs pre-period users
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 7))

    good_plac3 = good[~good['is_chicago']].dropna(subset=['pre_users', 'ratio'])
    ax.scatter(good_plac3['pre_users'], good_plac3['ratio'],
               alpha=0.5, s=50, c='gray', label='Placebo units (good fit)')

    # Regression line
    slope3, intercept3, r3, p3, se3 = stats.linregress(
        good_plac3['pre_users'], good_plac3['ratio'])
    x_line3 = np.linspace(0, good_plac3['pre_users'].max(), 100)
    ax.plot(x_line3, slope3 * x_line3 + intercept3, 'b-', linewidth=2,
            label=f'OLS: β={slope3:.4f}, r={r3:.2f}, p={p3:.3f}')

    # Chicago
    chicago_pre_users = good[good['is_chicago']]['pre_users'].values[0]
    ax.scatter(chicago_pre_users, chi['ratio'],
               s=200, c='red', marker='*', zorder=10,
               label=f'Chicago (ratio={chi['ratio']:.2f})')

    ax.set_xlabel('Pre-period mean users/month')
    ax.set_ylabel('Post/Pre RMSPE Ratio')
    ax.set_title('Placebo Test: RMSPE Ratio vs Pre-Period Users\n'
                 f'(pre-RMSPE < {threshold:.3f}, n={len(good)})')
    ax.legend(loc='upper right')

    # Annotate high-ratio or large units
    for _, row in good.iterrows():
        if row['ratio'] > 2.5 or row['pre_users'] > 300:
            label = 'Chicago' if row['is_chicago'] else row['zip3']
            ax.annotate(label,
                       (row['pre_users'], row['ratio']),
                       textcoords="offset points", xytext=(5, 5),
                       fontsize=8, alpha=0.8)

    plt.tight_layout()
    fname = f'rmspe_vs_pre_users_{thresh_label}.png'
    plt.savefig(OUT_DIR / fname, dpi=150)
    print(f"Saved: {OUT_DIR / fname}")
    plt.close()
    print(f"  Ratio vs pre_users: slope={slope3:.5f}, r={r3:.3f}, p={p3:.4f}")

    # =========================================================
    # Plot 4: Signed gap ratio vs pre-period users
    # gap_ratio = post_gap / pre_rmspe (treatment effect / noise)
    # =========================================================
    if 'post_gap' in good.columns and good['post_gap'].notna().any():
        fig, ax = plt.subplots(figsize=(10, 7))

        good_plac4 = good[~good['is_chicago']].dropna(
            subset=['pre_users', 'gap_ratio'])
        ax.scatter(good_plac4['pre_users'], good_plac4['gap_ratio'],
                   alpha=0.5, s=50, c='gray', label='Placebo units')

        # Regression line
        slope4, intercept4, r4, p4, se4 = stats.linregress(
            good_plac4['pre_users'], good_plac4['gap_ratio'])
        x_line4 = np.linspace(0, good_plac4['pre_users'].max(), 100)
        ax.plot(x_line4, slope4 * x_line4 + intercept4, 'b-', linewidth=2,
                label=f'OLS: β={slope4:.5f}, r={r4:.2f}, p={p4:.3f}')

        # Chicago
        ax.scatter(chicago_pre_users, chicago_gap_ratio,
                   s=200, c='red', marker='*', zorder=10,
                   label=f'Chicago ({chicago_gap_ratio:.2f})')

        # Zero line
        ax.axhline(0, color='gray', linestyle='-', alpha=0.3)

        ax.set_xlabel('Pre-period mean users/month')
        ax.set_ylabel('Signed Gap Ratio (post_gap / pre_RMSPE)')
        ax.set_title(f'Placebo: Treatment Effect / Noise vs Pre-Users\n'
                     f'(pre-RMSPE < {thresh_label} Chicago, n={len(good)})')
        ax.legend(loc='upper right')

        # Annotate extreme values
        for _, row in good.iterrows():
            if abs(row['gap_ratio']) > abs(chicago_gap_ratio) * 0.8:
                label = 'Chicago' if row['is_chicago'] else row['zip3']
                ax.annotate(label,
                           (row['pre_users'], row['gap_ratio']),
                           textcoords="offset points", xytext=(5, 5),
                           fontsize=8, alpha=0.8)

        plt.tight_layout()
        fname = f'gap_ratio_vs_pre_users_{thresh_label}.png'
        plt.savefig(OUT_DIR / fname, dpi=150)
        print(f"Saved: {OUT_DIR / fname}")
        plt.close()
        print(f"  Gap ratio vs pre_users: slope={slope4:.6f}, "
              f"r={r4:.3f}, p={p4:.4f}")
    else:
        print("  Skipping gap_ratio plot (no post_gap data yet)")

    # =========================================================
    # Plot 5: Histogram of RMSPE ratios
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 6))

    n_bins = min(30, max(5, len(good) // 3))
    ax.hist(good[~good['is_chicago']]['ratio'], bins=n_bins,
            color='gray', alpha=0.7, edgecolor='black', label='Placebo units')
    ax.axvline(chi['ratio'], color='red', linewidth=2, linestyle='--',
               label=f'Chicago ({chi['ratio']:.2f})')

    # Compute p-value for this threshold
    n_extreme = (good['ratio'] >= chi['ratio']).sum()
    pval = n_extreme / len(good)

    ax.set_xlabel('Post/Pre RMSPE Ratio')
    ax.set_ylabel('Count')
    ax.set_title(f'Placebo Distribution (pre-RMSPE < {thresh_label} Chicago, '
                 f'n={len(good)}, p={pval:.3f})')
    ax.legend()

    ax.text(0.95, 0.95,
            f'p-value = {pval:.3f}\n({n_extreme}/{len(good)} units)',
            transform=ax.transAxes, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    fname = f'placebo_histogram_{thresh_label}.png'
    plt.savefig(OUT_DIR / fname, dpi=150)
    print(f"Saved: {OUT_DIR / fname}")
    plt.close()

    # =========================================================
    # Summary stats
    # =========================================================
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    # P-values at multiple thresholds (Abadie style)
    print("\nP-VALUES BY PRE-RMSPE THRESHOLD:")
    print("-" * 50)
    print(f"{'Threshold':<20} {'n':<8} {'≥Chicago':<10} {'p-value':<10}")
    print("-" * 50)

    for mult_name, mult in [('All units', None), ('20×', 20), ('5×', 5), ('2×', 2)]:
        if mult is None:
            subset = df
        else:
            thresh = chi['pre_rmspe'] * mult
            subset = df[df['pre_rmspe'] < thresh]
        n_total = len(subset)
        n_extreme = (subset['ratio'] >= chi['ratio']).sum()
        pval = n_extreme / n_total if n_total > 0 else np.nan
        print(f"{mult_name:<20} {n_total:<8} {n_extreme:<10} {pval:.3f}")

    # Correlation with population
    corr = good['population'].corr(good['ratio'])
    print(f"Correlation(population, ratio): {corr:.3f}")

    # Top ratios
    print("\nTop 10 by RMSPE ratio (good pre-fit):")
    top10 = good.nlargest(10, 'ratio')[
        ['zip3', 'pre_rmspe', 'ratio', 'population', 'is_chicago']]
    top10['population'] = top10['population'].apply(lambda x: f"{x/1e6:.2f}M")
    print(top10.to_string(index=False))

    # Save data to derived_data
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DERIVED_DIR / 'placebo_results_with_pop.csv', index=False)
    print(f"\nSaved: {DERIVED_DIR / 'placebo_results_with_pop.csv'}")


if __name__ == "__main__":
    main()
