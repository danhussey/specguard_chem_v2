# Cost Control

Live LLM runs must be estimated before expensive execution. The estimator is
conservative: uncached calls are priced as if they use the estimated prompt
tokens plus the full configured output budget. Chemical JSON tokenizes densely,
so the default estimate uses a strict character-to-token ratio plus a safety
multiplier.

## Estimate Before Running

```bash
uv run sgchem estimate-llm-cost data/cards/cara_lo_paper_50.jsonl \
  --systems bare_llm,llm_validator,llm_tools,llm_tools_validator \
  --model-conditions openai_frontier_selector,anthropic_frontier_selector \
  --out-run-dir runs/cara_lo_paper_50_selector_matrix \
  --out runs/cara_lo_paper_50_selector_matrix/cost_estimate.json
```

The estimate reports:

- total planned requests;
- calls already covered by complete traces or replay cache;
- missing live calls;
- maximum estimated input tokens for any missing call;
- estimated incremental cost.

Pricing lives in `configs/provider_pricing.toml`. It is a snapshot, not a source
of truth. Check provider pricing pages before large runs.

## Gate Live Runs

Use hard gates whenever `--allow-external` is set:

```bash
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl \
  --systems llm_tools,llm_tools_validator \
  --model-conditions openai_frontier_selector \
  --out runs/cara_lo_paper_50_selector_matrix \
  --allow-external \
  --require-cost-estimate \
  --max-estimated-cost-usd 25 \
  --max-live-calls 50 \
  --max-input-tokens-per-call 175000
```

The command writes `cost_estimate.json` into the run directory and aborts before
provider calls if any gate fails.

## Resume Behavior

`run-llm-matrix` skips complete trace files by default and reuses response
caches for incomplete systems. Pass `--force` only when intentionally rerunning a
completed condition.

## Recommended Ladder

1. One-card preflight.
2. Five- or ten-card pilot with cost gates.
3. Full direct-JSON run after estimated cost is acceptable.
4. High-reasoning/thinking runs only as small pilots until the interface is
   redesigned or compressed.
