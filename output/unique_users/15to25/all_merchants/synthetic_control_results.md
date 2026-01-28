# Synthetic Control Results: Chicago PPLTT on ChatGPT Subscriptions

Generated: 2025-01-28

## Method

Synthetic control matching on **pre-treatment outcomes only** (Mar–Sep 2023, 7 months).

**Convex hull constraint enforced:**
- Weights sum to 1 (equality constraint)
- Each weight bounded [0, 1]
- Optimizer: SLSQP

**Outcome:** log(unique cardids with $15–$25 transaction) per ZIP3-month

## Sample

- **Treated unit:** ZIP3 606 (Chicago)
- **Treatment date:** October 2023 (9% PPLTT)
- **Donor pool:** 19 ZIP3s with unique users within 10% of Chicago in Mar–Jun 2023
- **Chicago size:** 181 unique users in matching window
- **Panel:** Constant individual panel (cardlinkids active in all 70-day windows)
- **Transaction filter:** $15–$25 (ChatGPT Plus subscription range)
- **Sample period:** Mar 2023 – Nov 2024

## Results

| Metric | Value |
|--------|-------|
| Pre-period RMSE | 0.018 |
| Pre-tax gap (Chicago − Synth) | +0.001 |
| Post-tax gap (Chicago − Synth) | −0.112 |
| **Treatment effect** | **−11.2 log points** |

The pre-treatment fit is near-perfect (gap ≈ 0). Post-tax, Chicago falls below the synthetic control by ~11%, and this gap persists through 2024.

## Donor Weights

8 ZIP3s receive weight ≥1%:

| ZIP3 | Weight | Location (?) |
|------|--------|--------------|
| 281 | 22.5% | Houston, TX (?) |
| 953 | 20.2% | Stockton, CA (?) |
| 280 | 15.8% | Miami, FL (?) |
| 890 | 15.8% | Gulfport, MS (?) |
| 957 | 13.4% | Fresno, CA (?) |
| 232 | 5.5% | Cincinnati, OH (?) |
| 208 | 3.5% | Washington, DC (?) |
| 775 | 3.2% | Lubbock, TX (?) |

**Note:** ZIP3-to-city mappings need verification against USPS data.

## Interpretation

The 9% Chicago PPLTT reduced the number of unique ChatGPT Plus subscribers by approximately 11% relative to the synthetic counterfactual. This is the extensive margin effect—fewer distinct cardholders making subscription-priced transactions.

## Technical Notes

- **Donor pool restriction:** Using all 751 ZIP3s caused optimizer convergence issues (weights concentrated on 3 ZIP3s, poor fit). Restricting to size-matched donors (within 10% of Chicago) yields stable results with 19 potential donors.
- **All weights used:** The synthetic is computed using all donor weights (summing to 1), not just the >1% subset shown in the table.

## Files

- `chicago_synth_control.png` — Time series plot
- `chicago_did.py` — Source code (toggle `USE_SYNTH_CONTROL = True`)
