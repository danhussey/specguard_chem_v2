# Post-hoc LLM Repair

The release experiment calls each model once per card and representation:
`bare_llm` or `llm_tools`. A deterministic post-hoc transform can then evaluate
that same recorded response both unaided and behind the benchmark harness repair.
It does not issue another provider request.

```bash
uv run sgchem repair-llm-trace \
  data/releases/v0.1.0/system_input_cards.jsonl \
  release/v0.1.0/experiments/llm/matrix/<condition>/bare_llm/trace.jsonl \
  --out release/v0.1.0/experiments/llm/matrix/<condition>/bare_llm/posthoc_repair.trace.jsonl \
  --scores-out release/v0.1.0/experiments/llm/matrix/<condition>/bare_llm/posthoc_scores \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

The transformed trace has a deliberately separate system name ending in
`__posthoc_repair`. Its fields have the following meanings:

- `raw_output` and `raw_issues` are exact copies of the source trace's recorded
  raw evidence;
- `output` and `issues` contain the deterministic repaired view;
- `repaired` says whether repair was actually applied on that card;
- `repair_mode`, `repair_policy`, `repair_source_system_name`, and
  `repair_source_trace_sha256` make the transformation attributable;
- `provider_calls_added` is always zero.

The transform accepts only unrepaired `bare_llm` and `llm_tools` records. It
refuses validator traces, already-repaired traces, in-place source overwrites,
or source `raw_issues` that disagree with current contract validation. Before
repair it reconstructs system inputs with scorer-only candidate outcomes
removed. The output contains no timestamp or local source path, so rerunning it
on the same bytes and software produces byte-identical JSONL.

Scoring the transformed trace yields the two views in one record: `raw_*`
metrics measure the model response, while the ordinary/final metrics measure
the same response plus deterministic harness repair. Final repaired metrics
must not be presented as raw model ability.
