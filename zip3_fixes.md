# ZIP3 Assignment Fix

## ⚠️ CONTAMINATION: WRONG SOURCE (Jan 30, 2026)

**Current demographics are contaminated.** We've been using `cardid_address_map` but CE docs say ZIP3 comes from the `card` table.

## How ZIP3 Actually Works in Consumer Edge

From CE documentation (card table):
> "Geography is delineated by the first three digits of each cardholder's home ZIP code"
>
> "In the event of a change of 3-digit zip code for a deidentified shopper, a new CARDLINKID will be generated"

**Key insight**: When someone changes ZIP3, a new cardlinkid is generated and all their cards are re-linked to it. The old cardlinkid is retired.

**Answered (Jan 30, 2026)**: The `zip` field in the card table **gets updated** when someone moves — it is NOT fixed at card issuance. Test result: 3.14% of cardids changed ZIP3 between Jul and Dec 2025 (5 months). Implies ~7.5%/year mover rate, so 15-20% of 2023 transactions may have "wrong" ZIP (assigned current location, not location at transaction time). This adds noise but shouldn't bias results.

## The Problem

`chatgpt_demographics_2023_2024_2025.csv` was built by `extract_merchant_transactions.py` using:
1. `cardid_address_map` parquet files — **wrong source**
2. `drop_duplicates(subset=['cardid'], keep='last')` — **arbitrary row**
3. Truncate 5-digit zip to first 3 digits

The `cardid_address_map` has garbage A→B→A bouncing (data source conflicts between usa1/usa2), not real moves.

## Fix Applied (Jan 30, 2026)

1. ✅ Re-extracted card table WITH ZIP on Mercury (Dec 26, 2025 snapshot, 901,911 cardlinkids)
2. ✅ Updated `load_chatgpt_data.py` to use `chatgpt_card_info_2025_12_26.parquet`
3. ✅ Re-ran pipeline with corrected ZIP3 (ratio=8.96, gap=-10%)

## Known Limitation

ZIP3 is from a **card table snapshot**, not where people lived at transaction time. Movers between 2023–2025 will be assigned their snapshot ZIP. This adds noise but shouldn't bias results systematically.

**Current extract**: Dec 26, 2025 snapshot. Proceeding with analysis using this.

**Test completed**: 3.14% of cardids changed ZIP3 between Jul–Dec 2025 (5 months). Card table ZIP is NOT fixed at issuance.

## cardid_address_map Validation (Jan 30, 2026)

Ran validation to check if `cardid_address_map` is usable for historical ZIP lookups.

**Test 1**: Does address_map's "valid on July 4" ZIP match card table July snapshot?
- Result: **97.15% match** (887,632 / 913,690 cardids)
- Good news: address_map is consistent with card table at that point in time

**Test 2**: For cardids that changed ZIP Jul→Dec in card table, does address_map capture both ZIPs?
- Result: Only **11% capture rate** (1,097 / 10,000)
- Expected: address_map ends July 4, so it can't have December ZIPs
- The bouncing is real but appears to be noise, not tracking actual moves

**Conclusion**: address_map is reliable for looking *backward* in time (pre-July 2025), not forward.

## Monthly ZIP3 Approach

To handle the daily bouncing noise in address_map, compute **modal ZIP3 per card-month**:

1. For each card-month, count days at each ZIP3
2. Assign the ZIP3 with the most days
3. Assumption: Monthly moving rate is tiny, so modal ≈ true residence

Script: `code/data_prep/compute_monthly_zip3.py`
Output: `cardid_monthly_zip3.parquet` with columns `[cardid, year_month, zip3]`

**Validation plots**: Run `python code/data_prep/visualize_row_distribution.py` → `output/address_row_*.png` (CDF + raw vs monthly modal examples).

**Bouncer plot**: `bouncer_zip3_timeseries.png` shows 5 high-bounce cardids. Pattern:
- Pre-2023: stable (100% modal confidence)
- Late 2022 - 2023: bouncing noise (modal picks winner each month)
- 2024+: stabilizes again

**Status (Jan 30, 2026)**:
- ✅ Script validated on 5 high-bounce cardids
- ✅ Validation plot: `bouncer_zip3_timeseries.png`
- 🔄 Full computation running in background (`python compute_monthly_zip3.py --full`)
- ETA: ~10-15 min for 913k cardids (CPU-bound)

To rerun if interrupted:
```bash
python3 code/data_prep/compute_monthly_zip3.py --full
```

## Remaining Questions

1. **What causes the bouncing?** Likely transaction location vs billing address confusion, or CE's internal inference algorithm. Worth asking CE directly.

2. **Did cardlinkid change when ZIP changed?** For the 10K cardids that changed ZIP3 Jul→Dec, check if their cardlinkid also changed. CE docs say movers get new cardlinkid. (Not yet tested.)

## Files

| File | Status |
|------|--------|
| `chatgpt_card_info_2025_12_26.parquet` | ✅ Current (Dec 26, 2025 snapshot) |
| `chatgpt_demographics_tv.parquet` | ✅ Usable for historical ZIP (97% consistent with card table) |
| `cardid_monthly_zip3.parquet` | 🔄 Running (modal ZIP3 per card-month) |
| `chatgpt_demographics_2023_2024_2025.csv` | ❌ Contaminated (don't use) |
