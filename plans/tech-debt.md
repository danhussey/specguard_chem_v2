# Technical Debt

- Validate CARA importer against the official downloaded dataset layout.
- Add source-specific CARA tests after the first real download.
- Add bootstrap confidence intervals to comparison reports.
- Add full provider metadata capture for live LLM calls.
- Add a resumable per-card trace writer so failed live matrix batches preserve
  partial traces, not only provider caches.
- Add candidate-summary compression or candidate prefiltering before another
  full frontier-model matrix; current full candidate-pool prompts are very large.
- Retry DeepSeek frontier only with a revised reasoning/output strategy.
- Add provider-specific controls for reasoning-token budgets. OpenAI frontier
  and DeepSeek frontier both consumed large reasoning budgets without final JSON
  under the current full-pool interface.
