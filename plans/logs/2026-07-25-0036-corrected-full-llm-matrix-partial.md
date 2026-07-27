# 2026-07-25 Corrected Full LLM Matrix: Partial Execution

> Historical interruption checkpoint. The same cached execution later
> completed; see `2026-07-25-0037-corrected-full-llm-matrix-complete.md` for
> the final matrix, analysis, and validation.

## Objective

Execute the explicitly approved corrected v0.1.0 provider matrix after deciding
to defer chemical-diversity changes to a future benchmark version.

## Authorization and gates

The user explicitly approved the full corrected analysis after the residual
estimate and gates had been presented. The authorized boundary remained:

- at most 540 new provider calls after the six-call pilot;
- residual estimate no greater than USD 119;
- no missing request above 175,000 conservatively estimated input tokens; and
- pilot plus residual ceilings no greater than USD 120.

Immediately before execution, official provider documentation was rechecked.
The frozen model IDs, context limits, and pricing inputs remained available and
consistent with `configs/model_matrix.toml` and
`configs/provider_pricing.toml`.

The fresh full-matrix preflight reported:

- 546 total requests;
- 6 shared pilot cache hits;
- 540 missing live calls;
- maximum missing input estimate 158,274 tokens;
- residual upper-bound estimate USD 105.122676615; and
- cached pilot actual cost USD 0.449700535.

## Execution

The full command used the corrected 91-card artifact, separate scorer outcomes,
the two raw interfaces, the three frozen model conditions, the shared cache,
`--allow-external`, and the USD 119 / 540-call / 175,000-token hard gates.
`--force` was not used and the default single worker was retained.

Results by provider:

- OpenAI `bare_llm`: complete, 91/91.
- OpenAI `llm_tools`: complete, 91/91.
- Anthropic `bare_llm`: 20/91 cached, including the pilot response. The next
  request returned HTTP 400 with an insufficient-credit error. SDK retries were
  disabled, the run stopped, and no incomplete trace was written.
- Anthropic `llm_tools`: 1/91 cached pilot response; not started in this run.
- DeepSeek `bare_llm`: complete, 91/91.
- DeepSeek `llm_tools`: complete, 91/91.

After the Anthropic stop, the already-authorized DeepSeek slice was resumed
separately with tighter gates: 180 missing calls, USD 4, and 175,000 input
tokens per call. Its fresh upper-bound estimate was USD 3.306621615. Both
DeepSeek conditions completed without retries or provider errors.

## Verification

The matrix currently contains 385/546 cached responses and four complete raw
traces. For each complete condition:

- the raw trace and card-score file contain the exact ordered 91-task set;
- the deterministic repaired trace and repaired score file contain the same
  exact 91-task set;
- every raw response records one provider attempt;
- configured and returned model IDs, response ID, finish reason, usage,
  latency, request hash, and retained raw response content are present;
- usage, latency, and cost coverage are 100%; and
- no record is marked as an externally skipped call.

The integrity audit found zero failures across 364 raw records and 364 repaired
records.

## Interim results

These are incomplete-provider diagnostics and are not the final paper
comparison:

| Condition | View | Feasible utility | NDCG@k | Action validity |
| --- | --- | ---: | ---: | ---: |
| OpenAI bare | raw | 72.9664 | 0.9158 | 0.7912 |
| OpenAI bare | repaired | 73.9637 | 0.9288 | 1.0000 |
| OpenAI tools | raw | 72.8047 | 0.9163 | 0.7473 |
| OpenAI tools | repaired | 73.8886 | 0.9273 | 1.0000 |
| DeepSeek bare | raw | 29.0302 | 0.3462 | 0.0879 |
| DeepSeek bare | repaired | 67.5645 | 0.8431 | 1.0000 |
| DeepSeek tools | raw | 43.0504 | 0.5304 | 0.2418 |
| DeepSeek tools | repaired | 69.1109 | 0.8651 | 1.0000 |

Recorded actual cost for the four complete traces is USD 28.39491601.
Usage-derived cost for the 21 Anthropic cache-only responses is USD 3.35084,
for USD 31.74575601 recorded spend so far.

## Remaining work

The fresh full-matrix estimate after DeepSeek completion reports:

- 385 cached or completed requests;
- 161 missing live calls, all Anthropic;
- maximum missing input estimate 158,265 tokens; and
- USD 44.010805 conservative remaining cost.

The current recorded spend plus that upper bound is USD 75.75656101, below the
authorized USD 120 aggregate ceiling. Completion requires Anthropic account
credits to be added outside this repository. After that external state changes,
resume the two Anthropic conditions against the same shared cache with no
`--force`, then:

1. build the two remaining repaired views;
2. rerun the full six-condition command cache-only to write one canonical
   complete manifest;
3. verify six raw and six repaired 91-row traces and complete operational
   provenance;
4. generate the 19-system paired comparison, uncertainty, figures, dashboard,
   and manuscript results; and
5. run the full release validation and record final costs.

No provider substitution, diversity redesign, release tag, push, or publication
action occurred.
