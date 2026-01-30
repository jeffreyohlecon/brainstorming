#!/usr/bin/env python3
"""
Explore the time-varying demographics data.

Validates the chatgpt_demographics_tv.parquet file and tests interval merge logic.
"""

import os
import sys
import pandas as pd

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from load_chatgpt_data import DATA_DIR


def main():
    # Load time-varying demographics
    tv_demo_path = os.path.join(DATA_DIR, 'chatgpt_demographics_tv.parquet')

    if not os.path.exists(tv_demo_path):
        print(f"[ERROR] File not found: {tv_demo_path}")
        print("Run extract_timevarying_demographics.py on Mercury first.")
        sys.exit(1)

    print(f"Loading {tv_demo_path}...")
    df = pd.read_parquet(tv_demo_path)

    # Schema
    print(f"\n=== SCHEMA ===")
    print(f"Columns: {list(df.columns)}")
    print(f"Dtypes:\n{df.dtypes}")

    # Basic stats
    print(f"\n=== BASIC STATS ===")
    print(f"Total rows: {len(df):,}")
    print(f"Unique cardids: {df['cardid'].nunique():,}")
    print(f"Unique zip3s: {df['zip3'].nunique()}")

    # Date ranges
    print(f"\n=== DATE RANGES ===")
    print(f"valid_begin: {df['valid_begin'].min()} to {df['valid_begin'].max()}")
    print(f"valid_end: {df['valid_end'].min()} to {df['valid_end'].max()}")

    # Mover analysis
    print(f"\n=== MOVER ANALYSIS ===")
    rows_per_cardid = df.groupby('cardid').size()
    n_movers = (rows_per_cardid > 1).sum()
    pct_movers = 100 * n_movers / len(rows_per_cardid)
    print(f"Cardids with 1 address: {(rows_per_cardid == 1).sum():,}")
    print(f"Cardids with 2+ addresses (movers): {n_movers:,} ({pct_movers:.1f}%)")
    print(f"\nRows per cardid distribution:")
    print(rows_per_cardid.value_counts().sort_index().head(10))

    # Sample movers
    print(f"\n=== SAMPLE MOVER ===")
    mover_cardids = rows_per_cardid[rows_per_cardid > 1].index
    if len(mover_cardids) > 0:
        sample_id = mover_cardids[0]
        print(f"cardid: {sample_id}")
        print(df[df['cardid'] == sample_id].to_string(index=False))

    # ZIP3 coverage
    print(f"\n=== ZIP3 COVERAGE ===")
    print(f"Top 10 ZIP3s by cardid count:")
    zip3_counts = df.groupby('zip3')['cardid'].nunique().sort_values(ascending=False)
    for z, c in zip3_counts.head(10).items():
        print(f"  {z}: {c:,}")

    # Chicago check
    print(f"\n=== CHICAGO (606) ===")
    chi = df[df['zip3'] == '606']
    print(f"Rows: {len(chi):,}")
    print(f"Unique cardids: {chi['cardid'].nunique():,}")

    # Study period coverage (Mar 2023 - Nov 2024)
    print(f"\n=== STUDY PERIOD COVERAGE ===")
    study_start = pd.Timestamp('2023-03-01')
    study_end = pd.Timestamp('2024-11-30')

    # A cardid covers study period if valid_begin <= study_start and valid_end >= study_end
    # OR if they have overlapping ranges
    df['covers_start'] = df['valid_begin'] <= study_start
    df['covers_end'] = df['valid_end'] >= study_end
    df['overlaps'] = (df['valid_begin'] <= study_end) & (df['valid_end'] >= study_start)

    cardids_with_coverage = df[df['overlaps']].groupby('cardid').first()
    print(f"Cardids with any overlap with study period: {len(cardids_with_coverage):,}")

    # Full coverage = have address info for entire study period
    # This requires valid_begin <= study_start AND valid_end >= study_end for some row
    full_coverage = df[(df['valid_begin'] <= study_start) & (df['valid_end'] >= study_end)]
    n_full = full_coverage['cardid'].nunique()
    print(f"Cardids with full study period coverage: {n_full:,}")

    print("\n=== NEXT STEPS ===")
    print("1. Update load_chatgpt_data.py to use interval merge")
    print("2. For each transaction, find address where:")
    print("   trans_date BETWEEN valid_begin AND valid_end")
    print("3. Re-run synthetic control with corrected ZIP3s")


if __name__ == "__main__":
    main()
