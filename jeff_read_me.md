# Jeff's Notes

## Consumer Edge Data Sources

| Source | Name | source_group |
|--------|------|--------------|
| USA1 | Formerly "CE Transact Prime US" | 1, 2 |
| USA2 | 30M Additional Debit Cards | 3 |

- All tables are gzipped and tab-delimited under `tsv/[TABLE]/v1/YYYY_MM_DD` subfolders
- Example path: `ce-transact-prime-usa-d28/usa1/tsv/trans/v1/2023_08_01/trans_dist_2023_08_01-000000000000.gz`

## ZIP3 Assignment (Jan 30, 2026)

See [zip3_fixes.md](zip3_fixes.md) for full details.

**Current approach**: Using `chatgpt_card_info_2025_12_26.parquet` which has ZIP from card table (Dec 2025 snapshot).

**Known issue**: Card table ZIP gets updated when people move (~3.14% changed in 5 months = ~7.5%/year). So 2023 transactions get assigned 2025 ZIP, not ZIP at transaction time. Adds noise but shouldn't bias results.

**Open question**: Could `cardid_address_map` give time-varying ZIP? Has date ranges but exhibited A→B→A bouncing. Need to investigate whether bouncing is fixable or fundamental garbage.
