#!/usr/bin/env python3
"""
TWFE DiD or Synthetic Control for Chicago PPLTT on ChatGPT subscriptions.
Control group: ZIP3s with similar transaction volume to Chicago (606xx Zip codes) in Jan-Jun 2023.
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from load_chatgpt_data import load_with_zip3, log, get_output_dir, get_filter_title, get_outcome_column

# Toggle: False = DiD with inference, True = Synthetic control (just the picture)
USE_SYNTH_CONTROL = False

TREATED_ZIP = '606'
START_DATE = '2023-03-01'  # Drop Feb 2023 (outlier month)
TREATMENT_DATE = '2023-10-01'
END_DATE = '2024-12-01'  # Exclude ChatGPT Pro period
SIZE_WINDOW = 0.1  # Controls must be within 10% of Chicago's size

EVENTS = {
    "ChatGPT Plus": "2023-02-01",
    "9% PPLTT": "2023-10-01",
}


def run_synth_control(trans, donor_zips, chicago_size, size_label):
    """Synthetic control: match pre-period outcomes, plot actual vs synthetic."""
    log("Running synthetic control...")
    outcome_col = get_outcome_column()

    # Monthly aggregations
    trans['month'] = trans['trans_date'].dt.to_period('M')
    monthly = trans.groupby(['zip3', 'month']).agg(
        n_transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        n_users=('cardid', 'nunique')
    ).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()

    # Pivot to wide format (months x zip3s)
    pivot = monthly.pivot(index='month_dt', columns='zip3', values=outcome_col)
    pivot_log = np.log(pivot)
    pivot_log = pivot_log.dropna(subset=[TREATED_ZIP])
    pivot_log = pivot_log[pivot_log.index < END_DATE]

    # Keep donors with complete pre-period data
    pre_mask = pivot_log.index < TREATMENT_DATE
    pre_data = pivot_log[pre_mask]
    valid_donors = [z for z in donor_zips if z in pre_data.columns and pre_data[z].notna().all()]
    log(f"Donors with complete pre-period: {len(valid_donors)}")

    # Fit weights on pre-period
    fit_data = pivot_log[pre_mask][[TREATED_ZIP] + valid_donors].dropna()
    log(f"Pre-period months: {len(fit_data)}")

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

    print("\n" + "="*60)
    print("SYNTHETIC CONTROL WEIGHTS")
    print("="*60)
    print(f"Pre-period RMSE (log {outcome_col}): {np.sqrt(result.fun):.4f}")

    weight_df = pd.DataFrame({'zip3': valid_donors, 'weight': weights})
    weight_df = weight_df[weight_df['weight'] > 0.01].sort_values('weight', ascending=False)
    print("\nTop donors by weight:")
    for _, row in weight_df.iterrows():
        print(f"  {row['zip3']}: {row['weight']:.3f}")
    print(f"\nDonors with weight > 1%: {len(weight_df)}")

    # Compute synthetic for full period
    top_donors = weight_df['zip3'].tolist()
    top_weights = weight_df['weight'].values
    full_data = pivot_log[[TREATED_ZIP] + top_donors].dropna()
    full_data = full_data[full_data.index < END_DATE]
    full_data['synthetic'] = full_data[top_donors].values @ top_weights

    # Plot
    log("Creating plot...")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(full_data.index, full_data[TREATED_ZIP], marker='o', linewidth=2,
            color='blue', label='Chicago (606xx Zip codes)')
    ax.plot(full_data.index, full_data['synthetic'], marker='s', linewidth=2,
            color='orange', linestyle='--', label='Synthetic Control')

    # Shade treatment period
    ax.axvspan(pd.to_datetime(TREATMENT_DATE), full_data.index.max(),
               alpha=0.15, color='red')

    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if full_data.index.min() <= event_dt <= full_data.index.max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

    ax.set_xlabel('Month')
    ax.set_ylabel(f'Log {outcome_col}')
    ax.set_title(f'Synthetic Control: Chicago vs {len(weight_df)} donors {get_filter_title()}')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    # Notes
    top3 = weight_df.head(3)
    weight_note = "Top weights: " + ", ".join([f"{r['zip3']}={r['weight']:.2f}" for _, r in top3.iterrows()])
    control_note = (f"Donors: {len(donor_zips)} ZIP3s within {SIZE_WINDOW*100:.0f}% of Chicago size\n"
                    f"(Chicago had {chicago_size:,.0f} {size_label} in Mar-Jun 2023)\n"
                    f"{weight_note}")
    ax.text(0.02, 0.02, control_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    out_dir = get_output_dir()
    plt.savefig(out_dir / "chicago_synth_control.png", dpi=150, bbox_inches='tight')
    log(f"Saved: {out_dir / 'chicago_synth_control.png'}")

    # Period comparisons
    print("\n" + "="*60)
    print("PERIOD COMPARISONS (log {})".format(outcome_col))
    print("="*60)
    for name, mask in [("Pre-tax (Feb-Sep 2023)", full_data.index < TREATMENT_DATE),
                       ("Post-tax (Oct 2023+)", full_data.index >= TREATMENT_DATE)]:
        subset = full_data[mask]
        if len(subset) > 0:
            diff = subset[TREATED_ZIP].mean() - subset['synthetic'].mean()
            print(f"{name}: Chicago - Synth = {diff:.3f}")


def main():
    trans = load_with_zip3()

    # Select controls based on Feb-Jun 2023 size (post ChatGPT Plus launch)
    # Match on the outcome variable (transactions, spend, or unique users)
    outcome_col = get_outcome_column()
    log(f"Selecting size-matched controls (matching on {outcome_col})...")
    early = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < '2023-07-01')]

    if outcome_col == 'n_users':
        counts = early.groupby('zip3')['cardid'].nunique().reset_index(name='size_metric')
        size_label = 'unique users'
    elif outcome_col == 'total_spend':
        counts = early.groupby('zip3')['trans_amount'].sum().reset_index(name='size_metric')
        size_label = 'total spend'
    else:  # n_transactions
        counts = early.groupby('zip3').size().reset_index(name='size_metric')
        size_label = 'transactions'

    chicago_size = counts[counts['zip3'] == TREATED_ZIP]['size_metric'].values[0]
    lower = chicago_size * (1 - SIZE_WINDOW)
    upper = chicago_size * (1 + SIZE_WINDOW)

    similar = counts[(counts['size_metric'] >= lower) & (counts['size_metric'] <= upper)]
    similar = similar[similar['zip3'] != TREATED_ZIP]  # Exclude Chicago
    similar = similar[similar['zip3'].str.match(r'^\d{3}$')]  # Valid ZIP3s only

    control_zips = similar['zip3'].tolist()
    log(f"Chicago {size_label} (Mar-Jun 2023): {chicago_size}")
    log(f"Control ZIP3s (within {SIZE_WINDOW*100:.0f}%): {len(control_zips)}")

    # Filter to relevant ZIPs
    all_zips = [TREATED_ZIP] + control_zips
    trans = trans[trans['zip3'].isin(all_zips)].copy()

    # Filter to sample period (ChatGPT Plus launch through Nov 2025)
    trans = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < END_DATE)].copy()
    log(f"Sample: {trans['trans_date'].min()} to {trans['trans_date'].max()}")

    # Branch based on method
    if USE_SYNTH_CONTROL:
        run_synth_control(trans, control_zips, chicago_size, size_label)
        return

    # Week-zip3 panel
    log("Creating week-zip3 panel...")
    trans['week'] = trans['trans_date'].dt.to_period('W')
    trans['month'] = trans['trans_date'].dt.to_period('M')

    df = trans.groupby(['zip3', 'week', 'month']).agg(
        n_transactions=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        n_users=('cardid', 'nunique')
    ).reset_index()
    df['week_dt'] = df['week'].dt.to_timestamp()
    df['month_str'] = df['month'].astype(str)

    outcome_col = get_outcome_column()
    df['log_y'] = np.log(df[outcome_col])

    df['treated'] = (df['zip3'] == TREATED_ZIP).astype(int)
    df['post'] = (df['week_dt'] >= TREATMENT_DATE).astype(int)
    df['treated_post'] = df['treated'] * df['post']

    print(f"\nWeek-zip3 obs: {len(df):,}")
    print(f"Weeks: {df['week'].nunique()}")
    print(f"ZIP3s: {df['zip3'].nunique()} (1 treated + {df['zip3'].nunique() - 1} controls)")

    # TWFE with clustered SEs
    print("\n" + "="*60)
    print(f"Y = log({outcome_col})")
    print("FE: zip3, month")
    print("Cluster: zip3")
    print("="*60)

    model = smf.ols('log_y ~ treated_post + C(zip3) + C(month_str)', data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['zip3']}
    )

    print(f"\nTreated × Post: {model.params['treated_post']:.4f}")
    print(f"Clustered SE: {model.bse['treated_post']:.4f}")
    print(f"t-stat: {model.tvalues['treated_post']:.2f}")
    print(f"p-value: {model.pvalues['treated_post']:.4f}")
    print(f"N = {int(model.nobs):,}, clusters = {df['zip3'].nunique()}")

    # Event study by month
    print("\n" + "="*60)
    print("EVENT STUDY (by month)")
    print("="*60)

    months_sorted = sorted(df['month_str'].unique())
    ref_month = '2023-09'

    month_to_var = {}
    for m in months_sorted:
        if m != ref_month:
            var = f'treat_{m.replace("-", "_")}'
            month_to_var[m] = var
            df[var] = ((df['zip3'] == TREATED_ZIP) & (df['month_str'] == m)).astype(int)

    interact_vars = [month_to_var[m] for m in months_sorted if m != ref_month]
    formula = 'log_y ~ ' + ' + '.join(interact_vars) + ' + C(zip3) + C(month_str)'

    model_es = smf.ols(formula, data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['zip3']}
    )

    es_coefs = []
    for m in months_sorted:
        if m == ref_month:
            es_coefs.append({'month': m, 'coef': 0, 'se': 0})
        else:
            var = month_to_var[m]
            es_coefs.append({'month': m, 'coef': model_es.params[var], 'se': model_es.bse[var]})

    es_df = pd.DataFrame(es_coefs)
    es_df['month_dt'] = pd.to_datetime(es_df['month'])
    es_df = es_df.sort_values('month_dt')

    # Plot
    log("Creating plot...")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.errorbar(es_df['month_dt'], es_df['coef'], yerr=1.96*es_df['se'],
                fmt='o-', color='blue', capsize=3)
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)

    # Shade treatment period (9% tax)
    ax.axvspan(pd.to_datetime(TREATMENT_DATE), es_df['month_dt'].max(),
               alpha=0.15, color='red')

    for event, date in EVENTS.items():
        event_dt = pd.to_datetime(date)
        if es_df['month_dt'].min() <= event_dt <= es_df['month_dt'].max():
            ax.axvline(event_dt, color='red', linestyle='--', alpha=0.7)
            ax.text(event_dt, ax.get_ylim()[1], event, rotation=90, va='top', fontsize=9, color='red')

    ax.set_xlabel('Month')
    # Clarify units based on outcome variable
    if outcome_col == 'n_users':
        y_label = 'Chicago × Month coefficient\n(Y = log unique cardids with $15-25 transaction)'
        title_outcome = 'unique users'
    elif outcome_col == 'total_spend':
        y_label = 'Chicago × Month coefficient\n(Y = log total spend on $15-25 transactions)'
        title_outcome = 'total spend'
    else:
        y_label = 'Chicago × Month coefficient\n(Y = log count of $15-25 transactions)'
        title_outcome = 'transactions'
    ax.set_ylabel(y_label, fontsize=10)
    ax.set_title(f'Event Study: {title_outcome}, {len(control_zips)} controls {get_filter_title()}')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    # Add control group description and treatment definition
    # Clarify that "user" = cardid with $15-25 transaction
    if outcome_col == 'n_users':
        size_clarify = f"{size_label} (cardids with $15-25 trans)"
    else:
        size_clarify = size_label
    control_note = (f"Controls: {len(control_zips)} ZIP3s matched on {size_clarify}\n"
                    f"within {SIZE_WINDOW*100:.0f}% of Chicago in Mar-Jun 2023\n"
                    f"(Chicago: {chicago_size:,.0f}; ref month = Sep 2023)\n"
                    f"Post = 1 for Chicago starting Oct 2023 (9% PPLTT)")
    ax.text(0.02, 0.02, control_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Add TWFE estimate
    twfe_note = f"TWFE: β = {model.params['treated_post']:.3f} (SE = {model.bse['treated_post']:.3f})"
    ax.text(0.98, 0.02, twfe_note, transform=ax.transAxes, fontsize=9, fontweight='bold',
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

    plt.tight_layout()
    out_dir = get_output_dir()
    plt.savefig(out_dir / "chicago_did.png", dpi=150, bbox_inches='tight')
    log(f"Saved: {out_dir / 'chicago_did.png'}")

    print("\nPre-treatment:")
    for _, row in es_df[es_df['month_dt'] < TREATMENT_DATE].iterrows():
        sig = "*" if abs(row['coef']) > 1.96 * row['se'] and row['se'] > 0 else ""
        print(f"  {row['month']}: {row['coef']:+.3f} (se={row['se']:.3f}) {sig}")

    print("\nPost-treatment:")
    for _, row in es_df[es_df['month_dt'] >= TREATMENT_DATE].iterrows():
        sig = "*" if abs(row['coef']) > 1.96 * row['se'] and row['se'] > 0 else ""
        print(f"  {row['month']}: {row['coef']:+.3f} (se={row['se']:.3f}) {sig}")

    # Pre-trends F-test (exclude Dec 2022 which has only 1 Chicago obs)
    print("\n" + "="*60)
    print("PRE-TRENDS TEST")
    print("="*60)
    pre_months = [m for m in months_sorted if m >= '2023-01' and m < '2023-10' and m != ref_month]
    pre_vars = [month_to_var[m] for m in pre_months]
    pre_coefs = np.array([model_es.params[v] for v in pre_vars])

    # Wald test
    r_matrix = np.zeros((len(pre_vars), len(model_es.params)))
    for i, v in enumerate(pre_vars):
        r_matrix[i, list(model_es.params.index).index(v)] = 1

    wald = model_es.wald_test(r_matrix, use_f=True, scalar=True)
    print(f"Joint F-test (H0: all pre-treatment coefs = 0):")
    print(f"  F({len(pre_vars)}, {int(model_es.df_resid)}): {wald.statistic:.3f}")
    print(f"  p-value: {wald.pvalue:.4f}")
    print(f"\nPre-trend coef range: [{pre_coefs.min():.3f}, {pre_coefs.max():.3f}]")
    print(f"Mean |pre-trend coef|: {np.abs(pre_coefs).mean():.3f}")


if __name__ == "__main__":
    main()
