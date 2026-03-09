# Governance Note
## CCP Margin Adequacy, Backtesting, and Risk Governance Engine

**Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal – Risk Governance

---

## 1. Purpose

This document defines the governance structure, roles and responsibilities, decision thresholds, breach handling procedures, reporting cadence, and model change management for the CCP Margin Engine. The objective is to ensure that margin adequacy is maintained through a governed, auditable process with clear accountability.

---

## 2. Roles and Responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Risk Analyst** | Daily monitoring; first-line investigation of amber/red breaches; data quality review; documentation of findings |
| **Senior Risk Officer** | Escalation recipient for consecutive red days and high-severity issues; approves margin call recommendations; signs off on provisional runs |
| **Model Validation** | Backtesting review; methodology adequacy assessment when exception thresholds are breached; independent challenge of margin model |
| **Risk Committee** | Monthly review of committee pack; approval of methodology changes; oversight of watchlist members; strategic risk decisions |
| **Market Data Team** | Resolution of stale/missing data issues; data feed monitoring; coordination with vendors |
| **Margin Operations** | Execution of margin calls; communication with clearing members; tracking of collateral receipts |
| **Quant Team** | Pricing model maintenance; convergence issue resolution; model enhancement proposals |

---

## 3. Threshold Table

### Margin Adequacy Thresholds

| Metric | Green | Amber | Red |
|--------|:-----:|:-----:|:---:|
| Coverage Ratio | ≥ 1.10 | 1.00 – 1.10 | < 1.00 |
| Backtesting Exceptions (250d) | < 3 | 3 – 4 | ≥ 5 |
| Concentration Add-On % of Total | < 10% | 10% – 25% | > 25% |

### Margin Call Thresholds

| Parameter | Value | Rationale |
|-----------|------:|-----------|
| Margin Threshold | $100,000 | Shortfall must exceed this to trigger a call |
| Minimum Transfer Amount | $100,000 | Minimum size of any margin call issued |

These thresholds balance operational burden against unsecured exposure, consistent with standard repo-style margining practice.

### Data Quality Thresholds

| Check | Threshold | Action Level |
|-------|-----------|:------------:|
| Stale Data | > 2 days unchanged | Medium |
| Missing Data | Any expected factor absent | Medium → High if > 1 day |
| Outlier Return | |return| > 15% | Medium |
| Implausible Vol | < 1% or > 300% annual | High |
| Exposure Jump | > 3σ day-over-day change | Medium |

---

## 4. Breach Handling Procedures

### 4.1 Margin Insufficiency Breach (Coverage < 1.00)

```
Day 1  → Risk Analyst investigates
         ├── Identifies cause (market move / position change / data issue)
         ├── Documents root cause
         └── Assesses whether margin call is warranted

Day 2+ → If still red:
         ├── Senior Risk Officer review
         ├── Margin call recommendation prepared
         └── Member notified

Day 5+ → If unresolved:
         ├── Risk Committee notified
         └── Enhanced monitoring / position limits considered
```

### 4.2 Backtesting Exception Breach

```
Exceptions ≥ 4 (rolling 250 days) → Model Validation triggered
         ├── Review model assumptions and calibration
         ├── Assess whether exceptions are clustered or random
         ├── Determine if model enhancement is needed
         └── Report findings to Risk Committee

Exceptions ≥ 5 → Formal methodology review
         ├── Full model adequacy assessment
         ├── Benchmark against alternative approaches
         └── Recommendation: recalibrate, enhance, or accept with documented rationale
```

### 4.3 Concentration Breach

```
Concentration add-on > 25% of total margin → Committee watchlist
         ├── Analyst documents concentration details
         ├── Member contacted for position clarification
         ├── Assessment of liquidation feasibility
         └── Committee decides: accept / impose limit / require additional margin
```

### 4.4 Data Quality Breach

```
Critical data issue detected → Run flagged as provisional
         ├── Market Data team notified immediately
         ├── Fallback values used (prior-day or long-run average)
         ├── Issue tracked until resolution
         └── Run re-executed once data corrected, or senior sign-off obtained
```

---

## 5. Committee Reporting Cadence

| Report | Frequency | Audience | Content |
|--------|-----------|----------|---------|
| **Daily Risk Summary** | Every business day | Risk Analysts, Senior Risk Officer | Aggregate margin, coverage by member, breaches, margin calls, DQ exceptions |
| **Weekly Exception Report** | Weekly (Friday) | Risk Team, Model Validation | Backtesting exceptions, concentration breaches, stale data, escalation summary |
| **Monthly Committee Pack** | Monthly (first Monday) | Risk Committee | Margin trend, stressed members, coverage distribution, backtesting summary, concentration analysis, methodology changes, limitations, recommended actions |

### Committee Pack Content Requirements

The monthly committee pack must include:
1. **Trend analysis** – Total required margin trajectory over 30 days
2. **Top stressed members** – 5 weakest by average coverage ratio
3. **Coverage distribution** – Statistical summary of all members
4. **Backtesting performance** – Exception counts and clustering analysis
5. **Concentration events** – Members with significant concentration add-ons
6. **Methodology status** – Any pending changes or reviews
7. **Known limitations** – Current model limitations and planned improvements
8. **Recommended actions** – Specific items for committee decision

---

## 6. Model Change Log Template

All changes to the margin methodology, thresholds, or control parameters must be documented in the model change log.

| Field | Description |
|-------|-------------|
| Change ID | Sequential identifier (e.g., MCL-2026-001) |
| Date Proposed | When the change was proposed |
| Date Approved | When committee/senior officer approved |
| Date Implemented | When deployed to production |
| Category | Methodology / Threshold / Control / Data |
| Description | Clear description of what changed |
| Rationale | Why the change is needed |
| Impact Assessment | Expected effect on margin levels and member coverage |
| Approved By | Name and role of approver |
| Implemented By | Name of person who deployed the change |
| Rollback Plan | How to revert if the change causes issues |

### Example Entry

| Field | Value |
|-------|-------|
| Change ID | MCL-2026-001 |
| Date Proposed | 2026-03-01 |
| Date Approved | 2026-03-05 |
| Date Implemented | 2026-03-10 |
| Category | Threshold |
| Description | Increased backtesting exception red threshold from 5 to 6 |
| Rationale | Review showed 5 was overly sensitive given current vol regime |
| Impact Assessment | Reduces false-positive methodology reviews by ~20% |
| Approved By | Chief Risk Officer |
| Implemented By | Risk Methodology Team |
| Rollback Plan | Revert config.BACKTEST_EXCEPTION_CRITICAL to 5 |

---

## 7. Governance Tiers

Members are assigned governance tiers based on their risk profile:

| Tier | Criteria | Enhanced Requirements |
|------|----------|----------------------|
| **Tier 1** | Weak liquidity, concentrated positions, or history of breaches | Daily senior review; lower margin call threshold; quarterly on-site review |
| **Tier 2** | Standard members meeting normal criteria | Standard monitoring; standard thresholds |

Tier assignment is reviewed quarterly by the Risk Committee.

---

## 8. Parameter Governance Table

All key model parameters are subject to formal governance. Changes require approval per the model change log process.

| Parameter | Current Value | Config Key | Owner | Review Frequency | Trigger for Review | Approval Status |
|-----------|-------------:|------------|-------|------------------|--------------------|-----------------|
| VaR confidence level | 99% | `CONFIDENCE_LEVEL` | Risk Methodology | Annual | Exception rate drift above expected 1% | Approved |
| Historical window | 500 days | `HIST_WINDOW` | Risk Methodology | Annual | Regime coverage concern | Approved |
| Stressed window | 60 days | `STRESSED_WINDOW` | Risk Methodology | Quarterly | Stress undercoverage | Approved |
| Impact coefficient | 0.10 | `IMPACT_COEFFICIENT` | Liquidity Risk | Monthly | Persistent liquidation shortfall | Under review |
| Concentration bands | 10%/20% ADV | `CONCENTRATION_BANDS` | Clearing Risk | Quarterly | Repeated crowding breaches | Approved |
| Green threshold | 110% | `GREEN_THRESHOLD` | Risk Committee | Annual | Traffic-light distribution review | Approved |
| Amber threshold | 100% | `AMBER_THRESHOLD` | Risk Committee | Annual | Traffic-light distribution review | Approved |
| Margin threshold | $100,000 | `MARGIN_THRESHOLD` | Margin Operations | Semi-annual | Operational efficiency review | Approved |
| Minimum transfer amount | $100,000 | `MINIMUM_TRANSFER_AMOUNT` | Margin Operations | Semi-annual | Operational efficiency review | Approved |
| Exception warning level | 3 | `BACKTEST_EXCEPTION_WARN` | Model Validation | Annual | False-positive rate assessment | Approved |
| Exception critical level | 5 | `BACKTEST_EXCEPTION_CRITICAL` | Model Validation | Annual | Methodology review frequency | Approved |
| Stale data threshold | 2 days | `STALE_DATA_THRESHOLD_DAYS` | Market Data Team | Quarterly | Data feed reliability changes | Approved |
| Outlier return threshold | 15% | `OUTLIER_RETURN_THRESHOLD` | Risk Analyst | Semi-annual | Market regime shifts | Approved |

---

## 9. Escalation Ladder

The escalation ladder defines the chain of authority for risk events of increasing severity:

```
Level 1: Risk Analyst
    └── First-line investigation (same day)
    └── Amber breaches, single-day red, DQ issues

Level 2: Senior Risk Officer
    └── Consecutive red days, margin call recommendations
    └── Sign-off on provisional runs
    └── Must respond within 1 business day

Level 3: Model Validation
    └── Backtesting exception threshold breached
    └── Methodology review and independent challenge
    └── Report to Risk Committee within 10 business days

Level 4: Risk Committee
    └── Strategic decisions on model changes
    └── Watchlist additions/removals
    └── Approval of methodology enhancements
    └── Monthly review, ad-hoc if critical
```

---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | March 2026 | Risk Governance | Initial version |
| 1.1 | March 2026 | Risk Governance | Added parameter governance table, escalation ladder |
