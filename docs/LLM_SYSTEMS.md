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
fixture files named `{system_name}__{task_id}.json`.

## Request Export

Use request export to inspect prompts before live provider runs:

```bash
uv run sgchem export-llm-requests data/cards/cara_lo_all_cards.jsonl --systems bare_llm,llm_tools --out runs/llm_requests.jsonl
```

The export includes both the structured request and the exact chat messages sent
to the provider path.

## Safety Boundary

Prompts instruct systems not to invent molecules or candidate IDs and not to make
synthesis, safety, selectivity, or clinical claims. These are prompt guardrails
only; scoring still relies on deterministic schema and constraint validation.
