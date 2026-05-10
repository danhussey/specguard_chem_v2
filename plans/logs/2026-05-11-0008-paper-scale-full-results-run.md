# 2026-05-11 0008 Paper-Scale Full Results Run

## Summary

Executed the first paper-scale CARA LO run on a frozen 50-card decision-card
artifact. Deterministic baselines and oracle controls completed. The complete
LLM matrix for fast models completed for OpenAI, Anthropic, and DeepSeek across
all four LLM system variants. Frontier conditions were attempted and partially
completed, but provider quota and throughput prevented a complete frontier
matrix in this run.

The clean primary result is the fast-complete comparison:
`paper/tables/cara_lo_paper_50_fast_complete/primary_leaderboard.csv`.

## Card Artifact

```text
cards: data/cards/cara_lo_paper_50.jsonl
cards_sha256: 9c4e45880dd6fe97643c1bcfd66a16a0f72b4a0e0a60476f12bc58d464d80d03
num_cards: 50
budget_k: 10
support_size: 50
selection_policy: largest_candidate_pool
mean_candidate_pool_size: 292.16
mean_feasible_candidate_count: 162.4
```

## Commands Run

```bash
uv run pytest
uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl --out data/cards/cara_lo_paper_50.jsonl --target-cards 50 --budget-k 10 --support-size 50 --selection-policy largest_candidate_pool
uv run sgchem validate-cards data/cards/cara_lo_paper_50.jsonl
uv run sgchem summarize-cards data/cards/cara_lo_paper_50.jsonl --out data/cards/cara_lo_paper_50.summary.json
uv run sgchem run-suite data/cards/cara_lo_paper_50.jsonl --systems oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm --out runs/cara_lo_paper_50_baselines
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json --out runs/cara_lo_paper_50_baselines/compare
uv run sgchem export-llm-requests data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-matrix configs/model_matrix.toml --model-conditions all --out runs/cara_lo_paper_50_llm_requests.jsonl
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions all --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions deepseek_fast --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_fast --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions anthropic_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions openai_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run --extra providers sgchem run-llm-matrix data/cards/cara_lo_paper_50.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --model-conditions deepseek_frontier --out runs/cara_lo_paper_50_llm_matrix --allow-external
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/*/*/scores/summary.json --out paper/tables/cara_lo_paper_50_completed
uv run sgchem compare-runs runs/cara_lo_paper_50_baselines/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/anthropic_fast/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/deepseek_fast/*/scores/summary.json runs/cara_lo_paper_50_llm_matrix/openai_fast/*/scores/summary.json --out paper/tables/cara_lo_paper_50_fast_complete
uv run sgchem make-figures paper/tables/cara_lo_paper_50_completed/system_comparison.csv --out paper/figures/cara_lo_paper_50_completed
uv run sgchem make-figures paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv --out paper/figures/cara_lo_paper_50_fast_complete
uv run sgchem make-report paper/tables/cara_lo_paper_50_fast_complete/system_comparison.csv --out paper --title "SpecGuard-Chem v2 CARA LO Paper-50 Fast-Complete Results"
```

## Tests

Final test result after the LLM output-normalization hardening:

```text
14 passed
```

## Main Fast-Complete Result

Top rows from `paper/tables/cara_lo_paper_50_fast_complete/primary_leaderboard.csv`:

| System | Feasible utility | NDCG@k | Compliance | Constrained regret |
| --- | ---: | ---: | ---: | ---: |
| `qsar_svm` | 81.3823 | 0.9096 | 1.000 | 7.6394 |
| `qsar_gbt` | 80.8879 | 0.9002 | 1.000 | 8.1338 |
| `qsar_rf` | 80.6341 | 0.9006 | 1.000 | 8.3876 |
| `similarity_to_best_active` | 73.6032 | 0.8253 | 1.000 | 15.4185 |
| `llm_validator__deepseek_fast` | 68.4017 | 0.7626 | 1.000 | 20.6200 |
| `llm_tools_validator__openai_fast` | 67.7022 | 0.7515 | 1.000 | 21.3195 |
| `llm_tools_validator__anthropic_fast` | 67.2255 | 0.7500 | 1.000 | 21.7962 |
| `llm_tools_validator__deepseek_fast` | 67.2174 | 0.7487 | 1.000 | 21.8043 |

Interpretation: QSAR baselines dominated the completed fast-model LLM conditions
on utility. Validators reliably improved compliance and feasible utility for
LLM systems. Tool summaries helped some unvalidated LLM conditions but did not
close the gap to QSAR.

## Frontier Attempts

Completed frontier traces:

- `anthropic_frontier/bare_llm`
- `anthropic_frontier/llm_validator`
- `deepseek_frontier/bare_llm`

Incomplete frontier cache counts:

```text
anthropic_frontier/llm_tools: 34/50 cached, stopped by Anthropic credit-balance error
openai_frontier/bare_llm: 3/50 cached, stopped by OpenAI insufficient_quota error
deepseek_frontier/bare_llm: completed 50/50 but produced empty selections because reasoning consumed the output budget
```

DeepSeek frontier generated `reasoning_content` and used the full configured
4096 completion tokens as reasoning tokens on observed cards, leaving no final
JSON selections. Its scored `bare_llm` trace therefore has `schema_error_rate=1`
and `feasible_utility=0`. This is a meaningful system failure mode, not a
medicinal-chemistry result.

## Files Generated

Generated artifacts are ignored by Git but present in the workspace:

- `data/cards/cara_lo_paper_50.jsonl`
- `data/cards/cara_lo_paper_50.meta.json`
- `data/cards/cara_lo_paper_50.summary.json`
- `runs/cara_lo_paper_50_baselines/`
- `runs/cara_lo_paper_50_llm_requests.jsonl`
- `runs/cara_lo_paper_50_llm_matrix/`
- `paper/tables/cara_lo_paper_50_completed/`
- `paper/tables/cara_lo_paper_50_fast_complete/`
- `paper/figures/cara_lo_paper_50_completed/`
- `paper/figures/cara_lo_paper_50_fast_complete/`
- `paper/RESULTS_SUMMARY.md`

## Code Changes During Run

LLM output normalization was hardened after DeepSeek fast returned
`confidence=7.0`, which previously violated the `[0, 1]` schema and aborted the
run. The normalizer now clamps numeric confidence values into range and drops
non-numeric confidence values.

## Decisions

- Use `largest_candidate_pool` for the paper-50 artifact to avoid hidden-activity
  tuning while keeping candidate selection non-trivial.
- Treat `paper/tables/cara_lo_paper_50_fast_complete/` as the coherent primary
  result because every fast provider/model/system condition completed.
- Treat `paper/tables/cara_lo_paper_50_completed/` as a broader diagnostic table
  that includes partial frontier traces.
- Do not substitute weaker frontier models without a separate plan; failed
  frontier conditions are recorded as provider/quota/throughput blockers.

## Follow-Up Work

- Resume `anthropic_frontier/llm_tools` and `llm_tools_validator` only after
  enough Anthropic credits are available; existing caches should reduce repeat
  cost.
- Retry OpenAI frontier only after quota/billing is resolved.
- For DeepSeek frontier, increase the output budget or change prompting so final
  JSON is produced after reasoning; consider a separate `deepseek_frontier_long`
  condition so cache keys do not mix.
- Include `max_tokens` and temperature in request/cache metadata before future
  live reruns.
- Consider candidate-summary compression before another full frontier matrix.
