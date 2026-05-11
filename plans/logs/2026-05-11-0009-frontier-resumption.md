# 2026-05-11 0009 Frontier Resumption

## Summary

Resumed the original Paper-50 full-candidate frontier run without adding the
candidate-compression interface. Anthropic frontier completed all four systems.
OpenAI frontier completed three systems, then stopped on `insufficient_quota`
during `llm_tools_validator`. DeepSeek frontier long-token retry was attempted
with the new cache identity but did not return a first-card result before being
stopped.

The updated diagnostic comparison is
`paper/tables/cara_lo_paper_50_completed/primary_leaderboard.csv`.

## Commands Run

```bash
uv run pytest
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems llm_tools,llm_tools_validator --model-conditions anthropic_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions deepseek_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external --workers 4
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Frontier Resumption Results"
```

## Tests

```text
16 passed
```

## Files Changed

- Added generation settings to LLM request/cache metadata.
- Increased `deepseek_frontier.max_tokens` to `32768`.
- Added bounded `--workers` execution support for batch runs.
- Completed Anthropic frontier traces and scores.
- Completed OpenAI frontier `bare_llm`, `llm_validator`, and `llm_tools`.
- Regenerated `paper/tables/cara_lo_paper_50_completed/`,
  `paper/figures/cara_lo_paper_50_completed/`, and `paper/RESULTS_SUMMARY.md`.

## Decisions

- Kept the original full-candidate prompt interface unchanged.
- Used `--workers 4` for OpenAI after serial execution proved too slow. This is
  an execution-speed change only.
- Treated OpenAI `insufficient_quota` as a billing/quota blocker, not a
  transient retryable rate limit.
- Stopped the DeepSeek 32768-token attempt after it produced no first-card cache
  result for a sustained interval.

## Follow-Up Work

- Resume OpenAI frontier `llm_tools_validator` after quota is restored; 8 card
  responses are already cached.
- Rework DeepSeek frontier output strategy before another full retry. Simply
  increasing token budget was not sufficient operationally.
- Add resumable per-card trace writing so failed matrix runs preserve partial
  traces, not only cache files.
- Run the candidate-compression interface ablation as a later methodological
  check, not as part of the original-run completion.
