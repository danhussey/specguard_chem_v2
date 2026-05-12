# 2026-05-12 0013 Direct-JSON Matrix Completion

## Summary

Completed the full paper-50 direct-JSON frontier matrix with cost gates enabled.
All OpenAI, Anthropic, and DeepSeek direct-JSON provider/system traces now have
50 rows. Regenerated comparison tables, frontier figure, and report summary.

## Commands Run

```bash
uv run sgchem estimate-llm-cost data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier_selector,anthropic_frontier_selector,deepseek_frontier_selector --out-run-dir runs/cara_lo_paper_50_selector_matrix --out runs/cara_lo_paper_50_selector_matrix/cost_estimate_before_resume.json
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions anthropic_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --require-cost-estimate --max-estimated-cost-usd 60 --max-live-calls 160 --max-input-tokens-per-call 175000 --workers 1
uv run pytest
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions anthropic_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --require-cost-estimate --max-estimated-cost-usd 35 --max-live-calls 90 --max-input-tokens-per-call 175000 --workers 1
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems llm_tools,llm_tools_validator --model-conditions openai_frontier_selector --out runs/cara_lo_paper_50_selector_matrix --allow-external --require-cost-estimate --max-estimated-cost-usd 35 --max-live-calls 90 --max-input-tokens-per-call 175000 --workers 2
uv run sgchem estimate-llm-cost data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier_selector,anthropic_frontier_selector,deepseek_frontier_selector --out-run-dir runs/cara_lo_paper_50_selector_matrix --out runs/cara_lo_paper_50_selector_matrix/cost_estimate_after_complete.json
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_selector_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_selector_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_selector_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_selector_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results"
```

## Tests

- `uv run pytest`: 19 passed.

## Files Changed

- Completed Anthropic direct-JSON traces and scores.
- Completed OpenAI direct-JSON tool traces and scores.
- Updated direct-JSON comparison tables, figure, and report.
- Added before/after cost-estimate artifacts.
- Updated run ledger and executed plan handoff notes.

## Decisions

- Anthropic was run with one worker to avoid the prior overload pattern.
- OpenAI was run with two workers after the cost gate passed.
- A malformed Anthropic JSON response during `llm_tools` caused an abort before
  parser hardening. After adding one parse retry and parse-failure capture, the
  retry completed without parse failures in final traces.

## Results Snapshot

- Comparison rows: 40 systems.
- Best deployable baseline: `qsar_svm`, feasible utility `81.3823`.
- Best direct-JSON LLM final row:
  `llm_validator__openai_frontier_selector`, feasible utility `78.1884`, raw
  feasible utility `76.7580`, repaired rate `0.14`, repaired-from-empty rate
  `0.0`.
- Best direct-JSON tool row:
  `llm_tools_validator__openai_frontier_selector`, feasible utility `77.6875`,
  raw feasible utility `77.2091`, repaired rate `0.04`.
- Best Anthropic direct-JSON row:
  `llm_tools_validator__anthropic_frontier_selector`, feasible utility
  `74.4707`, raw feasible utility `62.8591`, repaired rate `0.58`.
- Best DeepSeek direct-JSON row:
  `llm_validator__deepseek_frontier_selector`, feasible utility `67.6213`, raw
  feasible utility `49.2013`, repaired rate `0.56`.

## Cost Snapshot

- Before resume estimate: 234 missing live calls, estimated incremental cost
  `$79.26`.
- After completion estimate: 0 missing live calls.
- Approximate usage-derived selector-matrix cost by provider:
  Anthropic `$44.16`, OpenAI `$35.86`, DeepSeek `$2.78`, total `$82.80`.

## Follow-Up Work

- Rename `selector` configs/artifacts to `direct_json`.
- Add a compressed or staged high-reasoning interface before any high-reasoning
  full matrix.
- Add actual-usage cost summaries to the cost-estimate command so the above cost
  snapshot does not require an ad hoc script.
