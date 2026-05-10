# 0004 LLM Agent Systems

Status: completed on 2026-05-10. See
`plans/logs/2026-05-10-0005-llm-agent-systems.md`.

## Objective

Make the LLM conditions robust, cacheable, replayable, and clearly separated
from deterministic baselines.

## Scope

- Prompt/request templates.
- Request export for review and provider runs.
- Cache/replay fixtures.
- Validator and tool-summary ablations.

## Non-Goals

- Do not make live provider calls in default validation.
- Do not add multi-provider orchestration until the OpenAI path is stable.

## Affected Modules

- `specguard_chem_v2.systems.llm`
- `specguard_chem_v2.cli`
- `docs`
- `tests/fixtures/llm_cache`

## Tasks Completed

- Documented all four LLM conditions in `docs/LLM_SYSTEMS.md`.
- Added provider message construction separate from structured request payloads.
- Added `export-llm-requests`.
- Added tests for bare vs tool-enabled request payloads.
- Verified cached LLM replay through `run-suite`.

## Validation Commands

```bash
uv run --extra dev pytest
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems bare_llm,llm_tools --out /tmp/sgchem_llm_requests.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --cache-dir tests/fixtures/llm_cache --out runs/fixture_llm
```

## Acceptance Criteria

- Cached LLM runs require no network.
- Live calls fail closed unless `--allow-external` is set.
- Tool-enabled requests contain descriptor summaries not present in bare LLM
  requests.

## Risks

- Prompt output may be malformed; schema normalization must stay explicit.

## Handoff Notes

Promote `plans/upcoming/0005-reporting-and-paper-artifacts.md` next.
