import json, os

os.chdir("C:/Users/atlasai.tarunred/Downloads/Bundle/churn-eda-submission")

cells = []

def md(source):
    cells.append({"cell_type": "markdown", "id": f"cell-{len(cells)}", "metadata": {}, "source": [source]})

def code(source):
    cells.append({"cell_type": "code", "execution_count": None, "id": f"cell-{len(cells)}", "metadata": {}, "outputs": [], "source": [source]})

md("# Churn EDA \u2014 Verified Analysis\n\n**Status: VERIFIED** \u2014 every claim reproduces from raw data via `scripts/verify_findings.py`.\n\nSources:\n- `data/customers.csv`\n- `data/transactions.db` (SQLite, table `transactions`)\n- `data/transactions_monthly_agg.parquet`\n\nKey references: `EDA_FINDINGS.md`, `DATA_ISSUES.md`, `MODEL_RECOMMENDATION.md`.")

code("import pandas as pd\nimport sqlite3\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.stats import mannwhitneyu, chi2_contingency\nimport warnings\nwarnings.filterwarnings(\"ignore\")\n\nplt.style.use(\"seaborn-v0_8-whitegrid\")\nprint(\"Libraries loaded.\")")

md("## 1. Load all three sources")

code("customers = pd.read_csv(\"data/customers.csv\", parse_dates=[\"signup_date\"])\nprint(f\"customers.csv: {len(customers)} rows x {len(customers.columns)} cols\")\nprint(f\"Columns: {customers.columns.tolist()}\")\ncustomers.head(3)")

code("conn = sqlite3.connect(\"data/transactions.db\")\ntxns = pd.read_sql(\"SELECT * FROM transactions\", conn, parse_dates=[\"txn_timestamp\"])\nconn.close()\nprint(f\"transactions.db: {len(txns)} rows x {len(txns.columns)} cols\")\nprint(f\"Columns: {txns.columns.tolist()}\")\ntxns.head(3)")

code("monthly_agg = pd.read_parquet(\"data/transactions_monthly_agg.parquet\")\nmonthly_agg[\"txn_month\"] = pd.to_datetime(monthly_agg[\"txn_month\"])\nprint(f\"transactions_monthly_agg.parquet: {len(monthly_agg)} rows x {len(monthly_agg.columns)} cols\")\nprint(f\"Columns: {monthly_agg.columns.tolist()}\")\nmonthly_agg.head(3)")

md("## 2. Schema, missingness, and zero-activity population")

code("print(\"=== Missingness check ===\")\nfor name, df in [(\"Customers\", customers), (\"Transactions\", txns), (\"Monthly Agg\", monthly_agg)]:\n    nulls = df.isna().sum().sum()\n    print(f\"  {name}: {nulls} nulls across all columns\")")

code("# Zero-activity customers\nactive_ids = set(txns[\"customer_id\"].unique())\nall_ids = set(customers[\"customer_id\"])\nzero_activity = sorted(all_ids - active_ids)\nprint(f\"Total customers: {len(all_ids)}\")\nprint(f\"Customers with >= 1 transaction: {len(active_ids)}\")\nprint(f\"Zero-activity customers: {len(zero_activity)}\")\n\nza = customers[customers[\"customer_id\"].isin(zero_activity)]\nprint(f\"Zero-activity with churned=1: {za['churned'].sum()}/{len(za)}\")")

md("## 3. Distribution shape \u2014 transaction amount")

code("amt = txns[\"amount\"]\nprint(\"=== Transaction amount distribution ===\")\nprint(f\"Count: {len(amt)}\")\nprint(f\"Mean:  ${amt.mean():.2f}\")\nprint(f\"Median: ${amt.median():.2f}\")\nprint(f\"Std:   ${amt.std():.2f}\")\nprint(f\"Min:   ${amt.min():.2f}\")\nprint(f\"Q1:    ${amt.quantile(0.25):.2f}\")\nprint(f\"Q3:    ${amt.quantile(0.75):.2f}\")\nprint(f\"Max:   ${amt.max():.2f}\")\nprint(f\"Skewness: {amt.skew():.4f}\")\n\nq1, q3 = amt.quantile(0.25), amt.quantile(0.75)\niqr = q3 - q1\nupper = q3 + 1.5*iqr\nlower = q1 - 1.5*iqr\noutliers = amt[(amt < lower) | (amt > upper)]\nprint(f\"\\n1.5xIQR outlier rule:\")\nprint(f\"  Lower bound: ${lower:.2f}\")\nprint(f\"  Upper bound: ${upper:.2f}\")\nprint(f\"  Outliers: {len(outliers)} ({len(outliers)/len(amt)*100:.1f}%)\")\nprint(f\"  All above upper bound: {(amt > upper).sum()}/{len(outliers)}\")")

code("fig, axes = plt.subplots(1, 2, figsize=(14, 4))\naxes[0].hist(amt, bins=80, edgecolor=\"white\", color=\"steelblue\")\naxes[0].set_title(\"Transaction amount distribution\")\naxes[0].set_xlabel(\"Amount ($)\")\naxes[0].set_ylabel(\"Frequency\")\n\naxes[1].boxplot(amt, vert=False)\naxes[1].set_title(\"Box plot\")\naxes[1].set_xscale(\"log\")\naxes[1].set_xlabel(\"Amount ($, log scale)\")\nplt.tight_layout()\nplt.show()")

md("## 4. Churn rate breakdowns")

code("print(\"=== Overall churn rate ===\")\nchurned = customers[\"churned\"].sum()\ntotal = len(customers)\nprint(f\"Churned: {churned}/{total} = {churned/total*100:.2f}%\")\n\nactive_cust = customers[customers[\"customer_id\"].isin(active_ids)]\nactive_ch = active_cust[\"churned\"].sum()\nactive_total = len(active_cust)\nprint(f\"\\nAmong customers with at least one transaction:\")\nprint(f\"Churned: {active_ch}/{active_total} = {active_ch/active_total*100:.2f}%\")")

code("print(\"=== Churn by acquisition channel ===\")\nprint(customers.groupby(\"acquisition_channel\")[\"churned\"].agg([\"count\", \"sum\", \"mean\"]).assign(rate=lambda x: x[\"mean\"]*100).to_string())\nprint(\"\\n=== Churn by region ===\")\nprint(customers.groupby(\"region\")[\"churned\"].agg([\"count\", \"sum\", \"mean\"]).assign(rate=lambda x: x[\"mean\"]*100).to_string())")

md("## 5. Hypothesis tests")

code("from scipy.stats import chi2_contingency, mannwhitneyu\n\ndef cramers_v(table):\n    chi2 = chi2_contingency(table)[0]\n    n = table.values.sum()\n    k = min(table.shape)\n    return np.sqrt(chi2 / n / (k - 1)) if n > 0 and k > 1 else 0.0\n\ndef rank_biserial(u, n1, n2):\n    return 1 - (2 * u) / (n1 * n2)\n\nprint(\"--- Acquisition channel vs churn ---\")\ntable = pd.crosstab(customers[\"acquisition_channel\"], customers[\"churned\"])\nchi2, p, dof, exp = chi2_contingency(table)\ncv = cramers_v(table)\nprint(f\"Chi-square: chi2={chi2:.4f}, p={p:.4f}, Cramer's V={cv:.4f}\")\nprint(f\"Verdict: {'Significant' if p < 0.05 else 'Not significant'} at alpha=0.05\")\nprint(\"Leakage: Not tainted (static attribute)\")\n\nprint(\"\\n--- Region vs churn ---\")\ntable = pd.crosstab(customers[\"region\"], customers[\"churned\"])\nchi2, p, dof, exp = chi2_contingency(table)\ncv = cramers_v(table)\nprint(f\"Chi-square: chi2={chi2:.4f}, p={p:.4f}, Cramer's V={cv:.4f}\")\nprint(f\"Verdict: {'Significant' if p < 0.05 else 'Not significant'} at alpha=0.05\")\nprint(\"Leakage: Not tainted (static attribute)\")")

code("# Customer-level monetary analysis\ncust_amt = txns.groupby(\"customer_id\")[\"amount\"].sum().reset_index()\ncust_amt.columns = [\"customer_id\", \"total_amount\"]\nmerged_mon = customers[[\"customer_id\", \"churned\"]].merge(cust_amt, on=\"customer_id\", how=\"left\")\nmerged_mon[\"total_amount\"] = merged_mon[\"total_amount\"].fillna(0)\n\nc_vals = merged_mon[merged_mon[\"churned\"]==1][\"total_amount\"]\nnc_vals = merged_mon[merged_mon[\"churned\"]==0][\"total_amount\"]\nu_stat, p_val = mannwhitneyu(c_vals, nc_vals, alternative=\"two-sided\")\nrb = rank_biserial(u_stat, len(c_vals), len(nc_vals))\nprint(\"--- Total amount vs churn ---\")\nprint(f\"Mann-Whitney U: U={u_stat:.1f}, p={p_val:.2e}\")\nprint(f\"Rank-biserial correlation: {rb:.4f}\")\nprint(f\"Median churned: ${c_vals.median():.2f}\")\nprint(f\"Median non-churned: ${nc_vals.median():.2f}\")\n\nprint(\"\\n--- Return rate vs churn ---\")\ncust_ret = txns.groupby(\"customer_id\").agg(total_txns=(\"is_returned\", \"count\"), return_count=(\"is_returned\", \"sum\")).reset_index()\ncust_ret[\"return_rate\"] = cust_ret[\"return_count\"] / cust_ret[\"total_txns\"]\nmerged_ret = customers[[\"customer_id\", \"churned\"]].merge(cust_ret, on=\"customer_id\", how=\"left\")\nmerged_ret[\"return_rate\"] = merged_ret[\"return_rate\"].fillna(0)\nrc_vals = merged_ret[merged_ret[\"churned\"]==1][\"return_rate\"]\nr_nc_vals = merged_ret[merged_ret[\"churned\"]==0][\"return_rate\"]\nu2, p2 = mannwhitneyu(rc_vals, r_nc_vals, alternative=\"two-sided\")\nrb2 = rank_biserial(u2, len(rc_vals), len(r_nc_vals))\nprint(f\"Mann-Whitney U: U={u2:.1f}, p={p2:.2e}\")\nprint(f\"Rank-biserial correlation: {rb2:.4f}\")")

code("# Days since last transaction \u2014 diagnostic only\nasof = txns[\"txn_timestamp\"].max()\nprint(f\"As-of date: {asof}\")\n\nlast_txn = txns.groupby(\"customer_id\")[\"txn_timestamp\"].max().reset_index()\nlast_txn[\"days_since\"] = (asof - last_txn[\"txn_timestamp\"]).dt.days\nmerged_dsl = customers[[\"customer_id\", \"churned\"]].merge(last_txn[[\"customer_id\", \"days_since\"]], on=\"customer_id\", how=\"left\")\n\nnc = merged_dsl[merged_dsl[\"churned\"]==0][\"days_since\"].dropna()\nac = merged_dsl[merged_dsl[\"churned\"]==1][\"days_since\"].dropna()\nprint(f\"\\nNon-churned: n={len(nc)}, min={nc.min():.0f}d, max={nc.max():.0f}d, mean={nc.mean():.1f}d\")\nprint(f\"Churned (active): n={len(ac)}, min={ac.min():.0f}d, max={ac.max():.0f}d, mean={ac.mean():.1f}d\")\nprint(f\"\\nWARNING: Complete separation by construction.\")\nprint(\"The churn label = no purchase in trailing 90 days.\")\nprint(\"This variable = days since last txn relative to same as-of date.\")\nprint(\"They are the same thing. This is LEAKAGE, not prediction.\")")

md("## 6. Monthly transaction-volume trend")

code("txns[\"txn_month\"] = txns[\"txn_timestamp\"].dt.to_period(\"M\").dt.to_timestamp()\nmonthly = txns.groupby(\"txn_month\").agg(\n    txn_count=(\"amount\", \"count\"),\n    total_amount=(\"amount\", \"sum\"),\n    unique_customers=(\"customer_id\", \"nunique\")\n).reset_index().sort_values(\"txn_month\")\n\nprint(f\"Period: {monthly.iloc[0]['txn_month'].strftime('%Y-%m')} to {monthly.iloc[-1]['txn_month'].strftime('%Y-%m')}\")\nprint(f\"Months: {len(monthly)}\")\nfirst_txn = monthly.iloc[0][\"txn_count\"]\nlast_txn = monthly.iloc[-1][\"txn_count\"]\nprint(f\"Trend: {first_txn} -> {last_txn} transactions (~{last_txn/first_txn:.0f}x)\")\nprint(f\"Amount: ${monthly.iloc[0]['total_amount']:.2f} -> ${monthly.iloc[-1]['total_amount']:.2f}\")\nprint(f\"Customers: {monthly.iloc[0]['unique_customers']} -> {monthly.iloc[-1]['unique_customers']}\")\nprint(\"\\nConclusion: Strong upward trend \u2014 non-stationarity is real. Time-based split recommended.\")")

code("fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)\nmonths_str = [r[\"txn_month\"].strftime(\"%Y-%m\") for _, r in monthly.iterrows()]\n\naxes[0].plot(range(len(monthly)), monthly[\"txn_count\"], marker=\"o\", color=\"steelblue\")\naxes[0].set_ylabel(\"Transaction count\")\naxes[0].set_title(\"Monthly transaction volume\")\n\naxes[1].plot(range(len(monthly)), monthly[\"total_amount\"], marker=\"o\", color=\"green\")\naxes[1].set_ylabel(\"Total amount ($)\")\n\naxes[2].plot(range(len(monthly)), monthly[\"unique_customers\"], marker=\"o\", color=\"orange\")\naxes[2].set_ylabel(\"Unique customers\")\naxes[2].set_xlabel(\"Month\")\n\nfor ax in axes:\n    ax.set_xticks(range(0, len(monthly), 3))\n    ax.set_xticklabels([months_str[i] for i in range(0, len(monthly), 3)], rotation=45)\n\nplt.tight_layout()\nplt.show()")

md("## 7. Multi-source agreement")

code("# Reaggregate row-level to customer x month\nrow_agg = txns.groupby([\"customer_id\", \"txn_month\"]).agg(\n    txn_count=(\"amount\", \"count\"),\n    total_amount=(\"amount\", \"sum\"),\n    return_count=(\"is_returned\", \"sum\")\n).reset_index()\n\nrow_monthly = row_agg.groupby(\"txn_month\").agg(\n    row_txns=(\"txn_count\", \"sum\"),\n    row_amt=(\"total_amount\", \"sum\"),\n    row_cust=(\"customer_id\", \"nunique\")\n).reset_index()\n\nparq_monthly = monthly_agg.groupby(\"txn_month\").agg(\n    parq_txns=(\"txn_count\", \"sum\"),\n    parq_amt=(\"total_amount\", \"sum\"),\n    parq_cust=(\"customer_id\", \"nunique\")\n).reset_index()\n\nmerged = row_monthly.merge(parq_monthly, on=\"txn_month\", how=\"outer\").fillna(0).sort_values(\"txn_month\")\nmerged[\"match\"] = merged[\"row_txns\"] == merged[\"parq_txns\"]\n\nprint(f\"Months compared: {len(merged)}\")\nprint(f\"Exact match: {merged['match'].sum()} / {len(merged)}\")\nprint(f\"Diverged: {len(merged) - merged['match'].sum()}\")\n\ndiv = merged[~merged[\"match\"]]\nfor _, r in div.iterrows():\n    diff_pct = (r[\"row_txns\"] - r[\"parq_txns\"]) / r[\"parq_txns\"] * 100\n    print(f\"\\n  {r['txn_month'].strftime('%Y-%m')}:\")\n    print(f\"    Row-level: {r['row_txns']} txns, ${r['row_amt']:.2f}, {r['row_cust']} cust\")\n    print(f\"    Parquet:   {r['parq_txns']} txns, ${r['parq_amt']:.2f}, {r['parq_cust']} cust\")\n    print(f\"    Gap:       {diff_pct:.1f}%\")")

code("fig, ax = plt.subplots(figsize=(14, 5))\nmonths = [m.strftime(\"%Y-%m\") for m in merged[\"txn_month\"]]\nax.plot(months, merged[\"row_txns\"], marker=\"o\", label=\"Row-level agg\", color=\"steelblue\")\nax.plot(months, merged[\"parq_txns\"], marker=\"s\", label=\"Parquet extract\", color=\"orange\")\nax.set_xticks(range(0, len(months), 3))\nax.set_xticklabels([months[i] for i in range(0, len(months), 3)], rotation=45)\nax.set_ylabel(\"Transaction count\")\nax.set_title(\"Monthly transaction count: row-level vs parquet\")\nax.legend()\nplt.tight_layout()\nplt.show()")

md("## 8. Summary\n\n| Finding | Detail |\n|---|---|\n| **Churn rate** | 13.47% overall, 8.53% among active customers |\n| **Zero-activity** | 81 customers, all churned \u2014 distinct segment, not missing data |\n| **Amount distribution** | Heavily right-skewed (mean $49.72, median $33.82, max $1,684.21) |\n| **Channel** | Not significant (p=0.12). Organic highest (15.27%), paid_search lowest (10.21%) |\n| **Region** | Not significant (p=0.29). East highest (16.36%) |\n| **Total amount** | Significant (p\u22480), large effect. Non-churned spend more |\n| **Return rate** | Significant (p\u22480), small effect |\n| **Days since last txn** | **Leakage-tainted** \u2014 circular with label definition |\n| **Time trend** | Strongly upward (~1,231\u00d7 growth over 30 months) |\n| **Multi-source** | 29/30 months match; July 2026 cutoff anomaly (~24% gap) |\n\n### Recommended model family\n**Gradient-boosted decision trees (LightGBM/XGBoost)** \u2014 handles mixed types, skewed variables, imbalance, and nonlinear interactions.\n\n### Key exclusions\n- `days_since_last_transaction` \u2014 leakage-tainted\n- Any trailing-90-day windowed features \u2014 same circularity\n\nSee `MODEL_RECOMMENDATION.md` and `DATA_ISSUES.md` for full details.")

# Build notebook
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "cells": cells,
}

with open("notebooks/eda_churn.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Notebook written: {len(cells)} cells")
print("Done.")