#!/usr/bin/env python3
"""
Central config for ChatGPT analysis.
All scripts import from here to ensure consistent settings.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data")

# Filter modes (by transaction amount)
FILTER_PLUS_RANGE = 'plus_range'    # $20-22 (ChatGPT Plus price range with tax variation)
FILTER_WIDE_RANGE = 'wide_range'    # $15-25 (wider range to capture more subscriptions)
FILTER_OUTSIDE = 'outside'          # Outside $20-22 (API, partial, other)
FILTER_ALL = 'all'                  # No amount filter

# Current filter (change this to switch modes)
AMOUNT_FILTER = FILTER_WIDE_RANGE

# Merchant filter
USE_TOP_MERCHANTS = False  # If True, restrict to top 30 merchants
TOP_N_MERCHANTS = 30

# Outcome variable
OUTCOME_SPEND = 'spend'        # log(total_spend)
OUTCOME_TRANSACTIONS = 'trans' # log(n_transactions)
OUTCOME_USERS = 'unique_users' # log(n_unique_cardholders)
OUTCOME_VAR = OUTCOME_TRANSACTIONS  # Changed from OUTCOME_USERS Jan 2026

# Panel filter (constant individuals)
USE_PANEL = True  # If True, restrict to cardlinkids active in all 70-day windows


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_output_dir():
    """Return output directory path based on current filter settings.

    Structure: output/{outcome}/{amount}/{merchants}/
    All output goes to Dropbox for single source of truth.
    """
    base = Path('/Users/jeffreyohl/Dropbox/LLM_PassThrough/output')

    # Outcome
    outcome_dir = OUTCOME_VAR  # 'spend' or 'trans'

    # Amount filter
    if AMOUNT_FILTER == FILTER_PLUS_RANGE:
        amount_dir = '20to22'
    elif AMOUNT_FILTER == FILTER_WIDE_RANGE:
        amount_dir = '15to25'
    elif AMOUNT_FILTER == FILTER_OUTSIDE:
        amount_dir = 'outside20to22'
    else:
        amount_dir = 'all'

    # Merchant filter
    merchant_dir = 'top30' if USE_TOP_MERCHANTS else 'all_merchants'

    out_path = base / outcome_dir / amount_dir / merchant_dir
    out_path.mkdir(parents=True, exist_ok=True)
    return out_path


def get_exploratory_dir():
    """Return exploratory output directory (subfolder of main output dir)."""
    out_path = get_output_dir() / 'exploratory'
    out_path.mkdir(parents=True, exist_ok=True)
    return out_path


def get_filter_suffix():
    """Return suffix for filenames based on current filter (deprecated, use get_output_dir)."""
    suffix = ''
    if USE_TOP_MERCHANTS:
        suffix += '_top30'
    if AMOUNT_FILTER == FILTER_PLUS_RANGE:
        suffix += '_20to22'
    elif AMOUNT_FILTER == FILTER_WIDE_RANGE:
        suffix += '_15to25'
    elif AMOUNT_FILTER == FILTER_OUTSIDE:
        suffix += '_outside20to22'
    else:
        suffix += '_all'
    suffix += f'_{OUTCOME_VAR}'
    return suffix


def get_filter_title():
    """Return string for figure titles based on current filter."""
    parts = []
    if USE_PANEL:
        parts.append('constant panel')
    if USE_TOP_MERCHANTS:
        parts.append(f'top {TOP_N_MERCHANTS} merchants')
    if AMOUNT_FILTER == FILTER_PLUS_RANGE:
        parts.append(r'\$20-\$22 transactions')
    elif AMOUNT_FILTER == FILTER_WIDE_RANGE:
        parts.append(r'\$15-\$25 transactions')
    elif AMOUNT_FILTER == FILTER_OUTSIDE:
        parts.append(r'outside \$20-\$22 transactions')
    if parts:
        return '(' + ', '.join(parts) + ')'
    return ''


def get_outcome_column():
    """Return the column name to use as outcome."""
    if OUTCOME_VAR == OUTCOME_SPEND:
        return 'total_spend'
    elif OUTCOME_VAR == OUTCOME_USERS:
        return 'n_users'
    else:
        return 'n_transactions'


def get_log_outcome_column():
    """Return the log outcome column name for synth/plots."""
    if OUTCOME_VAR == OUTCOME_USERS:
        return 'log_users'
    else:
        return 'log_trans'


def get_outcome_label():
    """Return human-readable label for the current outcome."""
    if OUTCOME_VAR == OUTCOME_USERS:
        return 'Log Unique Users'
    elif OUTCOME_VAR == OUTCOME_TRANSACTIONS:
        return 'Log Transactions'
    else:
        return 'Log Total Spend'
