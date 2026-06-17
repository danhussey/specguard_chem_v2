# SpecGuard-Chem v2

SpecGuard-Chem v2 is a reproducible audit harness for constrained medicinal
chemistry compound prioritisation. It turns public assay data into frozen
decision cards, runs deterministic baselines and cached LLM systems, and reports
whether a system improves useful finite-budget top-k choices or only improves
contract compliance.

The project is deliberately narrow: systems rank supplied candidate IDs. They do
not generate molecules, plan synthesis, or make therapeutic claims.

![Compliance and utility frontier](paper/figures/cara_lo_paper_50_direct_json_completed/compliance_utility_frontier.png)

## Current Result

The current paper-facing result is the CARA lead-optimisation 50-card
direct-JSON audit. Each card gives a system support compounds with measured
activity, a hidden-activity candidate pool, hard constraints, and a budget of
`k=10` selections.

Headline: guarded LLM systems were useful and substantially better than simple
rule/random regions, but all three per-card QSAR baselines remained stronger
deployable systems on this benchmark slice.

| System | Feasible utility | NDCG@k | Compliance |
| --- | ---: | ---: | ---: |
| Oracle upper-bound | 89.022 | 1.000 | 1.000 |
| QSAR linear SVR | 81.382 | 0.910 | 1.000 |
| QSAR gradient boosting | 80.888 | 0.900 | 1.000 |
| QSAR random forest | 80.634 | 0.901 | 1.000 |
| LLM plus validator - OpenAI gpt-5.5, low reasoning, Direct JSON | 78.188 | 0.881 | 1.000 |
| LLM plus tools and validator - OpenAI gpt-5.5, low reasoning, Direct JSON | 77.688 | 0.873 | 1.000 |
| Similarity-to-best-active baseline | 73.603 | 0.825 | 1.000 |

Paired bootstrap over the same 50 cards estimated that `qsar_svm` exceeded the
best final LLM row by `3.194` feasible-utility points, with a 95% interval of
`1.942` to `4.692`. The oracle exceeded `qsar_svm` by `7.639` points, leaving
measurable headroom.

## What This Demonstrates

- A benchmark design that separates output validity from decision utility.
- A reproducible data path from CARA-derived assay splits to frozen decision
  cards.
- Strong non-language baselines: random valid, rule/desirability, similarity,
  random forest QSAR, gradient boosting QSAR, and linear SVR QSAR.
- LLM system adapters with replay caches, raw-vs-repaired output accounting,
  deterministic validation, and cost gates for live provider calls.
- Paper-facing reporting: leaderboard tables, bootstrap deltas, failure
  taxonomy, card-level diagnostics, static dashboards, and figures.

## Key Artifacts

- [Result snapshot](paper/CARA_LO_PAPER_50_RESULTS.md)
- [Generated results summary](paper/RESULTS_SUMMARY.md)
- [Static dashboard](paper/RESULTS_DASHBOARD.html)
- [Primary leaderboard CSV](paper/tables/cara_lo_paper_50_direct_json_completed/primary_leaderboard.csv)
- [Paired bootstrap deltas](paper/tables/cara_lo_paper_50_direct_json_completed/paired_bootstrap_key_deltas.csv)
- [50-card benchmark artifact](data/cards/cara_lo_paper_50.jsonl)
- [Benchmark card](BENCHMARK_CARD.md)
- [Data card](DATA_CARD.md)
- [Architecture notes](ARCHITECTURE.md)

## Repository Map

```text
src/specguard_chem_v2/   Python package and CLI implementation
configs/                 model matrix, pricing, and default constraints
data/cards/              committed small/frozen benchmark card artifacts
tests/                   unit tests and fixture cards
paper/                   tracked result tables, figures, dashboard, summaries
docs/                    methods notes, cost controls, run ledger, runbook
plans/                   executed milestone plans and logs
```

The implementation layers are intentionally simple: schemas, IO, chemistry
constraints/descriptors, CARA ingestion, systems, runner, scoring, reporting,
and CLI orchestration.

## Quickstart

Install with `uv`:

```bash
uv venv --seed
uv pip install -e ".[dev,providers]"
```

Run the test suite:

```bash
uv run pytest
```

Validate fixture cards and run the lightweight fixture suite:

```bash
uv run sgchem validate-cards tests/fixtures/cards.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl \
  --systems random_valid,rules_only,similarity_to_best_active,qsar_rf \
  --out runs/fixture
```

Regenerate a comparison and figures from scored runs:

```bash
uv run sgchem compare-runs runs/fixture/*/scores/summary.json \
  --out runs/fixture/compare
uv run sgchem make-figures runs/fixture/compare/system_comparison.csv \
  --out paper/figures
```

## LLM Runs

LLM calls are cacheable and off by default. Live provider calls require
`--allow-external`, and expensive runs should use the cost-estimation gates in
[docs/COST_CONTROL.md](docs/COST_CONTROL.md).

```bash
uv run sgchem export-llm-requests data/cards/cara_lo_paper_50.jsonl \
  --systems bare_llm,llm_tools \
  --model-matrix configs/model_matrix.toml \
  --out runs/llm_requests.jsonl
```

Raw model behavior and final guarded-system behavior are reported separately.
Validator repair is deterministic harness behavior; it is not treated as raw
LLM medicinal-chemistry performance.

## Safety Boundary

SpecGuard-Chem v2 ranks provided candidate IDs for retrospective offline audit.
It does not make prospective efficacy, toxicity, synthesis, selectivity, safety,
or clinical claims. See [BENCHMARK_CARD.md](BENCHMARK_CARD.md) and
[docs/SAFETY.md](docs/SAFETY.md) for the project boundary.
