# SpecGuard-Chem paper workspace

> **Status: results populated; manuscript in preparation.** The corrected data
> artifact, deterministic baselines, and full 546-request provider matrix are
> complete and audited across 91 cards, two interfaces, and three frozen model
> conditions. Six raw traces and six zero-call post-hoc-repaired views feed the
> canonical comparison, report, dashboard, figures, and manuscript result gate.
> The best repaired LLM reaches 73.964 utility; the QSAR SVM remains higher at
> 74.966.

## Working paper identity

**Working title:** *Before the Lab Acts: Benchmarking Language Models for
Constrained Compound Selection*

The paper frames SpecGuard-Chem as an action-level unit test for a future
automated laboratory: can a model-backed system turn sparse assay-local evidence
into a valid, useful, budget-constrained experimental shortlist?

The claim boundary is deliberately narrow. CARA supplies the activity records
and official split substrate. The paper evaluates one retrospective,
assay-local filter-predict-rank-allocate action. It does not claim de novo design,
synthesis planning, multi-step closed-loop learning, prospective biological
validation, or readiness for autonomous drug discovery.

## Evidence policy

- Candidate activity is hidden from systems and stored in a separate scorer
  artifact.
- Scientific utility and action validity are reported separately.
- Every paper number must trace to the corrected v0.1.0 cards, scorer outcomes,
  exact system/model condition, and per-card score.
- Raw model actions and deterministic post-hoc repair must be attributed from
  the same underlying response rather than treated as independent model calls.
- Current provider model identifiers, generation settings, dates, token counts,
  latency, and monetary cost must accompany LLM results.
- Invalid historical paper-50 cards, caches, responses, tables, figures, and
  claims must not be reused.

The authoritative status of those historical outputs is documented in
[`INVALID_RESULTS_NOTICE.md`](../INVALID_RESULTS_NOTICE.md).

## Layout

```text
paper/
  manuscript/   LaTeX source, generated result macros, compiled drafts, and bibliography
  tables/       generated deterministic and comparison-supporting tables
  figures/      corrected v0.1.0 aggregate and card-level analysis figures
  FIGURE_PACKAGE.md     numbered Figure 1–8 package with report captions
  RESULTS_SUMMARY.md     canonical human-readable results report
  RESULTS_DASHBOARD.html self-contained interactive results dashboard
  README.md     this paper-specific status and evidence policy
```

Do not hand-edit generated numerical tables or figures. Their final build path
must be recorded in the release reproduction guide and verified from a clean
checkout.

## Report-ready figures

The corrected full-matrix build replaces the complete retired paper-50 figure
package, not only the two newer core views. Every numbered figure is written as
a 300-dpi PNG for the report and as PDF and searchable SVG vector exports:

1. [Decision-card anatomy and leakage boundary](figures/v0.1.0/figure_1_decision_card_anatomy.png)
2. [Corrected 91-card benchmark pipeline](figures/v0.1.0/figure_2_benchmark_pipeline.png)
3. [Main feasible-utility comparison](figures/v0.1.0/figure_3_main_system_comparison.png)
4. [System NDCG@10 comparison](figures/v0.1.0/figure_4_ndcg_system_comparison.png)
5. [Raw versus post-hoc-repaired LLM utility](figures/v0.1.0/figure_5_raw_vs_final_llm.png)
6. [Raw versus post-hoc-repaired whole-action validity](figures/v0.1.0/figure_6_raw_vs_final_action_validity.png)
7. [Corrected leaderboard summary](figures/v0.1.0/figure_7_leaderboard_summary.png)
8. [Raw LLM failure taxonomy](figures/v0.1.0/figure_8_failure_taxonomy.png)

Two additional inferential views carry the main paired claims:
[utility–validity repair frontier](figures/v0.1.0/compliance_utility_frontier.png)
and [paired feasible-utility effects](figures/v0.1.0/paired_utility_effects.png).
The latter places each numerical effect label above its interval so the label
does not sit on the error-bar line.

Additional diagnostics include the
[complete primary leaderboard](figures/v0.1.0/primary_utility_leaderboard.png),
[repair decomposition](figures/v0.1.0/llm_repair_effect.png),
[standalone descriptor ablation](figures/v0.1.0/descriptor_ablation.png),
[across-card utility distributions](figures/v0.1.0/card_level_utility_distribution.png),
[across-card utility-difference distributions](figures/v0.1.0/card_level_delta_distribution.png),
and [per-card QSAR-versus-LLM scatter](figures/v0.1.0/card_level_qsar_vs_llm_scatter.png).
The numbered package uses the corrected 19-row comparison: seven
deterministic/oracle systems, six recorded raw LLM conditions, and six
zero-call repaired views.

## Release relationship

The paper is one component of the planned v0.1.0 archival bundle. See the
[`release/v0.1.0` candidate guide](../release/v0.1.0/README.md) and its
[`REPRODUCE.md`](../release/v0.1.0/REPRODUCE.md).

The directory name does not imply a released paper or software version. There
is no v0.1.0 tag, DOI, or final release date yet.

## Licensing

The repository code is MIT-licensed, while CARA and CARA-derived data are
subject to CC BY 4.0 attribution. The publication route and manuscript license
have not yet been selected, so there is deliberately no separate `paper/LICENSE`
grant at this stage. A paper-specific license and any venue-required notices are
a release gate; the root MIT license must not be assumed to cover the manuscript.

See [`DATA_LICENSE.md`](../DATA_LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
