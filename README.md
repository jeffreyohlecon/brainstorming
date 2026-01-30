# Chicago PPLTT Analysis

Analysis of Chicago's 9% Personal Property Lease Transaction Tax (PPLTT) effect on ChatGPT subscriptions (Oct 2023).

## Output Location

All output: `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/unique_users/15to25/all_merchants/`

No local output folder in this repo.

### Placebo Robustness Plots

`{outdir}/synthetic_placebo_robustness/` contains:

| File | Description |
|------|-------------|
| `placebo_spaghetti_{N}x.png` | Gap time series: Chicago (black) vs placebos (gray) |
| `placebo_histogram_{N}x.png` | Distribution of gap ratios with Chicago marked |
| `rmspe_vs_population_{N}x.png` | RMSPE ratio vs ZIP3 population |
| `rmspe_vs_pre_users_{N}x.png` | RMSPE ratio vs pre-treatment users |
| `gap_ratio_vs_pre_users_{N}x.png` | Gap ratio vs pre-treatment users |

Where `{N}x` = threshold (2x, 5x, 20x). Generate with `python code/robustness/run_placebo_plots.py 2`.

## Pipeline

### Quick Start
```bash
python run_analysis.py        # Full pipeline (export → Stata → plots → macros)
python run_analysis.py --quick  # Skip Stata, use existing results
```

### Manual Steps

**Step 1: Export panel data**
```bash
python code/analysis/export_synth_data.py
# Creates: data/synth_panel.dta
```

**Step 2: Run synthetic control**
```bash
/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp -b do chicago_synth.do
# Output: {outdir}/synth_results.dta
```

**Step 3: Extract weights and generate plots**
```bash
python code/analysis/extract_donor_weights.py   # Log → synth_donor_weights.csv
python code/analysis/plot_synth_with_o1.py      # SC plot
python code/analysis/chicago_spaghetti_plot.py  # Donor comparison
python code/analysis/export_synth_results_tex.py # → memos/synth_macros.tex
```

**Step 4: Placebo tests (slow, ~6 hours)**
```bash
/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp -b do chicago_synth_placebo_topq.do
python code/analysis/monitor_placebo.py  # Check progress
```

## Key Files

| File | Purpose |
|------|---------|
| `run_analysis.py` | Master pipeline script |
| `load_chatgpt_data.py` | Shared data loading + settings |
| `chicago_synth.do` | Main SC |
| `chicago_synth_placebo_topq.do` | Placebo tests |
| `memos/synth_macros.tex` | Auto-generated macros |

## LaTeX Macros

Scripts that generate `.tex` macro files for the memo:

| Script | Output | In Pipeline? |
|--------|--------|--------------|
| `code/analysis/export_synth_results_tex.py` | `memos/synth_macros.tex` | ✅ Yes |
| `code/exploratory/trans_per_user_macros.py` | `output/.../exploratory/trans_user_macros.tex` | ❌ Run separately |

After placebos complete, regenerate plots:
```bash
PYTHONPATH=. python3 code/robustness/run_placebo_plots.py 2
```

## Code Organization

### `code/analysis/` — Main SC Pipeline

| File | Purpose |
|------|---------|
| `export_synth_data.py` | Panel → Stata |
| `extract_donor_weights.py` | Parse Stata log → donor weights CSV |
| `plot_synth_with_o1.py` | SC plot |
| `chicago_spaghetti_plot.py` | Donor comparison plot |
| `monitor_placebo.py` | Live placebo progress |
| `export_synth_results_tex.py` | Results → LaTeX macros |

### `code/data_prep/` — Data Preparation

| File | Purpose |
|------|---------|
| `panelize.py` | Creates constant individual panel (cardlinkids active in all 70-day windows). One-time preprocessing for replicability. |
| `get_zip3_demographics.py` | Aggregates ACS demographics from ZCTA to ZIP3 |
| `explore_tv_demographics.py` | Validates time-varying demographics file (`chatgpt_demographics_tv.parquet`) |

### `code/robustness/` — Robustness Checks

**Dependency**: `run_placebo_plots.py` requires `chicago_synth_placebo_topq.do` to have run first (generates `placebo_series_long.dta` and log file). Can run mid-job with partial results—use looser threshold (e.g., 20x) if few placebos complete.

| File | Run? | Purpose |
|------|------|---------|
| `run_placebo_plots.py` | **Yes** | Entry point for placebo plots: `python run_placebo_plots.py 2` (2x threshold) |
| `chicago_sc_robustness.py` | No | Stale. Was leave-k-out robustness; should be reimplemented in Stata. |
| `helpers/plot_placebo_robustness.py` | No | Histogram + scatter plots (called by `run_placebo_plots.py`) |
| `helpers/plot_placebo_spaghetti.py` | No | Gap time series plot (called by `run_placebo_plots.py`) |
| `helpers/plot_placebo_unit.py` | No | Single-unit SC plot (called by `run_placebo_plots.py`) |

### `code/exploratory/` — Exploratory Analysis

| File | Purpose |
|------|---------|
| `median_price_by_zip3.py` | Plots median transaction price for any ZIP3. Useful for checking if high-RMSPE placebo units have tax-induced price jumps. |
| `detect_tax_changes.py` | Scans all ZIP3s for price changes between Mar 2023 and Nov 2024 |
| `quick_zip_compare.py` | Compare any two ZIP3s: `python quick_zip_compare.py 606 077` |
| `national_price_buckets.py` | National time series by price bucket |
| `chicago_raw_counts.py` | Raw time series: Chicago vs control mean |
| `chicago_chatgpt_analysis.py` | Descriptive plots for Chicago |

## Matching Variables

**Demographics**: pct_college, pct_hh_100k, pct_young, median_age, median_income, pct_stem, pct_broadband

**Pre-treatment outcomes**: pre_mean_early (Mar–Jun), pre_mean_late (Jul–Sep), pre_median_price

## Sample

- **Treatment**: ZIP3 606 (Chicago), Oct 2023
- **Donor pool**: ~740 ZIP3s
- **Period**: Mar 2023 – Nov 2024
- **Filter**: $15–25 transactions (Plus range)
- **Panel**: Constant individuals (all 70-day windows)

## Data Sources

- **Transactions**: `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/`
- **Demographics**: ACS 5-year 2022, ZCTA → ZIP3

### ZIP3 Assignment Options

Two approaches for assigning ZIP3 to cardids. See [zip3_fixes.md](zip3_fixes.md) for details.

| Method | File | Description |
|--------|------|-------------|
| **Snapshot** (current) | `chatgpt_card_info_2025_12_26.parquet` | ZIP3 from Dec 2025 card table snapshot. Simple but assigns current location, not location at transaction time. |
| **Monthly modal** (new) | `cardid_monthly_zip3.parquet` | Modal ZIP3 per card-month from `cardid_address_map`. Merge on `[cardid, year_month]` to get ZIP3 at transaction time. Handles movers correctly. |

**Current implementation**: Snapshot method. Monthly modal is validated and computing (Jan 30, 2026).

**Note**: Do NOT use `chatgpt_demographics_2023_2024_2025.csv` (contaminated) or raw `cardid_address_map` (has daily bouncing noise).

## Flexible Outcome Variable (Implemented Jan 2026)

**Goal**: Change outcome in ONE place (`load_chatgpt_data.py`) and all downstream inherits.

**Architecture**:
```
load_chatgpt_data.py     ← Single source of truth (OUTCOME_VAR setting)
        ↓
run_analysis.py          ← Master pipeline
        ↓
export_synth_data.py     ← Writes panel + data/synth_config.do
        ↓
chicago_synth.do         ← Reads synth_config.do, uses $outcome_var
        ↓
plots, exports, etc.
```

### How to Switch Outcomes

1. Edit `load_chatgpt_data.py`: change `OUTCOME_VAR = OUTCOME_TRANSACTIONS` to `OUTCOME_VAR = OUTCOME_USERS`
2. Run `python run_analysis.py` - all output goes to the appropriate folder
3. Update `memos/synthetic_control_results.tex`: change `\figpath` from `trans` to `unique_users`

### Key Functions (load_chatgpt_data.py)

| Function | Returns |
|----------|---------|
| `get_output_dir()` | `/output/{outcome}/15to25/all_merchants/` |
| `get_exploratory_dir()` | `{output_dir}/exploratory/` |
| `get_log_outcome_column()` | `'log_trans'` or `'log_users'` |
| `get_outcome_label()` | `'Log Transactions'` or `'Log Unique Users'` |

### Adding New Outcomes

1. Add constant in `load_chatgpt_data.py` (e.g., `OUTCOME_SPEND = 'spend'`)
2. Add case to `get_log_outcome_column()` and `get_outcome_label()`
3. Add the log column in `export_synth_data.py`

### Compile Memos
```bash
cd memos && latexmk -pdf synthetic_control_results.tex
```
