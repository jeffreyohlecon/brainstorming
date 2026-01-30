#!/usr/bin/env python3
"""Show several 2-row cardids to see the pattern."""

import pandas as pd

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'

def main():
    print("Loading address_map...")
    tv = pd.read_parquet(TV_PATH)
    tv['valid_begin'] = pd.to_datetime(tv['valid_begin'])
    tv['valid_end'] = pd.to_datetime(tv['valid_end'])

    # Find 2-row cardids
    counts = tv.groupby('cardid').size()
    two_row_cardids = counts[counts == 2].index.tolist()

    print(f"\n2-row cardids: {len(two_row_cardids):,} "
          f"({len(two_row_cardids)/len(counts[counts>1])*100:.1f}% of multi-row)")

    # Sample 10 random ones
    import random
    random.seed(42)
    sample = random.sample(two_row_cardids, 15)

    print("\n" + "="*70)
    print("SAMPLE OF 2-ROW CARDIDS")
    print("="*70)

    for cardid in sample:
        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')
        r1, r2 = rows.iloc[0], rows.iloc[1]

        # Check if ZIPs are same or different
        same_zip = str(r1['zip']) == str(r2['zip'])

        # Check if contiguous
        gap_days = (r2['valid_begin'] - r1['valid_end']).days

        print(f"\n{cardid[:25]}...")
        print(f"  Row 1: ZIP {r1['zip']:>3} | "
              f"{r1['valid_begin'].strftime('%Y-%m-%d')} to "
              f"{r1['valid_end'].strftime('%Y-%m-%d')} "
              f"({(r1['valid_end']-r1['valid_begin']).days+1:,}d)")
        print(f"  Row 2: ZIP {r2['zip']:>3} | "
              f"{r2['valid_begin'].strftime('%Y-%m-%d')} to "
              f"{r2['valid_end'].strftime('%Y-%m-%d')} "
              f"({(r2['valid_end']-r2['valid_begin']).days+1:,}d)")
        print(f"  → Same ZIP: {same_zip} | Gap: {gap_days}d")

    # Summary stats
    print("\n" + "="*70)
    print("SUMMARY STATS FOR 2-ROW CARDIDS")
    print("="*70)

    same_zip_count = 0
    real_mover_count = 0

    for cardid in two_row_cardids[:5000]:  # Sample for speed
        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')
        r1, r2 = rows.iloc[0], rows.iloc[1]
        if str(r1['zip']) == str(r2['zip']):
            same_zip_count += 1
        else:
            real_mover_count += 1

    print(f"\nOf first 5,000 2-row cardids:")
    print(f"  Same ZIP in both rows: {same_zip_count:,} "
          f"({same_zip_count/5000*100:.1f}%)")
    print(f"  Different ZIP (mover): {real_mover_count:,} "
          f"({real_mover_count/5000*100:.1f}%)")


if __name__ == "__main__":
    main()
