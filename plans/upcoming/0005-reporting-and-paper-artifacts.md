# 0005 Reporting And Paper Artifacts

## Objective

Produce manuscript-ready result tables, figures, and reproducibility metadata.

## Scope

- Frontier plot polish.
- Paper tables.
- Run manifests.
- Data card and benchmark card updates.

## Non-Goals

- Do not write final manuscript claims before CARA runs complete.

## Affected Modules

- `specguard_chem_v2.reports`
- `paper`
- `docs`

## Tasks

- Add bootstrap CI columns.
- Add ablation tables.
- Add failure taxonomy report.
- Add reproducibility manifest.

## Validation Commands

```bash
uv run sgchem compare-runs runs/cara_lo/*/scores/summary.json --out paper/tables
uv run sgchem make-figures paper/tables/system_comparison.csv --out paper/figures
```

## Acceptance Criteria

- Main figure shows compliance rate vs feasible utility.
- Tables can be regenerated from run artifacts.
- Reports avoid unsupported medicinal-chemistry claims.

## Risks

- Too many metrics may obscure the main compliance-vs-utility claim.

## Handoff Notes

Lead with feasible utility, constrained regret, and violation rate.
