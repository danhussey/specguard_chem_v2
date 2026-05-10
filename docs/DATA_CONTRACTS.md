# Data Contracts

## Decision Card

A decision card is the canonical task object. It contains public support
compounds, a candidate pool, hard constraints, a budget, and scorer-only
candidate activity values for offline evaluation.

Required fields:

- `task_id`: stable unique ID.
- `assay_context`: target and assay metadata when available.
- `support_set`: known compounds with measured activity.
- `candidate_pool`: candidate IDs, SMILES, descriptors, and scorer-only activity
  values. Non-oracle systems must not use candidate activity values as features.
- `budget_k`: number of candidate IDs to return.
- `hard_constraints`: typed machine-checkable constraints.
- `metadata`: source, transform config, and provenance.

## System Output

Systems return ranked candidate IDs. They must not invent new molecules.

```json
{
  "task_id": "CARA_LO_assay_0001",
  "system_name": "qsar_rf",
  "selections": [
    {"rank": 1, "candidate_id": "C001", "confidence": 0.74}
  ]
}
```

Malformed or incomplete output is normalized into explicit validation issues and
scored according to the metric policy.

## Provenance

Imported CARA artifacts must record source URL, local path, SHA256, import time,
and transform configuration. Frozen decision cards should be reproducible from
those provenance fields.

`import-cara` detects the official CARA layout when `Task/{split}.tsv` and
`Split/{split}_support/query.json` are present. In that case, support/query JSON
row indices are resolved against the task TSV and written as normalized records.
It also writes a layout summary next to the normalized JSONL. The summary records
table-like files, detected columns, role hints, and task-kind hints so later
chats can harden source-specific import logic without reopening large archives
blindly.
