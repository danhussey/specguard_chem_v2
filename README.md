# SpecGuard-Chem v2

SpecGuard-Chem v2 is a decision-audit harness for constrained medicinal-chemistry
compound prioritisation. It evaluates whether guarded and tool-using systems
improve useful finite-budget top-k choices, or mainly improve compliance with
surface-level specifications.

The project is intentionally not a broad activity-prediction benchmark, a drug
discovery agent benchmark, or a de novo molecular generation system.

## Quickstart

```bash
uv venv --seed
uv pip install -e ".[dev,providers]"

sgchem validate-cards tests/fixtures/cards.jsonl
sgchem list-systems
sgchem run-suite tests/fixtures/cards.jsonl --systems all --out runs/fixture
sgchem score-run tests/fixtures/cards.jsonl runs/fixture/random_valid/trace.jsonl --out runs/fixture/random_valid/scores
sgchem compare-runs runs/fixture/*/scores/summary.json --out runs/fixture/compare
sgchem make-figures runs/fixture/compare/system_comparison.csv --out paper/figures
sgchem make-report runs/fixture/compare/system_comparison.csv --out paper
```

## Repository Map

Start with `AGENTS.md`. It points to durable sources of truth in `docs/` and
`plans/`. Active and completed execution plans are versioned because this project
is expected to span multiple agent chats.

## Safety Boundary

SpecGuard-Chem v2 ranks supplied candidate IDs. It does not generate new
molecules, plan synthesis, or make therapeutic claims. See `SAFETY.md` and
`BENCHMARK_CARD.md`.
