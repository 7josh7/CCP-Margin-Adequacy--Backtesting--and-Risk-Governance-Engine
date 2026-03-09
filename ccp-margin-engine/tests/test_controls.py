"""Unit tests for controls, adequacy, backtesting, and escalation."""

import pytest
import pandas as pd
import numpy as np
from src.controls import (coverage_ratio, traffic_light, margin_call_amount,
                          classify_breaches, buffer)
from src.backtesting import (check_stale_data, check_outlier_returns,
                              check_implausible_vol, exception_status)
from src import config


# ══════════════════════════════════════════════════════════════════
# ADEQUACY / CONTROLS
# ══════════════════════════════════════════════════════════════════

class TestCoverageRatio:
    def test_normal(self):
        assert abs(coverage_ratio(110, 100) - 1.10) < 1e-10

    def test_zero_required_positive_posted(self):
        assert coverage_ratio(100, 0) == float("inf")

    def test_zero_both(self):
        assert coverage_ratio(0, 0) == 1.0

    def test_underfunded(self):
        assert coverage_ratio(80, 100) < 1.0


class TestTrafficLight:
    def test_green(self):
        assert traffic_light(1.15) == "green"

    def test_amber(self):
        assert traffic_light(1.05) == "amber"

    def test_red(self):
        assert traffic_light(0.90) == "red"

    def test_boundary_green(self):
        assert traffic_light(1.10) == "green"

    def test_boundary_amber(self):
        assert traffic_light(1.00) == "amber"


class TestMarginCall:
    def test_no_call_within_threshold(self):
        assert margin_call_amount(90_000, 100_000) == 0.0

    def test_call_above_threshold(self):
        call = margin_call_amount(0, 250_000)
        assert call >= config.MINIMUM_TRANSFER_AMOUNT

    def test_call_respects_min_transfer(self):
        # Shortfall of 150,000 exceeds threshold; call = max(150k, MTA)
        call = margin_call_amount(100_000, 250_000)
        assert call >= config.MINIMUM_TRANSFER_AMOUNT

    def test_no_call_when_overfunded(self):
        assert margin_call_amount(200_000, 100_000) == 0.0


class TestBuffer:
    def test_positive_buffer(self):
        assert buffer(200, 100) == 100

    def test_negative_buffer(self):
        assert buffer(50, 100) == -50


class TestClassifyBreaches:
    def test_margin_insufficiency(self):
        b = classify_breaches(0.90, 0, 0, False, False)
        assert "margin_insufficiency" in b

    def test_backtesting_spike(self):
        b = classify_breaches(1.2, config.BACKTEST_EXCEPTION_WARN, 0, False, False)
        assert "backtesting_exception_spike" in b

    def test_stale_data(self):
        b = classify_breaches(1.2, 0, 0, True, False)
        assert "stale_market_data" in b

    def test_no_breaches(self):
        b = classify_breaches(1.2, 0, 0, False, False)
        assert len(b) == 0


# ══════════════════════════════════════════════════════════════════
# DATA QUALITY CHECKS
# ══════════════════════════════════════════════════════════════════

class TestStaleData:
    def test_detects_stale(self):
        dates = pd.bdate_range("2024-01-02", periods=5)
        md = pd.DataFrame({
            "date": dates,
            "risk_factor_id": "SPX",
            "return_1d": [0.01, 0.0, 0.0, 0.0, 0.02],
            "spot": [100, 100, 100, 100, 102],
            "vol": [0.2]*5,
            "bid_ask_bps": [1]*5,
            "avg_daily_volume": [500000]*5,
            "liquidity_bucket": ["liquid"]*5,
            "asset_class": ["equity_index"]*5,
        })
        flags = check_stale_data(md)
        assert len(flags) >= 1


class TestOutlierReturns:
    def test_flags_large_return(self):
        md = pd.DataFrame({
            "date": pd.bdate_range("2024-01-02", periods=3),
            "risk_factor_id": ["SPX"]*3,
            "return_1d": [0.01, 0.20, -0.02],
            "spot": [100, 120, 117],
            "vol": [0.2]*3,
            "bid_ask_bps": [1]*3,
            "avg_daily_volume": [500000]*3,
            "liquidity_bucket": ["liquid"]*3,
            "asset_class": ["equity_index"]*3,
        })
        flags = check_outlier_returns(md)
        assert len(flags) >= 1


class TestImplausibleVol:
    def test_flags_zero_vol(self):
        md = pd.DataFrame({
            "date": pd.bdate_range("2024-01-02", periods=2),
            "risk_factor_id": ["SPX"]*2,
            "return_1d": [0.01, 0.02],
            "spot": [100, 102],
            "vol": [0.005, 0.20],
            "bid_ask_bps": [1]*2,
            "avg_daily_volume": [500000]*2,
            "liquidity_bucket": ["liquid"]*2,
            "asset_class": ["equity_index"]*2,
        })
        flags = check_implausible_vol(md)
        assert len(flags) >= 1


class TestExceptionStatus:
    def test_green(self):
        assert exception_status(0) == "green"

    def test_amber(self):
        assert exception_status(3) == "amber"

    def test_red(self):
        assert exception_status(5) == "red"


# ══════════════════════════════════════════════════════════════════
# SCENARIO SANITY TESTS
# ══════════════════════════════════════════════════════════════════

class TestScenarioSanity:
    """Ensure higher risk inputs never reduce risk measures."""

    def test_higher_vol_higher_var(self):
        rng = np.random.default_rng(42)
        from src.margin import historical_simulation_var
        low = pd.Series(rng.normal(0, 5, 500))
        high = pd.Series(rng.normal(0, 50, 500))
        assert historical_simulation_var(high) >= historical_simulation_var(low)

    def test_lower_liquidity_higher_scale(self):
        from src.liquidity import liquidation_horizon_scale
        base = 1000
        assert (liquidation_horizon_scale(base, "illiquid") >
                liquidation_horizon_scale(base, "liquid"))
