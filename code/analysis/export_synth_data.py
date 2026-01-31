#!/usr/bin/env python3
"""
Export ZIP3-month panel with demographics for Stata synth.

Output: data/synth_panel.dta
- Panel: ZIP3 × month
- Synth outcomes: log_trans (current), log_users (legacy)
- Spaghetti plot: users_pc (users/population) - comparable across ZIP3s
- Cross-section: ZIP3-level demographics for covariate matching
"""

import pandas as pd
import numpy as np
from pathlib import Path
from load_chatgpt_data import (load_with_zip3, log, get_log_outcome_column,
                               get_outcome_label, get_output_dir)

TREATED_ZIP = '606'
START_DATE = '2023-03-01'
END_DATE = '2024-12-01'
TREATMENT_DATE = '2023-10-01'


def main():
    # Load transactions
    trans = load_with_zip3()
    trans = trans[
        (trans['trans_date'] >= START_DATE) &
        (trans['trans_date'] < END_DATE)
    ].copy()
    log(f"Transactions: {len(trans):,}")

    # Aggregate to ZIP3-month
    trans['month'] = trans['trans_date'].dt.to_period('M')
    monthly = trans.groupby(['zip3', 'month']).agg(
        n_users=('cardid', 'nunique'),
        n_trans=('trans_amount', 'count'),
        total_spend=('trans_amount', 'sum'),
        median_price=('trans_amount', 'median')
    ).reset_index()

    # Convert month to integer (months since 2023-01)
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()
    base_month = pd.Timestamp('2023-01-01')
    monthly['month_num'] = (
        (monthly['month_dt'].dt.year - 2023) * 12 +
        monthly['month_dt'].dt.month
    )

    # Per-capita outcome (following Abadie et al. 2010)
    # Will compute after merging demographics (need population)

    # Treatment indicators
    treatment_month = 10  # October 2023
    monthly['treated'] = (monthly['zip3'] == TREATED_ZIP).astype(int)
    monthly['post'] = (monthly['month_num'] >= treatment_month).astype(int)

    # Pre-period median price (months 3-9, Mar-Sep 2023)
    pre_period = monthly[(monthly['month_num'] >= 3) & (monthly['month_num'] <= 9)]
    pre_median_price = pre_period.groupby('zip3')['median_price'].mean().reset_index()
    pre_median_price.columns = ['zip3', 'pre_median_price']
    monthly = monthly.merge(pre_median_price, on='zip3', how='left')
    log(f"Added pre_median_price for {len(pre_median_price)} ZIP3s")

    # Load demographics
    demo_path = Path(__file__).parent.parent.parent / 'data' / 'zip3_demographics_acs2022.parquet'
    demo = pd.read_parquet(demo_path)
    log(f"Demographics: {len(demo)} ZIP3s")

    # Keep all covariates
    demo = demo[['zip3', 'pct_college', 'pct_hh_100k', 'pct_young',
                 'median_age', 'median_income', 'pct_stem', 'pct_broadband',
                 'population']]

    # Merge
    panel = monthly.merge(demo, on='zip3', how='left')
    panel = panel.dropna(subset=['pct_college', 'pct_hh_100k', 'pct_young',
                                  'median_age', 'median_income', 'pct_stem', 'pct_broadband'])
    log(f"Panel after demo merge: {len(panel):,} obs")

    # Synth outcomes: log(users) and log(transactions)
    panel['log_users'] = np.log(panel['n_users'])
    panel['log_trans'] = np.log(panel['n_trans'])

    # Spaghetti plot: users per capita (comparable across ZIP3s)
    panel['users_pc'] = panel['n_users'] / panel['population']

    # Create numeric ZIP3 ID for Stata
    zip3_list = sorted(panel['zip3'].unique())
    zip3_to_id = {z: i+1 for i, z in enumerate(zip3_list)}
    panel['zip3_id'] = panel['zip3'].map(zip3_to_id)

    # Chicago's ID
    chicago_id = zip3_to_id.get(TREATED_ZIP)
    log(f"Chicago ZIP3 ID: {chicago_id}")
    log(f"Total ZIP3s: {len(zip3_list)}")

    # Keep relevant columns
    panel = panel[[
        'zip3', 'zip3_id', 'month_num', 'month_dt',
        'n_users', 'log_users', 'n_trans', 'log_trans',
        'users_pc', 'total_spend',
        'median_price', 'pre_median_price',
        'treated', 'post',
        'pct_college', 'pct_hh_100k', 'pct_young',
        'median_age', 'median_income', 'pct_stem', 'pct_broadband',
        'population'
    ]]

    # Sort
    panel = panel.sort_values(['zip3_id', 'month_num'])

    # Save
    out_dir = Path(__file__).parent.parent.parent / 'data'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'synth_panel.dta'
    panel.to_stata(out_path, write_index=False, version=118)
    log(f"Saved: {out_path}")

    # Summary
    print("\n" + "="*60)
    print("PANEL SUMMARY")
    print("="*60)
    print(f"ZIP3s: {panel['zip3_id'].nunique()}")
    print(f"Months: {panel['month_num'].min()} to {panel['month_num'].max()}")
    print(f"Obs: {len(panel):,}")
    print(f"\nChicago (zip3_id={chicago_id}):")
    chi = panel[panel['zip3'] == TREATED_ZIP].iloc[0]
    print(f"  pct_college:      {chi['pct_college']:.3f}")
    print(f"  pct_hh_100k:      {chi['pct_hh_100k']:.3f}")
    print(f"  pct_young:        {chi['pct_young']:.3f}")
    print(f"  pre_median_price: ${chi['pre_median_price']:.2f}")

    # Save ZIP3 ID mapping for reference
    map_df = pd.DataFrame([
        {'zip3': z, 'zip3_id': i}
        for z, i in zip3_to_id.items()
    ])
    map_path = out_dir / 'zip3_id_mapping.csv'
    map_df.to_csv(map_path, index=False)
    log(f"Saved ID mapping: {map_path}")

    # Write Stata config file (single source of truth for outcome)
    config_path = out_dir / 'synth_config.do'
    outcome_var = get_log_outcome_column()
    outcome_label = get_outcome_label()
    outdir = get_output_dir()
    with open(config_path, 'w') as f:
        f.write(f'* Auto-generated by export_synth_data.py\n')
        f.write(f'* DO NOT EDIT - change settings in load_chatgpt_data.py\n\n')
        f.write(f'global outcome_var "{outcome_var}"\n')
        f.write(f'global outcome_label "{outcome_label}"\n')
        f.write(f'global outdir "{outdir}"\n')
    log(f"Saved Stata config: {config_path}")


if __name__ == "__main__":
    main()
