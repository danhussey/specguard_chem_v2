# 0031 University Feedback and Corrected Report Revision

## Objective

Address the 24 July 2026 university feedback on manuscript v0.5 without
repeating the invalid historical paper-50 evidence. Produce evidence-backed,
paste-ready revisions based on the corrected 91-card v0.1.0 artifacts and make
the remaining live-result boundary explicit.

## Scope

- Review the submitted PDF against the repository's later positional-integrity
  correction and corrected v0.1.0 artifacts.
- Expand and sharpen the literature positioning for LLMs in drug discovery and
  the relationship to CARA.
- Define guarded systems, decision cards, and feasible utility in plain language.
- Replace the invalid purposive paper-50 sample with the corrected policy:
  consider all 100 official LO_All tasks and include all 91 with at least ten
  feasible candidates.
- Add reproducible constraint, QSAR, LLM, and paired-bootstrap details.
- Explain why card-level feasible utility can be aggregated despite differing
  assay endpoints and scales.
- Define and calculate shortlist-slot repair attribution from the completed
  corrected 91-card full matrix, while keeping its uncommitted archival status
  explicit.
- Produce a point-by-point response and paste-ready manuscript replacement text.

## Non-Goals

- Do not make new live LLM calls.
- Do not reuse any paper-50 card, score, interval, repair statistic, table,
  figure, or model-comparison claim.
- Do not present the one-card corrected pilot as a model leaderboard.
- Do not broaden claims to prospective medicinal chemistry, efficacy, safety, or
  general drug-discovery performance.
- Do not start the paused ChEMBL36 expansion.

## Planned Artifacts

- `paper/manuscript/UNIVERSITY_FEEDBACK_REVISION_PACK.md`
- `paper/manuscript/revision_repair_attribution.csv`
- Literature additions in `paper/manuscript/references.bib` where needed.
- A dated execution log.

## Validation

```bash
uv run python paper/manuscript/generate_results.py --check
uv run pytest
```

## Acceptance Criteria

- Every feedback point is mapped to a concrete revision.
- All new quantitative claims are traceable to local artifacts or cited
  literature.
- The invalidation of manuscript v0.5's numerical results is prominent and no
  historical paper-50 number is recommended for reuse.
- Repair is described as deterministic fallback behavior, not model behavior.
- The revised wording explicitly limits inference to the corrected retrospective
  benchmark and distinguishes verified completed-run values from an archival
  release, which still requires the full matrix to be frozen and committed.
- No TODO/editorial comments remain in the paste-ready text.

## Outcome

Completed on 28 July 2026. The revision pack maps every university comment to a
specific change, supplies paste-ready prose, replaces the invalid historical
paper-50 results with corrected 91-card values, and adds shortlist-level repair
attribution. The repaired-record audit covered all 546 corrected records and
matched the stored deterministic post-hoc outputs. No live provider call was
made.

The full corrected matrix remains uncommitted in its source working tree, so
the pack treats its verified numerical results as submission-ready only after
that state is frozen, merged, and reproduced from a clean checkout.
