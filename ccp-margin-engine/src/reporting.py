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


def save_csv_report(df: pd.DataFrame, folder: str, filename: str) -> Path:
    out_dir = config.REPORTS_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path


# ══════════════════════════════════════════════════════════════════
# MEMBER MARGIN ADEQUACY TABLE (CSV)
# ══════════════════════════════════════════════════════════════════
def export_member_margin_adequacy(date: pd.Timestamp,
                                  adequacy: pd.DataFrame) -> pd.DataFrame:
    """
    Extract member-level adequacy table for a given date with all
    columns visible for audit: posted, required, coverage, traffic
    light, margin call details, threshold/MTA flags.
    """
    day = adequacy[adequacy["date"] == date].copy()
    cols = ["date", "member_id", "posted_margin", "required_margin",
            "coverage_ratio", "traffic_light", "margin_call",
            "threshold_breached", "mta_triggered",
            "hsvar_99", "stressed_var_99", "liquidity_addon",
            "concentration_addon", "liquidation_adjusted_loss"]
    return day[[c for c in cols if c in day.columns]]


# ══════════════════════════════════════════════════════════════════
# BREACH REGISTER
# ══════════════════════════════════════════════════════════════════
_BREACH_OWNERS = {
    "margin_insufficiency": "Clearing Risk",
    "backtesting_exception": "Risk Methodology",
    "data_quality": "Risk Control",
    "model_control": "Quant Risk",
    "concentration_breach": "Clearing Risk",
}


def generate_breach_register(date: pd.Timestamp,
                             adequacy: pd.DataFrame,
                             exceptions: pd.DataFrame,
                             dq_flags: pd.DataFrame,
                             escalation_log: pd.DataFrame) -> pd.DataFrame:
    """
    Build a single-date breach register with:
        breach_id, date, member_id, breach_type, severity,
        description, owner, status, escalation_level,
        target_resolution_date
    """
    rows = []
    seq = 1

    # Margin insufficiency breaches
    day_ad = adequacy[adequacy["date"] == date]
    for _, r in day_ad[day_ad["traffic_light"] == "red"].iterrows():
        rows.append({
            "breach_id": f"BRX-{date.strftime('%Y%m%d')}-{seq:04d}",
            "date": date,
            "member_id": r["member_id"],
            "breach_type": "margin_insufficiency",
            "severity": "high",
            "description": f"Coverage ratio {r['coverage_ratio']:.2%} below 1.00 threshold",
            "owner": "Clearing Risk",
            "status": "open",
            "escalation_level": "senior_review",
            "target_resolution_date": date + timedelta(days=1),
        })
        seq += 1

    # Backtesting exception breaches
    day_exc = exceptions[exceptions["date"] == date] if not exceptions.empty else pd.DataFrame()
    for _, r in day_exc[day_exc["is_exception"] == True].iterrows():
        rows.append({
            "breach_id": f"BRX-{date.strftime('%Y%m%d')}-{seq:04d}",
            "date": date,
            "member_id": r["member_id"],
            "breach_type": "backtesting_exception",
            "severity": "medium",
            "description": f"Actual loss ${r['actual_loss']:,.0f} exceeded prior-day margin ${r['prior_margin']:,.0f}",
            "owner": "Risk Methodology",
            "status": "open",
            "escalation_level": "methodology_review" if r["actual_loss"] > r["prior_margin"] * 1.5 else "analyst_review",
            "target_resolution_date": date + timedelta(days=3),
        })
        seq += 1

    # Data quality breaches
    day_dq = dq_flags[dq_flags["date"] == date] if not dq_flags.empty else pd.DataFrame()
    for _, r in day_dq.iterrows():
        issue = r.get("issue", "unknown")
        bt = "model_control" if issue in ("implausible_vol", "exposure_jump") else "data_quality"
        rows.append({
            "breach_id": f"BRX-{date.strftime('%Y%m%d')}-{seq:04d}",
            "date": date,
            "member_id": r.get("member_id", "SYSTEM"),
            "breach_type": bt,
            "severity": "high" if issue in ("implausible_vol", "stale_data") else "medium",
            "description": f"{issue}: {r.get('risk_factor_id', r.get('instrument_id', 'N/A'))}",
            "owner": _BREACH_OWNERS.get(bt, "Risk Control"),
            "status": "open",
            "escalation_level": "analyst_review",
            "target_resolution_date": date + timedelta(days=2),
        })
        seq += 1

    # Concentration breaches
    for _, r in day_ad[day_ad.get("concentration_addon", pd.Series(dtype=float)) > 0].iterrows():
        rows.append({
            "breach_id": f"BRX-{date.strftime('%Y%m%d')}-{seq:04d}",
            "date": date,
            "member_id": r["member_id"],
            "breach_type": "concentration_breach",
            "severity": "medium",
            "description": f"Concentration add-on ${r['concentration_addon']:,.0f} applied",
            "owner": "Clearing Risk",
            "status": "open",
            "escalation_level": "committee_watchlist",
            "target_resolution_date": date + timedelta(days=5),
        })
        seq += 1

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════
# DAILY RISK REVIEW MEMO
# ══════════════════════════════════════════════════════════════════
def daily_risk_review(date: pd.Timestamp,
                      adequacy: pd.DataFrame,
                      exceptions: pd.DataFrame,
                      dq_flags: pd.DataFrame,
                      escalation_log: pd.DataFrame) -> str:
    """
    Generate a concise daily risk review memo suitable for
    morning risk meetings, covering the five key areas:
    top weak members, new breaches, open DQ issues,
    backtesting alerts, and recommended actions.
    """
    day_ad = adequacy[adequacy["date"] == date].copy()
    date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]

    lines = [
        f"# Daily Risk Review – {date_str}",
        "",
        "---",
        "",
    ]

    # 1. Top 5 weakest members by coverage
    lines.append("## 1. Top 5 Weakest Members by Coverage")
    lines.append("")
    if not day_ad.empty:
        top5 = day_ad.nsmallest(5, "coverage_ratio")
        lines.append("| Member | Coverage | Traffic Light | Required Margin | Posted Margin | Margin Call |")
        lines.append("|--------|----------|---------------|-----------------|---------------|-------------|")
        for _, r in top5.iterrows():
            lines.append(
                f"| {r['member_id']} | {r['coverage_ratio']:.2%} | {r['traffic_light'].upper()} "
                f"| {r['required_margin']:,.0f} | {r['posted_margin']:,.0f} "
                f"| {r.get('margin_call', 0):,.0f} |"
            )
    else:
        lines.append("No data available.")
    lines.append("")

    # 2. New red/amber breaches
    lines.append("## 2. New Red / Amber Breaches")
    lines.append("")
    breaches = day_ad[day_ad["traffic_light"].isin(["red", "amber"])]
    if not breaches.empty:
        lines.append(f"- **Red:** {(breaches['traffic_light'] == 'red').sum()} members")
        lines.append(f"- **Amber:** {(breaches['traffic_light'] == 'amber').sum()} members")
        for _, r in breaches[breaches["traffic_light"] == "red"].iterrows():
            lines.append(f"  - {r['member_id']}: coverage {r['coverage_ratio']:.2%}")
    else:
        lines.append("No red or amber breaches today.")
    lines.append("")

    # 3. Open DQ issues
    lines.append("## 3. Open Data Quality Issues")
    lines.append("")
    day_dq = dq_flags[dq_flags["date"] == date] if not dq_flags.empty else pd.DataFrame()
    if not day_dq.empty:
        if "issue" in day_dq.columns:
            for issue, cnt in day_dq["issue"].value_counts().items():
                lines.append(f"- {issue}: {cnt} flag(s)")
        else:
            lines.append(f"- {len(day_dq)} flag(s)")
    else:
        lines.append("No data quality issues today.")
    lines.append("")

    # 4. Backtesting alerts
    lines.append("## 4. Backtesting Alerts")
    lines.append("")
    day_exc = exceptions[exceptions["date"] == date] if not exceptions.empty else pd.DataFrame()
    n_exc = int(day_exc["is_exception"].sum()) if not day_exc.empty else 0
    if n_exc > 0:
        lines.append(f"- **{n_exc} backtesting exception(s)** detected today")
        for _, r in day_exc[day_exc["is_exception"]].iterrows():
            lines.append(f"  - {r['member_id']}: loss ${r['actual_loss']:,.0f} vs margin ${r['prior_margin']:,.0f}")
    else:
        lines.append("No backtesting exceptions today.")
    lines.append("")

    # 5. Recommended actions
    lines.append("## 5. Recommended Actions")
    lines.append("")
    actions = []
    red_count = (day_ad["traffic_light"] == "red").sum() if not day_ad.empty else 0
    if red_count > 0:
        actions.append(f"- Initiate margin calls for {red_count} red-flagged member(s)")
        actions.append("- Convene senior risk review for any members with consecutive red days")
    if n_exc > 0:
        actions.append("- Investigate backtesting exceptions; assess whether model recalibration is warranted")
    if not day_dq.empty:
        actions.append("- Follow up with Market Data team on open DQ flags")
        if "stale_data" in day_dq.get("issue", pd.Series()).values:
            actions.append("- Mark today's run as **provisional** pending stale data resolution")
    if not actions:
        actions.append("- No immediate actions required; continue standard monitoring")
    lines.extend(actions)
    lines.append("")

    # 6. Escalation summary
    lines.append("## 6. Escalation Summary")
    lines.append("")
    day_esc = escalation_log[escalation_log["date"] == date] if not escalation_log.empty else pd.DataFrame()
    if not day_esc.empty:
        lines.append(f"Total escalation events: {len(day_esc)}")
        if "severity" in day_esc.columns:
            for sev, cnt in day_esc["severity"].value_counts().items():
                lines.append(f"- {sev}: {cnt}")
    else:
        lines.append("No escalations triggered today.")
    lines.append("")

    lines += [
        "---",
        "",
        f"*Report generated for {date_str}. This is a stylised educational model.*",
    ]
    return "\n".join(lines)
