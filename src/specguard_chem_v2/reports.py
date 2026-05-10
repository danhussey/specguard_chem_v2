from __future__ import annotations

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
    for before, after, label in ABLATION_PAIRS:
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
