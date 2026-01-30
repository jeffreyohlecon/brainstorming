#!/usr/bin/env python3
"""
Create Abadie-style raw data plot: Chicago vs rest of US.
Shows log(monthly unique users) over time.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from load_chatgpt_data import (
    load_with_zip3, get_output_dir, log
)

def main():
    # Load data
    trans = load_with_zip3()

    # Create year-month
    trans['ym'] = trans['trans_date'].dt.to_period('M')

    # Restrict to analysis window: March 2023 - November 2024
    trans = trans[
        (trans['ym'] >= pd.Period('2023-03', freq='M')) &
        (trans['ym'] <= pd.Period('2024-11', freq='M'))
    ]
    log(f"After date filter (Mar 2023 - Nov 2024): {len(trans):,}")

    # Chicago = ZIP3 606
    chi_trans = trans[trans['zip3'] == '606']
    rest_trans = trans[trans['zip3'] != '606']

    # Aggregate: unique users per month
    chicago = (
        chi_trans
        .groupby('ym')
        .agg(n_users=('cardid', 'nunique'))
        .reset_index()
    )
    chicago['date'] = chicago['ym'].dt.to_timestamp()
    chicago['log_users'] = np.log(chicago['n_users'])

    rest = (
        rest_trans
        .groupby('ym')
        .agg(n_users=('cardid', 'nunique'))
        .reset_index()
    )
    rest['date'] = rest['ym'].dt.to_timestamp()
    rest['log_users'] = np.log(rest['n_users'])

    # Plot with two y-axes (different scales)
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(chicago['date'], chicago['log_users'],
             'k-', linewidth=2, label='Chicago')
    ax1.set_ylabel('Chicago: log(unique users)', fontsize=11)
    ax1.tick_params(axis='y')

    ax2 = ax1.twinx()
    ax2.plot(rest['date'], rest['log_users'],
             'k--', linewidth=2, label='rest of U.S.')
    ax2.set_ylabel('Rest of U.S.: log(unique users)', fontsize=11)
    ax2.tick_params(axis='y')

    # Vertical line at treatment (October 2023)
    ax1.axvline(pd.Timestamp('2023-10-01'), color='gray',
                linestyle=':', linewidth=1)
    ax1.text(pd.Timestamp('2023-10-15'), chicago['log_users'].min() + 0.05,
             'PPLTT  →', fontsize=9, ha='left')

    ax1.set_xlabel('month', fontsize=11)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper left', frameon=True)

    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)

    plt.tight_layout()

    # Save to exploratory
    out_dir = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/exploratory')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'chicago_vs_rest_raw.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    log(f"Saved: {out_path}")

    plt.close()

if __name__ == '__main__':
    main()
