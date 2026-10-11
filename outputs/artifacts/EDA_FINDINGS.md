# EDA Findings — Verified

**Status: VERIFIED** — every numeric claim below is reproducible from raw sources via `scripts/verify_findings.py`.

---

## 1. Schema and basic shape

| Source | Rows | Columns | Details |
|---|---|---|---|
| `customers.csv` | 1,500 | 5 | customer_id, signup_date, acquisition_channel, region, churned |
| `transactions.db` | 11,742 | 6 | customer_id, txn_timestamp, category, channel, amount, is_returned |
| `transactions_monthly_agg.parquet` | 8,086 | 5 | customer_id, txn_month, txn_count, total_amount, return_count |

All columns in all three sources have zero null values.

---

## 2. Zero-activity customer population

- **81 customers** appear in `customers.csv` but have no rows in `transactions.db`.
- All 81 have `churned = 1`.
- These are **not** missing transaction data — they are a legitimate zero-activity segment (signed up, never transacted).
- Excluding them, the churn rate among customers with at least one transaction is 121 / 1,419 = **8.53%**.
- Including them, the headline churn rate is 202 / 1,500 = **13.47%**.

---

## 3. Distribution shape — transaction amount

| Stat | Value |
|---|---|
| Count | 11,742 |
| Mean | $49.72 |
| Median | $33.82 |
| Std | $55.24 |
| Min | $3.00 |
| Q1 | $18.36 |
| Q3 | $61.39 |
| Max | $1,684.21 |
| Skewness | 6.11 (heavily right-skewed) |

- **Outlier rule**: 1.5× IQR. Lower bound = −$46.18, Upper bound = $125.93.
- **Outlier count**: 783 (6.7% of all transactions), all above the upper bound (no low-end outliers).
- **Interpretation**: mean ($49.72) >> median ($33.82), skewness 6.11 — heavily right-skewed. Typical for e-commerce: many small purchases, a long tail of large ones.
- **Implication**: Use median/IQR for summary stats rather than mean/std. Tree-based models handle this naturally; linear models would need transformation.

---

## 4. Categorical breakdowns and churn rates

### Overall churn
- **Total customers**: 1,500
- **Churned**: 202
- **Not churned**: 1,298
- **Churn rate**: **13.47%**

### By acquisition channel

| Channel | Total | Churned | Churn Rate |
|---|---|---|---|
| organic | 609 | 93 | 15.27% |
| paid_search | 431 | 44 | 10.21% |
| referral | 295 | 41 | 13.90% |
| social | 165 | 24 | 14.55% |

### By region

| Region | Total | Churned | Churn Rate |
|---|---|---|---|
| east | 385 | 63 | 16.36% |
| north | 381 | 47 | 12.34% |
| west | 380 | 47 | 12.37% |
| south | 354 | 45 | 12.71% |

---

## 5. Hypothesis test results

### Acquisition channel vs churn
- **Test**: Chi-square test of independence
- **χ²**: 5.8387, **p** = 0.120 (not significant at α = 0.05)
- **Effect size**: Cramér's V = 0.0624 (small)
- **Direction**: Organic highest (15.27%), paid_search lowest (10.21%)
- **Leakage**: Not tainted (static attribute)

### Region vs churn
- **Test**: Chi-square test of independence
- **χ²**: 3.7571, **p** = 0.289 (not significant at α = 0.05)
- **Effect size**: Cramér's V = 0.05 (small)
- **Direction**: East highest (16.36%), north lowest (12.34%)
- **Leakage**: Not tainted (static attribute)

### Total amount (customer-level) vs churn
- **Test**: Mann-Whitney U test (non-parametric; amount is strongly right-skewed)
- **U**: 61626.5, **p** ≈ 7.2 × 10⁻³⁴ (significant)
- **Effect size**: rank-biserial correlation = 0.53 (large)
- **Direction**: Non-churned customers have higher median total amount ($364.38) than churned ($71.12)
- **Leakage**: Not tainted (all-time aggregate)

### Return rate (customer-level) vs churn
- **Test**: Mann-Whitney U test (non-parametric; return rate is zero-inflated)
- **U**: 110279.0, **p** ≈ 9.3 × 10⁻⁶ (significant)
- **Effect size**: rank-biserial correlation = 0.16 (small)
- **Direction**: Non-churned customers have very slightly higher median return rates; both medians round to 0.00
- **Leakage**: Not tainted (all-time proportion)

### Days since last transaction (diagnostic only)
- **Test**: Descriptive + Mann-Whitney U (diagnostic — not a usable predictor)
- **U**: 157058.0, **p** ≈ 3.7 × 10⁻⁷⁴
- **Separation**: Non-churned: 0–90 days; churned (active): 91–365 days — complete separation by construction
- **Leakage**: **Tainted** — this variable is circular with the label definition
- **Verdict**: Do not use in any predictive model

---

## 6. Monthly transaction-volume trend

The dataset spans **February 2024 to July 2026** (30 months).

| Metric | First month (Feb 2024) | Last month (Jul 2026) | Growth |
|---|---|---|---|
| Transaction count | 1 | 1,231 | ~1,231× |
| Total amount | $25.03 | $62,084.62 | ~2,500× |
| Unique customers | 1 | 787 | ~800× |

- The trend is **consistently upward** across all three metrics. The direction is monotonic in the broad sense (strong positive trend with only minor local dips).
- **Non-stationarity is real and material.** A random train/test split would mix very different volume regimes. A time-based split is recommended.

---

## 7. Multi-source agreement

| Metric | Value |
|---|---|
| Matched months (exact agreement) | 29 of 30 |
| Diverged months | 1 (July 2026) |
| Extra customer-months in row-level agg | 102 |
| Extra customer-months in parquet | 0 |

**July 2026 details**:
- Row-level: 1,231 transactions, $62,084.62 total, 787 customers
- Parquet: 994 transactions, $50,116.67 total, 685 customers
- Gap: 237 transactions (23.8% difference)

**Interpretation**: 29 of 30 months show perfect agreement. The July 2026 divergence is consistent with the parquet having been generated with a cutoff before month-end while the row-level table captures the full month. This is a source-alignment warning but confined to one month.

---

## 8. Summary for modeling

1. **Churn rate 13.5%** — moderately imbalanced. Accuracy is misleading.
2. **Amount heavily right-skewed** — tree models or transformed inputs recommended.
3. **81 zero-activity customers** — distinct segment, all churned. Inclusion/exclusion is a business decision.
4. **Days since last transaction** — leakage-tainted, excluded from usable features.
5. **Channel and region** — visible churn rate gaps but not statistically significant at α = 0.05.
6. **Customer-level monetary amount** — significant and large effect (non-churned spend more).
7. **Return rate** — statistically significant but small effect.
8. **Non-stationarity** — strong upward trend (~1,231× growth); time-based split recommended.
9. **Multi-source agreement** — 29/30 months match; July 2026 cutoff anomaly exists but is isolated.