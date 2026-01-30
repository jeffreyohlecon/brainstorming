#!/usr/bin/env python3
"""
Master pipeline: export data -> run SC -> generate figures -> export macros.

Usage:
    python run_analysis.py           # Full pipeline
    python run_analysis.py --quick   # Skip Stata (use existing results)
"""

import subprocess
import sys
from pathlib import Path

STATA = '/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp'
PROJECT_DIR = Path(__file__).parent


def run(cmd, desc):
    """Run a command and print status."""
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print(f"FAILED: {desc}")
        sys.exit(1)
    print(f"DONE: {desc}\n")


def main():
    quick = '--quick' in sys.argv

    # Step 1: Export panel data (invalidates old placebo results)
    from config import get_output_dir
    outdir = get_output_dir()
    placebo_files = [
        outdir / 'placebo_results_topq.dta',
        outdir / 'placebo_series_long.dta',
        outdir / 'placebo_results_new.dta',
    ]
    for f in placebo_files:
        if f.exists():
            f.unlink()
            print(f"Deleted stale: {f.name}")

    run('python3 code/analysis/export_synth_data.py', 'Export panel data to Stata')

    # Step 2: Run main synthetic control (skip if --quick)
    if not quick:
        run(f'{STATA} -b do chicago_synth.do', 'Run synthetic control')
    else:
        print("\n[--quick] Skipping Stata, using existing results\n")

    # Step 3: Extract donor weights from log
    run('python3 code/analysis/extract_donor_weights.py', 'Extract donor weights')

    # Step 4: Generate main SC figures
    run('python3 code/analysis/plot_synth_with_o1.py', 'Plot SC with event lines')
    run('python3 code/analysis/chicago_spaghetti_plot.py', 'Plot donor spaghetti')

    # Step 5: Exploratory plots
    run('python3 code/exploratory/detect_tax_changes.py', 'Detect tax changes')
    run('python3 code/plot_chicago_vs_rest.py', 'Chicago vs rest raw plot')

    # Step 6: Placebo robustness plots (if placebo results exist)
    from config import get_output_dir
    placebo_results = get_output_dir() / 'placebo_results_topq.dta'
    if placebo_results.exists():
        run('python3 code/robustness/run_placebo_plots.py 2', 'Placebo plots (2x)')
    else:
        print("\n[Skipping placebo plots - run placebo tests first]\n")

    # Step 7: Export LaTeX macros
    run('python3 code/analysis/export_synth_results_tex.py', 'Export LaTeX macros')

    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print("="*60)
    print("\nTo compile memo:")
    print("  cd memos && latexmk -pdf synthetic_control_results.tex")
    print("\nTo run placebo tests (slow):")
    print(f"  {STATA} -b do chicago_synth_placebo_topq.do")


if __name__ == "__main__":
    main()
