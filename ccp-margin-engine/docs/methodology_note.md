# Methodology Note
## CCP Margin Adequacy, Backtesting, and Risk Governance Engine

**Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal – Risk Methodology

---

## 1. Objective

This document describes the margin methodology implemented by the CCP Margin Engine. The engine evaluates whether posted collateral is sufficient to cover liquidation losses on cleared derivatives portfolios under normal and stressed conditions.

**The organising question:**

> For each clearing member and each day, is posted margin sufficient to cover liquidation-adjusted loss at the chosen confidence level and under defined stress scenarios? If not, what gets escalated, how is it reported, and what methodology limitations are documented?

**Important disclaimer:** This is a stylised educational model. It is NOT a production CCP margin system and should not be used for actual margin calculations.

---

## 2. Scope

### Product Universe
- **Equity index futures:** S&P 500 (ES), Nasdaq-100 (NQ), Russell 2000 (RTY)
- **Rates futures:** 10-Year Treasury (TY), 5-Year Treasury (FV), Ultra Bond (US)
- **Volatility:** VIX futures (VX)
- **Commodity:** Crude Oil (CL)
- **Listed options:** SPX calls/puts, NDX calls/puts

### Member Universe
10 simulated clearing members with diverse profiles:
- Directional macro (3 members)
- Relative value (2 members)
- Concentrated volatility (1 member)
- Diversified (2 members)
- Weak liquidity (1 member)
- Additional directional macro (1 member)

---

## 3. Risk Factors

| Factor | Asset Class | Liquidity Bucket |
|--------|-------------|------------------|
| SPX | Equity Index | Liquid |
| NDX | Equity Index | Liquid |
| RTY | Equity Index | Semi-Liquid |
| TY | Rates | Liquid |
| FV | Rates | Liquid |
| US | Rates | Semi-Liquid |
| VIX | Volatility | Semi-Liquid |
| CL | Commodity | Liquid |

Market data is generated synthetically using fat-tailed distributions (Student-t, df=5) to capture realistic tail behaviour.

---

## 4. Margin Formula

The required initial margin for each clearing member is computed as:

$$
\text{Initial Margin} = \max(\text{HSVaR}_{99\%}, \text{Stressed VaR}_{99\%}) + \text{Liquidity Add-On} + \text{Concentration Add-On}
$$

### 4.1 Liquidation-Adjusted Loss

The **liquidation-adjusted loss** is the central output of the margin methodology. It represents the estimated cost of closing out a defaulting member's portfolio under adverse conditions:

$$
\text{Liquidation-Adjusted Loss} = \max(\text{HSVaR}_{99\%}, \text{Stressed VaR}_{99\%}) + \text{Liquidity Add-On} + \text{Concentration Add-On}
$$

This value is stored as `liquidation_adjusted_loss` in the margin results and directly equals `required_margin`. The separation into named components is maintained for decomposition, audit, and governance purposes.

| Component | Field Name | Purpose |
|-----------|-----------|---------|
| Historical VaR | `hsvar_99` | 99% VaR from 500-day rolling P&L distribution |
| Stressed VaR | `stressed_var_99` | 99% VaR from highest-vol 60-day sub-window |
| Liquidity add-on | `liquidity_addon` | Spread + impact cost, scaled by liquidation horizon |
| Concentration add-on | `concentration_addon` | Penalty for crowded positions relative to ADV |
| **Liquidation-adjusted loss** | `liquidation_adjusted_loss` | **Total: baseline + liquidity + concentration** |
| Required margin | `required_margin` | = liquidation-adjusted loss |

### 4.2 Baseline Margin: Historical Simulation VaR

- **Method:** Full-revaluation historical simulation
- **Confidence level:** 99%
- **Historical window:** 500 trading days (≈ 2 years)
- **Computation:** The 1st percentile of the member-level daily P&L distribution

For each day *t*, the VaR is the negative of the 1% quantile of the trailing P&L distribution:

$$
\text{HSVaR}_{99\%} = -Q_{0.01}(\{PnL_{t-1}, PnL_{t-2}, \ldots, PnL_{t-500}\})
$$

### 4.3 Stressed VaR

- **Method:** Same as HSVaR, but restricted to a stressed sub-window
- **Stressed window:** 60 consecutive trading days
- **Selection:** The contiguous 60-day period within the 500-day history exhibiting the highest realised volatility of the primary equity index factor (SPX)

The stressed VaR ensures margin does not drop during calm periods by anchoring to a high-volatility regime. By selecting the sub-window with peak realised vol rather than a fixed historical stress period, the methodology adapts dynamically to the data without manual intervention.

**Why the stressed window is selected this way:**
1. It avoids the subjectivity of choosing a specific historical crisis period
2. It ensures the stressed VaR never falls below a meaningful floor
3. It creates an automatic floor for margin during benign markets

### 4.4 Pricing

- **Futures:** Linear P&L (ΔPrice × Multiplier × Quantity)
- **Listed options:** Black-Scholes model with:
  - Annualised implied vol proxy from 20-day realised vol
  - Risk-free rate: 4.5%
  - Time to expiry: computed from contract specification
- **Rates futures:** Linear approximation (acceptable for margin sizing; duration-based refinement is a v2 enhancement)

---

## 5. Supported Product Types

| Product | Type | Underlying | Pricing Model | Liquidity Bucket |
|---------|------|-----------|---------------|-----------------|
| ES1 | Equity index future | SPX | Linear | Liquid |
| NQ1 | Equity index future | NDX | Linear | Liquid |
| RTY1 | Equity index future | RTY | Linear | Semi-Liquid |
| TY1 | Rates future | TY | Linear | Liquid |
| FV1 | Rates future | FV | Linear | Liquid |
| US1 | Rates future | US | Linear | Semi-Liquid |
| VX1 | Volatility future | VIX | Linear | Semi-Liquid |
| CL1 | Commodity future | CL | Linear | Liquid |
| SPX_C4900 | Listed equity-index option (call) | SPX | Black-Scholes | Liquid |
| SPX_P4700 | Listed equity-index option (put) | SPX | Black-Scholes | Liquid |
| NDX_C17000 | Listed equity-index option (call) | NDX | Black-Scholes | Liquid |
| NDX_P16500 | Listed equity-index option (put) | NDX | Black-Scholes | Liquid |

A machine-readable product universe is generated at `data/synthetic/product_universe.csv` with columns: `instrument_id`, `asset_class`, `product_type`, `underlying`, `liquidity_bucket`, `exchange_style`, `cleared_flag`.

---

## 6. Liquidity Adjustment Logic

Standard VaR does not capture the cost of liquidating positions in a default scenario. The liquidity add-on accounts for:

### 5.1 Bid-Ask Spread Cost

$$
\text{Spread Cost} = |Q| \times M \times S \times \frac{\text{BA}_{bps}}{20000}
$$

Where Q = quantity, M = multiplier, S = spot price, BA = bid-ask spread in basis points.

### 5.2 Market Impact

$$
\text{Impact} = \alpha \times \sqrt{\frac{|Q|}{\text{ADV}}} \times S \times |Q| \times M
$$

Where α = 0.10 (impact coefficient), ADV = average daily volume.

### 5.3 Liquidation Horizon Scaling

The raw liquidity cost is scaled by the square root of the liquidation horizon:

| Liquidity Bucket | Liquidation Horizon | Scale Factor |
|-----------------|--------------------:|:------------:|
| Liquid | 2 days | √2 ≈ 1.41 |
| Semi-Liquid | 3 days | √3 ≈ 1.73 |
| Illiquid | 5 days | √5 ≈ 2.24 |

### 5.4 Member Liquidity Multiplier

Each member type has a liquidity multiplier reflecting their expected ease of liquidation:

| Member Type | Multiplier |
|-------------|:----------:|
| Diversified | 0.7 |
| Relative Value | 0.8 |
| Directional Macro | 1.0 |
| Concentrated Vol | 1.3 |
| Weak Liquidity | 1.5 |

**Rationale:** Market liquidity research demonstrates that ordinary VaR misses liquidation risk. Depth, spread, and resilience all matter for sizing collateral conservatively enough to survive liquidation under stress.

---

## 7. Concentration Logic

If a member's position exceeds a threshold fraction of average daily volume, a concentration add-on is applied:

| ADV Fraction | Add-On Rate |
|:------------:|:-----------:|
| < 10% | 0% |
| 10% – 20% | +10% of baseline margin |
| > 20% | +25% of baseline margin |

The add-on is the product of the highest concentration rate across all instruments and the baseline margin.

---

## 8. Backtesting Method

### Exception Definition
An exception occurs when:

$$
\text{Actual Loss}_t > \text{Prior-Day Margin}_{t-1}
$$

### Monitoring Metrics
- **Rolling exception count:** 250-day rolling window
- **Exception classification:**
  - Green: < 3 exceptions
  - Amber: 3–4 exceptions
  - Red: ≥ 5 exceptions
- **Exception clustering:** Analysed by volatility regime and member
- **Margin responsiveness:** Tracked during regime transitions

---

## 9. Model-Control Checks

The term "model-control checks" encompasses all automated validations that ensure the margin calculation is based on reliable inputs and produces plausible outputs. The full set of controls includes:

1. **Stale market data flags** – risk factors unchanged for > 2 consecutive business days
2. **Missing required fields** – expected risk factors absent from daily feed
3. **Implausible volatility values** – annualised vol < 1% or > 300%
4. **Outlier return flags** – daily |return| > 15%
5. **Pricing sanity checks** – Black-Scholes producing non-negative, finite values
6. **Failed revaluation / null P&L checks** – NaN or infinite P&L values detected
7. **Unexplained exposure jumps** – member-instrument market value change > 3σ of historical

See the separate Control Framework document (`docs/control_framework.md`) for control IDs, thresholds, owners, and escalation paths.

---

## 10. Escalation Policy

| Trigger | Action | Owner |
|---------|--------|-------|
| 1 red breach day | Analyst review | Risk Analyst |
| 2+ consecutive red days | Senior risk review + margin call recommendation | Senior Risk Officer |
| ≥ 4 backtesting exceptions (rolling) | Methodology review | Model Validation |
| Concentration add-on > 25% of total | Committee watchlist | Risk Committee |
| Critical stale market data | Run marked provisional | Market Data Team |
| Margin call trigger | Issue call to member | Margin Operations |

---

## 11. Assumptions and Limitations

### Assumptions
- Log-normal return dynamics for price simulation
- Black-Scholes for option pricing (no smile/skew)
- Constant risk-free rate
- Static member profiles (no credit migration)
- No intraday margin calls
- Collateral haircuts are fixed per member-day

### Limitations
1. **Stylised margin formula** – not a real CCP methodology; no netting sets, no cross-margin offsets
2. **Simplified liquidation assumptions** – no auction mechanics, no fire-sale dynamics
3. **Limited product universe** – no swaps, no OTC derivatives, no cross-currency
4. **Simplified collateral eligibility** – binary cash/bond split; no wrong-way risk on collateral
5. **No auction/default management simulation** – no loss allocation waterfall
6. **No legal segregation** – no account structure modelling (house vs. client)
7. **Scenario set limitations** – may omit cross-asset contagion channels and feedback loops
8. **No credit risk adjustment** – member default probability not modelled
9. **Static vol surface** – no term structure or skew dynamics for options

---

## 12. Intended Use

### Intended For

This platform is intended for educational analysis of member-level collateral adequacy under stylised CCP-style margin methodology. Suitable uses include:

- Portfolio project demonstrating margin, backtesting, and governance concepts
- Interview discussion aid for quantitative risk analyst roles
- Learning tool for CCP margin methodology and risk control frameworks
- Reference implementation for stylised historical simulation VaR with add-ons

### Not Intended For

- Production margining or live collateral management decisions
- Legal or regulatory filing
- Real clearing operations or default management
- Replacement for validated, production-grade margin models
- Basis for actual margin calls or member notifications

---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | March 2026 | Risk Methodology | Initial version |
| 1.1 | March 2026 | Risk Methodology | Added liquidation-adjusted loss definition, product types, stressed window logic, intended use statement |
