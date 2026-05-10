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

- `oracle_valid_topk` as an oracle upper-bound control, reported separately from
  model/system leaderboards.
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

## Main Comparisons

- LLM-only vs LLM + validator.
- LLM + tools vs LLM + tools + validator.
- QSAR vs rules/similarity baselines.
- All agentic systems vs best non-language baseline.
