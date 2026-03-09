"""
Scenario generation for stress testing and historical simulation.

Generates shocked market states by applying historical return vectors
or user-defined stress moves to a base market snapshot.
"""

import numpy as np
import pandas as pd
from src import config


def historical_return_scenarios(market_data: pd.DataFrame,
                                 window: int = config.HIST_WINDOW
                                 ) -> pd.DataFrame:
    """
    Pivot market_data into a matrix of daily return vectors.

    Returns DataFrame: rows = dates, columns = risk_factor_id,
    values = return_1d.  Only the last *window* days are kept.
    """
    pivot = market_data.pivot_table(
        index="date", columns="risk_factor_id", values="return_1d"
    ).dropna()
    return pivot.iloc[-window:]


def stressed_return_scenarios(market_data: pd.DataFrame,
                               stressed_window: int = config.STRESSED_WINDOW
                               ) -> pd.DataFrame:
    """
    Select the *stressed_window* consecutive days with the highest
    realised equity-index volatility as the stressed period.
    """
    pivot = market_data.pivot_table(
        index="date", columns="risk_factor_id", values="return_1d"
    ).dropna()

    # Proxy for stress: rolling vol of SPX (or first equity column)
    equity_cols = [c for c in pivot.columns if c in ("SPX", "NDX", "RTY")]
    if not equity_cols:
        equity_cols = [pivot.columns[0]]

    rv = pivot[equity_cols[0]].rolling(stressed_window).std()
    peak_end_idx = rv.values.argmax()
    start_idx = max(peak_end_idx - stressed_window + 1, 0)
    return pivot.iloc[start_idx: peak_end_idx + 1]


def apply_scenario(base_spots: dict, return_vector: pd.Series,
                   horizon: int = 1) -> dict:
    """
    Apply a return scenario to base spots, scaling to *horizon* days
    via sqrt-of-time.

    Parameters
    ----------
    base_spots : {risk_factor_id: spot}
    return_vector : Series indexed by risk_factor_id
    horizon : liquidation horizon in days

    Returns
    -------
    {risk_factor_id: {"spot": shocked_spot, "vol": base_vol_placeholder}}
    """
    shocked = {}
    scale = np.sqrt(horizon)
    for rf, ret in return_vector.items():
        base = base_spots.get(rf)
        if base is None:
            continue
        shocked[rf] = {"spot": base * np.exp(ret * scale), "vol": 0.20}
    return shocked


def generate_stress_scenarios() -> list:
    """Pre-defined named stress scenarios (additive shocks in %)."""
    return [
        {
            "name": "equity_crash",
            "shocks": {"SPX": -0.08, "NDX": -0.10, "RTY": -0.12,
                       "TY": 0.01, "FV": 0.008, "US": 0.015,
                       "VIX": 0.50, "CL": -0.05},
        },
        {
            "name": "rates_spike",
            "shocks": {"SPX": -0.03, "NDX": -0.035, "RTY": -0.04,
                       "TY": -0.025, "FV": -0.018, "US": -0.035,
                       "VIX": 0.15, "CL": -0.02},
        },
        {
            "name": "vol_explosion",
            "shocks": {"SPX": -0.05, "NDX": -0.06, "RTY": -0.07,
                       "TY": 0.005, "FV": 0.004, "US": 0.008,
                       "VIX": 0.80, "CL": -0.03},
        },
        {
            "name": "commodity_shock",
            "shocks": {"SPX": -0.02, "NDX": -0.015, "RTY": -0.025,
                       "TY": 0.003, "FV": 0.002, "US": 0.005,
                       "VIX": 0.10, "CL": 0.15},
        },
    ]
