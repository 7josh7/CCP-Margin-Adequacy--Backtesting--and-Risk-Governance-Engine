"""
Configuration parameters for the CCP Margin Engine.

All tuneable constants live here so they can be changed in one place
and referenced throughout the codebase.
"""

from pathlib import Path
import os

# ── Paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
REPORTS_DIR = PROJECT_ROOT / "reports"

for _d in [DATA_RAW, DATA_PROCESSED, DATA_SYNTHETIC,
           REPORTS_DIR / "daily", REPORTS_DIR / "weekly",
           REPORTS_DIR / "committee_pack"]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Risk parameters ───────────────────────────────────────────────
CONFIDENCE_LEVEL = 0.99            # 99 % VaR
HIST_WINDOW = 500                  # rolling historical window (days)
STRESSED_WINDOW = 60               # stressed sub-window (days)
RISK_HORIZON_DEFAULT = 1           # base horizon (days)

# Liquidation-horizon mapping by liquidity bucket
LIQUIDATION_HORIZONS = {
    "liquid":       2,
    "semi_liquid":  3,
    "illiquid":     5,
}

# ── Liquidity add-on ─────────────────────────────────────────────
IMPACT_COEFFICIENT = 0.10          # market-impact coefficient

# ── Concentration add-on (fraction of ADV) ───────────────────────
CONCENTRATION_BANDS = [
    (0.10, 0.00),    # below 10 % ADV: 0 % add-on
    (0.20, 0.10),    # 10–20 % ADV:   10 % add-on
    (float("inf"), 0.25),  # above 20 % ADV:   25 % add-on
]

# ── Adequacy thresholds (traffic-light) ──────────────────────────
GREEN_THRESHOLD = 1.10
AMBER_THRESHOLD = 1.00   # >= 1.00 and < 1.10 = amber; < 1.00 = red

# ── Margin call thresholds ───────────────────────────────────────
MARGIN_THRESHOLD = 100_000         # USD
MINIMUM_TRANSFER_AMOUNT = 100_000  # USD

# ── Backtesting ──────────────────────────────────────────────────
BACKTEST_ROLLING_WINDOW = 250      # trading days
BACKTEST_EXCEPTION_WARN = 3        # amber if exceptions >= this
BACKTEST_EXCEPTION_CRITICAL = 5    # red if exceptions >= this

# ── Escalation triggers ─────────────────────────────────────────
ESCALATION_RED_DAYS_ANALYST = 1
ESCALATION_RED_DAYS_SENIOR = 2
ESCALATION_EXCEPTION_METHODOLOGY = 4
ESCALATION_CONCENTRATION_WATCHLIST = 0.25  # conc add-on > 25 % of total

# ── Simulation parameters ───────────────────────────────────────
NUM_MEMBERS = 10
SIMULATION_DAYS = 504              # ≈ 2 years of trading days
RANDOM_SEED = 42

# ── Option pricing ───────────────────────────────────────────────
RISK_FREE_RATE = 0.045             # 4.5 %

# ── Data quality ─────────────────────────────────────────────────
STALE_DATA_THRESHOLD_DAYS = 2
OUTLIER_RETURN_THRESHOLD = 0.15    # |return| > 15 % flagged
MIN_PLAUSIBLE_VOL = 0.01
MAX_PLAUSIBLE_VOL = 3.00
