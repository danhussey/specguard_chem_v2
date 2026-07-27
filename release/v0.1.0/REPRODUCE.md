# Reproducing the v0.1.0 release candidate

> **Pre-release guide.** These commands reproduce the current corrected offline
> path. No `v0.1.0` tag exists yet. The paper-facing LLM matrix is complete and
> replayable from committed response records without provider access. The final
> tagged guide will pin the release commit and verify the completed release
> manifest and checksums.

Run commands from the repository root. The project requires Python 3.11 or
newer, `uv`, and the committed `uv.lock`.

## 1. Create the locked environment

```bash
uv sync --locked --extra dev
uv lock --check
```

Provider SDKs and credentials are not required for the offline path.

## 2. Verify the software

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
```

## 3. Validate the frozen split artifacts

```bash
uv run sgchem validate-cards \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

This command validates both row contracts and the semantic pairing rules: task
sets, release provenance, candidate IDs and order, and the canonical public-card
hash stored in each scorer row. It also rejects candidate outcomes in the
system-facing artifact.

The JSON Schemas used to describe individual JSONL rows are:

- `data/releases/v0.1.0/schemas/system_input_card.schema.json`; and
- `data/releases/v0.1.0/schemas/scorer_outcomes.schema.json`.

JSON Schema alone cannot express cross-file hash binding or uniqueness by one
object property, so executable validation remains authoritative for those
invariants.

## 4. Reproduce corrected deterministic baselines

Write reproduction outputs to a new directory so the candidate bundle remains
untouched:

```bash
uv run sgchem run-suite \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm \
  --seed 7 \
  --out runs/reproduce-v0.1.0-baselines \
  --manifest-started-at 2026-07-16T11:12:43Z

uv run sgchem compare-runs \
  runs/reproduce-v0.1.0-baselines/*/scores/summary.json \
  --out runs/reproduce-v0.1.0-baselines/comparison
```

The committed candidate traces and scores are under
`release/v0.1.0/experiments/baselines/`, including its generated `comparison/`
tables. The final release will verify expected file hashes from a clean
checkout.

## 5. Regenerate and compile the manuscript

Rebuild the corrected report figures before regenerating the report. The
`--review-series` gate requires the split, hash-bound release artifacts and
emits the full numbered Figure 1–8 package as 300-dpi PNG, PDF, and searchable
SVG, in addition to the paired and card-level diagnostic figures:

```bash
uv run sgchem make-figures \
  release/v0.1.0/experiments/llm/comparison/system_comparison.csv \
  --out paper/figures/v0.1.0 \
  --review-series \
  --cards data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl

uv run sgchem make-report \
  release/v0.1.0/experiments/llm/comparison/system_comparison.csv \
  --out paper

uv run sgchem make-dashboard \
  release/v0.1.0/experiments/llm/comparison/system_comparison.csv \
  --out paper
```

The numbered stems are
`figure_1_decision_card_anatomy`,
`figure_2_benchmark_pipeline`,
`figure_3_main_system_comparison`,
`figure_4_ndcg_system_comparison`,
`figure_5_raw_vs_final_llm`,
`figure_6_raw_vs_final_action_validity`,
`figure_7_leaderboard_summary`, and
`figure_8_failure_taxonomy`. Figure 6 intentionally reports strict
whole-action validity rather than the legacy valid-selection fraction.

Generate the tracked manuscript values and deterministic baseline table
directly from the canonical release comparison and per-system summary
artifacts:

```bash
python3 paper/manuscript/generate_results.py
python3 paper/manuscript/generate_results.py --check
```

The second command is a no-write release check and fails if either generated
file is stale. With [Tectonic](https://tectonic-typesetting.github.io/) installed,
compile the manuscript and supplement using ordinary public commands:

```bash
cd paper/manuscript
tectonic -X compile --outdir build main.tex
tectonic -X compile --outdir build supplement.tex
```

A TeX Live installation may instead use `latexmk -pdf -outdir=build main.tex`
and the corresponding command for `supplement.tex`.

## 6. Reproduce and verify the no-call LLM request export

The following command serializes the frozen requests but does not contact a
provider:

```bash
uv run sgchem export-llm-requests \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --out runs/reproduce-v0.1.0-exact-requests.jsonl
```

The output must match the committed request stream exactly:

```bash
cmp \
  release/v0.1.0/experiments/llm/exact_requests.jsonl \
  runs/reproduce-v0.1.0-exact-requests.jsonl
```

Estimate the current state against the completed shared cache without making a
live call:

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out-run-dir runs/reproduce-v0.1.0-llm-matrix \
  --out runs/reproduce-v0.1.0-cost-estimate.json
```

The current estimate must report 546 cached or completed requests, zero missing
live calls, and zero incremental cost. The committed
`experiments/llm/pre_run_cost_estimate.json` is deliberately historical: before
any live call it reported 546 missing requests, a USD 106.059394070
conservative upper bound, and a maximum estimated request size of 158,274 input
tokens. Provider pricing is the dated snapshot in
`configs/provider_pricing.toml`; no pricing refresh is needed for cache-only
replay.

## 7. Verify and replay the fixed one-card pilot

The pilot is the first frozen task by release order, selected by its exact ID
rather than by a mutable row limit:
`CARA_LO_CHEMBL1006579_IC50_0001`. Export its two interfaces across all three
model conditions without contacting a provider:

```bash
uv run sgchem export-llm-requests \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --task-id CARA_LO_CHEMBL1006579_IC50_0001 \
  --out runs/reproduce-v0.1.0-pilot-requests.jsonl
```

The committed `pilot/cost_estimate.json` records the state immediately before
execution. To reproduce that historical six-missing-call estimate, point the
estimator at fresh empty reproduction directories:

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --pricing configs/provider_pricing.toml \
  --task-id CARA_LO_CHEMBL1006579_IC50_0001 \
  --cache-dir runs/reproduce-v0.1.0-empty-pilot-cache \
  --out-run-dir runs/reproduce-v0.1.0-empty-pilot-run \
  --out runs/reproduce-v0.1.0-pilot-cost-estimate.json
```

At the frozen pricing snapshot this is exactly six missing requests, at most
25,817 conservatively estimated input tokens for any request, and USD
0.936717455 upper-bound incremental cost.

The pilot was explicitly authorized and executed once with the following hard
gates. This is an execution record, not authorization to repurchase responses:

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

It completed six of six requests with one provider attempt per request and a
usage-derived cost of USD 0.449700535. Raw responses, structured provider
content, response/model identifiers, usage, latency, and scores are under
`experiments/llm/pilot/`; the six content-addressed response records are under
`experiments/llm/matrix/cache/`.

Replay those responses without credentials or provider access by omitting
`--allow-external` and writing to a new output directory:

```bash
uv run --extra providers sgchem run-llm-matrix \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --task-id CARA_LO_CHEMBL1006579_IC50_0001 \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out runs/reproduce-v0.1.0-pilot-replay \
  --require-cost-estimate \
  --max-estimated-cost-usd 1 \
  --max-live-calls 6 \
  --max-input-tokens-per-call 30000
```

The replay must require zero live calls and reproduce all six score directories.
The committed pilot passed this check; trace differences are limited to the
expected replay `cache_path` field, while score artifacts are byte-identical.

The pilot and full run deliberately share the matrix cache. The committed
`experiments/llm/post_pilot_cost_estimate.json` captures the historical state at
the pilot checkpoint: six cached requests, exactly 540 missing requests, a USD
105.122676615 conservative incremental upper bound, and USD 0.449700535 of
usage-derived cached pilot cost. The shared cache is now complete, so a current
estimate correctly reports 546 cached requests and zero missing rather than
reproducing that earlier state.

## 8. Replay and verify the completed full LLM matrix

The live matrix is complete. Reproduction must use the committed cache without
`--allow-external` and with zero-cost and zero-call gates:

```bash
uv run --extra providers sgchem run-llm-matrix \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out runs/reproduce-v0.1.0-llm-matrix \
  --require-cost-estimate \
  --max-estimated-cost-usd 0 \
  --max-live-calls 0 \
  --max-input-tokens-per-call 175000
```

The preflight must find 546 cached requests, zero missing requests, and zero
incremental cost. It then writes six raw traces and six separately attributed
post-hoc repair traces, each containing 91 rows. The following checks should
print `546`, followed by six raw counts of `91` and six repaired counts of
`91`:

```bash
find release/v0.1.0/experiments/llm/matrix/cache \
  -type f -name '*.json' | wc -l
wc -l runs/reproduce-v0.1.0-llm-matrix/*/*/trace.jsonl
wc -l runs/reproduce-v0.1.0-llm-matrix/*/*/posthoc_repair.trace.jsonl
```

Regenerate the 19-system comparison from the seven deterministic/oracle
summaries, six raw LLM summaries, and six repaired summaries:

```bash
uv run sgchem compare-runs \
  release/v0.1.0/experiments/baselines/*/scores/summary.json \
  runs/reproduce-v0.1.0-llm-matrix/*/*/scores/summary.json \
  runs/reproduce-v0.1.0-llm-matrix/*/*/posthoc_scores/summary.json \
  --out runs/reproduce-v0.1.0-llm-comparison

diff -ru \
  release/v0.1.0/experiments/llm/comparison \
  runs/reproduce-v0.1.0-llm-comparison
```

The canonical comparison includes the primary leaderboard, oracle controls,
metric winners, raw/final ablations, paired task-level bootstrap deltas,
card-level diagnostics, and failure taxonomy. The canonical
`experiments/llm/matrix/manifest.json` enumerates the six raw runs; repaired
artifacts are stored beside each source trace and explicitly identify their
source trace hash and repair policy.

Across the six unique live conditions, provider-reported token usage multiplied
by the frozen token prices gives USD 58.95671601. Cost coverage is 100%. Do not
sum the raw and repaired rows as separate purchases: post-hoc repair made zero
provider calls and carries the source condition's cost for attribution.

For historical provenance, the residual execution was authorized with the
following hard outer gates. It is recorded here as an execution record, not as
an instruction to repurchase responses:

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

The pilot's USD 1 gate plus the residual USD 119 gate preserved the USD 120
aggregate ceiling. Execution resumed from the same content-addressed cache after
an external billing interruption, so no successful response was purchased
twice. The final usage-derived total remained below the outer gate. Any missing
or mismatched cache record is now a reproduction failure: investigate it rather
than adding `--allow-external` or raising a gate.

## 9. Rebuild and smoke-test package distributions

Build both distribution formats from the release candidate:

```bash
uv build --out-dir runs/reproduce-v0.1.0-dist
```

The candidate bundle contains:

- `specguard_chem_v2-0.1.0-py3-none-any.whl`, SHA256
  `33e348ebdbbcbc610fe22df9322c8bc4566c173a56cda5e815ea1f3d0329881d`;
  and
- `specguard_chem_v2-0.1.0.tar.gz`, SHA256
  `8d1c8580d3ae0a72b0ffe57f6480be28889e8689361f51e35ed46046e48ba2d8`.

Install the wheel in a fresh environment, then run at least `sgchem --help`,
`sgchem list-systems`, and fixture-card validation. The bundled wheel was
verified this way under Python 3.12; its installed metadata reports version
`0.1.0` and the action-level benchmark description.

## 10. Final-release verification gate

`MANIFEST.json` and `SHA256SUMS` must not be generated until the data, traces,
paper, supplement, figures, package distributions, and metadata are all final.
The tagged reproduction procedure will then:

1. verify every manifest path, byte size, role, and SHA256 digest;
2. install and test from a clean checkout at the release commit;
3. validate the split artifacts and replay every reported offline score;
4. compile the paper and compare generated tables and figures; and
5. create the annotated tag only after those checks pass.

Until that gate is complete, this directory is a candidate workspace rather
than an archival release.
