# Run Ledger

This is the concise laboratory log for meaningful runs and experiments. Keep
execution detail in `plans/logs/`; use this file to compare what was run, why it
was run, what happened, and what to do next.

## Entry Template

```text
## YYYY-MM-DD short-run-name

- Artifacts: paths to traces, tables, figures, reports.
- Scope: cards, systems, providers, interface profile.
- Question: what this run was testing.
- Status: complete, partial, blocked, failed.
- Headline: one or two quantitative takeaways.
- Surprise / interpretation: what changed our understanding.
- Follow-up: concrete next action.
```

## 2026-05-11 paper-50 baselines

- Artifacts: `runs/cara_lo_paper_50_baselines/`,
  `paper/tables/cara_lo_paper_50_completed/`.
- Scope: 50 frozen CARA LO cards; oracle, random, rules, similarity, QSAR RF,
  QSAR GBT, QSAR SVM.
- Question: establish non-LLM lower bounds, chemistry baselines, and oracle
  headroom before interpreting LLM systems.
- Status: complete.
- Headline: QSAR SVM was the best deployable baseline at feasible utility
  `81.3823`; oracle upper bound was `89.0217`; similarity-to-best-active was
  `73.6032`; rules-only was `66.0431`.
- Surprise / interpretation: simple specialised baselines are strong; the paper
  should not frame LLMs as the default winner.
- Follow-up: keep QSAR and similarity as primary comparators in every LLM table.

## 2026-05-11 paper-50 fast LLM matrix

- Artifacts: `runs/cara_lo_paper_50_llm_matrix/`,
  `paper/tables/cara_lo_paper_50_fast_complete/`,
  `paper/figures/cara_lo_paper_50_fast_complete/`.
- Scope: 50 frozen CARA LO cards; fast model conditions for OpenAI, Anthropic,
  and DeepSeek; four LLM system variants.
- Question: test whether cheaper/faster provider models can beat simple
  non-language baselines under the full-pool interface.
- Status: complete.
- Headline: best fast LLM rows clustered around feasible utility `67-68`, below
  similarity (`73.6032`) and QSAR (`80+`).
- Surprise / interpretation: fast LLMs mostly added compliance/system behavior,
  not superior prioritisation utility.
- Follow-up: use fast models for smoke and budget-gated pilots, not as evidence
  that LLMs beat QSAR.

## 2026-05-11 paper-50 original frontier matrix

- Artifacts: `runs/cara_lo_paper_50_llm_matrix/`,
  `paper/tables/cara_lo_paper_50_completed/`,
  `paper/figures/cara_lo_paper_50_completed/`.
- Scope: 50 frozen CARA LO cards; original frontier/high-reasoning provider
  configs where available.
- Question: test the original frontier interface before adding raw-vs-repaired
  accounting.
- Status: partial/complete mixed by provider.
- Headline: Anthropic frontier was the strongest historical LLM condition
  (`llm_tools_validator__anthropic_frontier` feasible utility `73.9792`), around
  similarity baseline but below QSAR. OpenAI high-reasoning failed to produce
  useful visible JSON in raw non-validator paths; validator-assisted OpenAI
  collapsed to rules-like fallback behavior.
- Surprise / interpretation: the important result was an interface failure mode,
  not a clean model-capability comparison.
- Follow-up: do not overinterpret high-reasoning empty-output failures as
  chemistry reasoning failures; separate raw model output from guarded repair.

## 2026-05-12 paper-50 direct-JSON frontier matrix

- Artifacts: `runs/cara_lo_paper_50_selector_matrix/`,
  `paper/tables/cara_lo_paper_50_selector_completed/`,
  `paper/figures/cara_lo_paper_50_selector_completed/`,
  `plans/logs/2026-05-12-0013-direct-json-matrix-completion.md`.
- Scope: same 50 frozen CARA LO cards and full candidate pools; direct-JSON
  prompt profile; OpenAI frontier with low reasoning fallback; DeepSeek frontier
  with thinking disabled; Anthropic frontier without extended thinking.
- Question: test whether the high-reasoning failures were caused by the
  interface rather than the prioritisation task.
- Status: complete. All 12 provider/system direct-JSON traces have 50 rows.
- Headline: OpenAI direct-JSON was the strongest LLM condition but still below
  QSAR. Best rows: `llm_validator__openai_frontier_selector` final/raw
  `78.1884`/`76.7580`; `llm_tools_validator__openai_frontier_selector`
  final/raw `77.6875`/`77.2091`; `llm_tools__openai_frontier_selector`
  raw/final `77.1728`. Anthropic direct-JSON guarded rows reached `74.4707`
  final utility but relied heavily on repair. DeepSeek direct-JSON completed but
  was weaker; best DeepSeek final selector row was `67.6213`.
- Surprise / interpretation: direct-JSON substantially changed OpenAI behavior.
  The original high-reasoning failure should be described as an interface and
  output-budget failure mode. Validator repair materially changes Anthropic and
  DeepSeek final scores, so raw metrics are essential.
- Follow-up: rename selector artifacts/configs to direct-JSON terminology and
  design a compressed/staged interface before any high-reasoning full run.

## 2026-05-12 LO paper-50 result consolidation

- Artifacts: `paper/tables/cara_lo_paper_50_direct_json_completed/`,
  `paper/figures/cara_lo_paper_50_direct_json_completed/`,
  `paper/RESULTS_SUMMARY.md`, `paper/RESULTS_DASHBOARD.html`,
  `paper/CARA_LO_PAPER_50_RESULTS.md`.
- Scope: no new experiment. Reused the completed LO paper-50 baselines,
  historical LLM matrix, and direct-JSON matrix summaries.
- Question: make the current LO evidence paper-readable without scope creep and
  without ambiguous `frontier` / `selector` labels in reader-facing outputs.
- Status: complete consolidation artifact.
- Headline: paper-facing labels now show provider, exact model name, and
  reasoning/thinking profile. QSAR is described as per-card support-set training
  and remains the strongest deployable system family in the consolidated table.
- Surprise / interpretation: the paper story is cleaner when framed as
  compliance-plus-utility evaluation rather than as an LLM leaderboard. The
  strongest LLM rows are useful but still below all three QSAR variants.
- Follow-up: keep VS, compressed inputs, and high-reasoning-compatible
  interfaces as separate future work rather than mixing them into the LO result.

## 2026-05-12 LO paper-50 statistical diagnostics

- Artifacts: `paper/tables/cara_lo_paper_50_direct_json_completed/`,
  `paper/figures/cara_lo_paper_50_direct_json_completed/`,
  `paper/RESULTS_SUMMARY.md`.
- Scope: no new experiment. Reused existing score summaries, per-card scores,
  and failure-taxonomy files.
- Question: strengthen the LO result with paired card-level comparisons,
  card-level plots, and consolidated failure summaries.
- Status: complete reporting/statistics extension.
- Headline: paired bootstrap over the same 50 cards shows `qsar_svm` exceeded
  the best final LLM row by `3.194` feasible-utility points, 95% paired interval
  `1.942` to `4.692`. Oracle headroom above `qsar_svm` was `7.639`.
- Surprise / interpretation: the aggregate QSAR-over-LLM result persists under
  paired card-level resampling; failure taxonomy shows many raw/non-validator
  LLM failures are constraint/contract failures rather than just weak utility.
- Follow-up: use the key paired-delta table for paper prose; keep the full
  pairwise delta table as an audit artifact.

## Current Standing Interpretation

- Raw metrics measure model behavior.
- Final metrics for `*_validator` systems measure guarded system behavior.
- Validator checking is not an oracle: it checks schema, IDs, duplicates,
  support-set exclusion, and RDKit/property/alert constraints. It does not use
  hidden activity values.
- Repair fallback is deterministic harness behavior and must be reported
  separately.
- Provider quota, credit, overload, and timeout failures are run-feasibility
  failures, not scored model-performance outcomes.
