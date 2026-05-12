# AGENTS

This file is the short map for agents. Do not turn it into the project manual.
Use the linked docs as the system of record.

## Read First

1. `PROJECT_BRIEF.md`
2. `ARCHITECTURE.md`
3. `BENCHMARK_CARD.md` and `DATA_CARD.md`
4. `docs/CARA_LOCAL_AUDIT.md`
5. `docs/LLM_SYSTEMS.md`
6. `docs/LLM_FAILURE_MODES.md`
7. `plans/README.md`
8. latest plan in `plans/active/`
9. latest log in `plans/logs/`

## Core Rules

- Keep v2 focused on constrained top-k candidate prioritisation.
- Do not refactor or mutate `../specguard-chem`; it is a reference only.
- Do not implement de novo molecule generation in the first version.
- Live LLM calls require explicit `--allow-external` and must be cacheable.
- Update execution plans and logs when changing project direction or completing a milestone.

## Common Commands

```bash
uv run pytest
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems random_valid,rules_only,similarity_to_best_active,qsar_rf --out runs/fixture
```
