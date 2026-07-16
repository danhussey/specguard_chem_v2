# Reproducing the v0.1.0 release candidate

> **Pre-release guide.** These commands reproduce the current corrected offline
> path. No `v0.1.0` tag exists yet, and the paper-facing live LLM run is pending.
> The final tagged guide will pin the release commit and verify the completed
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

Generate the tracked paper values and deterministic baseline table directly
from the canonical release comparison and per-system summary artifacts:

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

## 6. Reproduce the no-call LLM request export

The following command serializes the proposed requests but does not contact a
provider:

```bash
uv run sgchem export-llm-requests \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --out runs/reproduce-v0.1.0-exact-requests.jsonl
```

Recompute the conservative pre-run estimate without making a live call:

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out-run-dir release/v0.1.0/experiments/llm/matrix \
  --out runs/reproduce-v0.1.0-cost-estimate.json
```

Provider pricing is a dated snapshot in `configs/provider_pricing.toml` and must
be rechecked before external execution.

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

It completed six of six requests with one provider attempt per request and an
actual recorded cost of USD 0.449700535. Raw responses, structured provider
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

The pilot and full run deliberately share the matrix cache. Recompute the
residual estimate against that cache:

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --pricing configs/provider_pricing.toml \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out-run-dir release/v0.1.0/experiments/llm/matrix \
  --out runs/reproduce-v0.1.0-post-pilot-cost-estimate.json
```

The committed `experiments/llm/post_pilot_cost_estimate.json` reports six cached
requests, exactly 540 missing requests, a USD 105.122676615 conservative
incremental upper bound, and USD 0.449700535 of actual cached pilot cost. A
fresh estimate must agree before any residual execution. Do not add the six
cached calls to the residual call budget again.

## 8. Live-run boundary

Do not infer authorization from this guide. Live calls require all of the
following:

- explicit user approval and `--allow-external`;
- a saved estimate based on current provider pricing;
- `--require-cost-estimate` plus hard maximum cost, call-count, and per-call
  token gates; and
- cacheable responses and complete model/provider metadata.

The post-pilot check above has passed, but it does not authorize external calls.
Only after separate explicit approval is the residual full-matrix command valid:

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

The pilot's USD 1 gate plus the residual USD 119 gate preserve the USD 120
aggregate ceiling. If any pilot cache entry is absent, the 540-call gate must
abort before a provider call; investigate rather than raising the gate.

At present, six pilot calls are preserved and 540 residual calls are pending.
The one-card traces are operational evidence only; no complete 91-card
paper-facing provider trace or cross-model result exists.

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
