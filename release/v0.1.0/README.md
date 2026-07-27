# SpecGuard-Chem v0.1.0 release workspace

> **Status: unreleased candidate.** This directory is being assembled for the
> first archival release. No `v0.1.0` Git tag or published release exists yet.

SpecGuard-Chem is an action-level benchmark for a bounded experimental decision:
given sparse assay-local evidence, a fixed candidate pool, explicit eligibility
rules, and a budget of ten experiments, issue an ordered shortlist of compounds
to test next.

The release is intended to make that decision auditable and reproducible. CARA
v1.0.1 supplies the activity records and official lead-optimisation splits;
SpecGuard-Chem contributes the action contract, hidden-outcome boundary,
comparators, scoring, and release protocol. It does not claim to reproduce an
end-to-end drug-discovery programme or establish autonomous-laboratory readiness.

## Current state

| Component | Candidate status |
| --- | --- |
| Corrected 91-card system-input artifact | Frozen and audited |
| Separate scorer-only outcomes | Frozen and hash-bound to each input card |
| Deterministic baseline runs | Completed on the corrected cards |
| Exact paper-facing LLM requests | Frozen and matched to all 546 response records |
| LLM cost estimates | Historical pre-run and post-pilot upper bounds retained |
| Fixed one-card LLM pilot | Completed and retained as a historical execution checkpoint |
| Full 91-card LLM matrix | **Completed and audited: 546/546 responses** |
| Raw and repaired LLM evidence | **Six 91-card raw traces plus six zero-call repaired traces** |
| Canonical cross-system comparison | **Completed with paired uncertainty and raw/final attribution** |
| Manuscript and supplementary material | Corrected results regenerated; final archival review pending |
| Wheel and source distribution | Built and smoke-tested in an isolated environment |
| Canonical release manifest and `SHA256SUMS` | **Deliberately pending final freeze** |
| `v0.1.0` tag, archive DOI, and release date | **Not created** |

The presence of a file under `release/v0.1.0/` does not mean that the release
has been published. Until the final gates below pass, all contents are release
candidates and may change.

## Candidate bundle map

```text
data/releases/v0.1.0/
  system_input_cards.jsonl       public evidence and action contract
  scorer_outcomes.jsonl          hidden retrospective candidate outcomes
  system_input_cards.meta.json   build identity and artifact hashes
  system_input_cards.audit.json  task inclusion, exclusion, and integrity audit
  import_audit.json              exhaustive official-split resolution audit
  source_provenance.json         CARA source, license, sizes, and hashes
  schemas/                       JSON Schemas for the paired JSONL row types

release/v0.1.0/
  experiments/baselines/         corrected deterministic traces and scores
  experiments/llm/               exact requests, full matrix, replay cache, comparison, and pilot provenance
  software/                      verified v0.1.0 wheel and source distribution
  README.md                      this status and bundle guide
  RELEASE_NOTES.md               draft release notes
  REPRODUCE.md                   current offline reproduction path

paper/
  manuscript/                    manuscript source under active development
  README.md                      paper status and evidence policy
```

The scorer artifact is public for transparent retrospective evaluation, but it
is evaluator-only during selection. Supplying it to a system invalidates the
benchmark result. The system-input schema forbids candidate activity values;
the executable loader additionally checks paired task IDs, candidate order,
provenance, and canonical input hashes.

## Evidence status

The corrected deterministic baselines and completed LLM matrix now establish
the paper-facing comparison ladder. The LLM directory contains the exact 546
request payloads, 546 content-addressed response records, six raw 91-card
traces, six separately attributed deterministic post-hoc repair traces, and
their score directories. The
[matrix manifest](experiments/llm/matrix/manifest.json) records all six raw
provider/interface runs, while the
[canonical comparison](experiments/llm/comparison/primary_leaderboard.csv)
combines the deterministic systems, raw LLM actions, and repaired system views.

The completed audit matched every response to the frozen request order and
request SHA256, found one provider attempt for every successful response, and
confirmed 100% usage, latency, and usage-derived cost coverage. Applying the
frozen token prices to provider-reported usage gives USD 58.95671601 across the
six unique live conditions. Post-hoc repair added no provider calls; repaired
scores characterize the model-plus-deterministic-harness system and must not be
read as unaided model performance.

No artifact or response cache derived from the invalid historical paper-50
import will be reused. See
[the invalid-results notice](../../INVALID_RESULTS_NOTICE.md).

The fixed pilot remains useful historical provenance. It selected task
`CARA_LO_CHEMBL1006579_IC50_0001` across both interfaces and all three model
conditions. All six calls completed with one provider attempt each for a
usage-derived cost of USD 0.449700535, below the USD 0.936717455 pilot gate.
At that checkpoint, the saved post-pilot estimate reported 540 missing calls
with a USD 105.122676615 conservative upper bound. Those calls have since
completed into the same shared cache. See the
[pilot record](experiments/llm/pilot/README.md).

## Release gates

The LLM execution, replay, attribution, and comparison gates have passed. The
archival release remains blocked until all of the following are true:

- paper tables, figures, and claims are regenerated only from corrected inputs;
- the manuscript, supplement, package distributions, and licensing metadata
  are final;
- a clean checkout reproduces the offline validation and reported artifacts;
- a canonical `MANIFEST.json` records every bundled file, size, role, and
  SHA256 digest;
- `SHA256SUMS` is generated from the final byte-for-byte bundle and verified;
  and
- repository, data, schema, citation, paper, release, and tag versions agree.

`MANIFEST.json` and `SHA256SUMS` are intentionally absent while files are still
changing. Generating them now would create a false finality signal and stale
checksums.

## Documentation

- [Reproduction guide](REPRODUCE.md)
- [Draft release notes](RELEASE_NOTES.md)
- [Benchmark card](../../BENCHMARK_CARD.md)
- [Data card](../../DATA_CARD.md)
- [Paper status](../../paper/README.md)
- [Data licensing](../../DATA_LICENSE.md)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)
