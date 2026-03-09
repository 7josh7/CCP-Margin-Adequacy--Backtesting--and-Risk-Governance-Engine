"""
Module D – Adequacy testing (controls layer).

Compares posted collateral against required margin and classifies
each member-day into a traffic-light status with breach types.
Also computes margin call amounts respecting threshold and
minimum transfer rules.
"""

import pandas as pd
from src import config


# ──────────────────────────────────────────────────────────────────
# Core ratios
# ──────────────────────────────────────────────────────────────────
def coverage_ratio(posted: float, required: float) -> float:
    if required <= 0:
        return float("inf") if posted > 0 else 1.0
    return posted / required


def stress_coverage_ratio(posted: float, stressed_loss: float) -> float:
    if stressed_loss <= 0:
        return float("inf") if posted > 0 else 1.0
    return posted / stressed_loss


def buffer(posted: float, required: float) -> float:
    return posted - required


# ──────────────────────────────────────────────────────────────────
# Traffic light
# ──────────────────────────────────────────────────────────────────
def traffic_light(cov_ratio: float) -> str:
    if cov_ratio >= config.GREEN_THRESHOLD:
        return "green"
    if cov_ratio >= config.AMBER_THRESHOLD:
        return "amber"
    return "red"


# ──────────────────────────────────────────────────────────────────
# Margin call
# ──────────────────────────────────────────────────────────────────
def margin_call_amount(posted: float, required: float,
                       threshold: float = config.MARGIN_THRESHOLD,
                       min_transfer: float = config.MINIMUM_TRANSFER_AMOUNT
                       ) -> float:
    """
    Compute margin call respecting threshold and MTA.

    A call is only triggered when the shortfall exceeds the threshold,
    and the call amount must be at least the minimum transfer amount.
    """
    shortfall = required - posted
    if shortfall <= threshold:
        return 0.0
    call = max(shortfall, min_transfer)
    return round(call, 2)


# ──────────────────────────────────────────────────────────────────
# Breach classification
# ──────────────────────────────────────────────────────────────────
BREACH_TYPES = [
    "margin_insufficiency",
    "backtesting_exception_spike",
    "concentration_breach",
    "stale_market_data",
    "pricing_convergence_failure",
]


def classify_breaches(cov_ratio: float,
                      backtest_exceptions: int,
                      concentration_addon_pct: float,
                      has_stale_data: bool,
                      has_pricing_failure: bool) -> list[str]:
    """Return list of active breach types for a member-day."""
    breaches = []
    if cov_ratio < config.AMBER_THRESHOLD:
        breaches.append("margin_insufficiency")
    if backtest_exceptions >= config.BACKTEST_EXCEPTION_WARN:
        breaches.append("backtesting_exception_spike")
    if concentration_addon_pct > 0:
        breaches.append("concentration_breach")
    if has_stale_data:
        breaches.append("stale_market_data")
    if has_pricing_failure:
        breaches.append("pricing_convergence_failure")
    return breaches


# ──────────────────────────────────────────────────────────────────
# Batch adequacy
# ──────────────────────────────────────────────────────────────────
def compute_adequacy(margin_results: pd.DataFrame,
                     collateral: pd.DataFrame) -> pd.DataFrame:
    """
    Merge margin results with collateral and compute adequacy metrics.

    Returns a DataFrame with:
        date, member_id, required_margin, posted_margin,
        coverage_ratio, buffer, traffic_light,
        margin_call, baseline_margin, liquidity_addon,
        concentration_addon
    """
    merged = margin_results.merge(
        collateral[["date", "member_id", "collateral_value_post_haircut"]],
        on=["date", "member_id"],
        how="left"
    )
    merged["posted_margin"] = merged["collateral_value_post_haircut"].fillna(0)

    merged["coverage_ratio"] = merged.apply(
        lambda r: coverage_ratio(r["posted_margin"], r["required_margin"]),
        axis=1
    )
    merged["buffer"] = merged.apply(
        lambda r: buffer(r["posted_margin"], r["required_margin"]),
        axis=1
    )
    merged["traffic_light"] = merged["coverage_ratio"].apply(traffic_light)
    merged["margin_call"] = merged.apply(
        lambda r: margin_call_amount(r["posted_margin"], r["required_margin"]),
        axis=1
    )

    cols = ["date", "member_id", "required_margin", "posted_margin",
            "coverage_ratio", "buffer", "traffic_light", "margin_call",
            "baseline_margin", "liquidity_addon", "concentration_addon",
            "hs_var", "stressed_var"]
    return merged[[c for c in cols if c in merged.columns]].round(2)
