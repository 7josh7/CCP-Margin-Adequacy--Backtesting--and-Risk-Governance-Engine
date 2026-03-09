# CCP Margin Adequacy, Backtesting, and Risk Governance Engine

A Python-based risk platform that assesses whether posted collateral is sufficient to cover liquidation-adjusted losses on multi-asset cleared futures portfolios and listed equity-index options under historical and stressed scenarios, with model-control checks, escalation rules, and committee-style reporting for daily risk review.

> **Disclaimer:** This is a stylised educational model. It is NOT a production CCP margin system.

---

## What This Project Demonstrates

1. **Margin Adequacy** — Sizing collateral conservatively enough to survive liquidation under stress, using Historical Simulation VaR with liquidity and concentration add-ons
2. **Model Monitoring & Backtesting** — Tracking exception counts, detecting clustering, and triggering methodology reviews when thresholds are breached
3. **Liquidity & Concentration Effects** — Explicit incorporation of bid-ask spread, market impact, liquidation horizon scaling, and position concentration penalties
4. **Governance, Controls & Escalation** — Data quality and model-control checks, breach classification (traffic-light), escalation rules with clear ownership, and committee-quality reporting for daily risk review

## Core Question

> For each clearing member and each day, is posted margin sufficient to cover liquidation-adjusted loss at the chosen confidence level and under defined stress scenarios? If not, what gets escalated, how is it reported, and what methodology limitations are documented?

---

## Product Coverage

The platform supports stylised cleared portfolios across:

| Asset Class | Products | Instruments |
|-------------|----------|-------------|
| **Equity Index** | S&P 500 (ES), Nasdaq-100 (NQ), Russell 2000 (RTY) futures | ES1, NQ1, RTY1 |
| **Rates** | 10-Year Treasury (TY), 5-Year Treasury (FV), Ultra Bond (US) futures | TY1, FV1, US1 |
| **Volatility** | VIX futures | VX1 |
| **Commodity** | Crude Oil (CL) futures | CL1 |
| **Listed Options** | SPX calls/puts, NDX calls/puts (equity-index options) | SPX_C4900, SPX_P4700, NDX_C17000, NDX_P16500 |

All products are assigned liquidity buckets and revalued under historical and stressed scenarios for member-level margin adequacy assessment. A machine-readable product universe file is generated at `data/synthetic/product_universe.csv`.

---

## Margin Methodology Flow

```
Market Data (8 risk factors, fat-tailed synthetic returns)
  │
  ▼
Pricing Engine (futures: linear P&L, options: Black-Scholes full reval)
  │
  ▼
Scenario Engine
  ├── Historical Scenarios  (500-day rolling window)
  └── Stressed Scenarios    (60-day highest-vol sub-window)
  │
  ▼
Baseline Margin = max(HSVaR₉₉, Stressed VaR₉₉)
  │
  ├── + Liquidity Add-On   (spread cost + market impact × √horizon)
  ├── + Concentration Add-On (position/ADV bands: 0% / 10% / 25%)
  │
  ▼
Liquidation-Adjusted Loss = Baseline + Liquidity Add-On + Concentration Add-On
  │
  ▼
Required Margin (= Liquidation-Adjusted Loss)
  │
  ▼
Compare with Posted Collateral
  │
  ├── Coverage Ratio     = posted / required
  ├── Traffic Light       ≥1.10 green │ ≥1.00 amber │ <1.00 red
  └── Margin Call         shortfall > threshold & ≥ MTA
```

### Liquidation-Adjusted Loss Definition

```
liquidation_adjusted_loss = max(hsvar_99, stressed_var_99) + liquidity_addon + concentration_addon
```

This field is computed explicitly for every member-day and appears in:
- `data/processed/margin_results.csv`
- `reports/daily/member_margin_adequacy.csv`
- The Streamlit dashboard Margin Decomposition tab

### Why Liquidation Horizon Varies by Liquidity Bucket

| Bucket | Horizon | Rationale |
|--------|:-------:|-----------|
| Liquid | 2 days | Deep order books; quick close-out feasible |
| Semi-Liquid | 3 days | Moderate depth; may require phased unwinding |
| Illiquid | 5 days | Thin markets; forced selling causes adverse price impact |

The raw liquidity cost is scaled by √(horizon), reflecting the standard square-root-of-time risk scaling.

### Stressed Window Selection

The 60-day stressed sub-window is selected as the contiguous period within the 500-day history exhibiting the highest realised volatility of the primary equity index factor (SPX). This ensures that the Stressed VaR anchors margin to a high-volatility regime and prevents procyclical margin drops during calm periods.

---

## Architecture

The project is built as **7 modules**:

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **A. Data & Portfolio** | Synthetic market data, instruments, member profiles, positions, collateral, product universe | `src/portfolio.py`, `src/data_loader.py` |
| **B. Pricing & P&L** | Full revaluation (futures: linear, options: Black-Scholes), scenario P&L | `src/pricing.py`, `src/scenarios.py` |
| **C. Margin Methodology** | HSVaR, Stressed VaR, liquidity add-on, concentration add-on, liquidation-adjusted loss | `src/margin.py`, `src/liquidity.py`, `src/concentration.py` |
| **D. Adequacy Testing** | Coverage ratios, traffic-light framework, margin calls with threshold/MTA | `src/controls.py` |
| **E. Backtesting & Monitoring** | Exception tracking, rolling counts, model-control & data quality checks | `src/backtesting.py` |
| **F. Governance & Escalation** | Rule-based escalation engine, consecutive-red detection, breach register | `src/escalation.py` |
| **G. Reporting** | Daily risk review, breach register, member adequacy CSV, weekly exception report, monthly committee pack | `src/reporting.py` |

---

## Project Structure

```
ccp-margin-engine/
├── app/
│   └── streamlit_app.py          # Interactive Streamlit dashboard (6 tabs)
├── data/
│   ├── raw/
│   ├── processed/                # Computed results (auto-generated)
│   │   ├── margin_results.csv    #   includes liquidation_adjusted_loss
│   │   ├── adequacy.csv          #   includes threshold_breached, mta_triggered
│   │   └── ...
│   └── synthetic/
│       ├── product_universe.csv  # Auditable instrument/asset-class mapping
│       └── ...
├── docs/
│   ├── methodology_note.md       # Full methodology documentation
│   ├── control_framework.md      # Model-control & data quality controls
│   ├── governance_note.md        # Roles, thresholds, escalation, parameter governance
│   └── breach_taxonomy.md        # Breach definitions, severity, ownership
├── notebooks/
│   ├── 01_data_generation.py     # Generate and explore synthetic data
│   ├── 02_pricing_validation.py  # BS sanity checks, P&L computation
│   ├── 03_margin_methodology.py  # VaR, margin decomposition, trends
│   ├── 04_backtesting.py         # Exception analysis, DQ checks
│   └── 05_reporting_examples.py  # Generate all report types
├── reports/
│   ├── daily/
│   │   ├── daily_risk_review_*.md        # Morning risk meeting memo
│   │   ├── member_margin_adequacy_*.csv  # Member-level adequacy table
│   │   └── breach_register_*.csv         # Open breach register
│   ├── weekly/
│   └── committee_pack/
├── src/
│   ├── __init__.py
│   ├── config.py                 # All tuneable parameters
│   ├── data_loader.py            # CSV read/write abstraction
│   ├── portfolio.py              # Synthetic data generation + product universe
│   ├── pricing.py                # Futures & options pricing, P&L
│   ├── scenarios.py              # Historical & stress scenario engine
│   ├── margin.py                 # Core margin methodology
│   ├── liquidity.py              # Liquidity add-on calculation
│   ├── concentration.py          # Concentration add-on calculation
│   ├── controls.py               # Adequacy ratios, traffic light, margin calls
│   ├── backtesting.py            # Exception tracking, model-control checks
│   ├── escalation.py             # Governance & escalation rules
│   └── reporting.py              # Report generation (daily review/breach/weekly/monthly)
├── tests/
│   ├── test_margin.py            # Margin, liquidity, concentration tests
│   ├── test_pricing.py           # BS pricing, sanity checks
│   ├── test_controls.py          # Adequacy, traffic-light, margin call, DQ, model-control tests
│   └── test_reporting.py         # Report generation & breach register tests
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd ccp-margin-engine
pip install -r requirements.txt
```

### 2. Generate Data & Run Pipeline

The Streamlit app auto-generates all data and runs the full pipeline on first launch:

```bash
streamlit run app/streamlit_app.py
```

Or run the headless pipeline:

```bash
python run_pipeline.py
```

Or step-by-step via notebooks (VS Code interactive Python):
1. `notebooks/01_data_generation.py`
2. `notebooks/02_pricing_validation.py`
3. `notebooks/03_margin_methodology.py`
4. `notebooks/04_backtesting.py`
5. `notebooks/05_reporting_examples.py`

### 3. Run Tests

```bash
pytest tests/ -v
```

---

## Report Samples

The pipeline generates five types of output files:

| Report | Location | Purpose |
|--------|----------|---------|
| **Daily Risk Review** | `reports/daily/daily_risk_review_*.md` | Morning risk meeting memo: top 5 weak members, new breaches, DQ issues, backtesting alerts, recommended actions |
| **Member Margin Adequacy** | `reports/daily/member_margin_adequacy_*.csv` | Auditable per-member table with posted, required, coverage, traffic light, margin call, threshold/MTA flags |
| **Breach Register** | `reports/daily/breach_register_*.csv` | Open breaches with ID, type, severity, owner, escalation level, target resolution date |
| **Weekly Exception Report** | `reports/weekly/weekly_*.md` | Backtesting exceptions, concentration breaches, stale data, escalation summary |
| **Monthly Committee Pack** | `reports/committee_pack/committee_pack_*.md` | Margin trend, stressed members, coverage distribution, backtesting summary, recommended actions |

### Example: Member Margin Adequacy CSV Columns

```
date, member_id, posted_margin, required_margin, coverage_ratio,
traffic_light, margin_call, threshold_breached, mta_triggered,
hsvar_99, stressed_var_99, liquidity_addon, concentration_addon,
liquidation_adjusted_loss
```

### Example: Breach Register CSV Columns

```
breach_id, date, member_id, breach_type, severity, description,
owner, status, escalation_level, target_resolution_date
```

---

## Dashboard Tabs

| Tab | Content |
|-----|---------|
| **Member Overview** | Posted vs required margin, coverage ratios, traffic-light status, margin calls |
| **Margin Decomposition** | Per-member breakdown: HSVaR₉₉, Stressed VaR₉₉, liquidity add-on, concentration add-on, liquidation-adjusted loss |
| **Backtesting** | Actual loss vs margin time series, rolling exception count, exception heatmap |
| **Controls & DQ** | Model-control checks, stale data flags, outlier returns, exposure jumps, escalation log |
| **Breach Register** | Today's open breaches by type, severity heatmap, breach ownership distribution |
| **Committee Summary** | Daily risk review, weekly exception report, monthly committee pack with export |

---

## Methodology Choices

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Confidence Level | 99% | Standard for CCP initial margin |
| Historical Window | 500 days | ≈ 2 years, captures multiple regimes |
| Stressed Window | 60 days | Highest-vol period in sample |
| Liquidation Horizon | 2–5 days by bucket | Liquid futures: 2d; semi-liquid: 3d; illiquid: 5d |
| Impact Coefficient | 0.10 | Conservative market impact estimate |
| Concentration Bands | <10%: 0%, 10-20%: +10%, >20%: +25% | ADV-based crowding penalty |
| Margin Threshold | $100,000 | Operational burden vs exposure trade-off |
| Minimum Transfer | $100,000 | Consistent with repo-style margining practice |

---

## Member Profiles

| Type | Count | Characteristics |
|------|:-----:|----------------|
| Directional Macro | 3 | Large equity/rates/commodity directional bets |
| Relative Value | 2 | Multi-leg rates strategies, moderate concentration |
| Concentrated Vol | 1 | Heavy VIX/options positions, high liquidity multiplier |
| Diversified | 2 | Small positions across many products |
| Weak Liquidity | 1 | Under-collateralised, Tier 1 governance |

---

## Documentation Map

| Document | Location | Content |
|----------|----------|---------|
| **Methodology Note** | `docs/methodology_note.md` | Margin formula, liquidation-adjusted loss definition, stressed window selection, product coverage, pricing models, intended use & limitations |
| **Control Framework** | `docs/control_framework.md` | Model-control checks (7 types), escalation paths, provisional-run protocol, model performance review triggers |
| **Governance Note** | `docs/governance_note.md` | Parameter governance table, roles and responsibilities, escalation ladder, committee cadence, model change log |
| **Breach Taxonomy** | `docs/breach_taxonomy.md` | Breach type definitions, severity classification, ownership matrix, escalation mapping |

---

## Known Limitations

- Stylised margin formula, not a real CCP methodology
- Simplified liquidation assumptions (no auction / fire-sale dynamics)
- Limited product universe (equity/rates futures, listed equity-index options)
- Simplified collateral eligibility and haircut structure
- No auction/default management simulation
- No legal segregation/account structure modelling
- Scenario set may omit some cross-asset contagion channels
- No credit migration or member default probability modelling
- Static implied vol surface for options (no skew/term structure)

---

## Tests

```
tests/
├── test_margin.py      # VaR non-negativity, monotonicity, concentration increasing
├── test_pricing.py     # Black-Scholes sanity, call-put parity, delta bounds
├── test_controls.py    # Coverage ratio, traffic-light classification, margin call
│                       # threshold/MTA logic, model-control checks, scenario sanity
└── test_reporting.py   # Report content validation, breach register, daily risk review
```

Test categories:
- **Unit tests:** Margin non-negative, coverage handles zero, concentration monotonic
- **Control tests:** Stale data flagged, missing collateral flagged, implausible vol rejected
- **Scenario sanity:** Higher vol → higher margin, higher concentration → higher add-on, lower liquidity → higher loss
- **Reporting tests:** Daily summary, weekly report, committee pack, breach register, daily risk review
