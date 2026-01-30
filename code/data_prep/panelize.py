#!/usr/bin/env python3
"""
Panelization: Implement CEdge's "Constant Individual Panel" methodology.
Keep only cardlinkids with ≥1 transaction in every 70-day window.

Memory-conscious: reads parquet in chunks, processes incrementally.
"""

import pyarrow.parquet as pq
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")

# Study period
STUDY_START = pd.Timestamp('2023-03-01')
STUDY_END = pd.Timestamp('2024-11-30')
WINDOW_DAYS = 70


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def generate_windows(start, end, window_days):
    """Generate non-overlapping 70-day windows covering the study period.

    If the final window would be shorter than window_days, merge it into the previous window.
    """
    windows = []
    current = start
    while current < end:
        window_end = current + pd.Timedelta(days=window_days)
        if window_end >= end:
            # Last window - extend to end
            windows.append((current, end))
            break
        else:
            # Check if remaining period after this window would be too short
            remaining = (end - window_end).days
            if remaining < window_days:
                # Merge: extend this window to end
                windows.append((current, end))
                break
            else:
                windows.append((current, window_end))
                current = window_end
    return windows


def load_card_info():
    """Load card info and filter out USA1 debit cards."""
    log("Loading card info...")
    card_info = pd.read_parquet(DATA_DIR / "chatgpt_card_info_2025_12_26.parquet")
    log(f"  Total cards: {len(card_info):,}")

    # Exclude USA1 debit cards (source_group == 1 AND cardtype == 'DEBIT')
    usa1_debit = (card_info['source_group'] == 1) & (card_info['cardtype'] == 'DEBIT')
    card_info = card_info[~usa1_debit].copy()
    log(f"  After excluding USA1 debit: {len(card_info):,}")

    return card_info[['cardid', 'cardlinkid']]


def get_cardlinkids_in_window(parquet_path, cardid_to_linkid, win_start, win_end):
    """Stream through parquet and collect cardlinkids active in this window.

    Reads row groups one at a time to limit memory.
    """
    valid_cardids = set(cardid_to_linkid.keys())
    active_linkids = set()

    pf = pq.ParquetFile(parquet_path)

    for i in range(pf.metadata.num_row_groups):
        # Read one row group at a time
        table = pf.read_row_group(i)
        chunk = table.to_pandas()

        # Filter to valid cardids
        chunk = chunk[chunk['cardid'].isin(valid_cardids)]

        # Filter to date window
        chunk['trans_date'] = pd.to_datetime(chunk['trans_date'])
        chunk = chunk[(chunk['trans_date'] >= win_start) & (chunk['trans_date'] <= win_end)]

        if len(chunk) > 0:
            # Map to cardlinkid and collect
            linkids = chunk['cardid'].map(cardid_to_linkid).unique()
            active_linkids.update(linkids)

        del chunk, table

    return active_linkids


def main():
    log("=" * 60)
    log("PANELIZATION: Constant Individual Panel")
    log("=" * 60)

    # Step 1: Load card info
    card_info = load_card_info()
    cardid_to_linkid = dict(zip(card_info['cardid'], card_info['cardlinkid']))
    all_cardlinkids = set(card_info['cardlinkid'].unique())
    log(f"  Unique cardlinkids: {len(all_cardlinkids):,}")
    del card_info

    # Step 2: Generate windows
    windows = generate_windows(STUDY_START, STUDY_END, WINDOW_DAYS)
    log(f"Generated {len(windows)} windows:")
    for i, (start, end) in enumerate(windows):
        log(f"  Window {i+1}: {start.date()} to {end.date()}")

    # Step 3: For each window, find active cardlinkids
    # Start with all cardlinkids, then intersect with each window's active set
    panel_members = all_cardlinkids.copy()

    activity_files = [
        DATA_DIR / "activity_dates_2023.parquet",
        DATA_DIR / "activity_dates_2024.parquet"
    ]

    for i, (win_start, win_end) in enumerate(windows):
        log(f"Processing window {i+1}: {win_start.date()} to {win_end.date()}")

        window_active = set()
        for f in activity_files:
            log(f"  Scanning {f.name}...")
            active = get_cardlinkids_in_window(f, cardid_to_linkid, win_start, win_end)
            window_active.update(active)
            log(f"    Found {len(active):,} active cardlinkids")

        # Intersect: keep only those active in this window
        before = len(panel_members)
        panel_members = panel_members.intersection(window_active)
        log(f"  Window {i+1}: {len(window_active):,} active, panel now {len(panel_members):,} (dropped {before - len(panel_members):,})")

    # Step 4: Save panel members
    output_path = DATA_DIR / "panel_cardlinkids.parquet"
    panel_df = pd.DataFrame({'cardlinkid': list(panel_members)})
    panel_df.to_parquet(output_path, index=False)
    log(f"Saved {len(panel_df):,} panel cardlinkids to {output_path}")

    log("=" * 60)
    log("DONE")
    log("=" * 60)


if __name__ == "__main__":
    main()
