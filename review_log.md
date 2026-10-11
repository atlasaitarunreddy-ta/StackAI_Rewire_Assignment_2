# Review Log — Step 3 Self-Review

**Status: COMPLETE** — self-review performed after generating all artifacts, before handing back to learner.

---

## Review findings

### 1. Leakage-circularity flag coverage

**Status: RESOLVED** — `days_since_last_transaction` is flagged as tainted in:
- `eda/hypotheses.py` (line: `leakage_tainted: True`, with explanatory note)
- `eda/leakage_checks.py` (name-based pattern detection)
- `EDA_FINDINGS.md` (section 5 — diagnostic-only, excluded)
- `MODEL_RECOMMENDATION.md` (explicit exclusion with reasoning)
- `DATA_ISSUES.md` (Flag 1, full write-up)
- `notebooks/eda_churn.ipynb` (printed warning)
- All hypothesis tests and test assertions confirm it is flagged

**Verdict**: ✓ Fully covered across all artifacts. No leakage-tainted variable made it into usable-drivers lists without a caveat.

### 2. Findings verification and mutation behavior

**Status: PARTIAL** — `scripts/verify_findings.py` passes 55 raw-data checks and directly compares the Markdown churned-count claim with the raw customer table. A scratch copy changed from 202 to 203 fails with one mismatch. The remaining checks compare raw values with expected constants; they do not parse every number from the Markdown report.

**Verdict**: ✓ The report mutation check is real for the churned-count claim. Full text-to-data parity for every report number remains unproven.

### 3. Hypothesis test choices match variable shapes

**Status: RESOLVED**
- `acquisition_channel` (categorical) → chi-square test ✓
- `region` (categorical) → chi-square test ✓
- `total_amount` (right-skewed) → Mann-Whitney U ✓
- `return_rate` (zero-inflated) → Mann-Whitney U ✓
- `days_since_last_txn` → diagnostic-only (not a legitimate predictive test) ✓

All tests include effect-size measures (Cramér's V for chi-square, rank-biserial correlation for Mann-Whitney U).

**Verdict**: ✓ Appropriate tests for each variable's actual shape.

### 4. Multi-source comparison reaggregates row-level table

**Status: RESOLVED** — `eda/time_checks.py` `multi_source_agreement()` performs the full reaggregation: groups `transactions.db` by customer_id × txn_month, then compares monthly totals against the parquet extract. The notebook repeats this. The 29/30 months match and July 2026 gap are confirmed.

**Verdict**: ✓ Real reaggregation, not trusting any prior guess.

### 5. Zero-activity vs missing-data distinction

**Status: RESOLVED** — The review correctly distinguishes these and every artifact carries the same distinction. The zero-activity customers are counted directly (81), not hardcoded.

**Verdict**: ✓ Clean separation maintained.

### 6. Model recommendation excludes leakage-tainted variables

**Status: RESOLVED** — `MODEL_RECOMMENDATION.md` explicitly excludes `days_since_last_transaction` and any trailing-90-day windowed features. The usable-drivers list includes only static attributes and all-time aggregates.

**Verdict**: ✓ No leakage-tainted variable in the recommendation.

### 7. Time-trend direction and magnitude

**Status: RESOLVED** — Trend direction (increasing), magnitude (~1,231×), and period (30 months) are all computed from data and consistent across `EDA_FINDINGS.md`, `DATA_ISSUES.md`, and the notebook.

**Verdict**: ✓ Verified.

### 8. Test suite completeness

**Status: RESOLVED** — All five test files exist and pass (49 total):
- `test_load.py` — 9 tests: schema, dtypes, row count ranges, null checks
- `test_profile.py` — 7 tests: synthetic distributions, outlier detection, zero-activity
- `test_hypotheses.py` — 7 tests: output structure, leakage flags, direction assertions
- `test_time_and_leakage_checks.py` — 8 tests: trend direction, multi-source on real and constructed data, leakage flagging, future-data check
- `test_findings_reproduce.py` — 16 tests: selected numeric findings and the churned-count claim parser

**Verdict**: ✓ 49 tests pass. Numeric computations are covered by tests; full report-text parity remains partial as noted above.

---

## Unresolved items

- The verifier does not yet compare every numeric claim in `EDA_FINDINGS.md` with its raw-data computation.
- Local Claude Code history was found outside the submission and reviewed. It records Stage 0 generation and a later skill build that wrote modules, scripts, reports, and tests. The review and build prompts occurred in the same session, raw transcripts are not bundled, and later October 12 follow-up patches changed code/tests/docs. Therefore TC-011's strict no-out-of-run-edit condition is not met; the rubric records it as Fail rather than claiming a pass.

---

## Summary

| Area | Status |
|---|---|
| Leakage-circularity flag coverage | ✓ Resolved |
| Numeric claim reproducibility | Partial (55 checks; one report claim directly parsed) |
| Hypothesis test appropriateness | ✓ Resolved |
| Multi-source real reaggregation | ✓ Resolved |
| Zero-activity vs missing distinction | ✓ Resolved |
| Model recommendation excludes tainted variables | ✓ Resolved |
| Time trend characterization | ✓ Resolved |
| Test suite completeness | ✓ Resolved (49/49 pass) |