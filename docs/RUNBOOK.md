# Runbook

This is the operational guide for SpecGuard-Chem v0.1.0. The canonical release
is a 91-card, `k=10` CARA `LO_All` benchmark with system inputs and scorer-only
outcomes stored separately.

> **Validity notice.** Do not use former `paper-50` cards, runs, tables, or
> figures. They were produced by an incorrect interpretation of CARA split
> indices and are invalid as scientific evidence. Historical logs remain for
> auditability only.

## Canonical Paths

| Path | Role |
| --- | --- |
| `data/raw/cara/` | Locally downloaded CARA source; ignored by Git. |
| `data/interim/` | Rebuild-only normalized records and inspection output. |
| `data/releases/v0.1.0/system_input_cards.jsonl` | Public, label-free input consumed by systems. |
| `data/releases/v0.1.0/scorer_outcomes.jsonl` | Hidden candidate outcomes used only for validation/scoring and oracle controls. |
| `data/releases/v0.1.0/system_input_cards.meta.json` | Build config, provenance, hashes, and ordered task IDs. |
| `data/releases/v0.1.0/system_input_cards.audit.json` | All 100 source-task inclusion/exclusion decisions. |
| `release/v0.1.0/experiments/baselines/` | Corrected deterministic traces, scores, and comparisons. |
| `release/v0.1.0/experiments/llm/` | Exact requests, pre-run cost estimate, and eventual provider matrix. |
| `paper/manuscript/` | Manuscript sources and derived paper assets. |

## Setup and Tests

```bash
uv venv --seed
uv sync --locked --extra dev --extra providers
uv run sgchem --help
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The `providers` extra is needed only for authorized live calls. Tests and all
deterministic workflows must work without network access.

## Fixture Smoke

```bash
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem list-systems
uv run sgchem run-suite \
  tests/fixtures/cards.jsonl \
  --systems random_valid,rules_only,similarity_to_best_active,qsar_rf \
  --out runs/fixture
```

Fixtures may use the legacy monolithic card form for compatibility testing.
Release-scale execution must use the split artifacts below.

## Rebuild the CARA Release

Download and inspect the upstream archive:

```bash
uv run sgchem download-cara --out data/raw/cara
uv run sgchem inspect-cara \
  data/raw/cara \
  --out data/interim/cara_layout.json
```

Verify the archive and member hashes against
`data/releases/v0.1.0/source_provenance.json` before importing.

```bash
uv run sgchem import-cara \
  data/raw/cara \
  --split-name LO_All \
  --out data/interim/cara_lo_all_records.jsonl

uv run sgchem build-cards \
  data/interim/cara_lo_all_records.jsonl \
  --out data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes-out data/releases/v0.1.0/scorer_outcomes.jsonl \
  --benchmark-version 0.1.0 \
  --data-version cara-lo-all/0.1.0 \
  --target-cards 100 \
  --budget-k 10 \
  --support-size 50 \
  --selection-policy first \
  --constraints configs/default_constraints.json
```

The importer resolves official split references as zero-based source-table
positions and requires every resolved `Task ID` to match its split key. The
builder deterministically orders records, considers all 100 official tasks, and
includes the 91 with at least ten feasible candidates. Never select tasks by
hidden candidate activity.

Validate the split pair:

```bash
uv run sgchem validate-cards \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

Validation checks schemas, provenance, task/candidate order, per-card input
hashes, and task semantics. The public input contains support activities but no
candidate outcomes. See `docs/CARA_LOCAL_AUDIT.md` for frozen counts and hashes.

## Deterministic Baselines

Run every corrected baseline over the same 91 inputs:

```bash
uv run sgchem run-suite \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl \
  --systems oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm \
  --out release/v0.1.0/experiments/baselines \
  --manifest-started-at 2026-07-16T11:12:43Z

uv run sgchem compare-runs \
  release/v0.1.0/experiments/baselines/*/scores/summary.json \
  --out release/v0.1.0/experiments/baselines/comparison
```

`run-suite` passes only the allowlisted public view to non-oracle systems.
Scoring then hydrates hash-matched candidate outcomes. Oracle results are upper
bounds and must remain separate from deployable-system comparisons.

The trace is the primary decision record. Aggregate tables must be regenerated
from traces, not hand-edited. Card-level aggregation prevents a large assay or
candidate pool from dominating the headline.

## Export and Review the LLM Requests

The primary LLM experiment has two raw representations and three model
conditions, giving `91 × 2 × 3 = 546` exact requests.

```bash
uv run sgchem export-llm-requests \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --out release/v0.1.0/experiments/llm/exact_requests.jsonl
```

Request export is offline. Before live calls, verify:

- exactly 546 rows and six 91-card conditions;
- candidate activity values and local paths are absent;
- benchmark/data version and per-card input hashes are present;
- exact prompts, model settings, and output budgets match the frozen configs;
- every prompt fits the provider context limit.

## Estimate Cost

```bash
uv run sgchem estimate-llm-cost \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --model-conditions openai_gpt_5_5_2026_04_23_selector,anthropic_opus_4_8_selector,deepseek_v4_pro_2026_07_16_selector \
  --pricing configs/provider_pricing.toml \
  --cache-dir release/v0.1.0/experiments/llm/matrix/cache \
  --out-run-dir release/v0.1.0/experiments/llm/matrix \
  --out release/v0.1.0/experiments/llm/pre_run_cost_estimate.json
```

The frozen estimate is 546 missing calls, a 158,274-token maximum conservative
input estimate, and USD 106.0594 upper-bound incremental cost. Re-check pricing,
model availability, and limits immediately before any authorized call. See
`docs/COST_CONTROL.md`.

## Fixed One-Card Pilot

Before a full run, use `--task-id CARA_LO_CHEMBL1006579_IC50_0001` to select
the first frozen task explicitly. Across two interfaces and three model
conditions this produces exactly six requests. The current no-call estimate is
USD 0.936717455, with a maximum 25,817 conservatively estimated input tokens
for one request. The offline export and estimate commands are recorded in
`release/v0.1.0/REPRODUCE.md`.

The following command is the fixed pilot shape, not authorization to execute
it:

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

The pilot uses the full matrix's cache so those six responses are replayed,
not repurchased. After reviewing all six pilot traces, rerun
`estimate-llm-cost` for the complete cards with
`--cache-dir release/v0.1.0/experiments/llm/matrix/cache` and
`--out-run-dir release/v0.1.0/experiments/llm/matrix`. Continue only if the
fresh estimate reports six cached requests and 540 missing requests. At the
unchanged pricing snapshot the residual upper-bound estimate is USD
105.122676615. Abort if any pilot request is not cached.

## Live LLM Execution

No external call is authorized merely by this runbook. After explicit approval,
run the fixed pilot above and review its six traces before using the full-run
command shape:

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

Complete runs have six raw traces, each with exactly 91 records. Cache and
resume are enabled by default. The pilot's USD 1 gate and this residual USD 119
gate preserve the USD 120 aggregate ceiling. Do not use `--force` without
recording why. Provider errors remain execution failures; they are not model
scores.

## Post-hoc Repair

Do not call validator prompt variants in the primary matrix. Derive the guarded
view from each existing raw trace:

```bash
uv run sgchem repair-llm-trace \
  data/releases/v0.1.0/system_input_cards.jsonl \
  release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/trace.jsonl \
  --out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_repair.trace.jsonl \
  --scores-out release/v0.1.0/experiments/llm/matrix/CONDITION_ID/INTERFACE_NAME/posthoc_scores \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

This adds zero provider calls and creates a separate system name ending in
`__posthoc_repair`. Preserve both views:

- raw metrics measure the recorded model response;
- repaired metrics measure model plus deterministic harness;
- `repaired_rate` and `repaired_from_empty_rate` disclose repair dependence.

See `docs/POSTHOC_REPAIR.md` for the transform contract.

## Interpreting and Reporting Results

- Treat v0.1.0 cards, constraints, and exact requests as frozen inputs.
- Compare systems on paired cards and report uncertainty.
- Report utility, whole-action validity, and valid-selection fraction separately.
- Use QSAR, similarity, rules, and random-valid as fixed comparators.
- Keep oracle controls out of deployable leaderboards.
- Do not equate schema validity with biological utility.
- Do not present repaired rankings as unaided model performance.
- Report missing/failed provider calls and the denominator for every metric.
- Limit claims to bounded compound selection; this is not autonomous-lab
  validation.

## Recovery Checks

If an artifact or result looks wrong, stop and check in this order:

```bash
uv run sgchem validate-cards \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl

uv run sgchem score-run \
  data/releases/v0.1.0/system_input_cards.jsonl \
  release/v0.1.0/experiments/baselines/qsar_svm/trace.jsonl \
  --out /tmp/specguard-chem-rescore \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

Then compare artifact hashes with the release manifest and inspect per-card
issues before rerunning any system. A card-construction change requires a new
version, not an in-place repair of v0.1.0.
