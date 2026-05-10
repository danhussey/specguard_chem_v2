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

`score-run` writes:

- `card_scores.jsonl`
- `summary.json`
- `metric_denominators.json`
- `failure_taxonomy.csv`

`compare-runs` writes system comparison, metric winner, and ablation-delta tables.

Oracle rows such as `oracle_valid_topk` are sanity controls. They should be kept
out of primary system leaderboards unless explicitly labelled as oracle-assisted.
