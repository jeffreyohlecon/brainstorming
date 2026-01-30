#!/usr/bin/env python3
"""
Extract donor weights from Stata synth log file.
Parses the Unit Weights table from chicago_synth.log.
"""

import re
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from load_chatgpt_data import get_output_dir, log

# ZIP3 to area name mapping
ZIP3_NAMES = {
    '900': 'Los Angeles, CA',
    '277': 'Raleigh, NC',
    '830': 'Wyoming',
    '785': 'Rio Grande Valley, TX',
    '865': 'Flagstaff, AZ',
    '303': 'Atlanta, GA',
    '100': 'Manhattan, NY',
    '606': 'Chicago, IL',
    '943': 'Palo Alto, CA',
    '786': 'Austin, TX',
    '738': 'Tulsa, OK',
    '273': 'Greensboro, NC',
    '247': 'Roanoke, VA',
    '348': 'Macon, GA',
    '765': 'Lafayette, IN',
    '715': 'Eau Claire, WI',
    '527': 'Rochester, MN',
    '631': 'Nassau, NY',
    '258': 'Beckley, WV',
    '387': 'Columbus, GA',
    '588': 'Rapid City, SD',
    '711': 'Shreveport, LA',
    '803': 'Columbia, SC',
    '288': 'Asheville, NC',
}


def extract_weights_from_log(log_path):
    """Parse Unit Weights section from Stata log."""
    text = log_path.read_text()

    # Find the Unit Weights section
    match = re.search(r'Unit Weights:.*?-{20,}(.*?)-{20,}', text, re.DOTALL)
    if not match:
        raise ValueError("Could not find Unit Weights section in log")

    weights_text = match.group(1)

    # Parse lines like "      247 |        .171"
    weights = []
    for line in weights_text.split('\n'):
        # Match: whitespace, number, pipe, whitespace, number (possibly with leading dot)
        m = re.match(r'\s*(\d+)\s*\|\s*([\d.]+)', line)
        if m:
            zip3_id = int(m.group(1))
            weight = float(m.group(2))
            if weight > 0.001:  # Only positive weights
                weights.append({'zip3_id': zip3_id, 'weight': weight})

    return pd.DataFrame(weights)


def main():
    repo_dir = Path(__file__).parent.parent
    log_path = repo_dir / 'chicago_synth.log'

    if not log_path.exists():
        raise FileNotFoundError(f"Run chicago_synth.do first: {log_path}")

    # Extract weights from log
    weights = extract_weights_from_log(log_path)
    log(f"Found {len(weights)} donors with positive weight")

    # Load ZIP3 mapping
    mapping_path = repo_dir / 'data' / 'zip3_id_mapping.csv'
    if mapping_path.exists():
        mapping = pd.read_csv(mapping_path, dtype={'zip3': str})
        weights = weights.merge(mapping, on='zip3_id', how='left')
    else:
        weights['zip3'] = weights['zip3_id'].astype(str).str.zfill(3)

    # Ensure zip3 is string and zero-padded
    weights['zip3'] = weights['zip3'].astype(str).str.zfill(3)

    # Sort by weight descending
    weights = weights.sort_values('weight', ascending=False)

    # Add area names
    weights['area'] = weights['zip3'].map(ZIP3_NAMES).fillna('Unknown')

    # Display top donors
    print("\nTop Donors:")
    print(weights[['zip3', 'weight', 'area']].head(15).to_string(index=False))

    # Save to output directory
    outdir = get_output_dir()
    out_path = outdir / 'synth_donor_weights.csv'
    weights[['zip3', 'zip3_id', 'weight']].to_csv(out_path, index=False)
    log(f"Saved: {out_path}")

    return weights


if __name__ == "__main__":
    main()
