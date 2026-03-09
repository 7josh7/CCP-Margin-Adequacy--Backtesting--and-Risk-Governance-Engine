"""Quick validation: imports, data files, Streamlit availability."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import config
from src.data_loader import load_synthetic, load_processed, table_exists
from src.portfolio import generate_all
from src.pricing import compute_daily_pnl, price_instrument, _bs_price
from src.scenarios import historical_return_scenarios, stressed_return_scenarios
from src.margin import compute_all_margins, historical_simulation_var
from src.liquidity import compute_liquidity_addon, spread_cost, market_impact
from src.concentration import compute_concentration_addon, concentration_rate
from src.controls import compute_adequacy, coverage_ratio, traffic_light, margin_call_amount
from src.backtesting import compute_exceptions, rolling_exception_count, run_all_data_quality_checks
from src.escalation import generate_escalation_log, evaluate_escalation, detect_consecutive_red
from src.reporting import daily_summary, weekly_exception_report, monthly_committee_pack

print("All 12 source modules imported OK")

import streamlit
print(f"Streamlit version: {streamlit.__version__}")

for t in ["market_data", "instruments", "member_profiles", "positions", "collateral"]:
    assert table_exists(t, "synthetic"), f"Missing synthetic/{t}"
    print(f"  synthetic/{t}.csv  OK")

for t in ["pnl_history", "margin_results", "adequacy", "exceptions",
          "rolling_exceptions", "dq_flags", "escalation_log"]:
    assert table_exists(t, "processed"), f"Missing processed/{t}"
    print(f"  processed/{t}.csv  OK")

from pathlib import Path
rdir = config.REPORTS_DIR
for sub in ["daily", "weekly", "committee_pack"]:
    files = list((rdir / sub).glob("*.md"))
    print(f"  reports/{sub}/: {len(files)} file(s)")
    assert len(files) > 0, f"No reports in {sub}"

# Quick data sanity
adequacy = load_processed("adequacy")
print(f"\nAdequacy sanity:")
print(f"  rows={len(adequacy)}, members={adequacy['member_id'].nunique()}")
print(f"  avg coverage={adequacy['coverage_ratio'].mean():.2%}")
print(f"  traffic lights: {adequacy['traffic_light'].value_counts().to_dict()}")

print("\n=== ALL CHECKS PASSED ===")
