# 2026-05-11 0007 Provider Model Run Readiness

## Summary

Prepared the harness for controlled LLM provider/model experiments. The repo now
has a model matrix, provider-specific live-call adapters for OpenAI, Anthropic,
and DeepSeek, matrix request export, and an offline-safe `run-llm-matrix` CLI
workflow. Matrix runs label each scored system as `{llm_system}__{model_config}`
so provider/model conditions remain distinct in comparison tables.

## Commands Run

```bash
uv run pytest tests/test_runner_scoring_reports.py tests/test_cli.py
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems llm_tools --model-matrix configs/model_matrix.toml --model-conditions openai_fast,deepseek_fast --out /tmp/sgchem_matrix_requests.jsonl
uv run sgchem run-llm-matrix tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_fast,deepseek_fast --out /tmp/sgchem_matrix_offline
uv run ruff check src/specguard_chem_v2/systems/llm.py src/specguard_chem_v2/systems/providers.py tests/test_runner_scoring_reports.py tests/test_cli.py --fix
uv run ruff check src/specguard_chem_v2/systems/llm.py src/specguard_chem_v2/systems/providers.py tests/test_runner_scoring_reports.py tests/test_cli.py
uv run pytest
git diff --check
```

## Tests

Final result:

```text
14 passed
```

Additional checks:

- Matrix request export wrote 4 fixture requests for 2 cards x 1 system x 2
  model conditions.
- Offline matrix smoke completed `llm_tools_validator__openai_fast` and
  `llm_tools_validator__deepseek_fast`.
- Ruff passed on the files touched by this provider-matrix slice.
- A full-project ruff run was attempted and exposed older line-length/import
  issues outside this slice; those were not broadened into this change.

## Files Changed

- Added `configs/model_matrix.toml`.
- Added `specguard_chem_v2.systems.providers`.
- Extended `specguard_chem_v2.systems.llm` with OpenAI, Anthropic, and DeepSeek
  provider paths.
- Extended runner/scoring/reporting so model-matrix run labels and metadata are
  preserved.
- Added `list-model-matrix` and `run-llm-matrix` CLI commands.
- Updated LLM, experiment protocol, and runbook docs.
- Added tests for model-matrix request export, offline matrix runs, and variant
  ablation tables.

## Decisions

- Keep the full live LLM run out of this implementation slice.
- Use `configs/model_matrix.toml` as the stable source of provider/model
  conditions.
- Label scored matrix systems as `{system_name}__{model_config_id}`.
- Do not store DeepSeek raw reasoning content by default; record whether it was
  present instead.
- Keep live calls opt-in through `--allow-external`.

## Follow-Up Work

- Create a paper-scale experiment plan before running live provider calls.
- Freeze the final CARA LO card artifact and record its checksum.
- Export and review full-card LLM requests before `--allow-external`.
- Decide whether to include all four LLM system conditions for every provider or
  reserve full-card live runs for `llm_tools` and `llm_tools_validator`.
