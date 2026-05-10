# 2026-05-10 0006 Reporting And Paper Artifacts

## Summary

Completed the initial reporting slice. The CLI can generate frontier plots and a
paper-facing markdown summary from comparison CSV files, with primary systems
separated from oracle controls.

## Commands Run

```bash
uv run --extra dev pytest
uv run sgchem make-figures runs/cara_lo_all_local/compare/system_comparison.csv --out paper/figures
uv run sgchem make-report runs/cara_lo_all_local/compare/system_comparison.csv --out paper
```

## Tests

Final result:

```text
12 passed
```

## Files Changed

- `.gitignore`
- `src/specguard_chem_v2/reports.py`
- `src/specguard_chem_v2/cli.py`
- `README.md`
- `docs/RUNBOOK.md`
- `paper/README.md`
- report tests

## Decisions

- Generated `paper/RESULTS_SUMMARY.md` is ignored because it includes a timestamp
  and should be regenerated from run artifacts.
- Paper-facing summaries must explicitly separate primary systems and oracle
  controls.

## Follow-Up Work

- Create a new plan for paper-scale experiment execution.
- Add optional frozen public sample cards if needed for a review artifact.
- Add live LLM run caches only after prompts and card selection are frozen.
