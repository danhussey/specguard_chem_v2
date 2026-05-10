# Runbook

## Setup

```bash
uv venv --seed
uv pip install -e ".[dev,providers]"
```

## Fixture Smoke

```bash
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem list-systems
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems all --out runs/fixture
uv run sgchem score-run tests/fixtures/cards.jsonl runs/fixture/qsar_rf/trace.jsonl --out runs/fixture/qsar_rf/scores
```

## CARA Pipeline

```bash
uv run sgchem download-cara --out data/raw/cara
uv run sgchem inspect-cara data/raw/cara --out data/interim/cara_layout.json
uv run sgchem import-cara data/raw/cara --split-name LO_All --out data/interim/cara_records.jsonl
uv run sgchem build-cards data/interim/cara_records.jsonl --out data/cards/cara_lo_cards.jsonl --target-cards 50 --selection-policy first
uv run sgchem summarize-cards data/cards/cara_lo_cards.jsonl --out data/cards/cara_lo_cards.summary.json
```

`download-cara` writes to `CARA.zip.part` first, resumes partial files with HTTP
range requests when possible, checks the server `Content-Length` or
`Content-Range`, rejects incomplete archives, and only then replaces `CARA.zip`.

## Full Experiment

```bash
uv run sgchem run-suite data/cards/cara_lo_cards.jsonl --systems all-with-oracle --out runs/cara_lo
uv run sgchem compare-runs runs/cara_lo/*/scores/summary.json --out paper/tables
uv run sgchem make-figures paper/tables/system_comparison.csv --out paper/figures
```
