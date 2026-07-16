# Architecture

SpecGuard-Chem v0.1.0 is an action-level benchmark: a system must turn sparse,
project-local assay evidence into a valid, useful, budget-constrained shortlist.
CARA supplies the activity records and official support/query partitions;
SpecGuard-Chem defines the action contract, system-visible artifact, baselines,
validation, scoring, and reproducible execution boundary.

## Trust Boundary

The release deliberately separates benchmark inputs from scorer-only outcomes:

- `data/releases/v0.1.0/system_input_cards.jsonl` is the only card artifact a
  system may consume. It contains support activities, candidate identities and
  structures, computed descriptors, constraints, assay context, and provenance.
  It contains no candidate activity labels, local source paths, or timestamps.
- `data/releases/v0.1.0/scorer_outcomes.jsonl` contains hidden candidate
  activities. Each outcome record is bound to the canonical system input by a
  per-card SHA256 digest and is loaded only by validation and scoring paths.

The runner reconstructs an allowlisted system-input view before execution even
when it is given an in-memory hydrated card. Oracle controls are the sole systems
allowed to depend on scorer outcomes, and they are reported separately from
deployable systems.

## Data and Evaluation Flow

```text
CARA v1.0.1 archive
  -> import-cara
       positional split lookup + exact task-key verification
  -> normalized LO_All records
  -> build-cards
       deterministic ordering + explicit constraints + inclusion audit
  -> system_input_cards.jsonl --------> baseline or LLM system
  -> scorer_outcomes.jsonl                  |
             |                              v
             +------------------------> trace.jsonl
                                             |
                                             v
                                      score-run / reports
```

The v0.1.0 build considers all 100 official `LO_All` tasks. Ninety-one satisfy
the prespecified requirement of at least ten feasible candidates for `k=10`;
the nine exclusions and their reasons are recorded in
`system_input_cards.audit.json`.

LLM evaluation adds a second, non-mutating branch:

```text
raw bare_llm or llm_tools trace
  -> deterministic repair-llm-trace
  -> separate __posthoc_repair trace
  -> raw and guarded-system scores from the same provider response
```

Post-hoc repair never issues a provider call and never replaces the raw trace.

## Package Layers

- `schemas`: Pydantic contracts for cards, provenance, outputs, issues, and
  traces.
- `io`: deterministic JSON and JSONL serialization.
- `chem`: RDKit descriptors, fingerprints, constraints, and validation.
- `data`: CARA downloader, integrity-checked importer, and deterministic builder.
- `artifacts`: allowlisted system-input projection, scorer-outcome binding, and
  verified hydration.
- `systems`: deterministic baselines plus LLM cache/replay adapters.
- `runner`: label-safe system execution and output validation.
- `posthoc`: attributable deterministic repair of existing raw LLM traces.
- `scoring`: scorer-only outcome hydration, card-level metrics, and aggregation.
- `reports`: comparisons, diagnostics, figures, and manuscript tables.
- `cli`: Typer command surface.

Dependencies should point downward through these layers. CLI code may
orchestrate all layers; core layers must not import CLI code.

## Reproducibility Boundary

Release claims must name the benchmark/data version and hashes of the system
inputs, scorer outcomes, exact requests, model configuration, and traces.
Generated artifacts live under `data/releases/v0.1.0/` and
`release/v0.1.0/`. Changing card construction, constraints, prompts, model
settings, or repair policy requires a new version or explicitly named
experimental condition; it must not silently overwrite v0.1.0 evidence.
