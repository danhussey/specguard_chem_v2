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
Generation settings such as token budget, temperature, reasoning effort,
thinking mode, thinking budget, prompt profile, and request timeout are included
in new request hashes so interface or budget changes do not replay stale
provider responses.

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
| `openai_frontier_selector` | OpenAI | `gpt-5.5` | Direct-selector frontier condition with `json_first` prompting. |
| `anthropic_frontier_selector` | Anthropic | `claude-opus-4-7` | Direct-selector frontier condition without extended thinking. |
| `deepseek_frontier_selector` | DeepSeek | `deepseek-v4-pro` | Direct-selector frontier condition with thinking disabled. |
| `openai_frontier_reasoning_budget` | OpenAI | `gpt-5.5` | Pilot-only reasoning-budget condition. |
| `anthropic_frontier_thinking_8k` | Anthropic | `claude-opus-4-7` | Pilot-only extended-thinking condition with explicit budget. |
| `deepseek_frontier_thinking_32k` | DeepSeek | `deepseek-v4-pro` | Pilot-only thinking condition with long budget and timeout. |

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

Use the selector conditions for the fair cross-provider frontier comparison:

```bash
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl \
  --systems bare_llm,llm_validator,llm_tools,llm_tools_validator \
  --model-conditions openai_frontier_selector,anthropic_frontier_selector,deepseek_frontier_selector \
  --out runs/cara_lo_paper_50_selector_matrix \
  --allow-external
```

Reasoning-budget conditions are exploratory. Run them on a small fixed subset
first and promote only if raw outputs reliably contain final JSON rather than
being mostly repaired from empty responses.

## Raw Versus Repaired Outputs

New traces store `raw_output` and `raw_issues` before validator repair. The
existing `output` and `issues` fields remain the final scored artifact after
repair. Reports include raw and final metrics so a validator fallback can raise
final utility without being mistaken for raw LLM decision quality.

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
