"""
End-to-end pipeline validation script.
Runs every step of the engine and prints summary statistics.
"""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    total_t0 = time.time()

    # ── Step 1: Generate synthetic data ──────────────────────────
    print("=" * 60)
    print("STEP 1: Generating synthetic data")
    print("=" * 60)
    t0 = time.time()
    from src.portfolio import generate_all
    md, instruments, members, positions, collateral = generate_all(save=True)
    print(f"  market_data:     {md.shape}")
    print(f"  instruments:     {instruments.shape}")
    print(f"  member_profiles: {members.shape}")
    print(f"  positions:       {positions.shape}")
    print(f"  collateral:      {collateral.shape}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 2: Compute daily P&L ────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 2: Computing daily P&L")
    print("=" * 60)
    t0 = time.time()
    from src.pricing import compute_daily_pnl
    from src.data_loader import save_processed
    pnl = compute_daily_pnl(positions, instruments, md)
    save_processed(pnl, "pnl_history")
    print(f"  pnl rows:   {len(pnl)}")
    print(f"  members:    {pnl['member_id'].nunique()}")
    print(f"  dates:      {pnl['date'].nunique()}")
    print(f"  date range: {pnl['date'].min().date()} to {pnl['date'].max().date()}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 3: Margin calculation ───────────────────────────────
    print()
    print("=" * 60)
    print("STEP 3: Computing margin requirements")
    print("=" * 60)
    t0 = time.time()
    from src.margin import compute_all_margins
    margins = compute_all_margins(pnl, positions, instruments, md, members)
    save_processed(margins, "margin_results")
    print(f"  margin rows:      {len(margins)}")
    print(f"  avg HS VaR:       ${margins['hs_var'].mean():,.0f}")
    print(f"  avg stressed VaR: ${margins['stressed_var'].mean():,.0f}")
    print(f"  avg liq addon:    ${margins['liquidity_addon'].mean():,.0f}")
    print(f"  avg conc addon:   ${margins['concentration_addon'].mean():,.0f}")
    print(f"  avg total margin: ${margins['required_margin'].mean():,.0f}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 4: Adequacy testing ─────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 4: Computing adequacy (coverage ratios)")
    print("=" * 60)
    t0 = time.time()
    from src.controls import compute_adequacy
    adequacy = compute_adequacy(margins, collateral)
    save_processed(adequacy, "adequacy")
    tl = adequacy["traffic_light"].value_counts()
    print(f"  adequacy rows: {len(adequacy)}")
    print(f"  avg coverage:  {adequacy['coverage_ratio'].mean():.2%}")
    print(f"  min coverage:  {adequacy['coverage_ratio'].min():.2%}")
    print(f"  GREEN: {tl.get('green', 0)}  AMBER: {tl.get('amber', 0)}  RED: {tl.get('red', 0)}")
    calls = adequacy[adequacy["margin_call"] > 0]
    print(f"  margin calls:  {len(calls)} ({calls['margin_call'].sum():,.0f} total)")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 5: Backtesting ──────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 5: Backtesting & data quality checks")
    print("=" * 60)
    t0 = time.time()
    from src.backtesting import (compute_exceptions, rolling_exception_count,
                                  run_all_data_quality_checks)
    exceptions = compute_exceptions(pnl, margins)
    save_processed(exceptions, "exceptions")
    total_exc = int(exceptions["is_exception"].sum())
    print(f"  exception rows:  {len(exceptions)}")
    print(f"  total exceptions:{total_exc}")
    print(f"  exception rate:  {total_exc/max(len(exceptions),1):.2%}")

    roll_exc = rolling_exception_count(exceptions)
    save_processed(roll_exc, "rolling_exceptions")
    print(f"  max rolling exceptions: {roll_exc['rolling_exceptions'].max()}")

    dq_flags = run_all_data_quality_checks(md, positions)
    save_processed(dq_flags, "dq_flags")
    if not dq_flags.empty and "issue" in dq_flags.columns:
        print(f"  DQ flags: {len(dq_flags)}")
        for issue, count in dq_flags["issue"].value_counts().items():
            print(f"    {issue}: {count}")
    else:
        print("  DQ flags: 0")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 6: Escalation ───────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 6: Generating escalation log")
    print("=" * 60)
    t0 = time.time()
    from src.escalation import generate_escalation_log
    esc_log = generate_escalation_log(adequacy, roll_exc, dq_flags)
    save_processed(esc_log, "escalation_log")
    print(f"  escalation events: {len(esc_log)}")
    if not esc_log.empty and "severity" in esc_log.columns:
        for sev, cnt in esc_log["severity"].value_counts().items():
            print(f"    {sev}: {cnt}")
    if not esc_log.empty and "rule_id" in esc_log.columns:
        print("  by rule:")
        for rule, cnt in esc_log["rule_id"].value_counts().items():
            print(f"    {rule}: {cnt}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Step 7: Reporting ────────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 7: Generating reports")
    print("=" * 60)
    t0 = time.time()
    from src.reporting import (daily_summary, daily_summary_markdown,
                               weekly_exception_report, weekly_report_markdown,
                               monthly_committee_pack, committee_pack_markdown,
                               save_report)
    latest = adequacy["date"].max()

    ds = daily_summary(latest, adequacy, dq_flags, esc_log)
    ds_md = daily_summary_markdown(ds)
    p1 = save_report(ds_md, "daily", f"daily_summary_{str(latest)[:10]}.md")
    print(f"  Daily summary saved:   {p1.name}")

    wr = weekly_exception_report(latest, adequacy, exceptions, dq_flags, esc_log)
    wr_md = weekly_report_markdown(wr)
    p2 = save_report(wr_md, "weekly", f"weekly_{str(latest)[:10]}.md")
    print(f"  Weekly report saved:   {p2.name}")

    cp = monthly_committee_pack(latest, adequacy, exceptions, dq_flags, esc_log, members)
    cp_md = committee_pack_markdown(cp)
    p3 = save_report(cp_md, "committee_pack", f"committee_pack_{str(latest)[:10]}.md")
    print(f"  Committee pack saved:  {p3.name}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ── Done ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"ALL STEPS COMPLETED SUCCESSFULLY in {time.time()-total_t0:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
