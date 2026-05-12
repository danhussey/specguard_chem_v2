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

## 2026-05-11 paper-50 direct-JSON frontier matrix

- Artifacts: `runs/cara_lo_paper_50_selector_matrix/`,
  `paper/tables/cara_lo_paper_50_selector_completed/`,
  `paper/figures/cara_lo_paper_50_selector_completed/`,
  `plans/logs/2026-05-11-0011-reasoning-budget-fairness-selector-partial.md`.
- Scope: same 50 frozen CARA LO cards and full candidate pools; direct-JSON
  prompt profile; OpenAI frontier with low reasoning fallback; DeepSeek frontier
  with thinking disabled; Anthropic direct-JSON preflight only.
- Question: test whether the high-reasoning failures were caused by the
  interface rather than the prioritisation task.
- Status: partial. DeepSeek completed all four systems. OpenAI completed
  `bare_llm` and `llm_validator`, then hit API quota during `llm_tools`.
  Anthropic preflight returned JSON, but the full run hit overload then low API
  credit.
- Headline: OpenAI direct-JSON returned valid, useful raw outputs:
  `bare_llm__openai_frontier_selector` feasible utility `75.7812`; raw/final
  `llm_validator__openai_frontier_selector` `76.7580`/`78.1884`, repaired-from-
  empty rate `0.0`. DeepSeek direct-JSON completed but was weaker; best DeepSeek
  final selector row was `67.6213`.
- Surprise / interpretation: direct-JSON substantially changed OpenAI behavior.
  The original high-reasoning failure should be described as an interface and
  output-budget failure mode.
- Follow-up: rename selector artifacts/configs to direct-JSON terminology, add
  cost estimation/budget gates, then resume incomplete OpenAI and Anthropic rows
  only after estimated cost is acceptable.

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
