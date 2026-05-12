# 2026-05-12 0012 Cost Controls And Prompt Audit

## Summary

Added conservative LLM cost estimation, hard run gates, resume-aware completed
trace skipping, provider pricing config, and concise docs for cost control and
high-reasoning interface redesign.

## Commands Run

```bash
uv run pytest
```

## Tests

- `uv run pytest`: 18 passed.

## Files Changed

- Added `src/specguard_chem_v2/costing.py`.
- Added `configs/provider_pricing.toml`.
- Added `sgchem estimate-llm-cost`.
- Added cost gates to `sgchem run-llm-matrix`.
- Added public LLM request hash/cache helpers.
- Added `docs/COST_CONTROL.md`.
- Added `docs/HIGH_REASONING_INTERFACE_OPTIONS.md`.
- Updated `AGENTS.md`, `docs/RUNBOOK.md`, and `docs/LLM_FAILURE_MODES.md`.

## Decisions

- Estimates are conservative and price uncached calls against full configured
  output budget.
- Existing complete traces are skipped by default; use `--force` for intentional
  reruns.
- High-reasoning work remains pilot-only until prompt compression or staged
  interfaces are designed and tested.

## Follow-Up Work

- Run `estimate-llm-cost` against the remaining direct-JSON matrix before
  topping up or resuming providers.
- Rename `selector` model conditions/artifacts to `direct_json` in a separate,
  careful migration.
- Add a first-class prompt-audit report if prompt inspection becomes frequent.
