# %% [markdown]
# # 01 – Data Generation
# Generate all synthetic data tables for the CCP Margin Engine.

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src.portfolio import generate_all
from src.data_loader import load_synthetic

# %% [markdown]
# ## Generate All Tables

# %%
md, instruments, members, positions, collateral = generate_all(save=True)

print(f"Market data:   {md.shape}")
print(f"Instruments:   {instruments.shape}")
print(f"Members:       {members.shape}")
print(f"Positions:     {positions.shape}")
print(f"Collateral:    {collateral.shape}")

# %% [markdown]
# ## Market Data Sample

# %%
md.head(20)

# %%
md.groupby("risk_factor_id")["spot"].describe()

# %% [markdown]
# ## Instruments

# %%
instruments

# %% [markdown]
# ## Member Profiles

# %%
members

# %% [markdown]
# ## Position Statistics

# %%
pos_stats = positions.groupby("member_id").agg(
    n_instruments=("instrument_id", "nunique"),
    total_market_value=("market_value", "sum"),
    abs_market_value=("market_value", lambda x: x.abs().sum()),
)
pos_stats

# %% [markdown]
# ## Collateral Summary

# %%
coll_stats = collateral.groupby("member_id").agg(
    avg_posted=("collateral_value_post_haircut", "mean"),
    avg_cash=("cash_collateral", "mean"),
    avg_bond=("gov_bond_collateral", "mean"),
    avg_haircut=("haircut_pct", "mean"),
)
coll_stats

# %% [markdown]
# ## Market Data – Spot Price Evolution

# %%
import plotly.express as px

pivot = md.pivot_table(index="date", columns="risk_factor_id", values="spot")
fig = px.line(pivot, title="Spot Prices (Synthetic)")
fig.show()

# %% [markdown]
# ## Return Distributions

# %%
import plotly.express as px

fig = px.histogram(md, x="return_1d", color="risk_factor_id", nbins=100,
                   title="Return Distributions by Risk Factor", barmode="overlay",
                   opacity=0.5)
fig.show()
