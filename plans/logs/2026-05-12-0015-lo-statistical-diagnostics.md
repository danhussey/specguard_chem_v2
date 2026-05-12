# 2026-05-12 0015 LO Statistical Diagnostics

## Summary

Added paired bootstrap deltas, card-level diagnostic tables/plots, and
consolidated failure-taxonomy summaries for the CARA LO paper-50 direct-JSON
result. No live LLM calls were made and no run traces were changed.

## Commands Run

```bash
uv run pytest
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json runs/cara_lo_paper_50_selector_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_direct_json_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_direct_json_completed
uv run sgchem make-report paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results"
uv run sgchem make-dashboard paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Dashboard"
```

The artifact-generation commands needed elevated sandbox access to read the
shared uv cache. They used existing local summaries, per-card scores, and
failure taxonomy files.

## Tests

- `uv run pytest`: passed, 19 tests.

## Files Changed

- `src/specguard_chem_v2/reports.py`
- `tests/test_runner_scoring_reports.py`
- `paper/RESULTS_SUMMARY.md`
- `paper/RESULTS_DASHBOARD.html`
- `paper/CARA_LO_PAPER_50_RESULTS.md`
- `paper/README.md`
- `paper/tables/cara_lo_paper_50_direct_json_completed/`
- `paper/figures/cara_lo_paper_50_direct_json_completed/`
- `docs/RUN_LEDGER.md`
- `plans/tech-debt.md`
- `plans/executed/0012-lo-result-statistical-diagnostics.md`

## Decisions

- Paired bootstrap deltas are computed over shared `task_id` card scores.
- `paired_bootstrap_deltas.csv` keeps all primary pairwise comparisons.
- `paired_bootstrap_key_deltas.csv` keeps the paper-facing comparisons.
- Failure taxonomy summaries aggregate final validation issues; raw LLM repair
  behavior remains represented separately through raw metrics and repair rates.

## Follow-Up Work

- Decide which key paired deltas should appear in the final manuscript tables.
- Keep additional experiments, including VS and compressed interfaces, separate
  from this LO consolidation.
