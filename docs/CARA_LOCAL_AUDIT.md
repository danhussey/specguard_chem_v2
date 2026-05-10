# CARA Local Audit

Date: 2026-05-10

## Download

- Source: `https://zenodo.org/records/14740896/files/CARA.zip?download=1`
- Local archive: `data/raw/cara/CARA.zip`
- Archive bytes: `103511135`
- SHA256: `87a71c2040d1a1434348d35691242ab1327b846cf06a46f1d64cd060867de12c`
- Extracted root: `data/raw/cara/extracted/CARA`

Raw downloaded data are ignored by Git.

## Observed Layout

Official CARA v1.0.1 archive contains:

- `CARA/Task/LO_All.tsv`
- `CARA/Task/LO_GPCR.tsv`
- `CARA/Task/LO_Kinase.tsv`
- `CARA/Task/VS_All.tsv`
- `CARA/Task/VS_GPCR.tsv`
- `CARA/Task/VS_Kinase.tsv`
- paired split JSON files under `CARA/Split`, such as
  `LO_All_support.json` and `LO_All_query.json`

The split JSON files map assay task IDs to row indices in the corresponding task
TSV. The implemented importer resolves those indices into normalized records.

## Local Import

Command:

```bash
uv run sgchem import-cara data/raw/cara --split-name LO_All --out data/interim/cara_lo_all_records.jsonl
```

Result:

- importer: `official_cara_split`
- split: `LO_All`
- normalized records: `23777`
- assay tasks: `100`

## Local Card Build

Command:

```bash
uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl --out data/cards/cara_lo_all_cards.jsonl --target-cards 20 --budget-k 10 --support-size 50
uv run sgchem validate-cards data/cards/cara_lo_all_cards.jsonl
```

Result:

- cards built: `20`
- budget: `10`
- support size: `50`
- validation: passed

## Deterministic Smoke

Command:

```bash
uv run sgchem run-suite data/cards/cara_lo_all_cards.jsonl --systems oracle_valid_topk,random_valid,rules_only,similarity_to_best_active,qsar_rf,qsar_gbt,qsar_svm --out runs/cara_lo_all_local
uv run sgchem compare-runs runs/cara_lo_all_local/*/scores/summary.json --out runs/cara_lo_all_local/compare
```

Headline comparison on the 20-card local smoke:

| System | Feasible utility | NDCG@k | Constrained regret | Compliance |
|---|---:|---:|---:|---:|
| oracle_valid_topk | 86.706 | 1.000 | 0.000 | 1.000 |
| qsar_gbt | 81.215 | 0.929 | 5.491 | 1.000 |
| qsar_svm | 81.198 | 0.928 | 5.508 | 1.000 |
| qsar_rf | 80.997 | 0.929 | 5.709 | 1.000 |
| similarity_to_best_active | 74.007 | 0.850 | 12.699 | 1.000 |
| random_valid | 68.285 | 0.779 | 18.421 | 1.000 |
| rules_only | 67.083 | 0.764 | 19.624 | 1.000 |

This is a smoke result, not a paper result. It confirms the harness can import
real CARA data, construct decision cards, run strong baselines, and report the
compliance-utility frontier.
