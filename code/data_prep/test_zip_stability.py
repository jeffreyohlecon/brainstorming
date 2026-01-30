#!/usr/bin/env python3
"""
Test if cardid-ZIP is stable across card table snapshots.

Compares July 2025 vs Dec 2025 for our ChatGPT cardids only.
Uses streaming to avoid OOM (full card table is too big to load twice).

If ~0% change, cardid-ZIP is fixed at issuance (good for us).
"""

import pandas as pd
import pyarrow.parquet as pq
import glob
import os
from datetime import datetime


CARD_PATH = '/kilts/consumeredge_processed/parquet/card'


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("ZIP STABILITY TEST: Jul vs Dec 2025")
    log("=" * 60)

    # Step 1: Get our ChatGPT cardids (small set)
    log("Loading ChatGPT cardids...")
    trans_files = glob.glob(os.path.expanduser('~/chatgpt_transactions_*.parquet'))
    our_cardids = set()
    for f in trans_files:
        df = pd.read_parquet(f, columns=['cardid'])
        our_cardids.update(df['cardid'].unique())
    log(f"  Our cardids: {len(our_cardids):,}")

    # Step 2: Stream through July snapshot, keep only our cardids
    log("Streaming July 2025 snapshot...")
    jul_zips = {}
    pf = pq.ParquetFile(f'{CARD_PATH}/card_usa1_2025_07_04.parquet')
    for batch in pf.iter_batches(columns=['cardid', 'zip'], batch_size=1_000_000):
        chunk = batch.to_pandas()
        matched = chunk[chunk['cardid'].isin(our_cardids)]
        for _, row in matched.iterrows():
            jul_zips[row['cardid']] = row['zip']
    log(f"  July: found {len(jul_zips):,} of our cardids")

    # Step 3: Stream through Dec snapshot, compare
    log("Streaming Dec 2025 snapshot...")
    changed = []
    matched_count = 0
    pf = pq.ParquetFile(f'{CARD_PATH}/card_usa1_2025_12_26.parquet')
    for batch in pf.iter_batches(columns=['cardid', 'zip'], batch_size=1_000_000):
        chunk = batch.to_pandas()
        matched = chunk[chunk['cardid'].isin(our_cardids)]
        for _, row in matched.iterrows():
            cardid = row['cardid']
            dec_zip = row['zip']
            if cardid in jul_zips:
                matched_count += 1
                jul_zip = jul_zips[cardid]
                if jul_zip != dec_zip:
                    changed.append({
                        'cardid': cardid,
                        'zip_jul': jul_zip,
                        'zip_dec': dec_zip
                    })

    log(f"  Dec: matched {matched_count:,} cardids in both snapshots")

    pct = 100 * len(changed) / matched_count if matched_count > 0 else 0
    log("")
    log("=" * 60)
    log(f"RESULT: ZIP changed Jul→Dec: {len(changed):,} ({pct:.4f}%)")
    log("=" * 60)

    if changed:
        log("\nExample changes:")
        for c in changed[:20]:
            log(f"  {c['cardid']}: {c['zip_jul']} → {c['zip_dec']}")

        out_path = os.path.expanduser('~/zip_changers_jul_dec.parquet')
        pd.DataFrame(changed).to_parquet(out_path, index=False)
        log(f"\nSaved {len(changed):,} changers to {out_path}")
    else:
        log("\nNo ZIP changes detected - cardid-ZIP is stable!")


if __name__ == "__main__":
    main()
