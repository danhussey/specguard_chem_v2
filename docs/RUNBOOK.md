# Runbook

This runbook explains the common project workflows and what each step produces.
It is meant to be operational: use it when starting a new chat, reproducing a run,
or checking whether a change preserved the decision-audit contract.

## Artifact Map

| Path | What it contains | Why it matters |
| --- | --- | --- |
| `tests/fixtures/` | Tiny CARA-like inputs, frozen cards, cached traces, and golden outputs. | Fast smoke tests without network or CARA downloads. |
| `data/raw/cara/` | Downloaded CARA archive and extracted source files. | Immutable source layer; keep provenance and checksums. |
| `data/interim/` | Normalized CARA records and layout inspection output. | Debuggable transform layer between CARA files and decision cards. |
| `data/cards/` | Frozen decision-card JSONL/parquet artifacts. | Main benchmark input consumed by systems and scorers. |
| `runs/` | Per-system traces, scores, exported LLM requests, and experiment outputs. | Reproducibility record for each execution. |
| `paper/` | Generated tables, figures, and report artifacts. | Manuscript-facing outputs; should be derived from runs, not hand-edited. |

## Setup

```bash
uv venv --seed
uv pip install -e ".[dev,providers]"
```

This creates the local Python environment and installs `specguard_chem_v2` in
editable mode. The `dev` extra provides test/report tooling; the `providers`
extra provides optional provider libraries used by live LLM integrations.

Use `uv run ...` for project commands so the CLI and tests run inside the same
environment.

```bash
uv run sgchem --help
uv run pytest
```

## Fixture Smoke

```bash
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem list-systems
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems all --out runs/fixture
uv run sgchem score-run tests/fixtures/cards.jsonl runs/fixture/qsar_rf/trace.jsonl --out runs/fixture/qsar_rf/scores
```

The fixture smoke is the fastest end-to-end check. It validates the committed
decision-card contract, lists registered systems, runs every implemented system
on tiny cards, and scores one trace explicitly.

The important output shape is:

```text
runs/fixture/
  random_valid/
    trace.jsonl
    scores/
      card_scores.jsonl
      summary.json
      failure_taxonomy.csv
  qsar_rf/
    trace.jsonl
    scores/
      summary.json
```

A run trace records the ranked candidate IDs a system selected, plus enough
metadata to replay or audit the decision:

```json
{
  "task_id": "fixture_assay_001",
  "system_name": "rules_only",
  "output": {
    "task_id": "fixture_assay_001",
    "system_name": "rules_only",
    "selections": [
      {"rank": 1, "candidate_id": "C003", "confidence": 0.74}
    ]
  },
  "issues": []
}
```

Scores are card-level first, then aggregated. This avoids a large assay or
candidate pool dominating the headline comparison.

## CARA Pipeline

```bash
uv run sgchem download-cara --out data/raw/cara
uv run sgchem inspect-cara data/raw/cara --out data/interim/cara_layout.json
uv run sgchem import-cara data/raw/cara --split-name LO_All --out data/interim/cara_records.jsonl
uv run sgchem build-cards data/interim/cara_records.jsonl --out data/cards/cara_lo_cards.jsonl --target-cards 50 --selection-policy first
uv run sgchem summarize-cards data/cards/cara_lo_cards.jsonl --out data/cards/cara_lo_cards.summary.json
```

The CARA pipeline turns public assay-level support/query data into frozen
finite-budget decision cards.

| Step | What it does | Output |
| --- | --- | --- |
| `download-cara` | Downloads the CARA archive, resumes partial downloads when possible, validates archive size, records provenance and checksums. | `data/raw/cara/CARA.zip`, extracted files, provenance metadata. |
| `inspect-cara` | Reads the raw directory and reports discovered tables/splits. | `data/interim/cara_layout.json`. |
| `import-cara` | Joins CARA task tables with support/query split files and normalizes compound rows. | `data/interim/cara_records.jsonl`. |
| `build-cards` | Groups normalized records by assay, computes descriptors/constraint flags, and emits decision cards. | `data/cards/cara_lo_cards.jsonl`. |
| `summarize-cards` | Counts cards, candidates, supports, constraint attrition, and activity coverage. | `data/cards/cara_lo_cards.summary.json`. |

The official CARA layout is treated as source data, not as a benchmark API. For
lead optimisation, the importer expects CARA-style task and split files such as:

```text
Task/LO_All.tsv
Split/LO_All_support.json
Split/LO_All_query.json
```

The normalized interim layer is intentionally simple. A representative record is:

```json
{
  "assay_id": "CHEMBL_assay_001",
  "compound_id": "CHEMBL123",
  "smiles": "CCOc1ccc...",
  "activity_value": 6.42,
  "role": "support",
  "target": "CHEMBL_target_001",
  "task_kind": "LO",
  "source_file": "Task/LO_All.tsv",
  "source_split": "LO_All",
  "row_index": 128
}
```

The card layer is the actual experiment input. Systems see support activity and
candidate descriptors, while hidden candidate activity is retained for scoring:

```json
{
  "task_id": "CHEMBL_assay_001",
  "support_set": [{"id": "S001", "smiles": "...", "pIC50": 6.42}],
  "candidate_pool": [{"id": "C001", "smiles": "...", "activity_value": 7.11, "descriptors": {}}],
  "budget_k": 10,
  "hard_constraints": [{"id": "mw_max_500", "type": "candidate", "check": "descriptor_max", "params": {"descriptor": "mw", "max": 500}}]
}
```

`download-cara` writes to `CARA.zip.part` first, resumes partial files with HTTP
range requests when possible, checks the server `Content-Length` or
`Content-Range`, rejects incomplete archives, and only then replaces `CARA.zip`.

## Full Experiment

```bash
uv run sgchem run-suite data/cards/cara_lo_cards.jsonl --systems all-with-oracle --out runs/cara_lo
uv run sgchem compare-runs runs/cara_lo/*/scores/summary.json --out paper/tables
uv run sgchem make-figures paper/tables/system_comparison.csv --out paper/figures
uv run sgchem make-report paper/tables/system_comparison.csv --out paper
```

`run-suite` executes each named system against the same frozen cards. Each system
gets its own directory under `runs/cara_lo/`, with a `trace.jsonl` and scored
outputs. This is the main reproducibility boundary: the trace says exactly what
was selected before any aggregate table was made.

`all-with-oracle` includes normal systems plus oracle controls. Oracle controls
are upper bounds and diagnostics, not primary systems for scientific claims.
Keep them separated when writing results.

`compare-runs` combines per-system summaries into manuscript tables:

```text
paper/tables/
  system_comparison.csv
  primary_leaderboard.csv
  oracle_controls.csv
  ablation_deltas.csv
  metric_winners.csv
```

The comparison tables separate utility from compliance. A useful row usually has
high feasible utility, low constrained regret, and low violation rate. A system
with perfect compliance but weak utility is evidence for the core project thesis,
not an implementation failure.

`make-figures` turns the comparison CSV into reproducible visuals, including the
compliance-utility frontier. `make-report` builds a generated report shell from
the same tables so paper artifacts remain traceable to run outputs.

## LLM Request Review

```bash
uv run sgchem export-llm-requests data/cards/cara_lo_cards.jsonl --systems bare_llm,llm_tools --out runs/llm_requests.jsonl
uv run sgchem export-llm-requests data/cards/cara_lo_cards.jsonl --systems llm_tools --model-matrix configs/model_matrix.toml --out runs/llm_matrix_requests.jsonl
```

This exports the exact prompts/messages that would be sent to LLM-backed systems
without making live calls. Use it before enabling external providers so prompt
size, candidate summaries, and hidden-field exclusion can be reviewed.

Default test and smoke paths must use cached or replayed LLM outputs. Live calls
require `--allow-external`, and the resulting responses must be written to cache
or trace artifacts so later runs can replay them without network access.

Example LLM review record:

```json
{
  "task_id": "CHEMBL_assay_001",
  "system_name": "llm_tools",
  "messages": [
    {"role": "system", "content": "Select valid candidate IDs only."},
    {"role": "user", "content": "Budget k=10 ..."}
  ],
  "cache_key": "sha256:..."
}
```

## Provider Matrix Pilot

```bash
uv run sgchem list-model-matrix configs/model_matrix.toml
uv run sgchem run-llm-matrix tests/fixtures/cards.jsonl --systems llm_tools_validator --model-conditions openai_fast,deepseek_fast --out runs/fixture_llm_matrix
```

The matrix runner executes the same LLM system condition across configured
provider/model conditions. Without `--allow-external`, it is a cache/replay
check: missing responses become explicit offline outputs, and validator systems
repair them with deterministic fallback rankings. This verifies directory shape,
trace labels, scoring, and comparison compatibility without spending provider
tokens.

Use a tiny live pilot before a full run:

```bash
uv run sgchem run-llm-matrix data/cards/cara_lo_cards.jsonl \
  --systems llm_tools,llm_tools_validator \
  --model-conditions openai_fast,anthropic_fast,deepseek_fast \
  --out runs/cara_lo_llm_pilot \
  --allow-external
```

Provider API keys are read from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and
`DEEPSEEK_API_KEY`. The run writes per-condition traces under:

```text
runs/cara_lo_llm_pilot/
  openai_fast/
    llm_tools/
      trace.jsonl
      scores/summary.json
  cache/
    openai_fast/
      llm_tools/
```

For the paper-50 frontier rerun, use the direct-selector conditions first. They
keep the full candidate pool and candidate JSON unchanged, but use a stricter
`json_first` output profile and avoid provider-specific hidden reasoning modes
where possible:

```bash
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl \
  --systems bare_llm,llm_validator,llm_tools,llm_tools_validator \
  --model-conditions openai_frontier_selector,anthropic_frontier_selector,deepseek_frontier_selector \
  --out runs/cara_lo_paper_50_selector_matrix \
  --allow-external
```

Reasoning-budget conditions should be treated as a separate pilot. Run them on
the first 10 frozen cards only, score raw versus final outputs, and continue to a
full 50-card reasoning run only if raw schema success is high and repairs are not
mostly from empty outputs.

## Interpreting Results

Use these rules when reading tables or writing the report:

- Treat decision cards as fixed inputs. If card construction changes, make a new
  run directory and record the transform config.
- Compare systems on paired cards first; aggregate averages are secondary.
- Report compliance and feasible utility separately.
- Do not describe oracle controls as deployable systems.
- Use oracle controls as upper bounds for regret/headroom checks, not as
  evidence that a real system can make those choices.
- Treat QSAR as the main non-language chemistry baseline: it trains on support
  compounds and predicts candidate activity from molecular fingerprints.
- Do not treat a valid output schema as medicinal-chemistry utility.
- For validator systems, report raw metrics alongside final repaired metrics.
  A repaired fallback can be useful operationally, but it is not raw LLM
  selection quality.
- Do not use live LLM outputs in default CI or fixture smoke tests.

## Common Recovery Checks

If a run looks wrong, check these in order:

```bash
uv run sgchem validate-cards data/cards/cara_lo_cards.jsonl
uv run sgchem summarize-cards data/cards/cara_lo_cards.jsonl --out data/cards/debug.summary.json
uv run sgchem score-run data/cards/cara_lo_cards.jsonl runs/cara_lo/<system>/trace.jsonl --out runs/cara_lo/<system>/rescore
```

`validate-cards` catches schema and contract errors. `summarize-cards` checks
whether the benchmark has enough feasible candidates after constraints.
`score-run` isolates scoring from system execution, which is useful when a trace
exists but aggregate metrics look suspicious.
