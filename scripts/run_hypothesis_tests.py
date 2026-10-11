#!/usr/bin/env python3
"""
Runner: hypothesis tests for all candidate churn drivers.
"""

from eda.load import load_customers, load_transactions
from eda.hypotheses import (
    test_channel_vs_churn,
    test_region_vs_churn,
    test_monetary_vs_churn,
    test_return_rate_vs_churn,
    diagnostic_days_since_last_txn,
)
from pathlib import Path
import json

DATA_DIR = Path("data")

if __name__ == "__main__":
    customers = load_customers(DATA_DIR / "customers.csv")
    txns = load_transactions(DATA_DIR / "transactions.db")

    tests = [
        test_channel_vs_churn(customers),
        test_region_vs_churn(customers),
        test_monetary_vs_churn(customers, txns),
        test_return_rate_vs_churn(customers, txns),
        diagnostic_days_since_last_txn(customers, txns),
    ]

    print("=" * 60)
    print("HYPOTHESIS TEST RESULTS")
    print("=" * 60)
    results_table = []
    for r in tests:
        print(f"\n--- {r['driver']} ---")
        print(f"  Test:                  {r['test_name']}")
        print(f"  Statistic:             {r['statistic']}")
        print(f"  p-value:               {r['p_value']}")
        print(f"  Effect size:           {r['effect_size_name']} = {r['effect_size']}")
        print(f"  Direction:             {r.get('direction', '')}")
        print(f"  Leakage tainted:       {r['leakage_tainted']}")
        print(f"  Leakage note:          {r['leakage_note']}")
        results_table.append(r)

    with open("outputs/hypothesis_results.json", "w") as f:
        json.dump(results_table, f, indent=2, default=str)
    print("\nResults saved to outputs/hypothesis_results.json")