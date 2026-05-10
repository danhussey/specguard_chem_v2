# Experiment Protocol

## Primary Dataset

Use CARA lead-optimisation few-shot tasks as the primary substrate. Support
compounds become the observed project state; query compounds become the hidden
candidate pool.

## Inclusion Rules

- Task has at least one support compound with activity.
- Task has enough candidates to return `budget_k` after hard constraints.
- Candidate IDs are unique within a decision card.
- SMILES parse under RDKit.

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
- `llm_validator`
- `llm_tools`
- `llm_tools_validator`

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

- LLM-only vs LLM + validator.
- LLM + tools vs LLM + tools + validator.
- QSAR vs rules/similarity baselines.
- All agentic systems vs best non-language baseline.
- Each LLM condition across the configured provider/model matrix.
