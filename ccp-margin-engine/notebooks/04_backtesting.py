# %% [markdown]
# # 04 – Backtesting
# Evaluate margin model performance: exceptions, rolling counts,
# regime analysis, and breach heatmaps.

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src.data_loader import load_synthetic, load_processed, table_exists, save_processed
from src.backtesting import (compute_exceptions, rolling_exception_count,
                              run_all_data_quality_checks, exception_status)
from src.controls import compute_adequacy
from src import config

# %% [markdown]
# ## Load Precomputed Data

# %%
md = load_synthetic("market_data")
positions = load_synthetic("positions")
collateral = load_synthetic("collateral")
pnl = load_processed("pnl_history")
margins = load_processed("margin_results")

# %% [markdown]
# ## Compute Adequacy

# %%
if table_exists("adequacy", "processed"):
    adequacy = load_processed("adequacy")
else:
    adequacy = compute_adequacy(margins, collateral)
    save_processed(adequacy, "adequacy")

print(f"Adequacy rows: {len(adequacy)}")

# %% [markdown]
# ## Compute Backtesting Exceptions

# %%
if table_exists("exceptions", "processed"):
    exceptions = load_processed("exceptions")
else:
    exceptions = compute_exceptions(pnl, margins)
    save_processed(exceptions, "exceptions")

total_exc = exceptions["is_exception"].sum()
print(f"Total exceptions: {total_exc} out of {len(exceptions)} observations")
print(f"Exception rate: {total_exc/len(exceptions):.2%}")

# %% [markdown]
# ## Backtesting – Single Member

# %%
sel = "MBR_006"  # concentrated vol member
mem_exc = exceptions[exceptions["member_id"] == sel].sort_values("date")

fig = go.Figure()
fig.add_trace(go.Scatter(x=mem_exc["date"], y=mem_exc["actual_loss"],
                          name="Actual Loss", line=dict(color="blue")))
fig.add_trace(go.Scatter(x=mem_exc["date"], y=mem_exc["prior_margin"],
                          name="Prior-Day Margin", line=dict(color="red", dash="dash")))
exc_pts = mem_exc[mem_exc["is_exception"]]
fig.add_trace(go.Scatter(x=exc_pts["date"], y=exc_pts["actual_loss"],
                          mode="markers", name="EXCEPTION",
                          marker=dict(color="red", size=12, symbol="x")))
fig.update_layout(title=f"Backtesting: {sel}", yaxis_title="USD")
fig.show()

# %% [markdown]
# ## Rolling Exception Count

# %%
if table_exists("rolling_exceptions", "processed"):
    roll_exc = load_processed("rolling_exceptions")
else:
    roll_exc = rolling_exception_count(exceptions)
    save_processed(roll_exc, "rolling_exceptions")

mem_roll = roll_exc[roll_exc["member_id"] == sel].sort_values("date")
fig2 = px.line(mem_roll, x="date", y="rolling_exceptions",
               title=f"Rolling {config.BACKTEST_ROLLING_WINDOW}-Day Exceptions: {sel}")
fig2.add_hline(y=config.BACKTEST_EXCEPTION_WARN, line_dash="dot", line_color="orange",
               annotation_text="Amber")
fig2.add_hline(y=config.BACKTEST_EXCEPTION_CRITICAL, line_dash="dash", line_color="red",
               annotation_text="Red")
fig2.show()

# %% [markdown]
# ## Exception Heatmap (All Members, Monthly)

# %%
exc_monthly = exceptions.copy()
exc_monthly["month"] = exc_monthly["date"].dt.to_period("M").astype(str)
heat = exc_monthly.groupby(["member_id", "month"])["is_exception"].sum().reset_index()
heat_pivot = heat.pivot(index="member_id", columns="month", values="is_exception").fillna(0)

fig3 = px.imshow(heat_pivot, aspect="auto", color_continuous_scale="RdYlGn_r",
                 title="Monthly Backtesting Exception Count by Member")
fig3.show()

# %% [markdown]
# ## Data Quality Flags

# %%
if table_exists("dq_flags", "processed"):
    dq_flags = load_processed("dq_flags")
else:
    dq_flags = run_all_data_quality_checks(md, positions)
    save_processed(dq_flags, "dq_flags")

if not dq_flags.empty and "issue" in dq_flags.columns:
    print(dq_flags["issue"].value_counts())
else:
    print("No data quality flags raised.")

# %% [markdown]
# ## Coverage Ratio Distribution Over Time

# %%
fig4 = px.box(adequacy, x=adequacy["date"].dt.to_period("M").astype(str),
              y="coverage_ratio", title="Coverage Ratio Distribution by Month")
fig4.add_hline(y=1.0, line_dash="dash", line_color="red")
fig4.add_hline(y=1.1, line_dash="dot", line_color="orange")
fig4.update_layout(xaxis_title="Month")
fig4.show()

# %% [markdown]
# ## Traffic Light Summary Over Time

# %%
tl_counts = adequacy.groupby([adequacy["date"].dt.to_period("W").astype(str),
                               "traffic_light"]).size().reset_index(name="count")
fig5 = px.bar(tl_counts, x="date", y="count", color="traffic_light",
              color_discrete_map={"green": "#2ecc71", "amber": "#f39c12", "red": "#e74c3c"},
              title="Weekly Traffic Light Counts")
fig5.show()
