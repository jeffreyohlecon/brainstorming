#!/usr/bin/env python3
"""
Compute monthly ZIP3 for each cardid using modal value from address_map.

Problem: address_map has noisy daily ZIP ("bouncing").
Solution: Modal ZIP3 per card-month.

Optimized: 80% of cardids have only 1 address row (constant ZIP).
Only compute modal for the 20% with multiple rows.

Run:
    python3 code/data_prep/compute_monthly_zip3.py --full
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
DROPBOX_OUT = '/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/trans/15to25/all_merchants'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'
OUTPUT_PATH = f'{CEDGE_DATA}/cardid_monthly_zip3.parquet'

START_YEAR = 2022
END_YEAR = 2025


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_months():
    """Generate all months in our range."""
    months = pd.date_range(f'{START_YEAR}-01-01', f'{END_YEAR}-07-01', freq='MS')
    return months


def process_single_row_cardids(tv, single_cardids):
    """
    For cardids with exactly 1 address row, just replicate ZIP for all months.
    No modal computation needed - their ZIP is constant.
    Vectorized using cross-join + filter.
    """
    log(f"Processing {len(single_cardids):,} single-row cardids (fast path)...")

    single_data = tv[tv['cardid'].isin(single_cardids)].copy()
    single_data['zip3'] = single_data['zip'].astype(str)

    # Create months dataframe
    months = get_months()
    months_df = pd.DataFrame({'month': months})
    months_df['year_month'] = months_df['month'].dt.strftime('%Y-%m')

    # Cross join: every cardid × every month
    single_data['_key'] = 1
    months_df['_key'] = 1
    cross = single_data.merge(months_df, on='_key').drop('_key', axis=1)

    # Filter to valid months only
    result = cross[
        (cross['month'] >= cross['valid_begin']) &
        (cross['month'] <= cross['valid_end'])
    ][['cardid', 'year_month', 'zip3']].copy()

    return result


def process_multi_row_cardids(tv, multi_cardids):
    """
    For cardids with >1 address row, compute modal ZIP per month.
    Vectorized approach using groupby.
    """
    log(f"Processing {len(multi_cardids):,} multi-row cardids...")

    multi_data = tv[tv['cardid'].isin(multi_cardids)].copy()
    multi_data['zip3'] = multi_data['zip'].astype(str)

    months = get_months()
    all_records = []

    # Process in chunks to avoid memory issues
    chunk_size = 10000
    cardid_list = list(multi_cardids)

    for i in range(0, len(cardid_list), chunk_size):
        chunk_cardids = cardid_list[i:i + chunk_size]
        chunk_data = multi_data[multi_data['cardid'].isin(chunk_cardids)]

        records = []
        for _, row in chunk_data.iterrows():
            # Find months this row covers
            for m in months:
                m_end = m + pd.offsets.MonthEnd(1)
                if row['valid_begin'] <= m_end and row['valid_end'] >= m:
                    # Compute days in this month
                    start = max(row['valid_begin'], m)
                    end = min(row['valid_end'], m_end)
                    days = (end - start).days + 1
                    records.append({
                        'cardid': row['cardid'],
                        'year_month': m.strftime('%Y-%m'),
                        'zip3': row['zip3'],
                        'days': days
                    })

        if records:
            chunk_df = pd.DataFrame(records)
            # Aggregate days per cardid-month-zip
            agg = chunk_df.groupby(['cardid', 'year_month', 'zip3'])['days'].sum().reset_index()
            # Find modal zip per cardid-month
            idx = agg.groupby(['cardid', 'year_month'])['days'].idxmax()
            modal = agg.loc[idx, ['cardid', 'year_month', 'zip3']]
            all_records.append(modal)

        if (i // chunk_size) % 5 == 0:
            log(f"  Processed {min(i + chunk_size, len(cardid_list)):,}/{len(cardid_list):,}")

    return pd.concat(all_records, ignore_index=True)


def compute_all_fast(tv):
    """Fast computation using single/multi split."""
    log("\n--- FAST COMPUTATION ---")

    # Split by row count
    counts = tv.groupby('cardid').size()
    single_cardids = set(counts[counts == 1].index)
    multi_cardids = set(counts[counts > 1].index)

    log(f"Single-row cardids: {len(single_cardids):,} (fast path)")
    log(f"Multi-row cardids: {len(multi_cardids):,} (need modal)")

    # Process each group
    single_result = process_single_row_cardids(tv, single_cardids)
    log(f"  Single-row result: {len(single_result):,} card-months")

    multi_result = process_multi_row_cardids(tv, multi_cardids)
    log(f"  Multi-row result: {len(multi_result):,} card-months")

    # Combine
    result = pd.concat([single_result, multi_result], ignore_index=True)
    log(f"Total: {len(result):,} card-months")

    return result


def validate_bouncers(tv):
    """Show modal ZIP3 time series for top bouncers with plots."""
    log("\n--- VALIDATION: Top bouncers ---")
    counts = tv.groupby('cardid').size().sort_values(ascending=False)
    bouncers = counts[counts > 50].head(5).index.tolist()

    fig, axes = plt.subplots(len(bouncers), 1, figsize=(12, 3 * len(bouncers)))

    for idx, cardid in enumerate(bouncers):
        cardid_data = tv[tv['cardid'] == cardid]
        unique_zips = sorted(cardid_data['zip'].astype(str).unique())
        log(f"\n{cardid[:20]}... rows={len(cardid_data)}, ZIPs={unique_zips}")

        # Quick modal computation for this cardid
        months = get_months()
        monthly_data = []
        for m in months:
            m_end = m + pd.offsets.MonthEnd(1)
            days_per_zip = {}
            for _, row in cardid_data.iterrows():
                if row['valid_begin'] <= m_end and row['valid_end'] >= m:
                    start = max(row['valid_begin'], m)
                    end = min(row['valid_end'], m_end)
                    days = (end - start).days + 1
                    z = str(row['zip'])
                    days_per_zip[z] = days_per_zip.get(z, 0) + days
            if days_per_zip:
                modal = max(days_per_zip, key=days_per_zip.get)
                total = sum(days_per_zip.values())
                monthly_data.append({
                    'date': m,
                    'zip3': modal,
                    'pct': days_per_zip[modal] / total
                })

        monthly = pd.DataFrame(monthly_data)
        zip_to_num = {z: i for i, z in enumerate(unique_zips)}
        monthly['zip_num'] = monthly['zip3'].map(zip_to_num)

        ax = axes[idx]
        for _, row in monthly.iterrows():
            alpha = max(0.3, row['pct'])
            ax.scatter(row['date'], row['zip_num'], c='steelblue', alpha=alpha, s=50)
        ax.plot(monthly['date'], monthly['zip_num'], 'steelblue', alpha=0.3)
        ax.set_yticks(range(len(unique_zips)))
        ax.set_yticklabels(unique_zips)
        ax.set_ylabel('ZIP3')
        ax.set_title(f"Cardid: {cardid[:15]}... ({len(cardid_data)} raw rows)")
        ax.axvline(pd.Timestamp('2022-11-30'), color='red', ls='--', alpha=0.5)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Month')
    plt.tight_layout()
    out_path = f'{DROPBOX_OUT}/bouncer_zip3_timeseries.png'
    plt.savefig(out_path, dpi=150)
    log(f"\nSaved plot to {out_path}")
    plt.close()


def main():
    import sys
    log("=" * 60)
    log("COMPUTE MONTHLY ZIP3")
    log("=" * 60)

    log("Loading address_map...")
    tv = pd.read_parquet(TV_PATH)
    tv['valid_begin'] = pd.to_datetime(tv['valid_begin'])
    tv['valid_end'] = pd.to_datetime(tv['valid_end'])
    log(f"  Rows: {len(tv):,}, Cardids: {tv['cardid'].nunique():,}")

    if '--full' in sys.argv:
        result = compute_all_fast(tv)
        result.to_parquet(OUTPUT_PATH, index=False)
        log(f"\nSaved to {OUTPUT_PATH}")
    else:
        validate_bouncers(tv)
        log("\n\nRun with --full to compute all cardids")


if __name__ == "__main__":
    main()
