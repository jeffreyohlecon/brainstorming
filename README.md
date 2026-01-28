# Chicago PPLTT Analysis

Analysis of Chicago's 9% Personal Property Lease Transaction Tax (PPLTT) on ChatGPT subscriptions (Oct 2023).

**Preferred method: Synthetic control** (see `chicago_did.py` with `USE_SYNTH_CONTROL = True`). DiD event study available as alternative.

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
- **Donor pool**: 19 ZIP3s with unique users within 10% of Chicago in Mar-Jun 2023
- **Period**: Mar 2023 through Nov 2024 (excludes ChatGPT Pro)
- **Filter**: $15-25 transactions (Plus subscription range with tax variation)
- **Outcome**: log(unique cardids) per ZIP3-month

### Matching Variables (Limitation)

**Currently matching on pre-treatment outcomes only** (log unique users, Mar-Sep 2023). This is non-standard—Abadie et al. recommend matching on both pre-treatment outcomes AND covariates. Without covariate matching, the synthetic control may not generalize well or may be fitting noise in the pre-period.

Ideal covariates for matching ZIP3 606:
- College education rate
- Median income
- Total population
- (other demographic characteristics)

TODO: Obtain ZIP3-level demographics (ask Matt Noto?) and re-run with proper covariate matching.

### Sensitivity to Donor Pool Size

Current analysis uses 10% size window (19 donors). TODO: Test robustness to wider windows (e.g., 20%, 50%). Using all ZIP3s (no restriction) causes optimizer convergence issues with SLSQP. May require subfolder structure: `donor_10pct/`, `donor_20pct/`, etc.

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

The unique-users outcome (`OUTCOME_VAR = 'unique_users'`) counts distinct cardholders per ZIP3-month, isolating the extensive margin. This shows excellent pre-treatment fit in synthetic control—Chicago tracks synthetic almost exactly through Sep 2023, then falls ~11% below post-tax.

## Current Results (Synthetic Control)

- **Pre-treatment RMSE**: 0.018
- **Pre-tax gap**: +0.001 (essentially zero)
- **Post-tax gap**: −0.112
- **Treatment effect**: −11.2 log points (~11% reduction in unique subscribers)

See `output/unique_users/15to25/all_merchants/synthetic_control_results.md` for full writeup.

## Archive

`archive/` contains deprecated scripts:
- `chicago_synth_control.py` - Standalone SC (now integrated into `chicago_did.py`)
- `ai_subscription_analysis.py` - Earlier exploratory analysis
- `chatgpt_timeseries_analysis.py` - Earlier time series work
