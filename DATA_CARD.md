# Data Card

## Primary Source

The intended primary substrate is CARA lead-optimisation few-shot data. CARA
organizes ChEMBL-derived compound activity data by assay and distinguishes
support/query samples in few-shot test scenarios.

## Local Artifacts

- `data/raw/`: downloaded archives and source provenance.
- `data/interim/`: normalized CARA-like records and layout summaries.
- `data/cards/`: frozen decision cards used by runs.

Raw and derived data artifacts are ignored by default except `.gitkeep` files.
Commit only small fixtures or deliberately frozen public samples.

## Normalized Record Fields

- `assay_id`
- `compound_id`
- `smiles`
- `activity_value`
- `role`
- `target`
- `task_kind`
- `source_file`
- `source_split`
- `row_index`

For official CARA imports, split JSON files map assay task IDs to row indices in
`Task/{split}.tsv`. The default split is `LO_All`, matching the project’s
lead-optimisation focus.

## Decision-Card Inclusion

Cards require enough support records and enough feasible candidate records to
satisfy `budget_k` after hard constraints.

## Provenance

Download provenance includes source URL, timestamp, archive path, SHA256, and
extraction path. Import provenance includes source files, layout summary path,
record counts, and assay counts.

The downloader validates the server `Content-Length` or `Content-Range` when
available and rejects invalid zip archives. A failed download may leave
`CARA.zip.part`; it is ignored by Git and can be resumed by rerunning
`download-cara`.

The first local CARA audit is recorded in `docs/CARA_LOCAL_AUDIT.md`.
