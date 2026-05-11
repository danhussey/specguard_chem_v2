# 0008 Complete Paper-50 Frontier Run

## Objective

Complete the original full-candidate Paper-50 frontier run without adding the
candidate-compression interface experiment.

## Scope

- Resume incomplete Anthropic and OpenAI frontier conditions.
- Rerun DeepSeek frontier with a larger output budget.
- Preserve cache/replay behavior and avoid replaying stale DeepSeek 4096-token
  failures after the budget change.
- Regenerate completed comparison tables, figures, report text, and execution
  logs.

## Non-Goals

- Do not add candidate compression, shortlist reranking, or active-learning
  metrics.
- Do not change the frozen card artifact or candidate-pool representation.
- Do not substitute weaker frontier models if quota or model access still fails.

## Affected Modules

- LLM request/cache construction.
- Provider model matrix.
- Paper-50 run artifacts and plans/logs.

## Tasks

- Add generation settings to LLM request/cache metadata.
- Make exact hashed cache paths preferred over legacy cache paths.
- Increase `deepseek_frontier.max_tokens` to `32768`.
- Add regression coverage for token-budget cache separation.
- Run tests and commit the code/config fix.
- Resume the Anthropic, OpenAI, and DeepSeek frontier runs.
- Regenerate scoring and report artifacts.
- Commit completed run artifacts and update logs.

## Validation Commands

```bash
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Completed Results"
```

## Acceptance Criteria

- All tests pass.
- Each intended frontier system has a 50-row trace and scored summary, unless a
  provider blocker is logged.
- DeepSeek frontier uses the new long-token request cache identity.
- Completed tables and figures regenerate from the scored traces.

## Risks

- Provider quota or access errors may still block completion.
- DeepSeek may continue to spend the output budget on reasoning and produce no
  final JSON.
- Full-pool prompts remain large and expensive by design for this original-run
  completion.

## Handoff Notes

This plan intentionally defers candidate-summary compression. Treat any
compression work as a later interface ablation, not part of this run.

Execution completed with provider blockers rather than a fully complete
frontier matrix. See `plans/logs/2026-05-11-0009-frontier-resumption.md`.
