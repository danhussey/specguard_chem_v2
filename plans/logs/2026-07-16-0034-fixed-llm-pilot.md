# 0034 Fixed LLM Pilot

## Outcome

The corrected, cost-gated one-card provider pilot completed across the two
frozen interfaces and three provider conditions. All six raw responses, shared
cache records, score artifacts, and deterministic post-hoc views are retained.
The pilot passed its execution and provenance audit. It is explicitly treated
as a one-card operational case study, not as the paper's model comparison.

## Pre-run safety and identity

- Live-run hardening is committed in `cf7f4ee`.
- SDK retries are disabled and each missing request permits one provider
  attempt; malformed or invalid output is retained rather than repurchased.
- Configured and provider-returned model names, response IDs, exact raw text and
  structured content, finish reason, usage, latency, attempt count, and
  pricing-derived cost are retained.
- Raw action validation occurs before normalization, and post-hoc repair is a
  separate zero-call transform.
- The pilot task is `CARA_LO_CHEMBL1006579_IC50_0001` and the six-request export
  SHA256 is
  `a9ddda7117ba588c2c3e5dd240f0633e131590110b0ef52d7fc4e995ecb827a4`.
- The no-call gate recorded six missing requests, maximum conservative input
  25,817 tokens, and USD 0.936717455 upper-bound incremental cost.

## Executed command

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
  --max-input-tokens-per-call 30000 \
  --workers 1
```

The run began at `2026-07-16T14:21:58.725311+00:00`. It did not continue into
the residual full matrix.

## Artifact and provenance audit

- Manifest entries: 6.
- Raw trace rows: 6, one per condition/interface.
- Shared response-cache records: 6, with six unique request digests and six
  unique response IDs.
- Provider attempts: 6 total; every trace records
  `provider_attempt_count = 1`.
- Model identity: configured and provider-returned IDs agree for GPT-5.5
  `2026-04-23`, Claude Opus 4.8, and DeepSeek V4 Pro.
- Parse/contract status: all six responses contain one parseable object, exactly
  ten unique selections ranked 1--10, and no response-contract issue.
- Operational coverage: usage, latency, and cost coverage are all 100%.
- Usage: 106,128 input tokens and 3,024 output tokens, including 1,024 OpenAI
  reasoning tokens.
- Actual cost: USD 0.449700535, below the USD 0.936717455 pilot gate.

## One-card observations

OpenAI and Anthropic issued valid actions in both interfaces. Their raw feasible
utilities were 74.690/74.170 and 72.040/72.415, respectively. DeepSeek's basic
response selected eight compounds above the cLogP constraint, leaving 2/10
valid selections and raw utility 15.200. Its descriptor-enriched response
selected nine support compounds, leaving 1/10 valid selection and raw utility
7.960.

All six outputs were syntactically clean. The contrast is therefore not a parser
artifact: generic JSON success did not imply an executable experimental action.
This is the pilot's central diagnostic value. It does not establish a model
ranking, because it is one response per interface on one assay task.

Task-matched deterministic context ranges from rules-only 64.125 and
random-valid 64.975 through similarity 74.790 and QSAR 73.380--74.970 to oracle
78.570. OpenAI is close to similarity/QSAR on this card and Anthropic is above
random-valid, but those observations are not generalized in the manuscript.

## Repair, replay, and residual estimate

Post-hoc repair added zero provider calls. It was a no-op for OpenAI and
Anthropic. For DeepSeek it retained 2/10 and 1/10 original selections, filled
the rest with the declared rules-only fallback, and raised final utility to
65.350 and 64.930. Those values are model-plus-harness outcomes, not raw model
ability.

An offline replay from the shared cache completed all six conditions with zero
external calls. All score artifacts were byte-identical; replay trace rows add
only the expected `cache_path` metadata.

The saved post-pilot estimate reports:

- 546 total planned requests;
- 6 cached requests;
- 540 missing live calls;
- USD 0.449700535 actual cached pilot cost; and
- USD 105.122676615 conservative residual upper bound.

The residual command remains separately unauthorized.

## Validation

- `pytest -p no:cacheprovider`: 60 passed.
- `ruff check --no-cache src tests`: passed.
- `ruff format --check --no-cache src tests`: 31 files already formatted.
- Frozen paired card validation: 91 cards passed.
- Manuscript generated-result check: passed; the full-result gate remains
  closed because no complete six-condition 91-card comparison exists.
- Manuscript and supplement compiled with bundled Tectonic and were rendered
  page-by-page for visual inspection: six and two pages, respectively, with no
  clipping or layout defect.
- The pilot cost regression test now uses an isolated empty cache so it remains
  valid after the canonical six-response cache was populated.

## Boundary

No residual provider call, final manifest, checksum freeze, tag, push, DOI, or
publication action occurred. The next live step requires explicit approval for
up to 540 missing calls under a fresh pricing/model/context verification and the
prespecified USD 119 residual gate.
