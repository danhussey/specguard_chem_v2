# Invalid Results Notice

**Status:** active release blocker  
**Recorded:** 2026-07-16

The previously published CARA `LO_All` paper-50 artifacts in this repository
must not be used as scientific results.

## What failed

CARA's support and query split files identify rows by **position in the task
table**. The original importer instead set the dataframe index to the exported
`Unnamed: 0` column and resolved split positions as index labels. Those two
coordinate systems are not equivalent.

Under the incorrect lookup, 811 of 24,588 official split references were
silently dropped. Of the 23,777 rows that were returned, only 362 had a source
`Task ID` matching the split task key. The resulting decision cards could mix
compounds from different tasks, targets, and endpoints.

## Affected artifacts

All cards, prompts, provider responses, traces, scores, tables, figures,
dashboards, presentations, and manuscript claims derived from the old
paper-50 cards are affected. In particular, the following historical result
tags are retained only as immutable provenance and are superseded:

- `results/cara-lo-paper-50-semicomplete`
- `results/cara-lo-paper-50-selector-partial`
- `results/cara-lo-paper-50-openai-frontier-complete`
- `results/cara-lo-paper-50-frontier-resumption`
- `results/cara-lo-paper-50-direct-json-complete`
- `results/cara-lo-paper-50-dashboard-rich-tooltips`

Do not reuse old LLM caches for corrected claims: corrected cards produce
different requests even where a task identifier happens to look familiar.

## Corrected import audit

The corrected importer resolves split references positionally and checks the
source `Task ID` before accepting every row. Against the local CARA v1.0.1
archive, it resolves exactly:

- 24,588 of 24,588 official references;
- 5,000 support rows and 19,588 query/candidate rows;
- 100 assay tasks, each with 50 support rows;
- zero task-key mismatches;
- zero mixed-target tasks;
- zero mixed-endpoint tasks; and
- zero duplicate or support/query-overlapping compound IDs within a task.

These are data-integrity counts, not model-performance results. Corrected model
results will be reported only after the new artifacts are frozen, hashed, and
all reported systems are rerun.

## Release policy

The next archival release will include a corrected importer, regression tests,
an explicit exclusion report, separate system-input and scorer-outcome
artifacts, corrected runs, a canonical manifest, checksums, and a rewritten
paper. The old tags will not be moved or deleted.
