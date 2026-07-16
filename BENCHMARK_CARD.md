# Benchmark Card

## Name and status

**SpecGuard-Chem 0.1.0** is the frozen action-level benchmark artifact for the
first archival release.
The corrected 91-card data artifact and deterministic baselines are frozen. A
fixed one-card, six-request provider pilot is complete and preserved as
operational evidence. The remaining 540 calls and the full 91-card LLM
comparison are pending, so the pilot is not a benchmark leaderboard result.

Historical paper-50 results are invalid and are not comparable benchmark
versions; see `INVALID_RESULTS_NOTICE.md`.

## Intended use

Offline evaluation of systems that select a ranked, fixed-size assay batch from
an assay-local pool. The benchmark is designed as a unit test for a decision
primitive that could sit inside a future automated design--make--test--analyse
workflow.

It is useful for comparing:

- conventional molecular ranking methods and LLM-backed systems;
- basic versus descriptor-enriched evidence representations;
- raw model actions versus the same actions after deterministic repair; and
- decision quality, execution reliability, and operational cost.

## Formal task

Each task provides:

- an assay and target identifier;
- 50 support compounds with observed pChEMBL activity, explicitly marked as
  higher-is-better;
- a finite candidate pool with structures and permitted descriptors;
- explicit hard constraints; and
- a budget `k = 10`.

The system returns exactly ten candidate IDs ordered from highest to lowest
priority. Candidate activity outcomes are absent from the system artifact and
reserved for retrospective scoring.

## What is new relative to CARA

CARA supplies the underlying activity records and official lead-optimization
splits. SpecGuard-Chem changes the evaluated object from per-compound activity
prediction to a budgeted action over a finite pool. Its contribution is the
action contract and evaluation/release protocol—not a new raw dataset and not a
claim that constrained selection is algorithmically unrelated to ranking.

The transparency of the solution class is intentional. A valid system must
filter, estimate, rank, and allocate; a benchmark result shows how well and how
reliably a particular system performs those operations under controlled
information access.

## v0.1.0 composition

- CARA version: `1.0.1` (`LO_All` split)
- CARA task keys considered: 100
- Included tasks: 91
- Excluded tasks: 9 with fewer than ten feasible candidates
- Support compounds: exactly 50 per card
- Candidate-pool range: 52--967
- Feasible-candidate range: 12--579
- Public input: `data/releases/v0.1.0/system_input_cards.jsonl`
- Hidden outcomes: `data/releases/v0.1.0/scorer_outcomes.jsonl`

The public and scorer artifacts carry shared benchmark/data/config provenance,
and each outcome row is bound to the canonical public card hash.

## Evaluation

Primary scientific readouts:

- NDCG@`k`;
- feasible utility;
- constrained regret to the hidden valid top-`k` oracle;
- selected activity and hit/enrichment measures where defined; and
- paired card-level uncertainty.

Action-reliability readouts:

- whole-action validity: the fraction of cards with no output-contract issue;
- exact-size, in-pool, nonduplicate, support-exclusion, and molecular-
  constraint validity;
- valid-selection fraction (`compliance_rate`) for partial-credit diagnosis; and
- raw-versus-repaired output attribution.

Validity is never substituted for utility. A compliant weak list is a valid but
poor action; a strong-looking invalid list is not executable as issued.

## Comparators

The release includes random-valid and rules/desirability floors, similarity to
the best observed support compound, three per-card QSAR models, and a
non-deployable hidden-outcome oracle. These are necessary controls: if an LLM
does not improve on a small transparent ranker, the benchmark should reveal
that rather than treating language use as a contribution by itself.

## Out of scope

- de novo molecule generation and synthesis planning;
- prospective or closed-loop wet-lab validation;
- selectivity, ADMET, toxicity, safety, and therapeutic recommendation;
- biological interpretation beyond the retrospective assay target/endpoint;
- autonomous-laboratory readiness; and
- comparison across card versions without explicit versioning.

## Known limitations

- Retrospective activity is only a proxy for the value of a future experiment.
- The task inherits CARA/ChEMBL measurement heterogeneity and curation choices.
- One assay-local potency endpoint omits multi-objective project biology.
- Molecular constraints are simple eligibility rules, not medicinal-chemistry
  or synthesis review.
- A one-shot shortlist does not evaluate learning across experimental rounds.
- Provider APIs and model behavior can change; exact request/model metadata and
  replay artifacts are therefore part of the benchmark result.

## Reporting policy

Every report must name the card and scorer artifact hashes, model/provider
condition, interface, raw-versus-repaired status, prompt/generation settings,
run date, and cost. Results from invalid historical imports must not appear as
current or comparative evidence.
