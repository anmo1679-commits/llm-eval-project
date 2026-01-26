# Data Quality Checks

## Overview
Quality checks to run before analysis to ensure data integrity.

---

## 1. Run ID Uniqueness

**Check:** All `run_id` values in `runs.csv` must be unique

**SQL-style validation:**
```sql
SELECT run_id, COUNT(*) as count
FROM runs
GROUP BY run_id
HAVING count > 1
```

**Expected:** 0 duplicates  
**Action if failed:** Investigate root cause in `run_eval.py`

---

## 2. Prompt Coverage

**Check:** Every `prompt_id` in `prompts.csv` has at least one run per (model, system_prompt_version)

**Validation:**
- Expected runs per model/config = 150 (number of prompts)
- Check for missing prompt_id values in runs

**Expected:** Complete coverage  
**Action if failed:** Re-run evaluation for missing combinations

---

## 3. Missing Output Text

**Check:** No blank or null `output_text` in `runs.csv`

**Validation:**
```sql
SELECT COUNT(*)
FROM runs
WHERE output_text IS NULL OR output_text = ''
```

**Expected:** 0 missing outputs  
**Action if failed:** Flag and review—may indicate model errors or API failures

---

## 4. Auto-Score to Run Join

**Check:** Every `run_id` in `runs.csv` has exactly one corresponding row in `auto_scores.csv`

**Validation:**
- `COUNT(runs.run_id)` = `COUNT(auto_scores.run_id)`
- No orphaned scores

**Expected:** Perfect 1:1 join  
**Action if failed:** Re-run `auto_score.py`

---

## 5. Latency Outliers

**Check:** Identify runs with extreme latency (>99th percentile)

**Validation:**
- Calculate P99 latency
- Flag runs where `latency_ms > P99 * 3`

**Expected:** <1% outliers  
**Action if failed:** Document outliers; may indicate system issues during eval

---

## 6. Human Rating Sample Coverage

**Check:** Human ratings sample represents all cohorts

**Validation:**
- Each (model, system_prompt_version, category) combination has ≥3 rated runs
- Total rated runs between 80-120

**Expected:** Balanced stratified sample  
**Action if failed:** Re-run `sample_for_human_rating.py` with adjusted parameters

---

## 7. Foreign Key Integrity

**Check:** All foreign keys resolve correctly

**Validations:**
- `runs.prompt_id` → exists in `prompts.prompt_id`
- `auto_scores.run_id` → exists in `runs.run_id`
- `human_ratings.run_id` → exists in `runs.run_id`

**Expected:** No orphaned records  
**Action if failed:** Data pipeline issue—investigate and regenerate

---

## 8. Auto-Score Value Ranges

**Check:** All auto-score columns contain only 0 or 1

**Validation:**
```sql
SELECT *
FROM auto_scores
WHERE format_followed NOT IN (0, 1)
   OR refusal_present NOT IN (0, 1)
   OR refusal_correct NOT IN (0, 1)
   OR mentions_uncertainty NOT IN (0, 1)
   OR contains_policy_risk_flag NOT IN (0, 1)
   OR citations_present NOT IN (0, 1)
```

**Expected:** 0 invalid values  
**Action if failed:** Bug in `auto_score.py`—fix and regenerate

---

## 9. Human Rating Value Ranges

**Check:** Rating columns are in valid ranges

**Validation:**
- `helpfulness_1_5`, `correctness_1_5`, `clarity_1_5`, `compliance_1_5` ∈ {1, 2, 3, 4, 5, NULL}
- `hallucination_flag` ∈ {0, 1, NULL}

**Expected:** All non-null values in range  
**Action if failed:** Data entry error—review and correct

---

## 10. Timestamp Consistency

**Check:** All timestamps are valid and within expected range

**Validation:**
- Parse all `timestamp` values successfully
- All timestamps > project start date
- All timestamps ≤ current date

**Expected:** Valid ISO 8601 timestamps  
**Action if failed:** Review `run_eval.py` timestamp generation

---

## Automated DQ Report (Optional)

Create `src/data_quality_check.py` to run these checks programmatically and output:
- Console summary (pass/fail per check)
- `data/dq_report.csv` with results:
  ```
  check_name, status, records_affected, notes
  ```

**Run frequency:** Before each Power BI refresh or analysis session
