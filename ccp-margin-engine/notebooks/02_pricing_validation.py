# %% [markdown]
# # 02 – Pricing Validation
# Validate the pricing engine against known results and sanity checks.

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.pricing import _bs_price, _bs_delta, price_instrument, compute_daily_pnl
from src.data_loader import load_synthetic

# %% [markdown]
# ## Black-Scholes Sanity Checks

# %%
# Call-Put Parity verification
S, K, T, r, sigma = 4800, 4800, 0.25, 0.045, 0.20
call = _bs_price(S, K, T, r, sigma, "call")
put = _bs_price(S, K, T, r, sigma, "put")
parity_rhs = S - K * np.exp(-r * T)

print(f"Call price:     {call:.4f}")
print(f"Put price:      {put:.4f}")
print(f"C - P:          {call - put:.4f}")
print(f"S - K*e^(-rT):  {parity_rhs:.4f}")
print(f"Parity error:   {abs(call - put - parity_rhs):.2e}")

# %% [markdown]
# ## Option Price Surface

# %%
strikes = np.linspace(4000, 5600, 50)
vols = [0.10, 0.15, 0.20, 0.30, 0.40]

fig = go.Figure()
for v in vols:
    prices = [_bs_price(4800, k, 0.25, 0.045, v, "call") for k in strikes]
    fig.add_trace(go.Scatter(x=strikes, y=prices, name=f"vol={v:.0%}"))
fig.update_layout(title="Call Price vs Strike (varying vol)",
                  xaxis_title="Strike", yaxis_title="Price")
fig.show()

# %% [markdown]
# ## Delta Profile

# %%
fig2 = go.Figure()
for v in vols:
    deltas = [_bs_delta(4800, k, 0.25, 0.045, v, "call") for k in strikes]
    fig2.add_trace(go.Scatter(x=strikes, y=deltas, name=f"vol={v:.0%}"))
fig2.update_layout(title="Call Delta vs Strike", xaxis_title="Strike", yaxis_title="Delta")
fig2.show()

# %% [markdown]
# ## Daily P&L Computation

# %%
md = load_synthetic("market_data")
instruments = load_synthetic("instruments")
positions = load_synthetic("positions")

pnl = compute_daily_pnl(positions, instruments, md)
print(f"P&L records: {len(pnl)}")
pnl.head(20)

# %% [markdown]
# ## P&L Distribution by Member

# %%
import plotly.express as px

fig3 = px.box(pnl, x="member_id", y="pnl_1d", title="Daily P&L Distribution by Member")
fig3.show()

# %% [markdown]
# ## P&L Time Series (selected members)

# %%
sample_members = pnl["member_id"].unique()[:3]
sample = pnl[pnl["member_id"].isin(sample_members)]

fig4 = px.line(sample, x="date", y="pnl_1d", color="member_id",
               title="Daily P&L – Sample Members")
fig4.show()
