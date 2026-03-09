"""
Module F – Governance and escalation engine.

Translates quantitative breach signals into actionable escalation
steps with clear ownership, using a rule-based framework that
mirrors institutional risk governance practice.
"""

import pandas as pd
from src import config


# ──────────────────────────────────────────────────────────────────
# Escalation rules
# ──────────────────────────────────────────────────────────────────
ESCALATION_RULES = [
    {
        "rule_id": "ESC-001",
        "trigger": "Single red breach day",
        "condition": lambda row: row.get("traffic_light") == "red",
        "action": "Analyst review – confirm cause and document",
        "owner": "Risk Analyst",
        "severity": "medium",
    },
    {
        "rule_id": "ESC-002",
        "trigger": "2+ consecutive red days",
        "condition": None,  # evaluated in batch
        "action": "Senior risk officer review – margin call recommendation",
        "owner": "Senior Risk Officer",
        "severity": "high",
    },
    {
        "rule_id": "ESC-003",
        "trigger": ">= 4 backtesting exceptions in rolling window",
        "condition": lambda row: row.get("rolling_exceptions", 0) >= config.ESCALATION_EXCEPTION_METHODOLOGY,
        "action": "Methodology review trigger – model adequacy assessment",
        "owner": "Model Validation",
        "severity": "high",
    },
    {
        "rule_id": "ESC-004",
        "trigger": "Concentration add-on > 25% of total margin",
        "condition": lambda row: (
            row.get("concentration_addon", 0) / max(row.get("required_margin", 1), 1)
            > config.ESCALATION_CONCENTRATION_WATCHLIST
        ),
        "action": "Add member to committee watchlist",
        "owner": "Risk Committee",
        "severity": "high",
    },
    {
        "rule_id": "ESC-005",
        "trigger": "Critical stale market data",
        "condition": lambda row: row.get("has_stale_data", False),
        "action": "Daily run marked provisional – data team notified",
        "owner": "Market Data Team",
        "severity": "medium",
    },
    {
        "rule_id": "ESC-006",
        "trigger": "Margin call above threshold and MTA",
        "condition": lambda row: row.get("margin_call", 0) > 0,
        "action": "Issue margin call to member – operations notified",
        "owner": "Margin Operations",
        "severity": "high",
    },
]


# ──────────────────────────────────────────────────────────────────
# Single-day escalation check
# ──────────────────────────────────────────────────────────────────
def evaluate_escalation(row: dict) -> list[dict]:
    """
    Apply all single-row escalation rules to a member-day record.
    Returns list of triggered escalations.
    """
    triggered = []
    for rule in ESCALATION_RULES:
        if rule["condition"] is not None and rule["condition"](row):
            triggered.append({
                "rule_id": rule["rule_id"],
                "trigger": rule["trigger"],
                "action": rule["action"],
                "owner": rule["owner"],
                "severity": rule["severity"],
            })
    return triggered


# ──────────────────────────────────────────────────────────────────
# Consecutive-red-day detection (ESC-002)
# ──────────────────────────────────────────────────────────────────
def detect_consecutive_red(adequacy: pd.DataFrame,
                           threshold: int = config.ESCALATION_RED_DAYS_SENIOR
                           ) -> pd.DataFrame:
    """
    Find members with *threshold* or more consecutive red days.
    Returns a DataFrame of (member_id, start_date, end_date, red_streak).
    """
    records = []
    for mid, grp in adequacy.groupby("member_id"):
        grp = grp.sort_values("date")
        is_red = (grp["traffic_light"] == "red").astype(int).values
        dates = grp["date"].values

        streak = 0
        start_idx = 0
        for i, v in enumerate(is_red):
            if v:
                if streak == 0:
                    start_idx = i
                streak += 1
            else:
                if streak >= threshold:
                    records.append({
                        "member_id": mid,
                        "start_date": dates[start_idx],
                        "end_date": dates[i - 1],
                        "red_streak": streak,
                    })
                streak = 0
        # Handle streak at end
        if streak >= threshold:
            records.append({
                "member_id": mid,
                "start_date": dates[start_idx],
                "end_date": dates[len(is_red) - 1],
                "red_streak": streak,
            })

    return pd.DataFrame(records)


# ──────────────────────────────────────────────────────────────────
# Batch escalation for all member-days
# ──────────────────────────────────────────────────────────────────
def generate_escalation_log(adequacy: pd.DataFrame,
                            rolling_exceptions: pd.DataFrame | None = None,
                            dq_flags: pd.DataFrame | None = None
                            ) -> pd.DataFrame:
    """
    Build a full escalation log from adequacy results, backtest
    exception counts, and data-quality flags.
    """
    # Merge optional inputs
    merged = adequacy.copy()
    if rolling_exceptions is not None:
        merged = merged.merge(rolling_exceptions, on=["date", "member_id"], how="left")
        merged["rolling_exceptions"] = merged["rolling_exceptions"].fillna(0).astype(int)

    if dq_flags is not None and not dq_flags.empty:
        stale_dates = set()
        if "issue" in dq_flags.columns:
            stale = dq_flags[dq_flags["issue"] == "stale_data"]
            stale_dates = set(stale["date"].unique())
        merged["has_stale_data"] = merged["date"].isin(stale_dates)
    else:
        merged["has_stale_data"] = False

    log_rows = []
    for _, row in merged.iterrows():
        row_dict = row.to_dict()
        triggered = evaluate_escalation(row_dict)
        for esc in triggered:
            log_rows.append({
                "date": row["date"],
                "member_id": row["member_id"],
                **esc,
            })

    # Add ESC-002 (consecutive reds)
    consec = detect_consecutive_red(adequacy)
    for _, cr in consec.iterrows():
        log_rows.append({
            "date": cr["end_date"],
            "member_id": cr["member_id"],
            "rule_id": "ESC-002",
            "trigger": f"{cr['red_streak']} consecutive red days",
            "action": "Senior risk officer review – margin call recommendation",
            "owner": "Senior Risk Officer",
            "severity": "high",
        })

    return pd.DataFrame(log_rows)
