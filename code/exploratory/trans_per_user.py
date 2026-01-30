#!/usr/bin/env python3
"""Calculate transactions per user for zip3 606."""

import sys
sys.path.insert(0, '/Users/jeffreyohl/Documents/GitHub/brainstorming')
from load_data import load_with_zip3

trans = load_with_zip3()

# Filter to zip3 606
chicago = trans[trans['zip3'] == '606']

n_trans = len(chicago)
n_users = chicago['cardid'].nunique()
trans_per_user = n_trans / n_users if n_users > 0 else 0

print(f"\nZip3 606 (Chicago) with $15-25 filter, panel:")
print(f"  Transactions: {n_trans:,}")
print(f"  Unique users: {n_users:,}")
print(f"  Transactions per user: {trans_per_user:.2f}")
