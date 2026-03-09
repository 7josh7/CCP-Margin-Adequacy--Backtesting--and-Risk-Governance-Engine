"""
Module A – Data and portfolio generation.

Creates synthetic but realistic market data, instruments, member profiles,
positions, and collateral tables.  All randomness is seeded for
reproducibility.
"""

import numpy as np
import pandas as pd
from typing import Tuple
from src import config


def _business_dates(n_days: int, start: str = "2024-01-02") -> pd.DatetimeIndex:
    """Generate n_days business dates starting from *start*."""
    return pd.bdate_range(start=start, periods=n_days)


# ──────────────────────────────────────────────────────────────────
# Risk factors / market data
# ──────────────────────────────────────────────────────────────────
_RISK_FACTORS = [
    # id, asset_class, initial_spot, annual_vol, bid_ask_bps, adv_lots, liq_bucket
    ("SPX",  "equity_index", 4800.0, 0.18, 1.0, 500_000, "liquid"),
    ("NDX",  "equity_index", 16800.0, 0.22, 1.5, 300_000, "liquid"),
    ("RTY",  "equity_index", 2020.0, 0.24, 3.0, 120_000, "semi_liquid"),
    ("TY",   "rates",        110.0,  0.05, 0.5, 800_000, "liquid"),
    ("FV",   "rates",        107.0,  0.04, 0.5, 600_000, "liquid"),
    ("US",   "rates",        120.0,  0.08, 1.0, 250_000, "semi_liquid"),
    ("VIX",  "volatility",   16.0,   0.90, 5.0, 150_000, "semi_liquid"),
    ("CL",   "commodity",    75.0,   0.35, 2.0, 400_000, "liquid"),
]


def generate_market_data(n_days: int = config.SIMULATION_DAYS,
                         seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = _business_dates(n_days)

    rows = []
    for rf_id, ac, s0, ann_vol, ba, adv, liq in _RISK_FACTORS:
        daily_vol = ann_vol / np.sqrt(252)
        # Generate returns with mild fat tails (t-distribution, df=5)
        raw = rng.standard_t(df=5, size=n_days) * daily_vol
        prices = s0 * np.exp(np.cumsum(raw))
        returns = np.concatenate([[0.0], np.diff(np.log(prices))])

        # Realised vol (20-day rolling, forward-fill first days)
        rv = pd.Series(returns).rolling(20, min_periods=1).std().values * np.sqrt(252)

        for i, d in enumerate(dates):
            rows.append({
                "date": d,
                "risk_factor_id": rf_id,
                "asset_class": ac,
                "spot": round(prices[i], 4),
                "return_1d": round(returns[i], 8),
                "vol": round(rv[i], 6),
                "bid_ask_bps": ba,
                "avg_daily_volume": adv,
                "liquidity_bucket": liq,
            })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# Instruments
# ──────────────────────────────────────────────────────────────────
def generate_instruments() -> pd.DataFrame:
    instruments = [
        # Equity index futures
        ("ES1", "future", "SPX", 50.0,  "2025-03-21", None, None),
        ("NQ1", "future", "NDX", 20.0,  "2025-03-21", None, None),
        ("RTY1","future", "RTY", 50.0,  "2025-03-21", None, None),
        # Rates futures
        ("TY1", "future", "TY",  1000.0,"2025-03-20", None, None),
        ("FV1", "future", "FV",  1000.0,"2025-03-20", None, None),
        ("US1", "future", "US",  1000.0,"2025-06-19", None, None),
        # VIX future
        ("VX1", "future", "VIX", 1000.0,"2025-03-19", None, None),
        # CL future
        ("CL1", "future", "CL",  1000.0,"2025-04-22", None, None),
        # Listed options on SPX
        ("SPX_C4900", "option", "SPX", 100.0, "2025-03-21", 4900.0, "call"),
        ("SPX_P4700", "option", "SPX", 100.0, "2025-03-21", 4700.0, "put"),
        # Listed options on NDX
        ("NDX_C17000","option", "NDX", 20.0,  "2025-03-21", 17000.0,"call"),
        ("NDX_P16500","option", "NDX", 20.0,  "2025-03-21", 16500.0,"put"),
    ]

    return pd.DataFrame(instruments, columns=[
        "instrument_id", "instrument_type", "underlying",
        "contract_multiplier", "expiry", "strike", "option_type"
    ])


# ──────────────────────────────────────────────────────────────────
# Member profiles
# ──────────────────────────────────────────────────────────────────
def generate_member_profiles(n: int = config.NUM_MEMBERS) -> pd.DataFrame:
    # Types assigned to guarantee diversity
    types = (["directional_macro"] * 3
             + ["relative_value"] * 2
             + ["concentrated_vol"]
             + ["diversified"] * 2
             + ["weak_liquidity"]
             + ["directional_macro"])[:n]

    liq_mult = {
        "directional_macro": 1.0,
        "relative_value":    0.8,
        "concentrated_vol":  1.3,
        "diversified":       0.7,
        "weak_liquidity":    1.5,
    }

    rows = []
    for i in range(n):
        mt = types[i]
        rows.append({
            "member_id": f"MBR_{i+1:03d}",
            "member_type": mt,
            "concentration_limit": 0.20,
            "liquidity_multiplier": liq_mult[mt],
            "margin_threshold": config.MARGIN_THRESHOLD,
            "minimum_transfer_amount": config.MINIMUM_TRANSFER_AMOUNT,
            "governance_tier": "tier_1" if mt == "weak_liquidity" else "tier_2",
        })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# Positions  (stochastic but consistent with member type)
# ──────────────────────────────────────────────────────────────────
_MEMBER_STYLE = {
    "directional_macro": {
        "instruments": ["ES1", "TY1", "CL1"],
        "size_range":  (50, 500),
        "sign":        "long_bias",
    },
    "relative_value": {
        "instruments": ["TY1", "FV1", "US1", "ES1", "NQ1"],
        "size_range":  (100, 600),
        "sign":        "mixed",
    },
    "concentrated_vol": {
        "instruments": ["VX1", "SPX_C4900", "SPX_P4700"],
        "size_range":  (200, 1500),
        "sign":        "mixed",
    },
    "diversified": {
        "instruments": ["ES1", "NQ1", "RTY1", "TY1", "FV1", "CL1"],
        "size_range":  (20, 200),
        "sign":        "mixed",
    },
    "weak_liquidity": {
        "instruments": ["RTY1", "US1", "NDX_P16500", "VX1"],
        "size_range":  (300, 1200),
        "sign":        "long_bias",
    },
}


def generate_positions(market_data: pd.DataFrame,
                       instruments: pd.DataFrame,
                       members: pd.DataFrame,
                       seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    dates = sorted(market_data["date"].unique())

    inst_map = instruments.set_index("instrument_id")
    rows = []

    for _, mem in members.iterrows():
        style = _MEMBER_STYLE[mem["member_type"]]
        lo, hi = style["size_range"]

        # Draw base positions once, then let them drift slowly
        base_qty = {}
        for inst in style["instruments"]:
            sign = 1 if style["sign"] == "long_bias" else rng.choice([-1, 1])
            base_qty[inst] = sign * int(rng.integers(lo, hi))

        for d in dates:
            for inst_id, bq in base_qty.items():
                # Small daily perturbation
                qty = bq + int(rng.normal(0, max(abs(bq) * 0.03, 1)))
                if qty == 0:
                    qty = 1 if bq > 0 else -1

                underlying = inst_map.loc[inst_id, "underlying"]
                spot_row = market_data[(market_data["date"] == d) &
                                       (market_data["risk_factor_id"] == underlying)]
                if spot_row.empty:
                    continue
                spot = spot_row["spot"].iloc[0]
                mult = float(inst_map.loc[inst_id, "contract_multiplier"])

                mv = qty * mult * spot
                delta_eq = qty * mult if inst_map.loc[inst_id, "instrument_type"] == "future" else qty * mult * 0.5
                vega_eq = 0.0 if inst_map.loc[inst_id, "instrument_type"] == "future" else abs(qty) * mult * 0.01 * spot

                rows.append({
                    "date": d,
                    "member_id": mem["member_id"],
                    "instrument_id": inst_id,
                    "quantity": qty,
                    "market_value": round(mv, 2),
                    "delta_equiv": round(delta_eq, 2),
                    "vega_equiv": round(vega_eq, 2),
                })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# Collateral
# ──────────────────────────────────────────────────────────────────
def generate_collateral(positions: pd.DataFrame,
                        members: pd.DataFrame,
                        seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    dates = sorted(positions["date"].unique())

    rows = []
    for _, mem in members.iterrows():
        mid = mem["member_id"]
        # Collateral sized relative to gross exposure with some noise
        mem_pos = positions[positions["member_id"] == mid]
        if mem_pos.empty:
            continue
        gross_avg = mem_pos.groupby("date")["market_value"].apply(lambda x: x.abs().sum()).mean()

        # Weak-liquidity members post less collateral (by design)
        margin_factor = 0.06 if mem["member_type"] != "weak_liquidity" else 0.035
        base_coll = gross_avg * margin_factor

        for d in dates:
            cash = base_coll * rng.uniform(0.5, 0.7)
            bond = base_coll * rng.uniform(0.25, 0.45)
            haircut_pct = round(rng.uniform(0.01, 0.05), 4)
            post_haircut = cash + bond * (1 - haircut_pct)
            rows.append({
                "date": d,
                "member_id": mid,
                "cash_collateral": round(cash, 2),
                "gov_bond_collateral": round(bond, 2),
                "haircut_pct": haircut_pct,
                "collateral_value_post_haircut": round(post_haircut, 2),
            })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# All-in-one generator
# ──────────────────────────────────────────────────────────────────
def generate_all(save: bool = True) -> Tuple[pd.DataFrame, ...]:
    """Generate every table.  Returns (market_data, instruments,
    member_profiles, positions, collateral)."""
    from src.data_loader import save_synthetic

    md = generate_market_data()
    inst = generate_instruments()
    mem = generate_member_profiles()
    pos = generate_positions(md, inst, mem)
    coll = generate_collateral(pos, mem)

    if save:
        save_synthetic(md, "market_data")
        save_synthetic(inst, "instruments")
        save_synthetic(mem, "member_profiles")
        save_synthetic(pos, "positions")
        save_synthetic(coll, "collateral")

    return md, inst, mem, pos, coll
