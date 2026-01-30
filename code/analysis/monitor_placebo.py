#!/usr/bin/env python3
"""
Monitor placebo tests in real-time. Shows running p-value as units complete.
Run with: python3 monitor_placebo.py
Or watch mode: watch -n 5 python3 monitor_placebo.py

Uses TOP QUARTILE placebo run (by pre-treatment outcome level).
"""

import re
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import get_output_dir, get_outcome_label


def get_chicago_stats():
    """Read Chicago's RMSPE from synth_results.dta."""
    import pandas as pd
    outdir = get_output_dir()
    results_path = outdir / 'synth_results.dta'

    if not results_path.exists():
        # Fallback if file missing
        return 0.0358, 0.127, 3.55

    results = pd.read_stata(results_path)
    results['gap'] = results['_Y_treated'] - results['_Y_synthetic']
    results['gap_sq'] = results['gap'] ** 2

    pre = results[results['_time'] < 10]
    post = results[results['_time'] >= 10]

    pre_rmspe = np.sqrt(pre['gap_sq'].mean())
    post_rmspe = np.sqrt(post['gap_sq'].mean())
    ratio = post_rmspe / pre_rmspe

    return pre_rmspe, post_rmspe, ratio


def parse_log():
    """Parse completed units from log file."""
    results = []

    repo_root = Path(__file__).parent.parent.parent
    log_path = repo_root / 'chicago_synth_placebo_topq.log'
    try:
        with open(log_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return results

    # Pattern: "pre=X, post=Y, ratio=Z"
    pattern = r'pre=([\d.]+), post=([\d.]+), ratio=([\d.]+)'

    for match in re.finditer(pattern, content):
        pre = float(match.group(1))
        post = float(match.group(2))
        ratio = float(match.group(3))
        results.append({'pre_rmspe': pre, 'post_rmspe': post, 'ratio': ratio})

    return results


def main():
    results = parse_log()

    if not results:
        print("No completed units yet. Waiting for placebo tests...")
        return

    # Get Chicago stats from synth_results.dta
    chi_pre, chi_post, chi_ratio = get_chicago_stats()

    outcome_label = get_outcome_label()
    print("=" * 60)
    print(f"PLACEBO MONITOR - TOP QUARTILE ({outcome_label})")
    print("=" * 60)
    print(f"Completed units: {len(results)} / ~211")
    print()

    # Chicago reference
    print("CHICAGO:")
    print(f"  Pre-RMSPE:  {chi_pre:.4f}")
    print(f"  Post-RMSPE: {chi_post:.4f}")
    print(f"  Ratio:      {chi_ratio:.2f}")
    print()

    # P-values at different thresholds
    print("P-VALUE SENSITIVITY (pre-RMSPE threshold):")
    print("-" * 60)
    print(f"{'Threshold':<20} {'Placebos':<12} {'>= Chicago':<12} {'p-value':<10}")
    print("-" * 60)

    for mult in [2, 5, 10, None]:  # None = all units
        if mult is None:
            good = results
            label = "All"
        else:
            threshold = chi_pre * mult
            good = [r for r in results if r['pre_rmspe'] < threshold]
            label = f"{mult}x (< {threshold:.3f})"
        n_good = len(good) + 1  # +1 for Chicago
        n_extreme = sum(1 for r in good if r['ratio'] >= chi_ratio) + 1
        pval = n_extreme / n_good
        print(f"{label:<20}{len(good):<12}{n_extreme:<12}{pval:.3f}")

    print()

    # Top ratios with details
    chicago = {'pre_rmspe': chi_pre, 'post_rmspe': chi_post,
               'ratio': chi_ratio, 'is_chicago': True}

    # Use 5x threshold for the ranking display
    threshold_5x = chi_pre * 5
    good_fit = [r for r in results if r['pre_rmspe'] < threshold_5x]
    good_fit.append(chicago)
    sorted_by_ratio = sorted(good_fit, key=lambda x: x['ratio'], reverse=True)

    print(f"TOP RATIOS (pre-RMSPE < {threshold_5x:.3f}):")
    print("-" * 60)
    print(f"{'Rank':<6} {'Pre-RMSPE':<12} {'Post-RMSPE':<12} {'Ratio':<10}")
    print("-" * 60)

    for i, r in enumerate(sorted_by_ratio[:10], 1):
        marker = " <<< CHICAGO" if r.get('is_chicago') else ""
        print(f"{i:<6} {r['pre_rmspe']:<12.4f} {r['post_rmspe']:<12.4f} "
              f"{r['ratio']:<10.2f}{marker}")

    # Summary stats
    placebo_ratios = [r['ratio'] for r in results]
    print()
    print(f"Placebo ratio range: {min(placebo_ratios):.2f} - {max(placebo_ratios):.2f}")
    print(f"Placebo ratio mean:  {sum(placebo_ratios)/len(placebo_ratios):.2f}")


if __name__ == "__main__":
    main()
