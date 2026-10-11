"""
Leakage checks: as-of-date discipline and label-circularity detection.
"""

import pandas as pd


def get_as_of_date(txns: pd.DataFrame) -> pd.Timestamp:
    """Return the as-of date — the last observed transaction timestamp."""
    return txns["txn_timestamp"].max()


def flag_leakage_tainted_variables(candidate_variables: list[str]) -> dict:
    """
    Given a list of candidate variable names, return those whose computation
    window overlaps the label's trailing-90-day definition.

    Known tainted patterns:
    - days_since_last_transaction (directly circular)
    - Any variable containing 'trailing_90d' or 'last_90d'
    - Any recency/windowed aggregate computed over the trailing 90 days
    """
    tainted = []
    clean = []
    for var in candidate_variables:
        is_tainted = False
        note = ""
        if var == "days_since_last_transaction":
            is_tainted = True
            note = "Directly circular — computed from the same trailing-90-day window that defines the churn label."
        elif "trailing_90" in var.lower() or "last_90" in var.lower():
            is_tainted = True
            note = "Windowed aggregate over the same 90-day window as the label definition."
        elif "recency" in var.lower():
            is_tainted = True
            note = "Recency-based variable — overlaps with the trailing-90-day label window."
        else:
            note = "No evidence of label-window overlap."

        if is_tainted:
            tainted.append({"variable": var, "reason": note})
        else:
            clean.append({"variable": var, "reason": note})

    return {"tainted": tainted, "clean": clean}


def check_no_future_data_used(
    txns: pd.DataFrame,
    as_of_date: pd.Timestamp,
    profile_period_end: pd.Timestamp | None = None,
) -> dict:
    """
    Confirm no transaction with timestamp after as_of_date was included
    in any profiling or hypothesis computation.
    """
    if profile_period_end is None:
        profile_period_end = as_of_date
    future_rows = txns[txns["txn_timestamp"] > profile_period_end]
    return {
        "as_of_date": str(as_of_date),
        "profile_period_end": str(profile_period_end),
        "future_rows_count": len(future_rows),
        "all_data_before_as_of": len(future_rows) == 0,
    }