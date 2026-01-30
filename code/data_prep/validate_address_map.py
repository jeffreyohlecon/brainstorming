#!/usr/bin/env python3
"""
Validate cardid_address_map against card table ZIP changes.

We know from test_zip_stability.py that 3.14% of cardids changed ZIP3
between July and December 2025 in the card table.

This script checks: does cardid_address_map actually capture those changes?
If yes, address_map is useful for tracking movers.
If no, address_map is unreliable (as suspected from "bouncing" patterns).

Inputs:
- chatgpt_demographics_tv.parquet: address_map data for our cardids
- zip_changers_jul_dec.parquet: cardids that changed ZIP in card table

Run:
    python3 code/data_prep/validate_address_map.py
"""

import pandas as pd
from datetime import datetime

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'
CHANGERS_PATH = f'{CEDGE_DATA}/zip_changers_jul_dec.parquet'


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("VALIDATE: Does address_map capture card table ZIP changes?")
    log("=" * 60)

    # Load data
    log("Loading demographics_tv (from cardid_address_map)...")
    tv = pd.read_parquet(TV_PATH)
    log(f"  Rows: {len(tv):,}, Unique cardids: {tv['cardid'].nunique():,}")

    log("Loading zip changers (card table Jul->Dec)...")
    changers = pd.read_parquet(CHANGERS_PATH)
    log(f"  Changers: {len(changers):,}")

    # Basic stats on address_map
    log("\n--- ADDRESS_MAP STRUCTURE ---")
    counts = tv.groupby('cardid').size()
    movers_in_map = (counts > 1).sum()
    log(f"Cardids with >1 address row: {movers_in_map:,} "
        f"({100*movers_in_map/len(counts):.1f}%)")

    # Vectorized cross-validation
    log("\n--- CROSS-VALIDATION ---")

    # Convert ZIPs to string for comparison
    tv['zip_str'] = tv['zip'].astype(str)
    changers['zip_jul_str'] = changers['zip_jul'].astype(str)
    changers['zip_dec_str'] = changers['zip_dec'].astype(str)

    # Count address_map rows per cardid
    map_counts = tv.groupby('cardid').size().rename('address_map_rows')

    # Get all ZIPs per cardid as sets
    map_zips = tv.groupby('cardid')['zip_str'].apply(set).rename('address_map_zips')

    # Merge onto changers
    results_df = changers.merge(map_counts, on='cardid', how='left')
    results_df = results_df.merge(map_zips, on='cardid', how='left')
    results_df['address_map_rows'] = results_df['address_map_rows'].fillna(0).astype(int)
    results_df['address_map_zips'] = results_df['address_map_zips'].apply(
        lambda x: x if isinstance(x, set) else set()
    )

    # Check if address_map has the July and Dec ZIPs
    results_df['has_jul_zip'] = results_df.apply(
        lambda r: r['zip_jul_str'] in r['address_map_zips'], axis=1
    )
    results_df['has_dec_zip'] = results_df.apply(
        lambda r: r['zip_dec_str'] in r['address_map_zips'], axis=1
    )
    results_df['has_both'] = results_df['has_jul_zip'] & results_df['has_dec_zip']

    # Summary stats
    log(f"Card table changers: {len(results_df):,}")
    log(f"  - Found in address_map: "
        f"{(results_df['address_map_rows'] > 0).sum():,}")
    log(f"  - Address_map has >1 row: "
        f"{(results_df['address_map_rows'] > 1).sum():,}")
    log(f"  - Address_map has July ZIP: "
        f"{results_df['has_jul_zip'].sum():,}")
    log(f"  - Address_map has Dec ZIP: "
        f"{results_df['has_dec_zip'].sum():,}")
    log(f"  - Address_map has BOTH ZIPs: "
        f"{results_df['has_both'].sum():,}")

    # Key metric: what % of card-table changers are captured?
    pct_captured = 100 * results_df['has_both'].sum() / len(results_df)
    log(f"\n*** CAPTURE RATE: {pct_captured:.1f}% ***")

    if pct_captured < 50:
        log("Address_map is NOT reliably capturing ZIP changes.")
    else:
        log("Address_map appears to track ZIP changes reasonably well.")

    # Show examples
    log("\n--- EXAMPLES: Changers with address_map data ---")
    examples = results_df[results_df['address_map_rows'] > 0].head(10)
    for _, r in examples.iterrows():
        log(f"  Card: {r['zip_jul']} -> {r['zip_dec']} | "
            f"Map rows: {r['address_map_rows']}, "
            f"Map ZIPs: {r['address_map_zips']}, "
            f"Has both: {r['has_both']}")

    # Show examples of mismatches
    log("\n--- EXAMPLES: Changers NOT captured by address_map ---")
    misses = results_df[~results_df['has_both']].head(10)
    for _, r in misses.iterrows():
        log(f"  Card: {r['zip_jul']} -> {r['zip_dec']} | "
            f"Map rows: {r['address_map_rows']}, "
            f"Map ZIPs: {r['address_map_zips']}")

    # Investigate address_map date patterns
    log("\n--- ADDRESS_MAP DATE PATTERNS ---")
    log("(How is address_map constructed? When do dates change?)")

    # Check valid_begin distribution
    log(f"valid_begin range: {tv['valid_begin'].min()} to {tv['valid_begin'].max()}")
    log(f"valid_end range: {tv['valid_end'].min()} to {tv['valid_end'].max()}")

    # For cardids with multiple rows, show date transitions
    multi_row = tv[tv['cardid'].isin(counts[counts > 1].index)]
    log(f"\nCardids with multiple address rows: {multi_row['cardid'].nunique():,}")

    # Sample a few movers to see date patterns
    log("\n--- SAMPLE MOVERS FROM ADDRESS_MAP ---")
    sample_movers = multi_row['cardid'].unique()[:5]
    for cardid in sample_movers:
        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')
        log(f"\nCardid: {cardid[:20]}...")
        for _, r in rows.iterrows():
            log(f"  ZIP {r['zip']}: {r['valid_begin']} to {r['valid_end']}")

    # Check if any changers show up in multi-row address_map records
    changers_with_multi = results_df[results_df['address_map_rows'] > 1]
    log(f"\n--- CHANGERS WITH MULTI-ROW ADDRESS_MAP ---")
    log(f"Card table changers: {len(results_df):,}")
    log(f"Changers with >1 address_map row: {len(changers_with_multi):,}")

    # Save detailed results
    out_path = f'{CEDGE_DATA}/address_map_validation.parquet'
    # Convert sets to lists for parquet compatibility
    results_df['address_map_zips'] = results_df['address_map_zips'].apply(list)
    results_df.to_parquet(out_path, index=False)
    log(f"\nSaved detailed results to {out_path}")

    log("\n" + "=" * 60)
    log("VALIDATION COMPLETE")
    log("=" * 60)


if __name__ == "__main__":
    main()
