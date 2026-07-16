# Manuscript

This directory contains the clean conference-paper incarnation of the bounded
SpecGuard-Chem release. It intentionally does not import any historical
paper-50 result, figure, table, or response cache.

`main.tex` is a compileable version-aligned pre-run manuscript. Corrected data and
deterministic baseline evidence are populated. A six-request, one-card provider
pilot has been completed as an execution/provenance check, but the full 91-card
experiment remains visibly marked as pending until its separately authorized
residual run is completed, scored, and audited.

`generated_results.tex` is the single result-status switch, and
`../tables/v0.1.0/deterministic_baseline_rows.tex` supplies the numerical rows
of the baseline table. Regenerate both tracked files from the canonical release
comparison and per-system summary artifacts, from the repository root:

```bash
python3 paper/manuscript/generate_results.py
python3 paper/manuscript/generate_results.py --check
```

Generation is timestamp-free and byte-stable. It also verifies that the
comparison rows agree with each canonical `scores/summary.json`. The generator
keeps `\llmresultsavailablefalse` until
`release/v0.1.0/experiments/llm/comparison/system_comparison.json` exists and
contains exactly the six frozen raw model/interface rows and their six
documented post-hoc repaired views. It cross-checks all 91 frozen task IDs in
the corresponding traces, card scores, summaries, and matrix manifest, and
requires the existing raw-versus-repaired and best-QSAR paired-bootstrap
outputs to cover all 91 cards. A pilot, substituted condition, extra LLM row,
or aggregate-only comparison cannot open the gate. Do not bypass it by editing
the generated TeX.

Compile with a normal Tectonic installation:

```bash
cd paper/manuscript
tectonic -X compile --outdir build main.tex
tectonic -X compile --outdir build supplement.tex
```

Alternatively, a TeX Live installation can build the same sources with
`latexmk -pdf -outdir=build main.tex` and
`latexmk -pdf -outdir=build supplement.tex`. The release process copies only
the final PDFs out of `build/`; auxiliary files remain ignored.

Before submission, confirm the author list, affiliation wording, acknowledgments,
funding, competing interests, target venue template, and AI-use disclosure.
