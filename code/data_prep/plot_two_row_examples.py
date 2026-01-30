#!/usr/bin/env python3
"""Plot representative 2-row cardids showing ZIP timeline."""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
DROPBOX_OUT = '/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/trans/15to25/all_merchants'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'

def main():
    print("Loading address_map...")
    tv = pd.read_parquet(TV_PATH)
    tv['valid_begin'] = pd.to_datetime(tv['valid_begin'])
    tv['valid_end'] = pd.to_datetime(tv['valid_end'])

    # Find 2-row cardids with different ZIPs (real movers)
    counts = tv.groupby('cardid').size()
    two_row_cardids = counts[counts == 2].index.tolist()

    # Find movers vs same-zip
    movers = []
    same_zip = []

    for cardid in two_row_cardids[:10000]:
        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')
        r1, r2 = rows.iloc[0], rows.iloc[1]
        if str(r1['zip']) != str(r2['zip']):
            movers.append(cardid)
        else:
            same_zip.append(cardid)

    print(f"In first 10k 2-row cardids:")
    print(f"  Movers (diff ZIP): {len(movers):,}")
    print(f"  Same ZIP: {len(same_zip):,}")

    # Plot 6 examples: 3 movers, 3 same-zip
    random.seed(42)
    examples = random.sample(movers[:500], 3) + random.sample(same_zip[:500], 3)

    fig, axes = plt.subplots(2, 3, figsize=(14, 6))
    axes = axes.flatten()

    colors = plt.cm.Set2.colors

    for idx, cardid in enumerate(examples):
        ax = axes[idx]
        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')

        # Get unique ZIPs for color mapping
        zips = rows['zip'].astype(str).unique()
        zip_colors = {z: colors[i % len(colors)] for i, z in enumerate(zips)}

        for _, row in rows.iterrows():
            z = str(row['zip'])
            ax.barh(
                y=0,
                width=(row['valid_end'] - row['valid_begin']).days,
                left=row['valid_begin'],
                height=0.5,
                color=zip_colors[z],
                edgecolor='black',
                linewidth=0.5
            )
            # Label
            mid = row['valid_begin'] + (row['valid_end'] - row['valid_begin']) / 2
            ax.text(mid, 0, z, ha='center', va='center',
                    fontsize=10, fontweight='bold')

        # Treatment line
        ax.axvline(pd.Timestamp('2023-10-01'), color='red',
                   ls='--', alpha=0.7, label='Oct 2023')

        ax.set_xlim(pd.Timestamp('2022-01-01'), pd.Timestamp('2025-07-01'))
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])

        is_mover = idx < 3
        ax.set_title(f"{'Mover' if is_mover else 'Same ZIP'}: "
                     f"{cardid[:12]}...", fontsize=9)

        if idx >= 3:
            ax.set_xlabel('Date')

    plt.suptitle("2-Row Cardids: ZIP Timeline\n"
                 "(Top: Different ZIPs = movers | Bottom: Same ZIP = data update)",
                 fontsize=11)
    plt.tight_layout()

    out_path = f'{DROPBOX_OUT}/two_row_zip_examples.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved to {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
