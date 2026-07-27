# 2026-07-28 Final Manuscript and Clean-Checkout Reproduction Gate

## Objective

Close the remaining submission gate after the university-feedback revision:
freeze the corrected 91-card evidence, make the report and package builds
repeatable, and reproduce the scientific and manuscript artifacts from a
genuinely clean checkout without a provider call.

## Scope

- Gate source commit: `82f92a6` (`Make report regeneration deterministic`).
- All 91 eligible CARA `LO_All` decision cards and separate scorer outcomes.
- Seven deterministic/oracle systems, six raw LLM conditions, and six
  deterministic post-hoc repaired views.
- The 19-system comparison, generated report/dashboard/tables/figures, main
  manuscript, supplement, wheel, and source distribution.
- No live provider access, credential use, tag, push, or publication action.

## Clean-checkout results

### Software and data

- A detached worktree was created at the gate commit with a fresh locked
  Python 3.12 environment.
- Ruff lint and format checks passed.
- All 72 tests passed.
- `uv lock --check` passed.
- The split validator resolved and validated all 91 cards against the separate
  scorer-only outcomes.

### Deterministic and QSAR systems

- All seven systems completed across 91 cards.
- Every regenerated candidate identifier and rank matched the frozen result.
- Score and comparison values matched within an absolute tolerance of
  `1e-12`; the maximum observed floating-point serialization difference was
  `3.55e-14`.
- This is numerical round-off only and does not change a candidate, rank,
  displayed result, interval, or conclusion.

### LLM replay and repair

- The exact 546-request export matched the committed request stream.
- Cache preflight found 546 cached responses, zero missing calls, zero
  incremental cost, and USD `58.95671601` of usage-derived historical cost.
- The historical six-request pilot estimate reproduced exactly: six missing
  calls, maximum input size 25,817 tokens, and USD `0.936717455` upper-bound
  cost. Its cache replay then reproduced all six raw traces and score
  directories byte-for-byte with zero live calls.
- The full matrix replay regenerated six 91-row raw traces and six 91-row
  repaired traces. Raw traces, raw scores, repaired traces, and repaired scores
  were byte-identical to the committed artifacts.
- Every repaired row was bound to the SHA256 of its source raw trace and
  recorded `provider_calls_added = 0`.
- Combining the replayed LLM summaries with the independently verified frozen
  baseline summaries reproduced all 13 canonical comparison files
  byte-for-byte. A comparison built wholly from regenerated baselines was also
  semantically identical across all 19 systems, with the same `3.55e-14`
  maximum numerical difference.

### Reports and PDFs

- The clean gate exposed a wall-clock timestamp in the report/dashboard and a
  stale frontier figure. `SOURCE_DATE_EPOCH=1784937600` now controls generated
  report timestamps, and the frontier artifact was refreshed.
- A second clean regeneration left every tracked report, dashboard, table, and
  figure byte-clean.
- Bundled Tectonic compiled the final main manuscript to eight A4 pages and the
  supplement to three A4 pages. Both use embedded fonts.
- Final PDF SHA256 values:
  - main: `ea773a95347e04a276bf3da5d46ab445a37ad2ff0a8883fddbf7dd508b025f1c`;
  - supplement:
    `c935236a57faa3cf601d9ce948f81beb39994cb95d1ad9ce00bf5d9e539d730e`.
- The supplement was byte-identical immediately. The main build exposed that
  the tracked PDF still embedded the previous frontier export; recompiling
  synchronized it with the refreshed figure. The changed page was visually
  inspected and remained unclipped and readable; the other seven pages were
  render-identical to the already reviewed manuscript.

### Package distributions

- The epoch-normalised wheel reproduced byte-for-byte from the clean checkout:
  `87ee2830655def0c999e14c199c9f68e1bdba34f8bed7311557d6b4e8cd9a820`.
- The bundled source archive SHA256 is
  `c8852809f4da6447fae96f9bf576dc833390bcce6fe4d794904697f75e30b6aa`.
  Setuptools preserves checkout-specific owner and modification-time metadata
  in that container, so the clean gate compared extracted member names and
  bytes; its payload was identical.
- The final wheel passed an independent fresh-environment smoke test:
  `sgchem --help`, `sgchem list-systems`, two-card fixture validation, installed
  version/import-path checks, and `pip check`.

## Submission outcome

The corrected manuscript and supplement are ready for the near-term university
revision. The gate supports the narrow result reported in the paper: on all 91
eligible cards, QSAR SVM retained a paired feasible-utility advantage of
`1.0027` over the strongest guarded LLM condition (95% bootstrap interval
`0.4049` to `1.6475`), and guarded results remain explicitly attributed to the
model-plus-deterministic-harness pipeline.

## Remaining archival administration

The clean scientific/manuscript gate is complete. A public archival release is
still intentionally pending the data and third-party license notices, the
bundle `MANIFEST.json` and `SHA256SUMS`, final DOI/release-date fields, annotated
release notes, tag, and publication. Those actions are not required to submit
the university revision and were not performed here.
