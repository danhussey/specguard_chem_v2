# Experiment Protocol

## Primary Dataset

Use CARA lead-optimisation few-shot tasks as the primary substrate. Support
compounds become the observed project state; query compounds become the hidden
candidate pool.

## Inclusion Rules

- Consider every one of the 100 official CARA `LO_All` task keys.
- Require exactly 50 support compounds with supplied pChEMBL activity, explicitly
  interpreted as higher-is-better.
- Include a task only when at least `budget_k = 10` candidates remain after the
  frozen molecular constraints.
- Require unique candidate IDs, no support--candidate identity overlap, and
  structures parseable by RDKit; any task/coherence mismatch is a hard error.
- Apply no hidden-outcome criterion when selecting tasks.

## Systems

Mandatory systems:

- `oracle_valid_topk` as an oracle upper-bound control. It ranks feasible
  candidates using scorer-only candidate activity values, so it is not a
  deployable system and must be reported separately from model/system
  leaderboards.
- `random_valid`
- `rules_only`
- `similarity_to_best_active`
- `qsar_rf`
- `qsar_gbt`
- `qsar_svm`
- `bare_llm`
- `llm_tools`

The primary LLM matrix crosses these two raw interfaces with the three frozen
provider/model conditions. Prompt-based validator variants are not part of the
primary experiment. A guarded-system view is derived post hoc from each raw
response using the deterministic repair policy, with zero additional provider
calls and explicit raw-versus-repaired attribution.

LLM systems must support cache/replay and must not make live calls unless
`--allow-external` is set.

Replay cache lookup accepts either content-addressed files written by live runs
or stable fixture files named `{system_name}__{task_id}.json`. Stable fixture
files are for tests and review packets only.

`run-suite --systems all` expands to non-oracle deterministic systems plus LLM
systems. `all-with-oracle` additionally includes `oracle_valid_topk`.

See `docs/LLM_SYSTEMS.md` for condition definitions and request-export workflow.

## Oracle And QSAR Interpretation

The oracle answers: "What score would we get if we already knew the hidden
candidate activity and selected the best valid top-k set?" Comparing baselines
to the oracle checks whether a card has real decision headroom. If ordinary
baselines are almost at oracle, the task may be too easy. If oracle is much
higher, there is meaningful utility left to recover.

QSAR means quantitative structure-activity relationship. In this harness, QSAR
systems train conventional molecular ML regressors on support-set compounds and
their measured activity, then predict candidate activity from molecular
fingerprints. QSAR is the key non-language chemistry baseline: LLM systems should
be compared against it, not only against other LLMs.

## Main Comparisons

- Each raw LLM condition versus the best assay-local QSAR baseline on paired
  cards, with utility and regret as the primary scientific comparison.
- Basic versus descriptor-enriched representation within each model condition.
- Raw action versus deterministic post-hoc repair of the same response.
- QSAR versus rules, similarity, and random-valid baselines.
- Every LLM condition across the frozen provider/model matrix, with latency,
  token use, and cost reported separately from scientific utility.
