# Brainstorming Project

## Data Handling
- **Never load GBs of data into memory at once**: The ChatGPT transaction parquet files are large. Process in chunks, sample first, or use lazy loading. A past instance crashed by loading too much data.
- Data lives in `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data`
- Config: `config.py` (settings), `load_data.py` (data loading)
- **No symlinks**: Don't use symlinks to redirect folders. Keep real folders in their expected locations.
- **Always use nohup for long jobs**: Stata placebo tests, etc. take hours. Run with `nohup ... &` so they survive if user closes Claude. Note the PID in `todo.md` so it can be killed later.

## Output Locations
- **All output goes to Dropbox**: `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/{outcome}/{amount}/{merchants}/`
  - Structure mirrors settings in `config.py`
  - Example: `unique_users/15to25/all_merchants/` for current defaults
  - Use `get_output_dir()` from `config.py` to get the correct path
- **Save at exactly the right level**: Output should be saved at exactly its level of sample specificity—no higher, no lower.
  - Sample-specific analysis (e.g., SC results for trans/15to25) → `output/trans/15to25/all_merchants/`
  - Data validation plots (not sample-specific) → `output/` root
  - Exploratory analysis for a sample → `output/.../exploratory/`
- Derived data (DTAs, CSVs for reuse): `/Users/jeffreyohl/Dropbox/LLM_PassThrough/derived_data`
- **No local output folder** in this repo
- **Don't copy files into repo**: Reference figures/data from Dropbox directly in LaTeX using absolute paths. Don't `cp` files into the repo.

## Current Work
- Chicago PPLTT synthetic control analysis
- Placebo tests running via `chicago_synth_placebo_topq.do` (restarted, ~10/185 done)
- Plots at 2x, 5x, 20x thresholds generated in `output/.../synthetic_placebo_robustness/`
- New metric: `gap_ratio = post_gap / pre_RMSPE` (signed treatment effect / noise)
- Monitor progress: `python3 monitor_placebo.py`
- Regenerate plots: `python3 plot_placebo_robustness.py` (change THRESHOLD_MULT for different thresholds)
