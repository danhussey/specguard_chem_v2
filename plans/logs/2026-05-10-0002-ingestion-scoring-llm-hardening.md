# 2026-05-10 0002 Ingestion, Scoring, And LLM Hardening

## Summary

Hardened the CARA-like data path and expanded the evaluation harness while the
official CARA archive download was still in progress. This log covers the
implementation slice after the initial scaffold commit.

## Commands Run

```bash
uv run --extra dev pytest tests/test_data_pipeline.py
uv run --extra dev pytest
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem inspect-cara tests/fixtures/cara_split_layout --out /tmp/sgchem_cara_layout.json
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems random_valid,rules_only,similarity_to_best_active,qsar_rf,bare_llm,llm_validator,llm_tools,llm_tools_validator --cache-dir tests/fixtures/llm_cache --out runs/fixture_full
uv run sgchem compare-runs runs/fixture_full/random_valid/scores/summary.json runs/fixture_full/rules_only/scores/summary.json runs/fixture_full/similarity_to_best_active/scores/summary.json runs/fixture_full/qsar_rf/scores/summary.json runs/fixture_full/bare_llm/scores/summary.json runs/fixture_full/llm_validator/scores/summary.json runs/fixture_full/llm_tools/scores/summary.json runs/fixture_full/llm_tools_validator/scores/summary.json --out runs/fixture_full/compare
```

## Tests

Final result for this slice:

```text
10 passed
```

## Files Changed

- Added `inspect-cara` CLI and layout summary support.
- Hardened flat-table and support/query split ingestion.
- Added semantic card validation.
- Added bootstrap CI fields, metric denominators, failure taxonomy, metric winner
  tables, and ablation deltas.
- Added stable task-level LLM replay fixtures.
- Added `BENCHMARK_CARD.md`, `DATA_CARD.md`, and `paper/README.md`.

## Decisions

- Keep real CARA archive contents ignored by default.
- Treat stable `{system_name}__{task_id}.json` replay cache files as test/review
  fixtures; live runs still write content-addressed cache files.
- Keep `plans/active/0002-cara-ingestion.md` active until the real CARA archive
  download completes or is explicitly deferred.

## Follow-Up Work

- Inspect the actual downloaded CARA archive once available.
- Add any source-specific importer branch required by the observed CARA layout.
- Promote or revise `0003` and `0004` after official CARA ingestion is confirmed.
