import json
from pathlib import Path
from textwrap import dedent


OUT_PATH = (
    Path(__file__).resolve().parent
    / "notebooks"
    / "00_project_walkthrough.ipynb"
)


def lines(text: str):
    return dedent(text).strip("\n").splitlines(keepends=True)


def md(text: str):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines(text + "\n"),
    }


def code_lines(text: str):
    raw_lines = dedent(text).strip("\n").splitlines()
    first_nonempty = next((line for line in raw_lines if line.strip()), "")
    base_indent = len(first_nonempty) - len(first_nonempty.lstrip(" "))
    normalized = []
    for line in raw_lines:
        if base_indent and line.startswith(" " * base_indent):
            normalized.append(line[base_indent:])
        else:
            normalized.append(line)
    return [line + "\n" for line in normalized]


def code(text: str):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": code_lines(text),
    }


cells = [
    md(
        """
        # CCP Margin Adequacy, Backtesting, and Risk Governance Engine

        This notebook is a single end-to-end walkthrough of the project. It shows how the engine generates synthetic cleared portfolios, revalues them under historical and stressed conditions, computes liquidation-adjusted margin, and translates quantitative breaches into governance actions and committee-style reports.

        ## What this notebook covers

        - the business question and architecture
        - synthetic market data, instruments, member archetypes, and collateral
        - pricing, historical and stressed scenarios, and margin decomposition
        - adequacy controls, margin calls, backtesting, and data-quality checks
        - escalation logic, reporting outputs, validation, and known limitations
        """
    ),
    md(
        """
        ## Presentation Framing

        A concise way to describe the project in an interview or portfolio review:

        > I built a stylised CCP risk platform that answers whether each clearing member's posted collateral is sufficient to survive liquidation-adjusted losses under historical and stressed conditions. The engine combines full revaluation, liquidity and concentration add-ons, backtesting, operational controls, rule-based escalation, and committee-ready reporting.

        What makes this stronger than a plain VaR demo:

        - margin is decomposed into baseline risk, liquidity cost, and concentration cost
        - adequacy is operationalised with thresholds, traffic lights, and minimum transfer logic
        - governance is explicit through backtesting, DQ checks, escalation ownership, and report generation
        - the full workflow runs offline on synthetic but structured data, so the project is reproducible
        """
    ),
    code(
        """
        from pathlib import Path
        import subprocess
        import sys

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns
        from IPython.display import Markdown, display

        PROJECT_ROOT = Path.cwd().resolve()
        if not (PROJECT_ROOT / "src").exists():
            PROJECT_ROOT = PROJECT_ROOT.parent

        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        from src import config
        from src.backtesting import compute_exceptions, rolling_exception_count, run_all_data_quality_checks
        from src.controls import compute_adequacy
        from src.data_loader import load_processed, load_synthetic, table_exists
        from src.escalation import generate_escalation_log
        from src.margin import compute_all_margins
        from src.portfolio import generate_all
        from src.pricing import compute_daily_pnl, price_instrument
        from src.reporting import (
            committee_pack_markdown,
            daily_risk_review,
            export_member_margin_adequacy,
            generate_breach_register,
            monthly_committee_pack,
        )
        from src.scenarios import historical_return_scenarios, stressed_return_scenarios

        pd.set_option("display.max_columns", 50)
        pd.set_option("display.width", 160)
        pd.options.display.float_format = "{:,.2f}".format

        plt.style.use("seaborn-v0_8-whitegrid")
        sns.set_theme(style="whitegrid", context="talk")
        """
    ),
    md(
        """
        ## Optional Pipeline Refresh

        The next cell will load all synthetic, processed, and reporting outputs. If any required tables are missing, it will run the full pipeline automatically. Set `REFRESH_PIPELINE = True` if you want to regenerate everything from scratch before presenting.
        """
    ),
    code(
        """
        REFRESH_PIPELINE = False

        required_synthetic = [
            "market_data",
            "instruments",
            "member_profiles",
            "positions",
            "collateral",
            "product_universe",
        ]
        required_processed = [
            "pnl_history",
            "margin_results",
            "adequacy",
            "exceptions",
            "rolling_exceptions",
            "dq_flags",
            "escalation_log",
        ]

        missing_synthetic = [name for name in required_synthetic if not table_exists(name, "synthetic")]
        missing_processed = [name for name in required_processed if not table_exists(name, "processed")]

        if REFRESH_PIPELINE or missing_synthetic or missing_processed:
            print("Running end-to-end pipeline...")
            subprocess.run([sys.executable, "run_pipeline.py"], cwd=PROJECT_ROOT, check=True)

        market_data = load_synthetic("market_data")
        instruments = load_synthetic("instruments")
        members = load_synthetic("member_profiles")
        positions = load_synthetic("positions")
        collateral = load_synthetic("collateral")
        product_universe = load_synthetic("product_universe")

        pnl = load_processed("pnl_history")
        margins = load_processed("margin_results")
        adequacy = load_processed("adequacy")
        exceptions = load_processed("exceptions")
        rolling_exceptions = load_processed("rolling_exceptions")
        dq_flags = load_processed("dq_flags")
        escalation_log = load_processed("escalation_log")

        latest_date = pd.Timestamp(adequacy["date"].max())
        latest_date_str = latest_date.strftime("%Y-%m-%d")

        print(f"Project root: {PROJECT_ROOT}")
        print(f"Latest adequacy date: {latest_date_str}")
        print(f"Loaded rows | market_data={len(market_data):,} pnl={len(pnl):,} margins={len(margins):,} adequacy={len(adequacy):,}")
        """
    ),
    md(
        """
        ## 1. Platform Snapshot

        The engine is structured like a production-style CCP monitoring workflow rather than a single analytics script. Synthetic data generation, valuation, margining, controls, escalations, and reporting are separated into modules so the pipeline is explainable and auditable.
        """
    ),
    code(
        """
        snapshot = pd.DataFrame(
            [
                ("Risk factors", market_data["risk_factor_id"].nunique()),
                ("Tradable instruments", instruments["instrument_id"].nunique()),
                ("Clearing members", members["member_id"].nunique()),
                ("Business dates in simulation", market_data["date"].nunique()),
                ("Member-day margin observations", len(margins)),
                ("Latest total required margin", adequacy.loc[adequacy["date"] == latest_date, "required_margin"].sum()),
                ("Latest total posted margin", adequacy.loc[adequacy["date"] == latest_date, "posted_margin"].sum()),
                ("Latest total margin calls", adequacy.loc[adequacy["date"] == latest_date, "margin_call"].sum()),
                ("Backtesting exceptions", int(exceptions["is_exception"].sum())),
                ("Escalation events", len(escalation_log)),
            ],
            columns=["Metric", "Value"],
        )
        display(snapshot)

        architecture = pd.DataFrame(
            [
                ("A. Data & Portfolio", "Synthetic market data, instruments, positions, collateral", "src/portfolio.py, src/data_loader.py"),
                ("B. Pricing & P&L", "Full revaluation for futures and listed options", "src/pricing.py, src/scenarios.py"),
                ("C. Margin Methodology", "HSVaR, stressed VaR, liquidity and concentration add-ons", "src/margin.py, src/liquidity.py, src/concentration.py"),
                ("D. Adequacy Controls", "Coverage ratios, traffic lights, margin-call logic", "src/controls.py"),
                ("E. Monitoring", "Backtesting exceptions and DQ controls", "src/backtesting.py"),
                ("F. Governance", "Rule-based escalation and ownership", "src/escalation.py"),
                ("G. Reporting", "Daily, weekly, and committee-facing artifacts", "src/reporting.py"),
            ],
            columns=["Module", "Purpose", "Key Files"],
        )
        display(architecture)
        """
    ),
    md(
        """
        ## 2. Product Coverage and Synthetic Market Design

        The market-data layer intentionally mixes asset classes and liquidity profiles:

        - equity index futures: ES, NQ, RTY
        - rates futures: TY, FV, US
        - volatility futures: VX
        - commodity futures: CL
        - listed equity-index options: SPX and NDX calls and puts

        Member archetypes are also deliberate. Most members are broadly capitalised, while the `weak_liquidity` archetype is under-collateralised by construction so the governance layer has something real to react to.
        """
    ),
    code(
        """
        risk_factor_summary = (
            market_data.groupby("risk_factor_id")
            .agg(
                asset_class=("asset_class", "last"),
                latest_spot=("spot", "last"),
                latest_vol=("vol", "last"),
                bid_ask_bps=("bid_ask_bps", "last"),
                avg_daily_volume=("avg_daily_volume", "last"),
                liquidity_bucket=("liquidity_bucket", "last"),
            )
            .reset_index()
            .sort_values("asset_class")
        )
        display(risk_factor_summary)

        display(product_universe.sort_values(["asset_class", "instrument_id"]).reset_index(drop=True))

        member_mix = (
            members.groupby(["member_type", "governance_tier"])
            .size()
            .reset_index(name="count")
            .sort_values(["count", "member_type"], ascending=[False, True])
        )
        display(member_mix)
        """
    ),
    code(
        """
        spot_panel = market_data.pivot(index="date", columns="risk_factor_id", values="spot").sort_index()
        normalized_spots = spot_panel.div(spot_panel.iloc[0]).mul(100)

        fig, ax = plt.subplots(figsize=(14, 6))
        normalized_spots.plot(ax=ax, linewidth=2)
        ax.set_title("Normalised Synthetic Spot Paths")
        ax.set_ylabel("Index = 100 at start")
        ax.set_xlabel("")
        ax.legend(title="Risk factor", ncol=4, frameon=True)
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 3. Portfolio Construction and Collateral

        Positions are generated by member style and then allowed to drift day by day. Collateral is posted as cash plus government bonds after haircut. This creates a realistic adequacy question: members can have large directional exposure, heterogeneous liquidity, and collateral that is only loosely proportional to gross exposure.
        """
    ),
    code(
        """
        latest_positions = positions[positions["date"] == latest_date].copy()
        latest_collateral = collateral[collateral["date"] == latest_date].copy()

        member_view = (
            latest_positions.groupby("member_id")
            .agg(
                instruments_held=("instrument_id", "nunique"),
                net_market_value=("market_value", "sum"),
                gross_market_value=("market_value", lambda s: s.abs().sum()),
                gross_delta_equiv=("delta_equiv", lambda s: s.abs().sum()),
                gross_vega_equiv=("vega_equiv", lambda s: s.abs().sum()),
            )
            .reset_index()
            .merge(
                latest_collateral[["member_id", "collateral_value_post_haircut"]],
                on="member_id",
                how="left",
            )
            .merge(
                members[["member_id", "member_type", "governance_tier", "liquidity_multiplier"]],
                on="member_id",
                how="left",
            )
            .sort_values("gross_market_value", ascending=False)
        )
        display(member_view)

        fig, ax = plt.subplots(figsize=(14, 6))
        x = np.arange(len(member_view))
        width = 0.42
        ax.bar(x - width / 2, member_view["gross_market_value"], width=width, label="Gross market value")
        ax.bar(x + width / 2, member_view["collateral_value_post_haircut"], width=width, label="Posted collateral")
        ax.set_xticks(x)
        ax.set_xticklabels(member_view["member_id"], rotation=45)
        ax.set_title("Latest Gross Exposure vs Posted Collateral")
        ax.set_ylabel("USD")
        ax.legend()
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 4. Pricing and Scenario Engine

        Pricing is intentionally simple but defensible:

        - futures are revalued linearly from the underlying spot and contract multiplier
        - listed options are revalued with Black-Scholes under the latest realised volatility
        - historical simulation uses the last 500 business days of return vectors
        - stressed VaR uses the 60-day contiguous window with the highest realised SPX volatility

        That last point matters because it prevents margins from collapsing in calm regimes just because the most recent realised volatility is low.
        """
    ),
    code(
        """
        spx_call = instruments.loc[instruments["instrument_id"] == "SPX_C4900"].iloc[0]
        pricing_demo = pd.DataFrame(
            {
                "spot": [4600, 4800, 5000, 5200],
                "vol": [0.18, 0.18, 0.18, 0.18],
            }
        )
        pricing_demo["per_contract_pv"] = pricing_demo.apply(
            lambda row: price_instrument(spx_call, row["spot"], row["vol"]),
            axis=1,
        )
        display(pricing_demo)

        returns_matrix = historical_return_scenarios(market_data)
        stressed_matrix = stressed_return_scenarios(market_data)

        spx_returns = (
            market_data.loc[market_data["risk_factor_id"] == "SPX", ["date", "return_1d"]]
            .drop_duplicates()
            .sort_values("date")
            .set_index("date")["return_1d"]
        )
        spx_rolling_vol = spx_returns.rolling(config.STRESSED_WINDOW).std() * np.sqrt(252)

        print(f"Historical scenario matrix: {returns_matrix.shape[0]} dates x {returns_matrix.shape[1]} factors")
        print(
            "Stressed window: "
            f"{stressed_matrix.index.min().date()} to {stressed_matrix.index.max().date()} "
            f"({len(stressed_matrix)} business days)"
        )

        fig, ax = plt.subplots(figsize=(14, 5))
        spx_rolling_vol.plot(ax=ax, color="#1f4e79", linewidth=2)
        ax.axvspan(stressed_matrix.index.min(), stressed_matrix.index.max(), color="#f28e2b", alpha=0.25)
        ax.set_title("SPX Rolling Realised Volatility with Selected Stressed Window")
        ax.set_ylabel("Annualised volatility")
        ax.set_xlabel("")
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 5. Margin Methodology

        The core loss measure is:

        $$
        \\text{liquidation-adjusted loss}
        =
        \\max(\\text{HSVaR}_{99}, \\text{Stressed VaR}_{99})
        + \\text{liquidity add-on}
        + \\text{concentration add-on}
        $$

        Interpretation:

        - `HSVaR_99` captures normal historical loss distribution over the last 500 days
        - `Stressed VaR_99` anchors the model to a high-vol regime
        - the liquidity add-on captures spread crossing, market impact, and liquidation horizon scaling
        - the concentration add-on penalises positions that are too large relative to ADV

        This is deliberately framed as a liquidation problem, not just a mark-to-market problem.
        """
    ),
    code(
        """
        latest_margin = margins[margins["date"] == latest_date].copy().sort_values("required_margin", ascending=False)
        display(
            latest_margin[
                [
                    "member_id",
                    "hsvar_99",
                    "stressed_var_99",
                    "liquidity_addon",
                    "concentration_addon",
                    "liquidation_adjusted_loss",
                    "required_margin",
                ]
            ]
        )

        margin_trend = margins.groupby("date")["required_margin"].sum().reset_index()

        fig, axes = plt.subplots(1, 2, figsize=(16, 5))
        axes[0].bar(latest_margin["member_id"], latest_margin["hsvar_99"], label="Baseline VaR")
        axes[0].bar(
            latest_margin["member_id"],
            latest_margin["liquidity_addon"],
            bottom=latest_margin["hsvar_99"],
            label="Liquidity add-on",
        )
        axes[0].bar(
            latest_margin["member_id"],
            latest_margin["concentration_addon"],
            bottom=latest_margin["hsvar_99"] + latest_margin["liquidity_addon"],
            label="Concentration add-on",
        )
        axes[0].set_title("Latest Margin Decomposition by Member")
        axes[0].set_ylabel("USD")
        axes[0].tick_params(axis="x", rotation=45)
        axes[0].legend()

        axes[1].plot(margin_trend["date"], margin_trend["required_margin"], color="#0b6e4f", linewidth=2.5)
        axes[1].set_title("Total Required Margin Over Time")
        axes[1].set_ylabel("USD")
        axes[1].set_xlabel("")

        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 6. Adequacy Controls and Margin Calls

        Required margin by itself is not enough. The controls layer converts model output into operational actions.

        - `coverage_ratio = posted_margin / required_margin`
        - `green` if coverage is at least 1.10
        - `amber` if coverage is at least 1.00 but below 1.10
        - `red` if coverage is below 1.00
        - margin calls only trigger when the shortfall exceeds both the threshold and the minimum transfer amount

        That is the bridge between quantitative risk and actual collateral operations.
        """
    ),
    code(
        """
        latest_adequacy = adequacy[adequacy["date"] == latest_date].copy().sort_values("coverage_ratio")

        traffic_order = ["red", "amber", "green"]
        traffic_counts = (
            latest_adequacy["traffic_light"].value_counts().reindex(traffic_order).fillna(0).astype(int)
        )
        adequacy_summary = pd.DataFrame(
            [
                ("Latest date", latest_date_str),
                ("Aggregate coverage", latest_adequacy["posted_margin"].sum() / latest_adequacy["required_margin"].sum()),
                ("Red members", traffic_counts["red"]),
                ("Amber members", traffic_counts["amber"]),
                ("Green members", traffic_counts["green"]),
                ("Triggered margin calls", int((latest_adequacy["margin_call"] > 0).sum())),
                ("Margin call amount", latest_adequacy["margin_call"].sum()),
            ],
            columns=["Metric", "Value"],
        )
        display(adequacy_summary)

        display(
            latest_adequacy[
                [
                    "member_id",
                    "posted_margin",
                    "required_margin",
                    "coverage_ratio",
                    "traffic_light",
                    "margin_call",
                    "threshold_breached",
                    "mta_triggered",
                ]
            ]
        )

        color_map = {"green": "#2ca02c", "amber": "#ffbf00", "red": "#d62728"}
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.bar(
            latest_adequacy["member_id"],
            latest_adequacy["coverage_ratio"],
            color=latest_adequacy["traffic_light"].map(color_map).fillna("#7f7f7f"),
        )
        ax.axhline(1.00, color="#d62728", linestyle="--", linewidth=2, label="Red threshold")
        ax.axhline(1.10, color="#ffbf00", linestyle=":", linewidth=2, label="Green threshold")
        ax.set_title("Coverage Ratio by Member on Latest Date")
        ax.set_ylabel("Coverage ratio")
        ax.set_xlabel("")
        ax.legend()
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 7. Backtesting and Model Controls

        The backtesting layer asks a simple governance question: did realised losses exceed prior-day margin? That creates exception tracking, rolling counts, and methodology-review triggers.

        Separately, the DQ layer monitors stale data, extreme returns, implausible volatilities, missing data, and exposure jumps. A real risk engine needs both model-performance evidence and operational-quality evidence.
        """
    ),
    code(
        """
        exception_rows = exceptions[exceptions["is_exception"]].copy()
        focus_member = (
            exception_rows.sort_values("actual_loss", ascending=False)["member_id"].iloc[0]
            if not exception_rows.empty
            else exceptions["member_id"].iloc[0]
        )

        exception_summary = pd.DataFrame(
            [
                ("Backtesting observations", len(exceptions)),
                ("Exceptions", int(exceptions["is_exception"].sum())),
                ("Exception rate", exceptions["is_exception"].mean()),
                ("Max rolling exceptions", rolling_exceptions["rolling_exceptions"].max()),
                ("Members with any exception", exception_rows["member_id"].nunique()),
            ],
            columns=["Metric", "Value"],
        )
        display(exception_summary)

        dq_issue_counts = (
            dq_flags["issue"].value_counts().rename_axis("issue").reset_index(name="count")
            if not dq_flags.empty and "issue" in dq_flags.columns
            else pd.DataFrame(columns=["issue", "count"])
        )
        display(dq_issue_counts if not dq_issue_counts.empty else pd.DataFrame({"message": ["No DQ issues flagged"]}))

        member_bt = exceptions[exceptions["member_id"] == focus_member].sort_values("date")
        member_roll = rolling_exceptions[rolling_exceptions["member_id"] == focus_member].sort_values("date")

        fig, axes = plt.subplots(1, 2, figsize=(16, 5))
        axes[0].plot(member_bt["date"], member_bt["actual_loss"], label="Actual loss", linewidth=2.2)
        axes[0].plot(member_bt["date"], member_bt["prior_margin"], label="Prior-day margin", linewidth=2.2)
        if member_bt["is_exception"].any():
            exc_points = member_bt[member_bt["is_exception"]]
            axes[0].scatter(exc_points["date"], exc_points["actual_loss"], color="#d62728", s=90, label="Exception")
        axes[0].set_title(f"Backtesting for {focus_member}")
        axes[0].set_ylabel("USD")
        axes[0].legend()

        axes[1].plot(member_roll["date"], member_roll["rolling_exceptions"], color="#1f77b4", linewidth=2.2)
        axes[1].axhline(config.BACKTEST_EXCEPTION_WARN, color="#ffbf00", linestyle=":", linewidth=2, label="Warn")
        axes[1].axhline(config.BACKTEST_EXCEPTION_CRITICAL, color="#d62728", linestyle="--", linewidth=2, label="Critical")
        axes[1].set_title(f"Rolling Exceptions for {focus_member}")
        axes[1].set_ylabel("Count")
        axes[1].legend()

        plt.tight_layout()
        plt.show()

        display(exception_rows.sort_values("actual_loss", ascending=False).reset_index(drop=True))
        """
    ),
    md(
        """
        ## 8. Governance, Escalation, and Reporting

        The escalation engine converts signals into actions with explicit ownership.

        Typical triggers include:

        - a red adequacy breach
        - consecutive red days
        - a material margin call
        - concentration add-ons above the watchlist threshold
        - stale-data conditions that require a provisional run

        The reporting layer then packages those outcomes into daily review notes, breach registers, weekly exception summaries, and monthly committee packs.
        """
    ),
    code(
        """
        escalation_summary = (
            escalation_log.groupby(["rule_id", "owner", "severity"])
            .size()
            .reset_index(name="count")
            .sort_values(["count", "rule_id"], ascending=[False, True])
        )
        display(escalation_summary)

        latest_member_adequacy = export_member_margin_adequacy(latest_date, adequacy)
        latest_breach_register = generate_breach_register(latest_date, adequacy, exceptions, dq_flags, escalation_log)
        display(latest_member_adequacy)
        display(latest_breach_register)

        committee_pack = monthly_committee_pack(
            latest_date,
            adequacy,
            exceptions,
            dq_flags,
            escalation_log,
            members,
        )
        daily_review_text = daily_risk_review(latest_date, adequacy, exceptions, dq_flags, escalation_log)
        committee_pack_text = committee_pack_markdown(committee_pack)

        display(Markdown("### Daily Risk Review Excerpt"))
        display(Markdown("\\n".join(daily_review_text.splitlines()[:30])))

        display(Markdown("### Committee Pack Excerpt"))
        display(Markdown("\\n".join(committee_pack_text.splitlines()[:24])))

        report_inventory = pd.DataFrame(
            [
                ("Daily review memo", "reports/daily/daily_risk_review_*.md"),
                ("Daily adequacy export", "reports/daily/member_margin_adequacy_*.csv"),
                ("Daily breach register", "reports/daily/breach_register_*.csv"),
                ("Weekly exception report", "reports/weekly/weekly_*.md"),
                ("Monthly committee pack", "reports/committee_pack/committee_pack_*.md"),
                ("Interactive dashboard", "app/streamlit_app.py"),
            ],
            columns=["Artifact", "Location"],
        )
        display(report_inventory)
        """
    ),
    md(
        """
        ## 9. Validation, Limitations, and Next Extensions

        The repository already contains automated tests and validation scripts. That matters because a project with governance ambitions should prove not only that it computes numbers, but also that its controls and report outputs are stable.
        """
    ),
    code(
        """
        validation_inventory = pd.DataFrame(
            [
                ("validate.py", "Imports, data files, processed tables, reports, quick sanity checks"),
                ("validate_app.py", "AST and compile validation for the Streamlit app"),
                ("tests/test_pricing.py", "Black-Scholes sanity, parity, delta bounds"),
                ("tests/test_margin.py", "VaR and add-on behaviour"),
                ("tests/test_controls.py", "Coverage ratio, traffic lights, margin calls, controls"),
                ("tests/test_reporting.py", "Daily, weekly, committee, and breach-register outputs"),
            ],
            columns=["Validation Artifact", "What it Covers"],
        )
        display(validation_inventory)

        limitations = pd.DataFrame(
            {
                "Known limitation": [
                    "Stylised educational margin methodology, not a production CCP model",
                    "Simplified liquidation assumptions and no auction default-management process",
                    "Limited product universe and simplified collateral eligibility",
                    "No member default probability or credit migration modelling",
                    "Static implied-vol treatment for listed options",
                    "Scenario design may miss some cross-asset contagion channels",
                ]
            }
        )
        display(limitations)

        RUN_VALIDATION = False
        if RUN_VALIDATION:
            subprocess.run([sys.executable, "validate.py"], cwd=PROJECT_ROOT, check=True)
            subprocess.run([sys.executable, "validate_app.py"], cwd=PROJECT_ROOT, check=True)
            subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=PROJECT_ROOT, check=True)
        """
    ),
    md(
        """
        ## Closing Talk Track

        If you need a short close:

        1. The project asks a practical CCP question: is posted collateral sufficient after accounting for liquidation reality, not just statistical VaR?
        2. The answer is built from a full workflow: synthetic market and portfolio generation, full revaluation, baseline and stressed VaR, liquidity and concentration add-ons, adequacy controls, backtesting, and escalation.
        3. The strongest portfolio angle is governance. The engine does not stop at numbers; it produces actionable calls, breach tracking, and committee-facing reporting.
        4. The main next step toward production realism would be richer scenario design, more realistic collateral policy, and default-management mechanics.
        """
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


OUT_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print(f"Wrote notebook to {OUT_PATH}")
