# TODO

## Current (Jan 30, 2026)

- [x] **ZIP3 fix applied** — Using `chatgpt_card_info_2025_12_26.parquet` (from card table). Old demographics CSV was contaminated.
- [x] **Re-ran main pipeline** — `run_analysis.py` completed with correct ZIP3. Results: ratio=8.96, gap=-10%.
- [ ] **Placebo tests** — Running via `nohup` (PID 45855). Survives closing terminal. Kill with `kill 45855`. ~6 hours total. Restarted Jan 30 ~10pm.

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
