"""
Tests for time_checks.py and leakage_checks.py.
"""

import pandas as pd
import numpy as np
from eda.time_checks import monthly_volume_trend, trend_direction, multi_source_agreement
from eda.leakage_checks import (
    get_as_of_date,
    flag_leakage_tainted_variables,
    check_no_future_data_used,
)


class TestTimeChecks:
    def test_monthly_volume_trend_direction(self):
        import sqlite3
        conn = sqlite3.connect("data/transactions.db")
        txns = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        txns["txn_timestamp"] = pd.to_datetime(txns["txn_timestamp"])
        monthly = monthly_volume_trend(txns)
        td = trend_direction(monthly)
        assert td["months_covered"] == 30
        assert td["first_month"] == "2024-02"
        assert td["last_month"] == "2026-07"
        assert td["trend_direction"] == "increasing"
        assert td["first_txn_count"] <= td["last_txn_count"]

    def test_multi_source_agreement(self):
        import sqlite3
        conn = sqlite3.connect("data/transactions.db")
        txns = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        txns["txn_timestamp"] = pd.to_datetime(txns["txn_timestamp"])
        parquet = pd.read_parquet("data/transactions_monthly_agg.parquet")
        ms = multi_source_agreement(txns, parquet)
        assert ms["total_months"] == 30
        assert ms["match_count"] == 29
        assert ms["diverged_count"] == 1
        assert ms["only_in_parquet"] == 0

    def test_multi_source_on_constructed_matching(self):
        """Construct two matching DataFrames at the monthly level and confirm they agree."""
        txns = pd.DataFrame({
            "customer_id": [1, 1, 2],
            "txn_timestamp": pd.to_datetime(["2024-01-15", "2024-01-20", "2024-02-10"]),
            "amount": [10.0, 20.0, 30.0],
            "is_returned": [0, 0, 1],
            "category": ["a", "a", "b"],
            "channel": ["web", "web", "store"],
        })
        parquet = pd.DataFrame({
            "customer_id": [1, 2],
            "txn_month": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "txn_count": [2, 1],
            "total_amount": [30.0, 30.0],
            "return_count": [0, 1],
        })
        ms = multi_source_agreement(txns, parquet)
        assert ms["total_months"] == 2
        assert ms["match_count"] == 2

    def test_multi_source_on_constructed_mismatch(self):
        """Construct DataFrames with intentional mismatch and confirm detection."""
        txns = pd.DataFrame({
            "customer_id": [1, 2],
            "txn_timestamp": pd.to_datetime(["2024-01-15", "2024-01-20"]),
            "amount": [10.0, 20.0],
            "is_returned": [0, 0],
            "category": ["a", "a"],
            "channel": ["web", "web"],
        })
        parquet = pd.DataFrame({
            "customer_id": [1],
            "txn_month": pd.to_datetime(["2024-01-01"]),
            "txn_count": [1],
            "total_amount": [10.0],
            "return_count": [0],
        })
        ms = multi_source_agreement(txns, parquet)
        assert ms["diverged_count"] >= 1


class TestLeakageChecks:
    def test_get_as_of_date(self):
        import sqlite3
        conn = sqlite3.connect("data/transactions.db")
        txns = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        txns["txn_timestamp"] = pd.to_datetime(txns["txn_timestamp"])
        asof = get_as_of_date(txns)
        assert asof.year == 2026 and asof.month == 7

    def test_flag_tainted_identifies_circular_variable(self):
        result = flag_leakage_tainted_variables(
            ["days_since_last_transaction", "acquisition_channel", "region"]
        )
        tainted_names = [v["variable"] for v in result["tainted"]]
        clean_names = [v["variable"] for v in result["clean"]]
        assert "days_since_last_transaction" in tainted_names
        assert "acquisition_channel" in clean_names
        assert "region" in clean_names

    def test_flag_tainted_identifies_trailing_window(self):
        result = flag_leakage_tainted_variables(["trailing_90d_spend", "last_90d_count"])
        tainted_names = [v["variable"] for v in result["tainted"]]
        assert "trailing_90d_spend" in tainted_names
        assert "last_90d_count" in tainted_names

    def test_no_future_data(self):
        import sqlite3
        conn = sqlite3.connect("data/transactions.db")
        txns = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        txns["txn_timestamp"] = pd.to_datetime(txns["txn_timestamp"])
        asof = get_as_of_date(txns)
        result = check_no_future_data_used(txns, asof)
        assert result["all_data_before_as_of"] is True
        assert result["future_rows_count"] == 0