"""
Concentration add-on calculation.

If a member's position in one product exceeds a threshold fraction
of average daily volume, an add-on is applied to penalise the
additional liquidation risk from crowdedness.

Bands (configurable in config.py):
    < 10 % ADV  →  0 %
    10–20 % ADV →  +10 %
    > 20 % ADV  →  +25 %
"""

import numpy as np
import pandas as pd
from src import config


def _adv_fraction(quantity: float, adv: float) -> float:
    if adv <= 0:
        return 0.0
    return abs(quantity) / adv


def concentration_rate(adv_frac: float) -> float:
    """Return the add-on rate for a given ADV fraction."""
    for threshold, rate in config.CONCENTRATION_BANDS:
        if adv_frac < threshold:
            return rate
    return config.CONCENTRATION_BANDS[-1][1]


def compute_concentration_addon(positions_day: pd.DataFrame,
                                instruments: pd.DataFrame,
                                market_data_day: pd.DataFrame,
                                base_margin: float) -> tuple[float, list]:
    """
    Compute total concentration add-on for one member on one day.

    Returns (addon_amount, breach_details) where breach_details is
    a list of dicts for any instrument that exceeds the lowest band.
    """
    inst_map = instruments.set_index("instrument_id")
    md_map = market_data_day.set_index("risk_factor_id")

    max_rate = 0.0
    breaches = []

    for _, pos in positions_day.iterrows():
        iid = pos["instrument_id"]
        if iid not in inst_map.index:
            continue
        inst = inst_map.loc[iid]
        und = inst["underlying"]
        if und not in md_map.index:
            continue

        md_row = md_map.loc[und]
        if isinstance(md_row, pd.DataFrame):
            md_row = md_row.iloc[0]

        adv = md_row["avg_daily_volume"]
        qty = pos["quantity"]
        frac = _adv_fraction(qty, adv)
        rate = concentration_rate(frac)

        if rate > 0:
            breaches.append({
                "instrument_id": iid,
                "underlying": und,
                "quantity": qty,
                "adv": adv,
                "adv_fraction": round(frac, 4),
                "addon_rate": rate,
            })

        max_rate = max(max_rate, rate)

    addon = base_margin * max_rate
    return round(addon, 2), breaches
