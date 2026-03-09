"""
Liquidity add-on calculation.

Captures the cost of liquidating a position that ordinary VaR
ignores: bid-ask crossing cost and market impact from selling
into limited depth.

Formula (simplified):
    liq_cost = half_spread_cost + impact_coeff * sqrt(|position_size| / ADV) * price

Or, for v1 simplicity:
    liq_addon = base_margin * liquidity_multiplier

Both paths are implemented; the engine uses the detailed path when
ADV data is available.
"""

import numpy as np
import pandas as pd
from src import config


def spread_cost(quantity: float, spot: float, bid_ask_bps: float,
                contract_multiplier: float) -> float:
    """Half-spread crossing cost for the full position."""
    half_spread = spot * (bid_ask_bps / 10_000) / 2
    return abs(quantity) * contract_multiplier * half_spread


def market_impact(quantity: float, spot: float, adv: float,
                  contract_multiplier: float,
                  coeff: float = config.IMPACT_COEFFICIENT) -> float:
    """Price-impact estimate: coeff * sqrt(|size| / ADV) * notional."""
    position_lots = abs(quantity)
    if adv <= 0:
        return 0.0
    impact_frac = coeff * np.sqrt(position_lots / adv)
    return impact_frac * spot * abs(quantity) * contract_multiplier


def liquidation_horizon_scale(base_amount: float,
                              liquidity_bucket: str) -> float:
    """Scale a 1-day risk amount to the liquidation horizon."""
    horizon = config.LIQUIDATION_HORIZONS.get(liquidity_bucket,
                                              config.RISK_HORIZON_DEFAULT)
    return base_amount * np.sqrt(horizon)


def compute_liquidity_addon(positions_day: pd.DataFrame,
                            instruments: pd.DataFrame,
                            market_data_day: pd.DataFrame,
                            base_margin: float | None = None,
                            member_liq_mult: float = 1.0) -> float:
    """
    Compute total liquidity add-on for one member on one day.

    If detailed data is present, uses spread + impact.
    Falls back to base_margin * liquidity_multiplier otherwise.
    """
    inst_map = instruments.set_index("instrument_id")
    md_map = market_data_day.set_index("risk_factor_id")

    total = 0.0
    detail_available = True

    for _, pos in positions_day.iterrows():
        iid = pos["instrument_id"]
        if iid not in inst_map.index:
            detail_available = False
            continue
        inst = inst_map.loc[iid]
        und = inst["underlying"]
        if und not in md_map.index:
            detail_available = False
            continue

        md_row = md_map.loc[und]
        if isinstance(md_row, pd.DataFrame):
            md_row = md_row.iloc[0]

        spot = md_row["spot"]
        ba = md_row["bid_ask_bps"]
        adv = md_row["avg_daily_volume"]
        liq_bucket = md_row["liquidity_bucket"]
        mult = float(inst["contract_multiplier"])
        qty = pos["quantity"]

        sc = spread_cost(qty, spot, ba, mult)
        mi = market_impact(qty, spot, adv, mult)
        raw = sc + mi
        scaled = liquidation_horizon_scale(raw, liq_bucket)
        total += scaled

    # Apply member-level multiplier
    total *= member_liq_mult

    # Fallback
    if not detail_available and base_margin is not None:
        total = max(total, base_margin * (member_liq_mult - 1.0))

    return round(total, 2)
