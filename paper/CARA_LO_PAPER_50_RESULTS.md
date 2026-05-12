# CARA LO Paper-50 Results Snapshot

Generated on 2026-05-12 after consolidating the completed direct-JSON
paper-50 result set.

## Primary Result Set

Use the direct-JSON completed result set as the current paper-facing LO result:

- `paper/tables/cara_lo_paper_50_direct_json_completed/primary_leaderboard.csv`
- `paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv`
- `paper/figures/cara_lo_paper_50_direct_json_completed/compliance_utility_frontier.png`
- `paper/RESULTS_SUMMARY.md`
- `paper/RESULTS_DASHBOARD.html`

The legacy `selector_completed` artifacts contain the same direct-JSON
experiment under the older internal naming. The `fast_complete` and
`completed` frontier artifacts remain historical diagnostic comparisons.

The direct-JSON table directory also contains strengthened statistical
diagnostics:

- `paired_bootstrap_key_deltas.csv`: paired card-level deltas for the main
  paper comparisons.
- `paired_bootstrap_deltas.csv`: all primary pairwise card-level deltas.
- `card_level_diagnostics.csv` and `card_level_key_systems.csv`: per-card
  utility diagnostics for key systems.
- `failure_taxonomy_summary.csv` and `failure_taxonomy_by_group.csv`:
  consolidated validation-failure summaries.

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

## Methods Framing

Each LO decision card represents a constrained next-assay prioritisation
problem. Systems receive already-tested support compounds, a candidate pool,
hard medicinal-chemistry constraints, and a finite budget `k`. They return
ranked candidate IDs, not newly generated molecules.

The central evaluation separates:

- utility: did the selected valid candidates have high hidden activity?
- compliance: did the output satisfy schema, candidate-pool, duplicate,
  support-exclusion, and molecular constraint requirements?
- raw model behavior: what the model returned before deterministic repair.
- final guarded-system behavior: what was scored after validator repair, where
  applicable.

This is the core paper contention: activity alone can ignore constraints, while
compliance alone can be nearly trivial. The relevant question is whether systems
can achieve both useful prioritisation and specification compliance.

## QSAR Baseline

QSAR means quantitative structure-activity relationship modelling. In this run,
each QSAR model is trained separately per decision card using only support-set
Morgan fingerprints and measured support activity. The trained model predicts
candidate activity and ranks feasible candidates. QSAR does not see hidden
candidate activity, so it is a deployable non-language baseline rather than an
oracle.

The three QSAR variants are:

- `qsar_rf`: random forest regressor.
- `qsar_gbt`: gradient-boosting regressor.
- `qsar_svm`: sparse-scaled linear-kernel support-vector regressor.

The fact that all three QSAR variants are strong here means LLM systems should
be compared against QSAR, not only against other LLMs. It does not mean QSAR is
ground truth or a universal activity predictor.

## Headline Results

| System | Feasible utility | 95% CI | NDCG@k | Compliance |
| --- | ---: | ---: | ---: | ---: |
| Oracle upper-bound | 89.022 | 87.394-90.604 | 1.000 | 1.000 |
| QSAR linear SVR | 81.382 | 79.532-83.271 | 0.910 | 1.000 |
| QSAR gradient boosting | 80.888 | 78.778-82.956 | 0.900 | 1.000 |
| QSAR random forest | 80.634 | 78.652-82.548 | 0.901 | 1.000 |
| LLM + validator, OpenAI gpt-5.5 low reasoning Direct JSON | 78.188 | 76.316-80.093 | 0.881 | 1.000 |
| LLM + tools + validator, OpenAI gpt-5.5 low reasoning Direct JSON | 77.688 | 75.702-79.794 | 0.873 | 1.000 |
| LLM + tools, OpenAI gpt-5.5 low reasoning Direct JSON | 77.173 | 75.115-79.295 | 0.870 | 0.990 |
| Similarity-to-best-active baseline | 73.603 | 70.825-76.490 | 0.825 | 1.000 |

The best direct-JSON LLM rows were useful and substantially better than the
rules-only/random region, but they remained below all three QSAR baselines. The
best raw LLM utility was `77.209` for OpenAI gpt-5.5 low-reasoning
Direct-JSON with tools and validator instrumentation, before final repair.

Paired bootstrap over the same 50 cards strengthens the main comparison:
`qsar_svm` exceeded the best final LLM row by `3.194` feasible-utility points
with a 95% paired-bootstrap interval of `1.942` to `4.692`. The oracle exceeded
`qsar_svm` by `7.639` feasible-utility points, showing remaining headroom.

## Hypothesis Readout

- H1, validators improve compliance more reliably than utility: supported as a
  reporting distinction. Validator-assisted final scores can improve, but raw
  metrics are needed to avoid attributing deterministic repair to the model.
- H2, QSAR and similarity baselines are competitive: supported. QSAR is the
  strongest deployable family in this LO run; similarity remains a serious
  simple comparator.
- H3, useful LLM systems are likely hybrid rather than naked LLMs: partially
  supported. Tool-summary and validator rows can improve over bare LLM rows, but
  this is not yet the broader agent design where QSAR, RDKit, similarity, and
  retrieval are callable tools.
- H4, compliance and utility are imperfectly correlated: supported. Several
  rows reach near-perfect compliance while differing substantially in feasible
  utility.

## Interpretation Notes

- Treat `oracle_valid_topk` as an upper-bound control only.
- Treat direct-JSON rows as the cleanest current cross-provider LLM comparison.
- Treat original high-reasoning frontier failures as interface/output-budget
  diagnostics unless rerun under a high-reasoning-compatible input design.
- Do not claim that LLMs are intrinsically poor at medicinal chemistry from this
  run alone. The more defensible claim is that, under the current full-pool
  interface, strong conventional QSAR baselines remain difficult to beat.
- Do not scope-creep this result into VS, de novo generation, docking, ADMET, or
  a broader autonomous agent benchmark.
