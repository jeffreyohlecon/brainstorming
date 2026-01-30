# TODO

## Current (Jan 30, 2026)

- [x] **ZIP3 fix applied** — Using `chatgpt_card_info_2025_12_26.parquet` (from card table). Old demographics CSV was contaminated.
- [x] **Re-ran main pipeline** — `run_analysis.py` completed with correct ZIP3. Results: ratio=8.96, gap=-10%.
- [ ] **Placebo tests** — Running via `nohup` (PID 45855). Survives closing terminal. Kill with `kill 45855`. ~6 hours total. Restarted Jan 30 ~10pm.
- [ ] **Synth sensitivity: price definition** — Testing one change at a time (keep all covariates fixed).
  - **Current test**: `pre_median_price` (mean of monthly medians) → `pre_mean_price` (simple mean of all pre-period transaction amounts)
  - **Baseline**: ratio=8.96, gap=-10%, pre-RMSPE=0.014
  - **Rule**: Only change ONE thing per test. If results break, revert before trying next change.
  - **Files touched**: `export_synth_data.py`, `chicago_synth.do`, `export_synth_results_tex.py`
- [ ] **Revert price definition** — Switch back to `pre_median_price` once sensitivity check is logged and decided.
- [ ] **Make covariate list configurable** — Toggle the matching covariates (Table 1 list) via `config.py` or a single source of truth (shared by Stata + Python).
- [ ] **Diagnose sensitivity** — Figure out why pre/post RMSPE ratio dropped from 8.96 to ~3.9 with `pre_mean_price`. Track the exact definition used previously (check GitHub/pastes) and write down the precise formulas.
- [ ] **Rollback reference** — Prior "good" RMSPE ratio (8.96) appears in commit `cae2744` (Jan 30, 2026 16:01) in `memos/synth_macros.tex`. Use `git checkout cae2744 -- memos/synth_macros.tex` as a reference point for the old results.
- [ ] **What broke + fix path** — Likely drivers: (1) price covariate changed from `pre_median_price` to `pre_mean_price`; (2) outcome/covariate balance row labels switched to `Log Transactions` (verify `OUTCOME_VAR`). Fix path: restore `pre_median_price` definition, confirm `OUTCOME_VAR` matches the old run, regenerate `synth_panel.dta`, rerun `chicago_synth.do`, then `export_synth_results_tex.py` and confirm `\rmspeRatio` ≈ 8.9x.
- [ ] **Sanity check sensitivity** — Sit down with pen/paper to assess whether this level of sensitivity to the price covariate is a substantive concern vs. a side effect of other silent changes. Verify no other spec changes slipped in.
- [ ] **Covariate validation OLS** — Ran `code/analysis/covariate_validation_ols.py`.
  - Output: `output/trans/15to25/all_merchants/exploratory/covariate_validation_ols*.csv`
  - Output: `output/trans/15to25/all_merchants/exploratory/covariate_validation_correlations.csv`
  - Output: `output/trans/15to25/all_merchants/exploratory/covariate_validation_scatterplots.png`
  - Output: `output/trans/15to25/all_merchants/exploratory/covariate_validation_partial_r2.csv`
  - Note: all predictors look significant; price has wrong sign.
  - Note: `pct_young` has low correlation; candidate to drop vs median_age.
  - Next: decide covariate set (avoid overfitting).
  - Partial R2 (delta in full-model R2 from dropping each covariate):
    median_age 0.053, pct_college 0.020, pct_hh_100k 0.017,
    pre_mean_price 0.016, pct_broadband 0.014, pct_young 0.012.
- [ ] **LASSO selection** — Run `code/analysis/covariate_validation_ols.py --lasso` (failed once with sandbox signal). Likely needs scikit-learn.
  - Update: scikit-learn is installed but `--lasso` still crashes (Signal 6).
- [ ] **Selection discipline** — LASSO is probably the right way to do this, but pause: read Abadie and think before touching more code. We might want better predictors.
- [ ] **Hard rule** — Never use log(x+1); use log(x) only (handled in code). If zeros exist, fix data/model instead.

### Currently Running Jobs

| PID | Job | Notes |
|-----|-----|-------|
| 45855 | Stata placebo tests | nohup, survives closing Claude |
| 40956 | `compute_monthly_zip3.py --full` | Claude shell wrapper (parent 40943) |
| 43466 | `plot_two_row_examples.py` | Claude shell wrapper (parent 43454) |

**To run**:
```bash
/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp -b do chicago_synth_placebo_topq.do
```

**Monitor progress**:
```bash
python3 code/analysis/monitor_placebo.py
```

### After Placebos Complete

1. Regenerate plots: `PYTHONPATH=. python3 code/robustness/run_placebo_plots.py 2`
2. Compile memo: `cd memos && latexmk -pdf synthetic_control_results.tex`

---

## Backlog

- [ ] **Covariate validation OLS** — Run pooled OLS of pre-period log(outcome) on demographics across all ZIP3s. Shows which covariates actually predict ChatGPT adoption (à la Abadie Table 1). May justify dropping redundant covariates (college/income likely collinear).
- [ ] **Robustness: transactions per panel member** — Normalize outcome by number of constant-panel cardholders per ZIP3 (like Abadie's "per capita" normalization).
- [x] **Monthly ZIP3 from address_map** — See [zip3_fixes.md](zip3_fixes.md) for full details. Script running, validated on bouncers.

## Memo Automation

| Component | Status |
|-----------|--------|
| `synth_macros.tex` | ✓ RMSPE, gap, donors, balance |
| `trans_user_macros.tex` | ✓ Trans per user stats |
| Placebo p-value | ✗ After placebos |

## Cleanup

- [ ] Delete `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/exploratory/` (old flat folder)

---

## Completed Reference Docs

These are finished investigations, not active workstreams. Keep for future reference.

| Doc | Summary |
|-----|---------|
| [zip3_fixes.md](zip3_fixes.md) | ZIP3 assignment investigation (Jan 2026). Validated address_map, built monthly modal approach, documented data quality issues. |
