# 0005 Reporting And Paper Artifacts

Status: completed on 2026-05-10. See
`plans/logs/2026-05-10-0006-reporting-and-paper-artifacts.md`.

## Objective

Produce manuscript-ready result tables, figures, and reproducibility metadata.

## Scope

- Frontier plot output.
- Paper-facing markdown summary.
- Run artifact manifests.
- Data card and benchmark card references.

## Non-Goals

- Do not write final manuscript claims before full CARA runs complete.

## Affected Modules

- `specguard_chem_v2.reports`
- `specguard_chem_v2.cli`
- `paper`
- `docs`

## Tasks Completed

- Added `make-report`.
- Generated primary and oracle sections from comparison CSV.
- Included source artifact paths and generation timestamp.
- Validated on fixture and local CARA smoke outputs.

## Validation Commands

```bash
uv run --extra dev pytest
uv run sgchem make-figures runs/cara_lo_all_local/compare/system_comparison.csv --out paper/figures
uv run sgchem make-report runs/cara_lo_all_local/compare/system_comparison.csv --out paper
```

## Acceptance Criteria

- Main figure shows compliance rate vs feasible utility.
- Summary report separates primary systems from oracle controls.
- Reports avoid unsupported medicinal-chemistry claims.

## Risks

- Too many metrics may obscure the main compliance-vs-utility claim.

## Handoff Notes

The initial implementation plan is now complete. Future work should create a new
active plan before adding paper-scale experiments, LLM live runs, or dataset
release packaging.
