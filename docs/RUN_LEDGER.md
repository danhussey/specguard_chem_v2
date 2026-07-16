# Run Ledger

> **Historical validity notice (2026-07-16).** Entries before the CARA
> positional-integrity recovery are preserved as an execution history only.
> Their paper-50 cards, results, tables, figures, and model comparisons are
> invalid as scientific evidence because the old importer interpreted official
> split positions as data-frame labels. Current evidence must use the 91-card
> split artifacts in `data/releases/v0.1.0/` and runs in
> `release/v0.1.0/`.

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

## 2026-05-21 ChEMBL36 expansion uplift audit

- Artifacts: external scratch volume `specguard_chembl36/`; key outputs
  `derived/chembl36_sql_prefilter_summary.json`,
  `derived/chembl36_sql_prefilter_tasks.json`,
  `derived/chembl36_full_uplift_summary.json`,
  `derived/chembl36_full_uplift_results.csv`, and
  `derived/chembl36_full_uplift_results.json`.
- Scope: official ChEMBL36 SQLite archive from EBI
  `chembl_36_sqlite.tar.gz`; archive bytes `5611751319`, archive SHA256
  `b25820eef0f0481ad7712bdf4bac3b45f354e3cbacb76be1fdbf4205d6b48fb9`;
  extracted SQLite DB bytes `29739835392`. Compared ChEMBL36 assay/type keys
  against the local CARA archive test/support/query split keys and the current
  50-card paper set.
- Question: estimate the dataset uplift available from a current ChEMBL-derived
  SpecGuard card expansion under CARA-style assay/type quality filters.
- Status: complete audit pass. SQL prefilter streamed ChEMBL36 activities with
  non-null pChEMBL, canonical SMILES, ChEMBL molecule IDs, single-protein
  targets with sequence, molecular weight at most `1000`, at least `100`
  distinct molecules per assay/type, activity range above `2`, and more than
  `10` unique pChEMBL values. The second pass median-merged molecule labels,
  used deterministic support/candidate partitioning, applied a ChEMBL-property
  proxy for SpecGuard constraints, and classified LO/VS by Morgan/Tanimoto
  median similarity.
- Headline: `2071` median-merged ChEMBL36 assay/type groups pass the audit's
  CARA-style quality filters. `1835` groups pass the k=10 SpecGuard viability
  proxy. Relative to CARA test/support/query keys only, `1554` viable groups
  are additional; relative to all CARA archive train-or-test keys checked,
  `1003` viable groups are additional. Restricting endpoint types to CARA's
  stated examples (`IC50`, `Ki`, `Kd`, `EC50`, `Potency`) yields `1760`
  viable groups, `955` additional relative to all CARA archive train-or-test
  keys. Under that stricter endpoint set, additional groups split into `887`
  LO-like and `68` VS-like groups by the similarity rule, with `142` additional
  groups having document-year evidence from `2022` or later.
- Surprise / interpretation: the ChEMBL36 expansion is not a marginal uplift
  over the current 50-card paper set, but the earlier "novel relative to CARA"
  framing was too broad if CARA training assay keys are treated as part of the
  CARA archive. The current counts are audit counts, not finalized card counts,
  because feasibility used ChEMBL `full_mwt`/`alogp` as a proxy, large-group
  similarity used a deterministic 500-molecule sample, and the audit has not
  recreated CARA's protein-cluster-based test-assay selection protocol.
- Decision / follow-up: pause the ChEMBL36 expansion for the current manuscript.
  The most conservative denominator is the full CARA archive train-or-test task
  key universe (`90737` keys), where the stricter ChEMBL36 endpoint-restricted
  uplift is `955 / 90737 = 1.05%`. That is useful feasibility evidence but not
  enough to justify adding a new ChEMBL36 benchmark construction and experiment
  track to the paper. If revisited later, build a reproducible ChEMBL36 card
  generator with RDKit descriptor recomputation and CARA-like protein-cluster
  held-out selection before making benchmark claims.

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

## 2026-07-16 CARA LO positional-integrity recovery and v0.1.0 freeze

- Artifacts: `data/releases/v0.1.0/system_input_cards.jsonl`,
  `data/releases/v0.1.0/scorer_outcomes.jsonl`,
  `data/releases/v0.1.0/system_input_cards.meta.json`, and
  `data/releases/v0.1.0/system_input_cards.audit.json`.
- Scope: all 100 official CARA `LO_All` task keys; split indices resolved as
  source-table row positions and verified against each named task; budget
  `k=10`, support size `50`, explicit default constraints.
- Question: recover a task-coherent, label-separated artifact after discovering
  that the historical importer treated positional split indices as labels.
- Status: complete. Ninety-one tasks meet the prespecified requirement of at
  least ten feasible candidates; nine exclusions are recorded explicitly.
- Headline: the corrected system-input artifact contains 91 cards (candidate
  pool 52--967; feasible pool 12--579). Its SHA256 is
  `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e`;
  the scorer-only outcome artifact SHA256 is
  `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4`.
- Surprise / interpretation: all corrected tasks are biologically coherent at
  the CARA target/endpoint level, but the old paper-50 results are not reusable.
  The release must treat those historical outputs as invalid rather than as a
  comparable earlier benchmark version.
- Follow-up: report only corrected v0.1.0 evidence and preserve the split-input
  visibility contract in every execution path.

## 2026-07-16 corrected v0.1.0 deterministic baselines

- Artifacts: `release/v0.1.0/experiments/baselines/`.
- Scope: all 91 corrected cards; oracle, random-valid, rules-only,
  similarity-to-best-active, QSAR RF, QSAR GBT, and QSAR SVM.
- Question: confirm that the corrected task has measurable scientific headroom
  and separates useful ranking systems before any new provider spend.
- Status: complete and independently rerun; traces and score artifacts were
  byte-identical, except for expected run-manifest time/path fields.
- Headline: oracle feasible utility was `79.5626`; QSAR SVM `74.9664`, QSAR RF
  `74.9580`, similarity `73.2882`, random-valid `68.4688`, and rules-only
  `66.9215`. All deterministic systems had whole-action validity and
  valid-selection fraction `1.0`; oracle-to-best deployable headroom was
  `4.5963` utility points.
- Surprise / interpretation: constraints alone do not solve the task. The gap
  from rules/random through similarity and QSAR to oracle supports treating it
  as a nontrivial action-quality benchmark, while keeping CARA visible as the
  underlying activity-data substrate.
- Follow-up: use these as the corrected fixed comparators for the minimum LLM
  matrix and manuscript; do not promote them as final cross-model results until
  the approved LLM runs are complete.

## 2026-07-16 v0.1.0 exact LLM request and cost export

- Artifacts: `release/v0.1.0/experiments/llm/exact_requests.jsonl` and
  `release/v0.1.0/experiments/llm/pre_run_cost_estimate.json`.
- Scope: 91 cards, two interfaces (`bare_llm`, `llm_tools`), and three pinned or
  date-qualified model conditions: GPT-5.5 `2026-04-23`, Claude Opus 4.8, and
  DeepSeek V4 Pro as checked on 2026-07-16.
- Question: freeze the smallest informative provider matrix and establish a
  conservative spend gate without changing the task or making external calls.
- Status: request/cost export complete; live experiment not started and no
  provider calls or costs incurred.
- Headline: 546 planned calls, zero cached/completed, maximum conservative input
  estimate `158274` tokens, and upper-bound incremental estimate `$106.0594`.
  Request SHA256 is
  `50e518893b19d4a7efd64c62e08ab94d610815f8fb7518c9af4b64ff40b6f6c5`;
  cost-estimate SHA256 is
  `d11ce35da68e5082153be4bc57c027915ccb76cf8fb19b02e5adf767b2ab525d`.
- Surprise / interpretation: the full candidate-pool interface remains large
  but fits all selected providers' documented context windows. Separating the
  two raw interfaces yields a cleaner experiment than paying for prompt-level
  validator variants; deterministic repair can be evaluated post hoc on the
  same responses. Pre-run QA also made the CARA pChEMBL scale and
  higher-is-better objective explicit in every card and prompt, avoiding a
  confound between pChEMBL and raw IC50/Ki endpoint direction.
- Follow-up: post-hoc repair attribution is now implemented and tested; obtain
  explicit authorization before a one-card pilot or any full
  `--allow-external` run.

## 2026-07-16 v0.1.0 offline release preflight

- Artifacts: `paper/manuscript/main.pdf`,
  `paper/manuscript/supplement.pdf`, and `release/v0.1.0/software/`.
- Scope: exact one-card pilot specification, full offline test/lint/schema
  validation, manuscript compilation and visual inspection, and Python package
  build/smoke installation.
- Question: determine whether the bounded release is internally reproducible
  and ready to pause at the explicit provider-call boundary.
- Status: offline preflight complete; no provider call, final manifest, tag, or
  publication action occurred.
- Headline: 44 tests passed; both 91-row JSONL artifacts passed executable and
  JSON Schema validation; the six-page manuscript and two-page supplement
  compiled cleanly; the wheel and source distribution built, and the wheel
  passed isolated Python 3.12 CLI validation. The fixed six-request pilot has a
  USD 0.936717455 upper-bound estimate and 25,817-token maximum input estimate.
- Surprise / interpretation: an explicit task selector and shared cache were
  necessary to make the pilot scientifically reproducible and prevent its six
  requests from being purchased again during the full matrix.
- Follow-up: obtain explicit authorization before the six-call pilot, confirm
  the manuscript license/authorship route, then complete provider results,
  final checksums, clean-checkout verification, and the annotated tag.

## 2026-07-16 fixed one-card LLM pilot

- Artifacts: `release/v0.1.0/experiments/llm/pilot/`,
  `release/v0.1.0/experiments/llm/matrix/cache/`, and
  `release/v0.1.0/experiments/llm/post_pilot_cost_estimate.json`.
- Scope: exact task `CARA_LO_CHEMBL1006579_IC50_0001`, two raw interfaces,
  three frozen provider conditions, six live requests, and six zero-call
  deterministic post-hoc views.
- Question: verify that the corrected provider path preserves one-attempt raw
  evidence, provenance, scoring, operational accounting, cache replay, and
  raw-versus-guarded attribution before any full-matrix spend.
- Status: complete. Six of six trace rows and cache entries exist; every row
  records one provider attempt, matching configured/returned model IDs,
  response ID, finish reason, usage, latency, verbatim text, structured content,
  and 100% cost coverage. The full 91-card provider matrix has not started.
- Headline: actual pilot cost was `$0.449700535` for 106,128 input and 3,024
  output tokens. Four of six raw actions were executable. DeepSeek basic had
  eight cLogP violations and DeepSeek descriptor-enriched selected nine support
  compounds; deterministic repair made both actions valid by replacing eight
  and nine positions, respectively. A cache-only replay reproduced all score
  artifacts. The post-pilot estimate records six cached, 540 missing, and a
  `$105.122676615` residual upper bound.
- Surprise / interpretation: all six responses were parseable, exact-size JSON,
  yet two were operationally unusable. The pilot therefore validates the need
  to separate response syntax, whole-action validity, valid-selection fraction,
  scientific utility, and model-plus-harness behavior. It is one assay task and
  cannot support model ranking or a descriptor-effect claim.
- Follow-up: retain the pilot as operational case-study evidence, require
  separate explicit approval before the residual 540 calls, then perform the
  prespecified 91-card paired uncertainty and raw-versus-repaired analysis.
