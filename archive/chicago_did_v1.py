#!/usr/bin/env python3
"""
TWFE DiD for Chicago PPLTT on ChatGPT subscriptions.
Week-zip3 level, transactions per 100k population, month FE, cluster at zip3.

Usage:
    python chicago_did.py                  # without trend
    python chicago_did.py --trend          # with Chicago-specific linear trend
"""

import argparse
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")
POP_FILE = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/derived_data/zip3_populations_acs2022.csv")
OUTPUT_DIR = Path(__file__).parent

TREATED_ZIP = '606'
CONTROL_ZIPS = ['600', '601', '602', '604', '605']
TREATMENT_DATE = '2023-10-01'
END_DATE = '2025-01-01'


def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main(include_trend=False):
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

    all_zips = [TREATED_ZIP] + CONTROL_ZIPS
    trans = trans[trans['zip3'].astype(str).isin(all_zips)].copy()
    trans['zip3'] = trans['zip3'].astype(str)
    log(f"Filtered to zips {all_zips}: {len(trans):,} transactions")

    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['week'] = trans['trans_date'].dt.to_period('W')
    trans['month'] = trans['trans_date'].dt.to_period('M')

    # Filter to sample period
    trans = trans[trans['trans_date'] < END_DATE].copy()
    log(f"Sample: {trans['trans_date'].min()} to {trans['trans_date'].max()}")

    # Week-zip3 panel
    log("Creating week-zip3 panel...")
    df = trans.groupby(['zip3', 'week', 'month']).size().reset_index(name='n_trans')
    df['week_dt'] = df['week'].dt.to_timestamp()
    df['month_str'] = df['month'].astype(str)

    df['log_trans'] = np.log(df['n_trans'])

    df['treated'] = (df['zip3'] == TREATED_ZIP).astype(int)
    df['post'] = (df['week_dt'] >= TREATMENT_DATE).astype(int)
    df['treated_post'] = df['treated'] * df['post']

    # Time trend (weeks since start)
    df['t'] = (df['week_dt'] - df['week_dt'].min()).dt.days / 7
    df['treated_trend'] = df['treated'] * df['t']

    print(f"\nWeek-zip3 obs: {len(df):,}")
    print(f"Weeks: {df['week'].nunique()}")

    # TWFE with clustered SEs
    print("\n" + "="*60)
    print("Y = log(transactions)")
    print("FE: zip3, month")
    print("Cluster: zip3")
    print("="*60)

    model = smf.ols('log_trans ~ treated_post + C(zip3) + C(month_str)', data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['zip3']}
    )

    print(f"\n--- Without Chicago trend ---")
    print(f"Treated × Post: {model.params['treated_post']:.4f} (se={model.bse['treated_post']:.4f}, p={model.pvalues['treated_post']:.4f})")

    # With Chicago-specific trend
    model_trend = smf.ols('log_trans ~ treated_post + treated_trend + C(zip3) + C(month_str)', data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['zip3']}
    )

    print(f"\n--- With Chicago trend ---")
    print(f"Treated × Post: {model_trend.params['treated_post']:.4f} (se={model_trend.bse['treated_post']:.4f}, p={model_trend.pvalues['treated_post']:.4f})")
    print(f"Treated × t:    {model_trend.params['treated_trend']:.4f} (se={model_trend.bse['treated_trend']:.4f}, p={model_trend.pvalues['treated_trend']:.4f})")

    print(f"\nTreated × Post: {model.params['treated_post']:.4f}")
    print(f"Clustered SE: {model.bse['treated_post']:.4f}")
    print(f"t-stat: {model.tvalues['treated_post']:.2f}")
    print(f"p-value: {model.pvalues['treated_post']:.4f}")
    print(f"N = {int(model.nobs):,}, clusters = 6")

    # Event study by month
    print("\n" + "="*60)
    trend_label = " (with Chicago trend)" if include_trend else ""
    print(f"EVENT STUDY (by month){trend_label}")
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
    if include_trend:
        formula = 'log_trans ~ treated_trend + ' + ' + '.join(interact_vars) + ' + C(zip3) + C(month_str)'
    else:
        formula = 'log_trans ~ ' + ' + '.join(interact_vars) + ' + C(zip3) + C(month_str)'

    model_es = smf.ols(formula, data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['zip3']}
    )

    if include_trend:
        print(f"Treated × t: {model_es.params['treated_trend']:.4f} (se={model_es.bse['treated_trend']:.4f})")

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
    ax.axvline(pd.to_datetime(TREATMENT_DATE), color='red', linestyle='--', alpha=0.7)
    ax.text(pd.to_datetime(TREATMENT_DATE), ax.get_ylim()[1] * 0.9, '9% PPLTT',
            rotation=90, va='top', fontsize=10, color='red')

    ax.set_xlabel('Month')
    ax.set_ylabel('Chicago × Month (ref = Sep 2023)')
    title = 'Event Study: log(transactions)'
    if include_trend:
        title += ' (with Chicago trend)'
    ax.set_title(title)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    output_file = "chicago_did_trend.png" if include_trend else "chicago_did.png"
    plt.savefig(OUTPUT_DIR / output_file, dpi=150, bbox_inches='tight')
    log(f"Saved: {output_file}")

    print("\nPre-treatment:")
    for _, row in es_df[es_df['month_dt'] < TREATMENT_DATE].iterrows():
        sig = "*" if abs(row['coef']) > 1.96 * row['se'] and row['se'] > 0 else ""
        print(f"  {row['month']}: {row['coef']:+.3f} (se={row['se']:.3f}) {sig}")

    print("\nPost-treatment:")
    for _, row in es_df[es_df['month_dt'] >= TREATMENT_DATE].iterrows():
        sig = "*" if abs(row['coef']) > 1.96 * row['se'] and row['se'] > 0 else ""
        print(f"  {row['month']}: {row['coef']:+.3f} (se={row['se']:.3f}) {sig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TWFE DiD for Chicago PPLTT')
    parser.add_argument('--trend', action='store_true', help='Include Chicago-specific linear trend in event study')
    args = parser.parse_args()
    main(include_trend=args.trend)
