# Evaluator Evidence Index

Review run: 2026-10-12, using the submission's `.venv`. These are reproduced results from this review; they do not establish when or by whom the original work was authored.

## Verified outcomes

- All three sources load: 1,500 customer rows, 11,742 transaction rows, and 8,086 monthly-aggregate rows; no nulls were found. The 81 customers without transactions are a distinct zero-activity population and all are churned. See `profile_run.txt` and `profile_summary.json`.
- Transaction amount is right-skewed: mean $49.72, median $33.82, skewness 6.1066, and 783 high-side outliers (6.7%) under the 1.5×IQR rule. See `profile_run.txt` and `EDA_FINDINGS.md`.
- Categorical channel testing uses chi-square and reports a null result (χ²=5.8387, p=0.1197, Cramér's V=0.0624). The trailing-90-day diagnostic is flagged as circular (p≈3.71×10⁻⁷⁴; 0–90 days vs. 91–365 days) and excluded from the recommendation. See `hypothesis_tests_run.txt`, `hypothesis_results.json`, and `MODEL_RECOMMENDATION.md`.
- Monthly transaction volume rises from 1 to 1,231 across 30 months. The row-level and parquet sources agree in 29/30 months; July 2026 differs by 237 transactions (23.8%). See `time_and_leakage_run.txt` and `time_and_leakage_results.json`.
- Current test run: 49 passed. Raw-data verifier: 55/55 checks passed. Notebook execution: all 26 cells completed. See `pytest_run.txt`, `verify_findings_run.txt`, `notebook_execution_run.txt`, and `eda_churn.executed.ipynb`.
- Edge probes: a constant-group Mann-Whitney test returned U=0 and p=0.220671; an empty profile raised an explicit `ValueError`; two injected high outliers were detected. See `edge_case_checks.txt`.
- A temporary findings copy changed `Churned: 202` to `Churned: 203`; verification exited 1 with a report-claim mismatch. The clean report passed 55/55. See `mutation_test.txt`.
- The rubric and test-case sheets now contain the evidence details inline, with adjacent Feedback columns; there is no separate Evidence Log sheet. Across the 24 feedback entries, 8 have targeted follow-up suggestions and 16 say “No changes required.”

## Evidence limits

- The verifier directly parses only the churned-count statement from `EDA_FINDINGS.md`; its other checks compare computed data with expected constants. It does not yet link every markdown number to its computation. The review log marks this as partial.
- Local Claude Code history was reviewed: one October 11 session records Stage 0 notebook/draft writes; another records the review and subsequent build invocation and writes to modules, scripts, reports, and tests. The review and build prompts occurred in the same session, and raw transcripts are not bundled. October 12 follow-up patches modified code/tests/docs outside the build run, so TC-011 is marked Fail under its strict no-out-of-run-edit condition. The inline rubric records the session IDs and details.
- The existing `churn-eda-submission-final.zip` predates these updates. Use the refreshed `churn-eda-submission-evidence.zip` in the parent folder; the older archive was left untouched.
