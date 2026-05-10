# 2026-05-10 0003 Official CARA Ingestion

## Summary

Completed real CARA ingestion for the `LO_All` split. The downloader now resumes
partial archives and validates expected byte counts. The importer now detects
the official CARA `Task/*.tsv` plus `Split/*_support/query.json` layout and
resolves split row indices into normalized support/query records.

## Commands Run

```bash
uv run --extra dev pytest
uv run sgchem download-cara --out data/raw/cara --max-attempts 4
uv run sgchem inspect-cara data/raw/cara --out data/interim/cara_layout.json
uv run sgchem import-cara data/raw/cara --split-name LO_All --out data/interim/cara_lo_all_records.jsonl
uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl --out data/cards/cara_lo_all_cards.jsonl --target-cards 20 --budget-k 10 --support-size 50
uv run sgchem validate-cards data/cards/cara_lo_all_cards.jsonl
uv run sgchem run-suite data/cards/cara_lo_all_cards.jsonl --systems oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm --out runs/cara_lo_all_local
uv run sgchem compare-runs runs/cara_lo_all_local/oracle_valid_topk/scores/summary.json runs/cara_lo_all_local/random_valid/scores/summary.json runs/cara_lo_all_local/rules_only/scores/summary.json runs/cara_lo_all_local/similarity_to_best_active/scores/summary.json runs/cara_lo_all_local/qsar_rf/scores/summary.json runs/cara_lo_all_local/qsar_gbt/scores/summary.json runs/cara_lo_all_local/qsar_svm/scores/summary.json --out runs/cara_lo_all_local/compare
```

## Tests

Final result:

```text
11 passed
```

## Files Changed

- `src/specguard_chem_v2/data/cara.py`
- `src/specguard_chem_v2/cli.py`
- `tests/test_data_pipeline.py`
- `docs/CARA_LOCAL_AUDIT.md`
- `DATA_CARD.md`
- `AGENTS.md`
- `plans/executed/0002-cara-ingestion.md`

## Decisions

- Use `LO_All` as the default official CARA split for this project.
- Keep raw/interim/card artifacts ignored by Git.
- Treat the 20-card real-data smoke as a harness validation checkpoint, not as
  manuscript evidence.

## Follow-Up Work

- Promote `0003-baselines-and-scoring`.
- Add a deterministic card-selection policy for paper runs.
- Add optional export of small frozen card samples if needed for review packets.
