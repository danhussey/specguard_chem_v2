# 0001 Scaffold And Contracts

Status: completed on 2026-05-10. See
`plans/logs/2026-05-10-0001-scaffold-and-contracts.md`.

## Objective

Create the initial package, documentation map, planning structure, core data
contracts, runnable fixture harness, and smoke tests.

## Scope

- Repository scaffold.
- Decision-card and system-output contracts.
- Descriptor and hard-constraint evaluation.
- CARA-like importer and card builder.
- Deterministic baselines.
- LLM cache/replay adapter interface.
- Runner, scoring, and report generation.
- Fixture data and tests.

## Non-Goals

- Do not run live LLM calls.
- Do not validate against the full CARA dataset in this milestone.
- Do not implement de novo molecular generation.

## Affected Modules

- `src/specguard_chem_v2`
- `tests`
- `docs`
- `plans`

## Tasks Completed

- Added package metadata and CLI entry point.
- Added durable project docs.
- Added schemas, IO helpers, descriptor code, and constraints.
- Added CARA downloader/importer/card builder.
- Added baseline and LLM adapter systems.
- Added runner, scoring, and reporting.
- Added fixture data and tests.

## Validation Commands

```bash
uv run --extra dev pytest
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems random_valid,rules_only,similarity_to_best_active,qsar_rf --out runs/fixture
```

## Acceptance Criteria

- Tests pass.
- Fixture cards validate.
- At least four non-language systems run end to end.
- Scores and comparison tables can be generated.

## Risks

- CARA public file layout may differ from the importer assumptions.
- RDKit dependency installation may vary by platform.
- Live LLM providers are intentionally untested in default CI.

## Handoff Notes

Start future work by hardening the CARA importer against the downloaded official
file layout, then promote `plans/upcoming/0002-cara-ingestion.md`.
