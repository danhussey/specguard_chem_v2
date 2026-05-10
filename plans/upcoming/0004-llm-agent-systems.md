# 0004 LLM Agent Systems

## Objective

Make the LLM conditions robust, cacheable, replayable, and clearly separated
from deterministic baselines.

## Scope

- Prompt templates.
- OpenAI provider path.
- Cache/replay fixtures.
- Validator and tool-summary ablations.

## Non-Goals

- Do not add multi-provider orchestration until OpenAI path is stable.

## Affected Modules

- `specguard_chem_v2.systems.llm`
- `specguard_chem_v2.runner`
- `tests/fixtures/llm_cache`

## Tasks

- Add provider integration tests behind environment gates.
- Add cached replay tests for all four LLM systems.
- Record prompt templates in docs.
- Add cost and token metadata capture when provider data is available.

## Validation Commands

```bash
uv run pytest
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --cache-dir tests/fixtures/llm_cache --out runs/fixture_llm
```

## Acceptance Criteria

- Cached LLM runs require no network.
- Live calls fail closed unless `--allow-external` is set.
- Validator ablations preserve comparable prompts and candidate pools.

## Risks

- Prompt output may be malformed; schema normalization must stay explicit.

## Handoff Notes

Keep live provider behavior behind one narrow adapter boundary.
