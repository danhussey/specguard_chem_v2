# Technical Debt

- Add full provider metadata capture for live LLM calls.
- Add a resumable per-card trace writer so failed live matrix batches preserve
  partial traces, not only provider caches.
- Add candidate-summary compression or candidate prefiltering before another
  full frontier-model matrix; current full candidate-pool prompts are very large.
- Retry DeepSeek frontier only with a revised reasoning/output strategy.
- Candidate-summary compression remains a separate future experiment; do not mix
  it into the direct-selector frontier comparison.
- Add manuscript-grade statistical wording after deciding which paired
  bootstrap deltas belong in the final paper tables.
- Add a second independent implementation of the CARA positional-import audit
  if the benchmark expands beyond the frozen v0.1.0 dataset.
