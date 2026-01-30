#!/usr/bin/env python3
"""
Validate: does address_map's "valid on July 4" ZIP match card table July snapshot?

If they match, address_map is consistent with the card table at that point,
giving confidence for looking backward in time.

Run:
    python3 code/data_prep/validate_address_map_july.py
"""

import pandas as pd
from datetime import datetime

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'
CARD_INFO_PATH = f'{CEDGE_DATA}/chatgpt_card_info_2025_12_26.parquet'
CHANGERS_PATH = f'{CEDGE_DATA}/zip_changers_jul_dec.parquet'

JULY_DATE = pd.Timestamp('2025-07-04')


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("VALIDATE: address_map July ZIP vs card table July ZIP")
    log("=" * 60)

    # Load address_map
    log("Loading address_map (demographics_tv)...")
    tv = pd.read_parquet(TV_PATH)
    log(f"  Rows: {len(tv):,}, Cardids: {tv['cardid'].nunique():,}")

    # Get ZIP valid on July 4
    log(f"\nFinding address_map ZIP valid on {JULY_DATE.date()}...")
    tv_july = tv[
        (tv['valid_begin'] <= JULY_DATE) &
        (tv['valid_end'] >= JULY_DATE)
    ].copy()
    log(f"  Rows valid on July 4: {len(tv_july):,}")
    log(f"  Unique cardids: {tv_july['cardid'].nunique():,}")

    # Dedupe
    tv_july = tv_july.drop_duplicates(subset='cardid', keep='first')
    tv_july = tv_july[['cardid', 'zip']].rename(columns={'zip': 'zip_addr_map'})
    tv_july['zip_addr_map'] = tv_july['zip_addr_map'].astype(str)

    # Load card info (Dec snapshot)
    log("\nLoading card table (Dec snapshot)...")
    card_info = pd.read_parquet(CARD_INFO_PATH)
    zip_col = next(
        (c for c in ['zip', 'ZIP', 'zip3', 'ZIP3'] if c in card_info.columns),
        None
    )
    card_info = card_info[['cardid', zip_col]].rename(columns={zip_col: 'zip_dec'})
    card_info['zip_dec'] = card_info['zip_dec'].astype(str)

    # Load changers for July ZIP
    log("Loading changers...")
    changers = pd.read_parquet(CHANGERS_PATH)[['cardid', 'zip_jul']]
    changers['zip_jul'] = changers['zip_jul'].astype(str)

    # Merge and compute July ZIP
    merged = tv_july.merge(card_info, on='cardid', how='inner')
    merged = merged.merge(changers, on='cardid', how='left')
    merged['zip_card_jul'] = merged['zip_jul'].fillna(merged['zip_dec'])

    # Compare
    merged['match'] = merged['zip_addr_map'] == merged['zip_card_jul']
    n_match = merged['match'].sum()
    pct = 100 * n_match / len(merged)

    log("\n" + "=" * 60)
    log(f"Address_map July ZIP == Card table July ZIP:")
    log(f"  {n_match:,} / {len(merged):,} = {pct:.2f}%")
    log("=" * 60)

    # Sample mismatches
    mismatches = merged[~merged['match']]
    if len(mismatches) > 0:
        log(f"\nMismatches: {len(mismatches):,}")
        for _, r in mismatches.head(10).iterrows():
            log(f"  addr_map={r['zip_addr_map']} card={r['zip_card_jul']}")

    merged.to_parquet(f'{CEDGE_DATA}/address_map_july_validation.parquet')
    log("\nDone.")


if __name__ == "__main__":
    main()
