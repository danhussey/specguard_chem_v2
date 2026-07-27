# 0030 Bounded V1 Archival Release

## Objective

Publish a citable, versioned release of SpecGuard-Chem as a deliberately bounded
evaluation of LLM-backed compound-selection systems for a future automated-lab
decision primitive.

The release asks one narrow question: given observed assay evidence, a fixed
candidate pool, explicit eligibility rules, and a finite testing budget, which
candidate IDs should a system select for the next assay batch?

## Release Framing

- Treat constrained top-k compound selection as one auditable action inside a
  larger future design-make-test-analyse loop.
- Describe CARA as the public activity-data substrate and SpecGuard-Chem as the
  action-level evaluation harness built over it.
- Keep action validity and scientific utility separate, while making neither a
  substitute for the paper's broader action-quality question.
- Be explicit that the formal task is filter-predict-sort. Its simplicity is a
  deliberate unit-test boundary, not a claim to reproduce drug discovery.
- Do not claim synthesis planning, molecule generation, biological efficacy,
  ADMET, prospective validation, or a complete autonomous-laboratory workflow.
- Defer radical task redesign and biology-rich extensions until this release is
  frozen and tagged.

## Scope

- Correct and verify official CARA positional split resolution.
- Rebuild and quality-audit the frozen paper card artifact.
- Rerun deterministic baselines and regenerate their result artifacts.
- Export and inspect corrected LLM requests, then prepare a cost-gated rerun
  proposal for the minimum paper-facing LLM matrix.
- Rerun approved live LLM conditions only with explicit `--allow-external`, a
  saved cost estimate, cacheable responses, and hard run gates.
- Regenerate paper tables, figures, writeup, dashboard, and result summaries
  exclusively from corrected runs.
- Build an archival release bundle with provenance, checksums, cards, scorer
  data, traces or replay artifacts, environment locks, documentation, citation
  metadata, licenses, and release notes.
- Verify the bundle from a clean checkout before creating the release tag.

## Non-Goals

- No de novo molecule generation.
- No synthesis planning or reaction execution.
- No new biological, selectivity, ADMET, or prospective dataset track.
- No sequential closed-loop redesign before the bounded release.
- No reuse of numerical claims, traces, or response caches whose inputs derive
  from the invalid CARA import.
- No live provider call without explicit external-call authorization and cost
  gates.
- No task-selection or chemical-diversity redesign in v0.1.0; those extensions
  require a future benchmark version.

## Stop-Ship Conditions

- Any resolved support or query row does not match its named CARA task.
- Support/query rows are silently dropped or resolved by a non-positional key.
- Candidate outcomes are exposed in system-facing artifacts or prompts.
- The frozen-card checksum, schema/data version, or transform configuration is
  missing.
- A paper result cannot be traced to a corrected run, card artifact, and exact
  system/model configuration.
- Release documentation presents preliminary paper-50 results as corrected.
- Current-facing README, presentation, report, or figure assets retain invalid
  historical numerical claims without an explicit retirement notice.
- Tests, package build, artifact checksums, or clean-checkout reproduction fail.

## Work Packages

### 1. Data-integrity recovery

- [x] Replace label-based CARA split lookup with positional lookup.
- [x] Add regression tests with deliberately non-positional source IDs.
- [x] Fail loudly on out-of-range indices and task-ID mismatches.
- [x] Audit all official LO support/query rows against their task keys.
- [x] Record corrected import counts, exclusions, source version, and checksums.

### 2. Frozen benchmark rebuild

- [x] Predeclare the paper card selection policy, support size, constraints, and
  budget.
- [x] Add explicit card-schema, benchmark, and data-release versions.
- [x] Make the resolved constraints configuration and its hash explicit.
- [x] Rebuild cards without overwriting historical artifacts silently.
- [x] Validate task coherence, endpoint metadata, duplicates, support/query
  overlap, feasible counts, and hidden-label separation.
- [x] Freeze system-facing inputs separately from scorer-only outcomes.

### 3. Corrected evidence run

- [x] Run oracle, random, rules, similarity, and QSAR baselines first.
- [x] Confirm task difficulty and oracle headroom before spending on LLM calls.
- [x] Export corrected LLM requests and inspect prompt sizes and redaction.
- [x] Estimate the minimum live rerun cost and define hard call/cost limits.
- [x] Enforce one provider attempt per request and preserve strict raw-response,
  model-provenance, usage, latency, and cost evidence.
- [x] Correct best-raw-system selection and raw-versus-baseline paired metrics.
- [x] Run the explicitly approved fixed six-request pilot and persist audited
  replay caches, raw traces, operational evidence, and zero-call repaired views.
- [x] Reproduce the corrected raw import, frozen split artifacts, deterministic
  suite, and cache-only pilot analysis from a fresh worktree.
- [x] Run the residual 540-call matrix only after separate explicit approval.
  Approval was received on 2026-07-25. A provider-credit interruption stopped
  Anthropic safely, then the same content-addressed cache resumed to 546/546
  completed responses after credits were restored.
- [x] Recompute paired uncertainty, raw/final attribution, robustness, and cost.
- [x] Build one canonical complete run manifest rather than relying on resumed
  per-command manifests.
- [x] Append every meaningful run to `docs/RUN_LEDGER.md`.

### 4. Paper and archival bundle

- [x] Write the bounded automated-lab action framing into the project brief,
  benchmark card, README, and paper/writeup.
- [x] Replace every preliminary number and figure with corrected evidence.
- [x] Bring the corrected full-matrix manuscript, supplement, and compiled PDFs
  onto this branch.
- [x] Add a central invalid-results notice that supersedes the six historical
  `results/cara-lo-paper-50-*` tags without deleting or moving them.
- [ ] Add `DATA_LICENSE.md` and `THIRD_PARTY_NOTICES.md` distinguishing MIT code
  from CC BY 4.0 CARA/CARA-derived data and the chosen manuscript license.
- [x] Include methods, limitations, model reporting, data provenance, citation
  metadata, and an exact reproduction guide.
- [ ] Generate a manifest containing file sizes and SHA256 checksums.
- [x] Include the committed environment lock and package distributions.
- [x] Verify the current candidate's data, traces, scores, reports, manuscript,
  supplement, and package distributions from a clean checkout.
- [ ] Repeat manifest-bound verification after the pending license notices and
  final bundle checksums are added.

### 5. Version and tag

- [x] Select the release version after the corrected artifact schema is frozen;
  default candidate: `v0.1.0` for the first archival research release.
- [x] Ensure package, citation, benchmark, data, schema, and release metadata
  agree on the version.
- [ ] Finalize the release date and DOI fields once the archive exists.
- [ ] Create annotated release notes that retire invalid historical results.
- [ ] Create the annotated Git tag only after all stop-ship gates pass.
- [ ] Push or publish the tag/release only as an explicit release action.

## Required Release Contents

- Source code and committed lockfiles.
- Corrected frozen system-input cards.
- Scorer-only labels or evaluator artifact with an explicit visibility policy.
- Card-construction configuration, source provenance, exclusion report, and
  checksums.
- Exact model/provider snapshots, prompts, generation settings, costs, and run
  timestamps for reported LLM conditions.
- Reproducible traces or legally shareable replay artifacts.
- Per-card scores, aggregate tables, uncertainty estimates, and figures.
- Paper or archival technical report and supplementary methods.
- `README.md`, `BENCHMARK_CARD.md`, `DATA_CARD.md`, `CITATION.cff`, `LICENSE`,
  data/third-party license notices, and release notes.
- A machine-readable manifest and `SHA256SUMS` for the release bundle.

## Validation

```bash
uv lock --check
uv sync --locked --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
uv run sgchem validate-cards <corrected-system-input-cards>
uv build
```

Additional release-specific validation commands will be recorded with exact
paths after the corrected artifact names are frozen.

## Acceptance Criteria

- The paper/writeup makes a narrow, evidence-backed claim about one bounded
  compound-selection action relevant to future automated laboratories.
- All reported results derive from task-coherent, positionally resolved CARA
  rows and corrected frozen cards.
- A reviewer can trace each number from paper figure to table, per-card score,
  run trace, card checksum, and source transform.
- The complete archival bundle reproduces in a clean environment without live
  calls except where an explicitly documented replay limitation applies.
- The repository, paper, citation metadata, bundle, and annotated tag share one
  release version.
