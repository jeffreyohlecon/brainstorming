# AI Tax Incidence: One-Pager

## The Core Idea

Chicago uniquely taxes AI subscriptions (9% → 11% → 15%). This creates two clean price shocks. Comparing churn in Chicago vs. surrounding suburbs identifies the price elasticity of AI demand.

But elasticity alone is just measurement. The contribution is combining it with external productivity estimates to answer: **What is the welfare cost of taxing AI access, and who bears it?**

---

## The Argument in Two Paragraphs

The elasticity estimates identify *who* gets priced out when AI becomes more expensive. External productivity estimates (Brynjolfsson et al.: +14%, Noy & Zhang: +37% quality, Peng et al.: +55% speed on coding) identify *what* they lose. Combining these gives a quantified welfare loss: the productivity gains destroyed when marginal users churn. If low-income users are more elastic, the tax is regressive not just in the standard sense (higher share of income) but in a deeper sense—it locks them out of productivity gains they could have captured.

The heterogeneity by self-employment status reveals something additional. Self-employed users capture AI productivity gains directly; employees don't (their employer does). If self-employed users are less elastic despite facing the same price increase, that's revealed-preference evidence that the private returns to AI are high for those who can internalize them. The gap in elasticities between self-employed and employees measures how much of the return to AI flows to workers versus firms.

---

## Identification

| Date | Rate Change | Magnitude |
|------|-------------|-----------|
| Jan 2025 | 9% → 11% | +2pp |
| Jan 2026 | 11% → 15% | +4pp |

**Treatment:** Chicago ZIP3s (606, 608)
**Control:** Suburban Cook + collar counties (600-605, 607)
**Unit:** Cardholder × month

---

## Specifications

**Average effect:**
$$\text{Churn}_{it} = \beta (\text{Chicago}_i \times \text{Post}_t) + \gamma_i + \delta_t + \epsilon_{it}$$

**Heterogeneity:**
- Interact with income proxy (total card spend)
- Interact with self-employment proxy (business-related spending)

$\beta_{\text{interaction}} > 0$ → that group is *more* elastic (churns more)
$\beta_{\text{interaction}} < 0$ → that group is *less* elastic (stays despite tax)

---

## Welfare Calculation

Let $\theta$ = productivity gain from AI (~15-40% from literature)
Let $\tau$ = tax-induced price increase

Users with WTP < new price churn. Elasticity estimates identify share and composition.

$$\text{DWL} = \sum_{i \in \text{churners}} \theta_i \cdot w_i$$

If low-income users churn more and $\theta$ is similar across groups, the tax destroys more surplus for those who can least afford it.

---

## What This Paper Is

Not "here's the elasticity of AI demand."

It's: **the welfare cost of taxing AI access, with distributional consequences.**

That's a policy paper.

---

## Diagnostics Before Running

| Check | Kill Threshold |
|-------|----------------|
| Chicago AI subscribers pre-2025 | < 500 kills project |
| OpenAI pass-through (price jump Jan 2025/2026) | No jump = no treatment |
| Pre-trends (6+ months) | Diverging trends = contaminated |
| Self-emp proxy validity | Noise = can't run Frame 2 |
