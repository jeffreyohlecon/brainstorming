#!/usr/bin/env python3
"""
Pipeline to regenerate all Chicago PPLTT analysis figures.

All scripts import from load_chatgpt_data.py for consistent sample restrictions.
To change filters, edit the settings in load_chatgpt_data.py:
  - AMOUNT_FILTER: 'plus_range' ($20-22), 'outside' (outside $20-22), 'all'
  - USE_TOP_MERCHANTS: True/False (top 30 merchants)
  - OUTCOME_VAR: 'spend' or 'trans'
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "chicago_chatgpt_analysis.py",  # Descriptive plots for Chicago
    "chicago_did.py",               # DiD event study
    "national_price_buckets.py",    # National price distribution
    "chicago_raw_counts.py",        # Raw time series comparison
]

PANEL_FILE = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/panel_cardlinkids.parquet")


def main():
    script_dir = Path(__file__).parent

    print("="*60)
    print("REGENERATING ALL FIGURES")
    print("="*60)

    # Run panelization only if panel file doesn't exist
    if not PANEL_FILE.exists():
        print(f"\n>>> Running panelize.py (panel file not found)...")
        result = subprocess.run(
            [sys.executable, script_dir / "panelize.py"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR in panelize.py:")
            print(result.stderr)
            return
        print("  Panel created.")
    else:
        print(f"\n>>> Skipping panelize.py (panel file exists: {PANEL_FILE.stat().st_mtime})")

    for script in SCRIPTS:
        script_path = script_dir / script
        if not script_path.exists():
            print(f"\n>>> Skipping {script} (not found)")
            continue

        print(f"\n>>> Running {script}...")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR in {script}:")
            print(result.stderr)
        else:
            lines = result.stdout.strip().split('\n')
            for line in lines[-5:]:
                print(f"  {line}")

    print("\n" + "="*60)
    print("DONE")
    print("="*60)


if __name__ == "__main__":
    main()
