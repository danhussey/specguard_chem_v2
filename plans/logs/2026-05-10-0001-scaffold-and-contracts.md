# 2026-05-10 0001 Scaffold And Contracts

## Summary

Implemented the initial SpecGuard-Chem v2 scaffold as a runnable Python package
for constrained top-k compound-prioritisation audits. The repository now has a
durable planning system, core docs, schemas, CARA-like ingestion, RDKit
constraints/descriptors, deterministic baselines, LLM cache/replay interfaces,
runner, scoring, reports, fixture data, and tests.

## Commands Run

```bash
uv run pytest
uv run --extra dev pytest
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems random_valid,rules_only,similarity_to_best_active,qsar_rf --out runs/fixture
uv run sgchem compare-runs runs/fixture/random_valid/scores/summary.json runs/fixture/rules_only/scores/summary.json runs/fixture/similarity_to_best_active/scores/summary.json runs/fixture/qsar_rf/scores/summary.json --out runs/fixture/compare
uv run sgchem make-figures runs/fixture/compare/system_comparison.csv --out paper/figures
```

## Tests

Final result:

```text
7 passed in 2.66s
```

Notes:

- `uv run pytest` initially failed because dev dependencies were not installed.
- `uv run --extra dev pytest` initially needed escalated filesystem access to
  the shared `uv` cache.
- Final CLI smoke run completed for `random_valid`, `rules_only`,
  `similarity_to_best_active`, and `qsar_rf`.

## Files Changed

- Added package scaffold and CLI in `src/specguard_chem_v2`.
- Added fixture data and tests under `tests`.
- Added docs in `docs`, plus `PROJECT_BRIEF.md`, `ARCHITECTURE.md`, `AGENTS.md`,
  and `README.md`.
- Added planning system under `plans`.
- Added `configs/default_constraints.json` and `.gitignore`.

## Decisions

- Kept v2 as a clean package, not a refactor of the sibling v1 benchmark.
- Treated `plans/` as the execution memory for future chats.
- Made live LLM calls opt-in via `--allow-external`; offline cache/replay is the
  default testable path.
- Used fixture CARA-like data for CI-style tests until official CARA ingestion is
  hardened.

## Follow-Up Work

- Promote `plans/upcoming/0002-cara-ingestion.md` and validate importer behavior
  against the real downloaded CARA archive.
- Add source-specific importer tests after inspecting the official file layout.
- Add bootstrap confidence intervals and paper-ready failure taxonomy reports.
- Add cached LLM fixtures for all LLM system variants.
