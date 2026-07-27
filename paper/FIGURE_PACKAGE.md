# Corrected v0.1.0 Figure Package

This package replaces the retired paper-50 figures. It is generated from the
corrected 91-card split artifacts and the complete 19-row comparison: seven
deterministic/oracle systems, six recorded raw LLM conditions, and six
zero-call post-hoc-repaired views. The paired raw and repaired rows reuse the
same provider responses.

## Figure 1. Decision-card anatomy and leakage boundary

![Decision-card anatomy and leakage boundary](figures/v0.1.0/figure_1_decision_card_anatomy.png)

The system-visible card contains assay context, observed support activities,
candidate structures and permitted descriptors, constraints, and the ordered
top-10 action schema. Candidate outcomes remain in a separate scorer-only row
bound to the public card by task identity and canonical hash.

## Figure 2. Corrected benchmark pipeline

![Corrected benchmark pipeline](figures/v0.1.0/figure_2_benchmark_pipeline.png)

The corrected positional import yields 91 system-input cards and 91 scorer-only
rows. The evaluation covers seven deterministic/oracle systems, six raw LLM
conditions comprising 546 recorded provider requests, and six deterministic
repaired views requiring no further provider calls.

## Figure 3. Main feasible-utility comparison

![Main feasible-utility comparison](figures/v0.1.0/figure_3_main_system_comparison.png)

Mean feasible utility and marginal 95% task-bootstrap intervals are shown for
the deterministic/oracle systems and the final post-hoc-repaired LLM systems.
Numerical labels are offset above the intervals for legibility.

## Figure 4. Ranking quality by system

![Ranking quality by system](figures/v0.1.0/figure_4_ndcg_system_comparison.png)

Mean NDCG@10 and marginal 95% task-bootstrap intervals use the same final-system
comparison as Figure 3. Paired claims are evaluated with the separate paired
task-level delta tables.

## Figure 5. Raw versus post-hoc-repaired LLM utility

![Raw versus post-hoc-repaired LLM utility](figures/v0.1.0/figure_5_raw_vs_final_llm.png)

Each line joins one recorded LLM condition to the deterministic repaired view
of those same responses. Labels on the right report how many of the 91 actions
triggered repair.

## Figure 6. Raw versus post-hoc-repaired whole-action validity

![Raw versus post-hoc-repaired whole-action validity](figures/v0.1.0/figure_6_raw_vs_final_action_validity.png)

Validity is strict: an action is valid only when the complete output has zero
schema, selection-contract, and candidate-constraint issues. This replaces the
legacy figure based on the weaker valid-selection fraction.

## Figure 7. Corrected leaderboard summary

![Corrected leaderboard summary](figures/v0.1.0/figure_7_leaderboard_summary.png)

The three panels summarize leading feasible utility, leading NDCG@10, and raw
LLM whole-action validity. The first two include the hidden-outcome oracle as
an explicitly non-deployable upper-bound control.

## Figure 8. Raw LLM failure taxonomy

![Raw LLM failure taxonomy](figures/v0.1.0/figure_8_failure_taxonomy.png)

Counts and card rates are shown for zero-issue actions and the three contract
failure families. Failure categories can overlap within a card, so their counts
must not be summed across a row.

## Additional inferential figures

The [utility–validity repair frontier](figures/v0.1.0/compliance_utility_frontier.png)
shows raw-to-repaired movement against non-language references. The
[paired feasible-utility effects](figures/v0.1.0/paired_utility_effects.png)
shows headline paired deltas and descriptor-minus-bare ablations with 95%
bootstrap intervals; each effect label is positioned above its error bar.

Rebuild the complete package with the command documented in
[`release/v0.1.0/REPRODUCE.md`](../release/v0.1.0/REPRODUCE.md).
