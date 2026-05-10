# Data Card

This data card explains what data SpecGuard-Chem v2 expects, how CARA-derived
files are transformed, and which fields are visible to systems versus reserved
for scoring.

## Short Glossary

| Term | Meaning in this project |
| --- | --- |
| CARA | Public compound-activity benchmark built from ChEMBL-derived assay data. It is the main substrate for v2 decision cards. |
| VS | Virtual screening. In CARA, VS tasks evaluate finding active compounds from a broader candidate set. VS is useful context but is not the first v2 focus. |
| LO | Lead optimisation. This is the letter `O`, not the number `0`. In CARA, LO tasks are closer to medicinal-chemistry follow-up around known active matter. |
| `LO_All` | CARA split name meaning the combined lead-optimisation task set used by the first v2 pipeline. |
| Support set | Compounds treated as already measured at the start of the decision card. Systems may use their activity values. |
| Query set / candidate pool | Compounds available for selection. Their activity values are hidden from systems and used only during scoring. |
| Decision card | Frozen benchmark instance: support compounds, candidate pool, scorer-only activity values, hard constraints, and budget `k`. |

## Primary Source

The intended primary substrate is CARA lead-optimisation few-shot data. CARA
organizes compound activity records by assay and provides support/query splits.
SpecGuard-Chem v2 reuses those splits but changes the evaluated action:

```text
CARA activity-prediction view:
  support compounds + query compounds -> predict/rank query activity

SpecGuard-Chem v2 decision view:
  support compounds + candidate pool + constraints + budget k -> choose top-k candidate IDs
```

The project starts with LO rather than VS because constrained top-k selection is
meant to resemble a small follow-up testing decision after some active compounds
are already known. VS can be added later as a separate stress or breadth module.

## Local Artifact Layers

| Layer | Path | What it stores | Should it be committed? |
| --- | --- | --- | --- |
| Raw source | `data/raw/` | Downloaded CARA archives, extracted source files, source metadata. | Usually no; keep large/public raw files out of Git. |
| Interim records | `data/interim/` | Normalized CARA-like JSONL records and layout summaries. | Usually no; regenerate from raw source. |
| Frozen cards | `data/cards/` | Decision-card JSONL/parquet artifacts used by experiments. | Usually no for full CARA; yes for tiny fixtures or explicitly frozen small samples. |
| Fixtures | `tests/fixtures/` | Small committed examples for tests and smoke runs. | Yes, when intentionally curated. |

Raw and derived data artifacts are ignored by default except `.gitkeep` files.
Commit only small fixtures or deliberately frozen public samples.

## Source To Card Flow

```text
download-cara
  -> data/raw/cara/

inspect-cara
  -> data/interim/cara_layout.json

import-cara
  -> data/interim/cara_records.jsonl

build-cards
  -> data/cards/cara_lo_cards.jsonl

run-system / run-suite
  -> runs/<experiment>/<system>/trace.jsonl

score-run
  -> runs/<experiment>/<system>/scores/
```

Each layer has a different job. Raw data preserves the source. Interim records
make CARA parsing auditable. Cards freeze the benchmark input. Run traces record
system behavior. Score outputs evaluate that behavior without changing the card.

## CARA Import Shape

For official CARA imports, split JSON files map assay task IDs to row indices in
task tables. The default split is `LO_All`, matching the project’s
lead-optimisation focus.

Representative source layout:

```text
Task/LO_All.tsv
Split/LO_All_support.json
Split/LO_All_query.json
```

The importer normalizes those files into one record per compound-assay row. A
representative interim record looks like:

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

## Normalized Record Fields

| Field | Meaning |
| --- | --- |
| `assay_id` | Assay/task identifier used to group records into decision cards. |
| `compound_id` | Stable compound identifier from the source row when available. |
| `smiles` | Molecular structure string used for descriptors and constraints. |
| `activity_value` | Measured activity value normalized for scoring, typically pIC50/pChEMBL-like when available. |
| `role` | `support` if visible to systems; `query` if hidden candidate activity. |
| `target` | Target/context metadata when provided by CARA. |
| `task_kind` | CARA task family, such as `LO` or `VS`. |
| `source_file` | Raw CARA table used to create the record. |
| `source_split` | CARA split name, for example `LO_All`. |
| `row_index` | Source table row index referenced by the split file. |

## Decision-Card Fields

A decision card is the unit consumed by systems and scorers:

```json
{
  "task_id": "CHEMBL_assay_001",
  "assay_context": {
    "target": "CHEMBL_target_001",
    "task_kind": "LO"
  },
  "support_set": [
    {"id": "S001", "smiles": "CCO...", "pIC50": 6.42}
  ],
  "candidate_pool": [
    {
      "id": "C001",
      "smiles": "CCN...",
      "activity_value": 7.11,
      "descriptors": {"mw": 318.4, "clogp": 2.7}
    }
  ],
  "budget_k": 10,
  "hard_constraints": [
    {"id": "mw_max_500", "type": "candidate", "check": "descriptor_max", "params": {"descriptor": "mw", "max": 500}}
  ]
}
```

Systems may see `support_set`, `candidate_pool`, `budget_k`, and
`hard_constraints`, but candidate `activity_value` is scorer-only information.
System adapters, LLM prompt builders, and exported LLM requests must redact or
ignore candidate activity values. They exist in the frozen card file so offline
scoring can be deterministic and self-contained.

## Decision-Card Inclusion

Cards require enough support records and enough feasible candidate records to
satisfy `budget_k` after hard constraints.

Typical exclusion reasons:

- Too few support compounds to train or summarize an early project state.
- Too few candidate/query compounds after descriptor parsing.
- Too few feasible candidates after hard constraints.
- Missing or unusable activity values for scoring.
- Invalid or duplicate molecular structures that cannot be resolved safely.

When inclusion thresholds change, record the transform config and make a new
card artifact. Do not silently overwrite a card set used for a reported run.

## Provenance

Download provenance includes source URL, timestamp, archive path, SHA256, and
extraction path. Import provenance includes source files, layout summary path,
record counts, and assay counts.

The downloader validates the server `Content-Length` or `Content-Range` when
available and rejects invalid zip archives. A failed download may leave
`CARA.zip.part`; it is ignored by Git and can be resumed by rerunning
`download-cara`.

The first local CARA audit is recorded in `docs/CARA_LOCAL_AUDIT.md`.

## Leakage Rules

- Do not include candidate `activity_value` in LLM prompts, exported LLM
  requests, or non-oracle system feature summaries.
- Do not train a system on query/candidate activity from the same card.
- Do not compare systems across different card artifacts without naming the
  card artifact and transform config.
- Do not treat CARA retrospective measurements as prospective validation.
