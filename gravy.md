# Gravy: Extensions If Core Elasticity Works

## Three Frames for the Bigger Paper

### Frame 1: Who Gets to Use AI?

The tax prices out elastic users. If elasticity correlates with income, the tax rations AI access to the wealthy. Digital divide story for the AI era.

**Test:** β₂ > 0 on HighIncome interaction → low-income users more elastic → priced out

**Policy angle:** If AI is skill-augmenting, taxing it is regressive in a deeper sense than "poor people pay higher share of income." You're locking them out of productivity gains.

---

### Frame 2: Returns to AI Are Private

Self-employed capture productivity gains directly (they keep the surplus). W-2 employees don't—employer captures it. If self-employed are less elastic, that's revealed-preference evidence that private returns to AI are high for those who can internalize them.

**Test:** β₂ < 0 on SelfEmp interaction → self-employed less elastic → reveals high private returns

**Implication:** The gap in elasticity between self-employed and employees measures how much of the return to AI flows to workers vs. firms.

---

### Frame 3: AI as Human Capital Investment

Frame AI subscriptions like education/training expenditure. Elasticity reveals who treats AI as investment (inelastic, ROI justifies cost) vs. consumption (elastic, discretionary).

**Test:** Characterize the inelastic users—are they also spending on business tools, education, professional development?

**Policy angle:** Should AI tools be tax-advantaged like education?

---

## Welfare Calculation Framework

### Simple Calibration

Let θ = productivity gain from AI (from external estimates)
Let τ = tax-induced price increase

Users with WTP < new price churn. Elasticity estimates identify share and composition of churners. **(Caveat: We don't observe WTP directly. Churn reveals WTP < post-tax price; staying reveals WTP > post-tax price. Stayers' WTP could be $25 or $2500—uninformative upper bound.)**

**Welfare loss:**

$$DWL = \sum_{i \in \text{churners}} \theta_i \cdot w_i$$

Where wᵢ is wage/output. If low-income users churn more and θ is similar across groups, the tax destroys more surplus for those who can least afford it.

### Model Structure

1. Agents choose whether to subscribe at price p(1 + τ)
2. AI provides productivity boost θ, which maps to income gain θ · wᵢ
3. Subscribe if θ · wᵢ > p(1 + τ)—return exceeds cost
4. Tax increase raises threshold, prices out marginal users
5. Elasticity by income tells you shape of WTP distribution **(requires functional form assumptions—e.g., log-normal WTP. Two price points can fit a two-parameter distribution, but extrapolation is sensitive to assumed form)**
6. Calibrate θ from external estimates, back out welfare

This is a Harberger triangle calculation with distributional weights.

---

## External Productivity Estimates

| Paper | Setting | Effect |
|-------|---------|--------|
| Brynjolfsson, Li, Raymond (2023) | Customer service agents | +14% productivity |
| Noy & Zhang (2023) | Writing tasks | +37% quality, −40% time |
| Peng et al. (2023) | GitHub Copilot / coding | +55% faster completion |
| Dell'Acqua et al. (2023) | BCG consultants + GPT-4 | +40% on structured tasks |

**Important caveat:** These are mostly workplace/employer-provided settings, and specific tasks where gains are largest. Your contribution is the *consumer* side—people paying out of pocket.

### WTP Estimates (The Right Comparison—But Caveat-Heavy)

**Major caveat:** Elasticity ≠ WTP. You can back out WTP from elasticity, but it requires functional form assumptions (e.g., assume WTP is log-normal, fit parameters from churn rates at different prices). Results are sensitive to assumed distribution. What follows compares *stated* WTP from surveys to what *revealed* WTP might look like—but revealed WTP requires assumptions to pin down.

**Noy & Zhang (2023):** RCT with 444 experienced white-collar professionals (writing tasks).
- After using ChatGPT, asked WTP for continued access
- Average WTP = 0.5% of monthly salary (~$500/year for $100k earner)
- Workers recognized immediate productivity gains (37% faster) and attached real monetary value

**Brynjolfsson, Collis, and Eggers (2023/2024):** GDP-B methodology applied to LLMs.
- Incentive-compatible choice experiments (choose between keeping service or cash)
- Estimated aggregate US consumer surplus from generative AI: ~$97B in 2024
- **Caveat:** Uses WTA (willingness to accept loss), which typically exceeds WTP

**Why this matters for your paper:**

The delta is WTP vs. actual price, not elasticity vs. productivity.

- Noy & Zhang WTP: ~$500/year
- Actual subscription cost: ~$240/year ($20/month)

If WTP > price, people *should* stay. High elasticity (churn when price rises 2-4pp) would suggest:
1. Stated WTP overstates true WTP, OR
2. Marginal subscribers have much lower WTP than average, OR
3. The tax tips marginal users below their threshold

**What you actually get:** Elasticity, not WTP. Bounds only: churners have WTP < post-tax price; stayers have WTP > post-tax price. Stayers' bound is uninformative (could be $25 or $25,000). To say anything about the WTP *distribution*, you need to assume a functional form (log-normal, Pareto, etc.) and fit parameters from observed churn rates. This is doable but adds assumptions. Don't claim "revealed WTP" without acknowledging this.

---

## Humlum Facts

### "Large Language Models, Small Labor Market Effects" (NBER WP 33777, 2025)

- Denmark: 25,000 workers, 7,000 workplaces
- AI chatbots → ~3% time savings on average
- No significant impact on earnings or recorded hours
- Only 3-7% of productivity gains flow to workers

### "The Unequal Adoption of ChatGPT" (PNAS, January 2025)

Denmark survey (18,000 workers, 11 exposed occupations):

- ChatGPT widespread among younger, less-experienced workers
- Women 16pp less likely to use for work
- **Selection:** Users earned slightly more *before* ChatGPT arrived, even given lower tenure
- Workers see productivity potential but hindered by employer restrictions and perceived need for training

**Why this matters:** The selection finding complicates "AI helps low-skill workers catch up" narrative. Higher earners adopted first. Your elasticity estimates are for *paying* consumers—a selected sample of people who already valued it enough to pay $20/month.

**Implications:**

1. If Humlum is right (~3% gains in practice), high elasticity is *rational*—people correctly perceive $20/month isn't worth it

2. Earlier estimates (14-40%) were from specific high-gain tasks, not representative occupations

3. Your elasticity estimates could help adjudicate: if self-employed are inelastic and employees elastic, gains are real but unevenly captured. If everyone is elastic, gains may be small.

**Possible framing:** "Revealed preference estimates of AI's value to different user types, using price shocks to separate true value from hype."

---

## Proxy Construction Details

### Income Proxy

Total monthly card spend, averaged over pre-period (6+ months before Jan 2025).

Split into terciles or quartiles. Interact with treatment.

### Self-Employment Proxy

You don't observe Schedule C. Proxy via spending patterns:

**High-signal merchants/categories:**
- Advertising (Meta Ads, Google Ads)
- Domain registrars (GoDaddy, Namecheap)
- Web hosting (AWS, Vercel, DigitalOcean)
- Business software (QuickBooks, FreshBooks, Gusto)
- Coworking spaces (WeWork, etc.)
- Freelance platforms (payments *from* Upwork/Fiverr)
- Office supplies, shipping (Staples, UPS Store)

**Construction:**
1. Flag cardholders with 2+ transactions in these categories over 6-month pre-period
2. Or: create continuous "business spending intensity" score

**Validation:** Check if proxy correlates with income volatility (self-employed have more variable month-to-month income)

---

## Heterogeneity Specifications

**By income:**

$$\text{Churn}_{it} = \beta_1 (\text{Chicago}_i \times \text{Post}_t) + \beta_2 (\text{Chicago}_i \times \text{Post}_t \times \text{HighIncome}_i) + \gamma_i + \delta_t + \epsilon_{it}$$

**By self-employment:**

$$\text{Churn}_{it} = \beta_1 (\text{Chicago}_i \times \text{Post}_t) + \beta_2 (\text{Chicago}_i \times \text{Post}_t \times \text{SelfEmp}_i) + \gamma_i + \delta_t + \epsilon_{it}$$

β₂ > 0 → that group is *more* elastic (churns more)
β₂ < 0 → that group is *less* elastic (stays despite tax)

---

## Stretch: Decomposing Returns

If self-employed are less elastic and employees are more elastic:

- Self-employed: capture θ directly → higher WTP → less elastic
- Employees: capture αθ where α < 1 (employer takes rest) → lower WTP → more elastic

**(Caveat: "Higher/lower WTP" is inferred from elasticity differences, not directly observed. Requires assumption that elasticity differences reflect WTP differences rather than, say, attention or hassle costs.)**

The gap in elasticities identifies α—the share of AI productivity gains flowing to workers vs. firms. **(Requires model structure to map elasticity gap → α. Not a free lunch.)**

---

## What This Buys You (If It Works)

1. **Quantified welfare loss** — Not just "people churn," but "X dollars of productivity destroyed"

2. **Distributional statement** — If low-income users are priced out and θ ≈ 15-40%, you can say: "The tax costs low-income users Y% of potential productivity gains"

3. **Policy counterfactual** — What if AI subscriptions were tax-exempt (like education) or subsidized?

---

## Speculative: "Too Elastic"

Intuition: People are surprisingly elastic to AI subscription prices. They complain about paying $100/year when they really should be willing to pay $100/year (or more).

If Noy & Zhang's *stated* WTP (~$500/year) reflects true productivity gains, and actual cost is ~$240/year, a 2-4pp tax increase ($5-10/year) shouldn't cause much churn. But if it does, something is off. **(Caveat: Comparing stated WTP to revealed behavior. We don't directly observe revealed WTP—we observe churn, which gives bounds. Any claim about "true WTP" requires functional form assumptions.)**

1. **Stated WTP ≠ true WTP.** People overstate in surveys what they'd actually pay.

2. **Present bias / salience.** The $20/month charge is salient. The productivity gains are diffuse. People weight the visible cost more than the invisible benefit.

3. **Uncertainty about own productivity gains.** Workers in Noy & Zhang's RCT *saw* their productivity improve. Typical consumers don't run their own A/B tests. They're uncertain whether AI actually helps them.

4. **Status quo bias.** Churning is the default when a subscription renews at a higher price. Staying requires active re-commitment.

5. **Mental accounting.** AI subscriptions coded as "discretionary tech spending" rather than "productivity investment." Different budgets, different elasticity.

### Anecdotal Support (Zvi Mowshowitz)

Zvi argues users drastically underrate top-tier LLM value due to "sticker shock"—comparing to Netflix rather than to human labor.

**Key quotes:**
- "Stop whining about the relative price. The absolute price is dirt cheap. ... If it costs $200/month, that is still approximately zero dollars. Consider what it would cost to get this amount of intelligence from a human. Pay up."
- "If you are constantly using AI... it is worth paying for the best version. Your sleep or productivity is worth a few thousand a year."

**The underrating mechanism:**
- Relative price view: "$20 is expensive for an app"
- Absolute value view: "$20 is infinitely cheap for an on-demand graduate-level researcher"

**Caveat (from Zvi):** Value isn't infinite for wrong use cases. "Slop" (low-value content generation) vs. cognitive labor. If you use LLMs for spam, you overrate value; for cognitive labor, you underrate it.

**Note:** This is about levels (WTP), not price sensitivity (elasticity). But supports the general framing.

### What "Too Elastic" Would Mean

If elasticity is high and heterogeneity shows:
- Self-employed (who capture gains) are *still* elastic
- High-income (who can afford it) are *still* elastic

Then it's not just "wrong people are priced out"—it's "people systematically undervalue AI relative to its productivity benefits."

That's a behavioral finding, not just a distributional one.

### Policy Implication (If True)

If people undervalue AI due to behavioral frictions, subsidizing AI access isn't just redistributive—it corrects a market failure (underinvestment in productivity-enhancing tools).

Analogy: Education subsidies aren't just about equity. They're also justified by human capital externalities and individual underinvestment due to credit constraints / present bias.

### Caution

This is speculative. "People are too elastic" requires a benchmark for what elasticity *should* be. That benchmark comes from external productivity estimates, which have their own problems (task-specific, lab settings, Humlum's ~3% real-world estimate).

Don't oversell this unless the elasticity is really striking.

---

## Sources

- [Humlum research page](https://www.andershumlum.com/research)
- [Large Language Models, Small Labor Market Effects (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5219933)
- [NBER WP 33777](https://www.nber.org/system/files/working_papers/w33777/w33777.pdf)
