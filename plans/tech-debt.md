# Technical Debt

- Validate CARA importer against the official downloaded dataset layout.
- Add source-specific CARA tests after the first real download.
- Add bootstrap confidence intervals to comparison reports.
- Add full provider metadata capture for live LLM calls.
- Include `max_tokens`, temperature, and any provider-specific reasoning
  controls in request/cache metadata before future live reruns.
- Add a resumable per-card trace writer so failed live matrix batches preserve
  partial traces, not only provider caches.
- Add candidate-summary compression or candidate prefiltering before another
  full frontier-model matrix; current full candidate-pool prompts are very large.
- Retry incomplete frontier conditions after provider quota/billing is resolved:
  Anthropic frontier tool conditions, OpenAI frontier, and DeepSeek frontier with
  a larger output budget or revised reasoning prompt.
