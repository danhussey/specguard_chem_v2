# Figure Package

Working figure set for the constrained lead-optimisation manuscript review.
PNG files are for quick review and MD/Pages insertion. PDF/SVG files are
available for higher-resolution or vector workflows.

## Figure 1. Example Frozen Decision Card

**Caption.** The figure shows an excerpt from one CARA-derived
lead-optimisation decision card. Each card contains task metadata, a support
set with visible activity values and molecular descriptors, a candidate pool
with molecular descriptors, hard output and molecular constraints, a fixed
selection budget, and an output schema for ranked candidate identifiers.
Candidate activity values are retained in the frozen artifact for offline
scoring but are hidden from evaluated deployable systems; only the oracle
upper-bound control uses them directly.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_1_decision_card_anatomy.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_1_decision_card_anatomy.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_1_decision_card_anatomy.svg`

## Figure 2. Benchmark Pipeline And Evaluation Flow

**Caption.** Public CARA/ChEMBL lead-optimisation records were converted into
50 fixed decision cards. Each method received the same card and returned a
ranked top-10 shortlist of candidate compounds. Shortlists were assessed in two
ways: compliance, meaning whether the shortlist followed the task rules, and
hidden-activity score, meaning whether the selected compounds had high withheld
activity values. The oracle is shown separately as an upper bound because it
can see the hidden activity values; language-model results are reported before
and after validation/repair.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_2_benchmark_pipeline.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_2_benchmark_pipeline.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_2_benchmark_pipeline.svg`

## Figure 3. Main System Comparison

**Caption.** Dots show mean feasible utility across the 50 decision cards;
horizontal bars show 95% bootstrap intervals over cards. The oracle is a
non-deployable upper bound because it uses hidden candidate activity. The plot
includes selected language-model variants with and without extra molecular
descriptors. The strongest deployable comparator was QSAR linear SVR, while
the strongest guarded language-model row was OpenAI gpt-5.5 with
validation/repair.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_3_main_system_comparison.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_3_main_system_comparison.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_3_main_system_comparison.svg`

## Figure 4. Ranking Quality By System

**Caption.** Dots show mean NDCG@10 across the 50 decision cards; horizontal
bars show 95% bootstrap intervals over cards. NDCG@10 measures whether
compounds with higher hidden activity values were placed nearer the top of the
ranked shortlist. The plot includes selected language-model variants with and
without extra molecular descriptors. This complements feasible utility, which
mainly measures the quality of the selected top-10 set.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_4_ndcg_system_comparison.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_4_ndcg_system_comparison.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_4_ndcg_system_comparison.svg`

## Figure 5. Raw Versus Final Utility For Selected Language Models

**Caption.** The figure shows selected conditions for each frontier language
model, including versions with and without extra molecular descriptors. Raw
output means the language-model response before deterministic repair. Final
output means the guarded pipeline after validation and repair. "Repair used" is
the percentage of the 50 tasks where repair was applied before final scoring.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_5_raw_vs_final_llm.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_5_raw_vs_final_llm.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_5_raw_vs_final_llm.svg`

## Figure 6. Raw Versus Final Compliance For Selected Language Models

**Caption.** Compliance is the fraction of the requested top-10 shortlist that
satisfied the task rules. Final compliance reaches 1.000 because the
validator/repair layer enforces the output contract. The figure includes
selected conditions with and without extra molecular descriptors. The raw
compliance values show how often the model/interface already followed the
rules; "repair used" is the percentage of the 50 tasks where repair was applied
before final scoring.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_6_raw_vs_final_compliance.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_6_raw_vs_final_compliance.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_6_raw_vs_final_compliance.svg`

## Figure 7. Leaderboard Snapshot

**Caption.** Compact summary of leading rows for feasible utility, NDCG@10
ranking quality, and raw language-model compliance. The compliance panel uses
raw language-model outputs because final guarded compliance is enforced by
validation/repair and is therefore not a useful leaderboard.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_7_leaderboard_summary.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_7_leaderboard_summary.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_7_leaderboard_summary.svg`

## Figure 8. Raw Language-Model Failure Taxonomy

**Caption.** Counts of raw language-model tasks with no detected issue,
molecular-rule failures, shortlist-format failures, or JSON/schema failures
before validation/repair. Categories can overlap on the same task, so counts
should not be summed across a row.

- PNG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_8_failure_taxonomy.png`
- PDF: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_8_failure_taxonomy.pdf`
- SVG: `paper/figures/cara_lo_paper_50_direct_json_completed/figure_8_failure_taxonomy.svg`

