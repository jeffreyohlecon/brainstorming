#!/usr/bin/env python3
"""
Visualize address_map row distribution:
1. CDF of row counts per cardid
2. Example timelines for 2-row, 5-10 row, and max-row cardids
   - Raw data (daily bouncing)
   - Coarsened data (monthly modal)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
DROPBOX_OUT = '/Users/jeffreyohl/Dropbox/LLM_PassThrough/output'  # Root, not sample-specific
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'


def get_months():
    """Generate all months in our range."""
    return pd.date_range('2022-01-01', '2025-07-01', freq='MS')


def compute_monthly_modal(rows):
    """Compute monthly modal ZIP3 for one cardid."""
    months = get_months()
    results = []

    for m in months:
        m_end = m + pd.offsets.MonthEnd(1)
        days_per_zip = {}

        for _, r in rows.iterrows():
            if r['valid_begin'] <= m_end and r['valid_end'] >= m:
                start = max(r['valid_begin'], m)
                end = min(r['valid_end'], m_end)
                days = (end - start).days + 1
                z = str(r['zip'])
                days_per_zip[z] = days_per_zip.get(z, 0) + days

        if days_per_zip:
            modal = max(days_per_zip, key=days_per_zip.get)
            results.append({
                'month': m,
                'month_end': m_end,
                'zip3': modal
            })

    return pd.DataFrame(results)


def plot_cdf(counts, out_path):
    """Plot CDF of row counts per cardid."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Left: CDF
    sorted_counts = np.sort(counts.values)
    cdf = np.arange(1, len(sorted_counts) + 1) / len(sorted_counts)

    ax1.plot(sorted_counts, cdf, 'b-', linewidth=2)
    ax1.set_xlabel('Number of address_map rows per cardid')
    ax1.set_ylabel('Cumulative fraction of cardids')
    ax1.set_title('CDF: Address rows per cardid')
    ax1.set_xlim(0, 100)
    ax1.grid(True, alpha=0.3)

    # Key percentiles
    for pct in [0.80, 0.90, 0.95, 0.99]:
        val = np.percentile(sorted_counts, pct * 100)
        ax1.axhline(pct, color='gray', ls=':', alpha=0.5)
        ax1.axvline(val, color='gray', ls=':', alpha=0.5)
        ax1.annotate(f'{pct:.0%}: {val:.0f} rows',
                     xy=(val, pct), fontsize=8,
                     xytext=(val + 5, pct - 0.03))

    # Right: Histogram (log scale)
    bins = [1, 2, 3, 4, 5, 10, 20, 50, 100, 300]
    hist, edges = np.histogram(counts.values, bins=bins)

    ax2.bar(range(len(hist)), hist, color='steelblue', edgecolor='black')
    ax2.set_xticks(range(len(hist)))
    ax2.set_xticklabels([f'{bins[i]}-{bins[i+1]-1}' for i in range(len(hist))])
    ax2.set_xlabel('Row count bucket')
    ax2.set_ylabel('Number of cardids')
    ax2.set_title('Distribution of row counts')
    ax2.set_yscale('log')

    for i, h in enumerate(hist):
        pct = h / len(counts) * 100
        ax2.annotate(f'{pct:.1f}%', xy=(i, h), ha='center',
                     va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"Saved CDF to {out_path}")
    plt.close()


def plot_raw_and_coarsened(cardid, tv, ax_raw, ax_coarse, title, colors):
    """Plot raw timeline (top) and coarsened monthly modal (bottom)."""
    rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')

    zips = rows['zip'].astype(str).unique()
    zip_colors = {z: colors[i % len(colors)] for i, z in enumerate(zips)}

    # RAW: plot each address_map row
    for _, row in rows.iterrows():
        z = str(row['zip'])
        width = (row['valid_end'] - row['valid_begin']).days
        ax_raw.barh(
            y=0,
            width=width,
            left=row['valid_begin'],
            height=0.5,
            color=zip_colors[z],
            edgecolor='black',
            linewidth=0.3
        )

    # COARSENED: compute monthly modal and plot
    monthly = compute_monthly_modal(rows)
    for _, row in monthly.iterrows():
        z = row['zip3']
        if z not in zip_colors:
            zip_colors[z] = colors[len(zip_colors) % len(colors)]
        width = (row['month_end'] - row['month']).days
        ax_coarse.barh(
            y=0,
            width=width,
            left=row['month'],
            height=0.5,
            color=zip_colors[z],
            edgecolor='black',
            linewidth=0.3
        )

    # Treatment line on both
    for ax in [ax_raw, ax_coarse]:
        ax.axvline(pd.Timestamp('2023-10-01'), color='red',
                   ls='--', alpha=0.7, linewidth=1)
        ax.set_xlim(pd.Timestamp('2022-01-01'), pd.Timestamp('2025-08-01'))
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])

    ax_raw.set_title(f"{title} — Raw ({len(rows)} rows)", fontsize=8)
    ax_coarse.set_title("Monthly modal", fontsize=8)

    # Legend
    legend_str = ", ".join(list(zips)[:4])
    if len(zips) > 4:
        legend_str += f", +{len(zips)-4}"
    ax_raw.text(0.02, 0.95, f"ZIPs: {legend_str}", transform=ax_raw.transAxes,
                fontsize=6, va='top')


def main():
    print("Loading address_map...")
    tv = pd.read_parquet(TV_PATH)
    tv['valid_begin'] = pd.to_datetime(tv['valid_begin'])
    tv['valid_end'] = pd.to_datetime(tv['valid_end'])

    counts = tv.groupby('cardid').size()
    print(f"Total cardids: {len(counts):,}")
    print(f"  1 row: {(counts == 1).sum():,} ({(counts == 1).mean()*100:.1f}%)")
    print(f"  2 rows: {(counts == 2).sum():,} ({(counts == 2).mean()*100:.1f}%)")
    print(f"  3-10 rows: {((counts >= 3) & (counts <= 10)).sum():,}")
    print(f"  11-50 rows: {((counts >= 11) & (counts <= 50)).sum():,}")
    print(f"  51+ rows: {(counts >= 51).sum():,}")
    print(f"  Max: {counts.max()} rows")

    # 1. CDF plot
    plot_cdf(counts, f'{DROPBOX_OUT}/address_row_cdf.png')

    # 2. Example timelines with raw vs coarsened
    random.seed(42)
    colors = plt.cm.Set2.colors

    # Get examples
    two_row = random.sample(list(counts[counts == 2].index), 3)
    mid_row = random.sample(list(counts[(counts >= 5) & (counts <= 10)].index), 3)
    heavy = random.sample(list(counts[counts >= 50].index), 2)
    max_cardid = counts.idxmax()

    # 3 rows of examples, each with 3 cardids, each cardid gets 2 rows (raw + coarse)
    fig, axes = plt.subplots(6, 3, figsize=(14, 10))

    # Row 0-1: 2-row examples
    for i, cardid in enumerate(two_row):
        plot_raw_and_coarsened(cardid, tv, axes[0, i], axes[1, i],
                                f"2-row: {cardid[:10]}...", colors)

    # Row 2-3: 5-10 row examples
    for i, cardid in enumerate(mid_row):
        n = counts[cardid]
        plot_raw_and_coarsened(cardid, tv, axes[2, i], axes[3, i],
                                f"{n}-row: {cardid[:10]}...", colors)

    # Row 4-5: Heavy bouncers + max
    examples_heavy = heavy + [max_cardid]
    for i, cardid in enumerate(examples_heavy):
        n = counts[cardid]
        label = "MAX" if cardid == max_cardid else f"{n}-row"
        plot_raw_and_coarsened(cardid, tv, axes[4, i], axes[5, i],
                                f"{label}: {cardid[:10]}...", colors)

    # Labels
    axes[0, 0].set_ylabel("2-row\n(raw)", fontsize=9)
    axes[1, 0].set_ylabel("(monthly)", fontsize=9)
    axes[2, 0].set_ylabel("5-10 row\n(raw)", fontsize=9)
    axes[3, 0].set_ylabel("(monthly)", fontsize=9)
    axes[4, 0].set_ylabel("50+ row\n(raw)", fontsize=9)
    axes[5, 0].set_ylabel("(monthly)", fontsize=9)

    for ax in axes[5, :]:
        ax.set_xlabel("Date")

    plt.suptitle("Address Map: Raw vs Monthly Modal\n"
                 "(Red line = Oct 2023 treatment)", fontsize=11)
    plt.tight_layout()

    out_path = f'{DROPBOX_OUT}/address_row_examples.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"Saved examples to {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
