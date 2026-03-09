# CCP Margin Adequacy, Backtesting, and Risk Governance Engine

A Python-based risk platform that evaluates whether posted collateral is sufficient to cover liquidation losses on cleared derivatives portfolios under normal and stressed conditions, with controls, exception monitoring, escalation rules, and committee-style reporting.

> **Disclaimer:** This is a stylised educational model. It is NOT a production CCP margin system.

---

## What This Project Demonstrates

1. **Margin Adequacy** — Sizing collateral conservatively enough to survive liquidation under stress, using Historical Simulation VaR with liquidity and concentration add-ons
2. **Model Monitoring & Backtesting** — Tracking exception counts, detecting clustering, and triggering methodology reviews when thresholds are breached
3. **Liquidity & Concentration Effects** — Explicit incorporation of bid-ask spread, market impact, liquidation horizon scaling, and position concentration penalties
4. **Governance, Controls & Escalation** — Data quality controls, breach classification (traffic-light), escalation rules with clear ownership, and committee-quality reporting

## Core Question

> For each clearing member and each day, is posted margin sufficient to cover liquidation-adjusted loss at the chosen confidence level and under defined stress scenarios? If not, what gets escalated, how is it reported, and what methodology limitations are documented?

---

## Architecture

The project is built as **7 modules**:

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **A. Data & Portfolio** | Synthetic market data, instruments, member profiles, positions, collateral | `src/portfolio.py`, `src/data_loader.py` |
| **B. Pricing & P&L** | Full revaluation (futures: linear, options: Black-Scholes), scenario P&L | `src/pricing.py`, `src/scenarios.py` |
| **C. Margin Methodology** | HSVaR, Stressed VaR, liquidity add-on, concentration add-on | `src/margin.py`, `src/liquidity.py`, `src/concentration.py` |
| **D. Adequacy Testing** | Coverage ratios, traffic-light framework, margin calls with threshold/MTA | `src/controls.py` |
| **E. Backtesting & Monitoring** | Exception tracking, rolling counts, data quality checks | `src/backtesting.py` |
| **F. Governance & Escalation** | Rule-based escalation engine, consecutive-red detection | `src/escalation.py` |
| **G. Reporting** | Daily summary, weekly exception report, monthly committee pack | `src/reporting.py` |

### Margin Formula

```
Initial Margin = max(HSVaR, Stressed VaR) + Liquidity Add-On + Concentration Add-On
```

- **HSVaR:** 99% confidence, 500-day rolling historical simulation
- **Stressed VaR:** Same method restricted to the highest-vol 60-day sub-window
- **Liquidity Add-On:** Spread cost + market impact, scaled by liquidation horizon
- **Concentration Add-On:** Penalty based on position/ADV ratio (0%/10%/25% bands)

---

## Project Structure

```
ccp-margin-engine/
├── app/
│   └── streamlit_app.py          # Interactive Streamlit dashboard (5 tabs)
├── data/
│   ├── raw/
│   ├── processed/                # Computed results (auto-generated)
│   └── synthetic/                # Generated synthetic data
├── docs/
│   ├── methodology_note.md       # Full methodology documentation
│   ├── control_framework.md      # Data quality & pricing controls
│   └── governance_note.md        # Roles, thresholds, escalation paths
├── notebooks/
│   ├── 01_data_generation.py     # Generate and explore synthetic data
│   ├── 02_pricing_validation.py  # BS sanity checks, P&L computation
│   ├── 03_margin_methodology.py  # VaR, margin decomposition, trends
│   ├── 04_backtesting.py         # Exception analysis, DQ checks
│   └── 05_reporting_examples.py  # Generate all three report types
├── reports/
│   ├── daily/
│   ├── weekly/
│   └── committee_pack/
├── src/
│   ├── __init__.py
│   ├── config.py                 # All tuneable parameters
│   ├── data_loader.py            # CSV read/write abstraction
│   ├── portfolio.py              # Synthetic data generation
│   ├── pricing.py                # Futures & options pricing, P&L
│   ├── scenarios.py              # Historical & stress scenario engine
│   ├── margin.py                 # Core margin methodology
│   ├── liquidity.py              # Liquidity add-on calculation
│   ├── concentration.py          # Concentration add-on calculation
│   ├── controls.py               # Adequacy ratios, traffic light, margin calls
│   ├── backtesting.py            # Exception tracking, DQ checks
│   ├── escalation.py             # Governance & escalation rules
│   └── reporting.py              # Report generation (daily/weekly/monthly)
├── tests/
│   ├── test_margin.py            # Margin, liquidity, concentration tests
│   ├── test_pricing.py           # BS pricing, sanity checks
│   ├── test_controls.py          # Adequacy, DQ, scenario sanity tests
│   └── test_reporting.py         # Report generation tests
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

Or run the pipeline step-by-step via notebooks (VS Code interactive Python):
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

## Dashboard Tabs

| Tab | Content |
|-----|---------|
| **Member Overview** | Posted vs required margin, coverage ratios, traffic-light status, margin calls |
| **Margin Decomposition** | Per-member breakdown: VaR, stress, liquidity add-on, concentration add-on |
| **Backtesting** | Actual loss vs margin time series, rolling exception count, exception heatmap |
| **Controls & DQ** | Stale data flags, outlier returns, exposure jumps, escalation log |
| **Committee Summary** | Daily summary, weekly exception report, monthly committee pack with export |

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

## Known Limitations

- Stylised margin formula, not a real CCP methodology
- Simplified liquidation assumptions (no auction / fire-sale dynamics)
- Limited product universe (equity/rates futures, listed options)
- Simplified collateral eligibility and haircut structure
- No auction/default management simulation
- No legal segregation/account structure modelling
- Scenario set may omit some cross-asset contagion channels
- No credit migration or member default probability modelling
- Static implied vol surface for options (no skew/term structure)

---

## Documentation

| Document | Location | Content |
|----------|----------|---------|
| Methodology Note | `docs/methodology_note.md` | Formulas, design choices, assumptions, limitations |
| Control Framework | `docs/control_framework.md` | DQ controls, pricing controls, escalation paths |
| Governance Note | `docs/governance_note.md` | Roles, thresholds, breach handling, committee cadence |

---

## Tests

```
tests/
├── test_margin.py      # VaR non-negativity, monotonicity, concentration increasing
├── test_pricing.py     # Black-Scholes sanity, call-put parity, delta bounds
├── test_controls.py    # Coverage ratio, traffic light, margin call logic, DQ checks
└── test_reporting.py   # Report content validation, markdown generation
```

Test categories:
- **Unit tests:** Margin non-negative, coverage handles zero, concentration monotonic
- **Control tests:** Stale data flagged, missing collateral flagged, implausible vol rejected
- **Scenario sanity:** Higher vol → higher margin, higher concentration → higher add-on, lower liquidity → higher loss
