# SpecGuard-Chem v2 CARA LO Paper-50 Direct-JSON Results

Generated at: `2026-05-12T10:49:30.655509+00:00`

Source comparison CSV: `paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv`

This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.

## Central Paper Argument

SpecGuard-Chem evaluates constrained medicinal-chemistry decision systems on two axes at once. Activity utility alone can reward potent compounds that violate project specifications. Compliance alone can be enforced cheaply and may produce valid but weak recommendations. The paper question is whether a system can choose candidate IDs that are both valid under the written constraints and useful as next-assay priorities.

The LO paper-50 results therefore compare LLM systems against deterministic baselines and QSAR models rather than only against other LLMs. In this result set, the best deployable QSAR baseline is **QSAR linear SVR** with feasible utility `81.382`, below the oracle upper bound `89.022` but above the best final LLM row **LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON** at `78.188` and the best raw LLM row **LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON** at raw feasible utility `77.209`.

## QSAR Baseline Interpretation

QSAR means quantitative structure-activity relationship modelling. Here, each QSAR row is trained separately for each decision card using only the support compounds' Morgan fingerprints and measured support activity. The trained model predicts candidate activity, then ranks feasible candidate IDs. It does not use hidden candidate activity and is therefore a deployable non-language comparator, unlike the oracle control.

The fact that `qsar_rf`, `qsar_gbt`, and `qsar_svm` all beat random, rules-only, and similarity baselines in this run supports treating QSAR as a serious baseline. It does not make QSAR ground truth, a universal activity model, or a substitute for prospective medicinal-chemistry judgement.

## Hypotheses And Contentions

- H1, validators improve compliance more reliably than utility: supported as a reporting requirement. Final validator-assisted rows can be more compliant and sometimes more useful, but raw metrics show when the gain is harness repair rather than raw model behavior.
- H2, simple QSAR and similarity baselines are competitive: supported. Best QSAR feasible utility is `81.382`; similarity-to-best-active is `73.603`; best final LLM is `78.188`.
- H3, the best useful system is likely hybrid: partially supported. Guarded/tool-summary LLM rows can improve over bare LLM rows, but this implementation is not yet the broader agent design where QSAR, RDKit, similarity retrieval, and other tools are actively available as callable tools.
- H4, compliance and utility are imperfectly correlated: supported. Near-perfect compliance appears in rows with materially different feasible utility, so compliance alone is not the target outcome.

## Paired Bootstrap Highlights

These deltas resample paired decision cards, so each comparison asks how two systems differed on the same cards rather than comparing independent aggregate means.

| comparison | metric | system_a_label | system_b_label | mean_delta | ci_95 | probability_delta_gt_zero |
| --- | --- | --- | --- | --- | --- | --- |
| oracle_minus_best_qsar | feasible_utility | Oracle upper-bound | QSAR linear SVR | 7.639 | 6.571 to 8.798 | 1.000 |
| oracle_minus_best_qsar | ndcg_at_k | Oracle upper-bound | QSAR linear SVR | 0.090 | 0.078 to 0.104 | 1.000 |
| oracle_minus_best_qsar | compliance_rate | Oracle upper-bound | QSAR linear SVR | 0.000 | 0.000 to 0.000 | 0.000 |
| best_qsar_minus_best_final_llm | feasible_utility | QSAR linear SVR | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | 3.194 | 1.942 to 4.692 | 1.000 |
| best_qsar_minus_best_final_llm | ndcg_at_k | QSAR linear SVR | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | 0.028 | 0.016 to 0.043 | 1.000 |
| best_qsar_minus_best_final_llm | compliance_rate | QSAR linear SVR | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | 0.000 | 0.000 to 0.000 | 0.000 |
| best_qsar_minus_similarity | feasible_utility | QSAR linear SVR | Similarity-to-best-active baseline | 7.779 | 5.289 to 10.437 | 1.000 |
| best_qsar_minus_similarity | ndcg_at_k | QSAR linear SVR | Similarity-to-best-active baseline | 0.084 | 0.057 to 0.113 | 1.000 |
| best_qsar_minus_similarity | compliance_rate | QSAR linear SVR | Similarity-to-best-active baseline | 0.000 | 0.000 to 0.000 | 0.000 |
| best_final_llm_minus_similarity | feasible_utility | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 4.585 | 1.941 to 7.272 | 1.000 |
| best_final_llm_minus_similarity | ndcg_at_k | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 0.056 | 0.028 to 0.086 | 1.000 |
| best_final_llm_minus_similarity | compliance_rate | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 0.000 | 0.000 to 0.000 | 0.000 |
| best_final_llm_minus_rules | feasible_utility | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Rule/desirability baseline | 12.145 | 10.282 to 14.056 | 1.000 |
| best_final_llm_minus_rules | ndcg_at_k | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Rule/desirability baseline | 0.151 | 0.130 to 0.171 | 1.000 |
| best_final_llm_minus_rules | compliance_rate | LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Rule/desirability baseline | 0.000 | 0.000 to 0.000 | 0.000 |
| best_raw_llm_minus_similarity | feasible_utility | LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 4.084 | 1.454 to 6.853 | 0.999 |
| best_raw_llm_minus_similarity | ndcg_at_k | LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 0.048 | 0.019 to 0.080 | 0.999 |
| best_raw_llm_minus_similarity | compliance_rate | LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON | Similarity-to-best-active baseline | 0.000 | 0.000 to 0.000 | 0.000 |

## Failure Taxonomy Summary

This table aggregates final-output validation failures across cards. Raw LLM repair behavior is still reported separately through raw metrics and repair rates.

| display_label | failure_type | cards_with_type | card_rate | total_issue_count | mean_issue_count_per_card |
| --- | --- | --- | --- | --- | --- |
| Bare LLM - DeepSeek deepseek-v4-pro, high reasoning, thinking on, original full-pool prompt | schema_failure | 50.000 | 1.000 | 50.000 | 1.000 |
| Bare LLM - OpenAI gpt-5.5, high reasoning, original full-pool prompt | schema_failure | 50.000 | 1.000 | 50.000 | 1.000 |
| LLM plus tool summaries - OpenAI gpt-5.5, high reasoning, original full-pool prompt | schema_failure | 50.000 | 1.000 | 50.000 | 1.000 |
| Bare LLM - DeepSeek deepseek-v4-flash, thinking off, fast model | selection_contract_failure | 39.000 | 0.780 | 253.000 | 5.060 |
| Bare LLM - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | constraint_failure | 30.000 | 0.600 | 112.000 | 2.240 |
| Bare LLM - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | constraint_failure | 28.000 | 0.560 | 109.000 | 2.180 |
| Bare LLM - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | selection_contract_failure | 28.000 | 0.560 | 63.000 | 1.260 |
| Bare LLM - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | selection_contract_failure | 28.000 | 0.560 | 61.000 | 1.220 |
| LLM plus tool summaries - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | constraint_failure | 26.000 | 0.520 | 75.000 | 1.500 |
| Bare LLM - OpenAI gpt-5.4-mini, low reasoning, fast model | selection_contract_failure | 25.000 | 0.500 | 115.000 | 2.300 |
| LLM plus tool summaries - DeepSeek deepseek-v4-pro, thinking off, Direct JSON | constraint_failure | 25.000 | 0.500 | 87.000 | 1.740 |
| LLM plus tool summaries - DeepSeek deepseek-v4-flash, thinking off, fast model | selection_contract_failure | 24.000 | 0.480 | 172.000 | 3.440 |
| LLM plus tool summaries - OpenAI gpt-5.4-mini, low reasoning, fast model | selection_contract_failure | 21.000 | 0.420 | 120.000 | 2.400 |
| LLM plus tool summaries - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | constraint_failure | 21.000 | 0.420 | 67.000 | 1.340 |

## Card-Level Diagnostics

Per-card diagnostic tables are written next to the comparison CSV in `paper/tables/cara_lo_paper_50_direct_json_completed`. The matching figure directory contains card-level utility distributions, utility-delta distributions, and a QSAR-versus-LLM per-card scatter plot when `make-figures` is run.

## Primary Systems

| display_label | system_name | feasible_utility | feasible_utility_ci_low | feasible_utility_ci_high | raw_feasible_utility | ndcg_at_k | ndcg_at_k_ci_low | ndcg_at_k_ci_high | raw_ndcg_at_k | constrained_regret | compliance_rate | raw_compliance_rate | schema_error_rate | raw_schema_error_rate | repaired_from_empty_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QSAR linear SVR | qsar_svm | 81.382 | 79.532 | 83.271 |  | 0.910 | 0.897 | 0.922 |  | 7.639 | 1.000 |  | 0.000 |  |  |
| QSAR gradient boosting | qsar_gbt | 80.888 | 78.778 | 82.956 |  | 0.900 | 0.884 | 0.916 |  | 8.134 | 1.000 |  | 0.000 |  |  |
| QSAR random forest | qsar_rf | 80.634 | 78.652 | 82.548 |  | 0.901 | 0.887 | 0.913 |  | 8.388 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | llm_validator__openai_frontier_selector | 78.188 | 76.316 | 80.093 | 76.758 | 0.881 | 0.863 | 0.899 | 0.868 | 10.833 | 1.000 | 0.976 | 0.000 | 0.000 | 0.000 |
| LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON | llm_tools_validator__openai_frontier_selector | 77.688 | 75.702 | 79.794 | 77.209 | 0.873 | 0.856 | 0.892 | 0.866 | 11.334 | 1.000 | 0.994 | 0.000 | 0.000 | 0.000 |
| LLM plus tool summaries - OpenAI gpt-5.5, low reasoning, Direct JSON | llm_tools__openai_frontier_selector | 77.173 | 75.115 | 79.295 | 77.173 | 0.870 | 0.851 | 0.889 | 0.870 | 11.849 | 0.990 | 0.990 | 0.000 | 0.000 | 0.000 |
| Bare LLM - OpenAI gpt-5.5, low reasoning, Direct JSON | bare_llm__openai_frontier_selector | 75.781 | 73.447 | 78.054 | 75.781 | 0.847 | 0.817 | 0.873 | 0.847 | 13.241 | 0.962 | 0.962 | 0.000 | 0.000 | 0.000 |
| LLM plus tools and validator - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | llm_tools_validator__anthropic_frontier_selector | 74.471 | 72.084 | 77.001 | 62.859 | 0.834 | 0.812 | 0.857 | 0.684 | 14.551 | 1.000 | 0.822 | 0.000 | 0.020 | 0.000 |
| LLM plus validator - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | llm_validator__anthropic_frontier_selector | 74.274 | 71.743 | 76.814 | 55.388 | 0.832 | 0.804 | 0.858 | 0.602 | 14.748 | 1.000 | 0.710 | 0.000 | 0.000 | 0.000 |
| LLM plus tools and validator - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | llm_tools_validator__anthropic_frontier | 73.979 | 71.695 | 76.461 |  | 0.832 | 0.811 | 0.856 |  | 15.043 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | llm_validator__anthropic_frontier | 73.739 | 71.160 | 76.195 |  | 0.831 | 0.805 | 0.856 |  | 15.283 | 1.000 |  | 0.000 |  |  |
| Similarity-to-best-active baseline | similarity_to_best_active | 73.603 | 70.825 | 76.490 |  | 0.825 | 0.797 | 0.852 |  | 15.418 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - DeepSeek deepseek-v4-flash, thinking off, fast model | llm_validator__deepseek_fast | 68.402 | 66.122 | 70.594 |  | 0.763 | 0.736 | 0.786 |  | 20.620 | 1.000 |  | 0.000 |  |  |
| LLM plus tools and validator - OpenAI gpt-5.4-mini, low reasoning, fast model | llm_tools_validator__openai_fast | 67.702 | 65.218 | 70.044 |  | 0.752 | 0.724 | 0.779 |  | 21.320 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - DeepSeek deepseek-v4-pro, thinking off, Direct JSON | llm_validator__deepseek_frontier_selector | 67.621 | 65.355 | 70.047 | 49.201 | 0.752 | 0.727 | 0.778 | 0.551 | 21.400 | 1.000 | 0.726 | 0.000 | 0.000 | 0.000 |
| LLM plus tools and validator - Anthropic claude-haiku-4-5-20251001, fast model | llm_tools_validator__anthropic_fast | 67.225 | 65.053 | 69.435 |  | 0.750 | 0.727 | 0.775 |  | 21.796 | 1.000 |  | 0.000 |  |  |
| LLM plus tools and validator - DeepSeek deepseek-v4-flash, thinking off, fast model | llm_tools_validator__deepseek_fast | 67.217 | 64.822 | 69.645 |  | 0.749 | 0.725 | 0.774 |  | 21.804 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - OpenAI gpt-5.4-mini, low reasoning, fast model | llm_validator__openai_fast | 67.000 | 64.582 | 69.438 |  | 0.744 | 0.720 | 0.769 |  | 22.022 | 1.000 |  | 0.000 |  |  |
| LLM plus tools and validator - DeepSeek deepseek-v4-pro, thinking off, Direct JSON | llm_tools_validator__deepseek_frontier_selector | 66.948 | 64.580 | 69.324 | 57.849 | 0.740 | 0.714 | 0.765 | 0.635 | 22.074 | 1.000 | 0.864 | 0.000 | 0.000 | 0.000 |
| LLM plus validator - Anthropic claude-haiku-4-5-20251001, fast model | llm_validator__anthropic_fast | 66.881 | 64.475 | 69.192 |  | 0.741 | 0.715 | 0.767 |  | 22.141 | 1.000 |  | 0.000 |  |  |
| Random valid baseline | random_valid | 66.843 | 65.304 | 68.372 |  | 0.739 | 0.723 | 0.756 |  | 22.178 | 1.000 |  | 0.000 |  |  |
| Rule/desirability baseline | rules_only | 66.043 | 64.058 | 68.199 |  | 0.731 | 0.708 | 0.753 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| LLM plus tools and validator - OpenAI gpt-5.5, high reasoning, original full-pool prompt | llm_tools_validator__openai_frontier | 66.043 | 64.058 | 68.199 |  | 0.731 | 0.708 | 0.753 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| LLM plus validator - OpenAI gpt-5.5, high reasoning, original full-pool prompt | llm_validator__openai_frontier | 66.043 | 64.058 | 68.199 |  | 0.731 | 0.708 | 0.753 |  | 22.979 | 1.000 |  | 0.000 |  |  |
| LLM plus tool summaries - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | llm_tools__anthropic_frontier_selector | 59.875 | 54.060 | 65.769 | 59.875 | 0.646 | 0.573 | 0.720 | 0.646 | 29.147 | 0.782 | 0.782 | 0.000 | 0.000 | 0.000 |
| LLM plus tool summaries - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | llm_tools__anthropic_frontier | 59.422 | 53.708 | 65.081 |  | 0.622 | 0.558 | 0.683 |  | 29.600 | 0.778 |  | 0.000 |  |  |
| LLM plus tool summaries - Anthropic claude-haiku-4-5-20251001, fast model | llm_tools__anthropic_fast | 55.432 | 49.523 | 61.294 |  | 0.610 | 0.539 | 0.677 |  | 33.589 | 0.810 |  | 0.000 |  |  |
| LLM plus tool summaries - DeepSeek deepseek-v4-pro, thinking off, Direct JSON | llm_tools__deepseek_frontier_selector | 55.408 | 50.224 | 60.778 | 55.408 | 0.608 | 0.551 | 0.667 | 0.608 | 33.614 | 0.810 | 0.810 | 0.000 | 0.000 | 0.000 |
| Bare LLM - Anthropic claude-opus-4-7, no extended thinking, Direct JSON | bare_llm__anthropic_frontier_selector | 53.780 | 47.039 | 60.135 | 53.780 | 0.580 | 0.500 | 0.652 | 0.580 | 35.242 | 0.692 | 0.692 | 0.000 | 0.000 | 0.000 |
| Bare LLM - Anthropic claude-opus-4-7, original full-pool prompt, no explicit thinking budget | bare_llm__anthropic_frontier | 53.323 | 46.600 | 60.249 |  | 0.579 | 0.498 | 0.657 |  | 35.699 | 0.682 |  | 0.000 |  |  |
| LLM plus tool summaries - OpenAI gpt-5.4-mini, low reasoning, fast model | llm_tools__openai_fast | 51.390 | 44.150 | 58.240 |  | 0.547 | 0.463 | 0.628 |  | 37.631 | 0.738 |  | 0.000 |  |  |
| Bare LLM - OpenAI gpt-5.4-mini, low reasoning, fast model | bare_llm__openai_fast | 51.067 | 43.612 | 57.736 |  | 0.557 | 0.473 | 0.640 |  | 37.954 | 0.732 |  | 0.000 |  |  |
| Bare LLM - Anthropic claude-haiku-4-5-20251001, fast model | bare_llm__anthropic_fast | 50.120 | 43.254 | 57.619 |  | 0.550 | 0.469 | 0.628 |  | 38.902 | 0.750 |  | 0.000 |  |  |
| Bare LLM - DeepSeek deepseek-v4-pro, thinking off, Direct JSON | bare_llm__deepseek_frontier_selector | 49.572 | 42.779 | 56.269 | 49.572 | 0.551 | 0.474 | 0.623 | 0.551 | 39.450 | 0.734 | 0.734 | 0.000 | 0.000 | 0.000 |
| LLM plus tool summaries - DeepSeek deepseek-v4-flash, thinking off, fast model | llm_tools__deepseek_fast | 33.526 | 25.471 | 40.658 |  | 0.373 | 0.283 | 0.459 |  | 55.496 | 0.512 |  | 0.040 |  |  |
| Bare LLM - DeepSeek deepseek-v4-flash, thinking off, fast model | bare_llm__deepseek_fast | 26.162 | 18.929 | 34.856 |  | 0.281 | 0.199 | 0.375 |  | 62.860 | 0.366 |  | 0.000 |  |  |
| Bare LLM - DeepSeek deepseek-v4-pro, high reasoning, thinking on, original full-pool prompt | bare_llm__deepseek_frontier | 0.000 | 0.000 | 0.000 |  | 0.000 | 0.000 | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |
| Bare LLM - OpenAI gpt-5.5, high reasoning, original full-pool prompt | bare_llm__openai_frontier | 0.000 | 0.000 | 0.000 |  | 0.000 | 0.000 | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |
| LLM plus tool summaries - OpenAI gpt-5.5, high reasoning, original full-pool prompt | llm_tools__openai_frontier | 0.000 | 0.000 | 0.000 |  | 0.000 | 0.000 | 0.000 |  | 89.022 | 0.000 |  | 1.000 |  |  |

## Oracle Controls

| display_label | system_name | feasible_utility | feasible_utility_ci_low | feasible_utility_ci_high | raw_feasible_utility | ndcg_at_k | ndcg_at_k_ci_low | ndcg_at_k_ci_high | raw_ndcg_at_k | constrained_regret | compliance_rate | raw_compliance_rate | schema_error_rate | raw_schema_error_rate | repaired_from_empty_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle upper-bound | oracle_valid_topk | 89.022 | 87.394 | 90.604 |  | 1.000 | 1.000 | 1.000 |  | 0.000 | 1.000 |  | 0.000 |  |  |

## Reading Guide

- Higher feasible utility and NDCG@k are better.
- Raw columns score the model output before deterministic validator repair.
- Final columns score the selected output after validator repair where applicable.
- Lower constrained regret and schema error rate are better.
- Oracle controls are sanity checks and must not be mixed into primary system claims.

## Label and Metric Glossary

### Study terms

- CARA: public compound-activity benchmark used here as the source substrate for assay-level support/query tasks.
- LO: lead optimisation. In this project, LO cards represent an observed support set plus candidate compounds to prioritise next.
- VS: virtual screening. VS is not the primary run here; it usually means ranking a broader candidate set for activity.
- Decision card: one benchmark instance containing support compounds, a candidate pool, hard constraints, budget `k`, and hidden activity values used only by the scorer.
- Support set: already-tested compounds with measured activity that systems may learn from but must not recommend.
- Candidate pool: compounds eligible for selection, subject to hard constraints.
- QSAR: quantitative structure-activity relationship; here, conventional ML regressors trained separately for each decision card on support-set Morgan fingerprints and measured support activity, then used to rank feasible candidates by predicted activity. QSAR rows are deployable baselines, not oracle controls.
- Oracle: non-deployable upper-bound scorer that uses hidden activity values. It is a sanity check, not a real model.
- Validator: deterministic harness logic that checks schema, candidate IDs, duplicates, support-set exclusion, and molecular constraints. It does not use hidden activity values.
- Direct JSON: the current LLM prompt profile that asks for final JSON only, reducing failures where reasoning/prose consumes the visible output budget.

### System labels

- `oracle_valid_topk`: non-deployable upper-bound control that uses hidden candidate activity values to choose the best valid top-k set.
- `random_valid`: random valid-candidate baseline.
- `rules_only`: deterministic fallback/rule ranking after applying hard constraints.
- `similarity_to_best_active`: ranks candidates by molecular similarity to the best active support compound.
- `qsar_rf`: random forest QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.
- `qsar_gbt`: gradient-boosting QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.
- `qsar_svm`: sparse-scaled linear-kernel support-vector QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.
- `bare_llm`: LLM receives the decision card and returns candidate IDs without deterministic repair.
- `llm_tools`: LLM condition with extra computed descriptor/tool-summary fields in the candidate rows.
- `llm_validator`: guarded LLM system; raw output is checked and invalid/missing slots may be deterministically repaired.
- `llm_tools_validator`: tool-summary LLM condition plus deterministic checking and repair.
- `*_frontier_selector`: legacy internal run ID for the direct-JSON condition. Reader-facing labels should use the provider, exact model name, and reasoning/thinking setting instead of this shorthand.
- `*_frontier`: legacy internal run ID for the original full-pool frontier-model condition. Some rows are diagnostic interface failures, not clean model-capability measurements.
- `*_fast`: legacy internal run ID for lower-latency/lower-cost provider conditions.

### Metrics

- `feasible_utility`: sum of hidden activity values for selected candidates that satisfy all hard constraints. Higher is better.
- `raw_feasible_utility`: feasible utility before deterministic validator repair. This is the closer measure of raw LLM behavior.
- `ndcg_at_k`: ranking-quality score using hidden activity as graded relevance. Higher is better; `1.0` is ideal ranking.
- `raw_ndcg_at_k`: NDCG before deterministic validator repair.
- `constrained_regret`: oracle valid top-k utility minus observed feasible utility. Lower is better.
- `compliance_rate`: fraction of the requested `k` selections that are valid after final repair, if repair applies.
- `raw_compliance_rate`: compliance before deterministic validator repair.
- `schema_error_rate`: fraction of cards with final schema/contract errors.
- `raw_schema_error_rate`: schema/contract error rate before deterministic validator repair.
- `repaired_from_empty_rate`: fraction of cards where the validator repaired an empty raw selection list. This should be near zero for a usable LLM interface.

### Interpretation rules

- Raw metrics describe model behavior; final metrics for `*_validator` rows describe model plus deterministic guardrail behavior.
- Oracle controls are sanity checks, not systems that could be used prospectively.
- A row can be highly compliant but still have weak utility; this distinction is the main object of the audit.
