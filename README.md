# Chicago PPLTT Analysis

Analysis of Chicago's 9% Personal Property Lease Transaction Tax (PPLTT) effect on ChatGPT subscriptions (Oct 2023).

## Key Findings

**Price pass-through**: Clear. Chicago median transaction jumps $20 → $21.20 at Oct 2023. Control areas stay flat at $20.

**Quantity effect**: Confounded. Chicago tracks Manhattan perfectly in log(users). The SC "effect" appears to be a big-city phenomenon, not tax-specific.

**Identification problem**: Manhattan (no new tax in Oct 2023, already taxed at ~8.5%) shows similar SC divergence. Big cities share confounds (Enterprise adoption, saturation) that smaller donors can't replicate.

## Latest SC Results

| Metric | Value |
|--------|-------|
| Pre-RMSPE | 0.027 |
| Post-RMSPE | 0.148 |
| RMSPE ratio | 5.56 |
| Post-treatment gap | −0.118 (~11%) |
| Top donors | LA (46%), Raleigh (17%), Wyoming (11%), Atlanta (11%) |
| Placebo p-value | TBD (running) |

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

### `code/robustness/` — Robustness Checks

| File | Purpose |
|------|---------|
| `run_placebo_plots.py` | **Run all placebo plots**: `python run_placebo_plots.py 2` (2x threshold) |
| `plot_placebo_unit.py` | Plot SC for a single placebo unit: `python plot_placebo_unit.py 077` |
| `chicago_sc_robustness.py` | Leave-k-out robustness checks |
| `helpers/` | Internal scripts called by `run_placebo_plots.py` (don't run directly) |

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

## TODO

- [x] Add pre_median_price matching
- [ ] **Placebo tests with price matching** ← RUNNING (incremental, resumes on crash)
- [x] Find other ZIP3s with tax changes (5% price jump) — only Chicago exceeds 5%; Manhattan +2.6%
- [ ] Restrict SC to big-city donor pool
- [ ] **Exclude ZIP3s with mid-sample price changes** — Manhattan (+2.6%) may have started collecting NY sales tax mid-sample; could exclude donors with price change > X%, or use continuous treatment intensity based on price change

---

## CURRENT MIGRATION: unique_users → trans (Jan 2026)

**Goal**: Change outcome from log(unique cardids) to log(transactions). Transactions better capture quantity (multiple purchases from same person count).

### Output Structure After Migration

All outputs go to: `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/trans/15to25/all_merchants/`

```
trans/15to25/all_merchants/
├── chicago_synth_stata.png      # Main SC plot
├── chicago_spaghetti_donors.png # Donor comparison
├── synth_results.dta            # Stata output
├── synth_donor_weights.csv
├── synthetic_placebo_robustness/
│   ├── placebo_spaghetti_2x.png
│   ├── placebo_histogram_2x.png
│   └── ...
└── exploratory/                 # NEW: exploratory outputs now here
    ├── chicago_vs_rest_raw.png
    ├── quick_*.png
    ├── zip3_price_changes.csv
    └── zip3_price_change_funnel.png
```

### Files to Change

1. **load_chatgpt_data.py**
   - Change `OUTCOME_VAR = OUTCOME_USERS` → `OUTCOME_VAR = OUTCOME_TRANSACTIONS`
   - Add `get_exploratory_dir()` function returning `{output_dir}/exploratory/`

2. **code/analysis/export_synth_data.py**
   - Add `log_trans = np.log(panel['n_trans'])` column
   - Keep both columns (log_users, log_trans) for flexibility

3. **chicago_synth.do** and **chicago_synth_placebo_topq.do**
   - Change `log_users` → `log_trans` throughout
   - Update comments

4. **code/analysis/chicago_spaghetti_plot.py**
   - Change `log_users` → `log_trans`
   - Update y-axis label

5. **code/analysis/export_synth_results_tex.py**
   - Update COVARIATE_NAMES: 'Log users' → 'Log trans'

6. **Exploratory scripts** (use new `get_exploratory_dir()`):
   - `code/exploratory/detect_tax_changes.py`
   - `code/exploratory/quick_zip_compare.py`
   - `code/plot_chicago_vs_rest.py`

7. **memos/synthetic_control_results.tex**
   - Change `\figpath` from `unique_users` to `trans`
   - Update outcome description text throughout

### Regeneration Steps

After making changes:
```bash
python run_analysis.py        # Full pipeline
# Then rerun exploratory scripts manually
python code/exploratory/detect_tax_changes.py
python code/plot_chicago_vs_rest.py
```

### Verification

Check that these exist:
- `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/trans/15to25/all_merchants/chicago_synth_stata.png`
- `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/trans/15to25/all_merchants/exploratory/zip3_price_change_funnel.png`
- `memos/synthetic_control_results.pdf` compiles without missing figures

---

## Memo Automation

**Goal**: `run_analysis.py` regenerates all results → memos compile with no hardcoded values.

### Status

| Component | Status |
|-----------|--------|
| `synth_macros.tex` | ✓ RMSPE, gap, donors |
| `chicago_ppltt.tex` | ✓ Uses macros |
| `synthetic_control_results.tex` | ✓ Uses macros |
| Covariate balance | ✗ TODO: parse Stata log |
| Placebo p-value | ✗ TODO: after tests |

### Compile Memos
```bash
cd memos && latexmk -pdf synthetic_control_results.tex
```
