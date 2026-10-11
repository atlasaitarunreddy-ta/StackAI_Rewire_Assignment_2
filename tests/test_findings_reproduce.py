"""
Tests for EDA_FINDINGS.md reproducibility.

For every numeric claim in the findings document, recompute it from the raw
sources and assert it matches. This is the parity test for this assignment.
"""

import pandas as pd
import numpy as np
import sqlite3
from eda.load import load_customers, load_transactions, load_monthly_agg


def test_row_count_customers():
    df = load_customers("data/customers.csv")
    assert len(df) == 1500


def test_row_count_transactions():
    df = load_transactions("data/transactions.db")
    assert len(df) == 11742


def test_row_count_monthly_agg():
    df = load_monthly_agg("data/transactions_monthly_agg.parquet")
    assert len(df) == 8086


def test_zero_nulls_all_sources():
    customers = load_customers("data/customers.csv")
    txns = load_transactions("data/transactions.db")
    parquet = load_monthly_agg("data/transactions_monthly_agg.parquet")
    assert customers.isna().sum().sum() == 0
    assert txns.isna().sum().sum() == 0
    assert parquet.isna().sum().sum() == 0


def test_zero_activity_count():
    customers = load_customers("data/customers.csv")
    txns = load_transactions("data/transactions.db")
    active = set(txns["customer_id"].unique())
    zero_act = set(customers["customer_id"]) - active
    assert len(zero_act) == 81


def test_zero_activity_all_churned():
    customers = load_customers("data/customers.csv")
    txns = load_transactions("data/transactions.db")
    active = set(txns["customer_id"].unique())
    za = customers[~customers["customer_id"].isin(active)]
    assert za["churned"].sum() == 81
    assert (za["churned"] == 0).sum() == 0


def test_overall_churn_rate():
    customers = load_customers("data/customers.csv")
    assert customers["churned"].sum() == 202
    assert round(customers["churned"].mean(), 4) == 0.1347


def test_active_customer_churn_rate():
    customers = load_customers("data/customers.csv")
    txns = load_transactions("data/transactions.db")
    active_ids = set(txns["customer_id"].unique())
    active = customers[customers["customer_id"].isin(active_ids)]
    assert active["churned"].sum() == 121
    assert round(active["churned"].mean(), 4) == 0.0853


def test_amount_distribution():
    txns = load_transactions("data/transactions.db")
    a = txns["amount"]
    assert round(a.mean(), 2) == 49.72
    assert round(a.median(), 2) == 33.82
    assert round(a.min(), 2) == 3.00
    assert round(a.max(), 2) == 1684.21
    assert round(a.quantile(0.25), 2) == 18.36
    assert round(a.quantile(0.75), 2) == 61.39


def test_amount_outliers():
    txns = load_transactions("data/transactions.db")
    a = txns["amount"]
    q1, q3 = a.quantile(0.25), a.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    lower = q1 - 1.5 * iqr
    assert round(upper, 2) == 125.93
    assert round(lower, 2) == -46.18
    outlier_count = int((a > upper).sum() + (a < lower).sum())
    assert outlier_count == 783
    assert round(outlier_count / len(a) * 100, 1) == 6.7
    assert (a < lower).sum() == 0  # no low-end outliers


def test_churn_by_channel():
    customers = load_customers("data/customers.csv")
    rates = customers.groupby("acquisition_channel")["churned"].mean()
    assert round(rates["organic"] * 100, 2) == 15.27
    assert round(rates["paid_search"] * 100, 2) == 10.21
    assert round(rates["referral"] * 100, 2) == 13.90
    assert round(rates["social"] * 100, 2) == 14.55


def test_churn_by_region():
    customers = load_customers("data/customers.csv")
    rates = customers.groupby("region")["churned"].mean()
    assert round(rates["east"] * 100, 2) == 16.36
    assert round(rates["north"] * 100, 2) == 12.34
    assert round(rates["west"] * 100, 2) == 12.37
    assert round(rates["south"] * 100, 2) == 12.71


def test_monthly_trend():
    txns = load_transactions("data/transactions.db")
    txns["txn_month"] = txns["txn_timestamp"].dt.to_period("M").dt.to_timestamp()
    monthly = txns.groupby("txn_month").agg(txn_count=("amount", "count")).reset_index().sort_values("txn_month")
    assert len(monthly) == 30
    assert monthly.iloc[0]["txn_count"] == 1
    assert monthly.iloc[-1]["txn_count"] == 1231
    assert monthly.iloc[0]["txn_month"].strftime("%Y-%m") == "2024-02"
    assert monthly.iloc[-1]["txn_month"].strftime("%Y-%m") == "2026-07"


def test_multi_source_agreement():
    txns = load_transactions("data/transactions.db")
    parquet = load_monthly_agg("data/transactions_monthly_agg.parquet")
    txns["txn_month"] = txns["txn_timestamp"].dt.to_period("M").dt.to_timestamp()
    row_agg = txns.groupby(["customer_id", "txn_month"]).agg(txn_count=("amount", "count")).reset_index()
    row_monthly = row_agg.groupby("txn_month").agg(row_txns=("txn_count", "sum")).reset_index()
    parq_monthly = parquet.groupby("txn_month").agg(parq_txns=("txn_count", "sum")).reset_index()
    merged = row_monthly.merge(parq_monthly, on="txn_month", how="outer").fillna(0)
    match_count = (merged["row_txns"] == merged["parq_txns"]).sum()
    assert match_count == 29


def test_days_since_leakage():
    customers = load_customers("data/customers.csv")
    txns = load_transactions("data/transactions.db")
    asof = txns["txn_timestamp"].max()
    last_txn = txns.groupby("customer_id")["txn_timestamp"].max().reset_index()
    last_txn["days_since"] = (asof - last_txn["txn_timestamp"]).dt.days
    merged = customers[["customer_id", "churned"]].merge(
        last_txn[["customer_id", "days_since"]], on="customer_id", how="left"
    )
    nc = merged[merged["churned"] == 0]["days_since"].dropna()
    ac = merged[merged["churned"] == 1]["days_since"].dropna()
    assert nc.max() == 90
    assert nc.min() == 0
    assert ac.min() >= 91
    assert (nc > 90).sum() == 0
    assert (ac < 91).sum() == 0