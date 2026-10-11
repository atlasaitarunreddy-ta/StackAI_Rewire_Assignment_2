# Artifact Notes — Self-critique log

**Status: VERIFIED** — this log documents what was reconsidered during the build.

---

## 1. Hypothesis test: return rate effect size was smaller than expected

The `return_rate_vs_churn` test showed a statistically significant result (p ≈ 9.3 × 10⁻⁶) but with a rank-biserial correlation of only 0.16 — a small effect. Both churned and non-churned customers have a median return rate that rounds to 0.00. The direction says "higher: non-churned" but the practical difference is negligible. In early reading of the churn rates, I expected a more meaningful difference. This reinforces the importance of effect-size reporting, not just p-values.

## 2. Channel and region not significant at α = 0.05

Both acquisition_channel (p = 0.12) and region (p = 0.29) failed to reach statistical significance despite visible churn rate gaps (organic 15.27% vs paid_search 10.21%; east 16.36% vs north 12.34%). The Stage 0 draft flagged these as candidate drivers from raw rates, but formal testing shows the gaps could arise from sampling variability. The recommendation appropriately notes them as "not significant" but still available as model candidates (statistical insignificance ≠ useless for prediction in a regularized model).

## 3. Multi-source gap was confined to one month — smaller scope than a systematic concern

The 24% gap in July 2026 between row-level and parquet sources is isolated (29/30 months match perfectly). In early inspection of the row vs parquet row counts (8,188 vs 8,086), the 102-row discrepancy felt like it might signal deeper misalignment. The month-by-month comparison confirmed it's a single-month cutoff artefact. The July anomaly is real but limited.

## 4. The zero-activity population was clean — no surprises

The 81 zero-activity customers, all churned=1, confirmed exactly. No edge case found where a zero-activity customer had churned=0 or where a customer appeared in transactions.db with zero presence in customers.csv. The distinction between zero-activity and missing data held cleanly.

## 5. Findings mutation check

**Performed**: After generating `EDA_FINDINGS.md`, I changed the stated churned count in `scripts/verify_findings.py` from 202 to 203 to test whether the parity script catches it. The script failed with `[FAIL] Churned count`. I restored the correct value. This confirms `test_findings_reproduce.py` and `verify_findings.py` catch claim mismatches.

## 6. Coverage-of-intent check

**Performed**: All candidate drivers listed in `eda_review.md` are covered by hypothesis tests, test functions, and the notebook. The leakage flags (days_since_last_transaction, trailing-90-day features) are present in `leakage_checks.py`, `DATA_ISSUES.md`, and `MODEL_RECOMMENDATION.md`. The multi-source comparison and time-trend checks are covered. No reviewed item was left unverified.

## Known limitation

The notebook cell with the f-string formatting for the monthly plot uses a mixed f-string and .format() pattern that is not ideal but runs correctly. If the notebook is re-executed top-to-bottom without having run the earlier "txn month" assignment cell first, the `monthly` variable would need to be recomputed — the notebook is designed to run sequentially and this is noted in the summary cell.