#!/usr/bin/env python3
"""
TWFE DiD for Chicago PPLTT on ChatGPT subscriptions.
Control group: ZIP3s with similar transaction volume to Chicago (606) in Jan-Jun 2023.
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
OUTPUT_DIR = Path(__file__).parent

TREATED_ZIP = '606'
START_DATE = '2023-02-01'  # ChatGPT Plus launch
TREATMENT_DATE = '2023-10-01'
END_DATE = '2025-01-01'  # Exclude 11% period
SIZE_WINDOW = 0.5  # Controls must be within 50% of Chicago's size

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

    # Select controls based on Feb-Jun 2023 size (post ChatGPT Plus launch)
    log("Selecting size-matched controls...")
    early = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < '2023-07-01')]
    counts = early.groupby('zip3').size().reset_index(name='n_trans')

    chicago_size = counts[counts['zip3'] == TREATED_ZIP]['n_trans'].values[0]
    lower = chicago_size * (1 - SIZE_WINDOW)
    upper = chicago_size * (1 + SIZE_WINDOW)

    similar = counts[(counts['n_trans'] >= lower) & (counts['n_trans'] <= upper)]
    similar = similar[similar['zip3'] != TREATED_ZIP]  # Exclude Chicago
    similar = similar[similar['zip3'].str.match(r'^\d{3}$')]  # Valid ZIP3s only

    control_zips = similar['zip3'].tolist()
    log(f"Chicago size (Jan-Jun 2023): {chicago_size}")
    log(f"Control ZIP3s (within {SIZE_WINDOW*100:.0f}%): {len(control_zips)}")

    # Filter to relevant ZIPs
    all_zips = [TREATED_ZIP] + control_zips
    trans = trans[trans['zip3'].isin(all_zips)].copy()

    # Filter to sample period (ChatGPT Plus launch through Nov 2025)
    trans = trans[(trans['trans_date'] >= START_DATE) & (trans['trans_date'] < END_DATE)].copy()
    log(f"Sample: {trans['trans_date'].min()} to {trans['trans_date'].max()}")

    # Week-zip3 panel
    log("Creating week-zip3 panel...")
    trans['week'] = trans['trans_date'].dt.to_period('W')
    trans['month'] = trans['trans_date'].dt.to_period('M')

    df = trans.groupby(['zip3', 'week', 'month']).size().reset_index(name='n_trans')
    df['week_dt'] = df['week'].dt.to_timestamp()
    df['month_str'] = df['month'].astype(str)

    df['log_trans'] = np.log(df['n_trans'])

    df['treated'] = (df['zip3'] == TREATED_ZIP).astype(int)
    df['post'] = (df['week_dt'] >= TREATMENT_DATE).astype(int)
    df['treated_post'] = df['treated'] * df['post']

    print(f"\nWeek-zip3 obs: {len(df):,}")
    print(f"Weeks: {df['week'].nunique()}")
    print(f"ZIP3s: {df['zip3'].nunique()} (1 treated + {df['zip3'].nunique() - 1} controls)")

    # TWFE with clustered SEs
    print("\n" + "="*60)
    print("Y = log(transactions)")
    print("FE: zip3, month")
    print("Cluster: zip3")
    print("="*60)

    model = smf.ols('log_trans ~ treated_post + C(zip3) + C(month_str)', data=df).fit(
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
    formula = 'log_trans ~ ' + ' + '.join(interact_vars) + ' + C(zip3) + C(month_str)'

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
    ax.set_ylabel('Chicago × Month (ref = Sep 2023)')
    ax.set_title(f'Event Study: log(transactions), {len(control_zips)} size-matched controls')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    # Add control group description and treatment definition
    control_note = (f"Controls: {len(control_zips)} ZIP3s with transaction counts\n"
                    f"within {SIZE_WINDOW*100:.0f}% of Chicago (606) in Feb-Jun 2023\n"
                    f"(Chicago had {chicago_size} transactions)\n"
                    f"Post = 1 for Chicago starting Oct 2023 (9% PPLTT)")
    ax.text(0.02, 0.02, control_note, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chicago_did.png", dpi=150, bbox_inches='tight')
    log("Saved: chicago_did.png")

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
