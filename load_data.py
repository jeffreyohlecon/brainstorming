#!/usr/bin/env python3
"""
Data loading for ChatGPT analysis.
Imports settings from config.py.
"""

import pandas as pd
from config import (
    DATA_DIR, AMOUNT_FILTER, USE_TOP_MERCHANTS, USE_PANEL, TOP_N_MERCHANTS,
    FILTER_PLUS_RANGE, FILTER_WIDE_RANGE, FILTER_OUTSIDE, log
)

# Cache for top merchants (computed once on full sample)
_TOP_MERCHANTS_CACHE = None

# Cache for panel cardids
_PANEL_CARDIDS_CACHE = None


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
    card_info = pd.read_parquet(DATA_DIR / "chatgpt_card_info_2025_12_26.parquet")
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
    """Load ZIP3 from card_info (correct source).

    Uses chatgpt_card_info.parquet which has ZIP directly from card table.
    The old demographics CSV used cardid_address_map which had garbage data.
    """
    log("Loading card info with ZIP3...")
    card_info = pd.read_parquet(DATA_DIR / "chatgpt_card_info_2025_12_26.parquet")
    # zip is already 3-digit from card table
    card_info['zip3'] = card_info['zip'].astype(str)
    log(f"Card info: {len(card_info):,} cardids")
    return card_info[['cardid', 'zip3']]


def load_with_zip3(services=('chatgpt', 'openai'), years=(2023, 2024, 2025),
                   amount_filter=None, use_top_merchants=None, use_panel=None):
    """Load transactions merged with zip3 from demographics."""
    trans = load_transactions(services, years, amount_filter, use_top_merchants, use_panel)
    demo = load_demographics()

    trans = trans.merge(demo[['cardid', 'zip3']], on='cardid', how='left')
    trans['zip3'] = trans['zip3'].astype(str)
    log(f"After zip3 merge: {len(trans):,} (matched: {trans['zip3'].notna().sum():,})")

    return trans
