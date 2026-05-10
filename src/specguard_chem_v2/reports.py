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
        ("ndcg_at_k", False),
        ("compliance_rate", False),
        ("constrained_regret", True),
        ("schema_error_rate", True),
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
    metrics = ["feasible_utility", "compliance_rate", "constrained_regret", "schema_error_rate"]

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
        "ndcg_at_k",
        "constrained_regret",
        "compliance_rate",
        "schema_error_rate",
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
        "- Lower constrained regret and schema error rate are better.",
        "- Oracle controls are sanity checks and must not be mixed into primary system claims.",
    ]
    output = out_dir / "RESULTS_SUMMARY.md"
    output.write_text("\n".join(content) + "\n", encoding="utf-8")
    return output
