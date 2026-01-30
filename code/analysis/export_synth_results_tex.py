#!/usr/bin/env python3
"""
Export synthetic control results to LaTeX macros.
Reads synth_results.dta, synth_donor_weights.csv, Stata log, and panel data.

Output: memos/synth_macros.tex (use \input{synth_macros.tex} in your doc)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from load_chatgpt_data import get_output_dir, get_exploratory_dir, get_outcome_label, log


# Covariate display names for balance table
COVARIATE_NAMES = {
    'pct_college': r'\% college',
    'pct_hh_100k': r'\% HH income $>$\$100k',
    'pct_young': r'\% ages 18--34',
    'median_age': 'Median age',
    'median_income': 'Median income',
    'pct_stem': r'\% STEM',
    'pct_broadband': r'\% broadband',
    'pre_mean_early': 'Log users (Mar--Jun)',
    'pre_mean_late': 'Log users (Jul--Sep)',
    'pre_median_price': 'Median price (pre)',
}

# ZIP3 to area name mapping (for donor weights table)
ZIP3_NAMES = {
    '900': 'Los Angeles, CA',
    '277': 'Raleigh, NC',
    '830': 'Wyoming',
    '785': 'Rio Grande Valley, TX',
    '865': 'Flagstaff, AZ',
    '303': 'Atlanta, GA',
    '100': 'Manhattan, NY',
    '606': 'Chicago, IL',
    '943': 'Palo Alto, CA',
    '786': 'Austin, TX',
    '738': 'Tulsa, OK',
    '273': 'Greensboro, NC',
    '247': 'Roanoke, VA',
    '348': 'Macon, GA',
    '765': 'Lafayette, IN',
    '715': 'Eau Claire, WI',
    '527': 'Rochester, MN',
    '631': 'Nassau, NY',
    '258': 'Beckley, WV',
    '387': 'Columbus, GA',
    '588': 'Rapid City, SD',
    '711': 'Shreveport, LA',
    '803': 'Columbia, SC',
    '288': 'Asheville, NC',
    '077': 'Long Branch, NJ',
}


def parse_covariate_balance(log_path):
    """Parse covariate balance table from Stata log."""
    if not log_path.exists():
        return None

    text = log_path.read_text()

    # Find the balance table section
    idx = text.find('Predictor Balance:')
    if idx < 0:
        return None

    # Extract lines until we hit a line starting with many dashes after data
    section = text[idx:idx + 2000]
    lines = section.split('\n')

    rows = []
    in_data = False
    for line in lines:
        # Skip until we pass the header separator
        if '---+---' in line:
            in_data = True
            continue
        # Stop at closing dashes
        if in_data and line.strip().startswith('---') and '|' not in line:
            break
        if not in_data:
            continue
        # Parse: "varname | treated synthetic"
        if '|' not in line:
            continue
        parts = line.split('|')
        if len(parts) != 2:
            continue
        varname = parts[0].strip()
        values = parts[1].split()
        if len(values) >= 2:
            try:
                treated = float(values[0])
                synthetic = float(values[1])
                rows.append((varname, treated, synthetic))
            except ValueError:
                continue

    return rows if rows else None


def compute_price_stats(panel_path, treatment_month=10):
    """Compute Chicago price statistics from panel data."""
    if not panel_path.exists():
        return None

    df = pd.read_stata(panel_path)
    chi = df[df['zip3'] == '606']

    pre = chi[chi['month_num'] < treatment_month]
    post = chi[chi['month_num'] >= treatment_month]

    return {
        'pre_median': pre['median_price'].mean(),
        'post_median': post['median_price'].mean(),
        'oct_price': chi[chi['month_num'] == 10]['median_price'].values[0],
    }


def compute_placebo_pvalue(outdir, chicago_ratio, threshold_mult=5):
    """Compute placebo p-value from placebo results."""
    placebo_path = outdir / 'placebo_rmspe_results.csv'
    if not placebo_path.exists():
        return None, None, None

    df = pd.read_csv(placebo_path)

    # Get Chicago's pre-RMSPE for threshold
    chicago_pre = df[df['zip3'] == 606]['pre_rmspe'].values
    if len(chicago_pre) == 0:
        return None, None, None
    chicago_pre = chicago_pre[0]

    # Filter to good pre-fit (threshold_mult times Chicago's)
    threshold = chicago_pre * threshold_mult
    good_fit = df[df['pre_rmspe'] < threshold]

    n_placebos = len(good_fit)
    n_extreme = (good_fit['rmspe_ratio'] >= chicago_ratio).sum()
    pvalue = n_extreme / n_placebos if n_placebos > 0 else None

    return pvalue, n_placebos, n_extreme


def main():
    outdir = get_output_dir()
    log(f"Output dir: {outdir}")

    # Read synth results
    results_path = outdir / 'synth_results.dta'
    if not results_path.exists():
        raise FileNotFoundError(f"Run chicago_synth.do first: {results_path}")

    results = pd.read_stata(results_path)
    results['gap'] = results['_Y_treated'] - results['_Y_synthetic']
    results['gap_sq'] = results['gap'] ** 2

    # RMSPE calculations
    pre = results[results['_time'] < 10]
    post = results[results['_time'] >= 10]

    pre_rmspe = np.sqrt(pre['gap_sq'].mean())
    post_rmspe = np.sqrt(post['gap_sq'].mean())
    rmspe_ratio = post_rmspe / pre_rmspe

    # Gaps
    pre_gap_mean = pre['gap'].mean()
    post_gap_mean = post['gap'].mean()

    # Effect size (percentage)
    effect_pct = (np.exp(post_gap_mean) - 1) * 100

    log(f"Pre-RMSPE: {pre_rmspe:.3f}")
    log(f"Post-RMSPE: {post_rmspe:.3f}")
    log(f"Ratio: {rmspe_ratio:.2f}")
    log(f"Post-gap mean: {post_gap_mean:.3f} ({effect_pct:.1f}%)")

    # Read donor weights
    weights_path = outdir / 'synth_donor_weights.csv'
    if weights_path.exists():
        weights = pd.read_csv(weights_path)
        weights = weights.sort_values('weight', ascending=False)
        top_donors = weights[weights['weight'] >= 0.01].head(10)
        log(f"Top donors: {len(top_donors)}")
    else:
        top_donors = pd.DataFrame()
        log("No donor weights file found")

    # Generate LaTeX macros
    macros = []
    macros.append("% Auto-generated by export_synth_results_tex.py")
    macros.append("% Do not edit - regenerate by running the script")
    macros.append("")
    macros.append("% RMSPE values")
    macros.append(f"\\newcommand{{\\preRMSPE}}{{{pre_rmspe:.3f}}}")
    macros.append(f"\\newcommand{{\\postRMSPE}}{{{post_rmspe:.3f}}}")
    macros.append(f"\\newcommand{{\\rmspeRatio}}{{{rmspe_ratio:.2f}}}")
    macros.append("")
    macros.append("% Gap values")
    macros.append(f"\\newcommand{{\\preGapMean}}{{{pre_gap_mean:.3f}}}")
    macros.append(f"\\newcommand{{\\postGapMean}}{{{post_gap_mean:.3f}}}")
    macros.append(f"\\newcommand{{\\effectPct}}{{{abs(effect_pct):.0f}}}")
    macros.append("")

    # Donor weights table
    if not top_donors.empty:
        macros.append("% Top donor weights")
        rows = []
        for _, row in top_donors.iterrows():
            zip3 = str(int(row['zip3'])).zfill(3)
            weight_pct = row['weight'] * 100
            area = ZIP3_NAMES.get(zip3, 'Unknown')
            rows.append(f"{zip3} & {weight_pct:.1f}\\% & {area} \\\\")

        macros.append("\\newcommand{\\donorWeightsRows}{%")
        macros.append("\n".join(rows))
        macros.append("}")
        macros.append(f"\\newcommand{{\\nDonors}}{{{len(weights)}}}")
        macros.append(f"\\newcommand{{\\nTopDonors}}{{{len(top_donors)}}}")

    # Covariate balance from Stata log
    repo_dir = Path(__file__).parent.parent.parent  # code/analysis -> code -> repo root
    log_path = repo_dir / 'chicago_synth.log'
    balance = parse_covariate_balance(log_path)
    if balance:
        macros.append("")
        macros.append("% Covariate balance")
        balance_rows = []
        for varname, treated, synthetic in balance:
            display_name = COVARIATE_NAMES.get(varname, varname)
            # Format: income in thousands, others as-is
            if varname == 'median_income':
                balance_rows.append(
                    f"{display_name} & \\${treated/1000:,.0f}k "
                    f"& \\${synthetic/1000:,.0f}k \\\\"
                )
            elif 'pct' in varname:
                balance_rows.append(
                    f"{display_name} & {treated*100:.1f}\\% "
                    f"& {synthetic*100:.1f}\\% \\\\"
                )
            elif varname == 'pre_median_price':
                balance_rows.append(
                    f"{display_name} & \\${treated:.2f} "
                    f"& \\${synthetic:.2f} \\\\"
                )
            else:
                balance_rows.append(
                    f"{display_name} & {treated:.2f} & {synthetic:.2f} \\\\"
                )
        macros.append("\\newcommand{\\covBalanceRows}{%")
        macros.append("\n".join(balance_rows))
        macros.append("}")
        log(f"Parsed {len(balance)} covariate balance rows")

    # Price statistics from panel data
    panel_path = repo_dir / 'data' / 'synth_panel.dta'
    price_stats = compute_price_stats(panel_path)
    if price_stats:
        macros.append("")
        macros.append("% Price statistics")
        macros.append(
            f"\\newcommand{{\\chiPrePrice}}"
            f"{{{price_stats['pre_median']:.2f}}}"
        )
        macros.append(
            f"\\newcommand{{\\chiPostPrice}}"
            f"{{{price_stats['post_median']:.2f}}}"
        )
        macros.append(
            f"\\newcommand{{\\chiOctPrice}}"
            f"{{{price_stats['oct_price']:.2f}}}"
        )
        log(f"Price: pre=${price_stats['pre_median']:.2f}, "
            f"post=${price_stats['post_median']:.2f}")

    # Placebo p-value (if available)
    pvalue, n_placebos, n_extreme = compute_placebo_pvalue(
        outdir, rmspe_ratio, threshold_mult=5
    )
    if pvalue is not None:
        macros.append("")
        macros.append("% Placebo inference")
        macros.append(f"\\newcommand{{\\placeboPvalue}}{{{pvalue:.3f}}}")
        macros.append(f"\\newcommand{{\\nPlacebos}}{{{n_placebos}}}")
        macros.append(f"\\newcommand{{\\nExtreme}}{{{n_extreme}}}")
        log(f"Placebo p-value: {pvalue:.3f} ({n_extreme}/{n_placebos})")

    # Write to file
    memo_dir = Path(__file__).parent.parent.parent / 'memos'
    out_path = memo_dir / 'synth_macros.tex'
    out_path.write_text("\n".join(macros))
    log(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
