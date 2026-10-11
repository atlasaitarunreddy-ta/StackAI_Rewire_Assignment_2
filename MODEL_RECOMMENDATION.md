# Model-Family Recommendation — Verified

**Status: VERIFIED** — based on confirmed hypothesis tests, leakage checks, and distribution profiling against raw data.

---

## Candidate family: Gradient-boosted decision trees (LightGBM or XGBoost)

### Why this is the recommended pick, tied to observed data characteristics

| Dataset characteristic | Why GBDT fits |
|---|---|
| **Mixed dtypes** — categorical (channel, region) + numeric (amount, txn_count) | GBDTs handle categorical features natively (LightGBM) or with simple encoding; no need to embed or normalize across heterogeneous types. |
| **Right-skewed monetary variables** — amount: mean $49.72, median $33.82, max $1,684.21, skewness 6.11 | Tree-based models are robust to skewed distributions — splits are based on rank order, not magnitude. |
| **Moderate class imbalance** — 13.47% churn rate overall (8.53% excluding zero-activity) | Both LightGBM and XGBoost support `scale_pos_weight` (~6.4 overall, ~10.7 if zero-activity excluded) to handle imbalance without manual resampling. |
| **Non-linear interaction potential** — channel × region × behavioral features may interact in complex ways | Trees capture interactions without manual specification. Logistic regression would require explicit interaction terms. |
| **Stakeholder interpretability** — retention marketing team needs to act on the model's output, not just evaluate its accuracy | GBDTs support SHAP values for per-customer explanations (which features pushed a customer's score up/down), partial dependence plots for business-facing driver analysis, and global feature-importance rankings for prioritizing interventions. Logistic regression offers simpler signed coefficients but at the cost of missing nonlinear patterns. |

### Which drivers this assumes are usable (NOT leakage-tainted)

- `acquisition_channel` — static categorical, no temporal overlap with label. Survived hypothesis test (p = 0.12, not significant, but still a candidate for modeling).
- `region` — static categorical, no temporal overlap. Survived hypothesis test (p = 0.29, not significant).
- `total_amount` (all-time) — not windowed. Statistically significant with large effect (rank-biserial = 0.53).
- `return_rate` (all-time) — not windowed. Statistically significant with small effect (rank-biserial = 0.16).
- `account_tenure` / `signup_date` — time since signup, not windowed.
- `total_historical_txn_count` — all-time count, not windowed.
- `category_preferences`, `channel_preferences` — category/channel mix, no temporal overlap.

### Which drivers this EXCLUDES (leakage-tainted)

- **`days_since_last_transaction`**: Produces near-perfect separation (non-churned: 0–90 days, churned: 91+ days) because the churn label is defined on exactly this same trailing-90-day window. This is a definitional artefact, not a predictive signal. **Excluded.**
- **Any trailing-90-day windowed feature** (e.g. `trailing_90d_spend`, `trailing_90d_txn_count`): Same circularity. **Excluded.**

---

## Alternative considered: Logistic regression with regularization

| Consideration | Assessment |
|---|---|
| **Why not the top pick** | Right-skewed monetary variables (skewness 6.11) need transformation (log or Box-Cox); categorical variables need manual encoding; interaction terms need explicit specification. GBDTs handle all of this implicitly. |
| **When logistic regression could win** | If the legitimate predictors turn out to be mostly linear with few interactions. On this dataset, the moderate imbalance and right-skewed variables make this less likely, but a regularized model would be worth benchmarking. |
| **Interpretability** | Logistic regression offers signed coefficient directions directly. For a high-scrutiny regulatory environment this may be advantageous. |
| **Where it struggles** | The observed right-skew in amount, the moderate imbalance, and the likely need for interaction handling all favor GBDTs. |

**Verdict**: GBDT as top pick, logistic regression as a strong alternative to benchmark against.

---

## Summary

> **Recommended: Gradient-boosted decision trees (LightGBM / XGBoost)**  
> **Alternative: Logistic regression with regularization (L1 or L2)**  
> **Reason**: Mixed dtypes, heavily right-skewed monetary variables (skewness 6.11), moderate imbalance (13.47% churn rate), and expected nonlinear interactions all favor GBDTs. The usable (non-leakage) drivers include static attributes and all-time behavioral aggregates.  
> **Key exclusion**: `days_since_last_transaction` and any trailing-90-day windowed features are leakage-tainted and must not be used.  
> **Accountability**: Every claim here is reproducible from raw data via `scripts/verify_findings.py`.