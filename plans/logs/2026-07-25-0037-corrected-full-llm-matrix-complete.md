# 2026-07-25 Corrected Full LLM Matrix: Completion and Analysis

## Objective

Complete the explicitly approved corrected v0.1.0 provider matrix after the
Anthropic credit interruption, then regenerate and verify the full scientific
analysis without adding a task-selection or chemical-diversity objective.

## Authorization and execution boundary

The approved outer boundary remained the previously reviewed residual
540-call / USD 119 / 175,000 estimated input-token gates, with the staged pilot
and residual ceilings below USD 120 in aggregate. Successful responses were
content-addressed and resumable; `--force` was never used and SDK retries
remained disabled.

Before the Anthropic resume, a fresh estimate reported:

- 182 Anthropic requests in the two interfaces;
- 21 cached responses and 161 missing calls;
- maximum missing input estimate 158,265 tokens; and
- USD 44.010805 conservative remaining cost.

The resumed Anthropic slice used tighter USD 45 and 161-call gates. After the
remaining responses completed, the complete three-provider command was rerun
against the shared cache with zero incremental cost and zero live-call gates.
That pass skipped all six complete traces, rescored them, and wrote the
canonical six-condition `matrix/manifest.json`.

## Completeness and provenance audit

The final matrix contains:

- 546 content-addressed response-cache records;
- six raw traces with 91 unique frozen task records each;
- six post-hoc-repaired traces with the same 91 tasks each;
- exactly one recorded provider attempt for every successful raw response;
- zero provider calls added by every repaired record;
- exact request-hash agreement with the 546-row frozen request export;
- configured/returned model, response ID, finish reason, usage, latency,
  request hash, and retained response content for every raw record; and
- 100% usage, latency, and pricing-derived cost coverage.

The canonical comparison contains seven deterministic/oracle systems, six raw
LLM systems, and six repaired model-plus-harness systems: 19 rows in total.
It includes the primary leaderboard, oracle controls, metric winners,
raw/final and representation ablations, 2,000-resample paired task-level
bootstrap deltas, card diagnostics, and the failure taxonomy.

## Usage-derived cost

Provider-reported token usage was multiplied by the frozen token-pricing
configuration. These are usage-derived costs, not invoice records.

| Condition | Usage-derived cost (USD) |
| --- | ---: |
| OpenAI bare | 11.623030000 |
| OpenAI descriptors | 14.857605000 |
| Anthropic bare | 13.463460000 |
| Anthropic descriptors | 17.098340000 |
| DeepSeek bare | 0.820817334 |
| DeepSeek descriptors | 1.093463676 |
| **Total** | **58.956716010** |

The six unique live conditions consumed 14,780,538 total tokens. Repaired rows
repeat their source condition's operational attribution and are not additional
purchases.

## Scientific results

The hidden-outcome oracle reached mean feasible utility 79.5626. Excluding that
control, the leading systems were QSAR SVM at 74.9664, QSAR random forest at
74.9580, and QSAR gradient boosting at 74.7499. SVM and random forest were not
meaningfully separated: SVM minus RF was 0.0084 utility with a 95% paired
bootstrap interval of -0.3755 to 0.3661.

The best final LLM view was OpenAI bare plus deterministic post-hoc repair:

- raw utility 72.9664 and raw whole-action validity 72/91 (79.12%);
- repaired model-plus-harness utility 73.9637, NDCG@10 0.9288, and final
  validity 91/91;
- repair on 19/91 actions (20.88%); and
- USD 11.62303 usage-derived cost.

Best QSAR minus best repaired LLM was 1.0027 utility points, with a paired 95%
interval of 0.4049 to 1.6475. The corresponding NDCG difference was 0.00868
with interval 0.00104 to 0.01648. The corrected benchmark therefore supports a
QSAR-family lead, not added decision value from the tested LLM conditions.

The best repaired LLM exceeded the similarity baseline by 0.6754 utility, but
the paired interval (-0.1033 to 1.4702) included zero. The best raw LLM was
0.3218 below similarity, with interval -1.4519 to 0.7129, and its whole-action
validity was 20.88 percentage points lower.

Descriptor enrichment was provider-dependent rather than a general gain.
Tools-minus-bare raw utility was -0.1618 for OpenAI, +1.4168 for Anthropic, and
+14.0202 for DeepSeek; only DeepSeek's interval excluded zero. After repair,
the deltas were -0.0751, -0.0574, and +1.5464 respectively. The best-performing
OpenAI condition did not improve with descriptor enrichment.

Repair made every final row executable but dominated the Anthropic and
DeepSeek guarded results: 75.82% to 91.21% of their actions required repair,
versus 20.88% to 25.27% for OpenAI. Those repaired utilities characterize the
model-plus-deterministic-harness system and are not unaided model gains.

## Generated artifacts

- Canonical raw/repaired matrix and manifest:
  `release/v0.1.0/experiments/llm/matrix/`
- Nineteen-system comparison:
  `release/v0.1.0/experiments/llm/comparison/`
- Human-readable summary and self-contained dashboard:
  `paper/RESULTS_SUMMARY.md` and `paper/RESULTS_DASHBOARD.html`
- Corrected aggregate and card-level figures:
  `paper/figures/v0.1.0/`
- Evidence-gated result macros and deterministic table:
  `paper/manuscript/generated_results.tex` and
  `paper/tables/v0.1.0/deterministic_baseline_rows.tex`
- Revised compiled manuscript and supplement:
  `paper/manuscript/main.pdf` and `paper/manuscript/supplement.pdf`

The report generator was corrected so repaired systems retain their condition
profile while displaying the mandatory `+ post-hoc repair` qualifier. The
frontier figure was also revised to show raw-to-repaired trajectories without
overlapping full model labels.

## Final validation

- `pytest -p no:cacheprovider`: 60 passed.
- Ruff lint and format checks: passed across `src`, `tests`, and the manuscript
  generator.
- Frozen card/scorer validation: 91 cards passed.
- Cost estimator: 546 cached or completed, zero missing, zero incremental cost.
- Independent integrity recount: 546 caches, 546 raw rows, 546 repaired rows,
  six manifest runs, 19 comparison systems, USD 58.95671601, and 14,780,538
  tokens.
- Manuscript generator write/check gate: passed.
- Bundled Tectonic: compiled the seven-page manuscript and two-page supplement.
- PDF render QA: all nine pages inspected without clipping, overlap, missing
  references, or placeholder text.
- `uv lock --check`: passed.
- Source distribution and wheel build: passed.
- `git diff --check`: passed.

## Decision and follow-up

The corrected full analysis is complete. Task-selection and chemical-diversity
changes remain explicitly deferred to a future benchmark version. The
remaining v0.1.0 archival work is release administration rather than analysis:
finalize manuscript/licensing metadata, generate final bundle checksums,
reproduce from a clean checkout, and create/publish a tag only with separate
authorization.
