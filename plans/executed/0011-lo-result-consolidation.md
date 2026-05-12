# 0011 LO Result Consolidation

## Objective

Consolidate the completed CARA LO paper-50 results into clearer paper-facing
artifacts without changing the experiment, rerunning live LLM calls, or adding
new scope.

## Scope

- Use existing scored runs only.
- Replace reader-facing `frontier` / `selector` shorthand with provider,
  model, reasoning/thinking, and prompt-profile labels.
- Regenerate preferred paper tables and figures under direct-JSON artifact
  names.
- Update the paper-facing results narrative and run ledger.

## Non-Goals

- Do not run VS cards.
- Do not add compressed candidate inputs or shortlist reranking.
- Do not run high-reasoning/thinking pilots.
- Do not rename internal cache, run, or model-condition IDs.
- Do not implement a broader agent where QSAR is a callable tool.

## Affected Modules

- `src/specguard_chem_v2/reports.py`
- `configs/model_matrix.toml`
- `paper/`
- `docs/`
- `plans/`

## Tasks

- Add paper-facing labels derived from model metadata and condition settings.
- Clarify QSAR descriptions as per-card deployable baselines trained on support
  data only.
- Regenerate comparison tables, figures, report summary, and dashboard from
  existing summaries.
- Update the paper results snapshot with methods/results/discussion framing.
- Record this consolidation in the run ledger and execution log.

## Validation Commands

```bash
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_direct_json_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_direct_json_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results"
uv run sgchem make-dashboard paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Dashboard"
```

## Acceptance Criteria

- Preferred paper tables and figures exist under `direct_json_completed`.
- Reports show model names and reasoning/thinking settings rather than ambiguous
  reader-facing `frontier` / `selector` labels.
- QSAR is described as a serious deployable baseline, not as oracle or ground
  truth.
- Raw model behavior remains distinct from validator-repaired final behavior.
- No live provider calls are made.

## Risks

- Renaming internal IDs would break reproducibility; this plan keeps them
  stable and only changes paper-facing labels/artifact names.
- Tables become wider after adding display labels and confidence intervals; keep
  raw IDs available through tooltips and CSV IDs.

## Handoff Notes

Completed on 2026-05-12. The old `selector_completed` artifacts remain
historical aliases. Future agents should prefer `direct_json_completed` for
paper-facing interpretation.
