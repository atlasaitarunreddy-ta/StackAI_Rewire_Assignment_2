# Data Issues — Verified Flags

**Status: VERIFIED** — every flag is backed by a specific check against raw data.

---

## Flag 1: Label-window leakage — days since last transaction

**Severity: HIGH**

### What the data shows

`days_since_last_transaction` separates churned and non-churned customers almost perfectly:
- **Non-churned**: 0–90 days since last txn (mean 28.6, median 23)
- **Churned (active)**: 91–365 days since last txn (mean 132.5, median 113)
- Mann-Whitney U: p ≈ 3.7 × 10⁻⁷⁴ — complete separation

### Why it is leakage, not a legitimate predictor

The churn label is defined as "no purchase in the trailing 90 days before the as-of date." `days_since_last_transaction` measures exactly that same relationship: it is computed from the last transaction timestamp relative to the same as-of date. The separation is **definitional**, not predictive. A model that relies on this variable would fail in production because for new customers we do not yet know whether they will have a 91+ day gap.

### Tainted variables
- `days_since_last_transaction` — directly circular
- Any trailing-90-day windowed aggregate (e.g. `trailing_90d_spend`, `trailing_90d_txn_count`) — same circularity

### Clean (not tainted)
- `acquisition_channel`, `region` — static attributes
- `total_amount` (all-time), `return_rate` (all-time) — not windowed
- `signup_date` / `account_tenure` — not derived from label window

---

## Flag 2: Class imbalance — 13.5% churn rate

**Severity: MEDIUM**

### Numbers
- Overall churn rate: **13.47%** (202 / 1,500)
- Among customers with transactions: **8.53%** (121 / 1,419)
- Majority class: **86.53%** not churned

### Modeling consequences
- **Accuracy is misleading**: a model predicting "not churned" for all customers achieves ~86.5% accuracy while being useless for retention marketing.
- **Recommended metrics**: precision, recall, F1, PR-AUC (not ROC-AUC, which can overstate performance on imbalanced data).
- **Class weighting**: `scale_pos_weight` ≈ 6.4 (ratio of negative to positive instances) in XGBoost/LightGBM.
- **Threshold tuning**: final decision threshold should reflect the retention team's cost structure for false positives (wasted outreach) vs false negatives (missed churner).
- If the zero-activity customers are excluded, the churn rate drops to 8.53% and `scale_pos_weight` would need recalculation (~10.7).

---

## Flag 3: Non-stationarity — strong upward volume trend

**Severity: MEDIUM-HIGH**

### Data
Monthly transaction volume grew consistently over 30 months (Feb 2024 – Jul 2026):
- Transaction count: 1 → 1,231 (~1,231× growth)
- Total amount: $25 → $62,085
- Unique customers: 1 → 787

The trend is strongly upward across all three metrics with only minor month-to-month dips.

### Modelling consequence
- A **random train/test split** would mix very different volume regimes — a customer from early 2024 (1–5 txns/month) alongside one from mid-2026 (1,000+ txns/month), overstating generalization.
- A **time-based split** (train on earlier months, test on later months) is recommended.
- Feature distributions beyond volume (category mix, amount distribution) may also drift and should be checked.

---

## Flag 4: Multi-source disagreement — July 2026 cutoff anomaly

**Severity: LOW-MEDIUM**

### Comparison results
- **29 of 30 months**: Perfect agreement between `transactions.db` (reaggregated) and `transactions_monthly_agg.parquet`.
- **July 2026 only**: Row-level table has 1,231 transactions vs parquet's 994 (23.8% gap), and $62,084.62 vs $50,116.67 total amount.
- **102 extra customer-months** exist in the row-level aggregate only — all involving customers whose last transaction was July 26–31, 2026.

### Interpretation
The parquet appears to have been generated with a cutoff before month-end, while the row-level table captures the full month. This is a pipeline timing artefact, not a fundamental data disagreement.

### Modelling consequence
- If models use the parquet for training and row-level data for inference (or vice versa), the July anomaly could cause training/serving skew.
- Affects one month and ~100 customers. Impact is likely small, but the pipeline team should align on which source is authoritative.

---

## Flag 5: Zero-activity customer population

**Severity: INFORMATIONAL**

### What it is
81 customers (5.4% of total) have signed up but never transacted. They have zero rows in `transactions.db`.

### Key facts
- All 81 have churned=1 (by definition — they have never transacted, so they certainly have not transacted in the trailing 90 days).
- They cannot have any transaction-based features (amount, count, category, channel, return rate).
- Inclusion/exclusion is a business decision: include them (with zero-filled features), exclude them, or model them separately.

---

## Summary of flags

| # | Issue | Severity | Evidence |
|---|---|---|---|
| 1 | Days-since-last-txn leakage (label window circularity) | HIGH | Perfect separation (0–90 vs 91–365 days); definitional, not predictive |
| 2 | Class imbalance (13.5% churn rate) | MEDIUM | Counted from CSV; accuracy baseline = 86.53% |
| 3 | Non-stationarity (~1,231× volume growth over 30 months) | MEDIUM-HIGH | Computed month-by-month from transactions |
| 4 | Multi-source disagreement (July 2026: 23.8% gap) | LOW-MEDIUM | Reaggregation comparison confirmed |
| 5 | Zero-activity population (81 customers, all churned) | INFORMATIONAL | Counted from data |