# Chicago PPLTT Analysis

Difference-in-differences analysis of Chicago's 9% Personal Property Lease Transaction Tax (PPLTT) on ChatGPT subscriptions (Oct 2023).

## Pipeline

```
python run_all.py
```

This runs all scripts in order. Output PNGs are named with filter settings in the suffix.

## Configuration

All sample restrictions are set in **`load_chatgpt_data.py`**:

```python
AMOUNT_FILTER = 'plus_range'  # 'plus_range' ($20-22), 'wide_range' ($15-25), 'outside', or 'all'
USE_TOP_MERCHANTS = True      # Filter to top 30 merchants
OUTCOME_VAR = 'spend'         # 'spend', 'trans', or 'unique_users'
```

Change these settings, then re-run `python run_all.py` to regenerate all figures with new filters.

## Scripts

### Core pipeline (use shared loader)

| Script | Purpose |
|--------|---------|
| `load_chatgpt_data.py` | Shared data loading and filtering (import from here) |
| `chicago_did.py` | DiD event study with clustered SEs |
| `chicago_raw_counts.py` | Raw time series: Chicago vs control mean |
| `chicago_chatgpt_analysis.py` | Descriptive plots for Chicago only |
| `run_all.py` | Pipeline runner |

### Diagnostics (don't use shared filters)

| Script | Purpose |
|--------|---------|
| `national_price_buckets.py` | Shows % of transactions in each price bucket nationally. Intentionally uses full sample to reveal what the $20-22 filter excludes. |

## Sample

- **Treatment**: Chicago (ZIP3 606) starting Oct 2023
- **Controls**: ~90 ZIP3s with transaction counts within 50% of Chicago in Feb-Jun 2023
- **Period**: Feb 2023 (ChatGPT Plus launch) through Nov 2024 (excludes ChatGPT Pro)
- **Filter**: $20-22 transactions (Plus subscription range with tax variation)

## Panel Data (for Constant Individual Panel)

Raw CEdge data is NOT panelized—transaction count trends may reflect panel composition changes rather than real consumption. To fix this, we extracted data needed to implement CEdge's "Constant Individual Panel" methodology (≥1 transaction every 70 days).

### Panel Data Files

Located in `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/`:

| File | Size | Contents |
|------|------|----------|
| `chatgpt_card_info.parquet` | 52MB | cardid → cardlinkid, cardtype, source_group |
| `activity_dates_2023.parquet` | 147MB | Unique (cardid, trans_date) pairs for 2023 |
| `activity_dates_2024.parquet` | 166MB | Unique (cardid, trans_date) pairs for 2024 |

### Key Concepts

- **cardid** = individual card
- **cardlinkid** = person (links multiple cards belonging to same individual)
- Panel membership should be defined at `cardlinkid` level
- **Exclude**: USA1 debit cards (`source_group == 1` AND `cardtype == 'DEBIT'`)

### Panelization Logic (TODO)

1. Load `chatgpt_card_info.parquet` to map cardid → cardlinkid
2. Load `activity_dates_*.parquet` to check 70-day activity windows
3. Generate 70-day rolling windows covering study period (Mar 2023 - Nov 2024)
4. Keep only cardlinkids with ≥1 transaction in ALL windows
5. Filter ChatGPT transactions to panelized cardlinkids
6. Re-run DiD analysis on panelized sample

### Extraction Details

Panel data extracted from Mercury cluster (job 15666111, Jan 26-27 2026). Source script: `/Users/jeffreyohl/Documents/GitHub/sb_incidence/code/cedge_scripts/extract_panel_data.py`

## Note on Panel Composition

The transaction-count outcome (`OUTCOME_VAR = 'trans'`) shows a steady downward drift in the event study coefficients through 2024 - suspicious for a tax effect, which should produce a level shift rather than a 14-month monotonic decline.

This pattern could reflect differential attrition (Chicago cardholders leaving the sample faster than controls). Hard to attribute to secular changes in population/employment/income given how rapidly it occurs.

The unique-users outcome (`OUTCOME_VAR = 'unique_users'`) counts distinct cardholders per zip3-month, isolating the extensive margin. This shows much cleaner parallel trends - Chicago tracks the synthetic control almost exactly post-treatment. The pre-treatment gap (Chicago above synthetic) closes to roughly zero post-tax.

## Archive

`archive/` contains deprecated scripts:
- `chicago_synth_control.py` - Synthetic control (replaced by DiD)
- `ai_subscription_analysis.py` - Earlier exploratory analysis
- `chatgpt_timeseries_analysis.py` - Earlier time series work
