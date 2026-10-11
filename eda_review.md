# eda_review.md — Churn EDA & Model-Family Recommendation

## Distribution / missingness / outlier corrections

- **Correction**: Stage 0 drafted that the zero-activity customers were a missing-data problem. I checked the raw data directly: 81 customers appear in `customers.csv` but have no rows in `transactions.db`, and all 81 have `churned = 1`. These are not nulls or missing transaction records; they are a legitimate zero-activity segment. This distinction matters because the headline churn rate is 13.47% overall, but among customers with at least one transaction it drops to 121 / 1,419 = 8.53%.
- **Correction**: Stage 0's draft called the amount distribution "roughly normal" or at least not deeply problematic. The actual check shows a strong right tail: mean amount is $49.72 but median is $33.82, with a max of $1,684.21 and Q3 of $61.39. With a 1.5×IQR rule, the upper bound is $125.93 and 783 transactions (6.7%) are flagged as outliers, all on the high side. This is not a symmetric distribution; monetary summaries downstream should use median/IQR and robust methods rather than mean/std.

## Hypothesis tests to run

- **Driver**: acquisition_channel
- **Null hypothesis**: acquisition channel and churn status are independent (channel proportions are the same for churned and non-churned customers).
- **Test**: chi-square test of independence
- **Effect-size measure**: Cramér's V (standardised phi for a multi-category variable)
- **Survives leakage check?**: Yes — acquisition_channel is static, no temporal overlap with the label window.
- **Why this test**: this is a categorical predictor against a binary churn outcome, so no ordering assumption is needed and the question is whether the channel proportions differ between churned and not-churned customers.

- **Driver**: region
- **Null hypothesis**: region and churn status are independent.
- **Test**: chi-square test of independence
- **Effect-size measure**: Cramér's V
- **Survives leakage check?**: Yes — region is a static attribute.
- **Why this test**: region is categorical and the churn outcome is binary, so a chi-square test is the correct distributional comparison.

- **Driver**: total_amount or average_amount per customer
- **Null hypothesis**: the distribution of customer-level monetary value is the same for churned and non-churned customers.
- **Test**: Mann-Whitney U test
- **Effect-size measure**: rank-biserial correlation (r̄ = 1 − 2U/(n₁n₂)); reports both the direction (which group has higher typical monetary value) and the magnitude.
- **Survives leakage check?**: Yes — total_amount is an all-time aggregate, not windowed to the label definition.
- **Why this test**: customer-level monetary values are bounded below by zero and strongly right-skewed, so a t-test's normality assumption is not defensible.

- **Driver**: return_rate or return_count
- **Null hypothesis**: the distribution of return-based features is the same for churned and non-churned customers.
- **Test**: Mann-Whitney U test
- **Effect-size measure**: rank-biserial correlation
- **Survives leakage check?**: Yes — return_rate is an all-time proportion, not windowed.
- **Why this test**: return-based features are bounded and often zero-inflated, making a nonparametric comparison more appropriate than a t-test.

- **Driver**: days_since_last_transaction (review only; not a usable model feature)
- **Null hypothesis**: (diagnostic only — not a legitimate hypothesis test because the feature is circular with the label.)
- **Test**: descriptive check + Mann-Whitney U as a diagnostic only
- **Effect-size measure**: descriptive separation range (min/max per group) rather than a formal effect size, because the near-perfect separation is a definitional artefact, not a real effect.
- **Survives leakage check?**: **No** — this variable is tautologically derived from the same trailing-90-day window that defines the label. Flagged as leakage-tainted. Do not use in any predictive model.
- **Why this test**: the feature is derived from the same trailing-90-day window that defines the label, so it is not a legitimate predictive variable even if the raw test is statistically compelling.

## Leakage / imbalance / non-stationarity / multi-source flags

- **Leakage**: `days_since_last_transaction` and any trailing-90-day windowed transaction features are tainted. The churn label is defined as no purchase in the trailing 90 days; a feature built from the same relationship to the same as-of date is circular with the label, not a real predictor. In the data, non-churned customers all have last transaction within 90 days while churned customers are at 91+ days, which is a definitional split rather than an independently predictive signal.
- **Imbalance**: the churn rate is 202 / 1,500 = 13.47%. That makes accuracy a misleading headline metric because a baseline model predicting "not churned" would be 86.53% accurate while still missing all churners. Precision, recall, F1, and PR-AUC are more suitable for retention modeling.
- **Class-weighting strategy**: both XGBoost and LightGBM support `scale_pos_weight` (ratio of negative to positive instances: ~6.4) to penalize false negatives during training without resampling. The final decision threshold should be tuned against the retention team's cost structure for false positives (wasted outreach) vs false negatives (missed churner). A separate note: if the zero-activity customers are excluded, the churn rate drops to 8.53% and `scale_pos_weight` would need recalculation accordingly.
- **Non-stationarity**: monthly transaction volume is strongly increasing through the sample (~1,200× growth). The data span Feb 2024 to Jul 2026, and the month-level volume rises from 1 transaction in the earliest month to 1,231 in the latest month, with a corresponding explosion in total amount and unique users. A random train/test split would mix very different operating regimes, so the time split should be evaluated and used instead of a shuffled split.
- **Multi-source**: the row-level transaction table and the customer-month parquet should be reaggregated to the same `customer_id × txn_month` granularity and compared month by month. A real disagreement would look like a systematic gap in counts or amounts for the same month, not just noise. In the observed data, 29 of 30 months agree exactly, but July 2026 shows a 24% gap: the row-level table includes 1,231 transactions and $62,085 total versus the parquet's 994 transactions and $50,117, with 102 extra customer-month rows. That is a source-alignment warning and should be checked before relying on either table for the final feature set.

## Model-family judgment

- **Candidate family**: gradient-boosted decision trees (LightGBM or XGBoost)
- **Why, tied to this dataset's checked characteristics**: the dataset has mixed types, right-skewed monetary variables, likely nonlinear interactions, and moderate imbalance. Tree-based models handle skewed numeric features, categorical inputs, and interaction effects without heavy preprocessing. They also support class weighting and produce useful feature-importance output for business review.
- **Stakeholder interpretability**: a retention-marketing audience needs to understand *why* a customer is flagged as likely to churn, not just *that* they were flagged. GBDT models support SHAP values for per-customer explanations (which features pushed this customer's score up or down and by how much), partial dependence plots for business-facing reasoning about individual drivers (e.g. "how does churn probability change with account tenure?"), and global feature-importance rankings (gain, split count) for prioritizing retention interventions. These tools serve a consumer that must act on the model's output, not just evaluate its accuracy. Logistic regression would offer simpler signed coefficients but at the cost of missing nonlinear patterns the data likely contain.
- **Alternative considered**: logistic regression with regularization — **Why not the top pick**: it requires more manual preprocessing for skewed monetary features and explicit interaction handling, while the observed patterns favor nonlinear splits.
- **Drivers assumed usable / excluded**: usable candidates include `acquisition_channel`, `region`, and any non-windowed historical behavior features that are not derived from the trailing-90-day churn definition. Excluded features include `days_since_last_transaction` and any trailing-90-day spend/count features whose calculation overlaps with the label window; these are circular and should not be used for modeling or for ranking feature importance.

## Final review note

The key correction in this review is that the most powerful apparent signal is not a legitimate predictive driver: it is defined by the same 90-day churn rule used to create the label. The right way to proceed is to treat it as a leakage risk, keep the class-imbalance and time-drift issues in view, and move forward with a model that uses static attributes and non-windowed behavioral signals only.
