# 0007 Paper-Scale Full Results Run

Status: completed on 2026-05-11. See
`plans/logs/2026-05-11-0008-paper-scale-full-results-run.md`.

## Objective

Produce the first full results artifact set for CARA LO constrained top-k
prioritisation, including deterministic baselines, oracle controls, and the
configured live LLM provider/model matrix.

## Scope

- Freeze a 50-card CARA LO decision-card artifact.
- Record checksums and card summary.
- Run deterministic baselines and oracle controls.
- Export LLM matrix requests for review.
- Run live LLM matrix with OpenAI, Anthropic, and DeepSeek conditions.
- Compare all scored systems and generate figures/report artifacts.
- Record exact commands, validation, failures, and follow-up work.

## Non-Goals

- Do not change metric definitions during the run.
- Do not inspect hidden candidate activity to tune prompts or systems.
- Do not modify the sibling `../specguard-chem` repository.

## Affected Modules And Artifacts

- `data/cards/cara_lo_paper_50.jsonl`
- `runs/cara_lo_paper_50_*`
- `paper/tables`
- `paper/figures`
- `paper/RESULTS_SUMMARY.md`
- `plans/logs`

## Tasks Completed

- Built 50 cards from `data/interim/cara_lo_all_records.jsonl` with
  `budget_k=10`, `support_size=50`, and
  `selection_policy=largest_candidate_pool`.
- Validated and summarized the frozen card artifact.
- Ran deterministic systems:
  `oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm`.
- Exported 1,200 LLM requests for all four LLM systems across all configured
  model conditions.
- Ran complete fast-model LLM matrix for OpenAI, Anthropic, and DeepSeek.
- Ran partial frontier diagnostics where provider quota/throughput allowed.
- Compared completed summaries and generated report/figure artifacts.

## Validation Commands

```bash
uv run pytest
uv run sgchem validate-cards data/cards/cara_lo_paper_50.jsonl
uv run sgchem summarize-cards data/cards/cara_lo_paper_50.jsonl --out data/cards/cara_lo_paper_50.summary.json
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/anthropic_fast/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/deepseek_fast/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/openai_fast/*/scores/summary.json --out paper/tables/cara_lo_paper_50_fast_complete
uv run sgchem make-figures paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv --out paper/figures/cara_lo_paper_50_fast_complete
uv run sgchem make-report paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Fast-Complete Results"
```

## Acceptance Criteria

- Card artifact validates.
- Deterministic baseline traces and scores exist for all mandatory baselines.
- Complete fast-model LLM traces and scores exist for OpenAI, Anthropic, and
  DeepSeek across all four LLM system variants.
- Frontier-model attempts are explicitly logged with completed traces and
  provider blockers.
- Comparison tables, frontier figure, and report summary are generated.
- Execution log records commands, tests, files changed/generated, decisions, and
  follow-up work.

## Risks

- Provider APIs may reject configured model IDs or JSON-output parameters.
- Full live frontier runs may be slow or hit account quotas.
- LLM outputs may be malformed; validator conditions repair, non-validator
  conditions are scored as produced.

## Handoff Notes

Use `paper/tables/cara_lo_paper_50_fast_complete/primary_leaderboard.csv` as the
clean primary result table. Use `paper/tables/cara_lo_paper_50_completed/` as a
broader diagnostic table that includes partial frontier conditions. Resume
frontier conditions only after provider quota and prompt-size strategy are
reviewed.
