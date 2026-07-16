# LLM Systems

SpecGuard-Chem evaluates an LLM as the decision component of a bounded
experimental workflow. Given sparse project-local assay evidence and a fixed
candidate pool, it must return exactly `k=10` valid candidate IDs in ranked
order. The benchmark does not ask the model to invent molecules, syntheses, or
assays.

No v0.1.0 live LLM result should be claimed until the frozen matrix has complete
provider traces. The exact requests and pre-run cost estimate are release
artifacts; they are not model-performance results.

## System-visible Input

LLM systems consume only
`data/releases/v0.1.0/system_input_cards.jsonl`. It contains support activities,
candidate identities/structures, assay context, constraints, and the benchmark
provenance needed to bind a request to the frozen artifact. Candidate activity
labels and local source paths are absent. Hidden labels remain in
`scorer_outcomes.jsonl` and enter only validation/scoring paths.

The release compares two raw interfaces:

| Interface | System-visible representation |
| --- | --- |
| `bare_llm` | Support examples, candidate IDs and SMILES, minimal descriptors, hard constraints, and output schema. |
| `llm_tools` | The same task plus deterministic computed descriptor/tool-summary fields for candidates. |

Both use the `json_first` profile: one JSON object, no rationale, markdown, or
preamble. The interface comparison asks whether deterministic chemical tooling
improves selection from the same fixed pool.

`llm_validator` and `llm_tools_validator` remain available for historical
replay and small engineering tests, but they are not provider-call conditions
in v0.1.0. The release derives a guarded view post hoc from each raw response,
which avoids paying for and confounding a second prompt.
Accordingly, the export, estimate, and matrix-run CLI defaults include only
`bare_llm,llm_tools`; historical prompt variants require an explicit
`--systems` value.

## Frozen Provider Matrix

The three release condition IDs are immutable experiment identifiers:

| Condition ID | Provider model | Interface settings |
| --- | --- | --- |
| `openai_gpt_5_5_2026_04_23_selector` | `gpt-5.5-2026-04-23` | Low reasoning, 4,096 output-token cap, direct JSON. |
| `anthropic_opus_4_8_selector` | `claude-opus-4-8` | No extended-thinking mode, 4,096 output-token cap, direct JSON. |
| `deepseek_v4_pro_2026_07_16_selector` | `deepseek-v4-pro` alias checked 2026-07-16 | Thinking disabled, 4,096 output-token cap, direct JSON; preserve provider-returned model ID. |

This produces `91 cards × 2 interfaces × 3 conditions = 546` raw requests.
Other frontier, fast, and reasoning-budget conditions in
`configs/model_matrix.toml` are exploratory or historical; they must not be
silently substituted into the v0.1.0 matrix.

Inspect all configured conditions with:

```bash
uv run sgchem list-model-matrix configs/model_matrix.toml
```

## Exact Request Export

Request export performs no network call:

```bash
uv run sgchem export-llm-requests \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --out release/v0.1.0/experiments/llm/exact_requests.jsonl
```

The export contains the structured request, exact provider messages, public
artifact provenance, canonical per-card input hash, and response cache key.
Review it for hidden-field exclusion and prompt size before any live execution.
Each request must state that support `activity_value` is pChEMBL and that higher
values are better; an export lacking those semantics is invalid for v0.1.0.

## Live Matrix

External calls are disabled unless `--allow-external` is present. They also
require explicit authorization and the staged pilot/cost gates in
`docs/COST_CONTROL.md`. The command below is the residual run after all six
fixed pilot requests are present in the shared cache and a fresh estimate
reports exactly 540 missing requests.

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

`--workers N` changes throughput only. It does not alter prompts, cache keys,
conditions, or scoring. Provider credentials default to `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, and `DEEPSEEK_API_KEY`.

Provider errors, quota failures, overloads, and timeouts are execution failures.
They must remain explicit in run artifacts and must not be converted into a
zero-utility model response.

Each missing cache key permits one provider attempt. SDK retries are disabled;
an invalid JSON/action response is retained and scored rather than silently
repurchased. Traces and caches preserve the configured model, provider-returned
model, response ID, exact raw text and structured content, finish reason, token
usage, latency, and attempt count.

## Cache and Replay

Live responses are cached by request content. Matrix runs look under
`release/v0.1.0/experiments/llm/matrix/cache/CONDITION_ID/INTERFACE_NAME/` and skip
complete traces unless `--force` is passed. Hash inputs include prompt and
generation settings so a reasoning, budget, or profile change cannot replay a
stale response.

Default tests and offline smoke runs use fixtures or cache/replay only. An
offline cache miss is a harness diagnostic, not publishable model evidence.
Scoring writes per-card operational metrics and coverage-safe latency, token,
attempt, and pricing-derived cost totals alongside scientific metrics.

## Post-hoc Guarded View

For every complete raw trace, create a separate, attributable repaired view:

```bash
uv run sgchem repair-llm-trace \
  data/releases/v0.1.0/system_input_cards.jsonl \
  release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/trace.jsonl \
  --out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_repair.trace.jsonl \
  --scores-out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_scores \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

The transform copies `raw_output` and `raw_issues`, validates them against the
current contract, and places deterministic repair in the final `output` view.
Its system name ends in `__posthoc_repair`, its metadata binds it to the source
trace hash and repair policy, and `provider_calls_added` is always zero. It
refuses validator traces, already repaired traces, and in-place overwrite.

Report raw LLM metrics and post-hoc guarded-system metrics as distinct outcomes.
See `docs/POSTHOC_REPAIR.md` and `docs/LLM_FAILURE_MODES.md`.

## Safety and Claim Boundary

Prompt instructions prohibit new molecule IDs and unsupported synthesis,
safety, selectivity, or clinical claims. Deterministic validation—not prompt
obedience—enforces candidate membership, exact budget, uniqueness, support-set
exclusion, and candidate constraints.

Success on v0.1.0 is evidence about bounded compound selection under a fixed
action contract. It is not evidence that a model can autonomously design,
execute, or interpret a wet-lab campaign.
