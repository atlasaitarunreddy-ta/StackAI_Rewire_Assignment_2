"""
Pure hypothesis-test functions for candidate churn drivers.

Each function returns a dict with: driver, test_name, statistic, p_value,
effect_size_name, effect_size, direction, and leakage_tainted.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu


def _cramers_v(contingency_table: np.ndarray) -> float:
    """Cramér's V for a chi-square test on a contingency table."""
    chi2, *_ = chi2_contingency(contingency_table)
    n = contingency_table.sum()
    k = min(contingency_table.shape)
    return float(np.sqrt(chi2 / n / (k - 1))) if n > 0 and k > 1 else 0.0


def _rank_biserial(u_stat: float, n1: int, n2: int) -> float:
    """Compute rank-biserial correlation from Mann-Whitney U."""
    return float(1 - (2 * u_stat) / (n1 * n2))


def test_channel_vs_churn(
    customers: pd.DataFrame,
    channel_col: str = "acquisition_channel",
    churn_col: str = "churned",
) -> dict:
    """
    Chi-square test of independence: acquisition_channel × churned.
    Returns dict with test results + Cramér's V.
    """
    table = pd.crosstab(customers[channel_col], customers[churn_col])
    chi2, p_value, dof, expected = chi2_contingency(table)
    v = _cramers_v(table.values)
    # Determine which channel has highest churn rate
    rates = customers.groupby(channel_col)[churn_col].mean()
    highest = rates.idxmax()
    lowest = rates.idxmin()
    return {
        "driver": channel_col,
        "test_name": "Chi-square test of independence",
        "statistic": round(float(chi2), 4),
        "p_value": float(p_value),
        "effect_size_name": "Cramér's V",
        "effect_size": round(v, 4),
        "direction": f"Highest churn: {highest} ({rates[highest]*100:.2f}%); lowest churn: {lowest} ({rates[lowest]*100:.2f}%)",
        "leakage_tainted": False,
        "leakage_note": "Static attribute — no temporal overlap with label.",
    }


def test_region_vs_churn(
    customers: pd.DataFrame,
    region_col: str = "region",
    churn_col: str = "churned",
) -> dict:
    """
    Chi-square test of independence: region × churned.
    """
    table = pd.crosstab(customers[region_col], customers[churn_col])
    chi2, p_value, dof, expected = chi2_contingency(table)
    v = _cramers_v(table.values)
    rates = customers.groupby(region_col)[churn_col].mean()
    highest = rates.idxmax()
    lowest = rates.idxmin()
    return {
        "driver": region_col,
        "test_name": "Chi-square test of independence",
        "statistic": round(float(chi2), 4),
        "p_value": float(p_value),
        "effect_size_name": "Cramér's V",
        "effect_size": round(v, 4),
        "direction": f"Highest churn: {highest} ({rates[highest]*100:.2f}%); lowest churn: {lowest} ({rates[lowest]*100:.2f}%)",
        "leakage_tainted": False,
        "leakage_note": "Static attribute — no temporal overlap with label.",
    }


def test_monetary_vs_churn(
    customers: pd.DataFrame,
    txns: pd.DataFrame,
) -> dict:
    """
    Mann-Whitney U test: total_amount per customer by churn status.

    Reaggregates transactions to customer-level total amount, then compares
    distributions between churned and non-churned.
    """
    cust_amt = txns.groupby("customer_id", as_index=False)["amount"].sum()
    cust_amt.rename(columns={"amount": "total_amount"}, inplace=True)
    merged = customers[["customer_id", "churned"]].merge(cust_amt, on="customer_id", how="left")
    merged["total_amount"] = merged["total_amount"].fillna(0)

    churned_vals = merged.loc[merged["churned"] == 1, "total_amount"]
    not_churned_vals = merged.loc[merged["churned"] == 0, "total_amount"]

    u_stat, p_value = mannwhitneyu(churned_vals, not_churned_vals, alternative="two-sided")
    rb = _rank_biserial(u_stat, len(churned_vals), len(not_churned_vals))

    median_c = float(churned_vals.median())
    median_nc = float(not_churned_vals.median())
    higher_group = "non-churned" if median_nc > median_c else "churned"

    return {
        "driver": "total_amount (customer-level)",
        "test_name": "Mann-Whitney U test",
        "statistic": round(float(u_stat), 2),
        "p_value": float(p_value),
        "effect_size_name": "rank-biserial correlation",
        "effect_size": round(rb, 4),
        "direction": f"Median total amount — churned: ${median_c:.2f}, non-churned: ${median_nc:.2f} (higher: {higher_group})",
        "leakage_tainted": False,
        "leakage_note": "All-time aggregate — not windowed relative to label.",
    }


def test_return_rate_vs_churn(
    customers: pd.DataFrame,
    txns: pd.DataFrame,
) -> dict:
    """
    Mann-Whitney U test: return rate per customer by churn status.

    Reaggregates transactions to customer-level return rate
    (count of returns / total transactions), then compares distributions.
    """
    cust_stats = txns.groupby("customer_id", as_index=False).agg(
        total_txns=("is_returned", "count"),
        return_count=("is_returned", "sum"),
    )
    cust_stats["return_rate"] = cust_stats["return_count"] / cust_stats["total_txns"]
    merged = customers[["customer_id", "churned"]].merge(cust_stats, on="customer_id", how="left")
    merged["return_rate"] = merged["return_rate"].fillna(0.0)

    churned_vals = merged.loc[merged["churned"] == 1, "return_rate"]
    not_churned_vals = merged.loc[merged["churned"] == 0, "return_rate"]

    u_stat, p_value = mannwhitneyu(churned_vals, not_churned_vals, alternative="two-sided")
    rb = _rank_biserial(u_stat, len(churned_vals), len(not_churned_vals))

    med_c = float(churned_vals.median())
    med_nc = float(not_churned_vals.median())
    higher_group = "churned" if med_c > med_nc else "non-churned"

    return {
        "driver": "return_rate (customer-level)",
        "test_name": "Mann-Whitney U test",
        "statistic": round(float(u_stat), 2),
        "p_value": float(p_value),
        "effect_size_name": "rank-biserial correlation",
        "effect_size": round(rb, 4),
        "direction": f"Median return rate — churned: {med_c:.4f}, non-churned: {med_nc:.4f} (higher: {higher_group})",
        "leakage_tainted": False,
        "leakage_note": "All-time proportion — not windowed relative to label.",
    }


def diagnostic_days_since_last_txn(
    customers: pd.DataFrame,
    txns: pd.DataFrame,
    as_of_date=None,
) -> dict:
    """
    Diagnostic-only check for days_since_last_transaction.

    This variable is circular with the label definition and is NOT a usable
    predictive feature. Reported for diagnostic completeness only.
    """
    if as_of_date is None:
        as_of_date = txns["txn_timestamp"].max()
    last_txn = txns.groupby("customer_id", as_index=False)["txn_timestamp"].max()
    last_txn["days_since"] = (as_of_date - last_txn["txn_timestamp"]).dt.days

    merged = customers[["customer_id", "churned"]].merge(
        last_txn[["customer_id", "days_since"]], on="customer_id", how="left"
    )

    nc = merged.loc[merged["churned"] == 0, "days_since"].dropna()
    ac = merged.loc[merged["churned"] == 1, "days_since"].dropna()

    result = {
        "driver": "days_since_last_transaction",
        "test_name": "Descriptive + Mann-Whitney U (diagnostic only)",
        "statistic": None,
        "p_value": None,
        "effect_size_name": "descriptive separation range",
        "effect_size": None,
        "direction": "",
        "leakage_tainted": True,
        "leakage_note": (
            "Circular with label definition — churn = no purchase in trailing 90 days, "
            "and this variable measures exactly that. Near-perfect separation is definitional, not predictive."
        ),
        "non_churned": {
            "count": len(nc),
            "min_days": int(nc.min()),
            "max_days": int(nc.max()),
            "mean_days": round(float(nc.mean()), 1),
            "median_days": round(float(nc.median()), 0),
        },
        "churned_active": {
            "count": len(ac),
            "min_days": int(ac.min()),
            "max_days": int(ac.max()),
            "mean_days": round(float(ac.mean()), 1),
            "median_days": round(float(ac.median()), 0),
        },
    }

    if len(nc) > 0 and len(ac) > 0:
        u_stat, p_val = mannwhitneyu(ac, nc, alternative="two-sided")
        result["statistic"] = round(float(u_stat), 2)
        result["p_value"] = float(p_val)
        result["effect_size"] = round(nc.max() - nc.min(), 2)
        result["direction"] = (
            f"Non-churned: 0–{int(nc.max())} days; churned (active): {int(ac.min())}–{int(ac.max())} days. "
            "Complete separation by construction — the label is defined on this same window."
        )

    return result