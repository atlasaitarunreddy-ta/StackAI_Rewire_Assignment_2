# Model-Family Recommendation — Draft (Stage 0)

**Status: PROVISIONAL — first-pass recommendation based on raw data profiling.**
This recommendation is not backed by formal hypothesis testing or a confirmed review. All
reasoning here is best-effort and should be confirmed, rejected, or refined in the learner's
`eda_review.md`.

Companion: `notebooks/eda_churn.ipynb`, `EDA_FINDINGS_DRAFT.md`, `DATA_ISSUES_DRAFT.md`.

**As-of-date assumption**: 2026-07-31 (max transaction timestamp) used as proxy. Confirmation needed.

---

## Candidate model family: Gradient-boosted decision trees (LightGBM or XGBoost)

### Why this is the initial pick, tied to observed data characteristics

| Dataset characteristic | Why GBDT fits |
|---|---|
| **Mixed dtypes** — categorical (channel, region, category) + numeric (amount, txn_count) + binary (is_returned) | GBDTs handle categorical features natively (LightGBM) or with simple encoding; no need to embed or normalize across heterogeneous types. |
| **Right-skewed numeric variables** — amount is heavily right-skewed (mean $49.72, median $33.82, max $1,684.21) | Tree-based models are robust to skewed distributions and outliers — no log-transformation or clipping needed. Splits are based on rank order, not magnitude. |
| **Moderate class imbalance** — 13.5% churn rate (8.5% excluding zero-activity) | Both LightGBM and XGBoost have built-in `scale_pos_weight` / `class_weight` to handle imbalance without manual resampling. |
| **Potential non-linear interactions** — channel × region × behavior may interact in complex ways | Trees naturally capture interactions without manual specification. Logistic regression would require explicit interaction terms. |
| **Stakeholder interpretation** — retention marketing team needs to understand why customers are flagged | GBDTs offer feature importance (gain, split count), SHAP values for per-customer explanations, and partial dependence plots for business-facing reasoning. |

### Which drivers this assumes are usable (NOT leakage-tainted)

- `acquisition_channel` — static categorical, no temporal overlap with label
- `region` — static categorical, no temporal overlap
- `account_tenure` / `signup_date` — time since signup, not windowed
- `total_historical_txn_count` — all-time count, not windowed
- `total_historical_amount` — all-time, not windowed
- `return_rate` — all-time proportion (provisional: confirm not computed over a recent window)
- `category_preferences` — category mix, no temporal overlap
- `channel_preferences` — channel mix, no temporal overlap

### Which drivers this EXCLUDES (suspected leakage tainted)

- **`days_since_last_transaction`**: Produces near-perfect separation (non-churned: 0-90 days,
  churned: 91+ days). The churn label definition ("no transaction in 90 days") and this
  feature are derived from the same window. See DATA_ISSUES_DRAFT.md Flag 1.
- **Any trailing-90-day windowed feature**: If `trailing_90d_spend`, `trailing_90d_txn_count`,
  or similar features exist in the feature set, they should be excluded for the same reason.

**IMPORTANT CAVEAT**: The `days_since_last_txn` feature is the single most powerful predictor in
the dataset and could produce an excellent-looking model — but that model would fail in
production because the feature is (likely) circular with the label definition. A model built on
this feature would not generalize to new customers.

---

## Alternative considered: Logistic regression with regularization

| Consideration | Assessment |
|---|---|
| **Why not the top pick** | Right-skewed monetary variables need transformation (log or Box-Cox) to meet linearity assumptions; categorical variables need manual encoding; interaction terms need explicit specification. GBDTs handle all of this implicitly. |
| **When logistic regression could win** | If the legitimate (non-leakage) predictors turn out to be mostly linear with few interactions after proper testing, a regularized logistic regression could be simpler, more auditable, and potentially generalize better on a dataset of this size (~1,400 active customers). |
| **Interpretability** | Logistic regression is inherently more interpretable (coefficients with signed directions). For retention marketing in a regulated or high-scrutiny environment, this might matter. |
| **Where it struggles** | With the observed right-skew in amount, the model would need feature engineering (log transform, interactions) that trees handle automatically. |

**Verdict**: GBDT as top pick, logistic regression as a strong alternative worth benchmarking
against. The choice depends on whether the legitimate predictors are roughly linear (→ logistic
regression may suffice) or require complex interactions (→ GBDT needed).

---

## Open questions for the learner's review

1. **Is the days-since-last-txn leakage confirmed?** If yes, it's excluded from both candidates.
   If the label definition is different than assumed, it might be usable after all.
2. **How many legitimate drivers survive hypothesis testing?** If only 2-3 moderately strong
   predictors survive proper leakage-aware testing, a simpler model becomes more attractive.
3. **Is the zero-activity population included or excluded?** If excluded (working only on the
   1,419 ever-active customers), the churn rate drops to 8.5% and the class imbalance is milder
   but still present.
4. **Does the July 2026 multi-source gap affect training?** If using the parquet for feature
   computation, ~100 customers' July 2026 features will be systematically underestimated vs the
   row-level table. This is a modelling decision, not a blocker.
5. **Should amount be log-transformed even for tree models?** Trees don't need it, but it can
   sometimes help with very skewed variables for better split finding.
6. **How does the retention team weigh false positives vs false negatives?** This determines
   the optimal probability threshold and the best metric to optimize.

---

## Summary

> **Recommended: Gradient-boosted decision trees (LightGBM / XGBoost)**  
> **Alternative: Logistic regression with regularization (L1 or L2)**  
> **Reason for pick**: Mixed dtypes, right-skewed numerics, moderate imbalance, and expected
> non-linear interactions all favor trees. The legitimate (non-leakage) drivers are a mix of
> categorical and numeric features that GBDTs handle natively.  
> **Key assumption**: `days_since_last_transaction` and any other trailing-90-day windowed
> features are excluded as leakage-tainted.  
> **This is a provisional recommendation subject to the learner's confirmed review.**

---

*This document is a draft. The learner's `eda_review.md` should confirm, reject, or refine the
family choice based on formal hypothesis testing and leakage checks — see
`DATA_ISSUES_DRAFT.md` for the candidate leakage flags.*