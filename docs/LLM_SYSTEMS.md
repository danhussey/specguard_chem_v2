# LLM Systems

LLM systems are evaluated as systems, not standalone medicinal-chemistry oracles.
They consume structured decision cards and return ranked candidate IDs.

## Conditions

- `bare_llm`: support set, candidate IDs, SMILES, minimal descriptors, hard
  constraints, and output schema.
- `llm_validator`: same as `bare_llm`, with deterministic validator repair or
  penalty after output.
- `llm_tools`: includes computed descriptor/tool-summary fields for each
  candidate.
- `llm_tools_validator`: tool-summary request plus deterministic validation.

## Cache And Replay

Live calls are disabled unless `--allow-external` is passed to run commands.
Replay cache files may be content-addressed files written by live runs or stable
fixture files named `{system_name}__{task_id}.json`. Model-matrix runs also
check stable files named `{system_name}__{model_config_id}__{task_id}.json`.
Generation settings such as token budget, temperature, reasoning effort, and
thinking mode are included in new request hashes so budget changes do not replay
stale provider responses.

## Provider Model Matrix

Provider/model conditions are configured in `configs/model_matrix.toml`. The
default matrix has one frontier/reasoning condition and one fast condition for
each supported provider:

| Condition | Provider | Model | Intended role |
| --- | --- | --- | --- |
| `openai_frontier` | OpenAI | `gpt-5.5` | Frontier reasoning/professional-work condition. |
| `openai_fast` | OpenAI | `gpt-5.4-mini` | Lower-latency OpenAI condition. |
| `anthropic_frontier` | Anthropic | `claude-opus-4-7` | Anthropic most capable condition. |
| `anthropic_fast` | Anthropic | `claude-haiku-4-5-20251001` | Anthropic fastest condition. |
| `deepseek_frontier` | DeepSeek | `deepseek-v4-pro` | DeepSeek pro condition with thinking enabled. |
| `deepseek_fast` | DeepSeek | `deepseek-v4-flash` | DeepSeek fast condition with thinking disabled. |

List the configured conditions with:

```bash
uv run sgchem list-model-matrix configs/model_matrix.toml
```

## Request Export

Use request export to inspect prompts before live provider runs:

```bash
uv run sgchem export-llm-requests data/cards/cara_lo_all_cards.jsonl --systems bare_llm,llm_tools --out runs/llm_requests.jsonl
uv run sgchem export-llm-requests data/cards/cara_lo_all_cards.jsonl --systems llm_tools --model-matrix configs/model_matrix.toml --out runs/llm_matrix_requests.jsonl
```

The export includes both the structured request and the exact chat messages sent
to the provider path.

## Matrix Runs

Use `run-llm-matrix` to run the same LLM system condition across multiple
provider/model conditions:

```bash
uv run sgchem run-llm-matrix data/cards/cara_lo_all_cards.jsonl \
  --systems llm_tools,llm_tools_validator \
  --model-conditions openai_frontier,openai_fast,anthropic_frontier,anthropic_fast,deepseek_frontier,deepseek_fast \
  --out runs/cara_lo_llm_matrix
```

Use `--workers N` for bounded card-level concurrency during live matrix runs.
This changes execution throughput only; it does not alter prompts, cache keys,
model conditions, or scoring.

Without `--allow-external`, missing replay cache entries produce explicit empty
offline outputs and validator systems repair them where applicable. Live calls
require:

```bash
uv run sgchem run-llm-matrix data/cards/cara_lo_all_cards.jsonl \
  --systems llm_tools,llm_tools_validator \
  --model-conditions openai_fast \
  --out runs/cara_lo_llm_pilot \
  --allow-external
```

Provider keys are read from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and
`DEEPSEEK_API_KEY` unless overridden in the model matrix.

## Safety Boundary

Prompts instruct systems not to invent molecules or candidate IDs and not to make
synthesis, safety, selectivity, or clinical claims. These are prompt guardrails
only; scoring still relies on deterministic schema and constraint validation.
Candidate activity values in the frozen card are scorer-only and are not included
in exported LLM request candidate summaries.
