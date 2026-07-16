# SpecGuard-Chem paper workspace

> **Status: in preparation.** The corrected data artifact and deterministic
> baselines exist, but the paper-facing live LLM run has not occurred. No final
> LLM comparison or conference-paper headline result is available yet.

## Working paper identity

**Working title:** *Before the Lab Acts: Benchmarking Language Models for
Constrained Compound Selection*

The paper frames SpecGuard-Chem as an action-level unit test for a future
automated laboratory: can a model-backed system turn sparse assay-local evidence
into a valid, useful, budget-constrained experimental shortlist?

The claim boundary is deliberately narrow. CARA supplies the activity records
and official split substrate. The paper evaluates one retrospective,
assay-local filter-predict-rank-allocate action. It does not claim de novo design,
synthesis planning, multi-step closed-loop learning, prospective biological
validation, or readiness for autonomous drug discovery.

## Evidence policy

- Candidate activity is hidden from systems and stored in a separate scorer
  artifact.
- Scientific utility and action validity are reported separately.
- Every paper number must trace to the corrected v0.1.0 cards, scorer outcomes,
  exact system/model condition, and per-card score.
- Raw model actions and deterministic post-hoc repair must be attributed from
  the same underlying response rather than treated as independent model calls.
- Current provider model identifiers, generation settings, dates, token counts,
  latency, and monetary cost must accompany LLM results.
- Invalid historical paper-50 cards, caches, responses, tables, figures, and
  claims must not be reused.

The authoritative status of those historical outputs is documented in
[`INVALID_RESULTS_NOTICE.md`](../INVALID_RESULTS_NOTICE.md).

## Layout

```text
paper/
  manuscript/   LaTeX source and bibliography under active development
  tables/       generated deterministic tables now; LLM tables after the complete run
  figures/      generated figures after the complete corrected provider run
  README.md     this paper-specific status and evidence policy
```

Do not hand-edit generated numerical tables or figures. Their final build path
must be recorded in the release reproduction guide and verified from a clean
checkout.

## Release relationship

The paper is one component of the planned v0.1.0 archival bundle. See the
[`release/v0.1.0` candidate guide](../release/v0.1.0/README.md) and its
[`REPRODUCE.md`](../release/v0.1.0/REPRODUCE.md).

The directory name does not imply a released paper or software version. There
is no v0.1.0 tag, DOI, or final release date yet.

## Licensing

The repository code is MIT-licensed, while CARA and CARA-derived data are
subject to CC BY 4.0 attribution. The publication route and manuscript license
have not yet been selected, so there is deliberately no separate `paper/LICENSE`
grant at this stage. A paper-specific license and any venue-required notices are
a release gate; the root MIT license must not be assumed to cover the manuscript.

See [`DATA_LICENSE.md`](../DATA_LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
