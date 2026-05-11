# CARA LO Paper-50 Results Snapshot

Generated on 2026-05-11 from the paper-scale SpecGuard-Chem v2 run and
frontier resumption attempt.

## Primary Result Set

Use the completed fast-model result set for the clean cross-provider primary
analysis:

- `paper/tables/cara_lo_paper_50_fast_complete/primary_leaderboard.csv`
- `paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv`
- `paper/figures/cara_lo_paper_50_fast_complete/compliance_utility_frontier.png`

This set includes deterministic baselines plus complete fast-model LLM runs for
OpenAI, Anthropic, and DeepSeek across all four LLM system variants.

Use the frontier-resumption result set as the broader diagnostic analysis:

- `paper/tables/cara_lo_paper_50_completed/primary_leaderboard.csv`
- `paper/tables/cara_lo_paper_50_completed/system_comparison.csv`
- `paper/figures/cara_lo_paper_50_completed/compliance_utility_frontier.png`

This diagnostic set now includes all Anthropic and OpenAI frontier systems.
DeepSeek frontier remains blocked by reasoning/output behavior and is deferred.

## Card Artifact

```text
data/cards/cara_lo_paper_50.jsonl
sha256: 9c4e45880dd6fe97643c1bcfd66a16a0f72b4a0e0a60476f12bc58d464d80d03
num_cards: 50
budget_k: 10
support_size: 50
selection_policy: largest_candidate_pool
mean_candidate_pool_size: 292.16
mean_feasible_candidate_count: 162.4
```

## Headline Finding

QSAR baselines outperformed completed LLM-agent conditions on feasible utility.
Validators improved LLM compliance and feasible utility, but did not close the
gap to QSAR.

| System | Feasible utility | NDCG@k | Compliance |
| --- | ---: | ---: | ---: |
| `qsar_svm` | 81.3823 | 0.9096 | 1.000 |
| `qsar_gbt` | 80.8879 | 0.9002 | 1.000 |
| `qsar_rf` | 80.6341 | 0.9006 | 1.000 |
| `llm_tools_validator__anthropic_frontier` | 73.9792 | 0.8323 | 1.000 |
| `llm_validator__anthropic_frontier` | 73.7389 | 0.8310 | 1.000 |
| `similarity_to_best_active` | 73.6032 | 0.8253 | 1.000 |
| `llm_validator__deepseek_fast` | 68.4017 | 0.7626 | 1.000 |
| `llm_tools_validator__openai_fast` | 67.7022 | 0.7515 | 1.000 |

## Frontier Status

Frontier conditions were resumed but are not yet a complete clean
cross-provider comparison:

- Anthropic frontier completed all four systems. Its best frontier condition was
  `llm_tools_validator__anthropic_frontier` with feasible utility `73.9792`.
- OpenAI frontier completed all four systems. `bare_llm` and `llm_tools`
  consumed the full 4096 completion budget as reasoning tokens and produced no
  final JSON, so they scored as schema failures. `llm_validator` and
  `llm_tools_validator` repaired empty outputs using deterministic fallback
  ranking and therefore matched the rules-only score.
- DeepSeek frontier `bare_llm` remains the original schema-failure trace. The
  32768-token rerun attempt did not return a first-card result before being
  stopped, so no new DeepSeek frontier trace was written.

## Interpretation Notes

- Treat `oracle_valid_topk` as an upper-bound control only.
- Treat the fast-complete matrix as the credible whole-run result.
- Treat `paper/tables/cara_lo_paper_50_completed/` as a broader diagnostic set
  that includes completed Anthropic/OpenAI frontier traces and the explicitly
  logged DeepSeek blocker.
- Do not claim that LLMs are intrinsically poor at medicinal chemistry from this
  run alone; a major follow-up is to reduce prompt overload and test compressed
  candidate summaries.
