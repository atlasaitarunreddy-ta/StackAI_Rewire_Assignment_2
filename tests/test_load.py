"""
Tests for load.py — source loaders against real files.
"""

import pandas as pd
from pathlib import Path
from eda.load import load_customers, load_transactions, load_monthly_agg

DATA = Path("data")


class TestLoad:
    def test_customers_columns_and_dtypes(self):
        df = load_customers(DATA / "customers.csv")
        expected_cols = {"customer_id", "signup_date", "acquisition_channel", "region", "churned"}
        assert expected_cols.issubset(set(df.columns)), f"Missing columns: {expected_cols - set(df.columns)}"
        assert df["customer_id"].dtype in ("int64",), f"customer_id dtype: {df['customer_id'].dtype}"
        assert df["churned"].dtype in ("int64",), f"churned dtype: {df['churned'].dtype}"

    def test_customers_row_count_in_range(self):
        df = load_customers(DATA / "customers.csv")
        assert 1400 <= len(df) <= 1600, f"Row count {len(df)} outside expected range"

    def test_transactions_columns_and_dtypes(self):
        df = load_transactions(DATA / "transactions.db")
        expected_cols = {"customer_id", "txn_timestamp", "category", "channel", "amount", "is_returned"}
        assert expected_cols.issubset(set(df.columns))
        assert df["amount"].dtype == "float64"

    def test_transactions_row_count_in_range(self):
        df = load_transactions(DATA / "transactions.db")
        assert 11000 <= len(df) <= 12500, f"Row count {len(df)} outside expected range"

    def test_monthly_agg_columns_and_dtypes(self):
        df = load_monthly_agg(DATA / "transactions_monthly_agg.parquet")
        expected_cols = {"customer_id", "txn_month", "txn_count", "total_amount", "return_count"}
        assert expected_cols.issubset(set(df.columns))
        assert df["txn_count"].dtype in ("int64",), f"txn_count dtype: {df['txn_count'].dtype}"

    def test_monthly_agg_row_count_in_range(self):
        df = load_monthly_agg(DATA / "transactions_monthly_agg.parquet")
        assert 7000 <= len(df) <= 9000, f"Row count {len(df)} outside expected range"

    def test_zero_nulls_customers(self):
        df = load_customers(DATA / "customers.csv")
        assert df.isna().sum().sum() == 0

    def test_zero_nulls_transactions(self):
        df = load_transactions(DATA / "transactions.db")
        assert df.isna().sum().sum() == 0

    def test_zero_nulls_monthly_agg(self):
        df = load_monthly_agg(DATA / "transactions_monthly_agg.parquet")
        assert df.isna().sum().sum() == 0