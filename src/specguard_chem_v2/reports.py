from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .io import read_json


ABLATION_PAIRS = [
    ("bare_llm", "llm_validator", "validator_delta"),
    ("llm_tools", "llm_tools_validator", "tools_validator_delta"),
    ("bare_llm", "llm_tools", "tools_delta"),
]


def compare_run_summaries(summary_paths: list[Path], out_dir: Path) -> pd.DataFrame:
    rows = [read_json(path) for path in summary_paths]
    frame = pd.DataFrame(rows)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_dir / "system_comparison.csv", index=False)
    frame.to_json(out_dir / "system_comparison.json", orient="records", indent=2)
    _write_leaderboard_slices(frame, out_dir)
    _write_metric_winners(frame, out_dir)
    _write_ablation_table(frame, out_dir)
    return frame


def _is_oracle_system(system_name: object) -> bool:
    return str(system_name).startswith("oracle_")


def _write_leaderboard_slices(frame: pd.DataFrame, out_dir: Path) -> None:
    if frame.empty or "system_name" not in frame.columns:
        frame.to_csv(out_dir / "primary_leaderboard.csv", index=False)
        frame.to_csv(out_dir / "oracle_controls.csv", index=False)
        return
    oracle_mask = frame["system_name"].map(_is_oracle_system)
    frame.loc[~oracle_mask].to_csv(out_dir / "primary_leaderboard.csv", index=False)
    frame.loc[oracle_mask].to_csv(out_dir / "oracle_controls.csv", index=False)


def _write_metric_winners(frame: pd.DataFrame, out_dir: Path) -> None:
    metrics = [
        ("feasible_utility", False),
        ("raw_feasible_utility", False),
        ("ndcg_at_k", False),
        ("raw_ndcg_at_k", False),
        ("compliance_rate", False),
        ("raw_compliance_rate", False),
        ("constrained_regret", True),
        ("schema_error_rate", True),
        ("raw_schema_error_rate", True),
    ]

    def _winner_rows(source: pd.DataFrame) -> list[dict[str, object]]:
        local_rows: list[dict[str, object]] = []
        if source.empty or "system_name" not in source.columns:
            return local_rows
        for metric, lower_is_better in metrics:
            if metric not in source.columns:
                continue
            metric_frame = source[["system_name", metric]].dropna()
            if metric_frame.empty:
                continue
            selected = metric_frame.sort_values(metric, ascending=lower_is_better).iloc[0]
            local_rows.append(
                {
                    "metric": metric,
                    "winner": selected["system_name"],
                    "value": selected[metric],
                    "lower_is_better": lower_is_better,
                }
            )
        return local_rows

    rows = _winner_rows(frame)
    pd.DataFrame(rows).to_csv(out_dir / "metric_winners.csv", index=False)
    if frame.empty or "system_name" not in frame.columns:
        pd.DataFrame([]).to_csv(out_dir / "metric_winners_primary.csv", index=False)
        return
    primary = frame.loc[~frame["system_name"].map(_is_oracle_system)]
    pd.DataFrame(_winner_rows(primary)).to_csv(out_dir / "metric_winners_primary.csv", index=False)


def _write_ablation_table(frame: pd.DataFrame, out_dir: Path) -> None:
    rows: list[dict[str, object]] = []
    if frame.empty or "system_name" not in frame.columns:
        pd.DataFrame(rows).to_csv(out_dir / "ablation_deltas.csv", index=False)
        return
    by_system = {str(row["system_name"]): row for _, row in frame.iterrows()}
    metrics = [
        "feasible_utility",
        "raw_feasible_utility",
        "compliance_rate",
        "raw_compliance_rate",
        "constrained_regret",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_rate",
        "repaired_from_empty_rate",
    ]

    pairs: list[tuple[str, str, str]] = []
    for before, after, label in ABLATION_PAIRS:
        pairs.append((before, after, label))
        suffixes = {
            system_name.removeprefix(f"{before}__")
            for system_name in by_system
            if system_name.startswith(f"{before}__")
        }
        for suffix in sorted(suffixes):
            variant_before = f"{before}__{suffix}"
            variant_after = f"{after}__{suffix}"
            if variant_after in by_system:
                pairs.append((variant_before, variant_after, f"{label}__{suffix}"))

    for before, after, label in pairs:
        if before not in by_system or after not in by_system:
            continue
        row: dict[str, object] = {"ablation": label, "before": before, "after": after}
        for metric in metrics:
            if metric not in frame.columns:
                continue
            before_value = by_system[before].get(metric)
            after_value = by_system[after].get(metric)
            if pd.isna(before_value) or pd.isna(after_value):
                row[f"{metric}_delta"] = None
            else:
                row[f"{metric}_delta"] = float(after_value) - float(before_value)
        rows.append(row)
    pd.DataFrame(rows).to_csv(out_dir / "ablation_deltas.csv", index=False)


def make_frontier_plot(comparison_csv: Path, out_dir: Path) -> Path:
    import matplotlib.pyplot as plt

    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    if not frame.empty:
        ax.scatter(frame["compliance_rate"], frame["feasible_utility"], s=70)
        for _, row in frame.iterrows():
            ax.annotate(
                str(row.get("system_name", "")),
                (float(row["compliance_rate"]), float(row["feasible_utility"])),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )
    ax.set_xlabel("Compliance rate")
    ax.set_ylabel("Feasible utility")
    ax.set_title("Compliance-Utility Frontier")
    ax.set_xlim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output = out_dir / "compliance_utility_frontier.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output


def _format_float(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    available = [column for column in columns if column in frame.columns]
    if frame.empty or not available:
        return "_No rows._\n"
    header = "| " + " | ".join(available) + " |"
    separator = "| " + " | ".join(["---"] * len(available)) + " |"
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in available:
            value = row[column]
            cells.append(_format_float(value) if column != "system_name" else str(value))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows]) + "\n"


def _results_glossary() -> list[str]:
    return [
        "## Label and Metric Glossary",
        "",
        "### Study terms",
        "",
        "- CARA: public compound-activity benchmark used here as the source substrate for assay-level support/query tasks.",
        "- LO: lead optimisation. In this project, LO cards represent an observed support set plus candidate compounds to prioritise next.",
        "- VS: virtual screening. VS is not the primary run here; it usually means ranking a broader candidate set for activity.",
        "- Decision card: one benchmark instance containing support compounds, a candidate pool, hard constraints, budget `k`, and hidden activity values used only by the scorer.",
        "- Support set: already-tested compounds with measured activity that systems may learn from but must not recommend.",
        "- Candidate pool: compounds eligible for selection, subject to hard constraints.",
        "- QSAR: quantitative structure-activity relationship; here, conventional ML models trained on support compounds to predict candidate activity from molecular fingerprints.",
        "- Oracle: non-deployable upper-bound scorer that uses hidden activity values. It is a sanity check, not a real model.",
        "- Validator: deterministic harness logic that checks schema, candidate IDs, duplicates, support-set exclusion, and molecular constraints. It does not use hidden activity values.",
        "- Direct JSON: the current LLM prompt profile that asks for final JSON only, reducing failures where reasoning/prose consumes the visible output budget.",
        "",
        "### System labels",
        "",
        "- `oracle_valid_topk`: non-deployable upper-bound control that uses hidden candidate activity values to choose the best valid top-k set.",
        "- `random_valid`: random valid-candidate baseline.",
        "- `rules_only`: deterministic fallback/rule ranking after applying hard constraints.",
        "- `similarity_to_best_active`: ranks candidates by molecular similarity to the best active support compound.",
        "- `qsar_rf`, `qsar_gbt`, `qsar_svm`: conventional QSAR baselines trained on support compounds with random forest, gradient-boosted trees, or support-vector regression.",
        "- `bare_llm`: LLM receives the decision card and returns candidate IDs without deterministic repair.",
        "- `llm_tools`: LLM condition with extra computed descriptor/tool-summary fields in the candidate rows.",
        "- `llm_validator`: guarded LLM system; raw output is checked and invalid/missing slots may be deterministically repaired.",
        "- `llm_tools_validator`: tool-summary LLM condition plus deterministic checking and repair.",
        "- `*_frontier_selector`: legacy run label for the direct-JSON frontier interface. It means final-answer JSON prompting with no explicit high/extended-thinking mode where avoidable.",
        "- `*_frontier`: original frontier/high-reasoning or provider-default frontier condition.",
        "- `*_fast`: lower-latency/lower-cost provider condition.",
        "",
        "### Metrics",
        "",
        "- `feasible_utility`: sum of hidden activity values for selected candidates that satisfy all hard constraints. Higher is better.",
        "- `raw_feasible_utility`: feasible utility before deterministic validator repair. This is the closer measure of raw LLM behavior.",
        "- `ndcg_at_k`: ranking-quality score using hidden activity as graded relevance. Higher is better; `1.0` is ideal ranking.",
        "- `raw_ndcg_at_k`: NDCG before deterministic validator repair.",
        "- `constrained_regret`: oracle valid top-k utility minus observed feasible utility. Lower is better.",
        "- `compliance_rate`: fraction of the requested `k` selections that are valid after final repair, if repair applies.",
        "- `raw_compliance_rate`: compliance before deterministic validator repair.",
        "- `schema_error_rate`: fraction of cards with final schema/contract errors.",
        "- `raw_schema_error_rate`: schema/contract error rate before deterministic validator repair.",
        "- `repaired_from_empty_rate`: fraction of cards where the validator repaired an empty raw selection list. This should be near zero for a usable LLM interface.",
        "",
        "### Interpretation rules",
        "",
        "- Raw metrics describe model behavior; final metrics for `*_validator` rows describe model plus deterministic guardrail behavior.",
        "- Oracle controls are sanity checks, not systems that could be used prospectively.",
        "- A row can be highly compliant but still have weak utility; this distinction is the main object of the audit.",
    ]


def write_results_summary(comparison_csv: Path, out_dir: Path, *, title: str = "SpecGuard-Chem v2 Results Summary") -> Path:
    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
        oracle = frame[frame["system_name"].map(_is_oracle_system)]
        primary = frame[~frame["system_name"].map(_is_oracle_system)]
    else:
        oracle = frame
        primary = frame

    columns = [
        "system_name",
        "feasible_utility",
        "raw_feasible_utility",
        "ndcg_at_k",
        "raw_ndcg_at_k",
        "constrained_regret",
        "compliance_rate",
        "raw_compliance_rate",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_from_empty_rate",
    ]
    generated_at = datetime.now(timezone.utc).isoformat()
    content = [
        f"# {title}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        f"Source comparison CSV: `{comparison_csv}`",
        "",
        "This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.",
        "",
        "## Primary Systems",
        "",
        _markdown_table(primary, columns),
        "## Oracle Controls",
        "",
        _markdown_table(oracle, columns),
        "## Reading Guide",
        "",
        "- Higher feasible utility and NDCG@k are better.",
        "- Raw columns score the model output before deterministic validator repair.",
        "- Final columns score the selected output after validator repair where applicable.",
        "- Lower constrained regret and schema error rate are better.",
        "- Oracle controls are sanity checks and must not be mixed into primary system claims.",
        "",
        *_results_glossary(),
    ]
    output = out_dir / "RESULTS_SUMMARY.md"
    output.write_text("\n".join(content) + "\n", encoding="utf-8")
    return output
