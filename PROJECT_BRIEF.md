# Project Brief

## Working title

**Before the Lab Acts: Benchmarking Language Models for Constrained Compound
Selection**

## Public premise

Future automated drug-discovery laboratories will delegate decisions that spend
material, time, and assay capacity. Before evaluating an end-to-end autonomous
laboratory, we need reproducible unit tests for the individual actions such a
system would issue.

SpecGuard-Chem evaluates one bounded action:

> Given sparse project-local assay evidence, a fixed candidate pool, explicit
> eligibility rules, and a budget of `k` experiments, select and rank the
> compounds to test next.

The task is deliberately filter--predict--rank--allocate. That makes it small
enough to audit, rerun, and compare against strong conventional rankers while
remaining consequential: the output is an executable allocation of an
experimental budget, not a free-form prediction or explanation.

## Relationship to CARA

CARA is the credited compound-activity and split substrate. SpecGuard-Chem does
not claim a new raw molecular dataset or a new potency-prediction primitive.
Its benchmark contribution is the conversion of retrospective assay evidence
into a versioned action contract, with:

- a finite candidate set and assay budget;
- explicit system-visible versus scorer-only information;
- machine-checkable action constraints;
- classical, QSAR, oracle, and LLM-backed comparators;
- raw-versus-repaired attribution;
- action-sensitive metrics and paired uncertainty; and
- exact, replayable requests, traces, costs, and provenance.

## Research questions

1. **Incremental decision value:** do current LLM systems allocate the assay
   budget better than random-valid, heuristic, similarity, and assay-local QSAR
   baselines on identical evidence?
2. **Evidence representation:** does descriptor-enriched molecular context
   change shortlist utility relative to a basic structure/property interface?
3. **Action reliability:** how often is the raw action invalid, and how do
   utility and validity change when the same response receives deterministic
   post-hoc repair?
4. **Operational value:** what latency, token use, and monetary cost buys any
   gain over conventional rankers?

Utility and action validity are separate measurements, not competing paper
framings. Utility asks whether the proposed experiment is worth running;
validity asks whether the proposed experiment can be run as issued.

## Scope and claim boundary

Version 0.1.0 is a retrospective, one-shot, assay-local benchmark. It retains the
target and assay endpoint supplied by CARA, but it does not model selectivity,
ADMET, toxicity, synthesis feasibility, multi-assay portfolio choice, or
prospective wet-lab outcomes. It therefore supports claims about one compound-
selection action, not autonomous drug-discovery readiness.

## Success criteria

- CARA split positions resolve to the named task and are audited exhaustively.
- Frozen public inputs are physically separated from hidden scorer outcomes.
- Strong non-language baselines and an oracle demonstrate task difficulty and
  measurable headroom.
- LLM responses are cacheable, attributable to exact model conditions, and
  scored both before and after deterministic repair without paying for separate
  repair prompts.
- Every paper number traces to a card version, request or trace, score artifact,
  transform configuration, and checksum.
- A clean checkout rebuilds the paper and verifies the archival bundle before
  the semantic release tag is created.

## Non-goals for v0.1.0

- De novo molecule generation.
- Synthesis or route planning.
- Sequential closed-loop optimization.
- A broad benchmark of all drug-discovery tasks.
- Claims of biological efficacy, safety, or clinical relevance.
- Supplanting CARA as an activity-prediction benchmark.
