# Churn EDA & Model-Family Recommendation

This repository contains the churn EDA work I completed as part of the learner submission. It includes my verified findings, leakage checks, time-drift checks, multi-source comparison, and my final recommendation based on the raw data.

## Environment setup

I used Python 3.12 and a local virtual environment from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

I validated the environment with:

```powershell
python -c "import pandas, numpy, scipy, pyarrow, matplotlib, pytest; print('dependencies OK')"
```

## Commands I ran and verified

I ran these checks successfully from the submission root:

```powershell
python -m scripts.run_profile
python -m scripts.run_hypothesis_tests
python -m scripts.run_time_and_leakage_checks
python -m scripts.verify_findings
pytest -v
```

### Verified results

- `python -m scripts.verify_findings` passed: 54 passed, 0 failed out of 54 checks
- `pytest -v` passed: 47 passed in 9.93s

## Key findings from my analysis

- Overall churn rate: 13.47%
- Zero-activity customer count: 81, and all 81 are churned
- No nulls were observed in the raw source tables
- Monetary distribution is strongly right-skewed; I used median/IQR and not mean/std for the summary logic
- `days_since_last_transaction` and trailing-90-day spend are leakage-tainted because they overlap with the churn label definition
- Transaction volume increases strongly over time, so a time-based split is preferable to a random split
- The row-level transaction table and parquet monthly aggregate disagree in July 2026, so month-level source agreement should be checked before production use

## Repository structure

- `data/` raw source files
- `eda/` profiling and hypothesis logic
- `scripts/` command entry points
- `notebooks/eda_churn.ipynb` notebook
- `tests/` verification suite
- `outputs/artifacts/` saved evidence and generated notes
- `EDA_FINDINGS.md` verified findings report
- `MODEL_RECOMMENDATION.md` model-family recommendation
- `DATA_ISSUES.md` data-quality and leakage notes
- `ARTIFACT_NOTES.md` artifact review
- `review_log.md` review log

## Notes

I checked the analysis against the raw data and did not rely only on the draft materials. I kept all raw files unmodified, used only the provided local data, and avoided adding credentials or secrets to the repo.

> Screenshots are optional evidence if the rubric or instructor asks for them. I kept the core evidence as exact command output and saved verification results in `outputs/artifacts/`, which is reproducible and easier to audit than screenshots alone.
