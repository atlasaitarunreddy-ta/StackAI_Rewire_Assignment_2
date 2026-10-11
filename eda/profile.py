"""
Schema, missingness, distribution shapes, and outlier detection.
"""

import pandas as pd
import numpy as np


def schema_summary(df: pd.DataFrame, name: str) -> dict:
    """Return column-level dtype and null-count summary."""
    rows = []
    for col in df.columns:
        rows.append({
            "source": name,
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(float(df[col].isna().mean() * 100), 2),
        })
    return pd.DataFrame(rows)


def numeric_profile(series: pd.Series, iqr_multiple: float = 1.5) -> dict:
    """
    Return distribution shape + outlier count for a numeric series.

    Outlier rule: values below Q1 - m * IQR or above Q3 + m * IQR are flagged.
    """
    if series.empty or series.isna().all():
        raise ValueError("Cannot profile an empty or all-missing numeric series.")

    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - iqr_multiple * iqr
    upper = q3 + iqr_multiple * iqr
    outliers = series[(series < lower) | (series > upper)]
    return {
        "count": len(series),
        "mean": round(float(series.mean()), 2),
        "median": round(float(series.median()), 2),
        "std": round(float(series.std()), 2),
        "min": round(float(series.min()), 2),
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "max": round(float(series.max()), 2),
        "skewness": round(float(series.skew()), 4),
        "outlier_rule": f"{iqr_multiple}×IQR",
        "outlier_lower_bound": round(lower, 2),
        "outlier_upper_bound": round(upper, 2),
        "outlier_count": len(outliers),
        "outlier_pct": round(len(outliers) / len(series) * 100, 1),
        "outlier_direction": (
            "all high"
            if (outliers > upper).sum() == len(outliers) > 0
            else "all low"
            if (outliers < lower).sum() == len(outliers) > 0
            else "both sides"
        ),
    }


def categorical_profile(series: pd.Series) -> pd.DataFrame:
    """Frequency table for a categorical column."""
    counts = series.value_counts(dropna=False).reset_index()
    counts.columns = ["value", "count"]
    counts["pct"] = round(counts["count"] / len(series) * 100, 2)
    return counts


def churn_rate_by_group(
    customers: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    """Churn rate broken down by a categorical column in customers.csv."""
    grouped = customers.groupby(group_col).agg(
        total=("customer_id", "count"),
        churned=("churned", "sum"),
    ).reset_index()
    grouped["churn_rate"] = round(grouped["churned"] / grouped["total"] * 100, 2)
    return grouped


def zero_activity_count(
    customers: pd.DataFrame,
    txns: pd.DataFrame,
) -> int:
    """Count customers present in customers.csv but absent from transactions.db."""
    active = set(txns["customer_id"].unique())
    all_cust = set(customers["customer_id"])
    return len(all_cust - active)


def zero_activity_churn_status(
    customers: pd.DataFrame,
    txns: pd.DataFrame,
) -> dict:
    """
    Return churned counts for the zero-activity population.
    """
    active = set(txns["customer_id"].unique())
    za = customers[~customers["customer_id"].isin(active)]
    return {
        "count": len(za),
        "churned": int(za["churned"].sum()),
        "not_churned": int((za["churned"] == 0).sum()),
    }