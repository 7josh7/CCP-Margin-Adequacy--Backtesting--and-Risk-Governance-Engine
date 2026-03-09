# Breach Taxonomy
## CCP Margin Adequacy, Backtesting, and Risk Governance Engine

**Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal – Risk Governance

---

## 1. Purpose

This document defines the taxonomy of breach types recognised by the CCP Margin Engine: their definitions, severity classification, ownership, escalation mapping, and expected resolution timelines. A formal breach taxonomy ensures consistent classification across the daily risk review, breach register, and committee reporting.

---

## 2. Breach Definitions

| Breach Type | Description | Examples |
|-------------|-------------|---------|
| **Margin insufficiency** | Posted collateral is insufficient to cover the required margin (liquidation-adjusted loss) for a clearing member | Coverage ratio < 1.00; member in "red" traffic-light status |
| **Backtesting exception** | Realised loss on a given day exceeds the prior-day margin estimate, indicating the model under-predicted risk | Actual loss > prior-day required margin |
| **Data quality** | Input data used in the margin calculation is missing, stale, or anomalous | Stale prices (unchanged > 2 days), missing risk factors, outlier returns (|return| > 15%) |
| **Model control** | Automated model validation checks detect an inconsistency or failure in the calculation pipeline | Implausible volatility (<1% or >300%), failed Black-Scholes pricing (NaN/Inf/negative), unexplained exposure jumps (>3σ) |
| **Concentration breach** | A member's position exceeds defined thresholds relative to average daily volume, triggering a concentration add-on | Position/ADV > 10%; concentration add-on applied to baseline margin |

---

## 3. Severity Classification

| Severity | Definition | Response Time | Escalation Target |
|----------|-----------|:-------------:|-------------------|
| **Critical** | Margin calculation may be materially incorrect; immediate member collateral risk | Same day | Senior Risk Officer + Risk Committee |
| **High** | Significant control breach or margin shortfall requiring senior attention | 1 business day | Senior Risk Officer |
| **Medium** | Notable issue requiring investigation; does not impair calculation integrity | 3 business days | Risk Analyst |
| **Low** | Minor issue for tracking; no immediate impact | Next weekly review | Risk Analyst |

### Severity by Breach Type

| Breach Type | Default Severity | Elevated To | Elevation Condition |
|-------------|:----------------:|:-----------:|---------------------|
| Margin insufficiency | High | Critical | Coverage < 80% or consecutive red days ≥ 3 |
| Backtesting exception | Medium | High | Clustered exceptions (≥ 3 in 20 days) or rolling count ≥ 5 |
| Data quality | Medium | High | Critical risk factor affected (SPX, TY) or persists > 1 day |
| Model control | High | Critical | Affects > 3 members or primary pricing model |
| Concentration breach | Medium | High | Concentration add-on > 25% of total required margin |

---

## 4. Ownership Matrix

| Breach Type | Primary Owner | Secondary Owner | Escalation Owner |
|-------------|--------------|-----------------|------------------|
| Margin insufficiency | Clearing Risk | Margin Operations | Senior Risk Officer |
| Backtesting exception | Risk Methodology | Model Validation | Risk Committee |
| Data quality | Risk Control | Market Data Team | Senior Risk Officer |
| Model control | Quant Risk | Risk Methodology | Model Validation |
| Concentration breach | Clearing Risk | Risk Analyst | Risk Committee |

---

## 5. Escalation Mapping

| Breach Type | Level 1 (Analyst) | Level 2 (Senior) | Level 3 (Committee) |
|-------------|:-:|:-:|:-:|
| Margin insufficiency | Single red day: investigate & document | 2+ consecutive red: margin call recommendation | 5+ consecutive red: position limits / enhanced monitoring |
| Backtesting exception | Log exception; single occurrence review | 3–4 rolling: root cause analysis | ≥ 5 rolling: formal methodology review |
| Data quality | Flag & notify data team | Persistent > 1 day: mark run provisional | Critical factor missing > 2 days: risk committee |
| Model control | Investigate & apply fallback | Pricing failure on material position: provisional run | Systematic failure: model suspension |
| Concentration breach | Document & monitor | Add-on > 25% total: watchlist | Repeated breaches: position limit recommendation |

---

## 6. Breach Register Schema

Each breach is recorded in the breach register (`reports/daily/breach_register_*.csv`) with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `breach_id` | String | Unique identifier: `BRX-YYYYMMDD-NNNN` |
| `date` | Date | Date the breach was detected |
| `member_id` | String | Affected clearing member (or "SYSTEM" for data/model issues) |
| `breach_type` | String | One of: `margin_insufficiency`, `backtesting_exception`, `data_quality`, `model_control`, `concentration_breach` |
| `severity` | String | `critical`, `high`, `medium`, or `low` |
| `description` | String | Human-readable description of the specific breach |
| `owner` | String | Primary owner responsible for resolution |
| `status` | String | `open`, `investigating`, `resolved`, `accepted` |
| `escalation_level` | String | Current escalation: `analyst_review`, `senior_review`, `methodology_review`, `committee_watchlist` |
| `target_resolution_date` | Date | Expected resolution date based on severity SLA |

---

## 7. Resolution SLAs

| Severity | Investigation Start | Resolution Target | Report To |
|----------|:-------------------:|:-----------------:|-----------|
| Critical | Immediately (same hour) | Same business day | Risk Committee (ad-hoc) |
| High | Same business day | 1 business day | Senior Risk Officer |
| Medium | Next business day | 3 business days | Weekly exception report |
| Low | Within 3 business days | Next weekly review | Weekly exception report |

---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | March 2026 | Risk Governance | Initial version |
