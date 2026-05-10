# 0003 Baselines And Scoring Hardening

Status: completed on 2026-05-10. See
`plans/logs/2026-05-10-0004-baselines-and-scoring.md`.

## Objective

Upgrade baseline and scoring outputs into paper-ready experimental components.

## Scope

- Deterministic card-selection controls.
- Card inventory reports.
- Primary-vs-oracle leaderboard separation.
- Metric sanity outputs.
- Tests for regret and invalid-output policy.

## Non-Goals

- Do not tune baselines on test performance.
- Do not make live LLM calls.

## Affected Modules

- `specguard_chem_v2.data.cara`
- `specguard_chem_v2.reports`
- `specguard_chem_v2.scoring`
- `specguard_chem_v2.cli`
- `tests`

## Tasks Completed

- Added deterministic `build-cards --selection-policy`.
- Added `summarize-cards`.
- Split comparison outputs into `primary_leaderboard.csv` and
  `oracle_controls.csv`.
- Added `metric_winners_primary.csv`.
- Regenerated the local CARA smoke card artifact with explicit selection-policy
  metadata.
- Ran fixture and CARA smoke validation.

## Validation Commands

```bash
uv run --extra dev pytest
uv run sgchem summarize-cards data/cards/cara_lo_all_cards.jsonl --out data/cards/cara_lo_all_cards.summary.json
uv run sgchem compare-runs runs/cara_lo_all_local/oracle_valid_topk/scores/summary.json runs/cara_lo_all_local/random_valid/scores/summary.json runs/cara_lo_all_local/rules_only/scores/summary.json runs/cara_lo_all_local/similarity_to_best_active/scores/summary.json runs/cara_lo_all_local/qsar_rf/scores/summary.json runs/cara_lo_all_local/qsar_gbt/scores/summary.json runs/cara_lo_all_local/qsar_svm/scores/summary.json --out runs/cara_lo_all_local/compare
```

## Acceptance Criteria

- Baseline outputs remain deterministic under seed.
- Metric definitions match `docs/METRICS.md`.
- Comparison tables include all headline metrics.
- Oracle controls are clearly separated from primary system rows.

## Risks

- Card-selection policy can accidentally become benchmark tuning if changed
  after seeing results.

## Handoff Notes

Promote `plans/upcoming/0004-llm-agent-systems.md` next. Keep oracle rows out of
primary paper claims unless clearly labelled as controls.
