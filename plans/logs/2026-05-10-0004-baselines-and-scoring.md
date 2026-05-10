# 2026-05-10 0004 Baselines And Scoring

## Summary

Completed baseline/scoring hardening. Card builds now record deterministic
selection policy, card packages can be summarized through the CLI, and comparison
reports split primary leaderboard rows from oracle controls.

## Commands Run

```bash
uv run --extra dev pytest
uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl --out data/cards/cara_lo_all_cards.jsonl --target-cards 20 --budget-k 10 --support-size 50 --selection-policy first
uv run sgchem validate-cards data/cards/cara_lo_all_cards.jsonl
uv run sgchem summarize-cards data/cards/cara_lo_all_cards.jsonl --out data/cards/cara_lo_all_cards.summary.json
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
- `src/specguard_chem_v2/reports.py`
- `docs/METRICS.md`
- `docs/RUNBOOK.md`
- `docs/CARA_LOCAL_AUDIT.md`
- tests for CLI, card summaries, and comparison outputs

## Decisions

- Use `first` as the documented local-smoke card-selection policy.
- Write primary and oracle comparison tables separately.
- Keep `oracle_valid_topk` available as a sanity control but out of primary
  leaderboard outputs.

## Follow-Up Work

- Promote `0004-llm-agent-systems`.
- Add real-card cached LLM smoke fixtures or run live calls explicitly.
- Add paper-ready figures in `0005`.
