# 2026-07-28 University Feedback Revision and Repair Attribution

## Objective

Address the 24 July 2026 university feedback on manuscript v0.5 without
repairing or reusing the invalid historical paper-50 evidence.

## Evidence boundary

The supplied 22-page PDF was extracted and visually reviewed. Its data,
methods, results, figures, and conclusion rely on the retired
`cara_lo_paper_50` build and therefore require numerical replacement rather
than prose-only editing.

The revision uses:

- the corrected 91-card v0.1.0 system-input and scorer artifacts in this branch;
- the deterministic baseline results in this branch; and
- the completed 546-response corrected provider matrix in the read-only sibling
  working tree `/Users/danielhussey/.codex/worktrees/1a6b/specguard_chem_v2`.

The provider matrix is complete and internally audited but remains in a large
uncommitted working state. Its values are identified as non-archival until
frozen and reproduced from a clean checkout.

## Changes

- Added `paper/manuscript/UNIVERSITY_FEEDBACK_REVISION_PACK.md` with:
  - a point-by-point response to the university;
  - paste-ready abstract, introduction, methods, results, discussion,
    limitations, and conclusion text;
  - plain definitions of decision card, guarded, and feasible utility;
  - the corrected all-eligible-task inclusion policy;
  - exact constraint, QSAR, LLM, and bootstrap specifications;
  - a paired within-card explanation of feasible-utility aggregation;
  - corrected headline results and explicit post-selection caveats; and
  - a submission and evidence-provenance checklist.
- Added `paper/manuscript/revision_repair_attribution.csv`.
- Added ChemLLMBench, ChemBench, LLM4SD, and Lipinski references to
  `paper/manuscript/references.bib`.

## Repair-attribution audit

All 546 corrected raw/repaired record pairs were checked. Every final action
contained ten unique IDs and added zero provider calls. The stored repair
records were independently re-applied against the corrected cards by a
separate audit and matched exactly.

For the best OpenAI basic condition, repair applied to 19/91 contract-invalid
actions, changed shortlist membership on 10/91 cards, and supplied 14/910 final
candidate identities (1.54%). Fallback supplied 15/910 OpenAI-descriptor,
252/910 Anthropic-basic, 229/910 Anthropic-descriptor, 534/910 DeepSeek-basic,
and 355/910 DeepSeek-descriptor positions.

The distinction between card repair rate and fallback-supplied shortlist
content is now explicit. Anthropic and DeepSeek guarded results are described
as model-plus-harness outcomes rather than underlying-model performance.

## Corrected headline

QSAR SVM reached mean feasible utility 74.9664. The best repaired LLM view,
OpenAI GPT-5.5 basic plus deterministic post-hoc repair, reached 73.9637 from a
raw response stream at 72.9664. The paired QSAR-minus-LLM difference was 1.0027
with a 95% percentile-bootstrap interval of 0.4049 to 1.6475.

## Validation

- Manuscript generated-result check: passed.
- Full offline test suite: 60 passed.
- `git diff --check`: passed.
- Reference-key and BibTeX brace checks: passed.
- Independent recount of all six repair-attribution CSV rows against all 546
  corrected trace pairs: passed.
- No live provider call, external write, tag, push, or publication action.

## Decision and follow-up

Use the revision pack to rebuild the university report; do not patch the v0.5
numbers. Before submission, freeze and merge the completed corrected matrix,
persist the repair-slot metric in the report generator, regenerate all tables
and figures, and reproduce the manuscript from a clean checkout.
