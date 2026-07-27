# SpecGuard-Chem v0.1.0 release notes

> **Draft — unreleased.** No `v0.1.0` tag, release archive, DOI, or final release
> date exists yet. These notes describe the intended first archival release,
> not a completed publication.

## Positioning

Version 0.1.0 presents constrained assay-local compound selection as an
action-level unit test for systems that may eventually participate in automated
drug-discovery laboratories. A system must convert sparse project-local assay
evidence into a useful, valid, budget-constrained experimental shortlist.

The benchmark deliberately evaluates a narrow filter-predict-rank-allocate
primitive. CARA remains the upstream data and split substrate. The contribution
is the frozen action contract and evaluation protocol, not a new raw molecular
dataset or a claim of end-to-end laboratory autonomy.

## Intended release contents

- A corrected positional importer for the official CARA `LO_All` split, with
  regression tests and exhaustive task-identity checks.
- Ninety-one deterministic decision cards at `k = 10`, including every official
  task with at least ten candidates feasible under the declared constraints.
- Separate system-input and scorer-only JSONL artifacts with shared provenance
  and per-card cryptographic binding.
- JSON Schemas for both split-artifact row types.
- Random-valid, rules, similarity, three per-assay QSAR comparators, and a
  hidden-outcome oracle, all rerun on corrected cards.
- A minimum paper-facing LLM matrix using basic and descriptor-enriched
  interfaces, exact requests, provider/model configuration, replayable traces,
  raw-versus-repaired attribution, and cost reporting.
- A conference-track manuscript, supplementary material, generated tables and
  figures, package distributions, citation metadata, license notices, a
  canonical manifest, and checksums.

## Artifact-contract change

Candidate outcomes are no longer carried in a monolithic system-facing card.
The release uses two paired artifacts:

- `data/releases/v0.1.0/system_input_cards.jsonl` contains only the information
  available when issuing an action; and
- `data/releases/v0.1.0/scorer_outcomes.jsonl` contains retrospective candidate
  outcomes for evaluator use.

Each scorer row records the canonical SHA256 digest of its matching public card.
Loading or scoring the pair verifies task identity, provenance, candidate order,
and the binding hash. The public-input schema excludes candidate activity fields.

## Invalid historical results

The six historical `results/cara-lo-paper-50-*` tags are retained as immutable
provenance but are superseded. Their CARA importer resolved positional split
references against the wrong dataframe index, so their cards, prompts, traces,
scores, tables, figures, and claims are invalid. They are not earlier benchmark
versions and must not be compared with v0.1.0.

Full details are in
[`INVALID_RESULTS_NOTICE.md`](../../INVALID_RESULTS_NOTICE.md).

## Current experimental status

Corrected deterministic baselines and the complete paper-facing LLM matrix have
been generated. The matrix crosses three frozen provider/model conditions with
the basic and descriptor-enriched interfaces over all 91 corrected cards. All
546 exact requests have matching content-addressed responses. The candidate
bundle retains six raw 91-card traces and six deterministic, zero-call post-hoc
repair traces, together with raw and repaired scores, a canonical matrix
manifest, and the cross-system comparison. Historical model responses and
caches from the invalid paper-50 import were not reused.

Every successful response has one recorded provider attempt, and usage,
latency, and usage-derived cost coverage are 100%. Provider-reported token
usage multiplied by the frozen pricing snapshot gives USD 58.95671601 for the
six unique live conditions. Repaired rows repeat the source condition's cost
and must not be summed as additional calls.

On feasible utility, the three QSAR systems occupy the first three non-oracle
positions. Linear SVR records 74.9664, while the strongest final LLM view,
OpenAI basic plus deterministic post-hoc repair, records 73.9637. The paired
QSAR-minus-LLM difference is 1.0027 with a task-level 95% percentile-bootstrap
interval of [0.4049, 1.6475]. The strongest raw LLM action has 79.12% whole-action
validity; repair raises final validity to 100% but is a harness intervention,
not recovered unaided model ability. Descriptor enrichment is
provider-dependent rather than a general improvement.

The original fixed one-card pilot, pre-run estimate, and post-pilot estimate
remain in the bundle as historical execution and cost-control provenance. They
must not be mistaken for the final 91-card evidence.

## Still required before release

- Final manuscript, supplement, tables, figures, and paper licensing decision.
- Clean-checkout reproduction and final bundle verification. The candidate
  wheel and source distribution already build and pass an isolated CLI smoke
  test.
- Final DOI, release date, and synchronized version metadata.
- Canonical `MANIFEST.json` and `SHA256SUMS`, generated only after every bundled
  file is frozen.
- Creation of the annotated `v0.1.0` tag only after all stop-ship gates pass.

## Licensing

Repository code is MIT-licensed. CARA and CARA-derived benchmark data remain
subject to CC BY 4.0 attribution; see
[`DATA_LICENSE.md`](../../DATA_LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md). The manuscript license
will be recorded before the archival release after the publication route is
fixed.
