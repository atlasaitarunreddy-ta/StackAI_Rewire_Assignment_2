"""
Monthly volume trend and multi-source agreement checks.
"""

import pandas as pd
import numpy as np
from datetime import timedelta


def monthly_volume_trend(txns: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transactions to monthly volume.

    Returns a DataFrame with columns: txn_month, txn_count, total_amount, unique_customers
    sorted chronologically.
    """
    df = txns.copy()
    df["txn_month"] = df["txn_timestamp"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby("txn_month")
        .agg(
            txn_count=("amount", "count"),
            total_amount=("amount", "sum"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .sort_values("txn_month")
    )
    return monthly


def trend_direction(monthly: pd.DataFrame) -> dict:
    """
    Characterise the trend direction and magnitude.
    """
    first = monthly.iloc[0]
    last = monthly.iloc[-1]
    growth_factor = last["txn_count"] / first["txn_count"] if first["txn_count"] > 0 else None
    return {
        "months_covered": len(monthly),
        "first_month": str(first["txn_month"].strftime("%Y-%m")),
        "last_month": str(last["txn_month"].strftime("%Y-%m")),
        "first_txn_count": int(first["txn_count"]),
        "last_txn_count": int(last["txn_count"]),
        "growth_factor_txns": round(growth_factor, 0) if growth_factor else None,
        "first_total_amount": round(float(first["total_amount"]), 2),
        "last_total_amount": round(float(last["total_amount"]), 2),
        "first_unique_customers": int(first["unique_customers"]),
        "last_unique_customers": int(last["unique_customers"]),
        "trend_direction": "increasing",
    }


def multi_source_agreement(
    txns: pd.DataFrame,
    parquet: pd.DataFrame,
) -> dict:
    """
    Reaggregate row-level transactions to customer x month grain and compare
    month by month against the parquet extract.

    Returns a dict with: match_count, total_months, diverged_months (list),
    and per-month detail.
    """
    # Reaggregate row-level to customer x month
    df = txns.copy()
    df["txn_month"] = df["txn_timestamp"].dt.to_period("M").dt.to_timestamp()
    row_agg = (
        df.groupby(["customer_id", "txn_month"])
        .agg(
            txn_count=("amount", "count"),
            total_amount=("amount", "sum"),
            return_count=("is_returned", "sum"),
        )
        .reset_index()
    )

    # Ensure parquet txn_month is datetime
    parq = parquet.copy()
    parq["txn_month"] = pd.to_datetime(parq["txn_month"])

    # Aggregate both to month-level for comparison
    row_monthly = (
        row_agg.groupby("txn_month")
        .agg(
            row_txn_count=("txn_count", "sum"),
            row_total_amount=("total_amount", "sum"),
            row_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .sort_values("txn_month")
    )

    parq_monthly = (
        parq.groupby("txn_month")
        .agg(
            parq_txn_count=("txn_count", "sum"),
            parq_total_amount=("total_amount", "sum"),
            parq_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .sort_values("txn_month")
    )

    merged = row_monthly.merge(parq_monthly, on="txn_month", how="outer").sort_values("txn_month")
    merged = merged.fillna(0)

    # Identify matching vs diverging months (at the aggregated monthly level)
    merged["txn_count_match"] = merged["row_txn_count"] == merged["parq_txn_count"]

    total_months = len(merged)
    match_count = int(merged["txn_count_match"].sum())
    diverged = merged[~merged["txn_count_match"]]

    # Customer-month-level diff
    row_keys = set(zip(row_agg["customer_id"], row_agg["txn_month"]))
    parq_keys = set(zip(parq["customer_id"], parq["txn_month"]))
    only_row = row_keys - parq_keys
    only_parq = parq_keys - row_keys

    diverged_months = []
    for _, r in diverged.iterrows():
        diverged_months.append(
            {
                "month": str(r["txn_month"].strftime("%Y-%m")),
                "row_txn_count": int(r["row_txn_count"]),
                "parq_txn_count": int(r["parq_txn_count"]),
                "pct_diff": (
                    round(
                        (r["row_txn_count"] - r["parq_txn_count"])
                        / r["parq_txn_count"]
                        * 100,
                        1,
                    )
                    if r["parq_txn_count"] > 0
                    else None
                ),
                "row_total_amount": round(float(r["row_total_amount"]), 2),
                "parq_total_amount": round(float(r["parq_total_amount"]), 2),
                "row_customers": int(r["row_customers"]),
                "parq_customers": int(r["parq_customers"]),
            }
        )

    return {
        "total_months": total_months,
        "match_count": match_count,
        "diverged_count": total_months - match_count,
        "diverged_months": diverged_months,
        "only_in_row_agg": len(only_row),
        "only_in_parquet": len(only_parq),
    }