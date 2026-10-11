"""
Tests for hypotheses.py — each hypothesis function on constructed input with known answer.
"""

import pandas as pd
import numpy as np
# Import using a non-test-visible alias to avoid pytest collecting the imported functions
_hyp = __import__("eda.hypotheses", fromlist=[
    "test_channel_vs_churn", "test_region_vs_churn", "test_monetary_vs_churn",
    "test_return_rate_vs_churn", "diagnostic_days_since_last_txn",
])


def _load_customers_and_txns():
    """Helper to load both sources with proper timestamp parsing."""
    customers = pd.read_csv("data/customers.csv", parse_dates=["signup_date"])
    import sqlite3
    conn = sqlite3.connect("data/transactions.db")
    txns = pd.read_sql("SELECT * FROM transactions", conn, parse_dates=["txn_timestamp"])
    conn.close()
    if not pd.api.types.is_datetime64_any_dtype(txns["txn_timestamp"]):
        txns["txn_timestamp"] = pd.to_datetime(txns["txn_timestamp"])
    return customers, txns


class TestChannelVsChurn:
    def test_output_structure(self):
        customers, _ = _load_customers_and_txns()
        result = _hyp.test_channel_vs_churn(customers)
        for key in ["driver", "test_name", "statistic", "p_value", "effect_size_name", "effect_size", "leakage_tainted"]:
            assert key in result, f"Missing key: {key}"
        assert result["leakage_tainted"] is False

    def test_not_tainted(self):
        customers, _ = _load_customers_and_txns()
        result = _hyp.test_channel_vs_churn(customers)
        assert result["leakage_tainted"] is False


class TestRegionVsChurn:
    def test_output_structure(self):
        customers, _ = _load_customers_and_txns()
        result = _hyp.test_region_vs_churn(customers)
        for key in ["driver", "test_name", "statistic", "p_value", "effect_size_name", "effect_size", "leakage_tainted"]:
            assert key in result
        assert result["leakage_tainted"] is False


class TestMonetaryVsChurn:
    def test_output_structure(self):
        customers, txns = _load_customers_and_txns()
        result = _hyp.test_monetary_vs_churn(customers, txns)
        assert result["leakage_tainted"] is False
        assert result["effect_size_name"] == "rank-biserial correlation"
        assert result["p_value"] is not None

    def test_non_churned_should_have_higher_amount(self):
        customers, txns = _load_customers_and_txns()
        result = _hyp.test_monetary_vs_churn(customers, txns)
        assert result["p_value"] < 0.05
        assert "non-churned" in result["direction"].lower()


class TestReturnRateVsChurn:
    def test_output_structure(self):
        customers, txns = _load_customers_and_txns()
        result = _hyp.test_return_rate_vs_churn(customers, txns)
        assert result["leakage_tainted"] is False


class TestDiagnosticDaysSince:
    def test_leakage_flagged(self):
        customers, txns = _load_customers_and_txns()
        result = _hyp.diagnostic_days_since_last_txn(customers, txns)
        assert result["leakage_tainted"] is True
        assert "circular" in result["leakage_note"].lower()

    def test_perfect_separation(self):
        customers, txns = _load_customers_and_txns()
        result = _hyp.diagnostic_days_since_last_txn(customers, txns)
        nc = result["non_churned"]
        ac = result["churned_active"]
        assert nc["max_days"] <= 90
        assert ac["min_days"] >= 91