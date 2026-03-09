"""Unit tests for the pricing engine."""

import pytest
import numpy as np
import pandas as pd
from src.pricing import _bs_price, _bs_delta, price_instrument, delta_instrument


class TestBlackScholes:
    def test_call_price_nonnegative(self):
        assert _bs_price(100, 100, 0.25, 0.05, 0.20, "call") >= 0

    def test_put_price_nonnegative(self):
        assert _bs_price(100, 100, 0.25, 0.05, 0.20, "put") >= 0

    def test_call_put_parity(self):
        S, K, T, r, sigma = 100, 100, 0.25, 0.05, 0.20
        call = _bs_price(S, K, T, r, sigma, "call")
        put = _bs_price(S, K, T, r, sigma, "put")
        # C - P = S - K * e^(-rT)
        parity = S - K * np.exp(-r * T)
        assert abs(call - put - parity) < 1e-6

    def test_deep_itm_call(self):
        # Deep ITM call ≈ S - K*e^(-rT)
        val = _bs_price(200, 100, 0.25, 0.05, 0.10, "call")
        assert val > 95

    def test_deep_otm_put(self):
        # Deep OTM put should be near zero
        val = _bs_price(200, 100, 0.25, 0.05, 0.10, "put")
        assert val < 1

    def test_call_delta_between_0_and_1(self):
        d = _bs_delta(100, 100, 0.25, 0.05, 0.20, "call")
        assert 0 <= d <= 1

    def test_put_delta_between_neg1_and_0(self):
        d = _bs_delta(100, 100, 0.25, 0.05, 0.20, "put")
        assert -1 <= d <= 0


class TestPriceInstrument:
    def test_future_pv(self):
        inst = pd.Series({
            "instrument_type": "future",
            "contract_multiplier": 50,
            "underlying": "SPX",
            "strike": None,
            "option_type": None,
        })
        pv = price_instrument(inst, 4800, 0.20)
        assert pv == 4800 * 50

    def test_option_pv_nonnegative(self):
        inst = pd.Series({
            "instrument_type": "option",
            "contract_multiplier": 100,
            "underlying": "SPX",
            "strike": 4900,
            "option_type": "call",
        })
        pv = price_instrument(inst, 4800, 0.20)
        assert pv >= 0


class TestHigherVolNoReduceMargin:
    """Scenario sanity: higher vol should not reduce option price
    (holding other inputs constant)."""

    def test_option_price_increases_with_vol(self):
        inst = pd.Series({
            "instrument_type": "option",
            "contract_multiplier": 100,
            "underlying": "SPX",
            "strike": 4800,
            "option_type": "call",
        })
        p_low = price_instrument(inst, 4800, 0.10)
        p_high = price_instrument(inst, 4800, 0.40)
        assert p_high > p_low
