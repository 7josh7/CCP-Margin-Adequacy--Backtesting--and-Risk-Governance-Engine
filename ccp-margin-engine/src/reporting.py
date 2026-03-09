"""
Module G – Reporting engine.

Generates daily risk summaries, weekly exception reports, and
monthly committee packs suitable for risk committee consumption.

Output formats: in-memory DataFrames (for Streamlit) and
Markdown text (for export).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
from src import config


# ══════════════════════════════════════════════════════════════════
# DAILY SUMMARY
# ══════════════════════════════════════════════════════════════════
def daily_summary(date: pd.Timestamp,
                  adequacy: pd.DataFrame,
                  dq_flags: pd.DataFrame | None = None,
                  escalation_log: pd.DataFrame | None = None) -> dict:
    """
    Build daily risk summary for *date*.
    Returns a dict of sections, each suitable for rendering.
    """
    day = adequacy[adequacy["date"] == date].copy()
    if day.empty:
        return {"error": f"No data for {date}"}

    top5_weak = (day.nsmallest(5, "coverage_ratio")
                 [["member_id", "coverage_ratio", "traffic_light",
                   "required_margin", "posted_margin", "margin_call"]])

    red_amber = day[day["traffic_light"].isin(["red", "amber"])]

    pending_calls = day[day["margin_call"] > 0]

    dq_today = pd.DataFrame()
    if dq_flags is not None and not dq_flags.empty:
        dq_today = dq_flags[dq_flags["date"] == date]

    esc_today = pd.DataFrame()
    if escalation_log is not None and not escalation_log.empty:
        esc_today = escalation_log[escalation_log["date"] == date]

    return {
        "date": date,
        "total_required_margin": round(day["required_margin"].sum(), 2),
        "total_posted_margin": round(day["posted_margin"].sum(), 2),
        "aggregate_coverage": round(
            day["posted_margin"].sum() / max(day["required_margin"].sum(), 1), 4),
        "member_count": len(day),
        "red_count": int((day["traffic_light"] == "red").sum()),
        "amber_count": int((day["traffic_light"] == "amber").sum()),
        "green_count": int((day["traffic_light"] == "green").sum()),
        "top5_weakest": top5_weak.to_dict("records"),
        "new_breaches": red_amber[["member_id", "traffic_light",
                                    "coverage_ratio"]].to_dict("records"),
        "pending_margin_calls": pending_calls[
            ["member_id", "margin_call"]].to_dict("records"),
        "dq_exceptions_count": len(dq_today),
        "escalations_today": esc_today.to_dict("records") if not esc_today.empty else [],
    }


def daily_summary_markdown(summary: dict) -> str:
    """Render daily summary as Markdown text."""
    lines = [
        f"# Daily Risk Summary – {summary['date'].strftime('%Y-%m-%d') if hasattr(summary['date'], 'strftime') else summary['date']}",
        "",
        "## Aggregate",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Required Margin | {summary['total_required_margin']:,.0f} |",
        f"| Total Posted Margin | {summary['total_posted_margin']:,.0f} |",
        f"| Aggregate Coverage | {summary['aggregate_coverage']:.2%} |",
        f"| Members | {summary['member_count']} |",
        f"| Red | {summary['red_count']} | Amber | {summary['amber_count']} | Green | {summary['green_count']} |",
        "",
        "## Top 5 Weakest Coverage",
    ]
    for m in summary["top5_weakest"]:
        lines.append(
            f"- **{m['member_id']}**: coverage={m['coverage_ratio']:.2%}, "
            f"status={m['traffic_light']}, call={m.get('margin_call', 0):,.0f}"
        )
    lines += ["", "## Pending Margin Calls"]
    if summary["pending_margin_calls"]:
        for mc in summary["pending_margin_calls"]:
            lines.append(f"- {mc['member_id']}: {mc['margin_call']:,.0f}")
    else:
        lines.append("- None")

    lines += [
        "",
        f"## Data Quality Exceptions: {summary['dq_exceptions_count']}",
        "",
        f"## Escalations: {len(summary['escalations_today'])}",
    ]
    for e in summary["escalations_today"]:
        lines.append(f"- [{e.get('rule_id','')}] {e.get('trigger','')} → {e.get('action','')}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# WEEKLY EXCEPTION REPORT
# ══════════════════════════════════════════════════════════════════
def weekly_exception_report(end_date: pd.Timestamp,
                            adequacy: pd.DataFrame,
                            exceptions: pd.DataFrame,
                            dq_flags: pd.DataFrame,
                            escalation_log: pd.DataFrame) -> dict:
    start_date = end_date - timedelta(days=7)
    week_ad = adequacy[(adequacy["date"] > start_date) & (adequacy["date"] <= end_date)]
    week_ex = exceptions[(exceptions["date"] > start_date) & (exceptions["date"] <= end_date)]
    week_dq = dq_flags[(dq_flags["date"] > start_date) & (dq_flags["date"] <= end_date)] if not dq_flags.empty else pd.DataFrame()
    week_esc = escalation_log[(escalation_log["date"] > start_date) & (escalation_log["date"] <= end_date)] if not escalation_log.empty else pd.DataFrame()

    bt_count = int(week_ex["is_exception"].sum()) if not week_ex.empty else 0
    conc_breaches = int((week_ad["concentration_addon"] > 0).sum()) if "concentration_addon" in week_ad.columns else 0
    stale_count = int((week_dq["issue"] == "stale_data").sum()) if not week_dq.empty and "issue" in week_dq.columns else 0

    return {
        "period_start": start_date,
        "period_end": end_date,
        "backtesting_exceptions": bt_count,
        "concentration_breaches": conc_breaches,
        "stale_data_incidents": stale_count,
        "escalation_count": len(week_esc),
        "high_severity_escalations": int((week_esc["severity"] == "high").sum()) if not week_esc.empty else 0,
    }


def weekly_report_markdown(report: dict) -> str:
    lines = [
        f"# Weekly Exception Report",
        f"**Period:** {report['period_start']} to {report['period_end']}",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Backtesting Exceptions | {report['backtesting_exceptions']} |",
        f"| Concentration Breaches | {report['concentration_breaches']} |",
        f"| Stale Data Incidents | {report['stale_data_incidents']} |",
        f"| Total Escalations | {report['escalation_count']} |",
        f"| High-Severity Escalations | {report['high_severity_escalations']} |",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# MONTHLY COMMITTEE PACK
# ══════════════════════════════════════════════════════════════════
def monthly_committee_pack(end_date: pd.Timestamp,
                           adequacy: pd.DataFrame,
                           exceptions: pd.DataFrame,
                           dq_flags: pd.DataFrame,
                           escalation_log: pd.DataFrame,
                           members: pd.DataFrame) -> dict:
    start_date = end_date - timedelta(days=30)
    month = adequacy[(adequacy["date"] > start_date) & (adequacy["date"] <= end_date)]
    month_ex = exceptions[(exceptions["date"] > start_date) & (exceptions["date"] <= end_date)]

    # Trend – average required margin per day
    margin_trend = month.groupby("date")["required_margin"].sum().reset_index()

    # Top stressed members (lowest avg coverage)
    member_stats = month.groupby("member_id").agg(
        avg_coverage=("coverage_ratio", "mean"),
        min_coverage=("coverage_ratio", "min"),
        red_days=("traffic_light", lambda x: (x == "red").sum()),
    ).reset_index().sort_values("avg_coverage")

    top_stressed = member_stats.head(5).merge(
        members[["member_id", "member_type"]], on="member_id", how="left")

    # Coverage distribution
    cov_dist = month["coverage_ratio"].describe().to_dict()

    # Backtest summary
    total_exceptions = int(month_ex["is_exception"].sum()) if not month_ex.empty else 0
    exception_by_member = (
        month_ex.groupby("member_id")["is_exception"].sum()
        .reset_index().rename(columns={"is_exception": "exceptions"})
        .sort_values("exceptions", ascending=False)
    ) if not month_ex.empty else pd.DataFrame()

    # Concentration
    conc_month = month[month["concentration_addon"] > 0] if "concentration_addon" in month.columns else pd.DataFrame()

    return {
        "period_start": start_date,
        "period_end": end_date,
        "margin_trend": margin_trend.to_dict("records"),
        "top_stressed_members": top_stressed.to_dict("records"),
        "coverage_distribution": cov_dist,
        "total_backtest_exceptions": total_exceptions,
        "exception_by_member": exception_by_member.to_dict("records") if not exception_by_member.empty else [],
        "concentration_events": len(conc_month),
        "known_limitations": [
            "Stylised margin formula, not a real CCP methodology",
            "Simplified liquidation assumptions",
            "Limited product universe (equity/rates futures, listed options)",
            "Simplified collateral eligibility and haircut structure",
            "No auction/default management simulation",
            "No legal segregation/account structure modelling",
            "Scenario set may omit some cross-asset contagion channels",
        ],
    }


def committee_pack_markdown(pack: dict) -> str:
    lines = [
        "# Monthly Risk Committee Pack",
        f"**Period:** {pack['period_start']} to {pack['period_end']}",
        "",
        "## 1. Margin Trend",
        "*(See attached chart – total required margin by day)*",
        "",
        "## 2. Top Stressed Members",
        "| Member | Type | Avg Coverage | Min Coverage | Red Days |",
        "|--------|------|-------------|-------------|----------|",
    ]
    for m in pack["top_stressed_members"]:
        lines.append(
            f"| {m['member_id']} | {m.get('member_type','')} | "
            f"{m['avg_coverage']:.2%} | {m['min_coverage']:.2%} | "
            f"{m['red_days']} |"
        )

    lines += [
        "",
        "## 3. Coverage Ratio Distribution",
        f"- Mean: {pack['coverage_distribution'].get('mean', 0):.2%}",
        f"- Std: {pack['coverage_distribution'].get('std', 0):.4f}",
        f"- Min: {pack['coverage_distribution'].get('min', 0):.2%}",
        f"- Max: {pack['coverage_distribution'].get('max', 0):.2%}",
        "",
        f"## 4. Backtesting Summary – {pack['total_backtest_exceptions']} exceptions",
    ]
    for m in pack["exception_by_member"][:5]:
        lines.append(f"- {m['member_id']}: {int(m['exceptions'])} exceptions")

    lines += [
        "",
        f"## 5. Concentration Events: {pack['concentration_events']}",
        "",
        "## 6. Known Limitations",
    ]
    for lim in pack["known_limitations"]:
        lines.append(f"- {lim}")

    lines += [
        "",
        "## 7. Recommended Actions",
        "- Review margin call triggers for red-flagged members",
        "- Validate stressed VaR calibration against recent vol regime",
        "- Confirm concentration add-on thresholds remain appropriate",
        "- Investigate any stale data sources flagged in weekly reports",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# File writers
# ──────────────────────────────────────────────────────────────────
def save_report(text: str, folder: str, filename: str) -> Path:
    out_dir = config.REPORTS_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(text, encoding="utf-8")
    return path
