# 0010 Cost Controls And High-Reasoning Prompt Audit

## Objective

Add conservative cost estimation and hard live-run gates before more provider
spend, and document why high-reasoning modes need a compressed or staged
interface.

## Scope

- Add provider pricing config.
- Add `estimate-llm-cost`.
- Add cost gates and resume-aware skipping to `run-llm-matrix`.
- Add concise cost-control and high-reasoning interface docs.
- Preserve current full-pool task semantics.

## Non-Goals

- No live provider run.
- No candidate compression implementation.
- No model-condition rename in this milestone.

## Affected Modules

- `src/specguard_chem_v2/costing.py`
- `src/specguard_chem_v2/cli.py`
- `src/specguard_chem_v2/systems/llm.py`
- `configs/provider_pricing.toml`
- `docs/`
- `tests/`

## Tasks

1. Implement pricing config loading and conservative token/cost estimates.
2. Detect complete traces and response caches before estimating live calls.
3. Add CLI cost-estimate command.
4. Add cost gates to live matrix execution.
5. Skip complete traces by default and require `--force` to rerun them.
6. Add tests for estimate output and gate failure.
7. Document cost-control workflow and high-reasoning interface options.

## Validation Commands

```bash
uv run pytest
uv run sgchem estimate-llm-cost tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_fast,deepseek_fast --out-run-dir /tmp/sgchem_cost_fixture --out /tmp/sgchem_cost_fixture.json
```

## Acceptance Criteria

- Cost estimates report missing live calls and incremental estimated cost.
- Live matrix runs can abort before provider calls when cost gates fail.
- Completed traces are skipped by default.
- Pricing config is explicit and source-linked.
- High-reasoning compression options are documented separately from current runs.

## Risks

- Token estimates are approximate for uncached calls; use conservative safety
  multipliers and treat provider bills as final truth.
- Provider prices change; update `configs/provider_pricing.toml` before large
  runs.

## Handoff Notes

Use cost gates for any further live LLM work. Do not run high-reasoning modes at
paper scale until a small pilot and interface-compression plan pass budget and
raw-JSON checks.
