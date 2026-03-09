"""
Module B – Pricing and P&L engine.

Computes base present values and daily P&L for futures (linear)
and listed options (Black-Scholes).  Also provides a scenario
engine for shocked P&L computation.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from src import config


# ──────────────────────────────────────────────────────────────────
# Black-Scholes helpers
# ──────────────────────────────────────────────────────────────────
def _bs_d1(S, K, T, r, sigma):
    with np.errstate(divide="ignore", invalid="ignore"):
        return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def _bs_price(S, K, T, r, sigma, opt_type):
    """Vectorised Black-Scholes price."""
    d1 = _bs_d1(S, K, T, r, sigma)
    d2 = d1 - sigma * np.sqrt(T)
    if opt_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _bs_delta(S, K, T, r, sigma, opt_type):
    d1 = _bs_d1(S, K, T, r, sigma)
    if opt_type == "call":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1.0


# ──────────────────────────────────────────────────────────────────
# Single-instrument pricing
# ──────────────────────────────────────────────────────────────────
def price_instrument(inst_row: pd.Series, spot: float, vol: float,
                     T: float = 0.25, r: float = config.RISK_FREE_RATE) -> float:
    """Return per-contract PV for a single instrument."""
    mult = float(inst_row["contract_multiplier"])
    if inst_row["instrument_type"] == "future":
        return spot * mult
    # Option
    K = float(inst_row["strike"])
    T = max(T, 1 / 365)  # avoid zero
    sigma = max(vol, 0.01)
    opt_px = _bs_price(spot, K, T, r, sigma, inst_row["option_type"])
    return opt_px * mult


def delta_instrument(inst_row: pd.Series, spot: float, vol: float,
                     T: float = 0.25, r: float = config.RISK_FREE_RATE) -> float:
    mult = float(inst_row["contract_multiplier"])
    if inst_row["instrument_type"] == "future":
        return mult
    K = float(inst_row["strike"])
    sigma = max(vol, 0.01)
    return _bs_delta(spot, K, max(T, 1/365), r, sigma, inst_row["option_type"]) * mult


# ──────────────────────────────────────────────────────────────────
# Portfolio-level daily P&L
# ──────────────────────────────────────────────────────────────────
def compute_daily_pnl(positions: pd.DataFrame,
                      instruments: pd.DataFrame,
                      market_data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute member-level daily P&L by full revaluation.

    Returns DataFrame with columns:
        date, member_id, base_pv, pnl_1d
    """
    inst_map = instruments.set_index("instrument_id")
    dates = sorted(positions["date"].unique())

    records = []
    prev_pv = {}  # (member, instrument) -> prior PV

    for d in dates:
        day_pos = positions[positions["date"] == d]
        day_md = market_data[market_data["date"] == d].set_index("risk_factor_id")

        member_pv = {}
        for _, row in day_pos.iterrows():
            mid = row["member_id"]
            iid = row["instrument_id"]
            qty = row["quantity"]

            inst = inst_map.loc[iid]
            und = inst["underlying"]
            if und not in day_md.index:
                continue
            spot = day_md.loc[und, "spot"]
            vol = day_md.loc[und, "vol"]
            if isinstance(spot, pd.Series):
                spot = spot.iloc[0]
                vol = vol.iloc[0]

            pv = price_instrument(inst, spot, vol) * qty
            key = (mid, iid)
            pnl_1d = pv - prev_pv.get(key, pv)
            prev_pv[key] = pv

            member_pv.setdefault(mid, {"base_pv": 0.0, "pnl_1d": 0.0})
            member_pv[mid]["base_pv"] += pv
            member_pv[mid]["pnl_1d"] += pnl_1d

        for mid, vals in member_pv.items():
            records.append({
                "date": d,
                "member_id": mid,
                "base_pv": round(vals["base_pv"], 2),
                "pnl_1d": round(vals["pnl_1d"], 2),
            })

    return pd.DataFrame(records)


# ──────────────────────────────────────────────────────────────────
# Scenario P&L (for stress / margin calc)
# ──────────────────────────────────────────────────────────────────
def scenario_pnl(positions_day: pd.DataFrame,
                 instruments: pd.DataFrame,
                 base_md: pd.Series,
                 shocked_md: pd.Series) -> dict:
    """
    Compute portfolio PV change when moving from *base_md* spots
    to *shocked_md* spots.  Returns {member_id: loss} where
    loss > 0 means money lost.
    """
    inst_map = instruments.set_index("instrument_id")
    pnl = {}
    for _, row in positions_day.iterrows():
        mid = row["member_id"]
        iid = row["instrument_id"]
        qty = row["quantity"]
        inst = inst_map.loc[iid]
        und = inst["underlying"]

        base_spot = base_md.get(und, {}).get("spot", None)
        shocked_spot = shocked_md.get(und, {}).get("spot", None)
        vol = base_md.get(und, {}).get("vol", 0.20)
        if base_spot is None or shocked_spot is None:
            continue

        pv_base = price_instrument(inst, base_spot, vol) * qty
        pv_shock = price_instrument(inst, shocked_spot, vol) * qty
        loss = -(pv_shock - pv_base)  # positive = loss
        pnl[mid] = pnl.get(mid, 0.0) + loss

    return pnl
