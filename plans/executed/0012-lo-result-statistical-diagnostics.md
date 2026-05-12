# 0012 LO Result Statistical Diagnostics

## Objective

Strengthen the consolidated CARA LO paper-50 result without changing the
experiment by adding paired card-level comparisons, card-level plots, and
paper-level failure-taxonomy summaries.

## Scope

- Use existing `summary.json`, `card_scores.jsonl`, and `failure_taxonomy.csv`
  artifacts only.
- Extend report generation so `compare-runs` writes paired bootstrap and
  card-level diagnostic tables.
- Extend figure generation so `make-figures` writes card-level diagnostic plots
  when card-level tables are available.
- Update paper summaries and logs.

## Non-Goals

- Do not rerun live LLM providers.
- Do not alter trace files or card construction.
- Do not add VS, compressed inputs, or high-reasoning pilots.
- Do not change scoring definitions.

## Affected Modules

- `src/specguard_chem_v2/reports.py`
- `tests/test_runner_scoring_reports.py`
- `paper/`
- `docs/`
- `plans/`

## Tasks

- Generate `paired_bootstrap_deltas.csv` and key paired comparison deltas.
- Generate `card_level_key_systems.csv` and `card_level_diagnostics.csv`.
- Generate consolidated `failure_taxonomy_summary.csv` and
  `failure_taxonomy_by_group.csv`.
- Generate card-level utility distribution, delta distribution, and QSAR-vs-LLM
  scatter plots.
- Add report-summary sections for paired bootstrap and failure taxonomy.

## Validation Commands

```bash
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_direct_json_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_direct_json_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results"
uv run sgchem make-dashboard paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Dashboard"
```

## Acceptance Criteria

- New paired bootstrap, card-level, and failure-taxonomy tables exist under the
  direct-JSON table directory.
- New card-level figures exist under the direct-JSON figure directory.
- The generated summary explains paired bootstrap and failure taxonomy.
- Tests pass.
- No live provider calls are made.

## Risks

- Pairwise bootstrap tables can become large; key-delta tables provide the
  paper-facing subset.
- Failure taxonomy currently summarizes final validation issues; raw repair
  behavior remains represented through raw metrics and repair-rate fields.

## Handoff Notes

Completed on 2026-05-12. This is a reporting/statistics improvement only. Any
new experiment should be planned separately.
