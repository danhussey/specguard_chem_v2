# 2026-07-25 0035 Corrected Analysis Reproduction

## Outcome

The CARA task-indexing defect and its corrected recovery were independently
verified from the original local CARA v1.0.1 archive. The corrected normalized
records and all four frozen split-artifact files reproduced byte-for-byte. The
91-card deterministic analysis reproduced the same selections and headline
metrics, and the six corrected pilot responses replayed from cache without an
external call.

The full corrected LLM comparison is still incomplete. Six pilot requests are
cached and 540 live requests remain separately unauthorized.

## Root cause confirmed

- CARA support/query integers are zero-based positions in `Task/LO_All.tsv`.
- The invalid importer resolved them as labels from the exported `Unnamed: 0`
  column and silently skipped missing labels.
- The corrected importer uses positional lookup, rejects out-of-range
  references, and requires every resolved source `Task ID` to match the split
  task key.
- The historical paper-50 artifacts remain invalid under
  `INVALID_RESULTS_NOTICE.md`.

## Commands run

```bash
uv sync --locked --extra dev
uv lock --check
uv run ruff check --no-cache src tests
uv run ruff format --check --no-cache src tests
uv run pytest -p no:cacheprovider
uv run sgchem validate-cards \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl

uv run sgchem import-cara data/raw/cara \
  --split-name LO_All \
  --out runs/reproduce-v0.1.0-data/cara_lo_all_records.jsonl

uv run sgchem build-cards \
  runs/reproduce-v0.1.0-data/cara_lo_all_records.jsonl \
  --out runs/reproduce-v0.1.0-data/system_input_cards.jsonl \
  --scorer-outcomes-out runs/reproduce-v0.1.0-data/scorer_outcomes.jsonl \
  --benchmark-version 0.1.0 \
  --data-version cara-lo-all/0.1.0 \
  --target-cards 100 \
  --budget-k 10 \
  --support-size 50 \
  --selection-policy first \
  --constraints configs/default_constraints.json

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

The cache-only replay omitted `--allow-external`.

## Verification

- Source archive and the three relevant CARA members matched the frozen source
  SHA256 values.
- Import: 24,588 records across 100 tasks; normalized-record SHA256
  `cec651b6e97f044bf82820c465b441763cafa18a34b12361a33e79ab30faf438`.
- Rebuilt artifacts were byte-identical to the frozen release:
  - system inputs:
    `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e`;
  - scorer outcomes:
    `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4`;
  - metadata:
    `d986ba96589032c59dac2dcc24cadf9aa3325616fa2a395cec682ece7220af54`;
  - inclusion audit:
    `abb80ad110ef71d69a2cea2f09cc456399a81d431bc9e365320ab8b27064812c`.
- Fresh semantic validation passed for all 91 cards.
- Every deterministic trace contained the exact 91-task set. Decisions, raw
  outputs, issues, and repair state matched the committed corrected run for all
  seven systems. Per-card score structures matched, with maximum floating-point
  drift `3.55e-14`.
- The fresh traces include null operational-provenance fields added after the
  original baseline freeze, so whole trace files are not byte-identical. This
  is schema evolution, not decision or metric drift.
- Corrected deterministic means remain oracle `79.5626`, QSAR SVM `74.9664`,
  QSAR RF `74.9580`, similarity `73.2882`, random-valid `68.4688`, and
  rules-only `66.9215`.
- The six pilot score artifacts replayed byte-for-byte. Replay traces matched
  after removing the expected cache-path field. The replay manifest records
  `allow_external: false`.
- Fresh residual estimate: 546 total requests, six cached, 540 missing,
  maximum conservative missing input `158274` tokens, and
  `$105.122676615` conservative incremental cost under the frozen pricing
  snapshot.
- Validation: 60 tests passed; lint, format, lock, card validation, and
  manuscript generated-result checks passed.

## Artifacts

Reproduction outputs are ignored worktree artifacts:

- `runs/reproduce-v0.1.0-data/`
- `runs/reproduce-v0.1.0-baselines/`
- `runs/reproduce-v0.1.0-pilot-replay/`
- `runs/reproduce-v0.1.0-post-pilot-cost-estimate.json`

## Boundary and follow-up

No provider call, response purchase, final paper comparison, tag, push, or
publication action occurred. Before any residual run, recheck provider pricing
and model availability, retain the prespecified USD 119 / 540-call / 175,000
input-token hard gates, and obtain explicit authorization.
