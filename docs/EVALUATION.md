# Evaluation and feedback

## Current checks

- Unit tests validate that SQL writes, multiple statements, unapproved tables and internal SQLite tables are rejected.
- API tests check startup/health and the browser UI.
- MCP integration test checks tool discovery and a schema call through the actual stdio MCP transport.
- `evaluation/datasets/routing_cases.json` is a small routing benchmark.
- `python -m scripts.run_eval` reports tool-routing recall: the share of test cases for which all expected agents were selected. This is a smoke metric, not a benchmark for answer truthfulness.

## Recommended extension

Add a human-reviewed golden dataset with `question`, `expected_tools`, `expected_sql_result`, `expected_source_ids`, `reference_answer`, and `must_not_claim`. Measure SQL execution accuracy, retrieval recall@k, citation validity, answer faithfulness, end-to-end task success, latency and cost. Split the evaluation set before prompt changes, and rerun it after each release.

Feedback records contain trace ID, positive/negative rating, category and comment. Use them to prioritize fixes and update the golden dataset only after human review. Do not silently convert all negative ratings into training labels; disagreement, ambiguity and missing context require triage.
