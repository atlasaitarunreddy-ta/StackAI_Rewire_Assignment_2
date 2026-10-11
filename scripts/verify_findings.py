#!/usr/bin/env python3
"""
Check key EDA findings against raw data and validate the report's churned count.

The raw-data checks compare computed values with expected values. The report
claim check confirms that the churned count in the selected Markdown file
matches the raw customer data. The script exits non-zero on any mismatch.
"""

import sys
import argparse
import re
from pathlib import Path
import pandas as pd
import numpy as np
from eda.load import load_customers, load_transactions, load_monthly_agg
from eda.profile import numeric_profile, zero_activity_count, zero_activity_churn_status
from eda.time_checks import monthly_volume_trend, trend_direction, multi_source_agreement

DATA_DIR = "data"

def check(name: str, expected, computed):
    """Assert equality and print result."""
    ok = expected == computed
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if not ok:
        print(f"         expected = {expected!r}")
        print(f"         computed = {computed!r}")
    return ok


def extract_churned_count_claim(findings_text: str):
    match = re.search(r"^\s*-\s+\*\*Churned\*\*:\s*([\d,]+)\s*$", findings_text, re.MULTILINE)
    return int(match.group(1).replace(",", "")) if match else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--findings-file",
        default="EDA_FINDINGS.md",
        help="Markdown findings file whose churned-count claim should be checked.",
    )
    args = parser.parse_args()

    customers = load_customers(f"{DATA_DIR}/customers.csv")
    txns = load_transactions(f"{DATA_DIR}/transactions.db")
    parquet = load_monthly_agg(f"{DATA_DIR}/transactions_monthly_agg.parquet")
    findings_text = Path(args.findings_file).read_text(encoding="utf-8")

    print("=" * 60)
    print("VERIFYING NUMERIC CLAIMS IN EDA_FINDINGS.md")
    print("=" * 60)

    results = []

    # 1. Row counts
    results.append(check("Row count: customers.csv", 1500, len(customers)))
    results.append(check("Row count: transactions.db", 11742, len(txns)))
    results.append(check("Row count: monthly_agg.parquet", 8086, len(parquet)))

    # 2. Zero nulls
    results.append(check("Zero nulls: customers", 0, customers.isna().sum().sum()))
    results.append(check("Zero nulls: transactions", 0, txns.isna().sum().sum()))
    results.append(check("Zero nulls: monthly_agg", 0, parquet.isna().sum().sum()))

    # 3. Zero-activity customers
    za_count = zero_activity_count(customers, txns)
    results.append(check("Zero-activity customer count", 81, za_count))
    za_status = zero_activity_churn_status(customers, txns)
    results.append(check("Zero-activity: all churned=1", True, za_status["churned"] == 81 and za_status["not_churned"] == 0))

    # 4. Overall churn rate
    overall_churn = customers["churned"].mean()
    results.append(check("Overall churn rate", 0.1347, round(overall_churn, 4)))
    churned_count = int(customers["churned"].sum())
    results.append(check("Churned count", 202, churned_count))
    results.append(check(
        "EDA_FINDINGS.md churned-count claim",
        churned_count,
        extract_churned_count_claim(findings_text),
    ))

    # 5. Churn among active customers
    active_ids = set(txns["customer_id"].unique())
    active_cust = customers[customers["customer_id"].isin(active_ids)]
    active_churn_rate = active_cust["churned"].mean()
    results.append(check("Active customer churn rate", 0.0853, round(active_churn_rate, 4)))
    results.append(check("Active churned count", 121, int(active_cust["churned"].sum())))

    # 6. Amount distribution
    amt = txns["amount"]
    amt_profile = numeric_profile(amt)
    results.append(check("Amount mean", 49.72, amt_profile["mean"]))
    results.append(check("Amount median", 33.82, amt_profile["median"]))
    results.append(check("Amount std", 55.24, amt_profile["std"]))
    results.append(check("Amount min", 3.00, amt_profile["min"]))
    results.append(check("Amount Q1", 18.36, amt_profile["q1"]))
    results.append(check("Amount Q3", 61.39, amt_profile["q3"]))
    results.append(check("Amount max", 1684.21, amt_profile["max"]))
    # 1.5*IQR outlier rule
    q1, q3 = amt.quantile(0.25), amt.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    lower = q1 - 1.5 * iqr
    results.append(check("IQR outlier upper bound", 125.93, round(upper, 2)))
    results.append(check("IQR outlier lower bound", -46.18, round(lower, 2)))
    outlier_count = int((amt > upper).sum() + (amt < lower).sum())
    results.append(check("Outlier count", 783, outlier_count))
    results.append(check("Outlier %", 6.7, round(outlier_count / len(amt) * 100, 1)))
    results.append(check("Outliers all high", "all high", amt_profile["outlier_direction"]))

    # 7. Churn by acquisition channel
    ac_rates = customers.groupby("acquisition_channel")["churned"].mean()
    results.append(check("Channel: organic churn rate", 15.27, round(ac_rates.get("organic", 0) * 100, 2)))
    results.append(check("Channel: paid_search churn rate", 10.21, round(ac_rates.get("paid_search", 0) * 100, 2)))
    results.append(check("Channel: referral churn rate", 13.90, round(ac_rates.get("referral", 0) * 100, 2)))
    results.append(check("Channel: social churn rate", 14.55, round(ac_rates.get("social", 0) * 100, 2)))

    # 8. Churn by region
    reg_rates = customers.groupby("region")["churned"].mean()
    results.append(check("Region: east churn rate", 16.36, round(reg_rates.get("east", 0) * 100, 2)))
    results.append(check("Region: north churn rate", 12.34, round(reg_rates.get("north", 0) * 100, 2)))
    results.append(check("Region: west churn rate", 12.37, round(reg_rates.get("west", 0) * 100, 2)))
    results.append(check("Region: south churn rate", 12.71, round(reg_rates.get("south", 0) * 100, 2)))

    # 9. Time trend — monthly volume
    monthly = monthly_volume_trend(txns)
    td = trend_direction(monthly)
    results.append(check("Trend: months covered", 30, td["months_covered"]))
    results.append(check("Trend: first month", "2024-02", td["first_month"]))
    results.append(check("Trend: last month", "2026-07", td["last_month"]))
    results.append(check("Trend: first txn count", 1, td["first_txn_count"]))
    results.append(check("Trend: last txn count", 1231, td["last_txn_count"]))
    results.append(check("Trend: direction", "increasing", td["trend_direction"]))

    # 10. Multi-source agreement
    ms = multi_source_agreement(txns, parquet)
    results.append(check("Multi-source: total months", 30, ms["total_months"]))
    results.append(check("Multi-source: match count", 29, ms["match_count"]))
    results.append(check("Multi-source: diverged count", 1, ms["diverged_count"]))
    results.append(check("Multi-source: only in row agg", 102, ms["only_in_row_agg"]))
    results.append(check("Multi-source: only in parquet", 0, ms["only_in_parquet"]))

    if ms["diverged_months"]:
        d = ms["diverged_months"][0]
        results.append(check("Multi-source: diverged month", "2026-07", d["month"]))
        results.append(check("Multi-source: July row txns", 1231, d["row_txn_count"]))
        results.append(check("Multi-source: July parq txns", 994, d["parq_txn_count"]))
        results.append(check("Multi-source: July row amt", 62084.62, round(d["row_total_amount"], 2)))
        results.append(check("Multi-source: July parq amt", 50116.67, round(d["parq_total_amount"], 2)))

    # 10. Days-since-last-txn separation
    asof = txns["txn_timestamp"].max()
    last_txn = txns.groupby("customer_id")["txn_timestamp"].max().reset_index()
    last_txn["days_since"] = (asof - last_txn["txn_timestamp"]).dt.days
    merged = customers[["customer_id", "churned"]].merge(
        last_txn[["customer_id", "days_since"]], on="customer_id", how="left"
    )
    nc_days = merged.loc[merged["churned"] == 0, "days_since"].dropna()
    ac_days = merged.loc[merged["churned"] == 1, "days_since"].dropna()
    results.append(check("DSLT: non-churned max days", 90, int(nc_days.max())))
    results.append(check("DSLT: non-churned min days", 0, int(nc_days.min())))
    results.append(check("DSLT: churned (active) max days", 365, int(ac_days.max())))
    results.append(check("DSLT: churned (active) min days", 91, int(ac_days.min())))
    results.append(check("DSLT: non-churned > 90 days", 0, int((nc_days > 90).sum())))
    results.append(check("DSLT: churned < 91 days", 0, int((ac_days < 91).sum())))

    # Summary
    passed = sum(results)
    failed = len(results) - passed
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} checks")
    if failed > 0:
        print("ERROR: Some claims in EDA_FINDINGS.md do not reproduce!")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED - raw-data checks and the churned-count claim match.")
        sys.exit(0)


if __name__ == "__main__":
    main()