# 2026-07-25 Corrected Report-Figure Regeneration

## Objective

Regenerate the complete retired Figure 1–8 report series from the corrected
v0.1.0 artifacts, together with the newer inferential and card-level views.
The narrative covers leakage control, system utility, whole-action validity,
deterministic repair, paired descriptor effects, and failure taxonomy.
Chemical diversity and task-selection changes remain outside this version.

## Source artifacts

- `release/v0.1.0/experiments/llm/comparison/system_comparison.csv`
- `release/v0.1.0/experiments/llm/comparison/paired_bootstrap_key_deltas.csv`
- `release/v0.1.0/experiments/llm/comparison/paired_bootstrap_deltas.csv`
- `release/v0.1.0/experiments/llm/comparison/card_level_diagnostics.csv`
- `release/v0.1.0/experiments/llm/comparison/failure_taxonomy_summary.csv`
- `data/releases/v0.1.0/system_input_cards.jsonl`
- `data/releases/v0.1.0/scorer_outcomes.jsonl`

Repaired rows were treated as deterministic views of the same recorded raw
responses. They were not counted as additional calls or costs. Paired intervals
were read from the paired card-level bootstrap tables rather than constructed
by subtracting marginal confidence bounds.

## Corrected numbered package

The historical series was rebuilt under `paper/figures/v0.1.0/` rather than
reviving the invalid historical output directory:

1. `figure_1_decision_card_anatomy` separates system-visible inputs from the
   hash-bound scorer-only outcomes and makes the candidate-activity leakage
   boundary explicit.
2. `figure_2_benchmark_pipeline` derives the 91-card, seven-deterministic,
   six-raw-condition/546-request, and six-zero-call-repair flow.
3. `figure_3_main_system_comparison` shows final-system feasible utility with
   marginal task-bootstrap intervals.
4. `figure_4_ndcg_system_comparison` gives the corresponding NDCG@10 view.
5. `figure_5_raw_vs_final_llm` joins each raw LLM result to the deterministic
   repaired view of the same responses.
6. `figure_6_raw_vs_final_action_validity` replaces the retired
   valid-selection-fraction figure with strict zero-issue whole-action
   validity.
7. `figure_7_leaderboard_summary` summarizes leading utility, leading NDCG@10,
   and raw LLM action validity.
8. `figure_8_failure_taxonomy` reports zero-issue actions plus overlapping
   schema, selection-contract, and candidate-constraint failure families.

Each numbered figure has a 300-dpi PNG, PDF, and searchable SVG export. Input
gates reject non-91-card artifacts, non-19-row comparisons, incomplete raw and
repaired matrices, provider substitutions, and leaked candidate outcomes.

## Additional inferential figures

1. `compliance_utility_frontier.{png,pdf}` plots whole-action validity against
   feasible utility, with provider color, interface line style, raw/repaired
   marker state, non-language references, and the exact repair rate on every
   LLM trajectory.
2. `paired_utility_effects.{png,pdf}` combines the four headline paired
   feasible-utility comparisons with the six matched descriptor-minus-bare
   effects. Pair direction is normalized before plotting.

The first view shows why guarded results must be distinguished from unaided
model behavior. The second carries the inferential claims: best observed QSAR
minus best repaired LLM was `1.0027` with paired 95% interval `0.4049` to
`1.6475`; descriptor summaries were not a general benefit. Every numerical
effect label now sits above, rather than on, its interval.

## Supporting figures

- `primary_utility_leaderboard.{png,pdf}`: every non-oracle system with its
  marginal bootstrap interval and the oracle as a reference line.
- `llm_repair_effect.{png,pdf}`: raw-to-repaired utility dumbbells beside
  valid-as-issued versus repair-triggered action shares.
- `descriptor_ablation.{png,pdf}`: a standalone, report-sized version of the
  descriptor forest plot.
- `card_level_utility_distribution.{png,pdf}` and
  `card_level_delta_distribution.{png,pdf}` now show every card as a
  deterministic-jitter point over the horizontal box plots.
- `card_level_qsar_vs_llm_scatter.{png,pdf}` directly encodes which system wins
  each card and reports 58 QSAR wins, 32 repaired-LLM wins, and one tie.

PNG exports use 300 dpi for Markdown and report rendering. Matching vector PDFs
are available for typesetting.

## Report integration

`paper/RESULTS_SUMMARY.md` now embeds the complete corrected Figure 1–8 series,
then the two additional inferential views, and links all remaining card-level
diagnostics. `paper/FIGURE_PACKAGE.md` provides report captions and
interpretation boundaries. `paper/README.md` indexes every asset. The report
generator performs this integration only when it recognizes a versioned release
source and the complete numbered package exists.

## Validation

- Full test suite: 66 passed after the numbered-series integration. Ruff
  lint/format and `git diff --check` also passed.
- All eight numbered PNGs, the paired-effect forest plot, and the three
  refreshed card-level views were visually inspected. The paired-effect values
  are legibly offset above their interval lines; no final text or legend
  clipping remains.
- Numbered PDF and SVG exports are one page each; PDFs use TrueType-compatible
  font embedding and SVG text remains searchable. A repeat build reproduced all
  40 committed PNG/PDF/SVG figure files byte-for-byte.

## Decision

Retain the complete corrected Figure 1–8 series as the replacement report
package. Use the utility-validity frontier and paired utility-effects forest
plot as additional inferential views, and keep the remaining distributions and
scatter as diagnostics. Diversity remains deferred to a separately versioned
analysis.
