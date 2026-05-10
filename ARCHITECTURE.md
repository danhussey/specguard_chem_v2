# Architecture

SpecGuard-Chem v2 is organized around frozen decision cards and replayable system
runs.

## Data Flow

```text
raw CARA assets
  -> import-cara
  -> normalized records
  -> build-cards
  -> frozen decision cards
  -> run-suite / run-system
  -> trace.jsonl
  -> score-run
  -> summary tables and figures
```

## Package Layers

- `schemas`: Pydantic contracts for cards, outputs, validation issues, and run records.
- `io`: JSON/JSONL helpers with deterministic serialization.
- `chem`: RDKit descriptors, fingerprints, constraints, and validation.
- `data`: CARA downloader/importer/card builder.
- `systems`: deterministic baselines and LLM cache/replay adapters.
- `runner`: system execution, output validation, validator repair.
- `scoring`: metrics and per-card aggregate scoring.
- `reports`: comparison tables and frontier plots.
- `cli`: Typer command surface.

Dependencies should point downward through these layers. CLI code may orchestrate
all layers; core layers should not import CLI code.
