# 0002 CARA Ingestion Hardening

Status: completed on 2026-05-10. See
`plans/logs/2026-05-10-0003-official-cara-ingestion.md`.

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

## Tasks Completed

- Added resumable, content-length checked CARA download.
- Added `inspect-cara` layout reporting.
- Resolved official `Task/{split}.tsv` plus
  `Split/{split}_support/query.json` files into normalized support/query
  records.
- Preserved role, target, assay, value-type, row-index, and source-file metadata.
- Added importer tests for generic, split support/query, and official CARA-like
  layouts.
- Imported real `LO_All` records and built/validated a 20-card local data smoke.

## Validation Commands

```bash
uv run --extra dev pytest
uv run sgchem import-cara data/raw/cara --split-name LO_All --out data/interim/cara_lo_all_records.jsonl
uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl --out data/cards/cara_lo_all_cards.jsonl --target-cards 20 --budget-k 10 --support-size 50
uv run sgchem validate-cards data/cards/cara_lo_all_cards.jsonl
```

## Acceptance Criteria

- Imported records include assay IDs, compound IDs, SMILES, split/role labels,
  source files, and activity.
- Support/query split layout fixture builds at least one valid card.
- Provenance includes layout summary and source-file list.
- Real CARA `LO_All` imports and yields at least 20 valid cards.

## Risks

- Larger paper-scale card builds may need selection policies beyond first-N
  assay ordering.
- Generated raw/interim/card artifacts are intentionally ignored and must be
  regenerated or intentionally frozen before sharing.

## Handoff Notes

Promote `plans/upcoming/0003-baselines-and-scoring.md` next. The local CARA
audit in `docs/CARA_LOCAL_AUDIT.md` should be treated as the current empirical
checkpoint.
