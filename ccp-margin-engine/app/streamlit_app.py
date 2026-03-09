"""
CCP Margin Adequacy, Backtesting, and Risk Governance Engine
Streamlit Dashboard

Run:  streamlit run app/streamlit_app.py    (from project root)
"""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src import config
from src.data_loader import load_synthetic, load_processed, table_exists
from src.portfolio import generate_all
from src.pricing import compute_daily_pnl
from src.margin import compute_all_margins
from src.controls import compute_adequacy
from src.backtesting import (compute_exceptions, rolling_exception_count,
                              run_all_data_quality_checks)
from src.escalation import generate_escalation_log
from src.reporting import (daily_summary, daily_summary_markdown,
                           weekly_exception_report, weekly_report_markdown,
                           monthly_committee_pack, committee_pack_markdown,
                           save_report)

st.set_page_config(page_title="CCP Margin Engine", layout="wide")

# ══════════════════════════════════════════════════════════════════
# DATA LOADING / GENERATION
# ══════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading data…")
def load_or_generate():
    """Load pre-computed results or run the full pipeline."""
    # Step 1: Generate synthetic data if needed
    if not table_exists("market_data"):
        with st.spinner("Generating synthetic data…"):
            generate_all(save=True)

    md = load_synthetic("market_data")
    instruments = load_synthetic("instruments")
    members = load_synthetic("member_profiles")
    positions = load_synthetic("positions")
    collateral = load_synthetic("collateral")

    # Step 2: Compute P&L
    if not table_exists("pnl_history", "processed"):
        with st.spinner("Computing daily P&L (this may take a few minutes)…"):
            pnl = compute_daily_pnl(positions, instruments, md)
            from src.data_loader import save_processed
            save_processed(pnl, "pnl_history")
    pnl = load_processed("pnl_history")

    # Step 3: Margin calculation
    if not table_exists("margin_results", "processed"):
        with st.spinner("Computing margin requirements…"):
            margins = compute_all_margins(pnl, positions, instruments, md, members)
            from src.data_loader import save_processed
            save_processed(margins, "margin_results")
    margins = load_processed("margin_results")

    # Step 4: Adequacy
    if not table_exists("adequacy", "processed"):
        adequacy = compute_adequacy(margins, collateral)
        from src.data_loader import save_processed
        save_processed(adequacy, "adequacy")
    adequacy = load_processed("adequacy")

    # Step 5: Backtesting
    if not table_exists("exceptions", "processed"):
        exc = compute_exceptions(pnl, margins)
        from src.data_loader import save_processed
        save_processed(exc, "exceptions")
    exceptions = load_processed("exceptions")

    if not table_exists("rolling_exceptions", "processed"):
        roll_exc = rolling_exception_count(exceptions)
        from src.data_loader import save_processed
        save_processed(roll_exc, "rolling_exceptions")
    roll_exc = load_processed("rolling_exceptions")

    # Step 6: Data quality
    if not table_exists("dq_flags", "processed"):
        dq = run_all_data_quality_checks(md, positions)
        from src.data_loader import save_processed
        save_processed(dq, "dq_flags")
    dq_flags = load_processed("dq_flags")

    # Step 7: Escalation
    if not table_exists("escalation_log", "processed"):
        esc_log = generate_escalation_log(adequacy, roll_exc, dq_flags)
        from src.data_loader import save_processed
        save_processed(esc_log, "escalation_log")
    esc_log = load_processed("escalation_log")

    return {
        "market_data": md,
        "instruments": instruments,
        "members": members,
        "positions": positions,
        "collateral": collateral,
        "pnl": pnl,
        "margins": margins,
        "adequacy": adequacy,
        "exceptions": exceptions,
        "rolling_exceptions": roll_exc,
        "dq_flags": dq_flags,
        "escalation_log": esc_log,
    }


data = load_or_generate()

adequacy = data["adequacy"]
members = data["members"]
margins = data["margins"]
exceptions = data["exceptions"]
roll_exc = data["rolling_exceptions"]
dq_flags = data["dq_flags"]
esc_log = data["escalation_log"]
pnl = data["pnl"]

dates = sorted(adequacy["date"].unique())
member_ids = sorted(adequacy["member_id"].unique())

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
st.sidebar.title("🏛️ CCP Margin Engine")
st.sidebar.caption("Margin Adequacy, Backtesting & Risk Governance")

selected_date = st.sidebar.select_slider(
    "Select Date", options=dates,
    value=dates[-1] if dates else None,
    format_func=lambda d: str(d)[:10]
)

# ══════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Member Overview",
    "🔍 Margin Decomposition",
    "📈 Backtesting",
    "⚙️ Controls & DQ",
    "📋 Committee Summary",
])

# ── TAB 1: Member Overview ────────────────────────────────────────
with tab1:
    st.header("Member Overview")
    day_data = adequacy[adequacy["date"] == selected_date].copy()

    if day_data.empty:
        st.warning("No data for selected date.")
    else:
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Required Margin", f"${day_data['required_margin'].sum():,.0f}")
        c2.metric("Total Posted Margin", f"${day_data['posted_margin'].sum():,.0f}")
        c3.metric("Red Members", int((day_data["traffic_light"] == "red").sum()))
        c4.metric("Amber Members", int((day_data["traffic_light"] == "amber").sum()))

        # Traffic light table
        display_cols = ["member_id", "required_margin", "posted_margin",
                        "coverage_ratio", "buffer", "traffic_light", "margin_call"]
        avail_cols = [c for c in display_cols if c in day_data.columns]
        st.dataframe(
            day_data[avail_cols].sort_values("coverage_ratio"),
            use_container_width=True,
            hide_index=True,
        )

        # Coverage bar chart
        fig = px.bar(day_data.sort_values("coverage_ratio"),
                     x="member_id", y="coverage_ratio",
                     color="traffic_light",
                     color_discrete_map={"green": "#2ecc71", "amber": "#f39c12", "red": "#e74c3c"},
                     title="Coverage Ratio by Member")
        fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="100%")
        fig.add_hline(y=1.1, line_dash="dot", line_color="orange", annotation_text="110%")
        st.plotly_chart(fig, use_container_width=True)


# ── TAB 2: Margin Decomposition ──────────────────────────────────
with tab2:
    st.header("Margin Decomposition")
    sel_member = st.selectbox("Select Member", member_ids)

    mem_data = adequacy[adequacy["member_id"] == sel_member].sort_values("date")
    mem_margin = margins[margins["member_id"] == sel_member].sort_values("date") if not margins.empty else pd.DataFrame()

    if mem_margin.empty:
        st.info("No margin data for this member yet.")
    else:
        day_margin = mem_margin[mem_margin["date"] == selected_date]
        if not day_margin.empty:
            dm = day_margin.iloc[0]
            cols = st.columns(5)
            cols[0].metric("HS VaR", f"${dm.get('hs_var', 0):,.0f}")
            cols[1].metric("Stressed VaR", f"${dm.get('stressed_var', 0):,.0f}")
            cols[2].metric("Liquidity Add-On", f"${dm.get('liquidity_addon', 0):,.0f}")
            cols[3].metric("Concentration Add-On", f"${dm.get('concentration_addon', 0):,.0f}")
            cols[4].metric("Total Required", f"${dm.get('required_margin', 0):,.0f}")

        # Stacked area of margin components over time
        comp_cols = ["hs_var", "stressed_var", "liquidity_addon", "concentration_addon"]
        avail_comp = [c for c in comp_cols if c in mem_margin.columns]
        if avail_comp:
            fig2 = go.Figure()
            for col in avail_comp:
                fig2.add_trace(go.Scatter(
                    x=mem_margin["date"], y=mem_margin[col],
                    mode="lines", stackgroup="one", name=col
                ))
            fig2.update_layout(title=f"Margin Components – {sel_member}",
                               yaxis_title="USD")
            st.plotly_chart(fig2, use_container_width=True)

        # Posted vs Required over time
        if not mem_data.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=mem_data["date"], y=mem_data["required_margin"],
                                     name="Required", line=dict(color="red")))
            fig3.add_trace(go.Scatter(x=mem_data["date"], y=mem_data["posted_margin"],
                                     name="Posted", line=dict(color="green")))
            fig3.update_layout(title=f"Posted vs Required Margin – {sel_member}",
                               yaxis_title="USD")
            st.plotly_chart(fig3, use_container_width=True)


# ── TAB 3: Backtesting ───────────────────────────────────────────
with tab3:
    st.header("Backtesting & Model Monitoring")

    sel_member_bt = st.selectbox("Select Member", member_ids, key="bt_member")

    mem_exc = exceptions[exceptions["member_id"] == sel_member_bt].sort_values("date") if not exceptions.empty else pd.DataFrame()
    mem_roll = roll_exc[roll_exc["member_id"] == sel_member_bt].sort_values("date") if not roll_exc.empty else pd.DataFrame()

    if not mem_exc.empty:
        # Loss vs Margin time series
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=mem_exc["date"], y=mem_exc["actual_loss"],
                                  name="Actual Loss", line=dict(color="blue")))
        fig4.add_trace(go.Scatter(x=mem_exc["date"], y=mem_exc["prior_margin"],
                                  name="Prior-Day Margin", line=dict(color="red", dash="dash")))
        # Mark exceptions
        exc_pts = mem_exc[mem_exc["is_exception"]]
        fig4.add_trace(go.Scatter(x=exc_pts["date"], y=exc_pts["actual_loss"],
                                  mode="markers", name="Exception",
                                  marker=dict(color="red", size=10, symbol="x")))
        fig4.update_layout(title=f"Backtesting – {sel_member_bt}",
                           yaxis_title="USD")
        st.plotly_chart(fig4, use_container_width=True)

    if not mem_roll.empty:
        fig5 = px.line(mem_roll, x="date", y="rolling_exceptions",
                       title=f"Rolling {config.BACKTEST_ROLLING_WINDOW}-Day Exception Count – {sel_member_bt}")
        fig5.add_hline(y=config.BACKTEST_EXCEPTION_WARN, line_dash="dot", line_color="orange")
        fig5.add_hline(y=config.BACKTEST_EXCEPTION_CRITICAL, line_dash="dash", line_color="red")
        st.plotly_chart(fig5, use_container_width=True)

    # Exception heatmap (all members)
    st.subheader("Exception Heatmap (All Members)")
    if not exceptions.empty:
        heat_data = exceptions.groupby(["member_id", exceptions["date"].dt.to_period("M")])[
            "is_exception"].sum().reset_index()
        heat_data["date"] = heat_data["date"].astype(str)
        heat_pivot = heat_data.pivot(index="member_id", columns="date", values="is_exception").fillna(0)
        fig6 = px.imshow(heat_pivot, aspect="auto",
                         color_continuous_scale="RdYlGn_r",
                         title="Monthly Exception Count by Member")
        st.plotly_chart(fig6, use_container_width=True)


# ── TAB 4: Controls & Data Quality ──────────────────────────────
with tab4:
    st.header("Controls & Data Quality")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Data Quality Flags")
        if dq_flags.empty:
            st.success("No data quality issues detected.")
        else:
            day_dq = dq_flags[dq_flags["date"] == selected_date] if "date" in dq_flags.columns else dq_flags
            if day_dq.empty:
                st.success(f"No DQ issues on {str(selected_date)[:10]}.")
            else:
                st.dataframe(day_dq, use_container_width=True, hide_index=True)

            # Summary by issue type
            if "issue" in dq_flags.columns:
                issue_counts = dq_flags["issue"].value_counts().reset_index()
                issue_counts.columns = ["Issue Type", "Count"]
                st.bar_chart(issue_counts.set_index("Issue Type"))

    with col_b:
        st.subheader("Escalation Log")
        if esc_log.empty:
            st.info("No escalations triggered.")
        else:
            day_esc = esc_log[esc_log["date"] == selected_date] if "date" in esc_log.columns else esc_log
            if day_esc.empty:
                st.info(f"No escalations on {str(selected_date)[:10]}.")
            else:
                st.dataframe(day_esc, use_container_width=True, hide_index=True)

            # Escalation severity breakdown
            sev_counts = esc_log["severity"].value_counts()
            fig7 = px.pie(values=sev_counts.values, names=sev_counts.index,
                          title="Escalation Severity Distribution",
                          color_discrete_map={"high": "#e74c3c", "medium": "#f39c12"})
            st.plotly_chart(fig7, use_container_width=True)


# ── TAB 5: Committee Summary ────────────────────────────────────
with tab5:
    st.header("Committee Summary")

    # Daily summary
    with st.expander("📄 Daily Risk Summary", expanded=True):
        ds = daily_summary(selected_date, adequacy, dq_flags, esc_log)
        if "error" not in ds:
            md_text = daily_summary_markdown(ds)
            st.markdown(md_text)
            if st.button("Export Daily Summary"):
                path = save_report(md_text, "daily",
                                   f"daily_summary_{str(selected_date)[:10]}.md")
                st.success(f"Saved to {path}")

    # Weekly report
    with st.expander("📄 Weekly Exception Report"):
        wr = weekly_exception_report(selected_date, adequacy,
                                      exceptions, dq_flags, esc_log)
        wr_text = weekly_report_markdown(wr)
        st.markdown(wr_text)
        if st.button("Export Weekly Report"):
            path = save_report(wr_text, "weekly",
                               f"weekly_{str(selected_date)[:10]}.md")
            st.success(f"Saved to {path}")

    # Monthly committee pack
    with st.expander("📄 Monthly Committee Pack"):
        cp = monthly_committee_pack(selected_date, adequacy,
                                     exceptions, dq_flags, esc_log, members)
        cp_text = committee_pack_markdown(cp)
        st.markdown(cp_text)

        # Margin trend chart
        if cp["margin_trend"]:
            trend_df = pd.DataFrame(cp["margin_trend"])
            fig8 = px.line(trend_df, x="date", y="required_margin",
                           title="Total Required Margin Trend (30 days)")
            st.plotly_chart(fig8, use_container_width=True)

        if st.button("Export Committee Pack"):
            path = save_report(cp_text, "committee_pack",
                               f"committee_pack_{str(selected_date)[:10]}.md")
            st.success(f"Saved to {path}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    "⚠️ **Disclaimer:** Stylised educational model. "
    "Not a production CCP margin system."
)
st.sidebar.markdown(f"Confidence: {config.CONFIDENCE_LEVEL:.0%} | "
                    f"Window: {config.HIST_WINDOW}d")
