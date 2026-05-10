# 0002 CARA Ingestion Hardening

## Objective

Validate and harden the automated downloader/importer against official and
CARA-like dataset layouts, then preserve the observed layout in reproducible
metadata.

## Scope

- Download official CARA assets when network/runtime allows.
- Map support/query split files and flat tables into normalized records.
- Add source-layout tests.
- Record checksums, layout summaries, source files, and provenance.

## Non-Goals

- Do not expand to SIMPD, MoleculeACE, or raw ChEMBL in this plan.

## Affected Modules

- `specguard_chem_v2.data.cara`
- `specguard_chem_v2.cli`
- `docs/DATA_CONTRACTS.md`
- `docs/RUNBOOK.md`
- `plans/logs`

## Tasks

- Run `sgchem download-cara` if feasible.
- Reject truncated downloads using `Content-Length` and zip validation.
- Add `inspect-cara` layout reporting.
- Support flat files with split columns and paired `support`/`query` files.
- Preserve role, target, task-kind, and source-file metadata.
- Add importer tests for split support/query layouts.

## Validation Commands

```bash
uv run sgchem inspect-cara tests/fixtures/cara_split_layout --out /tmp/cara_layout.json
uv run sgchem import-cara tests/fixtures/cara_split_layout --out /tmp/cara_records.jsonl
uv run sgchem build-cards /tmp/cara_records.jsonl --out /tmp/cara_cards.jsonl --target-cards 1 --budget-k 3 --support-size 3
uv run --extra dev pytest
```

## Acceptance Criteria

- Imported records include assay IDs, compound IDs, SMILES, split/role labels,
  source files, and activity.
- Support/query split layout fixture builds at least one valid card.
- Provenance includes layout summary and source-file list.

## Risks

- CARA file structure may still require additional source-specific mapping after
  the real archive finishes downloading.
- Dataset download may be large or unavailable during agent execution.

## Handoff Notes

Keep the normalized schema stable; add source-specific adapters rather than
changing downstream card semantics.
