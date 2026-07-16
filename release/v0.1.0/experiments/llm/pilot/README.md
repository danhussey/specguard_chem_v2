# Fixed one-card LLM pilot

## Scope and claim boundary

This pilot exercises the frozen v0.1.0 provider path on exactly one task:
`CARA_LO_CHEMBL1006579_IC50_0001`. The card contains 50 observed support
compounds, 119 candidate compounds, 73 candidates feasible under the declared
constraints, and a budget of `k = 10` selections.

The pilot crosses two interfaces (`bare_llm` and the descriptor-enriched
`llm_tools` interface) with three provider conditions, for six requests. It is
an execution, provenance, scoring, and repair-attribution check. Because it
covers one assay task, it must not be used to rank models, infer a general
representation effect, report inferential confidence intervals, or supply a
conference-paper headline result.

## Execution audit

- Six of six requests completed and produced one trace row and one shared-cache
  record each.
- Every row records exactly one provider attempt; SDK retries were disabled.
- Configured and provider-returned model identifiers agree in all six records.
- Response IDs, finish reasons, positive latency, complete usage, verbatim raw
  text, and structured provider content are retained.
- All responses contain one parseable JSON object with ten unique selections
  ranked 1--10. No response-contract parse issue was observed.
- Usage, latency, and pricing-derived cost coverage are 100%.
- Total recorded usage is 106,128 input tokens and 3,024 output tokens
  (109,152 total), including 1,024 OpenAI reasoning tokens.
- Actual aggregate cost is USD 0.449700535, below the USD 0.936717455 pilot
  upper-bound gate.
- A cache-only replay required zero provider calls and reproduced every score
  artifact byte-for-byte. Replay traces add only the expected `cache_path`
  provenance field.

## One-card observations

These values describe this card only. `Valid selections` is shown explicitly
because activity means over one or two surviving molecules can otherwise look
misleadingly strong.

| Provider / interface | Raw action valid | Valid selections | Raw feasible utility | Raw NDCG@10 | Guarded utility | Cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenAI / basic | 1 | 10/10 | 74.690 | 0.9278 | 74.690 | 0.092765000 |
| OpenAI / descriptor-enriched | 1 | 10/10 | 74.170 | 0.9459 | 74.170 | 0.113405000 |
| Anthropic / basic | 1 | 10/10 | 72.040 | 0.9044 | 72.040 | 0.102110000 |
| Anthropic / descriptor-enriched | 1 | 10/10 | 72.415 | 0.9319 | 72.415 | 0.126865000 |
| DeepSeek / basic | 0 | 2/10 | 15.200 | 0.1246 | 65.350 | 0.006379275 |
| DeepSeek / descriptor-enriched | 0 | 1/10 | 7.960 | 0.1396 | 64.930 | 0.008176260 |

OpenAI and Anthropic returned executable actions on this card. DeepSeek returned
syntactically correct JSON but selected eight candidates above the cLogP limit
in the basic interface and nine support compounds in the descriptor-enriched
interface. This is a clean example of why JSON/schema success, whole-action
validity, valid-selection fraction, and scientific utility are distinct
measurements.

Deterministic post-hoc repair added no provider calls. It was a no-op for the
four already valid actions. For DeepSeek it retained only 2/10 and 1/10 raw
selections, then filled the remaining positions with the declared rules-only
fallback. The resulting utility increases therefore characterize a
model-plus-harness system, not recovered unaided model ability.

For task-matched context, deterministic utilities on the same card are 64.125
for rules-only, 64.975 for random-valid, 74.790 for similarity to the best
support compound, 73.380--74.970 across the three QSAR models, and 78.570 for
the hidden-outcome oracle. The OpenAI responses are therefore close to the
similarity/QSAR comparators on this single task, while the Anthropic responses
are above random-valid but below those comparators. These are case-study
observations, not general comparative claims.

There is no consistent one-card descriptor effect: utility changes by -0.520
for OpenAI, +0.375 for Anthropic, and becomes less compliant for DeepSeek. The
`llm_tools` label denotes a descriptor-enriched prompt, not interactive tool
use, and it also increases prompt length. The full paired 91-card experiment is
required to estimate any representation effect.

## Residual run boundary

The pilot and full matrix share
`release/v0.1.0/experiments/llm/matrix/cache/`. The saved post-pilot estimate
reports six cached requests, 540 missing requests, USD 0.449700535 of actual
cached pilot cost, and a USD 105.122676615 conservative residual upper bound.
The residual run requires separate explicit authorization; this pilot does not
authorize it.

The raw traces and `scores/` directories remain primary evidence. Each
condition/interface directory also contains `posthoc_repair.trace.jsonl` and
`posthoc_scores/` for the separately attributed deterministic guarded view.
