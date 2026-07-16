# Data Contracts

## Paired benchmark artifacts

The frozen benchmark deliberately separates the decision card visible to a
system from the retrospective outcomes used by the scorer. A release row is not
complete unless the two artifacts pass the executable pairing checks.

### System-input decision card

Required fields include:

- `schema_version` and `provenance`: contract and content identity;
- `task_id`: stable unique ID;
- `assay_context`: CARA target, endpoint, source, activity scale, and direction;
- `support_set`: known compounds with measured pChEMBL activity;
- `candidate_pool`: candidate IDs, SMILES, and permitted descriptors, with no
  candidate activity field;
- `budget_k`: number of candidate IDs to return;
- `hard_constraints`: typed machine-checkable constraints; and
- `output_schema` and `metadata`: action contract and construction metadata.

### Scorer outcomes

The paired scorer-only row contains `schema_version`, matching `provenance` and
`task_id`, the canonical `system_input_sha256`, and one hidden pChEMBL outcome
per candidate ID. It is public for reproducible retrospective evaluation but
must never be supplied during non-oracle selection.

Loading a pair verifies the same task set, shared provenance, candidate identity
and order, and the per-card canonical hash. The system-input JSON Schema also
forbids candidate activity fields. Legacy monolithic fixtures remain supported
for tests, but non-oracle execution receives only the strict public projection.

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

Imported CARA artifacts record source URL, source version and license, SHA256,
and transform configuration. Frozen decision cards must be reproducible from
those provenance fields. Deterministic release manifests omit wall-clock import
times so independent builds can be byte-identical.

`import-cara` detects the official CARA layout when `Task/{split}.tsv` and
`Split/{split}_support/query.json` are present. In that case, support/query JSON
row indices are resolved against the task TSV and written as normalized records.
It also writes a layout summary next to the normalized JSONL. The summary records
table-like files, detected columns, role hints, and task-kind hints so later
chats can harden source-specific import logic without reopening large archives
blindly.
