# 2026-05-11 0010 OpenAI Frontier Completion

## Summary

Resumed only the remaining OpenAI frontier `llm_tools_validator` condition after
API quota was topped up. DeepSeek was intentionally left untouched. The OpenAI
frontier matrix is now complete across all four systems.

The resumed `llm_tools_validator__openai_frontier` condition produced no raw
candidate IDs on all 50 cards because the model consumed the full 4096
completion-token budget as reasoning tokens. The deterministic validator
repaired each empty output using fallback ranking, so the scored result matches
the rules-only baseline.

## Commands Run

```bash
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems llm_tools_validator --model-conditions openai_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external --workers 4
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 OpenAI Frontier Completion Results"
```

## Tests

No code changes were made in this step. The previous code state passed:

```text
16 passed
```

## Files Changed

- Completed `runs/cara_lo_paper_50_llm_matrix/openai_frontier/llm_tools_validator/`.
- Regenerated `paper/tables/cara_lo_paper_50_completed/`.
- Regenerated `paper/figures/cara_lo_paper_50_completed/`.
- Regenerated `paper/RESULTS_SUMMARY.md`.
- Updated the Paper-50 result snapshot and technical debt notes.

## Decisions

- Ignored DeepSeek for this continuation, per user direction.
- Kept the original full-candidate prompt interface unchanged.
- Treated OpenAI frontier validator systems as successful execution but not
  useful raw LLM selection because outputs were validator-repaired from empty
  selections.

## Follow-Up Work

- Add provider-specific reasoning/output controls before retrying reasoning
  frontier models on the full-pool interface.
- Keep candidate-summary compression as a later interface ablation rather than
  changing this original-run result.
