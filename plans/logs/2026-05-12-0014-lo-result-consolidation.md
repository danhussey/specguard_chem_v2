# 2026-05-12 0014 LO Result Consolidation

## Summary

Consolidated the completed CARA LO paper-50 results into paper-facing direct-JSON
artifacts. No live LLM calls were made and no run traces were changed.

## Commands Run

```bash
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_direct_json_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_direct_json_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results"
uv run sgchem make-dashboard paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Dashboard"
```

The first non-test `uv run sgchem` command needed elevated sandbox access to
read the shared uv cache. This was a local artifact-generation command, not a
provider call.

## Tests

- `uv run pytest`: passed, 19 tests.
- Browser QA on `paper/RESULTS_DASHBOARD.html`: confirmed direct-JSON title,
  provider/model/reasoning labels, QSAR explanation, hypothesis panel, and
  visible system-table labels without raw run IDs printed as the main label.

## Files Changed

- `src/specguard_chem_v2/reports.py`
- `configs/model_matrix.toml`
- `docs/COST_CONTROL.md`
- `docs/LLM_SYSTEMS.md`
- `docs/RUNBOOK.md`
- `docs/RUN_LEDGER.md`
- `paper/CARA_LO_PAPER_50_RESULTS.md`
- `paper/RESULTS_SUMMARY.md`
- `paper/RESULTS_DASHBOARD.html`
- `paper/tables/cara_lo_paper_50_direct_json_completed/`
- `paper/figures/cara_lo_paper_50_direct_json_completed/`
- `plans/executed/0011-lo-result-consolidation.md`

## Decisions

- Kept internal condition IDs such as `openai_frontier_selector` stable for
  cache/run reproducibility.
- Used paper-facing labels based on provider, model, reasoning/thinking setting,
  and prompt profile.
- Treated QSAR as a deployable per-card support-set baseline, not as oracle or
  ground truth.
- Kept VS, compressed inputs, high-reasoning pilots, and broader agent tooling
  out of this consolidation milestone.

## Follow-Up Work

- Future paper drafts should use `paper/tables/cara_lo_paper_50_direct_json_completed/`
  as the preferred LO result table source.
- Any high-reasoning rerun should first redesign or compress the full-pool input
  interface.
- Any VS analysis should be planned as a separate scope-control decision.
