# 0003 Baselines And Scoring Hardening

## Objective

Upgrade the first baseline and scoring implementations into paper-ready
experimental components.

## Scope

- Validate QSAR settings.
- Add bootstrap confidence intervals.
- Add per-task and aggregate metric sanity checks.
- Add failure taxonomy summaries.

## Non-Goals

- Do not tune baselines on test performance.

## Affected Modules

- `specguard_chem_v2.systems.baselines`
- `specguard_chem_v2.scoring`
- `specguard_chem_v2.reports`

## Tasks

- Compare RF settings on fixture and dev cards.
- Add metric denominator reports.
- Add oracle top-k sanity checks.
- Add tests for regret and invalid-output policy.

## Validation Commands

```bash
uv run pytest
uv run sgchem run-suite data/cards/cara_lo_cards.jsonl --systems random_valid,rules_only,similarity_to_best_active,qsar_rf --out runs/cara_baselines
```

## Acceptance Criteria

- Baseline outputs are deterministic under seed.
- Metric definitions match `docs/METRICS.md`.
- Comparison tables include all headline metrics.

## Risks

- QSAR may fail on very small support sets.

## Handoff Notes

Prefer conservative fallbacks over silent row dropping.
