# Chicago PPLTT / ChatGPT Analysis Status

## Current State (Jan 26, 2025)

### Sample Period
- **Start**: Feb 1, 2023 (ChatGPT Plus launch)
- **End**: Dec 31, 2024 (before 11% tax)
- **Treatment**: Oct 1, 2023 (9% PPLTT)

### Scripts

| Script | Status | Output |
|--------|--------|--------|
| `chicago_did.py` | **UPDATED, needs rerun** | `chicago_did.png` |
| `chicago_synth_control.py` | **UPDATED, needs rerun** | `chicago_synth_control.png` |
| `chicago_chatgpt_analysis.py` | **UPDATED, needs rerun** | `chicago_chatgpt_*.png` |
| `run_all.py` | Created | Pipeline to run all scripts |

### Recent Changes
1. Control group: Now uses 93 size-matched ZIP3s (within 50% of Chicago's Feb-Jun 2023 transaction count) instead of neighboring IL zips
2. Sample: Feb 2023 - Dec 2024 only (single treatment period)
3. Removed 11% PPLTT analysis to simplify

### PNG Status

**STALE (need regeneration)**:
- `chicago_did.png` - Last run included 2025 data
- `chicago_synth_control.png` - Uses old IL neighbors, old date range
- `chicago_raw_counts.png` - Uses old date range
- `chicago_chatgpt_*.png` - Uses old date range

**STALE (old analysis)**:
- `chatgpt_timeseries.png` - General timeseries, not Chicago-specific
- `claude_timeseries.png` - Claude analysis, not relevant
- `chicago_chatgpt_timeseries.png` - Old combined 4-panel figure

### To Regenerate Everything

```bash
python3 run_all.py
```

Or individually:
```bash
python3 chicago_chatgpt_analysis.py
python3 chicago_did.py
python3 chicago_synth_control.py
```

Note: `run_all.py` also generates `chicago_raw_counts.png` via inline script.

---

## Latest Results (Pre-Update)

These are from the last run with 93 size-matched controls (but including 2025 data):

### DiD
- **Treated × Post**: -0.19 (se=0.02, p<0.0001)
- Elasticity: ~-2.2 (mixing 9% and 11% periods)
- Pre-trends: Formally rejects (F-test p<0.0001), but magnitudes small (mean |coef| = 0.05)

### Period-Specific (before simplification)
- 9% period only: coef = -0.08, elasticity ≈ -1
- 11% period only: coef = -0.33, elasticity ≈ -3

### Pass-Through
- Expected @ 9%: $21.80
- Observed median: $21.36
- Pass-through ~97%

---

## Background

**Chicago PPLTT on AI subscriptions**:
| Date | Rate | Expected ChatGPT Price |
|------|------|------------------------|
| Pre-Oct 2023 | 0% | $20.00 |
| Oct 1, 2023 | 9% | $21.80 |
| Jan 1, 2025 | 11% | $22.20 |
| Jan 1, 2026 | 15% | $23.00 |

Source: https://www.swlaw.com/publication/artificial-intelligence-as-a-service-the-evolving-conversation-in-state-taxation/

---

## Data

Location: `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data/`

- `chatgpt_transactions_2023.parquet`
- `chatgpt_transactions_2024.parquet`
- `chatgpt_transactions_2025.parquet`
- `chatgpt_demographics_2023_2024_2025.csv`

---

## Data Quality Issue (Jan 26, 2025)

`national_price_buckets.py` reveals ~40-49% of transactions fall outside $20-25 (Plus) range:
- $20-25 (Plus): 51-60%
- $200-250 (Pro): 0.5% (post-Dec 2024)
- Other: 40-49%

**Next step**: Examine merchant-level detail to understand what's in "Other":
- Partial months / prorated charges?
- API usage fees?
- Team/Enterprise tiers?
- Misclassified transactions?
- Tax variation across jurisdictions?

Need to re-extract data with `merchid` field to filter more precisely and reduce measurement error across all analyses.

---

## LaTeX

Draft started at `chicago_ppltt.tex` but not updated with latest changes.
