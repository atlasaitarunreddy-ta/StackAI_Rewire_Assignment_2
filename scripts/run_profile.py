#!/usr/bin/env python3
"""
Runner: schema profile, missingness, distribution shapes, outliers.
"""

from eda.load import load_customers, load_transactions, load_monthly_agg
from eda.profile import (
    schema_summary,
    numeric_profile,
    zero_activity_count,
    zero_activity_churn_status,
)
from pathlib import Path
import json

DATA_DIR = Path("data")

if __name__ == "__main__":
    customers = load_customers(DATA_DIR / "customers.csv")
    txns = load_transactions(DATA_DIR / "transactions.db")
    parquet = load_monthly_agg(DATA_DIR / "transactions_monthly_agg.parquet")

    print("=" * 60)
    print("SCHEMA SUMMARY")
    print("=" * 60)
    for name, df in [("customers", customers), ("transactions", txns), ("monthly_agg", parquet)]:
        s = schema_summary(df, name)
        print(f"\n--- {name} ({len(df)} rows) ---")
        for _, r in s.iterrows():
            print(f"  {r['column']:30s} {r['dtype']:12s}  nulls={r['null_count']} ({r['null_pct']}%)")

    print("\n" + "=" * 60)
    print("ZERO-ACTIVITY CUSTOMER POPULATION")
    print("=" * 60)
    za_count = zero_activity_count(customers, txns)
    za_status = zero_activity_churn_status(customers, txns)
    print(f"  Count: {za_count}")
    print(f"  Churned: {za_status['churned']}/{za_count}")
    print(f"  Not churned: {za_status['not_churned']}/{za_count}")

    print("\n" + "=" * 60)
    print("NUMERIC DISTRIBUTION — TRANSACTION AMOUNT")
    print("=" * 60)
    amt = numeric_profile(txns["amount"])
    for k, v in amt.items():
        print(f"  {k:25s} = {v}")

    # Save profile summary
    profile_data = {
        "zero_activity": za_status,
        "amount_distribution": amt,
        "row_counts": {
            "customers": len(customers),
            "transactions": len(txns),
            "monthly_agg": len(parquet),
        },
    }
    with open("outputs/profile_summary.json", "w") as f:
        json.dump(profile_data, f, indent=2, default=str)
    print("\nProfile saved to outputs/profile_summary.json")