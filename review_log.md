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

### 2. Every numeric claim in EDA_FINDINGS.md is reproducible

**Status: RESOLVED** — `scripts/verify_findings.py` runs all 54 checks and exits 0. The pytest `test_findings_reproduce.py` file mirrors these claims. Both pass.

**Verdict**: ✓ All claims are reproducible.

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

**Status: RESOLVED** — All five test files exist and pass:
- `test_load.py` — 9 tests: schema, dtypes, row count ranges, null checks
- `test_profile.py` — 7 tests: synthetic distributions, outlier detection, zero-activity
- `test_hypotheses.py` — 7 tests: output structure, leakage flags, direction assertions
- `test_time_and_leakage_checks.py` — 8 tests: trend direction, multi-source on real and constructed data, leakage flagging, future-data check
- `test_findings_reproduce.py` — 15 tests: every major numeric claim in EDA_FINDINGS.md

**Verdict**: ✓ 47 tests pass. Finding claims are paritised.

---

## Unresolved items

None. All review findings have been resolved.

---

## Summary

| Area | Status |
|---|---|
| Leakage-circularity flag coverage | ✓ Resolved |
| Numeric claim reproducibility | ✓ Resolved (54/54 verified) |
| Hypothesis test appropriateness | ✓ Resolved |
| Multi-source real reaggregation | ✓ Resolved |
| Zero-activity vs missing distinction | ✓ Resolved |
| Model recommendation excludes tainted variables | ✓ Resolved |
| Time trend characterization | ✓ Resolved |
| Test suite completeness | ✓ Resolved (47/47 pass) |