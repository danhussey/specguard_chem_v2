# SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results

Generated at: `2026-05-12T06:07:32.990843+00:00`

Source comparison CSV: `paper/tables/cara_lo_paper_50_selector_completed/system_comparison.csv`

This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.

## Primary Systems

| system_name | feasible_utility | raw_feasible_utility | ndcg_at_k | raw_ndcg_at_k | constrained_regret | compliance_rate | raw_compliance_rate | schema_error_rate | raw_schema_error_rate | repaired_from_empty_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qsar_svm | 81.382 |  | 0.910 |  | 7.639 | 1.000 |  | 0.000 |  |  |
| qsar_gbt | 80.888 |  | 0.900 |  | 8.134 | 1.000 |  | 0.000 |  |  |
| qsar_rf | 80.634 |  | 0.901 |  | 8.388 | 1.000 |  | 0.000 |  |  |
| llm_validator__openai_frontier_selector | 78.188 | 76.758 | 0.881 | 0.868 | 10.833 | 1.000 | 0.976 | 0.000 | 0.000 | 0.000 |
| llm_tools_validator__openai_frontier_selector | 77.688 | 77.209 | 0.873 | 0.866 | 11.334 | 1.000 | 0.994 | 0.000 | 0.000 | 0.000 |
| llm_tools__openai_frontier_selector | 77.173 | 77.173 | 0.870 | 0.870 | 11.849 | 0.990 | 0.990 | 0.000 | 0.000 | 0.000 |
| bare_llm__openai_frontier_selector | 75.781 | 75.781 | 0.847 | 0.847 | 13.241 | 0.962 | 0.962 | 0.000 | 0.000 | 0.000 |
| llm_tools_validator__anthropic_frontier_selector | 74.471 | 62.859 | 0.834 | 0.684 | 14.551 | 1.000 | 0.822 | 0.000 | 0.020 | 0.000 |
| llm_validator__anthropic_frontier_selector | 74.274 | 55.388 | 0.832 | 0.602 | 14.748 | 1.000 | 0.710 | 0.000 | 0.000 | 0.000 |
| llm_tools_validator__anthropic_frontier | 73.979 |  | 0.832 |  | 15.043 | 1.000 |  | 0.000 |  |  |
| llm_validator__anthropic_frontier | 73.739 |  | 0.831 |  | 15.283 | 1.000 |  | 0.000 |  |  |
| similarity_to_best_active | 73.603 |  | 0.825 |  | 15.418 | 1.000 |  | 0.000 |  |  |
| llm_validator__deepseek_fast | 68.402 |  | 0.763 |  | 20.620 | 1.000 |  | 0.000 |  |  |
| llm_tools_validator__openai_fast | 67.702 |  | 0.752 |  | 21.320 | 1.000 |  | 0.000 |  |  |
| llm_validator__deepseek_frontier_selector | 67.621 | 49.201 | 0.752 | 0.551 | 21.400 | 1.000 | 0.726 | 0.000 | 0.000 | 0.000 |
| llm_tools_validator__anthropic_fast | 67.225 |  | 0.750 |  | 21.796 | 1.000 |  | 0.000 |  |  |
| llm_tools_validator__deepseek_fast | 67.217 |  | 0.749 |  | 21.804 | 1.000 |  | 0.000 |  |  |
| llm_validator__openai_fast | 67.000 |  | 0.744 |  | 22.022 | 1.000 |  | 0.000 |  |  |
| llm_tools_validator__deepseek_frontier_selector | 66.948 | 57.849 | 0.740 | 0.635 | 22.074 | 1.000 | 0.864 | 0.000 | 0.000 | 0.000 |
| llm_validator__anthropic_fast | 66.881 |  | 0.741 |  | 22.141 | 1.000 |  | 0.000 |  |  |
| random_valid | 66.843 |  | 0.739 |  | 22.178 | 1.000 |  | 0.000 |  |  |
| rules_only | 66.043 |  | 0.731 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| llm_tools_validator__openai_frontier | 66.043 |  | 0.731 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| llm_validator__openai_frontier | 66.043 |  | 0.731 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| llm_tools__anthropic_frontier_selector | 59.875 | 59.875 | 0.646 | 0.646 | 29.147 | 0.782 | 0.782 | 0.000 | 0.000 | 0.000 |
| llm_tools__anthropic_frontier | 59.422 |  | 0.622 |  | 29.600 | 0.778 |  | 0.000 |  |  |
| llm_tools__anthropic_fast | 55.432 |  | 0.610 |  | 33.589 | 0.810 |  | 0.000 |  |  |
| llm_tools__deepseek_frontier_selector | 55.408 | 55.408 | 0.608 | 0.608 | 33.614 | 0.810 | 0.810 | 0.000 | 0.000 | 0.000 |
| bare_llm__anthropic_frontier_selector | 53.780 | 53.780 | 0.580 | 0.580 | 35.242 | 0.692 | 0.692 | 0.000 | 0.000 | 0.000 |
| bare_llm__anthropic_frontier | 53.323 |  | 0.579 |  | 35.699 | 0.682 |  | 0.000 |  |  |
| llm_tools__openai_fast | 51.390 |  | 0.547 |  | 37.631 | 0.738 |  | 0.000 |  |  |
| bare_llm__openai_fast | 51.067 |  | 0.557 |  | 37.954 | 0.732 |  | 0.000 |  |  |
| bare_llm__anthropic_fast | 50.120 |  | 0.550 |  | 38.902 | 0.750 |  | 0.000 |  |  |
| bare_llm__deepseek_frontier_selector | 49.572 | 49.572 | 0.551 | 0.551 | 39.450 | 0.734 | 0.734 | 0.000 | 0.000 | 0.000 |
| llm_tools__deepseek_fast | 33.526 |  | 0.373 |  | 55.496 | 0.512 |  | 0.040 |  |  |
| bare_llm__deepseek_fast | 26.162 |  | 0.281 |  | 62.860 | 0.366 |  | 0.000 |  |  |
| bare_llm__deepseek_frontier | 0.000 |  | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |
| bare_llm__openai_frontier | 0.000 |  | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |
| llm_tools__openai_frontier | 0.000 |  | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |

## Oracle Controls

| system_name | feasible_utility | raw_feasible_utility | ndcg_at_k | raw_ndcg_at_k | constrained_regret | compliance_rate | raw_compliance_rate | schema_error_rate | raw_schema_error_rate | repaired_from_empty_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oracle_valid_topk | 89.022 |  | 1.000 |  | 0.000 | 1.000 |  | 0.000 |  |  |

## Reading Guide

- Higher feasible utility and NDCG@k are better.
- Raw columns score the model output before deterministic validator repair.
- Final columns score the selected output after validator repair where applicable.
- Lower constrained regret and schema error rate are better.
- Oracle controls are sanity checks and must not be mixed into primary system claims.
