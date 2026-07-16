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
| Exact paper-facing LLM requests | Exported without provider calls |
| LLM cost estimates | Pre-run and post-pilot upper bounds saved |
| Fixed one-card LLM pilot | **Completed and audited: 6/6 traces and caches** |
| Full 91-card LLM matrix and cross-model results | **Pending; 540 calls remain** |
| Manuscript and supplementary material | Compiled pre-run drafts; final results pending |
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
  experiments/llm/               exact requests, pilot traces/caches/scores, and cost estimates
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

The corrected deterministic baselines establish an offline comparison ladder.
They are not a substitute for the pending paper-facing LLM experiment. The LLM
directory contains the exact 546 request payloads plus a completed fixed pilot:
six response caches, raw traces, scores, deterministic post-hoc views, and
complete model/usage/latency/cost provenance for one task. The other 540 calls
and any cross-model paper result remain pending.

No artifact or response cache derived from the invalid historical paper-50
import will be reused. See
[the invalid-results notice](../../INVALID_RESULTS_NOTICE.md).

The fixed pilot selects task `CARA_LO_CHEMBL1006579_IC50_0001` across both
interfaces and all three model conditions. All six calls completed with one
provider attempt each for an actual recorded cost of USD 0.449700535, below the
USD 0.936717455 pilot gate. A cache-only replay reproduced all score artifacts.
The shared full-matrix cache now contains those six responses, and the saved
post-pilot estimate reports 540 missing calls with a USD 105.122676615
conservative upper bound. See the [pilot record](experiments/llm/pilot/README.md).

## Release gates

The archival release remains blocked until all of the following are true:

- any approved live LLM conditions have run with explicit external-call
  authorization, saved replay data, and hard cost/call/token gates;
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
