# Auxiliary Subscriptions Placebo Test

## Status (Jan 31, 2026)

**Spotify extraction running** - Job 15697469 on Mercury. Step 1 (transactions) in progress.

---

## Purpose

If Chicago's amusement tax caused ChatGPT subscriptions to decline, other
digital subscriptions (Netflix, Spotify) should NOT show the same pattern.
If they do decline in parallel, it suggests a confounder (macro trend,
Chicago-specific shock) rather than a tax effect.

## Data Extraction

Scripts are in `sb_incidence/code/cedge_scripts/`. Spotify and Netflix are
extracted separately (file sizes could be huge).

### Files to push to Mercury

```bash
scp extract_merchant_transactions.py johl@mercury.chicagobooth.edu:~/
scp run_spotify_2023_2024.sh johl@mercury.chicagobooth.edu:~/
scp extract_auxiliary_panel_data.py johl@mercury.chicagobooth.edu:~/
scp run_extract_spotify_panel.sh johl@mercury.chicagobooth.edu:~/
```

### Step 1: Extract transactions

```bash
sbatch run_spotify_2023_2024.sh
```

Output (in `~` on Mercury):
- `spotify_merchants_2023_2024.csv`
- `spotify_transactions_2023.parquet`
- `spotify_transactions_2024.parquet`
- `spotify_demographics_2023_2024.csv` ← DON'T USE (address_map, contaminated)

### Step 2: Extract card info + activity dates

**Run AFTER Step 1 completes** (needs transaction files).

```bash
sbatch run_extract_spotify_panel.sh
```

Output:
- `spotify_card_info.parquet` ← USE THIS for ZIP3 (from card table)
- `spotify_activity_dates_2023.parquet`
- `spotify_activity_dates_2024.parquet`

### Download to local

```bash
scp "johl@mercury.chicagobooth.edu:~/spotify_transactions_*.parquet" \
    "/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/"
scp "johl@mercury.chicagobooth.edu:~/spotify_card_info.parquet" \
    "/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/"
scp "johl@mercury.chicagobooth.edu:~/spotify_activity_dates_*.parquet" \
    "/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/"
```

## Netflix (later)

Same process with `run_netflix_2023_2024.sh` and `run_extract_netflix_panel.sh`.
Netflix is likely HUGE - may need to collapse on Mercury rather than downloading.

## ZIP3 Note

The `spotify_demographics_*.csv` from Step 1 uses `cardid_address_map` which has
garbage bouncing (see [zip3_fixes.md](zip3_fixes.md)). Use `spotify_card_info.parquet`
instead - it has `zip` from the card table (correct source).

## Analysis

Once data is local, adapt the synth control pipeline:
1. Create `load_spotify_data.py` (copy of `load_data.py` with spotify prefix)
2. Run panelization with same window parameters
3. Export to Stata, run synthetic control
4. Compare Chicago gap to ChatGPT results

## Expected Results

- **Good outcome**: Spotify shows no Chicago decline (or positive),
  confirming ChatGPT effect is tax-specific
- **Bad outcome**: Similar decline pattern would suggest Chicago-wide shock
  unrelated to the tax policy

## Notes

- Netflix and Spotify may NOT be subject to Chicago's amusement tax (taxed
  differently or exempt depending on classification)
- These services have similar price points (~$10-20/month) to ChatGPT Plus
- Same demographic likely uses all three services
