# Brainstorming Project

## Data Handling
- **Never load GBs of data into memory at once**: The ChatGPT transaction parquet files are large. Process in chunks, sample first, or use lazy loading. A past instance crashed by loading too much data.
- Data lives in `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data`
- Main data loader: `load_chatgpt_data.py`
- **No symlinks**: Don't use symlinks to redirect folders. Keep real folders in their expected locations.

## Output Locations
- **All output goes to Dropbox**: `/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/{outcome}/{amount}/{merchants}/`
  - Structure mirrors settings in `load_chatgpt_data.py`
  - Example: `unique_users/15to25/all_merchants/` for current defaults
  - Use `get_output_dir()` from `load_chatgpt_data.py` to get the correct path
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
