#!/usr/bin/env python3
"""
Shared data loading for ChatGPT analysis.
All scripts import from here to ensure consistent filtering.
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
OUTCOME_VAR = OUTCOME_USERS    # Current setting

# Panel filter (constant individuals)
USE_PANEL = True  # If True, restrict to cardlinkids active in all 70-day windows

# Cache for top merchants (computed once on full sample)
_TOP_MERCHANTS_CACHE = None

# Cache for panel cardids
_PANEL_CARDIDS_CACHE = None


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_output_dir():
    """Return output directory path based on current filter settings.

    Structure: output/{outcome}/{amount}/{merchants}/
    """
    base = Path(__file__).parent / 'output'

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


def _get_top_merchants(trans_raw):
    """Get top N merchants by count from full sample (no amount filter)."""
    global _TOP_MERCHANTS_CACHE
    if _TOP_MERCHANTS_CACHE is not None:
        return _TOP_MERCHANTS_CACHE

    log(f"Computing top {TOP_N_MERCHANTS} merchants...")
    top = trans_raw['merchid'].value_counts().head(TOP_N_MERCHANTS).index.tolist()
    _TOP_MERCHANTS_CACHE = top
    return top


def _get_panel_cardids():
    """Get cardids belonging to panel cardlinkids (active in all 70-day windows)."""
    global _PANEL_CARDIDS_CACHE
    if _PANEL_CARDIDS_CACHE is not None:
        return _PANEL_CARDIDS_CACHE

    log("Loading panel cardlinkids...")
    panel_path = DATA_DIR / "panel_cardlinkids.parquet"
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel file not found: {panel_path}. Run panelize.py first.")

    panel = pd.read_parquet(panel_path)
    panel_linkids = set(panel['cardlinkid'])
    log(f"  Panel cardlinkids: {len(panel_linkids):,}")

    # Map to cardids via card_info
    card_info = pd.read_parquet(DATA_DIR / "chatgpt_card_info.parquet")
    # Exclude USA1 debit (same filter as panelize.py)
    usa1_debit = (card_info['source_group'] == 1) & (card_info['cardtype'] == 'DEBIT')
    card_info = card_info[~usa1_debit]

    panel_cards = card_info[card_info['cardlinkid'].isin(panel_linkids)]
    panel_cardids = set(panel_cards['cardid'])
    log(f"  Panel cardids: {len(panel_cardids):,}")

    _PANEL_CARDIDS_CACHE = panel_cardids
    return panel_cardids


def load_transactions(services=('chatgpt', 'openai'), years=(2023, 2024, 2025),
                      amount_filter=None, use_top_merchants=None, use_panel=None):
    """Load and filter ChatGPT transactions.

    amount_filter: 'subscriptions' (>=$20), 'api' (<$20), 'all' (no filter)
                   If None, uses module-level AMOUNT_FILTER setting.
    use_top_merchants: If None, uses module-level USE_TOP_MERCHANTS setting.
    use_panel: If None, uses module-level USE_PANEL setting.
    """
    if amount_filter is None:
        amount_filter = AMOUNT_FILTER
    if use_top_merchants is None:
        use_top_merchants = USE_TOP_MERCHANTS
    if use_panel is None:
        use_panel = USE_PANEL

    log("Loading transactions...")
    dfs = []
    for year in years:
        f = DATA_DIR / f"chatgpt_transactions_{year}.parquet"
        if f.exists():
            dfs.append(pd.read_parquet(f))
    trans = pd.concat(dfs, ignore_index=True)
    log(f"Total transactions: {len(trans):,}")

    # Filter to services
    trans = trans[trans['service'].str.lower().isin(services)]
    log(f"After service filter: {len(trans):,}")

    # Apply panel filter (constant individuals)
    if use_panel:
        before_panel = len(trans)
        panel_cardids = _get_panel_cardids()
        trans = trans[trans['cardid'].isin(panel_cardids)].copy()
        pct_kept = 100 * len(trans) / before_panel if before_panel > 0 else 0
        log(f"After panel filter: {len(trans):,} ({pct_kept:.1f}% of {before_panel:,})")

    # Convert types
    trans['trans_date'] = pd.to_datetime(trans['trans_date'])
    trans['trans_amount'] = pd.to_numeric(trans['trans_amount'], errors='coerce')

    # Apply top merchants filter BEFORE amount filter
    # (top merchants defined on full sample)
    if use_top_merchants:
        top_merchs = _get_top_merchants(trans)
        trans = trans[trans['merchid'].isin(top_merchs)].copy()
        log(f"After top {TOP_N_MERCHANTS} merchants filter: {len(trans):,}")

    # Apply amount filter
    if amount_filter == FILTER_PLUS_RANGE:
        trans = trans[(trans['trans_amount'] >= 20) & (trans['trans_amount'] <= 22)].copy()
        log(f"After $20-22 filter: {len(trans):,}")
    elif amount_filter == FILTER_WIDE_RANGE:
        trans = trans[(trans['trans_amount'] >= 15) & (trans['trans_amount'] <= 25)].copy()
        log(f"After $15-25 filter: {len(trans):,}")
    elif amount_filter == FILTER_OUTSIDE:
        trans = trans[(trans['trans_amount'] < 20) | (trans['trans_amount'] > 22)].copy()
        log(f"After outside $20-22 filter: {len(trans):,}")
    else:
        log(f"No amount filter applied: {len(trans):,}")

    return trans


def load_demographics():
    """Load demographics for zip3 matching."""
    log("Loading demographics...")
    demo = pd.read_csv(DATA_DIR / "chatgpt_demographics_2023_2024_2025.csv", low_memory=False)
    log(f"Demographics: {len(demo):,} cardids")
    return demo


def load_with_zip3(services=('chatgpt', 'openai'), years=(2023, 2024, 2025),
                   amount_filter=None, use_top_merchants=None, use_panel=None):
    """Load transactions merged with zip3 from demographics."""
    trans = load_transactions(services, years, amount_filter, use_top_merchants, use_panel)
    demo = load_demographics()

    trans = trans.merge(demo[['cardid', 'zip3']], on='cardid', how='left')
    trans['zip3'] = trans['zip3'].astype(str)
    log(f"After zip3 merge: {len(trans):,} (matched: {trans['zip3'].notna().sum():,})")

    return trans
