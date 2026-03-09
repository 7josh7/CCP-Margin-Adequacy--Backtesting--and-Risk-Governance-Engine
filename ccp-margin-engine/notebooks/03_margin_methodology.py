# %% [markdown]
# # 03 – Margin Methodology
# Demonstrate the full margin calculation pipeline:
# HSVaR → Stressed VaR → Liquidity Add-On → Concentration Add-On → Total Margin

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data_loader import load_synthetic, load_processed, table_exists, save_processed
from src.pricing import compute_daily_pnl
from src.margin import compute_all_margins, historical_simulation_var

# %% [markdown]
# ## Load Data

# %%
md = load_synthetic("market_data")
instruments = load_synthetic("instruments")
members = load_synthetic("member_profiles")
positions = load_synthetic("positions")
collateral = load_synthetic("collateral")

# %% [markdown]
# ## Compute Daily P&L

# %%
if table_exists("pnl_history", "processed"):
    pnl = load_processed("pnl_history")
else:
    pnl = compute_daily_pnl(positions, instruments, md)
    save_processed(pnl, "pnl_history")

print(f"P&L rows: {len(pnl)}")

# %% [markdown]
# ## VaR Example – Single Member

# %%
member_pnl = pnl[pnl["member_id"] == "MBR_001"].set_index("date")["pnl_1d"].tail(500)
var_99 = historical_simulation_var(member_pnl, 0.99)
var_95 = historical_simulation_var(member_pnl, 0.95)

print(f"MBR_001  VaR 99%: ${var_99:,.0f}")
print(f"MBR_001  VaR 95%: ${var_95:,.0f}")

fig = px.histogram(member_pnl, nbins=80, title="MBR_001 – P&L Distribution")
fig.add_vline(x=-var_99, line_dash="dash", line_color="red", annotation_text="VaR 99%")
fig.add_vline(x=-var_95, line_dash="dot", line_color="orange", annotation_text="VaR 95%")
fig.show()

# %% [markdown]
# ## Full Margin Calculation (All Members)

# %%
if table_exists("margin_results", "processed"):
    margins = load_processed("margin_results")
else:
    margins = compute_all_margins(pnl, positions, instruments, md, members)
    save_processed(margins, "margin_results")

print(f"Margin results: {len(margins)} rows")
margins.head(20)

# %% [markdown]
# ## Margin Decomposition – Latest Day

# %%
latest = margins[margins["date"] == margins["date"].max()]

fig2 = go.Figure()
for col, color in [("baseline_margin", "#3498db"), ("liquidity_addon", "#e67e22"),
                    ("concentration_addon", "#e74c3c")]:
    if col in latest.columns:
        fig2.add_trace(go.Bar(x=latest["member_id"], y=latest[col], name=col,
                              marker_color=color))
fig2.update_layout(barmode="stack", title="Margin Decomposition (Latest Day)",
                   yaxis_title="USD")
fig2.show()

# %% [markdown]
# ## Required Margin Time Series

# %%
total_margin = margins.groupby("date")["required_margin"].sum().reset_index()

fig3 = px.line(total_margin, x="date", y="required_margin",
               title="Total Required Margin Over Time")
fig3.show()

# %% [markdown]
# ## Margin by Member Over Time (top 5 by average)

# %%
avg_margin = margins.groupby("member_id")["required_margin"].mean().nlargest(5).index
top5 = margins[margins["member_id"].isin(avg_margin)]

fig4 = px.line(top5, x="date", y="required_margin", color="member_id",
               title="Required Margin – Top 5 Members")
fig4.show()
