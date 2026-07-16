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

Corrected deterministic baselines have been generated. Exact requests and a
pre-run cost estimate have been generated for the proposed LLM matrix, but **no
live provider call has been made for this release candidate**. Therefore there
is no final LLM comparison, raw-versus-repaired result, or conference-paper
headline result yet. Historical model responses and caches will not be reused.

## Still required before release

- Explicit approval and cost-gated execution of the paper-facing live LLM run.
- Corrected uncertainty, attribution, robustness, latency, token, and monetary
  analyses from those runs.
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
