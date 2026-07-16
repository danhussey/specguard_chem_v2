# SpecGuard-Chem

**An action-level benchmark for asking whether a language-model system can turn
sparse assay evidence into a valid, useful experimental shortlist.**

[![CI](https://github.com/danhussey/specguard_chem_v2/actions/workflows/ci.yml/badge.svg)](https://github.com/danhussey/specguard_chem_v2/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Code license: MIT](https://img.shields.io/badge/code%20license-MIT-2EA44F)
![LLM calls: offline by default](https://img.shields.io/badge/LLM%20calls-offline%20by%20default-6F42C1)

Automated drug-discovery laboratories will not only ask models for predictions
or prose. They will delegate actions: choose what to synthesize, which assay to
run, and where to spend a finite experimental budget. Those actions consume
material, time, and capacity.

SpecGuard-Chem evaluates one deliberately bounded action primitive before
attempting an end-to-end autonomous loop:

> Given project-local assay evidence, a fixed candidate pool, explicit
> eligibility rules, and a budget of `k` experiments, which compounds should be
> tested next?

The benchmark is an **action-level unit test**. It does not claim to simulate
drug discovery. Its value is that the action is consequential, auditable,
cheap enough to evaluate repeatedly, and narrow enough to compare LLM systems
against strong conventional molecular rankers on identical evidence.

## Result status

**No prior paper-50 number in this repository is a valid current result.** The
old CARA importer resolved positional split references against the wrong
dataframe index. All downstream cards, model calls, tables, figures, and claims
from that import are retired. See [INVALID_RESULTS_NOTICE.md](INVALID_RESULTS_NOTICE.md).

The corrected import has now passed an exhaustive local integrity audit:

- 24,588 of 24,588 official `LO_All` split references resolve to the named task;
- 5,000 support and 19,588 candidate rows form 100 coherent assay tasks;
- every task has 50 support measurements;
- there are no task, target, endpoint, or support/query identity mismatches; and
- 91 tasks remain feasible at `k = 10` under the current explicit constraints.

The corrected `0.1.0` data artifact is now frozen as separate system-input
and scorer-only files, with deterministic build/audit manifests and checksums.
Corrected deterministic baselines have also been rerun on all 91 cards. The
paper-facing LLM matrix is specified and costed but has **not** made live
provider calls, so no cross-model paper result is yet final. No historical
response cache will be reused.

## The evaluated action

Each decision card represents one retrospective assay-local allocation choice.

| Component | System visibility | Purpose |
| --- | :---: | --- |
| Support compounds and measured activity | Yes | Evidence available before the action |
| Assay/target metadata available in CARA | Yes | Local experimental context |
| Candidate IDs, structures, and permitted descriptors | Yes | Finite action space |
| Hard constraints and budget `k` | Yes | Executable action contract |
| Candidate activity outcomes | **No** | Scorer-only retrospective evidence |

A system returns an ordered list of exactly `k` candidate IDs. It may not invent
molecules or select outside the supplied pool.

The formal solution class is intentionally simple: **filter, predict, rank, and
allocate**. Simplicity is a feature of the unit-test boundary. It lets the study
isolate whether an LLM adds decision value over a transparent molecular model,
and whether the issued action could actually be executed.

## What the paper asks

The conference paper is organized around action quality rather than around
guardrails alone:

1. **Incremental value:** do current LLM systems select better assay batches
   than random-valid, heuristic, similarity, and per-assay QSAR baselines?
2. **Representation:** does descriptor-enriched evidence change scientific
   shortlist quality relative to a basic molecular representation?
3. **Execution reliability:** how often does a direct model response violate
   the action contract, and what changes when deterministic repair is applied
   to the same raw response?
4. **Operational cost:** what latency, token, and monetary cost buys any
   observed gain over conventional rankers?

Primary scientific readouts are ranking/selection utility and regret relative
to a hidden-outcome oracle. Action validity is reported separately so a
well-formatted weak shortlist is not mistaken for a useful decision, and an
invalid shortlist is not credited as executable.

## Is this only CARA with filtering?

CARA is the upstream data and split substrate; SpecGuard-Chem does not claim a
new raw molecular dataset or a fundamentally new potency-prediction problem.
The benchmark contribution is the adaptation from label prediction to a frozen
experimental action contract:

- a finite assay-local decision state and explicit budget;
- machine-checkable candidate and output constraints;
- strong classical, QSAR, oracle, and LLM-backed comparators;
- raw-versus-repaired action attribution;
- per-card action-sensitive metrics and paired uncertainty;
- exact prompts, traces, model settings, costs, and replay controls; and
- a versioned release in which system inputs and scorer outcomes are separate.

If a conventional per-assay ranker dominates the LLMs, that is not a failed
benchmark. It is evidence about where language models should—and should not—be
placed in a future automated laboratory.

## Scope boundary

Version 0.1.0 evaluates one-shot, retrospective, assay-local compound selection.
It does **not** evaluate:

- de novo molecule generation;
- synthesis or route planning;
- multi-step closed-loop experimentation;
- selectivity, ADMET, toxicity, or clinical efficacy;
- prospective wet-lab outcomes; or
- readiness for autonomous drug discovery.

Those are possible later layers, not prerequisites for publishing this bounded
benchmark. Current constraints are intentionally simple molecular-property and
output-contract rules; they are not a substitute for medicinal-chemistry or
biological review.

## System and evaluation ladder

The offline harness includes:

- random-valid and rules/desirability floors;
- similarity to the best observed support compound;
- per-card random-forest, gradient-boosting, and support-vector QSAR models;
- a hidden-activity valid top-k oracle as a non-deployable upper bound; and
- basic and descriptor-enriched LLM interfaces with optional deterministic
  validation/repair.

The main metrics are NDCG@`k`, feasible utility, constrained regret, mean
selected activity, action-validity rates, and raw/final attribution. Systems are
compared on the same cards with paired card-level uncertainty.

## Reproduce the offline path

The project uses [uv](https://docs.astral.sh/uv/) and a committed lockfile.

```bash
uv sync --locked --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
```

Run a fully offline fixture evaluation:

```bash
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl \
  --systems random_valid,rules_only,similarity_to_best_active,qsar_rf \
  --out runs/fixture
uv run sgchem compare-runs runs/fixture/*/scores/summary.json \
  --out runs/fixture/compare
```

The fixture path makes no network or provider call. Live LLM calls are disabled
unless `--allow-external` is passed. Paper-scale calls additionally require a
saved cost estimate and hard limits; see [docs/COST_CONTROL.md](docs/COST_CONTROL.md).

## Release target

The first archival release will bundle and checksum:

- corrected system-input cards and separate scorer outcomes;
- resolved build configuration, source provenance, and exclusion audit;
- deterministic and approved LLM traces with exact requests and model settings;
- per-card scores, aggregate tables, uncertainty estimates, and figures;
- manuscript source, compiled paper, and supplementary methods;
- environment lock, package distributions, citation and licensing metadata;
- a canonical manifest and `SHA256SUMS`; and
- release notes that supersede the six historical result tags without moving
  or deleting them.

The active execution plan is
[plans/active/0030-bounded-v1-archival-release.md](plans/active/0030-bounded-v1-archival-release.md).

## Repository guide

```text
src/specguard_chem_v2/   package, task contracts, systems, scoring, reports, CLI
configs/                 constraints, model matrix, pricing snapshot
tests/                   unit/integration tests and offline fixtures
data/                    raw, normalized, and deliberately frozen data layers
runs/                    replayable traces and score artifacts
paper/                   manuscript, tables, figures, and supplementary material
docs/                    methods, safety, data contracts, runbook, run ledger
plans/                   active/executed plans and experiment logs
```

Start with [PROJECT_BRIEF.md](PROJECT_BRIEF.md),
[BENCHMARK_CARD.md](BENCHMARK_CARD.md), [DATA_CARD.md](DATA_CARD.md), and
[ARCHITECTURE.md](ARCHITECTURE.md).

## Data provenance and licenses

The activity-data substrate is CARA v1.0.1:

> Tian, T., Li, S., Zhang, Z., Chen, L., Zou, Z., Zhao, D., and Zeng, J.
> *CARA: Benchmarking Compound Activity Prediction for Real-World Drug
> Discovery Applications.* Zenodo.
> [doi:10.5281/zenodo.14740896](https://doi.org/10.5281/zenodo.14740896)

Code is released under the [MIT License](LICENSE). CARA and CARA-derived data
remain subject to the upstream CC BY 4.0 attribution terms described in
[DATA_LICENSE.md](DATA_LICENSE.md) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Citation metadata is in
[CITATION.cff](CITATION.cff).
