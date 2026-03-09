"""Unit and sanity tests for the margin methodology."""

import pytest
import numpy as np
import pandas as pd
from src.margin import historical_simulation_var
from src.liquidity import spread_cost, market_impact, liquidation_horizon_scale
from src.concentration import concentration_rate, _adv_fraction


# ══════════════════════════════════════════════════════════════════
# MARGIN TESTS
# ══════════════════════════════════════════════════════════════════

class TestHistoricalSimulationVaR:
    def test_var_is_nonnegative(self):
        pnl = pd.Series(np.random.default_rng(42).normal(0, 100, 500))
        var = historical_simulation_var(pnl)
        assert var >= 0.0

    def test_var_increases_with_volatility(self):
        rng = np.random.default_rng(42)
        low_vol = pd.Series(rng.normal(0, 10, 500))
        high_vol = pd.Series(rng.normal(0, 100, 500))
        assert historical_simulation_var(high_vol) > historical_simulation_var(low_vol)

    def test_empty_series_returns_zero(self):
        assert historical_simulation_var(pd.Series(dtype=float)) == 0.0

    def test_all_positive_pnl_returns_zero(self):
        pnl = pd.Series([10, 20, 30, 40, 50] * 50)
        assert historical_simulation_var(pnl, confidence=0.99) == 0.0


# ══════════════════════════════════════════════════════════════════
# LIQUIDITY TESTS
# ══════════════════════════════════════════════════════════════════

class TestLiquidity:
    def test_spread_cost_nonnegative(self):
        assert spread_cost(100, 4800, 1.0, 50) >= 0

    def test_spread_cost_increases_with_quantity(self):
        c1 = spread_cost(100, 4800, 1.0, 50)
        c2 = spread_cost(500, 4800, 1.0, 50)
        assert c2 > c1

    def test_market_impact_nonnegative(self):
        assert market_impact(100, 4800, 500000, 50) >= 0

    def test_market_impact_increases_with_size(self):
        i1 = market_impact(100, 4800, 500000, 50)
        i2 = market_impact(1000, 4800, 500000, 50)
        assert i2 > i1

    def test_market_impact_zero_adv(self):
        assert market_impact(100, 4800, 0, 50) == 0.0

    def test_liquidation_horizon_scale_increases(self):
        base = 1000.0
        s_liq = liquidation_horizon_scale(base, "liquid")
        s_semi = liquidation_horizon_scale(base, "semi_liquid")
        s_ill = liquidation_horizon_scale(base, "illiquid")
        assert s_liq < s_semi < s_ill


# ══════════════════════════════════════════════════════════════════
# CONCENTRATION TESTS
# ══════════════════════════════════════════════════════════════════

class TestConcentration:
    def test_monotonically_increasing(self):
        r1 = concentration_rate(0.05)   # < 10 %
        r2 = concentration_rate(0.15)   # 10–20 %
        r3 = concentration_rate(0.25)   # > 20 %
        assert r1 <= r2 <= r3

    def test_below_first_band_is_zero(self):
        assert concentration_rate(0.05) == 0.0

    def test_above_highest_band(self):
        assert concentration_rate(0.5) == 0.25

    def test_adv_fraction_zero_adv(self):
        assert _adv_fraction(100, 0) == 0.0

    def test_adv_fraction_correct(self):
        assert abs(_adv_fraction(100, 1000) - 0.10) < 1e-10
