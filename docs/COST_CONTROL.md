# Cost Control

Live LLM calls are never required for tests, card validation, deterministic
baselines, request export, costing, or post-hoc repair. A live command requires
both explicit user authorization and `--allow-external`.

## Frozen v0.1.0 Matrix

The release experiment has exactly two raw interfaces and three model
conditions:

- `bare_llm` and `llm_tools`;
- `openai_gpt_5_5_2026_04_23_selector`;
- `anthropic_opus_4_8_selector`; and
- `deepseek_v4_pro_2026_07_16_selector`.

Across 91 cards this is `91 × 2 × 3 = 546` provider requests. Deterministic
repair is applied post hoc to recorded traces and adds zero provider requests.
The former four-prompt matrix, which paid separately for validator prompt
variants, is historical and is not the v0.1.0 design.

The matrix is now complete: 546/546 requests have successful
content-addressed cache records; six raw and six zero-call post-hoc-repaired
traces each cover all 91 cards; and the canonical manifest and comparison are
present. Usage, latency, and pricing-derived cost coverage are 100%. The
usage-derived token-pricing total is USD 58.95671601.

## Estimate Before Running

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --pricing configs/provider_pricing.toml \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out-run-dir release/v0.1.0/experiments/llm/matrix \
  --out release/v0.1.0/experiments/llm/pre_run_cost_estimate.json
```

The frozen pre-run estimate reports 546 missing live calls, a maximum
conservative input estimate of 158,274 tokens, and an upper-bound incremental
cost of USD 106.0594. It assumes the configured maximum output budget for every
uncached call, so it is a spend gate rather than a forecast of the final invoice.

Pricing in `configs/provider_pricing.toml` was checked on 2026-07-16. It is a
versioned snapshot, not a source of truth: verify provider pricing, context
limits, and model availability again immediately before an authorized run. If
any value or model changes, regenerate the exact-request and cost artifacts and
record the change as a new condition/version.

## Pre-Pilot Whole-Matrix Ceiling

The following records the historical pre-pilot ceiling for all 546 unique
requests. The staged procedure used tighter pilot and residual gates. The
six-call pilot and separately authorized residual execution have both since
completed; this command is retained as pre-execution provenance, not standing
authorization to purchase responses.

```bash
uv run --extra providers sgchem run-llm-matrix \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out release/v0.1.0/experiments/llm/matrix \
  --allow-external \
  --require-cost-estimate \
  --max-estimated-cost-usd 120 \
  --max-live-calls 546 \
  --max-input-tokens-per-call 175000
```

The runner writes a fresh `cost_estimate.json` and aborts before provider calls
if any gate fails.

## Fixed One-Card Pilot Gates

The pilot uses the first frozen task, selected by the stable identifier
`CARA_LO_CHEMBL1006579_IC50_0001`. It preserves both raw interfaces and all
three model conditions, so its call limit is exactly six. At the frozen pricing
snapshot its no-call estimate is USD 0.936717455 and the largest conservative
input estimate is 25,817 tokens.

This exact command was explicitly authorized and executed once. It is retained
as the run record, not as standing authorization to repurchase the responses:

```bash
uv run --extra providers sgchem run-llm-matrix \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --task-id CARA_LO_CHEMBL1006579_IC50_0001 \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out release/v0.1.0/experiments/llm/pilot \
  --allow-external \
  --require-cost-estimate \
  --max-estimated-cost-usd 1 \
  --max-live-calls 6 \
  --max-input-tokens-per-call 30000
```

The USD 1, six-call, and 30,000-token gates were pilot-specific. The shared
matrix cache was mandatory for the residual execution because it prevented
repurchasing those same six requests, and it remains mandatory for provenance-
preserving replay. The exact offline export and estimate commands are in
`release/v0.1.0/REPRODUCE.md`.

The pilot completed six of six requests with one provider attempt per request,
complete usage/latency/model/raw-response provenance, and actual aggregate cost
USD 0.449700535. Its raw traces, deterministic repaired views, scores, and audit
record are under `release/v0.1.0/experiments/llm/pilot/`. A cache-only replay
reproduced every score artifact without provider access.

One missing request is exactly one provider attempt. The live adapters disable
SDK retries and do not repurchase a response merely because its JSON or action
contract is invalid. Such a response is preserved, cached, and scored as the
single raw action. A transport/API exception aborts execution rather than being
converted into a zero-utility model response. Every successful response must
record `provider_attempt_count = 1`; otherwise the run is not release evidence.

The historical post-pilot estimate passed review: it reported six cached
requests, exactly 540 missing requests, a residual conservative upper bound of
USD 105.122676615, and USD 0.449700535 of cached actual pilot cost. It was
recomputed immediately before the residual execution, and the counts and
frozen pricing still satisfied the gates.

The check passing did not itself authorize spend. Separate explicit approval
was received before the residual gates were used:

```bash
uv run --extra providers sgchem run-llm-matrix \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out release/v0.1.0/experiments/llm/matrix \
  --allow-external \
  --require-cost-estimate \
  --max-estimated-cost-usd 119 \
  --max-live-calls 540 \
  --max-input-tokens-per-call 175000
```

The pilot USD 1 gate plus residual USD 119 gate preserve the USD 120 aggregate
ceiling. A missing pilot cache entry makes the 540-call gate fail; do not raise
the gate to work around it.

The completed cache now has 546/546 successful provider responses. The
canonical output contains six raw and six zero-call post-hoc-repaired 91-card
traces, one six-condition manifest, and the combined comparison. Operational
usage, latency, and pricing-derived cost coverage are 100%; actual recorded
usage under the frozen token-pricing snapshot totals USD 58.95671601. No
additional external call is required to replay or rescore this matrix.

Task-selection and chemical-diversity changes were deliberately excluded from
the corrected execution and are deferred to a future benchmark version.

## Resume and Cache Rules

`run-llm-matrix` skips complete trace files and reuses content-addressed response
caches by default. Request hashes include the system interface, exact public
input, prompt profile, provider/model condition, token budget, temperature, and
reasoning/thinking settings. Pass `--force` only for an intentional, documented
rerun.

Do not count cached or completed calls twice. Do not overwrite a partial trace
with an unrelated request configuration. Preserve provider-returned model IDs,
verbatim response text and structured content, finish reasons, usage, latency,
attempt counts, errors, and cache keys with the trace.

## Cost-Neutral Post-hoc Repair

After raw traces exist, guarded-system behavior is derived from those same
responses:

```bash
uv run sgchem repair-llm-trace \
  data/releases/v0.1.0/system_input_cards.jsonl \
  release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/trace.jsonl \
  --out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_repair.trace.jsonl \
  --scores-out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_scores \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

This operation is deterministic, makes no network request, and must remain
separate from raw model performance.
