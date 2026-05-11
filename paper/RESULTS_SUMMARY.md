# SpecGuard-Chem v2 CARA LO Paper-50 Frontier Resumption Results

Generated at: `2026-05-11T05:27:03.234697+00:00`

Source comparison CSV: `paper/tables/cara_lo_paper_50_completed/system_comparison.csv`

This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.

## Primary Systems

| system_name | feasible_utility | ndcg_at_k | constrained_regret | compliance_rate | schema_error_rate |
| --- | --- | --- | --- | --- | --- |
| qsar_svm | 81.382 | 0.910 | 7.639 | 1.000 | 0.000 |
| qsar_gbt | 80.888 | 0.900 | 8.134 | 1.000 | 0.000 |
| qsar_rf | 80.634 | 0.901 | 8.388 | 1.000 | 0.000 |
| llm_tools_validator__anthropic_frontier | 73.979 | 0.832 | 15.043 | 1.000 | 0.000 |
| llm_validator__anthropic_frontier | 73.739 | 0.831 | 15.283 | 1.000 | 0.000 |
| similarity_to_best_active | 73.603 | 0.825 | 15.418 | 1.000 | 0.000 |
| llm_validator__deepseek_fast | 68.402 | 0.763 | 20.620 | 1.000 | 0.000 |
| llm_tools_validator__openai_fast | 67.702 | 0.752 | 21.320 | 1.000 | 0.000 |
| llm_tools_validator__anthropic_fast | 67.225 | 0.750 | 21.796 | 1.000 | 0.000 |
| llm_tools_validator__deepseek_fast | 67.217 | 0.749 | 21.804 | 1.000 | 0.000 |
| llm_validator__openai_fast | 67.000 | 0.744 | 22.022 | 1.000 | 0.000 |
| llm_validator__anthropic_fast | 66.881 | 0.741 | 22.141 | 1.000 | 0.000 |
| random_valid | 66.843 | 0.739 | 22.178 | 1.000 | 0.000 |
| rules_only | 66.043 | 0.731 | 22.979 | 1.000 | 0.000 |
| llm_validator__openai_frontier | 66.043 | 0.731 | 22.979 | 1.000 | 0.000 |
| llm_tools__anthropic_frontier | 59.422 | 0.622 | 29.600 | 0.778 | 0.000 |
| llm_tools__anthropic_fast | 55.432 | 0.610 | 33.589 | 0.810 | 0.000 |
| bare_llm__anthropic_frontier | 53.323 | 0.579 | 35.699 | 0.682 | 0.000 |
| llm_tools__openai_fast | 51.390 | 0.547 | 37.631 | 0.738 | 0.000 |
| bare_llm__openai_fast | 51.067 | 0.557 | 37.954 | 0.732 | 0.000 |
| bare_llm__anthropic_fast | 50.120 | 0.550 | 38.902 | 0.750 | 0.000 |
| llm_tools__deepseek_fast | 33.526 | 0.373 | 55.496 | 0.512 | 0.040 |
| bare_llm__deepseek_fast | 26.162 | 0.281 | 62.860 | 0.366 | 0.000 |
| bare_llm__deepseek_frontier | 0.000 | 0.000 | 89.022 | 0.000 | 1.000 |
| bare_llm__openai_frontier | 0.000 | 0.000 | 89.022 | 0.000 | 1.000 |
| llm_tools__openai_frontier | 0.000 | 0.000 | 89.022 | 0.000 | 1.000 |

## Oracle Controls

| system_name | feasible_utility | ndcg_at_k | constrained_regret | compliance_rate | schema_error_rate |
| --- | --- | --- | --- | --- | --- |
| oracle_valid_topk | 89.022 | 1.000 | 0.000 | 1.000 | 0.000 |

## Reading Guide

- Higher feasible utility and NDCG@k are better.
- Lower constrained regret and schema error rate are better.
- Oracle controls are sanity checks and must not be mixed into primary system claims.
