# 2026-05-11 0011 Reasoning-Budget Fairness Selector Partial

## Summary

Implemented raw-vs-repaired trace and scoring support, added selector and
reasoning-budget provider configs, and ran selector preflights plus the first
paper-50 selector matrix attempts. DeepSeek selector completed all four systems.
OpenAI selector completed `bare_llm` and `llm_validator` before quota blocked the
tool conditions. Anthropic selector preflight succeeded, but the full run was
blocked by provider overload followed by low API credit.

## Commands Run

```bash
uv run pytest
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_frontier_selector --model-matrix configs/model_matrix.toml --out /tmp/sgchem_selector_requests.jsonl
uv run sgchem list-model-matrix configs/model_matrix.toml
sed -n '1p' data/cards/cara_lo_paper_50.jsonl > /tmp/sgchem_one_card.jsonl
uv run --extra providers sgchem run-llm-matrix /tmp/sgchem_one_card.jsonl --systems llm_tools_validator --model-conditions openai_frontier_selector --out runs/preflight_selector_20260511 --allow-external
uv run --extra providers sgchem run-llm-matrix /tmp/sgchem_one_card.jsonl --systems llm_tools_validator --model-conditions anthropic_frontier_selector --out runs/preflight_selector_20260511 --allow-external
uv run --extra providers sgchem run-llm-matrix /tmp/sgchem_one_card.jsonl --systems llm_tools_validator --model-conditions deepseek_frontier_selector --out runs/preflight_selector_20260511 --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --workers 4
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions anthropic_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --workers 4
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions anthropic_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --workers 1
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions deepseek_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --workers 4
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_selector_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_selector_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_selector_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_selector_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Selector Results"
```

## Tests

- `uv run pytest`: 18 passed.
- Request export smoke check succeeded after sandbox escalation for uv cache
  access.
- Model matrix listing includes selector and reasoning-budget configs.

## Files Changed

- Added raw-output fields to run records and raw-vs-final score fields.
- Added `prompt_profile`, `thinking_budget_tokens`, and request timeout controls.
- Added `json_first` prompt profile and selector/reasoning-budget model configs.
- Updated LLM, metric, and runbook docs.
- Regenerated selector comparison tables, frontier plot, and report summary.

## Decisions

- OpenAI rejected `reasoning_effort = "minimal"` for `gpt-5.5`; the selector
  config was changed to the predefined fallback `low`.
- Historical high-reasoning OpenAI/DeepSeek results were not overwritten.
- Candidate compression remains out of scope for this run.
- Reasoning-budget pilot was not started because the selector matrix is not yet
  complete.

## Results Snapshot

- Comparison rows: 34 systems.
- DeepSeek selector completed all four systems.
- OpenAI selector completed `bare_llm` and `llm_validator`.
- Anthropic selector full run has no complete scored system yet.
- Best new selector row so far: `llm_validator__openai_frontier_selector`,
  feasible utility `78.1884`, raw feasible utility `76.7580`, repaired rate
  `0.14`, repaired-from-empty rate `0.0`.

## Provider Blockers

- OpenAI full selector run failed during `llm_tools` with `429 insufficient_quota`.
- Anthropic full selector run first failed with `529 overloaded`; retrying with
  one worker then failed with low API credit.

## Follow-Up Work

- Resume OpenAI selector for `llm_tools` and `llm_tools_validator` after API
  quota is available; 19 `llm_tools` cache files already exist.
- Resume Anthropic selector after API credits are available; 47 `bare_llm` cache
  files already exist.
- Re-run comparison/report generation after the remaining selector rows finish.
- Start the 10-card reasoning-budget pilot only after the selector matrix is
  complete.
