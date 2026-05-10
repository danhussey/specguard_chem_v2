# 0006 Provider Model Run Readiness

Status: completed on 2026-05-11. See
`plans/logs/2026-05-11-0007-provider-model-run-readiness.md`.

## Objective

Prepare the harness for a controlled live LLM experiment across OpenAI,
Anthropic, and DeepSeek model conditions, while preserving cache/replay,
traceability, and fair comparison against deterministic baselines and oracle
controls.

## Scope

- Provider/model matrix configuration.
- Provider-specific live-call adapters.
- Matrix request export and matrix run CLI workflow.
- Trace metadata for provider, model, request hash, latency, and token usage.
- Documentation for oracle controls, QSAR, and pre-run checks.
- Fixture-level non-live validation.

## Non-Goals

- Do not run the full paper-scale live LLM experiment in this implementation
  slice.
- Do not expose hidden/scorer-only candidate activity to LLM requests.
- Do not tune prompts or card selection after seeing live results.

## Affected Modules

- `configs`
- `src/specguard_chem_v2/systems`
- `src/specguard_chem_v2/runner.py`
- `src/specguard_chem_v2/cli.py`
- `docs`
- `tests`

## Tasks Completed

- Added a pinned model matrix for frontier/reasoning and fast conditions.
- Added model-matrix loading and selection helpers.
- Routed OpenAI, Anthropic, and DeepSeek calls through a common LLM adapter.
- Added `run-llm-matrix` and model-matrix request export support.
- Ensured matrix traces use distinct system labels.
- Added fixture tests for model-matrix request export and offline matrix runs.
- Updated runbook/LLM docs with pre-run guidance.

## Validation Commands

```bash
uv run pytest
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems llm_tools --model-matrix configs/model_matrix.toml --model-conditions openai_fast,deepseek_fast --out /tmp/sgchem_matrix_requests.jsonl
uv run sgchem run-llm-matrix tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_fast,deepseek_fast --out /tmp/sgchem_matrix_offline
```

## Acceptance Criteria

- Tests pass.
- Matrix request export creates one row per card, system, and selected model
  condition.
- Offline matrix runs produce scored trace directories without network access.
- Live calls remain opt-in via `--allow-external`.
- Provider/model metadata is recorded in traces or output metadata.

## Risks

- Provider APIs differ in JSON-output enforcement and reasoning controls.
- Model aliases may change; use pinned IDs where providers document them as
  pinned.
- Reasoning output should not become part of the scored artifact unless needed
  for debugging and explicitly documented.

## Handoff Notes

Create a separate paper-scale experiment plan to freeze cards, run deterministic
baselines, export/review full LLM requests, then run live LLM conditions with
`--allow-external`.
