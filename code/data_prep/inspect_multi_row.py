#!/usr/bin/env python3
"""
Inspect a few multi-row cardids to sanity check modal ZIP3 computation.
"""

import pandas as pd

CEDGE_DATA = '/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data'
TV_PATH = f'{CEDGE_DATA}/chatgpt_demographics_tv.parquet'

def main():
    print("Loading address_map...")
    tv = pd.read_parquet(TV_PATH)
    tv['valid_begin'] = pd.to_datetime(tv['valid_begin'])
    tv['valid_end'] = pd.to_datetime(tv['valid_end'])

    # Find cardids with multiple rows
    counts = tv.groupby('cardid').size().sort_values(ascending=False)
    multi = counts[counts > 1]

    print(f"\nMulti-row cardids: {len(multi):,}")
    print(f"Row count distribution:")
    print(multi.value_counts().head(20))

    # Pick a few examples with different patterns
    # 1. Cardid with exactly 2 rows (most common multi-row case)
    two_row = counts[counts == 2].index[0]

    # 2. Cardid with 5-10 rows (moderate bouncing)
    mid_bounce = counts[(counts >= 5) & (counts <= 10)].index[0]

    # 3. Cardid with 20+ rows (heavy bouncing)
    heavy_bounce = counts[counts >= 20].index[0]

    examples = [
        ("2 rows", two_row),
        ("5-10 rows", mid_bounce),
        ("20+ rows", heavy_bounce),
    ]

    for label, cardid in examples:
        print(f"\n{'='*60}")
        print(f"EXAMPLE: {label}")
        print(f"Cardid: {cardid[:30]}...")
        print("="*60)

        rows = tv[tv['cardid'] == cardid].sort_values('valid_begin')
        print(f"\nRaw address_map rows ({len(rows)}):")
        for _, r in rows.iterrows():
            days = (r['valid_end'] - r['valid_begin']).days + 1
            print(f"  ZIP {r['zip']:>3} | "
                  f"{r['valid_begin'].strftime('%Y-%m-%d')} to "
                  f"{r['valid_end'].strftime('%Y-%m-%d')} "
                  f"({days:,} days)")

        # Compute modal for a few months
        print(f"\nModal ZIP3 by month (sample):")
        test_months = pd.date_range('2023-01-01', '2024-01-01', freq='MS')

        for m in test_months:
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
                total = sum(days_per_zip.values())
                pct = days_per_zip[modal] / total * 100
                breakdown = ", ".join(f"{z}:{d}d" for z, d in
                                      sorted(days_per_zip.items(),
                                             key=lambda x: -x[1]))
                print(f"  {m.strftime('%Y-%m')}: {modal} "
                      f"({pct:.0f}% of {total}d) [{breakdown}]")


if __name__ == "__main__":
    main()
