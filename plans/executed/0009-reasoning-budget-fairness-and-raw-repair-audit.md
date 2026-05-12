# 0009 Reasoning-Budget Fairness and Raw-Repair Audit

## Objective

Separate raw LLM behavior from validator-repaired behavior and add fair selector/reasoning-budget model conditions for the paper-50 frontier runs.

## Scope

- Preserve the original full-candidate-pool decision task.
- Store raw LLM outputs and raw validation issues in traces.
- Add raw-vs-final scoring fields and report columns.
- Add provider controls for prompt profile, thinking budget, and request timeout.
- Add direct-selector and reasoning-budget pilot model conditions.

## Non-Goals

- No candidate compression or shortlist reranking.
- No new baseline family.
- No de novo molecule generation.
- No silent substitution of weaker provider models.

## Affected Modules

- `src/specguard_chem_v2/schemas.py`
- `src/specguard_chem_v2/runner.py`
- `src/specguard_chem_v2/scoring.py`
- `src/specguard_chem_v2/systems/providers.py`
- `src/specguard_chem_v2/systems/llm.py`
- `src/specguard_chem_v2/reports.py`
- `configs/model_matrix.toml`
- `tests/`
- `docs/` and `plans/`

## Tasks

1. Add backward-compatible raw-output fields to `RunRecord`.
2. Preserve pre-repair output and issues during validator runs.
3. Add raw-vs-final scoring fields and summary aggregation.
4. Add prompt profile, thinking budget, and request timeout config fields.
5. Add `json_first` message profile without changing candidate payload content.
6. Add selector and reasoning-budget model conditions.
7. Add regression tests for cache identity, raw repair accounting, and Anthropic thinking config validation.
8. Update durable docs and complete an execution log.

## Validation Commands

```bash
uv run pytest
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_frontier_selector --model-matrix configs/model_matrix.toml --out /tmp/sgchem_selector_requests.jsonl
```

## Acceptance Criteria

- Existing traces without raw fields still load.
- New traces include `raw_output` and `raw_issues`.
- Validator summaries expose repaired rate, repaired-from-empty rate, and raw/final utility separation.
- Changing prompt profile or thinking budget changes request cache identity.
- Selector and reasoning-budget model conditions are listed by `sgchem list-model-matrix`.
- Tests pass.

## Risks

- Provider APIs may reject some new frontier settings; preflight runs must log exact errors and only use the predefined OpenAI `minimal` to `low` fallback.
- Historical traces will have null raw fields because they did not persist raw outputs.

## Handoff Notes

Code/config/reporting implementation is complete. The direct-JSON matrix has
complete live results under `runs/cara_lo_paper_50_selector_matrix`: OpenAI,
Anthropic, and DeepSeek each completed all four LLM system variants on the 50
frozen cards. The reasoning-budget pilot was intentionally deferred because
high-reasoning modes still need a compressed or staged interface plan.
