# CARA LO Paper-50 Results Snapshot

Generated on 2026-05-11 from the first paper-scale SpecGuard-Chem v2 run.

## Primary Result Set

Use the fast-complete result set for the clean primary analysis:

- `paper/tables/cara_lo_paper_50_fast_complete/primary_leaderboard.csv`
- `paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv`
- `paper/figures/cara_lo_paper_50_fast_complete/compliance_utility_frontier.png`

This set includes deterministic baselines plus complete fast-model LLM runs for
OpenAI, Anthropic, and DeepSeek across all four LLM system variants.

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
| `similarity_to_best_active` | 73.6032 | 0.8253 | 1.000 |
| `llm_validator__deepseek_fast` | 68.4017 | 0.7626 | 1.000 |
| `llm_tools_validator__openai_fast` | 67.7022 | 0.7515 | 1.000 |

## Frontier Status

Frontier conditions were attempted but are not the clean primary comparison:

- Anthropic frontier completed `bare_llm` and `llm_validator`, then stopped on
  credit balance during tool-enabled runs.
- OpenAI frontier stopped on account quota after 3 cached `bare_llm` card
  responses.
- DeepSeek frontier completed `bare_llm`, but reasoning consumed the completion
  budget and produced no final JSON selections, so it scored as schema failure.

## Interpretation Notes

- Treat `oracle_valid_topk` as an upper-bound control only.
- Treat the fast-complete matrix as the credible whole-run result.
- Treat `paper/tables/cara_lo_paper_50_completed/` as a broader diagnostic set
  that includes partial frontier traces.
- Do not claim that LLMs are intrinsically poor at medicinal chemistry from this
  run alone; a major follow-up is to reduce prompt overload and test compressed
  candidate summaries.
