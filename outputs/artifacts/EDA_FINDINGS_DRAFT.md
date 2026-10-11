# EDA Findings — Draft (Stage 0)

**Status: PROVISIONAL — first-pass draft generated directly from raw data sources.**
This document is best-effort and may contain errors. Every claim below should be reviewed and
corrected by the learner in `eda_review.md`. Low-confidence claims are marked individually.

Companion files: `notebooks/eda_churn.ipynb` (the runnable notebook), `MODEL_RECOMMENDATION_DRAFT.md`,
`DATA_ISSUES_DRAFT.md`.

**As-of-date assumption**: The last observed transaction is 2026-07-31 23:50:29. This notebook
uses that maximum `txn_timestamp` as a proxy as-of date. The actual as-of date used for the
churn label definition should be confirmed by the learner. **If the actual as-of date differs,
all "days since last transaction" calculations shift accordingly.**

---

## 1. Schema and basic shape

| Source | Rows | Columns | Details |
|---|---|---|---|
| `customers.csv` | 1,500 | 5 | customer_id, signup_date, acquisition_channel, region, churned |
| `transactions.db` | 11,742 | 6 | customer_id, txn_timestamp, category, channel, amount, is_returned |
| `transactions_monthly_agg.parquet` | 8,086 | 5 | customer_id, txn_month, txn_count, total_amount, return_count |

**Confidence: HIGH** — counts are computed directly and should reproduce exactly.

**Important schema note**: `transactions.db` has no `quantity` column (contrary to what some
prior documentation may suggest). The only numeric transaction-level columns are `amount` and `is_returned`.

---

## 2. Missingness

- **All three sources**: Zero null values in every column. **(HIGH confidence — programmatically checked.)**
- **Zero-activity customers**: 81 customers appear in `customers.csv` with zero rows in
  `transactions.db`. These are **not** missing transaction data — they are an **81-customer
  zero-activity population** (signed up, never transacted). All 81 have churned=1.
  **(HIGH confidence — counted directly from data.)**
- **No genuinely missing values exist in any source.** The only "absence" is the zero-activity
  population, which is a legitimate customer segment, not a data-quality gap.

---

## 3. Distribution shape — numeric columns

### Transaction amount (transactions.db)

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
| Skewness | > 2.0 (heavily right-skewed) |

- **Outlier rule**: 1.5× IQR. Lower bound = -$46.18, Upper bound = $125.93.
- **Outlier count**: 783 (6.7% of all transactions), all above the upper bound (no low-end outliers).
- **Interpretation**: mean >> median + skewness > 0.5 = **heavily right-skewed**. Typical for
  e-commerce: many small purchases, a long tail of large ones.
- **Implication**: Use median/IQR for summary stats, not mean/std. Tree-based models handle
  this naturally; linear models would need transformation.
- **(HIGH confidence for mean/median/outlier count — computed. MEDIUM confidence for the best**
- **downstream transformation — domain judgment.)**

### is_returned (transactions.db, binary)

| Value | Count | Percent |
|---|---|---|
| 0 (not returned) | 11,151 | 94.97% |
| 1 (returned) | 591 | 5.03% |

- Overall return rate: **5.0%**. This is relatively low for e-commerce.
- **(HIGH confidence — counted from data.)**

### Monthly aggregations (parquet)

| Column | Mean | Median | Min | Max | Interpretation |
|---|---|---|---|---|---|
| txn_count | 1.42 | 1.0 | 1 | 6 | Most customers have 1-2 txns/month; right-skewed |
| total_amount | $70.72 | $48.32 | $3.00 | $1,753.23 | Right-skewed (mirrors amount distribution) |
| return_count | 0.07 | 0.0 | 0 | 3 | Most months have zero returns; heavily zero-inflated |

- **(HIGH confidence — computed from parquet.)**

---

## 4. Categorical breakdowns and churn rate

### Overall churn rate

- **Total customers**: 1,500
- **Churned**: 202 (churned=1)
- **Not churned**: 1,298 (churned=0)
- **Churn rate**: **13.47%**
- **(HIGH confidence — counted from CSV.)**

**Important**: All 81 zero-activity customers have churned=1. The churn rate among
**customers with at least one transaction** is 121 / 1,419 = **8.53%**. The 13.47% overall
figure includes the zero-activity population. The learner should decide whether to report
one or both based on modelling context.

### Churn by acquisition channel

| Channel | Total | Churned | Churn Rate |
|---|---|---|---|
| organic | 609 | 93 | 15.27% |
| paid_search | 431 | 44 | 10.21% |
| referral | 295 | 41 | 13.90% |
| social | 165 | 24 | 14.55% |

- Organic has the highest churn rate (~15.3%); paid_search the lowest (~10.2%).
- The ~5pp gap between organic and paid_search is the most notable inter-channel difference.
- **(LOW-MEDIUM confidence — these are raw rates, not tested for significance.)**

### Churn by region

| Region | Total | Churned | Churn Rate |
|---|---|---|---|
| east | 385 | 63 | 16.36% |
| north | 381 | 47 | 12.34% |
| west | 380 | 47 | 12.37% |
| south | 354 | 45 | 12.71% |

- East has a notably higher churn rate (~16.4%) than the other three (~12-13%).
- The ~4pp east vs rest gap is a candidate driver for formal testing.
- **(LOW-MEDIUM confidence — raw rates, not tested.)**

### Transaction-level churn by category and channel

These show much smaller differences and may not be meaningful drivers:

| Category | Churn Rate | Channel | Churn Rate |
|---|---|---|---|
| home | 7.97% | web | 6.84% |
| electronics | 7.17% | store | 6.82% |
| apparel | 7.09% | mobile_app | 6.68% |
| sports | 6.65% | | |
| beauty | 6.33% | | |
| grocery | 5.46% | | |

- Differences are small (range: 5.5%-8.0% by category, 6.7%-6.8% by channel).
- **(LOW CONFIDENCE — these are transaction-level churn rates, which violate independence)**
- **(because one customer contributes many transactions.)**

---

## 5. Days since last transaction — the strongest candidate predictor

This candidate feature shows **near-perfect separation** between churned and non-churned customers:

| Group | Mean | Median | Min | Max | n |
|---|---|---|---|---|---|
| Not churned | 28.6 days | 23 days | 0 days | 90 days | 1,298 |
| Churned (active only) | 132.5 days | 113 days | 91 days | 365 days | 121 |

- Non-churned customers all have ≤ 90 days since last transaction (by definition of the label).
- Churned customers all have ≥ 91 days since last transaction.
- Mann-Whitney U test: p ≈ 0 (complete separation).
- **This is the single most powerful candidate predictor found.**
- **(HIGH confidence on the numbers — LOW confidence on whether this is a legitimate predictor;**
- **see DATA_ISSUES_DRAFT.md and the learner's review.)**

---

## 6. Monthly transaction-volume trend

The dataset spans **February 2024 to July 2026** (30 months).

| Metric | First month (Feb 2024) | Last month (Jul 2026) | Growth |
|---|---|---|---|
| Transaction count | 1 | 1,231 | ~1,200× |
| Total amount | $25 | $62,085 | ~2,500× |
| Unique customers | 1 | 787 | ~800× |

- The trend is **consistently upward** across all three metrics. The growth appears roughly
  exponential in the first 12-18 months, then continues linearly upward.
- **Non-stationarity is real and material.** A random train/test split would mix very different
  volume regimes.
- **(HIGH confidence — computed month by month from data. The trend direction is unambiguous.)**

---

## 7. Multi-source agreement

| Metric | Value |
|---|---|
| Matched customer-months (both sources) | 8,086 |
| Only in row-level agg (Jul 2026 only) | 102 |
| Only in parquet | 0 |
| Rows with amount disagreement (>$0.01) | 110 of 8,086 (1.4%) |
| All disagreements in month | July 2026 |

- **29 of 30 months show perfect agreement.**
- July 2026: row-level has 1,231 transactions vs parquet's 994; $62,085 vs $50,117 (24% gap).
- The 102 extra customer-months in the row-level table come from customers whose last
  transaction was July 26-31, 2026 — the parquet likely used a cutoff before month-end.
- **(HIGH confidence on the comparison — computed from data. MEDIUM confidence on the cause —**
- **inferred from timestamp patterns, not confirmed.)**

---

## 8. Provisional summary of findings for modeling

1. **Churn rate 13.5%** — moderately imbalanced. Accuracy is misleading.
2. **Amount right-skewed** — tree models or transformed inputs needed.
3. **81 zero-activity customers** — distinct population, all churned. Inclusion decision matters.
4. **Days since last txn** — nearly perfect predictor (circularity risk — see DATA_ISSUES).
5. **Channel and region** — candidate drivers with visible gaps (organic vs paid_search; east vs rest).
6. **Non-stationarity** — strong upward trend; time-based split needed.
7. **Multi-source agreement** — generally good (29/30 months), but July 2026 cutoff anomaly exists.
8. **Return rate ~5%** — small difference by churn status (churned slightly higher).

---

*See `MODEL_RECOMMENDATION_DRAFT.md` for the provisional model family recommendation and
`DATA_ISSUES_DRAFT.md` for the leakage, imbalance, non-stationarity, and multi-source flags.*