# Metrics

Metrics separate utility from compliance.

## Utility

- `ndcg_at_k`: ranking quality using hidden activity as graded relevance.
- `mean_selected_activity`: mean true activity among valid selected candidates.
- `hit_recovery_at_k`: fraction of true hits recovered by the selected list.
- `enrichment_at_k`: selected hit rate divided by candidate-pool hit rate.
- `feasible_utility`: sum of hidden activity for valid selected candidates, with
  invalid selections contributing zero.
- `constrained_regret`: best possible valid top-k feasible utility minus observed
  feasible utility.
- `oracle_utility`: best possible valid top-k utility for the card. It is used
  only for regret and sanity checks, never exposed to systems.

## Compliance

- `compliance_rate`: valid selected entries divided by `budget_k`.
- `schema_error_rate`: malformed output rate.
- `pool_violation_count`: selected IDs absent from the candidate pool.
- `duplicate_count`: repeated selected IDs.
- `support_violation_count`: selected support IDs.
- `constraint_violation_count`: property or alert violations.
- `wrong_k`: output length differs from `budget_k`.

## Aggregation

Score each decision card first, then average over cards. Confidence intervals are
bootstrap intervals over decision cards, not over candidate rows.

## Raw Versus Final Metrics

For LLM systems, traces may contain both raw model output and final output after
deterministic validator repair. Raw metrics score `raw_output` with `raw_issues`.
Final metrics score `output` with `issues`.

- `raw_feasible_utility`, `raw_ndcg_at_k`, `raw_compliance_rate`, and
  `raw_schema_error_rate` measure model behavior before repair.
- `repaired_rate` is the fraction of cards where validator repair changed an
  invalid raw output.
- `repaired_from_empty_rate` is the fraction of cards repaired after the raw
  model returned no usable selections.
- `repair_delta_feasible_utility` is final feasible utility minus raw feasible
  utility.

When raw fields are blank, the trace was produced before raw-output persistence
was added. Do not infer raw LLM quality from those historical rows.

`score-run` writes:

- `card_scores.jsonl`
- `summary.json`
- `metric_denominators.json`
- `failure_taxonomy.csv`

`compare-runs` writes system comparison, metric winner, and ablation-delta tables.
It also writes `primary_leaderboard.csv` and `oracle_controls.csv` so oracle rows
are not accidentally mixed into the main leaderboard.

Oracle rows such as `oracle_valid_topk` are sanity controls. They should be kept
out of primary system leaderboards unless explicitly labelled as oracle-assisted.
