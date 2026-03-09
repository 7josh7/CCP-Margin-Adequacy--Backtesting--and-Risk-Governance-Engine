"""
Module E – Backtesting and model monitoring.

Tracks whether the margin model correctly covers realised losses,
counts exceptions, detects data quality issues, and flags model
stability problems.
"""

import numpy as np
import pandas as pd
from src import config


# ──────────────────────────────────────────────────────────────────
# Backtesting exceptions
# ──────────────────────────────────────────────────────────────────
def compute_exceptions(pnl_history: pd.DataFrame,
                       margin_results: pd.DataFrame) -> pd.DataFrame:
    """
    For each member-day, check whether the realised loss exceeded
    the prior-day margin estimate.

    An exception occurs when: actual_loss > prior_day_margin.
    (loss is the negative of pnl_1d when pnl_1d < 0.)

    Returns DataFrame with:
        date, member_id, pnl_1d, prior_margin, actual_loss,
        is_exception
    """
    # Merge P&L with shifted margin
    margin_shifted = margin_results[["date", "member_id", "required_margin"]].copy()
    margin_shifted["date"] = margin_shifted.groupby("member_id")["date"].shift(-1)
    margin_shifted = margin_shifted.dropna(subset=["date"])
    margin_shifted.rename(columns={"required_margin": "prior_margin"}, inplace=True)

    merged = pnl_history.merge(margin_shifted, on=["date", "member_id"], how="inner")
    merged["actual_loss"] = merged["pnl_1d"].clip(upper=0).abs()
    merged["is_exception"] = merged["actual_loss"] > merged["prior_margin"]

    return merged[["date", "member_id", "pnl_1d", "prior_margin",
                    "actual_loss", "is_exception"]]


def rolling_exception_count(exceptions: pd.DataFrame,
                            window: int = config.BACKTEST_ROLLING_WINDOW
                            ) -> pd.DataFrame:
    """
    Compute rolling exception count per member over *window* days.
    """
    records = []
    for mid, grp in exceptions.groupby("member_id"):
        grp = grp.sort_values("date")
        roll = grp["is_exception"].astype(int).rolling(window, min_periods=1).sum()
        for idx, row in grp.iterrows():
            records.append({
                "date": row["date"],
                "member_id": mid,
                "rolling_exceptions": int(roll.loc[idx]),
            })
    return pd.DataFrame(records)


def exception_status(count: int) -> str:
    if count >= config.BACKTEST_EXCEPTION_CRITICAL:
        return "red"
    if count >= config.BACKTEST_EXCEPTION_WARN:
        return "amber"
    return "green"


# ──────────────────────────────────────────────────────────────────
# Data quality controls
# ──────────────────────────────────────────────────────────────────
def check_stale_data(market_data: pd.DataFrame) -> pd.DataFrame:
    """
    Flag risk factors where the price has not changed for more
    than STALE_DATA_THRESHOLD_DAYS consecutive days.
    """
    flags = []
    for rf, grp in market_data.groupby("risk_factor_id"):
        grp = grp.sort_values("date")
        unchanged = (grp["return_1d"].abs() < 1e-10).astype(int)
        streak = unchanged.groupby((unchanged != unchanged.shift()).cumsum()).cumsum()
        stale_dates = grp.loc[streak >= config.STALE_DATA_THRESHOLD_DAYS, "date"]
        for d in stale_dates:
            flags.append({"date": d, "risk_factor_id": rf,
                          "issue": "stale_data"})
    return pd.DataFrame(flags)


def check_outlier_returns(market_data: pd.DataFrame) -> pd.DataFrame:
    flags = []
    mask = market_data["return_1d"].abs() > config.OUTLIER_RETURN_THRESHOLD
    for _, row in market_data[mask].iterrows():
        flags.append({"date": row["date"],
                       "risk_factor_id": row["risk_factor_id"],
                       "issue": "outlier_return",
                       "value": round(row["return_1d"], 6)})
    return pd.DataFrame(flags)


def check_implausible_vol(market_data: pd.DataFrame) -> pd.DataFrame:
    flags = []
    mask = ((market_data["vol"] < config.MIN_PLAUSIBLE_VOL) |
            (market_data["vol"] > config.MAX_PLAUSIBLE_VOL))
    for _, row in market_data[mask].iterrows():
        flags.append({"date": row["date"],
                       "risk_factor_id": row["risk_factor_id"],
                       "issue": "implausible_vol",
                       "value": round(row["vol"], 6)})
    return pd.DataFrame(flags)


def check_missing_data(market_data: pd.DataFrame) -> pd.DataFrame:
    """Flag dates where a risk factor is completely absent."""
    all_dates = set(market_data["date"].unique())
    all_rfs = set(market_data["risk_factor_id"].unique())
    flags = []
    for rf in all_rfs:
        present = set(market_data[market_data["risk_factor_id"] == rf]["date"])
        for d in all_dates - present:
            flags.append({"date": d, "risk_factor_id": rf,
                          "issue": "missing_data"})
    return pd.DataFrame(flags)


def check_exposure_jumps(positions: pd.DataFrame,
                         threshold: float = 3.0) -> pd.DataFrame:
    """Flag member-instrument pairs where day-over-day market value
    changes by more than *threshold* standard deviations without a
    commensurate market move."""
    flags = []
    for (mid, iid), grp in positions.groupby(["member_id", "instrument_id"]):
        grp = grp.sort_values("date")
        mv = grp["market_value"]
        mv_chg = mv.diff().abs()
        mu = mv_chg.mean()
        sigma = mv_chg.std()
        if sigma == 0 or pd.isna(sigma):
            continue
        outliers = grp[mv_chg > mu + threshold * sigma]
        for _, row in outliers.iterrows():
            flags.append({
                "date": row["date"],
                "member_id": mid,
                "instrument_id": iid,
                "issue": "exposure_jump",
                "value": round(float(mv_chg.loc[row.name]), 2),
            })
    return pd.DataFrame(flags)


def run_all_data_quality_checks(market_data: pd.DataFrame,
                                 positions: pd.DataFrame) -> pd.DataFrame:
    """Run all DQ checks and return a unified flags table."""
    frames = [
        check_stale_data(market_data),
        check_outlier_returns(market_data),
        check_implausible_vol(market_data),
        check_missing_data(market_data),
        check_exposure_jumps(positions),
    ]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["date", "issue"])
    return pd.concat(frames, ignore_index=True)
