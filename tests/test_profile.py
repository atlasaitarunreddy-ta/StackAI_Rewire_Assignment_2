"""
Tests for profile.py — profiling functions on synthetic and real data.
"""

import pandas as pd
import numpy as np
from eda.profile import numeric_profile, categorical_profile, zero_activity_count


class TestNumericProfile:
    def test_known_symmetric_distribution(self):
        """A normal distribution should have mean ~ median and few 1.5xIQR outliers."""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 15, 1000))
        prof = numeric_profile(data)
        assert abs(prof["mean"] - prof["median"]) < 5, f"Mean/median gap too large: {prof['mean']} vs {prof['median']}"
        # For N(100,15), ~0.7% are beyond 1.5xIQR
        assert prof["outlier_pct"] < 5, f"Too many outliers: {prof['outlier_pct']}%"

    def test_known_right_skewed(self):
        """A log-normal should show mean > median."""
        np.random.seed(42)
        data = pd.Series(np.exp(np.random.normal(3, 0.8, 1000)))
        prof = numeric_profile(data)
        assert prof["mean"] > prof["median"], "Right-skewed should have mean > median"
        assert prof["skewness"] > 0.5, f"Skewness should be positive: {prof['skewness']}"

    def test_known_outliers_detected(self):
        """A series with injected extreme values should flag them."""
        data = pd.Series([1, 2, 2, 3, 3, 4, 5, 100, 200])
        prof = numeric_profile(data)
        assert prof["outlier_count"] >= 2, f"Should detect injected outliers, got {prof['outlier_count']}"
        assert prof["outlier_direction"] == "all high"

    def test_no_outliers_constant(self):
        """A constant series should have zero outliers."""
        data = pd.Series([5.0] * 50)
        prof = numeric_profile(data)
        assert prof["outlier_count"] == 0


class TestCategoricalProfile:
    def test_frequency_table(self):
        data = pd.Series(["a", "a", "b", "c", "c", "c"])
        prof = categorical_profile(data)
        assert len(prof) == 3
        assert prof.loc[prof["value"] == "c", "count"].values[0] == 3

    def test_pct_sums_to_100(self):
        data = pd.Series(["x", "y", "z"] * 10)
        prof = categorical_profile(data)
        assert abs(prof["pct"].sum() - 100) < 0.1


class TestZeroActivity:
    def test_zero_activity_all_81_churned(self):
        customers = pd.read_csv("data/customers.csv")
        import sqlite3
        conn = sqlite3.connect("data/transactions.db")
        txns = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        za_count = zero_activity_count(customers, txns)
        assert za_count == 81, f"Expected 81 zero-activity, got {za_count}"