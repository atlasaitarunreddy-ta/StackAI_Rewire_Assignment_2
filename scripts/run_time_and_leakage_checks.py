#!/usr/bin/env python3
"""
Runner: time trend, multi-source agreement, leakage checks.
"""

from eda.load import load_transactions, load_monthly_agg, load_customers
from eda.time_checks import monthly_volume_trend, trend_direction, multi_source_agreement
from eda.leakage_checks import get_as_of_date, flag_leakage_tainted_variables, check_no_future_data_used
from pathlib import Path
import json

DATA_DIR = Path("data")

if __name__ == "__main__":
    txns = load_transactions(DATA_DIR / "transactions.db")
    parquet = load_monthly_agg(DATA_DIR / "transactions_monthly_agg.parquet")

    print("=" * 60)
    print("TIME TREND — MONTHLY VOLUME")
    print("=" * 60)
    monthly = monthly_volume_trend(txns)
    td = trend_direction(monthly)
    print(f"  Period: {td['first_month']} to {td['last_month']} ({td['months_covered']} months)")
    print(f"  Txn count:  {td['first_txn_count']} -> {td['last_txn_count']}  (~{td['growth_factor_txns']}x)")
    print(f"  Total amt:  ${td['first_total_amount']:.2f} -> ${td['last_total_amount']:.2f}")
    print(f"  Customers:  {td['first_unique_customers']} -> {td['last_unique_customers']}")
    print(f"  Direction:  {td['trend_direction']}")

    # Print all months
    print("\n  Month-by-month:")
    for _, r in monthly.iterrows():
        print(f"    {r['txn_month'].strftime('%Y-%m')}: {r['txn_count']:>5} txns  ${r['total_amount']:>8.0f}  {r['unique_customers']:>4} cust")

    print("\n" + "=" * 60)
    print("MULTI-SOURCE AGREEMENT")
    print("=" * 60)
    ms = multi_source_agreement(txns, parquet)
    print(f"  Months compared: {ms['total_months']}")
    print(f"  Exact match:     {ms['match_count']}")
    print(f"  Diverged:        {ms['diverged_count']}")
    for d in ms['diverged_months']:
        print(f"\n  --- {d['month']} ---")
        print(f"    Row-level:     {d['row_txn_count']} txns, ${d['row_total_amount']:.2f}, {d['row_customers']} cust")
        print(f"    Parquet:       {d['parq_txn_count']} txns, ${d['parq_total_amount']:.2f}, {d['parq_customers']} cust")
        print(f"    Txn diff:      {d['pct_diff']}%")
    print(f"\n  Extra customer-months (row-only): {ms['only_in_row_agg']}")
    print(f"  Extra customer-months (parq-only): {ms['only_in_parquet']}")

    print("\n" + "=" * 60)
    print("LEAKAGE CHECKS")
    print("=" * 60)
    asof = get_as_of_date(txns)
    print(f"  As-of date: {asof}")
    fv = check_no_future_data_used(txns, asof)
    print(f"  Future-data check: {fv}")
    lf = flag_leakage_tainted_variables([
        "days_since_last_transaction",
        "acquisition_channel",
        "region",
        "total_amount",
        "return_rate",
        "trailing_90d_spend",
    ])
    print(f"\n  Tainted variables:")
    for v in lf["tainted"]:
        print(f"    - {v['variable']}: {v['reason']}")
    print(f"\n  Clean variables:")
    for v in lf["clean"]:
        print(f"    - {v['variable']}: {v['reason']}")

    time_data = {
        "trend": td,
        "monthly_detail": [
            {"month": str(r["txn_month"].strftime("%Y-%m")), "txn_count": int(r["txn_count"]), "total_amount": float(r["total_amount"]), "unique_customers": int(r["unique_customers"])}
            for _, r in monthly.iterrows()
        ],
        "multi_source": ms,
        "leakage": {
            "as_of_date": str(asof),
            "future_data_check": fv,
            "tainted_variables": lf["tainted"],
            "clean_variables": lf["clean"],
        },
    }
    with open("outputs/time_and_leakage_results.json", "w") as f:
        json.dump(time_data, f, indent=2, default=str)
    print("\nResults saved to outputs/time_and_leakage_results.json")