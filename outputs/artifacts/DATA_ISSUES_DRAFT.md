# Data Issues — Draft (Stage 0)

**Status: PROVISIONAL — first-pass candidate data-issue flags.**
These are issues found or suspected during Stage 0 EDA. Every flag should be verified by the
learner's review in `eda_review.md`. This is NOT a substitute for formal verification.

Companion: `notebooks/eda_churn.ipynb`, `EDA_FINDINGS_DRAFT.md`, `MODEL_RECOMMENDATION_DRAFT.md`.

**As-of-date assumption**: The maximum `txn_timestamp` in the dataset (2026-07-31 23:50:29) is used
as a proxy as-of date. The actual as-of date for the churn label definition needs to be confirmed.

---

## Flag 1: Days since last transaction — near-perfect predictor (and potential leakage risk)

**Severity: HIGH — this is the most important finding in this draft.**

### What we found
The `days_since_last_transaction` candidate feature separates churned and non-churned customers
almost perfectly:
- **Non-churned**: 0-90 days since last txn (mean 28.6d, median 23d)
- **Churned (with transactions)**: 91-365 days since last txn (mean 132.5d, median 113d)
- Mann-Whitney U test: p ≈ 0.0 (complete separation)

### Why this matters
This candidate predictor is suspiciously powerful — far stronger than any other feature checked.
The churn label is defined as "no transaction in the trailing 90 days before the as-of date."
The `days_since_last_txn` feature is derived from exactly that same window.

**Hypothesis for the learner to evaluate**: If the churn label definition uses a trailing-90-day
window, and `days_since_last_txn` is also computed relative to the same as-of date, then this
feature is not "predicting" churn — it's circularly derived from the same information that
defines the label. A model that relies on it would fail in production when deployed on new
customers where we don't yet know whether they'll have a 91-day gap.

### Candidate tainted variables (for learner to confirm)
- `days_since_last_transaction`: Potentially circular — the separation is definitional, not predictive
- Any trailing-90-day windowed aggregates (spend, count, etc.): Same issue if computed over the same window

### NOT tainted (legitimate candidates)
- `acquisition_channel`, `region`: Static attributes, no temporal overlap
- `signup_date` / `account_tenure`: Not derived from the label window
- `total_historical_txn_count`: All-time count, not windowed
- `return_rate`: All-time proportion (needs confirmation it's not windowed)
- Transaction behavior features: Category mix, channel preference, etc.

### Evidence
This is partly a logical check (label definition overlap) and partly empirical (the separation is
suspiciously perfect). The learner's review should determine whether the leak is real.

---

## Flag 2: Class imbalance — 13.5% churn rate

**Severity: MEDIUM**

### Actual numbers
- Churn rate: **13.47%** (202 churned / 1,500 total)
- Among customers with transactions: **8.53%** (121 / 1,419)
- Majority class: **86.53%** not churned (1,298 / 1,500)

### What this means for modeling
- **Accuracy is misleading**: A model that always predicts "not churned" achieves ~86.5% accuracy
  while being useless for retention marketing.
- **Recommended metrics**: Precision, recall, F1, and PR-AUC (precision-recall AUC, not ROC-AUC,
  which can overstate performance on imbalanced data).
- **Class weighting**: Both XGBoost and LightGBM offer `scale_pos_weight` / `class_weight`
  parameters. A `scale_pos_weight` of ~6.4 (1,298 / 202) would balance the classes.
- **Business context**: The retention marketing team cares about catching likely churners
  (high recall) without flooding outreach with false positives (precision matters too).

### Confidence
**HIGH** on the churn rate number.
**MEDIUM** on metric implications (standard practice, but the exact tradeoff depends on the team's
cost structure for false negatives vs false positives).

---

## Flag 3: Non-stationarity — strong upward volume trend

**Severity: MEDIUM-HIGH**

### What the data shows
Monthly transaction volume grew consistently over 30 months:

| Period | Mean Monthly Txns | Mean Monthly Amount |
|---|---|---|
| Feb-Dec 2024 (first 11 months) | ~44 | ~$2,114 |
| Jan-Jul 2026 (last 7 months) | ~960 | ~$47,363 |

- Transaction count grew from 1/month to 1,231/month (~1,200× growth)
- The trend is monotonic and consistently upward across all three metrics (txn count, unique
  customers, total amount)

### Modelling consequence
- A **random train/test split** would mix very different volume regimes — a customer from early
  2024 (when the platform had 1-5 txns/month) might appear alongside a customer from mid-2026
  (1,000+ txns/month), and the model would overstate its ability to generalize.
- A **time-based split** (train on earlier months, test on later months) is strongly recommended.
- Feature distributions (amount, category mix, etc.) may also drift over time — worth checking
  whether the early vs late populations differ beyond volume.

### Confidence
**HIGH** on the trend direction and magnitude (computed from data).
**MEDIUM** on the distribution-drift consequence (suspected but not yet checked).

---

## Flag 4: Multi-source disagreement — July 2026 cutoff anomaly

**Severity: LOW-MEDIUM**

### What the comparison found
- **29 of 30 months**: Perfect agreement between `transactions.db` reaggregated and
  `transactions_monthly_agg.parquet` at the aggregated (monthly) level.
- **July 2026**: The only disagreement:
  - Row-level table: 1,231 transactions, 787 customers, $62,085 total amount
  - Parquet extract: 994 transactions, 685 customers, $50,117 total amount
  - Gap: 237 transactions (24%), 102 customers (15%), $11,968 total amount (24%)
- The 102 customer-months only in the row-level table all involve customers whose last
  transaction was July 26-31, 2026.

### Interpretation
The parquet extract appears to have been generated with a cutoff date sometime before the end
of July 2026, while the row-level table captures the full month. This is consistent with a
pipeline that processes monthly aggregates up to a cutoff before month-end, while the raw
transaction table receives real-time or batch-upserted data through the end of the month.

### Modelling consequence
- If models use the parquet for training and the row-level table for inference (or vice versa),
  the July anomaly could cause training/serving skew for customers near month boundaries.
- The effect is confined to one month and ~100 customers, so impact is likely small — but
  the pipeline team should align on which source is authoritative.

### Confidence
**HIGH** on the comparison result (computed from data).
**MEDIUM** on the cause (plausible inference, not confirmed).
**LOW** on whether this actually affects model performance (would need to test).

---

## Flag 5: Zero-activity customer population (81 customers)

**Severity: INFORMATIONAL**

### What it is
81 customers (5.4% of total) have signed up but never transacted. They have no rows in
`transactions.db` at all.

### Key facts
- All 81 have churned=1 (by definition — they have never transacted, so they certainly haven't
  transacted in the trailing 90 days)
- They cannot have any transaction-based features (amount, count, category, channel, return rate)
- The model population decision — include them (with zero-filled features), exclude them, or
  model them separately — is a business-driven choice

### Impact on churn rate
- Including them: 13.47% churn
- Excluding them: 8.53% churn among customers who have ever transacted
- This ~5pp difference is material. The learner should decide which churn rate to report
  as the "headline" for modelling.

### Confidence
**HIGH** on the count and churn status (computed from data).
**N/A** on what to do with them (business decision, not an analytical finding).

---

## Summary of flags by severity

| # | Issue | Severity | Evidence status |
|---|---|---|---|
| 1 | Days-since-last-txn: near-perfect predictor (potential label leakage) | HIGH | Empirical (suspiciously perfect separation) + logical (label definition overlap) |
| 2 | Class imbalance: 13.5% churn rate | MEDIUM | Counted from CSV |
| 3 | Non-stationarity: ~1,200× volume growth over 30 months | MEDIUM-HIGH | Computed month by month from transactions |
| 4 | Multi-source disagreement: July 2026 cutoff anomaly (24% gap) | LOW-MEDIUM | Computed comparison confirmed |
| 5 | Zero-activity population: 81 customers, all churned=1 | INFORMATIONAL | Counted from data |

---

*This document is a draft. Every flag should be reviewed and corrected in `eda_review.md`.
The learner's review is expected to find issues with these provisional flags — including catching
the fact that Flag 1 may be more than "suspiciously strong" and instead be a straightforward
leakage case.*