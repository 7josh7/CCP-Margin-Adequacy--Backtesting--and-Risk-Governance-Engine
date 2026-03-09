# Control Framework
## CCP Margin Adequacy, Backtesting, and Risk Governance Engine

**Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal – Risk Controls

---

## 1. Purpose

This document defines the control framework governing data quality, pricing integrity, model monitoring, issue classification, and escalation paths for the CCP Margin Engine. Controls exist to ensure that margin calculations are based on reliable inputs and that any degradation in data or model quality is detected, classified, and escalated promptly.

---

## 2. Data Quality Controls

### 2.1 Stale Data Detection

| Control ID | DQ-001 |
|-----------|--------|
| **Description** | Detect risk factors where the price has not changed for more than 2 consecutive business days |
| **Threshold** | 2 days of zero return |
| **Action** | Flag as stale; notify Market Data team; mark daily run as provisional if critical risk factor |
| **Owner** | Market Data Team |
| **Frequency** | Daily, pre-margin calculation |

### 2.2 Missing Data Detection

| Control ID | DQ-002 |
|-----------|--------|
| **Description** | Detect risk factors that are completely absent from the day's market data feed |
| **Threshold** | Any expected risk factor missing |
| **Action** | Use prior-day value with staleness flag; escalate if persists > 1 day |
| **Owner** | Market Data Team |
| **Frequency** | Daily |

### 2.3 Outlier Return Detection

| Control ID | DQ-003 |
|-----------|--------|
| **Description** | Flag daily returns exceeding ±15% |
| **Threshold** | |return_1d| > 0.15 |
| **Action** | Manual verification required; if confirmed genuine, document; if error, correct and re-run |
| **Owner** | Risk Analyst |
| **Frequency** | Daily |

### 2.4 Implausible Volatility

| Control ID | DQ-004 |
|-----------|--------|
| **Description** | Flag annualised volatility values outside plausible range |
| **Threshold** | vol < 1% or vol > 300% |
| **Action** | Reject value; use fallback (prior-day vol or long-run average); document override |
| **Owner** | Risk Analyst |
| **Frequency** | Daily |

### 2.5 Exposure Jump Detection

| Control ID | DQ-005 |
|-----------|--------|
| **Description** | Detect member-instrument pairs where day-over-day market value changes by more than 3 standard deviations without a commensurate market move |
| **Threshold** | |ΔMV| > μ + 3σ of historical daily MV changes |
| **Action** | Investigate cause (position change vs. data error); document finding |
| **Owner** | Risk Analyst |
| **Frequency** | Daily |

---

## 3. Pricing Controls

### 3.1 Option Pricing Convergence

| Control ID | PR-001 |
|-----------|--------|
| **Description** | Verify Black-Scholes option pricing produces valid (non-negative, finite) values |
| **Threshold** | Price < 0 or Price = NaN/Inf |
| **Action** | Flag as pricing failure; use prior-day valuation; mark member results as provisional |
| **Owner** | Quant / Risk Analyst |
| **Frequency** | Daily |

### 3.2 Cross-Validation

| Control ID | PR-002 |
|-----------|--------|
| **Description** | Verify that portfolio P&L is consistent with observed market moves (delta-approximated P&L should be within tolerance of full-reval P&L) |
| **Threshold** | |Full Reval PnL - Delta PnL| > 20% of Full Reval PnL |
| **Action** | Investigate; likely indicates convexity not captured or data issue |
| **Owner** | Quant Team |
| **Frequency** | Weekly |

---

## 4. Model Monitoring Controls

### 4.1 Backtesting Exception Count

| Control ID | MM-001 |
|-----------|--------|
| **Description** | Track rolling 250-day count of backtesting exceptions per member |
| **Thresholds** | Green: < 3 | Amber: 3–4 | Red: ≥ 5 |
| **Action** | Amber: increased monitoring; Red: methodology review trigger |
| **Owner** | Model Validation / Risk Committee |
| **Frequency** | Daily computation, weekly review |

### 4.2 Exception Clustering

| Control ID | MM-002 |
|-----------|--------|
| **Description** | Detect whether exceptions cluster in time (indicating systematic model weakness in specific regimes) rather than being randomly distributed |
| **Method** | Visual inspection of exception timing vs. market volatility regime |
| **Action** | If clustering detected, assess whether model responsiveness needs improvement |
| **Owner** | Model Validation |
| **Frequency** | Monthly |

### 4.3 Margin Responsiveness

| Control ID | MM-003 |
|-----------|--------|
| **Description** | Monitor whether margin requirements respond appropriately to regime changes (e.g., vol spike should increase margin) |
| **Method** | Compare margin level changes vs. realised vol changes |
| **Action** | If margin is unresponsive during stress, investigate VaR window and model calibration |
| **Owner** | Risk Methodology |
| **Frequency** | Monthly |

---

## 5. Issue Classification

Every detected issue is classified by:

### Severity

| Level | Definition | Response Time |
|-------|-----------|---------------|
| **Critical** | Margin calculation may be materially incorrect; member collateral at risk | Same day |
| **High** | Significant control breach; requires senior attention | 1 business day |
| **Medium** | Notable issue requiring investigation | 3 business days |
| **Low** | Minor issue for tracking | Next weekly review |

### Issue Categories

| Category | Examples |
|----------|---------|
| Data Quality | Stale prices, missing data, outlier returns |
| Pricing | Non-convergent Black-Scholes, negative prices |
| Model Performance | Excessive backtesting exceptions, unresponsive margin |
| Concentration | Single-name or single-product crowding |
| Collateral | Haircut anomalies, valuation mismatches |
| Operational | Late data feeds, system errors |

---

## 6. Escalation Paths

```
┌─────────────────────────────────────────────────────┐
│                     Issue Detected                   │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Auto-classify  │
              │  severity/type  │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼───┐   ┌────▼────┐  ┌────▼────────┐
    │  Low   │   │ Medium  │  │ High/Critical│
    └────┬───┘   └────┬────┘  └────┬────────┘
         │            │            │
    ┌────▼────┐  ┌───▼─────┐  ┌──▼──────────┐
    │ Weekly  │  │ Analyst │  │ Senior Risk │
    │ Review  │  │ Review  │  │ Officer     │
    └─────────┘  └─────────┘  └──┬──────────┘
                                  │
                            ┌─────▼────────┐
                            │ Risk         │
                            │ Committee    │
                            └──────────────┘
```

### Detailed Escalation Rules

| Rule ID | Trigger | Action | Owner |
|---------|---------|--------|-------|
| ESC-001 | Single red breach day | Analyst review – confirm cause and document | Risk Analyst |
| ESC-002 | 2+ consecutive red days | Senior risk officer review – margin call recommendation | Senior Risk Officer |
| ESC-003 | ≥ 4 backtesting exceptions (250-day rolling) | Methodology review trigger – model adequacy assessment | Model Validation |
| ESC-004 | Concentration add-on > 25% of total margin | Add member to committee watchlist | Risk Committee |
| ESC-005 | Critical stale market data | Daily run marked provisional – data team notified | Market Data Team |
| ESC-006 | Margin call above threshold and MTA | Issue margin call to member – operations notified | Margin Operations |

---

## 7. Provisional Run Protocol

When a control failure is detected that may affect margin accuracy but does not halt the calculation:

1. The daily run is completed but flagged as **provisional**
2. All reports generated from a provisional run carry a visible warning banner
3. The provisional flag is cleared only after the underlying issue is resolved and the run is re-executed, or a senior risk officer signs off on the provisional results
4. Provisional runs are tracked in the model change log

### Provisional-Run Criteria

A run is marked provisional when any of the following conditions hold:

| Condition | Trigger | Action |
|-----------|---------|--------|
| Critical risk factor stale | Primary equity or rates factor unchanged > 2 days | Use prior values; flag |
| Missing risk factor | Any expected factor absent | Fill from prior day; flag |
| Pricing failure | Black-Scholes returns NaN/Inf/negative on material position | Use prior-day price; flag |
| Volume data absent | ADV unavailable for liquidity calculation | Use fallback ADV; flag |

---

## 8. Model Performance Review Framework

The model performance review framework defines how the margin model is monitored for ongoing adequacy and when corrective action is triggered.

### 8.1 Rolling Exception Monitoring

- **Metric:** 250-business-day rolling count of backtesting exceptions per member
- **Frequency:** Computed daily, reviewed weekly
- **Thresholds:**
  - Green: < 3 exceptions → standard monitoring
  - Amber: 3–4 exceptions → increased monitoring, root cause analysis
  - Red: ≥ 5 exceptions → formal methodology review triggered

### 8.2 Exception Clustering Rule

Exceptions are examined for temporal clustering vs. random distribution:

- If ≥ 3 exceptions occur within any 20-business-day window: clustering is flagged
- Clustered exceptions indicate systematic model weakness in a specific regime
- Non-clustered exceptions may reflect rare but valid tail events

### 8.3 Regime-Based Analysis

When exception clustering is detected, the model performance review includes:

1. **Regime identification** — classify the period as low-vol, normal, or high-vol based on realised SPX volatility
2. **Regime-specific exception rate** — compute exception frequency within each regime
3. **Model responsiveness** — verify that margin levels increase during vol transitions (margin should respond within 5–10 trading days of a vol regime shift)
4. **Responsiveness gap** — if margin fails to increase during a vol spike and exceptions occur, this is a model weakness rather than a data issue

### 8.4 Methodology Review Trigger

A formal methodology review is triggered when:

| Trigger | Review Scope | Owner |
|---------|-------------|-------|
| ≥ 5 exceptions (rolling 250d) for any member | Full model adequacy assessment | Model Validation |
| ≥ 3 clustered exceptions (within 20d) | Regime-specific calibration review | Risk Methodology |
| Margin unresponsive during vol spike | VaR window and lookback assessment | Risk Methodology |
| HSVaR and Stressed VaR persistently equal | Stressed window selection review | Model Validation |

### 8.5 Control Override Tracking

Any manual override of a model-control check must be documented:

| Field | Description |
|-------|-------------|
| Override ID | Sequential identifier |
| Date | When override was applied |
| Control ID | Which control was overridden (e.g., DQ-001) |
| Reason | Justification for override |
| Duration | Expected duration of override |
| Approved By | Senior Risk Officer or Risk Committee |
| Review Date | When override will be reassessed |
| Status | Active / Expired / Revoked |

---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | March 2026 | Risk Controls | Initial version |
| 1.1 | March 2026 | Risk Controls | Added provisional-run criteria, model performance review framework, control override tracking |
