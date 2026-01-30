#!/usr/bin/env python3
"""
Spaghetti plot: gap (treated - synthetic) over time for all placebo units.
Like Abadie et al. California Prop 99 Figure 4.

NOTE: Don't run directly. Use run_placebo_plots.py instead:
    python code/robustness/run_placebo_plots.py 2
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/'
                'unique_users/15to25/all_merchants')
OUT_DIR = DATA_DIR / 'synthetic_placebo_robustness'

THRESHOLD_MULT = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def get_chicago_stats():
    """Compute Chicago pre-RMSPE from synth_results.dta."""
    results = pd.read_stata(DATA_DIR / 'synth_results.dta')
    results['gap'] = results['_Y_treated'] - results['_Y_synthetic']
    results['gap_sq'] = results['gap'] ** 2
    pre = results[results['_time'] < 10]
    return np.sqrt(pre['gap_sq'].mean())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get Chicago's pre-RMSPE for threshold
    chi_pre_rmspe = get_chicago_stats()
    threshold = chi_pre_rmspe * THRESHOLD_MULT
    print(f"Chicago pre-RMSPE: {chi_pre_rmspe:.4f}")
    print(f"Threshold ({THRESHOLD_MULT}x): {threshold:.4f}")

    # Load placebo series (has gap for each unit at each time)
    series = pd.read_stata(DATA_DIR / 'placebo_series_long.dta')
    print(f"Loaded {len(series)} rows from placebo_series_long.dta")

    # Compute pre-RMSPE for each unit to filter
    pre_rmspe = series[series['month_num'] < 10].groupby('zip3_id').agg(
        pre_rmspe=('gap', lambda x: np.sqrt((x**2).mean()))
    ).reset_index()

    # Filter to good pre-fit units
    good_units = pre_rmspe[pre_rmspe['pre_rmspe'] < threshold]['zip3_id'].values
    print(f"Units with pre-RMSPE < {threshold:.4f}: {len(good_units)}")

    # Separate Chicago from placebos
    chicago = series[series['zip3_id'] == 606].sort_values('month_num')
    placebos = series[(series['zip3_id'].isin(good_units)) &
                      (series['zip3_id'] != 606)]

    # Plot
    fig, ax = plt.subplots(figsize=(12, 7))

    # Gray spaghetti for placebos
    for unit_id in placebos['zip3_id'].unique():
        unit = placebos[placebos['zip3_id'] == unit_id].sort_values('month_num')
        ax.plot(unit['month_num'], unit['gap'],
                color='gray', alpha=0.3, linewidth=0.8)

    # Black line for Chicago
    ax.plot(chicago['month_num'], chicago['gap'],
            color='black', linewidth=2.5, label='Chicago (606)')

    # Treatment line
    ax.axvline(x=10, color='black', linestyle=':', linewidth=1)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5, alpha=0.5)

    # Labels
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Gap (Treated − Synthetic)', fontsize=12)
    ax.set_title(f'Placebo Gaps: Chicago vs Control ZIP3s\n'
                 f'(pre-RMSPE < {THRESHOLD_MULT}× Chicago, n={len(good_units)})',
                 fontsize=14)

    # Add text annotation for treatment
    ax.text(10.3, ax.get_ylim()[0] + 0.02, 'Chicago tax\n(Oct 2023)',
            fontsize=9, va='bottom')

    # Legend with custom entry for gray lines
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='black', linewidth=2.5, label='Chicago'),
        Line2D([0], [0], color='gray', alpha=0.5, linewidth=1,
               label=f'Placebo units (n={len(good_units)-1})')
    ]
    ax.legend(handles=legend_elements, loc='lower left')

    plt.tight_layout()
    outfile = OUT_DIR / f'placebo_spaghetti_{THRESHOLD_MULT}x.png'
    plt.savefig(outfile, dpi=150)
    print(f"Saved: {outfile}")
    plt.close()


if __name__ == "__main__":
    main()
