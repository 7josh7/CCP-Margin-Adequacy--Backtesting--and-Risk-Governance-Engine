"""
Module C – Margin methodology engine.

Combines:
    1. Baseline margin  (Historical Simulation VaR / Stressed VaR)
    2. Liquidity add-on
    3. Concentration add-on

Final formula:
    Initial Margin = max(HSVaR, StressLossQuantile) + LiquidityAddOn + ConcentrationAddOn

IMPORTANT: This is a stylised methodology, not a real CCP margin formula.
"""

import numpy as np
import pandas as pd
from src import config
from src.pricing import compute_daily_pnl, price_instrument
from src.scenarios import (historical_return_scenarios,
                           stressed_return_scenarios,
                           apply_scenario)
from src.liquidity import compute_liquidity_addon
from src.concentration import compute_concentration_addon


# ──────────────────────────────────────────────────────────────────
# Historical Simulation VaR
# ──────────────────────────────────────────────────────────────────
def historical_simulation_var(pnl_series: pd.Series,
                              confidence: float = config.CONFIDENCE_LEVEL
                              ) -> float:
    """
    Compute VaR from a series of daily P&L values.
    Convention: losses are negative; VaR returned as a positive number.
    """
    if pnl_series.empty:
        return 0.0
    quantile = pnl_series.quantile(1 - confidence)
    return max(-quantile, 0.0)


def stressed_var(pnl_series: pd.Series,
                 market_data: pd.DataFrame,
                 confidence: float = config.CONFIDENCE_LEVEL) -> float:
    """
    VaR computed only over the stressed sub-window.
    Falls back to normal VaR if window is too short.
    """
    stressed_ret = stressed_return_scenarios(market_data)
    stressed_dates = set(stressed_ret.index)
    stressed_pnl = pnl_series[pnl_series.index.isin(stressed_dates)]
    if len(stressed_pnl) < 10:
        return historical_simulation_var(pnl_series, confidence)
    return historical_simulation_var(stressed_pnl, confidence)


# ──────────────────────────────────────────────────────────────────
# Full margin calculation for one member on one day
# ──────────────────────────────────────────────────────────────────
def compute_member_margin(member_id: str,
                          date: pd.Timestamp,
                          pnl_history: pd.DataFrame,
                          positions: pd.DataFrame,
                          instruments: pd.DataFrame,
                          market_data: pd.DataFrame,
                          members: pd.DataFrame) -> dict:
    """
    Compute full margin requirement for *member_id* on *date*.

    Returns dict with all components and breach details.
    """
    # ── Member attributes ─────────────────────────────────────────
    mem_row = members[members["member_id"] == member_id].iloc[0]
    liq_mult = mem_row["liquidity_multiplier"]

    # ── 1. Baseline VaR ──────────────────────────────────────────
    member_pnl = pnl_history[pnl_history["member_id"] == member_id].copy()
    member_pnl = member_pnl[member_pnl["date"] <= date].tail(config.HIST_WINDOW)

    if member_pnl.empty:
        hs_var = 0.0
        s_var = 0.0
    else:
        pnl_s = member_pnl.set_index("date")["pnl_1d"]
        hs_var = historical_simulation_var(pnl_s)
        s_var = stressed_var(pnl_s, market_data)

    baseline = max(hs_var, s_var)

    # ── 2. Liquidity add-on ──────────────────────────────────────
    pos_day = positions[(positions["date"] == date) &
                        (positions["member_id"] == member_id)]
    md_day = market_data[market_data["date"] == date]

    liq_addon = compute_liquidity_addon(pos_day, instruments, md_day,
                                        base_margin=baseline,
                                        member_liq_mult=liq_mult)

    # ── 3. Concentration add-on ──────────────────────────────────
    conc_addon, conc_breaches = compute_concentration_addon(
        pos_day, instruments, md_day, baseline)

    # ── Total ────────────────────────────────────────────────────
    required_margin = baseline + liq_addon + conc_addon

    return {
        "date": date,
        "member_id": member_id,
        "hs_var": round(hs_var, 2),
        "stressed_var": round(s_var, 2),
        "baseline_margin": round(baseline, 2),
        "liquidity_addon": round(liq_addon, 2),
        "concentration_addon": round(conc_addon, 2),
        "required_margin": round(required_margin, 2),
        "concentration_breaches": conc_breaches,
    }


# ──────────────────────────────────────────────────────────────────
# Batch: all members, all dates
# ──────────────────────────────────────────────────────────────────
def compute_all_margins(pnl_history: pd.DataFrame,
                        positions: pd.DataFrame,
                        instruments: pd.DataFrame,
                        market_data: pd.DataFrame,
                        members: pd.DataFrame,
                        start_date: pd.Timestamp | None = None
                        ) -> pd.DataFrame:
    """
    Run margin calculation for every member on every date after
    a warm-up period (HIST_WINDOW days).

    Returns a flat DataFrame of margin results.
    """
    dates = sorted(positions["date"].unique())
    warmup = config.HIST_WINDOW
    calc_dates = dates[warmup:] if start_date is None else [d for d in dates if d >= start_date]

    member_ids = members["member_id"].tolist()
    results = []

    for d in calc_dates:
        for mid in member_ids:
            res = compute_member_margin(mid, d, pnl_history,
                                        positions, instruments,
                                        market_data, members)
            # Drop nested list for flat storage
            res_flat = {k: v for k, v in res.items()
                        if k != "concentration_breaches"}
            results.append(res_flat)

    return pd.DataFrame(results)
