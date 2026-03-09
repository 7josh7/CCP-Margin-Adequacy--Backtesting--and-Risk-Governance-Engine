# %% [markdown]
# # 05 – Reporting Examples
# Generate and display the three report types: Daily Summary, Weekly
# Exception Report, and Monthly Committee Pack.

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import pandas as pd
from src.data_loader import load_synthetic, load_processed, table_exists
from src.reporting import (daily_summary, daily_summary_markdown,
                           weekly_exception_report, weekly_report_markdown,
                           monthly_committee_pack, committee_pack_markdown,
                           save_report)
from src.escalation import generate_escalation_log

# %% [markdown]
# ## Load Data

# %%
members = load_synthetic("member_profiles")
adequacy = load_processed("adequacy")
exceptions = load_processed("exceptions")
roll_exc = load_processed("rolling_exceptions")
dq_flags = load_processed("dq_flags") if table_exists("dq_flags", "processed") else pd.DataFrame()
esc_log = load_processed("escalation_log") if table_exists("escalation_log", "processed") else pd.DataFrame()

# If escalation log doesn't exist, compute it
if esc_log.empty:
    esc_log = generate_escalation_log(adequacy, roll_exc, dq_flags)

dates = sorted(adequacy["date"].unique())
latest_date = dates[-1]

print(f"Latest date: {latest_date}")
print(f"Date range: {dates[0]} to {dates[-1]}")

# %% [markdown]
# ## Daily Risk Summary

# %%
ds = daily_summary(latest_date, adequacy, dq_flags, esc_log)
md_text = daily_summary_markdown(ds)
print(md_text)

# %%
# Export
path = save_report(md_text, "daily", f"daily_summary_{str(latest_date)[:10]}.md")
print(f"Saved: {path}")

# %% [markdown]
# ## Weekly Exception Report

# %%
wr = weekly_exception_report(latest_date, adequacy, exceptions, dq_flags, esc_log)
wr_text = weekly_report_markdown(wr)
print(wr_text)

# %%
path = save_report(wr_text, "weekly", f"weekly_report_{str(latest_date)[:10]}.md")
print(f"Saved: {path}")

# %% [markdown]
# ## Monthly Committee Pack

# %%
cp = monthly_committee_pack(latest_date, adequacy, exceptions, dq_flags, esc_log, members)
cp_text = committee_pack_markdown(cp)
print(cp_text)

# %%
path = save_report(cp_text, "committee_pack", f"committee_pack_{str(latest_date)[:10]}.md")
print(f"Saved: {path}")

# %% [markdown]
# ## Escalation Log Summary

# %%
if not esc_log.empty:
    print(f"Total escalations: {len(esc_log)}")
    if "severity" in esc_log.columns:
        print("\nBy severity:")
        print(esc_log["severity"].value_counts())
    if "rule_id" in esc_log.columns:
        print("\nBy rule:")
        print(esc_log["rule_id"].value_counts())
else:
    print("No escalations triggered.")

# %% [markdown]
# ## Margin Trend Chart (for Committee Pack)

# %%
import plotly.express as px

if cp["margin_trend"]:
    trend_df = pd.DataFrame(cp["margin_trend"])
    fig = px.line(trend_df, x="date", y="required_margin",
                  title="Total Required Margin – Last 30 Days")
    fig.show()

# %% [markdown]
# ## Top Stressed Members

# %%
pd.DataFrame(cp["top_stressed_members"])
