"""Tests for the reporting module."""

import pytest
import pandas as pd
import numpy as np
from src.reporting import (daily_summary, weekly_exception_report,
                           daily_summary_markdown, weekly_report_markdown,
                           committee_pack_markdown, monthly_committee_pack)


@pytest.fixture
def sample_adequacy():
    dates = pd.bdate_range("2025-01-02", periods=30)
    members = [f"MBR_{i:03d}" for i in range(1, 6)]
    rows = []
    rng = np.random.default_rng(42)
    for d in dates:
        for m in members:
            req = rng.uniform(50000, 200000)
            posted = rng.uniform(40000, 220000)
            cr = posted / req if req > 0 else 1.0
            tl = "green" if cr >= 1.10 else ("amber" if cr >= 1.0 else "red")
            rows.append({
                "date": d, "member_id": m,
                "required_margin": round(req, 2),
                "posted_margin": round(posted, 2),
                "coverage_ratio": round(cr, 4),
                "buffer": round(posted - req, 2),
                "traffic_light": tl,
                "margin_call": max(req - posted - 100000, 0),
                "concentration_addon": rng.uniform(0, 5000),
            })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_exceptions():
    dates = pd.bdate_range("2025-01-02", periods=30)
    members = [f"MBR_{i:03d}" for i in range(1, 6)]
    rows = []
    rng = np.random.default_rng(42)
    for d in dates:
        for m in members:
            rows.append({
                "date": d, "member_id": m,
                "pnl_1d": rng.normal(0, 50000),
                "prior_margin": rng.uniform(50000, 200000),
                "actual_loss": abs(min(rng.normal(0, 50000), 0)),
                "is_exception": rng.random() < 0.05,
            })
    return pd.DataFrame(rows)


class TestDailySummary:
    def test_returns_dict(self, sample_adequacy):
        d = sample_adequacy["date"].iloc[0]
        result = daily_summary(d, sample_adequacy)
        assert isinstance(result, dict)
        assert "total_required_margin" in result

    def test_markdown_output(self, sample_adequacy):
        d = sample_adequacy["date"].iloc[0]
        result = daily_summary(d, sample_adequacy)
        md = daily_summary_markdown(result)
        assert "Daily Risk Summary" in md

    def test_empty_date(self, sample_adequacy):
        result = daily_summary(pd.Timestamp("2099-01-01"), sample_adequacy)
        assert "error" in result


class TestWeeklyReport:
    def test_returns_dict(self, sample_adequacy, sample_exceptions):
        d = sample_adequacy["date"].iloc[-1]
        dq = pd.DataFrame(columns=["date", "issue"])
        esc = pd.DataFrame(columns=["date", "severity"])
        result = weekly_exception_report(d, sample_adequacy,
                                          sample_exceptions, dq, esc)
        assert "backtesting_exceptions" in result

    def test_markdown_output(self, sample_adequacy, sample_exceptions):
        d = sample_adequacy["date"].iloc[-1]
        dq = pd.DataFrame(columns=["date", "issue"])
        esc = pd.DataFrame(columns=["date", "severity"])
        result = weekly_exception_report(d, sample_adequacy,
                                          sample_exceptions, dq, esc)
        md = weekly_report_markdown(result)
        assert "Weekly Exception Report" in md


class TestCommitteePack:
    def test_returns_dict(self, sample_adequacy, sample_exceptions):
        d = sample_adequacy["date"].iloc[-1]
        dq = pd.DataFrame(columns=["date", "issue"])
        esc = pd.DataFrame(columns=["date", "severity"])
        members = pd.DataFrame({
            "member_id": [f"MBR_{i:03d}" for i in range(1, 6)],
            "member_type": ["directional_macro"]*5,
        })
        result = monthly_committee_pack(d, sample_adequacy,
                                         sample_exceptions, dq, esc, members)
        assert "known_limitations" in result
        assert len(result["known_limitations"]) > 0

    def test_markdown_output(self, sample_adequacy, sample_exceptions):
        d = sample_adequacy["date"].iloc[-1]
        dq = pd.DataFrame(columns=["date", "issue"])
        esc = pd.DataFrame(columns=["date", "severity"])
        members = pd.DataFrame({
            "member_id": [f"MBR_{i:03d}" for i in range(1, 6)],
            "member_type": ["directional_macro"]*5,
        })
        result = monthly_committee_pack(d, sample_adequacy,
                                         sample_exceptions, dq, esc, members)
        md = committee_pack_markdown(result)
        assert "Monthly Risk Committee Pack" in md
        assert "Known Limitations" in md
