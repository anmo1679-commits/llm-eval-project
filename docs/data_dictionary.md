# Data Dictionary

## Overview
This document describes all datasets in the LLM Evaluation Harness pipeline.

---

## `data/prompts.csv`

**Purpose:** Master prompt suite for LLM evaluation

| Column | Type | Description |
|--------|------|-------------|
| `prompt_id` | int | Unique identifier for the prompt |
| `category` | string | Prompt category (e.g., "factual", "creative", "coding", "safety") |
| `difficulty` | string | Difficulty level ("easy", "medium", "hard") |
| `should_refuse` | int | 1 if model should refuse, 0 otherwise (safety evaluation) |
| `expected_format` | string | Expected response format ("json", "text", "code", etc.) |
| `prompt_text` | string | The actual prompt text sent to the model |

**Row Count:** 150  
**Grain:** One row per unique prompt

---

## `data/runs.csv`

**Purpose:** Records of all evaluation runs across models and configurations

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | int | Unique identifier for this run |
| `prompt_id` | int | Foreign key to `prompts.csv` |
| `model_name` | string | Name of the Ollama model used |
| `system_prompt_version` | string | System prompt variant (e.g., "v1", "v2") for A/B testing |
| `temperature` | float | Model temperature parameter |
| `timestamp` | datetime | When the run was executed (ISO 8601 format) |
| `latency_ms` | int | Response latency in milliseconds |
| `output_len_chars` | int | Character count of model output |
| `output_text` | string | Full text response from the model |

**Grain:** One row per model run (model × prompt × configuration)

---

## `data/auto_scores.csv`

**Purpose:** Automated scoring of model outputs using rule-based heuristics

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | int | Foreign key to `runs.csv` |
| `format_followed` | int | 1 if output matches expected format, 0 otherwise |
| `refusal_present` | int | 1 if refusal language detected, 0 otherwise |
| `refusal_correct` | int | 1 if model correctly refused when `should_refuse=1`, 0 otherwise |
| `mentions_uncertainty` | int | 1 if uncertainty language present ("depends", "not sure"), 0 otherwise |
| `contains_policy_risk_flag` | int | 1 if policy risk keywords detected, 0 otherwise |
| `citations_present` | int | 1 if citations/references detected, 0 otherwise |

**Grain:** One row per run (1:1 with `runs.csv`)  
**Scoring Logic:** See `src/auto_score.py` for detailed pattern matching

---

## `data/human_ratings.csv`

**Purpose:** Manual human ratings for a stratified sample of runs

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | int | Foreign key to `runs.csv` |
| `helpfulness_1_5` | int | Helpfulness rating (1-5 scale) |
| `correctness_1_5` | int | Factual correctness rating (1-5 scale) |
| `clarity_1_5` | int | Clarity and readability rating (1-5 scale) |
| `compliance_1_5` | int | Policy compliance rating (1-5 scale) |
| `hallucination_flag` | int | 1 if hallucination detected, 0 otherwise |
| `notes` | string | Optional notes from human rater |

**Sample Size:** 80-120 runs  
**Sampling Strategy:** Stratified by (model_name × system_prompt_version × category)  
**Grain:** One row per rated run (partial coverage of `runs.csv`)

---

## Relationships

```
prompts (1) ──── (many) runs
runs (1) ──── (1) auto_scores
runs (1) ──── (0 or 1) human_ratings
```

---

## Power BI Data Model

Recommended relationships:
1. `prompts[prompt_id]` → `runs[prompt_id]` (1:many)
2. `runs[run_id]` → `auto_scores[run_id]` (1:1)
3. `runs[run_id]` → `human_ratings[run_id]` (1:0 or 1)

Mark all relationships as single-direction for performance.
