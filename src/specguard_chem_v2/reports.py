from __future__ import annotations

from itertools import combinations
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs

from .io import read_json, read_jsonl


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
        frame = _add_display_columns(frame)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_dir / "system_comparison.csv", index=False)
    frame.to_json(out_dir / "system_comparison.json", orient="records", indent=2)
    _write_leaderboard_slices(frame, out_dir)
    _write_metric_winners(frame, out_dir)
    _write_ablation_table(frame, out_dir)
    card_scores = _load_card_scores(summary_paths)
    failure_rows = _load_failure_taxonomies(summary_paths)
    _write_paired_bootstrap_tables(card_scores, frame, out_dir)
    _write_card_level_diagnostics(card_scores, frame, out_dir)
    _write_failure_taxonomy_tables(failure_rows, frame, out_dir)
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


def _load_card_scores(summary_paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for summary_path in summary_paths:
        card_scores_path = summary_path.parent / "card_scores.jsonl"
        if not card_scores_path.exists():
            continue
        rows.extend(read_jsonl(card_scores_path))
    return pd.DataFrame(rows)


def _load_failure_taxonomies(summary_paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for summary_path in summary_paths:
        taxonomy_path = summary_path.parent / "failure_taxonomy.csv"
        if taxonomy_path.exists():
            frames.append(pd.read_csv(taxonomy_path))
    if not frames:
        return pd.DataFrame(columns=["task_id", "system_name", "failure_type", "count"])
    return pd.concat(frames, ignore_index=True)


def _system_label_maps(frame: pd.DataFrame) -> dict[str, dict[str, object]]:
    if frame.empty or "system_name" not in frame.columns:
        return {}
    enriched = _add_display_columns(frame)
    maps: dict[str, dict[str, object]] = {}
    for _, row in enriched.iterrows():
        system_name = str(row.get("system_name", ""))
        maps[system_name] = {
            "display_label": row.get("display_label", system_name),
            "system_group": row.get("system_group", _system_group(system_name)),
            "condition_label": row.get("condition_label", ""),
        }
    return maps


def _add_score_labels(scores: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    if scores.empty or "system_name" not in scores.columns:
        return scores
    maps = _system_label_maps(frame)
    output = scores.copy()
    output["display_label"] = output["system_name"].map(
        lambda value: maps.get(str(value), {}).get("display_label", str(value))
    )
    output["system_group"] = output["system_name"].map(
        lambda value: maps.get(str(value), {}).get("system_group", _system_group(str(value)))
    )
    output["condition_label"] = output["system_name"].map(
        lambda value: maps.get(str(value), {}).get("condition_label", "")
    )
    return output


def _paired_bootstrap_delta(
    left: pd.Series,
    right: pd.Series,
    *,
    samples: int = 2000,
    seed: int = 7,
) -> dict[str, float | int]:
    differences = (left.astype(float) - right.astype(float)).dropna().to_numpy()
    if len(differences) == 0:
        return {
            "n_cards": 0,
            "mean_delta": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "probability_delta_gt_zero": np.nan,
        }
    if len(differences) == 1 or samples <= 0:
        value = float(differences[0])
        return {
            "n_cards": int(len(differences)),
            "mean_delta": value,
            "ci_low": value,
            "ci_high": value,
            "probability_delta_gt_zero": 1.0 if value > 0 else 0.0,
        }
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    for index in range(samples):
        means[index] = float(np.mean(rng.choice(differences, size=len(differences), replace=True)))
    return {
        "n_cards": int(len(differences)),
        "mean_delta": float(np.mean(differences)),
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
        "probability_delta_gt_zero": float(np.mean(means > 0)),
    }


def _paired_metric_row(
    scores: pd.DataFrame,
    labels: dict[str, dict[str, object]],
    system_a: str,
    system_b: str,
    metric: str,
    *,
    comparison: str,
    seed: int,
) -> dict[str, object] | None:
    if metric not in scores.columns:
        return None
    left = scores.loc[scores["system_name"] == system_a, ["task_id", metric]].dropna()
    right = scores.loc[scores["system_name"] == system_b, ["task_id", metric]].dropna()
    merged = left.merge(right, on="task_id", suffixes=("_a", "_b"))
    if merged.empty:
        return None
    stats = _paired_bootstrap_delta(merged[f"{metric}_a"], merged[f"{metric}_b"], seed=seed)
    if stats["n_cards"] == 0:
        return None
    return {
        "comparison": comparison,
        "metric": metric,
        "system_a": system_a,
        "system_a_label": labels.get(system_a, {}).get("display_label", system_a),
        "system_b": system_b,
        "system_b_label": labels.get(system_b, {}).get("display_label", system_b),
        "direction": "system_a_minus_system_b",
        **stats,
    }


def _best_system(frame: pd.DataFrame, group: str | None, metric: str) -> str | None:
    if frame.empty or metric not in frame.columns or "system_name" not in frame.columns:
        return None
    source = frame
    if group is not None and "system_group" in source.columns:
        source = source[source["system_group"] == group]
    metric_frame = source.dropna(subset=[metric])
    if metric_frame.empty:
        return None
    return str(metric_frame.sort_values(metric, ascending=False).iloc[0]["system_name"])


def _write_paired_bootstrap_tables(scores: pd.DataFrame, frame: pd.DataFrame, out_dir: Path) -> None:
    columns = [
        "comparison",
        "metric",
        "system_a",
        "system_a_label",
        "system_b",
        "system_b_label",
        "direction",
        "n_cards",
        "mean_delta",
        "ci_low",
        "ci_high",
        "probability_delta_gt_zero",
    ]
    if scores.empty or frame.empty:
        pd.DataFrame(columns=columns).to_csv(out_dir / "paired_bootstrap_deltas.csv", index=False)
        pd.DataFrame(columns=columns).to_csv(out_dir / "paired_bootstrap_key_deltas.csv", index=False)
        return

    enriched_frame = _add_display_columns(frame)
    primary = enriched_frame.loc[~enriched_frame["system_name"].map(_is_oracle_system)].copy()
    labels = _system_label_maps(enriched_frame)
    metrics = [
        "feasible_utility",
        "ndcg_at_k",
        "compliance_rate",
        "raw_feasible_utility",
        "raw_ndcg_at_k",
        "raw_compliance_rate",
    ]
    ordered_systems = [str(value) for value in primary["system_name"].tolist()]
    rows: list[dict[str, object]] = []
    for system_a, system_b in combinations(ordered_systems, 2):
        for metric in metrics:
            row = _paired_metric_row(
                scores,
                labels,
                system_a,
                system_b,
                metric,
                comparison="all_primary_pairs",
                seed=7,
            )
            if row is not None and int(row["n_cards"]) >= 2:
                rows.append(row)
    all_pairs = pd.DataFrame(rows, columns=columns)
    all_pairs.to_csv(out_dir / "paired_bootstrap_deltas.csv", index=False)

    oracle = _best_system(enriched_frame, "Oracle", "feasible_utility")
    best_qsar = _best_system(enriched_frame, "QSAR", "feasible_utility")
    best_llm = _best_system(enriched_frame, "LLM", "feasible_utility")
    best_raw_llm = _best_system(enriched_frame, "LLM", "raw_feasible_utility")
    similarity = "similarity_to_best_active" if "similarity_to_best_active" in ordered_systems else None
    rules = "rules_only" if "rules_only" in ordered_systems else None
    key_specs = [
        ("oracle_minus_best_qsar", oracle, best_qsar),
        ("best_qsar_minus_best_final_llm", best_qsar, best_llm),
        ("best_qsar_minus_similarity", best_qsar, similarity),
        ("best_final_llm_minus_similarity", best_llm, similarity),
        ("best_final_llm_minus_rules", best_llm, rules),
        ("best_raw_llm_minus_similarity", best_raw_llm, similarity),
    ]
    key_rows: list[dict[str, object]] = []
    for comparison, system_a, system_b in key_specs:
        if system_a is None or system_b is None or system_a == system_b:
            continue
        for metric in ["feasible_utility", "ndcg_at_k", "compliance_rate"]:
            row = _paired_metric_row(
                scores,
                labels,
                system_a,
                system_b,
                metric,
                comparison=comparison,
                seed=13,
            )
            if row is not None and int(row["n_cards"]) >= 2:
                key_rows.append(row)
    pd.DataFrame(key_rows, columns=columns).to_csv(
        out_dir / "paired_bootstrap_key_deltas.csv",
        index=False,
    )


def _card_series_specs(frame: pd.DataFrame) -> list[tuple[str, str | None, str]]:
    enriched = _add_display_columns(frame)
    return [
        ("Oracle upper-bound", _best_system(enriched, "Oracle", "feasible_utility"), "final"),
        ("Best QSAR", _best_system(enriched, "QSAR", "feasible_utility"), "final"),
        ("Best final LLM", _best_system(enriched, "LLM", "feasible_utility"), "final"),
        ("Best raw LLM", _best_system(enriched, "LLM", "raw_feasible_utility"), "raw"),
        ("Similarity baseline", "similarity_to_best_active", "final"),
        ("Rules-only baseline", "rules_only", "final"),
    ]


def _score_value(row: pd.Series, metric: str, source: str) -> object:
    if source == "raw":
        raw_metric = f"raw_{metric}" if not metric.startswith("raw_") else metric
        return row.get(raw_metric)
    return row.get(metric)


def _write_card_level_diagnostics(scores: pd.DataFrame, frame: pd.DataFrame, out_dir: Path) -> None:
    key_columns = [
        "task_id",
        "series",
        "system_name",
        "display_label",
        "metric_source",
        "feasible_utility",
        "ndcg_at_k",
        "compliance_rate",
        "constrained_regret",
        "oracle_utility",
    ]
    diagnostic_columns = [
        "task_id",
        "oracle_utility",
        "best_qsar_utility",
        "best_final_llm_utility",
        "best_raw_llm_utility",
        "similarity_utility",
        "rules_utility",
        "oracle_minus_best_qsar",
        "best_qsar_minus_best_final_llm",
        "best_qsar_minus_best_raw_llm",
        "best_final_llm_minus_similarity",
        "best_qsar_minus_similarity",
    ]
    if scores.empty or frame.empty:
        pd.DataFrame(columns=key_columns).to_csv(out_dir / "card_level_key_systems.csv", index=False)
        pd.DataFrame(columns=diagnostic_columns).to_csv(out_dir / "card_level_diagnostics.csv", index=False)
        return

    labelled_scores = _add_score_labels(scores, frame)
    score_by_system = {system: group for system, group in labelled_scores.groupby("system_name")}
    key_rows: list[dict[str, object]] = []
    for series, system_name, source in _card_series_specs(frame):
        if system_name is None or system_name not in score_by_system:
            continue
        system_scores = score_by_system[system_name]
        for _, row in system_scores.iterrows():
            feasible_utility = _score_value(row, "feasible_utility", source)
            if pd.isna(feasible_utility):
                continue
            key_rows.append(
                {
                    "task_id": row["task_id"],
                    "series": series,
                    "system_name": system_name,
                    "display_label": row.get("display_label", system_name),
                    "metric_source": source,
                    "feasible_utility": feasible_utility,
                    "ndcg_at_k": _score_value(row, "ndcg_at_k", source),
                    "compliance_rate": _score_value(row, "compliance_rate", source),
                    "constrained_regret": row.get("oracle_utility") - float(feasible_utility),
                    "oracle_utility": row.get("oracle_utility"),
                }
            )
    key_frame = pd.DataFrame(key_rows, columns=key_columns)
    key_frame.to_csv(out_dir / "card_level_key_systems.csv", index=False)

    if key_frame.empty:
        pd.DataFrame(columns=diagnostic_columns).to_csv(out_dir / "card_level_diagnostics.csv", index=False)
        return
    pivot = key_frame.pivot_table(
        index="task_id",
        columns="series",
        values="feasible_utility",
        aggfunc="first",
    )
    oracle_values = key_frame.groupby("task_id")["oracle_utility"].first()
    diagnostics = pd.DataFrame({"task_id": pivot.index})
    diagnostics["oracle_utility"] = diagnostics["task_id"].map(oracle_values)
    series_to_column = {
        "Best QSAR": "best_qsar_utility",
        "Best final LLM": "best_final_llm_utility",
        "Best raw LLM": "best_raw_llm_utility",
        "Similarity baseline": "similarity_utility",
        "Rules-only baseline": "rules_utility",
    }
    for series, column in series_to_column.items():
        diagnostics[column] = diagnostics["task_id"].map(pivot[series]) if series in pivot else np.nan
    diagnostics["oracle_minus_best_qsar"] = diagnostics["oracle_utility"] - diagnostics["best_qsar_utility"]
    diagnostics["best_qsar_minus_best_final_llm"] = (
        diagnostics["best_qsar_utility"] - diagnostics["best_final_llm_utility"]
    )
    diagnostics["best_qsar_minus_best_raw_llm"] = (
        diagnostics["best_qsar_utility"] - diagnostics["best_raw_llm_utility"]
    )
    diagnostics["best_final_llm_minus_similarity"] = (
        diagnostics["best_final_llm_utility"] - diagnostics["similarity_utility"]
    )
    diagnostics["best_qsar_minus_similarity"] = diagnostics["best_qsar_utility"] - diagnostics["similarity_utility"]
    diagnostics[diagnostic_columns].to_csv(out_dir / "card_level_diagnostics.csv", index=False)


def _write_failure_taxonomy_tables(taxonomy: pd.DataFrame, frame: pd.DataFrame, out_dir: Path) -> None:
    summary_columns = [
        "system_name",
        "display_label",
        "system_group",
        "failure_type",
        "num_cards",
        "cards_with_type",
        "card_rate",
        "total_issue_count",
        "mean_issue_count_per_card",
    ]
    group_columns = [
        "system_group",
        "failure_type",
        "systems",
        "num_cards",
        "cards_with_type",
        "card_rate",
        "total_issue_count",
    ]
    if taxonomy.empty or frame.empty:
        pd.DataFrame(columns=summary_columns).to_csv(out_dir / "failure_taxonomy_summary.csv", index=False)
        pd.DataFrame(columns=group_columns).to_csv(out_dir / "failure_taxonomy_by_group.csv", index=False)
        return
    labels = _system_label_maps(frame)
    working = taxonomy.copy()
    working["count"] = pd.to_numeric(working["count"], errors="coerce").fillna(0)
    working["display_label"] = working["system_name"].map(
        lambda value: labels.get(str(value), {}).get("display_label", str(value))
    )
    working["system_group"] = working["system_name"].map(
        lambda value: labels.get(str(value), {}).get("system_group", _system_group(str(value)))
    )
    system_card_counts = working.groupby("system_name")["task_id"].nunique().to_dict()
    rows: list[dict[str, object]] = []
    for (system_name, failure_type), group in working.groupby(["system_name", "failure_type"]):
        if failure_type == "none":
            cards_with_type = group["task_id"].nunique()
        else:
            cards_with_type = group.loc[group["count"] > 0, "task_id"].nunique()
        num_cards = int(system_card_counts.get(system_name, group["task_id"].nunique()))
        total_count = float(group["count"].sum())
        rows.append(
            {
                "system_name": system_name,
                "display_label": labels.get(str(system_name), {}).get("display_label", system_name),
                "system_group": labels.get(str(system_name), {}).get("system_group", _system_group(str(system_name))),
                "failure_type": failure_type,
                "num_cards": num_cards,
                "cards_with_type": int(cards_with_type),
                "card_rate": (float(cards_with_type) / num_cards) if num_cards else 0.0,
                "total_issue_count": total_count,
                "mean_issue_count_per_card": (total_count / num_cards) if num_cards else 0.0,
            }
        )
    summary = pd.DataFrame(rows, columns=summary_columns).sort_values(
        ["failure_type", "card_rate", "total_issue_count"],
        ascending=[True, False, False],
    )
    summary.to_csv(out_dir / "failure_taxonomy_summary.csv", index=False)

    group_rows: list[dict[str, object]] = []
    for (system_group, failure_type), group in summary.groupby(["system_group", "failure_type"]):
        num_cards = int(group["num_cards"].sum())
        cards_with_type = int(group["cards_with_type"].sum())
        total_count = float(group["total_issue_count"].sum())
        group_rows.append(
            {
                "system_group": system_group,
                "failure_type": failure_type,
                "systems": int(group["system_name"].nunique()),
                "num_cards": num_cards,
                "cards_with_type": cards_with_type,
                "card_rate": (cards_with_type / num_cards) if num_cards else 0.0,
                "total_issue_count": total_count,
            }
        )
    pd.DataFrame(group_rows, columns=group_columns).sort_values(
        ["failure_type", "card_rate"],
        ascending=[True, False],
    ).to_csv(out_dir / "failure_taxonomy_by_group.csv", index=False)


def make_frontier_plot(comparison_csv: Path, out_dir: Path) -> Path:
    import matplotlib.pyplot as plt

    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    if not frame.empty:
        frame = _add_display_columns(frame)
        label_column = "display_label" if "display_label" in frame.columns else "system_name"
        ax.scatter(frame["compliance_rate"], frame["feasible_utility"], s=70)
        for _, row in frame.iterrows():
            ax.annotate(
                str(row.get(label_column, row.get("system_name", ""))),
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
    _make_card_level_plots(comparison_csv.parent, out_dir)
    return output


def _wrap_tick(label: object, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(str(label), width=width, break_long_words=False))


def _make_card_level_plots(table_dir: Path, out_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    outputs: list[Path] = []
    key_path = table_dir / "card_level_key_systems.csv"
    diagnostics_path = table_dir / "card_level_diagnostics.csv"
    if not key_path.exists() or not diagnostics_path.exists():
        return outputs
    key = pd.read_csv(key_path)
    diagnostics = pd.read_csv(diagnostics_path)
    if key.empty or diagnostics.empty:
        return outputs

    series_order = [
        "Oracle upper-bound",
        "Best QSAR",
        "Best final LLM",
        "Best raw LLM",
        "Similarity baseline",
        "Rules-only baseline",
    ]
    available_series = [series for series in series_order if series in set(key["series"])]
    if available_series:
        plot_data = [
            key.loc[key["series"] == series, "feasible_utility"].dropna().astype(float).to_numpy()
            for series in available_series
        ]
        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        ax.boxplot(plot_data, tick_labels=[_wrap_tick(series) for series in available_series], showfliers=False)
        ax.set_ylabel("Per-card feasible utility")
        ax.set_title("Card-Level Utility Distribution")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        output = out_dir / "card_level_utility_distribution.png"
        fig.savefig(output, dpi=200)
        plt.close(fig)
        outputs.append(output)

    delta_columns = [
        "oracle_minus_best_qsar",
        "best_qsar_minus_best_final_llm",
        "best_qsar_minus_best_raw_llm",
        "best_final_llm_minus_similarity",
        "best_qsar_minus_similarity",
    ]
    available_deltas = [
        column for column in delta_columns if column in diagnostics.columns and diagnostics[column].notna().any()
    ]
    if available_deltas:
        plot_data = [diagnostics[column].dropna().astype(float).to_numpy() for column in available_deltas]
        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        ax.boxplot(
            plot_data,
            tick_labels=[_wrap_tick(column.replace("_", " ")) for column in available_deltas],
            showfliers=False,
        )
        ax.axhline(0, color="#64717f", linewidth=1)
        ax.set_ylabel("Per-card utility delta")
        ax.set_title("Card-Level Utility Deltas")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        output = out_dir / "card_level_delta_distribution.png"
        fig.savefig(output, dpi=200)
        plt.close(fig)
        outputs.append(output)

    if {
        "best_qsar_utility",
        "best_final_llm_utility",
    }.issubset(diagnostics.columns):
        scatter = diagnostics[["best_qsar_utility", "best_final_llm_utility"]].dropna()
        if not scatter.empty:
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.scatter(scatter["best_qsar_utility"], scatter["best_final_llm_utility"], alpha=0.75)
            axis_min = float(min(scatter.min()))
            axis_max = float(max(scatter.max()))
            ax.plot([axis_min, axis_max], [axis_min, axis_max], color="#64717f", linestyle="--", linewidth=1)
            ax.set_xlabel("Best QSAR feasible utility")
            ax.set_ylabel("Best final LLM feasible utility")
            ax.set_title("Per-Card QSAR Versus LLM Utility")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            output = out_dir / "card_level_qsar_vs_llm_scatter.png"
            fig.savefig(output, dpi=200)
            plt.close(fig)
            outputs.append(output)
    return outputs


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


SYSTEM_LABELS = {
    "oracle_valid_topk": "Oracle upper-bound",
    "random_valid": "Random valid baseline",
    "rules_only": "Rule/desirability baseline",
    "similarity_to_best_active": "Similarity-to-best-active baseline",
    "qsar_rf": "QSAR random forest",
    "qsar_gbt": "QSAR gradient boosting",
    "qsar_svm": "QSAR linear SVR",
    "bare_llm": "Bare LLM",
    "llm_tools": "LLM plus tool summaries",
    "llm_validator": "LLM plus validator",
    "llm_tools_validator": "LLM plus tools and validator",
}


SYSTEM_DESCRIPTIONS = {
    "oracle_valid_topk": "Non-deployable upper-bound control that ranks valid candidates using hidden activity values.",
    "random_valid": "Samples valid candidates at random after deterministic feasibility filtering.",
    "rules_only": "Applies deterministic constraints, then ranks by simple molecular-property desirability around MW 350, cLogP 2.5, and TPSA 75.",
    "similarity_to_best_active": "Ranks feasible candidates by Morgan-fingerprint Tanimoto similarity to the most active support compound.",
    "qsar_rf": "Trains a random forest QSAR regressor separately on each card's support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity. It does not see hidden candidate activity.",
    "qsar_gbt": "Trains a gradient-boosting QSAR regressor separately on each card's support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity. It does not see hidden candidate activity.",
    "qsar_svm": "Trains a sparse-scaled linear-kernel QSAR support-vector regressor separately on each card's support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity. It does not see hidden candidate activity.",
    "bare_llm": "Prompts the model to return ranked candidate IDs directly, with no deterministic repair.",
    "llm_tools": "Adds computed tool-summary fields to the candidate rows before prompting the model.",
    "llm_validator": "Checks raw model output and deterministically repairs invalid or missing slots where possible, without hidden activity.",
    "llm_tools_validator": "Combines tool-summary candidate rows with deterministic validation and repair.",
}


CONDITION_METADATA = {
    "openai_frontier_selector": {
        "provider": "openai",
        "model": "gpt-5.5",
        "profile": "low reasoning, Direct JSON",
        "description": "Direct JSON prompt profile. OpenAI minimal reasoning was rejected in preflight, so this condition uses the predefined low-reasoning fallback.",
    },
    "anthropic_frontier_selector": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "profile": "no extended thinking, Direct JSON",
        "description": "Direct JSON prompt profile without Anthropic extended thinking.",
    },
    "deepseek_frontier_selector": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "thinking off, Direct JSON",
        "description": "Direct JSON prompt profile with DeepSeek thinking disabled.",
    },
    "openai_frontier": {
        "provider": "openai",
        "model": "gpt-5.5",
        "profile": "high reasoning, original full-pool prompt",
        "description": "Original full-pool prompt condition with OpenAI high reasoning. Some rows are diagnostic interface failures where reasoning consumed the visible output budget.",
    },
    "anthropic_frontier": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "profile": "original full-pool prompt, no explicit thinking budget",
        "description": "Original full-pool prompt condition using the configured Anthropic frontier model without an explicit extended-thinking budget.",
    },
    "deepseek_frontier": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "high reasoning, thinking on, original full-pool prompt",
        "description": "Original full-pool prompt condition with DeepSeek thinking enabled. Some rows are diagnostic interface or provider-output failures.",
    },
    "openai_fast": {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "profile": "low reasoning, fast model",
        "description": "Lower-cost/lower-latency OpenAI condition used for fast matrix comparison.",
    },
    "anthropic_fast": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "profile": "fast model",
        "description": "Lower-cost/lower-latency Anthropic condition used for fast matrix comparison.",
    },
    "deepseek_fast": {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "profile": "thinking off, fast model",
        "description": "Lower-cost/lower-latency DeepSeek condition with thinking disabled.",
    },
    "openai_frontier_reasoning_budget": {
        "provider": "openai",
        "model": "gpt-5.5",
        "profile": "low reasoning, long output budget pilot, Direct JSON",
        "description": "Pilot-only reasoning-budget condition, not part of the consolidated LO result.",
    },
    "anthropic_frontier_thinking_8k": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "profile": "8k extended thinking budget pilot, Direct JSON",
        "description": "Pilot-only extended-thinking condition, not part of the consolidated LO result.",
    },
    "deepseek_frontier_thinking_32k": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "thinking on, long output budget pilot, Direct JSON",
        "description": "Pilot-only thinking-budget condition, not part of the consolidated LO result.",
    },
}


METRIC_DESCRIPTIONS = {
    "feasible_utility": "Final utility after any validator repair. Sums hidden activity for selected candidates that satisfy hard constraints. Higher is better.",
    "raw_feasible_utility": "Utility before validator repair. This is the closer measure of raw LLM behavior. Higher is better.",
    "ndcg_at_k": "Final ranking quality using hidden activity as graded relevance. 1.0 is ideal.",
    "raw_ndcg_at_k": "NDCG before validator repair.",
    "constrained_regret": "Oracle valid top-k utility minus observed feasible utility. Lower is better.",
    "compliance_rate": "Fraction of requested selections that are valid after final repair, if repair applies.",
    "raw_compliance_rate": "Fraction of requested selections that are valid before validator repair.",
    "schema_error_rate": "Fraction of cards with final output schema or contract errors.",
    "raw_schema_error_rate": "Fraction of cards with raw output schema or contract errors.",
    "repaired_rate": "Fraction of cards where the final validator changed the raw model output.",
    "repaired_from_empty_rate": "Fraction of cards where an empty raw model selection was repaired. Near zero is expected for a usable LLM interface.",
}


METRIC_EXAMPLES = {
    "feasible_utility": "Example: k=3 and the final valid selections have hidden activities 7.2, 6.8, and 0.0 for an invalid or missing slot. feasible_utility = 7.2 + 6.8 + 0.0 = 14.0.",
    "raw_feasible_utility": "Same calculation as feasible_utility, but applied to the model's raw output before deterministic validator repair.",
    "ndcg_at_k": "Example: the best possible valid ranking has DCG=18.0 and the system ranking has DCG=14.4. NDCG@k = 14.4 / 18.0 = 0.80.",
    "raw_ndcg_at_k": "Same NDCG@k calculation, but on the raw model output before validator repair.",
    "constrained_regret": "Example: the hidden-activity oracle can reach 90.0 feasible utility and a system reaches 76.0. constrained_regret = 90.0 - 76.0 = 14.0.",
    "compliance_rate": "Example: budget k=10 and 9 final selections are valid candidate IDs satisfying all hard constraints. compliance_rate = 9 / 10 = 0.90.",
    "raw_compliance_rate": "Same compliance calculation, but on the raw model output before validator repair.",
    "schema_error_rate": "Example: if a card has a malformed final output, wrong k, or missing candidate IDs, schema_error_rate=1 for that card; otherwise 0. Run summaries average this over cards.",
    "raw_schema_error_rate": "Same schema/contract error calculation, but before validator repair.",
    "repaired_rate": "Example: if validator repair changed 12 out of 50 raw card outputs, repaired_rate = 12 / 50 = 0.24.",
    "repaired_from_empty_rate": "Example: if 2 out of 50 cards had an empty raw selection list that was filled by repair, repaired_from_empty_rate = 2 / 50 = 0.04.",
}


def _attr(value: object) -> str:
    return escape(str(value), quote=True).replace("\n", "&#10;")


def _term(label: str, tooltip: str, *, example: str = "", title: str | None = None) -> str:
    title_attr = f' data-tooltip-title="{_attr(title)}"' if title else ""
    example_attr = f' data-example="{_attr(example)}"' if example else ""
    return (
        f'<span class="term" tabindex="0"{title_attr} '
        f'data-tooltip="{_attr(tooltip)}"{example_attr}>{escape(label)}</span>'
    )


def _base_system_name(system_name: str) -> str:
    return system_name.split("__", 1)[0]


def _condition_name(system_name: str) -> str:
    if "__" not in system_name:
        return ""
    return system_name.split("__", 1)[1]


def _system_group(system_name: str) -> str:
    base = _base_system_name(system_name)
    if _is_oracle_system(system_name):
        return "Oracle"
    if base.startswith("qsar_"):
        return "QSAR"
    if base in {"random_valid", "rules_only", "similarity_to_best_active"}:
        return "Baseline"
    if base.startswith("llm_") or base == "bare_llm":
        return "LLM"
    return "Other"


def _system_provider(system_name: str) -> str:
    condition = _condition_name(system_name)
    for provider in ["openai", "anthropic", "deepseek"]:
        if condition.startswith(provider):
            return provider
    return ""


def _title_provider(provider: object) -> str:
    provider_name = str(provider or "")
    return {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "deepseek": "DeepSeek",
    }.get(provider_name, provider_name.title() if provider_name else "")


def _condition_metadata(condition: str) -> dict[str, str]:
    return CONDITION_METADATA.get(condition, {})


def _condition_label_from_row(row: pd.Series | dict[str, object]) -> str:
    system_name = str(row.get("system_name", ""))
    condition = _condition_name(system_name)
    if not condition:
        return ""
    metadata = _condition_metadata(condition)
    provider = row.get("llm_provider") or metadata.get("provider") or _system_provider(system_name)
    model = row.get("llm_model") or metadata.get("model") or condition
    provider_label = _title_provider(provider)
    profile = metadata.get("profile")
    if provider_label and model and profile:
        return f"{provider_label} {model}, {profile}"
    if provider_label and model:
        return f"{provider_label} {model}"
    return condition


def _condition_description(condition: str) -> str:
    if not condition:
        return ""
    metadata = _condition_metadata(condition)
    if metadata:
        return metadata["description"]
    return f"Model/run condition: {condition}."


def _system_display_label_from_row(row: pd.Series | dict[str, object]) -> str:
    system_name = str(row.get("system_name", ""))
    base = _base_system_name(system_name)
    base_label = SYSTEM_LABELS.get(base, system_name)
    condition_label = _condition_label_from_row(row)
    if condition_label:
        return f"{base_label} - {condition_label}"
    return base_label


def _system_description_from_row(row: pd.Series | dict[str, object]) -> str:
    system_name = str(row.get("system_name", ""))
    base = _base_system_name(system_name)
    description = SYSTEM_DESCRIPTIONS.get(base, "System row from the comparison table.")
    condition = _condition_description(_condition_name(system_name))
    if condition:
        return f"{description} Model condition: {_condition_label_from_row(row)}. {condition} Raw run ID: {system_name}."
    return description


def _add_display_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "system_name" not in frame.columns:
        return frame
    enriched = frame.copy()
    enriched["system_group"] = [str(_system_group(str(row.get("system_name", "")))) for _, row in enriched.iterrows()]
    enriched["display_label"] = [_system_display_label_from_row(row) for _, row in enriched.iterrows()]
    enriched["condition_label"] = [_condition_label_from_row(row) for _, row in enriched.iterrows()]
    enriched["condition_description"] = [
        _condition_description(_condition_name(str(row.get("system_name", "")))) for _, row in enriched.iterrows()
    ]
    return enriched


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dashboard_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    frame = _add_display_columns(frame)
    numeric_columns = [
        "feasible_utility",
        "raw_feasible_utility",
        "ndcg_at_k",
        "raw_ndcg_at_k",
        "constrained_regret",
        "compliance_rate",
        "raw_compliance_rate",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_rate",
        "repaired_from_empty_rate",
    ]
    for _, row in frame.iterrows():
        system_name = str(row.get("system_name", ""))
        base = _base_system_name(system_name)
        output: dict[str, object] = {
            "system_name": system_name,
            "base_system": base,
            "display_name": str(row.get("display_label") or _system_display_label_from_row(row)),
            "condition": _condition_name(system_name),
            "condition_label": str(row.get("condition_label") or _condition_label_from_row(row)),
            "provider": _system_provider(system_name),
            "group": _system_group(system_name),
            "description": _system_description_from_row(row),
        }
        for column in numeric_columns:
            output[column] = _safe_float(row.get(column)) if column in frame.columns else None
        rows.append(output)
    return rows


def _json_for_html(value: object) -> str:
    return json.dumps(value, sort_keys=True).replace("<", "\\u003c")


def _optional_csv_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    if frame.empty:
        return []
    return frame.replace({np.nan: None}).to_dict(orient="records")


def write_results_dashboard(
    comparison_csv: Path,
    out_dir: Path,
    *,
    title: str = "SpecGuard-Chem v2 Results Dashboard",
) -> Path:
    frame = pd.read_csv(comparison_csv)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
    rows = _dashboard_rows(frame)
    table_dir = comparison_csv.parent
    paired_rows = _optional_csv_records(table_dir / "paired_bootstrap_key_deltas.csv")
    card_key_rows = _optional_csv_records(table_dir / "card_level_key_systems.csv")
    card_diagnostic_rows = _optional_csv_records(table_dir / "card_level_diagnostics.csv")
    failure_rows = _optional_csv_records(table_dir / "failure_taxonomy_summary.csv")
    generated_at = datetime.now(timezone.utc).isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "RESULTS_DASHBOARD.html"
    plotly_js = get_plotlyjs()
    run_pipeline_term = _term(
        "Run Pipeline",
        "The reproducible path from frozen decision cards to scored result artifacts.",
        example="cards.jsonl -> run traces.jsonl -> score summary.json -> comparison CSV -> dashboard/report",
    )
    decision_cards_term = _term(
        "1. Decision cards",
        "One benchmark instance: support compounds, candidate pool, hard constraints, budget k, and hidden scorer-only activity values.",
        example='{\n  "task_id": "CARA_LO_assay_0001",\n  "budget_k": 10,\n  "support_set": [{"id": "S001", "smiles": "...", "pIC50": 6.4}],\n  "candidate_pool": [{"id": "C017", "mw": 412.2, "clogp": 3.1}],\n  "hard_constraints": ["MW <= 500", "cLogP <= 4.5", "no support compounds"]\n}',
    )
    system_output_term = _term(
        "2. System output",
        "The runnable system returns an ordered batch of candidate IDs. Baselines produce this deterministically; LLM rows produce it from the prompt response.",
        example='{\n  "selections": [\n    {"rank": 1, "candidate_id": "C017", "confidence": 0.72},\n    {"rank": 2, "candidate_id": "C042", "confidence": 0.61}\n  ]\n}',
    )
    raw_audit_term = _term(
        "3. Raw audit",
        "Scores and records the model output before deterministic validator repair, so repaired behavior is not mistaken for raw model behavior.",
        example="raw_output: C017, C017, S003\nraw_issues: duplicate C017; support compound S003; fewer than k unique valid candidate IDs",
    )
    validator_term = _term(
        "4. Validator",
        "Deterministic harness logic for schema, candidate IDs, duplicates, support-set exclusion, and RDKit/property constraints. It does not use hidden activity.",
        example="kept: C017\nrejected: duplicate C017, support compound S003\nfilled missing slots from fallback_ranking(card)\nvalidator_repaired: true",
    )
    scoring_term = _term(
        "5. Scoring",
        "Computes utility, ranking quality, compliance, regret, repair rates, and comparison tables from the final output and raw output where available.",
        example="feasible_utility = sum(hidden activity for valid selected IDs)\ncompliance_rate = valid_selected_count / budget_k\nconstrained_regret = oracle_valid_topk_utility - feasible_utility",
    )
    table_terms = {
        "feasible_utility": _term(
            "Utility",
            METRIC_DESCRIPTIONS["feasible_utility"],
            example=METRIC_EXAMPLES["feasible_utility"],
            title="feasible_utility",
        ),
        "raw_feasible_utility": _term(
            "Raw utility",
            METRIC_DESCRIPTIONS["raw_feasible_utility"],
            example=METRIC_EXAMPLES["raw_feasible_utility"],
            title="raw_feasible_utility",
        ),
        "ndcg_at_k": _term(
            "NDCG",
            METRIC_DESCRIPTIONS["ndcg_at_k"],
            example=METRIC_EXAMPLES["ndcg_at_k"],
            title="ndcg_at_k",
        ),
        "compliance_rate": _term(
            "Compliance",
            METRIC_DESCRIPTIONS["compliance_rate"],
            example=METRIC_EXAMPLES["compliance_rate"],
            title="compliance_rate",
        ),
        "raw_compliance_rate": _term(
            "Raw compliance",
            METRIC_DESCRIPTIONS["raw_compliance_rate"],
            example=METRIC_EXAMPLES["raw_compliance_rate"],
            title="raw_compliance_rate",
        ),
        "repaired_rate": _term(
            "Repaired",
            METRIC_DESCRIPTIONS["repaired_rate"],
            example=METRIC_EXAMPLES["repaired_rate"],
            title="repaired_rate",
        ),
    }
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #64717f;
      --line: #d7ddd8;
      --oracle: #111827;
      --qsar: #2563eb;
      --baseline: #0f766e;
      --llm: #b91c1c;
      --other: #6b7280;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    h1 {{ margin: 0 0 6px; font-size: 24px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 17px; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; }}
    .subtle {{ color: var(--muted); }}
    main {{ max-width: 1480px; margin: 0 auto; padding: 22px 24px 36px; }}
    .grid {{ display: grid; gap: 16px; }}
    .summary-grid {{ grid-template-columns: repeat(4, minmax(180px, 1fr)); }}
    .plot-grid {{ grid-template-columns: minmax(560px, 1.4fr) minmax(340px, 0.9fr); }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
    }}
    .stat-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .stat-value {{ margin-top: 6px; font-size: 24px; font-weight: 700; }}
    .stat-note {{ margin-top: 4px; color: var(--muted); font-size: 12px; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 10px 16px; margin: 10px 0 0; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }}
    .swatch {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }}
    select, input {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 9px;
      background: #ffffff;
      color: var(--ink);
    }}
    svg {{ width: 100%; height: auto; display: block; }}
    .axis text {{ fill: var(--muted); font-size: 11px; }}
    .axis line, .axis path {{ stroke: var(--line); }}
    .bar-row {{ display: grid; grid-template-columns: minmax(180px, 1fr) 120px; gap: 10px; align-items: center; margin: 8px 0; }}
    .bar-track {{ height: 18px; background: #eef1ed; border-radius: 5px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 5px; }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); }}
    .bar-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .flow {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; align-items: stretch; }}
    .flow-step {{ border: 1px solid var(--line); border-radius: 7px; padding: 10px; background: #fbfcfa; min-height: 86px; }}
    .flow-step strong {{ display: block; margin-bottom: 4px; }}
    .flow-step small {{ color: var(--muted); }}
    .hypothesis-grid {{ display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 12px; }}
    .hypothesis {{
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fbfcfa;
      padding: 12px;
    }}
    .hypothesis-title {{ display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }}
    .hypothesis-title strong {{ font-size: 14px; }}
    .status {{ border-radius: 999px; color: #fff; display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; white-space: nowrap; }}
    .status-supported {{ background: #0f766e; }}
    .status-partial {{ background: #a16207; }}
    .status-caveat {{ background: #475569; }}
    .evidence {{ color: var(--muted); margin: 0; }}
    .term {{
      border-bottom: 1px dotted var(--muted);
      cursor: help;
      text-decoration: none;
      position: relative;
    }}
    .rich-tooltip {{
      background: #17202a;
      border-radius: 6px;
      box-shadow: 0 8px 24px rgba(31, 41, 51, 0.22);
      color: #ffffff;
      display: none;
      font-size: 12px;
      font-weight: 500;
      line-height: 1.35;
      max-width: min(460px, calc(100vw - 24px));
      opacity: 0;
      padding: 10px 12px;
      pointer-events: none;
      position: fixed;
      text-transform: none;
      transform: translateY(-4px);
      transition: opacity 120ms ease, transform 120ms ease;
      white-space: normal;
      z-index: 1000;
    }}
    .rich-tooltip.visible {{
      display: block;
      opacity: 1;
      transform: translateY(0);
    }}
    .rich-tooltip-title {{
      color: #ffffff;
      font-weight: 800;
      margin-bottom: 4px;
    }}
    .rich-tooltip-body {{ color: #edf2f0; }}
    .rich-tooltip-example {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: 5px;
      color: #f8fafc;
      font: 11px/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      margin: 8px 0 0;
      overflow-x: auto;
      padding: 8px;
      white-space: pre-wrap;
    }}
    .metric-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 4px 0 12px;
    }}
    .metric-chip {{
      background: #edf0ec;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--ink);
      display: inline-flex;
      font-size: 12px;
      padding: 3px 8px;
    }}
    .chart {{ min-height: 420px; }}
    .side-chart {{ min-height: 520px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: #fbfcfa; position: sticky; top: 0; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 2px 7px; font-size: 12px; color: #fff; }}
    .Oracle {{ background: var(--oracle); }}
    .QSAR {{ background: var(--qsar); }}
    .Baseline {{ background: var(--baseline); }}
    .LLM {{ background: var(--llm); }}
    .Other {{ background: var(--other); }}
    details {{ margin-top: 16px; }}
    summary {{ cursor: pointer; font-weight: 600; }}
    code {{ background: #edf0ec; padding: 1px 4px; border-radius: 4px; }}
    @media (max-width: 980px) {{
      .summary-grid, .plot-grid, .flow, .hypothesis-grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 16px; }}
      header {{ padding: 22px 18px 14px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="subtle">Generated at <code>{escape(generated_at)}</code> from <code>{escape(str(comparison_csv))}</code></div>
  </header>
  <main>
    <section class="grid summary-grid" id="summaryCards"></section>

    <section class="panel" style="margin-top:16px">
      <h2>{run_pipeline_term}</h2>
      <div class="flow">
        <div class="flow-step"><strong>{decision_cards_term}</strong><small>Support set, candidate pool, hard constraints, and budget k.</small></div>
        <div class="flow-step"><strong>{system_output_term}</strong><small>Baselines or LLMs return ranked candidate IDs.</small></div>
        <div class="flow-step"><strong>{raw_audit_term}</strong><small>Raw LLM selections are scored before repair where available.</small></div>
        <div class="flow-step"><strong>{validator_term}</strong><small>Deterministic schema, ID, duplicate, support-exclusion, and RDKit/property checks.</small></div>
        <div class="flow-step"><strong>{scoring_term}</strong><small>Utility, compliance, regret, repair rate, and frontier plots.</small></div>
      </div>
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>Original Hypotheses and Evidence</h2>
      <p class="subtle">This panel links the completed comparison table back to the project brief. It is descriptive, not a replacement for statistical analysis in the manuscript.</p>
      <div id="hypotheses" class="hypothesis-grid"></div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px" id="pairedBootstrapSection">
      <div class="panel">
        <h2><span class="term" tabindex="0" data-tooltip="Paired bootstrap resamples the same decision cards for two systems and estimates the confidence interval for their per-card metric difference.">Paired Card-Level Bootstrap</span></h2>
        <p class="subtle">Positive bars mean system A outperformed system B on the same cards.</p>
        <div id="pairedBootstrapBars" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Key Deltas</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Comparison</th>
                <th>Metric</th>
                <th>System A</th>
                <th>System B</th>
                <th>Delta</th>
                <th>95% interval</th>
              </tr>
            </thead>
            <tbody id="pairedBootstrapRows"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px" id="cardDiagnosticsSection">
      <div class="panel">
        <h2><span class="term" tabindex="0" data-tooltip="Per-card feasible utility distribution for key systems. This shows whether aggregate results are driven by many cards or a few outliers.">Card-Level Utility Distribution</span></h2>
        <div id="cardUtilityBoxes" class="chart"></div>
      </div>
      <div class="panel">
        <h2>QSAR Versus LLM By Card</h2>
        <p class="subtle">Points above the diagonal favor the LLM; points below favor QSAR.</p>
        <div id="qsarLlmScatter" class="chart"></div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px" id="failureTaxonomySection">
      <div class="panel">
        <h2><span class="term" tabindex="0" data-tooltip="Aggregated validation-failure classes across cards. This summarizes final-output contract and constraint failures; raw/final repair effects are shown separately.">Failure Taxonomy</span></h2>
        <div id="failureTaxonomyBars" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Top Failure Rows</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>System</th>
                <th>Failure type</th>
                <th>Cards</th>
                <th>Card rate</th>
                <th>Issues/card</th>
              </tr>
            </thead>
            <tbody id="failureTaxonomyRows"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2><span class="term" tabindex="0" data-tooltip="Scatter plot separating specification compliance on the x-axis from medicinal-chemistry decision utility on the y-axis.">Compliance-Utility Frontier</span></h2>
        <div class="controls">
          <label>{_term("Y metric", "Metric plotted on the vertical axis. Hover the selected metric chip below for the calculation.")}
            <select id="yMetric">
              <option value="feasible_utility">Final feasible utility</option>
              <option value="raw_feasible_utility">Raw feasible utility</option>
              <option value="ndcg_at_k">Final NDCG@k</option>
              <option value="raw_ndcg_at_k">Raw NDCG@k</option>
            </select>
          </label>
          <label>{_term("X metric", "Metric plotted on the horizontal axis. Hover the selected metric chip below for the calculation.")}
            <select id="xMetric">
              <option value="compliance_rate">Final compliance</option>
              <option value="raw_compliance_rate">Raw compliance</option>
              <option value="schema_error_rate">Final schema error</option>
              <option value="raw_schema_error_rate">Raw schema error</option>
            </select>
          </label>
          <label>{_term("X scale", "How the x-axis is transformed. Log gap to 1.0 expands values clustered near perfect compliance; log value expands small error rates.")}
            <select id="xScale">
              <option value="auto" selected>Auto log for clustered rates</option>
              <option value="linear">Linear</option>
              <option value="log_gap">Log gap to 1.0</option>
              <option value="log_value">Log value</option>
            </select>
          </label>
          <label>
            <span class="term" tabindex="0" data-tooltip="Switches the LLM scatter points between final scored outputs, raw model outputs, or both connected by repair links. Deterministic baselines remain shown as context.">LLM point view</span>
            <select id="repairPointView">
              <option value="final" selected>Final scored points</option>
              <option value="raw">Raw LLM points</option>
              <option value="both">Raw + final repair links</option>
            </select>
          </label>
        </div>
        <div class="metric-chip-row" id="selectedMetricDefinitions"></div>
        <p class="subtle" id="repairLinkNote">Showing final scored outputs. For validator rows, final points may include deterministic repair.</p>
        <div id="scatter" class="chart"></div>
        <div class="legend" id="legend"></div>
      </div>
      <div class="panel">
        <h2>Top <span class="term" tabindex="0" data-tooltip="Primary systems exclude oracle controls. They are the deployable or prospectively runnable systems used for main comparisons.">Primary Systems</span></h2>
        <div id="leaderboard" class="side-chart"></div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2>Raw-to-Final Repair Delta</h2>
        <p class="subtle">Positive bars mean deterministic repair increased final feasible utility relative to raw model output.</p>
        <div id="repairBars" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Label Guide</h2>
        <p><strong><span class="term" tabindex="0" data-tooltip="Quantitative structure-activity relationship models: conventional molecular ML regressors, not language models. In this run they are trained independently for each decision card using only support-set compounds and measured support activity.">QSAR models:</span></strong> deployable non-language baselines trained separately per decision card on support-set Morgan fingerprints and measured activity. They predict candidate activity and rank feasible candidates; they do not see hidden candidate activity.</p>
        <p><code>qsar_rf</code> is a random forest regressor; <code>qsar_gbt</code> is a gradient-boosting regressor; <code>qsar_svm</code> is a sparse-scaled linear-kernel support-vector regressor. Their strength here supports QSAR as a serious comparator, not as ground truth or a universal activity model.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="Deterministic harness logic, not a model and not an activity oracle.">Validator:</span></strong> deterministic harness checks and repair. It does not inspect hidden activity values.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="A non-deployable control that uses hidden candidate activity values.">Oracle:</span></strong> hidden-activity upper bound used only to show remaining decision headroom.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="The current prompt profile: final answer JSON only, without relying on visible chain-of-thought text.">Direct JSON:</span></strong> final-answer JSON prompting designed to avoid visible-output budget failures.</p>
      </div>
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>System Table</h2>
      <div class="controls">
        <label>Group
          <select id="groupFilter">
            <option value="all">All groups</option>
            <option value="Oracle">Oracle</option>
            <option value="QSAR">QSAR</option>
            <option value="Baseline">Baseline</option>
            <option value="LLM">LLM</option>
          </select>
        </label>
        <label>Search
          <input id="searchBox" type="search" placeholder="system, provider, metric label">
        </label>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>System</th>
              <th>Group</th>
              <th>{table_terms["feasible_utility"]}</th>
              <th>{table_terms["raw_feasible_utility"]}</th>
              <th>{table_terms["ndcg_at_k"]}</th>
              <th>{table_terms["compliance_rate"]}</th>
              <th>{table_terms["raw_compliance_rate"]}</th>
              <th>{table_terms["repaired_rate"]}</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody id="systemRows"></tbody>
        </table>
      </div>
    </section>

    <details class="panel">
      <summary>Metric definitions</summary>
      <dl id="metricDefinitions"></dl>
    </details>
    <div id="richTooltip" class="rich-tooltip" role="tooltip" aria-hidden="true"></div>
  </main>
  <script>
{plotly_js}
  </script>
  <script>
    const rows = {_json_for_html(rows)};
    const pairedRows = {_json_for_html(paired_rows)};
    const cardKeyRows = {_json_for_html(card_key_rows)};
    const cardDiagnosticRows = {_json_for_html(card_diagnostic_rows)};
    const failureRows = {_json_for_html(failure_rows)};
    const metricHelp = {_json_for_html(METRIC_DESCRIPTIONS)};
    const metricExamples = {_json_for_html(METRIC_EXAMPLES)};
    const colors = {{Oracle: "#111827", QSAR: "#2563eb", Baseline: "#0f766e", LLM: "#b91c1c", Other: "#6b7280"}};

    const fmt = (value, digits = 3) => value === null || value === undefined || Number.isNaN(value) ? "" : Number(value).toFixed(digits);
    const primaryRows = () => rows.filter(row => row.group !== "Oracle");
    const byMetricDesc = metric => [...rows].filter(row => row[metric] !== null).sort((a, b) => b[metric] - a[metric]);
    const labelFor = row => row?.display_name || row?.system_name || "n/a";

    function bestBy(metric, filterFn = () => true) {{
      return rows.filter(row => filterFn(row) && row[metric] !== null).sort((a, b) => b[metric] - a[metric])[0] || null;
    }}

    function renderSummary() {{
      const oracle = bestBy("feasible_utility", row => row.group === "Oracle");
      const primary = bestBy("feasible_utility", row => row.group !== "Oracle");
      const rawLlm = bestBy("raw_feasible_utility", row => row.group === "LLM");
      const repairSensitive = rows.filter(row => row.repaired_rate !== null && row.repaired_rate >= 0.1).length;
      const cards = [
        [metricTerm("feasible_utility", "Best primary utility"), primary ? fmt(primary.feasible_utility) : "", primary ? escapeHtml(labelFor(primary)) : ""],
        [metricTerm("feasible_utility", "Oracle utility"), oracle ? fmt(oracle.feasible_utility) : "", "Upper bound, not deployable"],
        [metricTerm("raw_feasible_utility", "Best raw LLM utility"), rawLlm ? fmt(rawLlm.raw_feasible_utility) : "", rawLlm ? escapeHtml(labelFor(rawLlm)) : ""],
        [metricTerm("repaired_rate", "Repair-sensitive rows"), String(repairSensitive), "Rows with repaired_rate >= 0.10"]
      ];
      document.getElementById("summaryCards").innerHTML = cards.map(card => `
        <div class="panel">
          <div class="stat-label">${{card[0]}}</div>
          <div class="stat-value">${{card[1]}}</div>
          <div class="stat-note">${{card[2]}}</div>
        </div>`).join("");
    }}

    function rowByName(name) {{
      return rows.find(row => row.system_name === name) || null;
    }}

    function bestRow(metric, filterFn = () => true) {{
      return rows
        .filter(row => filterFn(row) && row[metric] !== null)
        .sort((a, b) => b[metric] - a[metric])[0] || null;
    }}

    function metricRange(metric, filterFn = () => true) {{
      const values = rows.filter(row => filterFn(row) && row[metric] !== null).map(row => row[metric]);
      if (!values.length) return null;
      return {{min: Math.min(...values), max: Math.max(...values)}};
    }}

    function renderHypotheses() {{
      const bestQsar = bestRow("feasible_utility", row => row.group === "QSAR");
      const bestLlmFinal = bestRow("feasible_utility", row => row.group === "LLM");
      const bestRawLlm = bestRow("raw_feasible_utility", row => row.group === "LLM");
      const similarity = rowByName("similarity_to_best_active");
      const bareOpenai = rowByName("bare_llm__openai_frontier_selector");
      const toolsOpenai = rowByName("llm_tools__openai_frontier_selector");
      const validatorOpenai = rowByName("llm_validator__openai_frontier_selector");
      const repairRows = rows
        .filter(row => row.raw_feasible_utility !== null && row.feasible_utility !== null)
        .map(row => ({{...row, delta: row.feasible_utility - row.raw_feasible_utility}}))
        .sort((a, b) => b.delta - a.delta);
      const biggestRepair = repairRows[0];
      const perfectComplianceRange = metricRange("feasible_utility", row => row.group !== "Oracle" && row.compliance_rate !== null && row.compliance_rate >= 0.999);
      const hypotheses = [
        {{
          label: "H1",
          status: "Supported",
          statusClass: "status-supported",
          title: "Validators raise compliance more reliably than utility.",
          evidence: biggestRepair
            ? `Largest observed raw-to-final ${{metricTerm("feasible_utility", "utility")}} shift is ${{escapeHtml(labelFor(biggestRepair))}}: +${{fmt(biggestRepair.delta)}} feasible utility, with ${{metricTerm("repaired_rate", "repaired_rate")}} ${{fmt(biggestRepair.repaired_rate)}}. These final scores are guarded-system behavior, not raw model behavior.`
            : "Raw-to-final repair data were not available for this table."
        }},
        {{
          label: "H2",
          status: "Supported",
          statusClass: "status-supported",
          title: "Simple QSAR and similarity baselines are competitive.",
          evidence: `Best QSAR is ${{escapeHtml(labelFor(bestQsar))}} at ${{fmt(bestQsar?.feasible_utility)}} ${{metricTerm("feasible_utility", "feasible utility")}}; best LLM final is ${{escapeHtml(labelFor(bestLlmFinal))}} at ${{fmt(bestLlmFinal?.feasible_utility)}}; similarity-to-best-active is ${{fmt(similarity?.feasible_utility)}}.`
        }},
        {{
          label: "H3",
          status: "Partial",
          statusClass: "status-partial",
          title: "The best LLM system is likely hybrid, not a naked LLM.",
          evidence: `For OpenAI direct JSON, bare LLM is ${{fmt(bareOpenai?.feasible_utility)}}, tools-only is ${{fmt(toolsOpenai?.feasible_utility)}}, and validator-assisted is ${{fmt(validatorOpenai?.feasible_utility)}} on ${{metricTerm("feasible_utility", "feasible utility")}}. Hybrid/guarded LLM rows improve on bare LLMs, but none beats the best QSAR baseline.`
        }},
        {{
          label: "H4",
          status: "Supported",
          statusClass: "status-supported",
          title: "Compliance and utility are imperfectly correlated.",
          evidence: perfectComplianceRange
            ? `Among non-oracle rows with final ${{metricTerm("compliance_rate", "compliance")}} near 1.0, ${{metricTerm("feasible_utility", "feasible utility")}} ranges from ${{fmt(perfectComplianceRange.min)}} to ${{fmt(perfectComplianceRange.max)}}. Perfect compliance alone does not imply strong prioritisation utility.`
            : "No near-perfect compliance rows were available."
        }},
        {{
          label: "Central contention",
          status: "Caveat",
          statusClass: "status-caveat",
          title: "Compliance is not utility.",
          evidence: `The current results support the audit framing: direct-JSON LLMs can become valid and useful, but best raw LLM ${{metricTerm("raw_feasible_utility", "utility")}} (${{fmt(bestRawLlm?.raw_feasible_utility)}}) remains below best QSAR ${{metricTerm("feasible_utility", "utility")}} (${{fmt(bestQsar?.feasible_utility)}}), and validator repair can materially change final scores.`
        }}
      ];
      document.getElementById("hypotheses").innerHTML = hypotheses.map(item => `
        <article class="hypothesis">
          <div class="hypothesis-title">
            <strong>${{item.label}}: ${{item.title}}</strong>
            <span class="status ${{item.statusClass}}">${{item.status}}</span>
          </div>
          <p class="evidence">${{item.evidence}}</p>
        </article>`).join("");
    }}

    function effectiveXScale(metric, requested) {{
      if (requested !== "auto") return requested;
      if (metric.includes("compliance")) return "log_gap";
      if (metric.includes("schema_error")) return "log_value";
      return "linear";
    }}

    function transformX(value, metric, mode) {{
      const epsilon = 1e-4;
      if (mode === "log_gap") return -Math.log10(Math.max(epsilon, 1 - value));
      if (mode === "log_value") return Math.log10(Math.max(epsilon, value));
      return value;
    }}

    function xTickValues(metric, mode) {{
      if (mode === "log_gap") return [0, 0.9, 0.99, 0.999, 1.0];
      if (mode === "log_value") return [0, 0.001, 0.01, 0.1, 1.0];
      return [0, 0.25, 0.5, 0.75, 1.0];
    }}

    function xTickLabel(value, mode) {{
      if (mode === "log_gap") return value === 1 ? "1.000" : fmt(value, value >= 0.99 ? 3 : 2);
      if (mode === "log_value") return value === 0 ? "0" : String(value);
      return fmt(value, 2);
    }}

    function xAxisLabel(metric, mode) {{
      if (mode === "log_gap") return `${{metric}}<br>(log distance from 1.0; right is better)`;
      if (mode === "log_value") return `${{metric}} (log value)`;
      return metric;
    }}

    function rawMetricFor(metric) {{
      const mapping = {{
        feasible_utility: "raw_feasible_utility",
        ndcg_at_k: "raw_ndcg_at_k",
        compliance_rate: "raw_compliance_rate",
        schema_error_rate: "raw_schema_error_rate"
      }};
      return mapping[metric] || metric;
    }}

    function renderSelectedMetricDefinitions() {{
      const xMetric = document.getElementById("xMetric").value;
      const yMetric = document.getElementById("yMetric").value;
      const xMode = effectiveXScale(xMetric, document.getElementById("xScale").value);
      const chips = [
        `<span class="metric-chip">Y: ${{metricCodeTerm(yMetric)}}</span>`,
        `<span class="metric-chip">X: ${{metricCodeTerm(xMetric)}}</span>`,
        `<span class="metric-chip">${{termHtml("scale: " + xMode, "The selected x-axis transform. log_gap plots -log10(1 - value), which spreads values clustered close to 1.0. log_value plots log10(value), which spreads small error rates.", "linear: value is unchanged\\nlog_gap: compliance 0.99 becomes 2.0 because -log10(0.01)=2\\nlog_value: schema error 0.01 becomes -2.0 because log10(0.01)=-2")}}</span>`,
      ];
      document.getElementById("selectedMetricDefinitions").innerHTML = chips.join("");
    }}

    function hasRawPoint(row, rawXMetric, rawYMetric) {{
      return row[rawXMetric] !== null && row[rawXMetric] !== undefined && row[rawYMetric] !== null && row[rawYMetric] !== undefined;
    }}

    function wrapPlotLabel(value, maxLineLength = 24) {{
      const text = String(value);
      const chunks = text.split("__");
      const lines = [];
      let current = "";
      for (const chunk of chunks) {{
        const part = current ? "__" + chunk : chunk;
        if (current && current.length + part.length > maxLineLength) {{
          lines.push(current);
          current = chunk;
        }} else {{
          current += part;
        }}
      }}
      if (current) lines.push(current);
      const expanded = [];
      for (const line of lines) {{
        if (line.length <= maxLineLength + 8) {{
          expanded.push(line);
          continue;
        }}
        const pieces = line.split("_");
        let subline = "";
        for (const piece of pieces) {{
          const part = subline ? "_" + piece : piece;
          if (subline && subline.length + part.length > maxLineLength) {{
            expanded.push(subline);
            subline = piece;
          }} else {{
            subline += part;
          }}
        }}
        if (subline) expanded.push(subline);
      }}
      return expanded.join("<br>");
    }}

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function escapeAttr(value) {{
      return escapeHtml(value).replace(/\\n/g, "&#10;");
    }}

    function termHtml(label, tooltip, example = "", title = "") {{
      const titleAttr = title ? ` data-tooltip-title="${{escapeAttr(title)}}"` : "";
      const exampleAttr = example ? ` data-example="${{escapeAttr(example)}}"` : "";
      return `<span class="term" tabindex="0"${{titleAttr}} data-tooltip="${{escapeAttr(tooltip)}}"${{exampleAttr}}>${{escapeHtml(label)}}</span>`;
    }}

    function metricTerm(metric, label) {{
      return termHtml(label, metricHelp[metric] || metric, metricExamples[metric] || "", metric);
    }}

    function metricCodeTerm(metric) {{
      const tooltip = metricHelp[metric] || metric;
      const example = metricExamples[metric] || "";
      return `<code class="term" tabindex="0" data-tooltip-title="${{escapeAttr(metric)}}" data-tooltip="${{escapeAttr(tooltip)}}" data-example="${{escapeAttr(example)}}">${{escapeHtml(metric)}}</code>`;
    }}

    function wrapHoverText(value, maxLineLength = 68) {{
      const words = String(value || "").trim().split(/\\s+/).filter(Boolean);
      const lines = [];
      let current = "";
      for (const word of words) {{
        if (!current) {{
          current = word;
        }} else if (current.length + 1 + word.length > maxLineLength) {{
          lines.push(current);
          current = word;
        }} else {{
          current += " " + word;
        }}
      }}
      if (current) lines.push(current);
      return lines.map(escapeHtml).join("<br>");
    }}

    function wrapIdentifier(value, maxLineLength = 44) {{
      return wrapPlotLabel(value, maxLineLength).split("<br>").map(escapeHtml).join("<br>");
    }}

    function plotlyLayout(title, xTitle, yTitle, height = 460) {{
      return {{
        title: {{text: title, font: {{size: 15}}, x: 0}},
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "#fbfcfa",
        margin: {{l: 72, r: 24, t: 42, b: 68}},
        height,
        hovermode: "closest",
        hoverlabel: {{align: "left"}},
        legend: {{orientation: "h", y: -0.22}},
        font: {{family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: "#1f2933"}},
        xaxis: {{title: xTitle, gridcolor: "#e4e8e4", zerolinecolor: "#cbd5d0", automargin: true}},
        yaxis: {{title: yTitle, gridcolor: "#e4e8e4", zerolinecolor: "#cbd5d0", automargin: true}}
      }};
    }}

    const plotlyConfig = {{responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"]}};

    function renderScatter() {{
      const xMetric = document.getElementById("xMetric").value;
      const yMetric = document.getElementById("yMetric").value;
      const xMode = effectiveXScale(xMetric, document.getElementById("xScale").value);
      renderSelectedMetricDefinitions();
      const pointView = document.getElementById("repairPointView").value;
      const rawXMetric = rawMetricFor(xMetric);
      const rawYMetric = rawMetricFor(yMetric);
      const canShowRepair = rawXMetric !== xMetric || rawYMetric !== yMetric;
      const data = rows
        .map(row => {{
          const showRaw = pointView === "raw" && row.group === "LLM" && hasRawPoint(row, rawXMetric, rawYMetric);
          return {{
            ...row,
            plot_x: showRaw ? row[rawXMetric] : row[xMetric],
            plot_y: showRaw ? row[rawYMetric] : row[yMetric],
            point_kind: showRaw ? "raw LLM output" : "final scored output",
            marker_symbol: showRaw ? "circle-open" : "circle"
          }};
        }})
        .filter(row => row.plot_x !== null && row.plot_x !== undefined && row.plot_y !== null && row.plot_y !== undefined)
        .filter(row => pointView !== "raw" || row.group !== "LLM" || row.point_kind === "raw LLM output");
      const traces = [];
      const linkRows = rows.filter(row => hasRawPoint(row, rawXMetric, rawYMetric) && row[xMetric] !== null && row[xMetric] !== undefined && row[yMetric] !== null && row[yMetric] !== undefined);
      if (pointView === "both" && canShowRepair) {{
        linkRows.forEach((row, index) => traces.push({{
            type: "scatter",
            mode: "lines",
            name: "raw -> final repair",
            legendgroup: "repair_links",
            showlegend: index === 0,
            hoverinfo: "text",
            line: {{color: "#9aa5a1", width: 1.4, dash: "dot"}},
            opacity: 0.55,
            x: [transformX(row[rawXMetric], xMetric, xMode), transformX(row[xMetric], xMetric, xMode)],
            y: [row[rawYMetric], row[yMetric]],
            text: [`<b>${{wrapHoverText(labelFor(row), 44)}}</b><br>raw ${{escapeHtml(xMetric)}}: ${{fmt(row[rawXMetric])}}<br>raw ${{escapeHtml(yMetric)}}: ${{fmt(row[rawYMetric])}}<br>raw run ID: ${{wrapIdentifier(row.system_name)}}`, `<b>${{wrapHoverText(labelFor(row), 44)}}</b><br>final ${{escapeHtml(xMetric)}}: ${{fmt(row[xMetric])}}<br>final ${{escapeHtml(yMetric)}}: ${{fmt(row[yMetric])}}<br>raw run ID: ${{wrapIdentifier(row.system_name)}}`]
        }}));
        traces.push({{
          type: "scatter",
          mode: "markers",
          name: "raw output",
          legendgroup: "repair_links",
          x: linkRows.map(row => transformX(row[rawXMetric], xMetric, xMode)),
          y: linkRows.map(row => row[rawYMetric]),
          customdata: linkRows.map(row => [wrapHoverText(labelFor(row), 44), row[rawXMetric], row[rawYMetric], row[xMetric], row[yMetric], wrapIdentifier(row.system_name)]),
          hovertemplate: "<b>%{{customdata[0]}}</b><br>raw output<br>raw x: %{{customdata[1]:.3f}}<br>raw y: %{{customdata[2]:.3f}}<br>final x: %{{customdata[3]:.3f}}<br>final y: %{{customdata[4]:.3f}}<br>raw run ID: %{{customdata[5]}}<extra></extra>",
          marker: {{symbol: "circle-open", size: 11, color: "#64717f", line: {{color: "#64717f", width: 2}}}}
        }});
      }}
      for (const group of ["Oracle", "QSAR", "Baseline", "LLM", "Other"]) {{
        const groupRows = data.filter(row => row.group === group);
        if (!groupRows.length) continue;
        traces.push({{
          type: "scatter",
          mode: "markers",
          name: group,
          x: groupRows.map(row => transformX(row.plot_x, xMetric, xMode)),
          y: groupRows.map(row => row.plot_y),
          customdata: groupRows.map(row => [wrapHoverText(labelFor(row), 44), wrapHoverText(row.description), row.plot_x, row.plot_y, wrapHoverText(row.condition_label || row.condition || "none", 44), row.point_kind, wrapIdentifier(row.system_name)]),
          hovertemplate: "<b>%{{customdata[0]}}</b><br>%{{customdata[5]}}<br>%{{customdata[1]}}<br>" + xMetric + ": %{{customdata[2]:.3f}}<br>" + yMetric + ": %{{customdata[3]:.3f}}<br>condition: %{{customdata[4]}}<br>raw run ID: %{{customdata[6]}}<extra></extra>",
          marker: {{size: group === "Oracle" ? 15 : 11, color: colors[group] || colors.Other, symbol: groupRows.map(row => row.marker_symbol), opacity: 0.88, line: {{color: "#ffffff", width: 1}}}}
        }});
      }}
      const tickValues = xTickValues(xMetric, xMode);
      const layout = plotlyLayout("Compliance versus utility", xAxisLabel(xMetric, xMode), yMetric, 500);
      layout.xaxis.tickmode = "array";
      layout.xaxis.tickvals = tickValues.map(value => transformX(value, xMetric, xMode));
      layout.xaxis.ticktext = tickValues.map(value => xTickLabel(value, xMode));
      Plotly.react("scatter", traces, layout, plotlyConfig);
      const note = document.getElementById("repairLinkNote");
      if (pointView === "raw") {{
        note.textContent = "Showing raw LLM output points where raw metrics are available; LLM rows without raw metrics are omitted, while deterministic baselines and oracle controls remain as context.";
      }} else if (pointView === "both" && canShowRepair) {{
        note.textContent = "Open grey circles are raw LLM outputs. Dotted grey segments connect each raw point to that same system's final scored point.";
      }} else if (pointView === "both") {{
        note.textContent = "Raw-to-final repair links require a final metric with a matching raw metric. Use final utility/compliance or final NDCG/compliance to inspect repair movement.";
      }} else {{
        note.textContent = "Showing final scored outputs. For validator rows, final points may include deterministic repair.";
      }}
      document.getElementById("legend").innerHTML = "";
    }}

    function renderLeaderboard() {{
      const data = primaryRows().filter(row => row.feasible_utility !== null).sort((a, b) => b.feasible_utility - a.feasible_utility).slice(0, 16);
      const plotRows = [...data].reverse();
      const trace = {{
        type: "bar",
        orientation: "h",
        x: plotRows.map(row => row.feasible_utility),
        y: plotRows.map(row => labelFor(row)),
        marker: {{color: plotRows.map(row => colors[row.group] || colors.Other)}},
        customdata: plotRows.map(row => [wrapHoverText(row.description), row.ndcg_at_k, row.compliance_rate, wrapHoverText(labelFor(row), 44), wrapIdentifier(row.system_name)]),
        hovertemplate: "<b>%{{customdata[3]}}</b><br>%{{customdata[0]}}<br>utility: %{{x:.3f}}<br>NDCG@k: %{{customdata[1]:.3f}}<br>compliance: %{{customdata[2]:.3f}}<br>raw run ID: %{{customdata[4]}}<extra></extra>"
      }};
      const layout = plotlyLayout("Primary-system leaderboard", "feasible_utility", "", 560);
      layout.margin = {{l: 138, r: 24, t: 42, b: 52}};
      layout.showlegend = false;
      layout.yaxis.tickmode = "array";
      layout.yaxis.tickvals = plotRows.map(row => labelFor(row));
      layout.yaxis.ticktext = plotRows.map(row => wrapPlotLabel(labelFor(row), 26));
      layout.yaxis.tickfont = {{size: 11}};
      Plotly.react("leaderboard", [trace], layout, plotlyConfig);
    }}

    function renderRepairBars() {{
      const data = rows
        .filter(row => row.raw_feasible_utility !== null && row.feasible_utility !== null)
        .map(row => ({{...row, delta: row.feasible_utility - row.raw_feasible_utility}}))
        .filter(row => Math.abs(row.delta) > 0.0001)
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
        .slice(0, 14);
      if (!data.length) {{
        document.getElementById("repairBars").innerHTML = "<p class='subtle'>No raw-to-final repair deltas were available.</p>";
        return;
      }}
      const plotRows = [...data].reverse();
      const trace = {{
        type: "bar",
        orientation: "h",
        x: plotRows.map(row => row.delta),
        y: plotRows.map(row => labelFor(row)),
        marker: {{color: plotRows.map(row => row.delta >= 0 ? "#7c3aed" : "#ca8a04")}},
        customdata: plotRows.map(row => [row.raw_feasible_utility, row.feasible_utility, row.repaired_rate, wrapHoverText(row.description), wrapHoverText(labelFor(row), 44), wrapIdentifier(row.system_name)]),
        hovertemplate: "<b>%{{customdata[4]}}</b><br>%{{customdata[3]}}<br>raw utility: %{{customdata[0]:.3f}}<br>final utility: %{{customdata[1]:.3f}}<br>delta: %{{x:+.3f}}<br>repaired rate: %{{customdata[2]:.3f}}<br>raw run ID: %{{customdata[5]}}<extra></extra>"
      }};
      const layout = plotlyLayout("Validator repair effect", "final - raw feasible utility", "", 500);
      layout.margin = {{l: 138, r: 24, t: 42, b: 52}};
      layout.showlegend = false;
      layout.yaxis.tickmode = "array";
      layout.yaxis.tickvals = plotRows.map(row => labelFor(row));
      layout.yaxis.ticktext = plotRows.map(row => wrapPlotLabel(labelFor(row), 26));
      layout.yaxis.tickfont = {{size: 11}};
      layout.xaxis.zeroline = true;
      layout.xaxis.zerolinewidth = 2;
      layout.xaxis.zerolinecolor = "#64717f";
      Plotly.react("repairBars", [trace], layout, plotlyConfig);
    }}

    function comparisonLabel(value) {{
      return String(value || "")
        .replace(/_/g, " ")
        .replace(/\\b\\w/g, letter => letter.toUpperCase());
    }}

    function renderPairedBootstrap() {{
      const section = document.getElementById("pairedBootstrapSection");
      if (!pairedRows.length) {{
        section.style.display = "none";
        return;
      }}
      section.style.display = "";
      const feasible = pairedRows
        .filter(row => row.metric === "feasible_utility" && row.mean_delta !== null)
        .slice(0, 8);
      if (!feasible.length) {{
        document.getElementById("pairedBootstrapBars").innerHTML = "<p class='subtle'>No paired feasible-utility deltas available.</p>";
      }} else {{
        const plotRows = [...feasible].reverse();
        const trace = {{
          type: "bar",
          orientation: "h",
          x: plotRows.map(row => row.mean_delta),
          y: plotRows.map(row => comparisonLabel(row.comparison)),
          marker: {{color: plotRows.map(row => row.mean_delta >= 0 ? "#2563eb" : "#ca8a04")}},
          error_x: {{
            type: "data",
            array: plotRows.map(row => Math.max(0, row.ci_high - row.mean_delta)),
            arrayminus: plotRows.map(row => Math.max(0, row.mean_delta - row.ci_low)),
            visible: true,
            color: "#64717f"
          }},
          customdata: plotRows.map(row => [
            wrapHoverText(row.system_a_label, 52),
            wrapHoverText(row.system_b_label, 52),
            row.ci_low,
            row.ci_high,
            row.probability_delta_gt_zero
          ]),
          hovertemplate: "<b>%{{y}}</b><br>A: %{{customdata[0]}}<br>B: %{{customdata[1]}}<br>mean delta: %{{x:.3f}}<br>95% interval: %{{customdata[2]:.3f}} to %{{customdata[3]:.3f}}<br>P(delta > 0): %{{customdata[4]:.3f}}<extra></extra>"
        }};
        const layout = plotlyLayout("Key paired feasible-utility deltas", "system A - system B", "", 450);
        layout.margin = {{l: 172, r: 26, t: 42, b: 52}};
        layout.showlegend = false;
        layout.xaxis.zeroline = true;
        layout.xaxis.zerolinewidth = 2;
        layout.xaxis.zerolinecolor = "#64717f";
        Plotly.react("pairedBootstrapBars", [trace], layout, plotlyConfig);
      }}
      const tableRows = pairedRows
        .filter(row => ["feasible_utility", "ndcg_at_k", "compliance_rate"].includes(row.metric))
        .slice(0, 18);
      document.getElementById("pairedBootstrapRows").innerHTML = tableRows.map(row => `
        <tr>
          <td>${{escapeHtml(comparisonLabel(row.comparison))}}</td>
          <td>${{metricCodeTerm(row.metric)}}</td>
          <td>${{escapeHtml(row.system_a_label)}}</td>
          <td>${{escapeHtml(row.system_b_label)}}</td>
          <td class="num">${{fmt(row.mean_delta)}}</td>
          <td class="num">${{fmt(row.ci_low)}} to ${{fmt(row.ci_high)}}</td>
        </tr>`).join("");
    }}

    function renderCardDiagnostics() {{
      const section = document.getElementById("cardDiagnosticsSection");
      if (!cardKeyRows.length || !cardDiagnosticRows.length) {{
        section.style.display = "none";
        return;
      }}
      section.style.display = "";
      const order = ["Oracle upper-bound", "Best QSAR", "Best final LLM", "Best raw LLM", "Similarity baseline", "Rules-only baseline"];
      const boxTraces = order
        .map(series => {{
          const values = cardKeyRows
            .filter(row => row.series === series && row.feasible_utility !== null)
            .map(row => row.feasible_utility);
          if (!values.length) return null;
          return {{
            type: "box",
            name: series,
            y: values,
            boxpoints: "outliers",
            marker: {{color: series.includes("QSAR") ? colors.QSAR : series.includes("LLM") ? colors.LLM : series.includes("Oracle") ? colors.Oracle : colors.Baseline}}
          }};
        }})
        .filter(Boolean);
      if (boxTraces.length) {{
        const layout = plotlyLayout("Per-card feasible utility", "", "feasible_utility", 450);
        layout.showlegend = false;
        layout.xaxis.tickangle = -20;
        Plotly.react("cardUtilityBoxes", boxTraces, layout, plotlyConfig);
      }}
      const scatterRows = cardDiagnosticRows.filter(row => row.best_qsar_utility !== null && row.best_final_llm_utility !== null);
      if (!scatterRows.length) {{
        document.getElementById("qsarLlmScatter").innerHTML = "<p class='subtle'>No paired QSAR/LLM card diagnostics available.</p>";
        return;
      }}
      const xValues = scatterRows.map(row => row.best_qsar_utility);
      const yValues = scatterRows.map(row => row.best_final_llm_utility);
      const axisMin = Math.min(...xValues, ...yValues);
      const axisMax = Math.max(...xValues, ...yValues);
      const trace = {{
        type: "scatter",
        mode: "markers",
        name: "cards",
        x: xValues,
        y: yValues,
        customdata: scatterRows.map(row => [wrapIdentifier(row.task_id), row.best_qsar_minus_best_final_llm, row.best_final_llm_minus_similarity]),
        hovertemplate: "<b>%{{customdata[0]}}</b><br>QSAR: %{{x:.3f}}<br>best final LLM: %{{y:.3f}}<br>QSAR - LLM: %{{customdata[1]:.3f}}<br>LLM - similarity: %{{customdata[2]:.3f}}<extra></extra>",
        marker: {{size: 9, color: "#b91c1c", opacity: 0.72, line: {{color: "#ffffff", width: 1}}}}
      }};
      const diagonal = {{
        type: "scatter",
        mode: "lines",
        name: "equal utility",
        x: [axisMin, axisMax],
        y: [axisMin, axisMax],
        line: {{color: "#64717f", dash: "dash", width: 1.5}},
        hoverinfo: "skip"
      }};
      const layout = plotlyLayout("Best QSAR versus best final LLM", "Best QSAR feasible utility", "Best final LLM feasible utility", 450);
      layout.showlegend = false;
      Plotly.react("qsarLlmScatter", [diagonal, trace], layout, plotlyConfig);
    }}

    function renderFailureTaxonomy() {{
      const section = document.getElementById("failureTaxonomySection");
      const failures = failureRows
        .filter(row => row.failure_type !== "none" && Number(row.cards_with_type || 0) > 0)
        .sort((a, b) => Number(b.card_rate || 0) - Number(a.card_rate || 0))
        .slice(0, 14);
      if (!failures.length) {{
        section.style.display = "none";
        return;
      }}
      section.style.display = "";
      const plotRows = [...failures].reverse();
      const trace = {{
        type: "bar",
        orientation: "h",
        x: plotRows.map(row => row.card_rate),
        y: plotRows.map(row => `${{row.failure_type}}<br>${{wrapPlotLabel(row.display_label, 26)}}`),
        marker: {{color: plotRows.map(row => colors[row.system_group] || colors.Other)}},
        customdata: plotRows.map(row => [wrapHoverText(row.display_label, 52), row.cards_with_type, row.num_cards, row.total_issue_count, row.mean_issue_count_per_card]),
        hovertemplate: "<b>%{{customdata[0]}}</b><br>%{{y}}<br>cards with type: %{{customdata[1]}} / %{{customdata[2]}}<br>card rate: %{{x:.3f}}<br>total issues: %{{customdata[3]:.0f}}<br>issues/card: %{{customdata[4]:.3f}}<extra></extra>"
      }};
      const layout = plotlyLayout("Most frequent final-output failures", "card rate", "", 500);
      layout.margin = {{l: 220, r: 24, t: 42, b: 52}};
      layout.showlegend = false;
      layout.xaxis.range = [0, Math.min(1, Math.max(...plotRows.map(row => row.card_rate)) * 1.15)];
      Plotly.react("failureTaxonomyBars", [trace], layout, plotlyConfig);
      document.getElementById("failureTaxonomyRows").innerHTML = failures.slice(0, 12).map(row => `
        <tr>
          <td>${{escapeHtml(row.display_label)}}</td>
          <td>${{escapeHtml(row.failure_type)}}</td>
          <td class="num">${{row.cards_with_type}} / ${{row.num_cards}}</td>
          <td class="num">${{fmt(row.card_rate)}}</td>
          <td class="num">${{fmt(row.mean_issue_count_per_card)}}</td>
        </tr>`).join("");
    }}

    function renderTable() {{
      const group = document.getElementById("groupFilter").value;
      const search = document.getElementById("searchBox").value.trim().toLowerCase();
      const filtered = rows.filter(row => {{
        const groupOk = group === "all" || row.group === group;
        const text = `${{row.system_name}} ${{row.display_name}} ${{row.condition_label}} ${{row.provider}} ${{row.description}}`.toLowerCase();
        return groupOk && (!search || text.includes(search));
      }});
      document.getElementById("systemRows").innerHTML = filtered.map(row => `
        <tr>
          <td><span class="term" tabindex="0" data-tooltip="Raw run ID: ${{escapeAttr(row.system_name)}}">${{escapeHtml(labelFor(row))}}</span></td>
          <td><span class="pill ${{row.group}}">${{row.group}}</span></td>
          <td class="num">${{fmt(row.feasible_utility)}}</td>
          <td class="num">${{fmt(row.raw_feasible_utility)}}</td>
          <td class="num">${{fmt(row.ndcg_at_k)}}</td>
          <td class="num">${{fmt(row.compliance_rate)}}</td>
          <td class="num">${{fmt(row.raw_compliance_rate)}}</td>
          <td class="num">${{fmt(row.repaired_rate)}}</td>
          <td>${{row.description}}</td>
        </tr>`).join("");
    }}

    function renderMetricDefinitions() {{
      document.getElementById("metricDefinitions").innerHTML = Object.entries(metricHelp)
        .map(([metric, description]) => `<dt>${{metricCodeTerm(metric)}}</dt><dd>${{escapeHtml(description)}}</dd>`)
        .join("");
    }}

    function tooltipElement() {{
      return document.getElementById("richTooltip");
    }}

    function showRichTooltip(term) {{
      const tooltip = tooltipElement();
      const title = term.dataset.tooltipTitle || term.textContent.trim();
      const body = term.dataset.tooltip || "";
      const example = term.dataset.example || "";
      tooltip.replaceChildren();
      const titleEl = document.createElement("div");
      titleEl.className = "rich-tooltip-title";
      titleEl.textContent = title;
      tooltip.appendChild(titleEl);
      if (body) {{
        const bodyEl = document.createElement("div");
        bodyEl.className = "rich-tooltip-body";
        bodyEl.textContent = body;
        tooltip.appendChild(bodyEl);
      }}
      if (example) {{
        const exampleEl = document.createElement("pre");
        exampleEl.className = "rich-tooltip-example";
        exampleEl.textContent = example;
        tooltip.appendChild(exampleEl);
      }}
      tooltip.style.display = "block";
      tooltip.setAttribute("aria-hidden", "false");
      const rect = term.getBoundingClientRect();
      const width = tooltip.offsetWidth;
      const height = tooltip.offsetHeight;
      const margin = 12;
      let left = Math.min(Math.max(margin, rect.left), window.innerWidth - width - margin);
      let top = rect.bottom + 8;
      if (top + height + margin > window.innerHeight) {{
        top = Math.max(margin, rect.top - height - 8);
      }}
      tooltip.style.left = `${{left}}px`;
      tooltip.style.top = `${{top}}px`;
      tooltip.classList.add("visible");
    }}

    function hideRichTooltip() {{
      const tooltip = tooltipElement();
      tooltip.classList.remove("visible");
      tooltip.setAttribute("aria-hidden", "true");
      tooltip.style.display = "none";
    }}

    function closestTerm(target) {{
      return target instanceof Element ? target.closest(".term") : null;
    }}

    document.addEventListener("mouseover", event => {{
      const term = closestTerm(event.target);
      if (term) showRichTooltip(term);
    }});
    document.addEventListener("mouseout", event => {{
      const term = closestTerm(event.target);
      if (term && (!event.relatedTarget || !term.contains(event.relatedTarget))) hideRichTooltip();
    }});
    document.addEventListener("focusin", event => {{
      const term = closestTerm(event.target);
      if (term) showRichTooltip(term);
    }});
    document.addEventListener("focusout", event => {{
      const term = closestTerm(event.target);
      if (term) hideRichTooltip();
    }});
    window.addEventListener("scroll", hideRichTooltip, true);
    window.addEventListener("resize", hideRichTooltip);

    document.getElementById("xMetric").addEventListener("change", renderScatter);
    document.getElementById("xScale").addEventListener("change", renderScatter);
    document.getElementById("yMetric").addEventListener("change", renderScatter);
    document.getElementById("repairPointView").addEventListener("change", renderScatter);
    document.getElementById("groupFilter").addEventListener("change", renderTable);
    document.getElementById("searchBox").addEventListener("input", renderTable);
    renderSummary();
    renderHypotheses();
    renderScatter();
    renderLeaderboard();
    renderRepairBars();
    renderPairedBootstrap();
    renderCardDiagnostics();
    renderFailureTaxonomy();
    renderTable();
    renderMetricDefinitions();
  </script>
</body>
</html>
"""
    output.write_text(html, encoding="utf-8")
    return output


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
        "- QSAR: quantitative structure-activity relationship; here, conventional ML regressors trained separately for each decision card on support-set Morgan fingerprints and measured support activity, then used to rank feasible candidates by predicted activity. QSAR rows are deployable baselines, not oracle controls.",
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
        "- `qsar_rf`: random forest QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.",
        "- `qsar_gbt`: gradient-boosting QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.",
        "- `qsar_svm`: sparse-scaled linear-kernel support-vector QSAR regressor trained per card on support-set Morgan fingerprints and measured activity.",
        "- `bare_llm`: LLM receives the decision card and returns candidate IDs without deterministic repair.",
        "- `llm_tools`: LLM condition with extra computed descriptor/tool-summary fields in the candidate rows.",
        "- `llm_validator`: guarded LLM system; raw output is checked and invalid/missing slots may be deterministically repaired.",
        "- `llm_tools_validator`: tool-summary LLM condition plus deterministic checking and repair.",
        "- `*_frontier_selector`: legacy internal run ID for the direct-JSON condition. Reader-facing labels should use the provider, exact model name, and reasoning/thinking setting instead of this shorthand.",
        "- `*_frontier`: legacy internal run ID for the original full-pool frontier-model condition. Some rows are diagnostic interface failures, not clean model-capability measurements.",
        "- `*_fast`: legacy internal run ID for lower-latency/lower-cost provider conditions.",
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


def _best_row(frame: pd.DataFrame, metric: str, *, group: str | None = None) -> pd.Series | None:
    if frame.empty or metric not in frame.columns:
        return None
    source = frame
    if group is not None and "system_group" in source.columns:
        source = source[source["system_group"] == group]
    metric_frame = source.dropna(subset=[metric])
    if metric_frame.empty:
        return None
    return metric_frame.sort_values(metric, ascending=False).iloc[0]


def _row_label(row: pd.Series | None) -> str:
    if row is None:
        return "n/a"
    return str(row.get("display_label") or row.get("system_name") or "n/a")


def _row_value(row: pd.Series | None, metric: str) -> str:
    if row is None or metric not in row or pd.isna(row.get(metric)):
        return "n/a"
    return _format_float(row.get(metric))


def _optional_paired_bootstrap_section(table_dir: Path) -> list[str]:
    path = table_dir / "paired_bootstrap_key_deltas.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    if frame.empty:
        return []
    metrics = {"feasible_utility", "ndcg_at_k", "compliance_rate"}
    subset = frame[frame["metric"].isin(metrics)].copy()
    if subset.empty:
        return []
    subset["ci_95"] = subset.apply(
        lambda row: f"{_format_float(row['ci_low'])} to {_format_float(row['ci_high'])}",
        axis=1,
    )
    columns = [
        "comparison",
        "metric",
        "system_a_label",
        "system_b_label",
        "mean_delta",
        "ci_95",
        "probability_delta_gt_zero",
    ]
    return [
        "## Paired Bootstrap Highlights",
        "",
        "These deltas resample paired decision cards, so each comparison asks how two systems differed on the same cards rather than comparing independent aggregate means.",
        "",
        _markdown_table(subset[columns].head(18), columns),
    ]


def _optional_failure_taxonomy_section(table_dir: Path) -> list[str]:
    path = table_dir / "failure_taxonomy_summary.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    if frame.empty:
        return []
    failures = frame[(frame["failure_type"] != "none") & (frame["cards_with_type"] > 0)].copy()
    if failures.empty:
        return [
            "## Failure Taxonomy Summary",
            "",
            "No consolidated final-output contract failures were recorded in this comparison table.",
            "",
        ]
    failures = failures.sort_values(["card_rate", "total_issue_count"], ascending=[False, False])
    columns = [
        "display_label",
        "failure_type",
        "cards_with_type",
        "card_rate",
        "total_issue_count",
        "mean_issue_count_per_card",
    ]
    return [
        "## Failure Taxonomy Summary",
        "",
        "This table aggregates final-output validation failures across cards. Raw LLM repair behavior is still reported separately through raw metrics and repair rates.",
        "",
        _markdown_table(failures[columns].head(14), columns),
    ]


def write_results_summary(comparison_csv: Path, out_dir: Path, *, title: str = "SpecGuard-Chem v2 Results Summary") -> Path:
    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not frame.empty and "system_name" in frame.columns:
        frame = _add_display_columns(frame)
        frame["system_group"] = frame["system_name"].map(_system_group)
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
        oracle = frame[frame["system_name"].map(_is_oracle_system)]
        primary = frame[~frame["system_name"].map(_is_oracle_system)]
    else:
        oracle = frame
        primary = frame

    best_qsar = _best_row(primary, "feasible_utility", group="QSAR")
    best_llm = _best_row(primary, "feasible_utility", group="LLM")
    best_raw_llm = _best_row(primary, "raw_feasible_utility", group="LLM")
    best_similarity = primary[primary["system_name"] == "similarity_to_best_active"].iloc[0] if not primary.empty and (primary["system_name"] == "similarity_to_best_active").any() else None
    best_oracle = _best_row(oracle, "feasible_utility")

    columns = [
        "display_label",
        "system_name",
        "feasible_utility",
        "feasible_utility_ci_low",
        "feasible_utility_ci_high",
        "raw_feasible_utility",
        "ndcg_at_k",
        "ndcg_at_k_ci_low",
        "ndcg_at_k_ci_high",
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
        "## Central Paper Argument",
        "",
        "SpecGuard-Chem evaluates constrained medicinal-chemistry decision systems on two axes at once. Activity utility alone can reward potent compounds that violate project specifications. Compliance alone can be enforced cheaply and may produce valid but weak recommendations. The paper question is whether a system can choose candidate IDs that are both valid under the written constraints and useful as next-assay priorities.",
        "",
        "The LO paper-50 results therefore compare LLM systems against deterministic baselines and QSAR models rather than only against other LLMs. In this result set, the best deployable QSAR baseline is "
        f"**{_row_label(best_qsar)}** with feasible utility `{_row_value(best_qsar, 'feasible_utility')}`, "
        f"below the oracle upper bound `{_row_value(best_oracle, 'feasible_utility')}` but above the best final LLM row "
        f"**{_row_label(best_llm)}** at `{_row_value(best_llm, 'feasible_utility')}` and the best raw LLM row "
        f"**{_row_label(best_raw_llm)}** at raw feasible utility `{_row_value(best_raw_llm, 'raw_feasible_utility')}`.",
        "",
        "## QSAR Baseline Interpretation",
        "",
        "QSAR means quantitative structure-activity relationship modelling. Here, each QSAR row is trained separately for each decision card using only the support compounds' Morgan fingerprints and measured support activity. The trained model predicts candidate activity, then ranks feasible candidate IDs. It does not use hidden candidate activity and is therefore a deployable non-language comparator, unlike the oracle control.",
        "",
        "The fact that `qsar_rf`, `qsar_gbt`, and `qsar_svm` all beat random, rules-only, and similarity baselines in this run supports treating QSAR as a serious baseline. It does not make QSAR ground truth, a universal activity model, or a substitute for prospective medicinal-chemistry judgement.",
        "",
        "## Hypotheses And Contentions",
        "",
        "- H1, validators improve compliance more reliably than utility: supported as a reporting requirement. Final validator-assisted rows can be more compliant and sometimes more useful, but raw metrics show when the gain is harness repair rather than raw model behavior.",
        f"- H2, simple QSAR and similarity baselines are competitive: supported. Best QSAR feasible utility is `{_row_value(best_qsar, 'feasible_utility')}`; similarity-to-best-active is `{_row_value(best_similarity, 'feasible_utility')}`; best final LLM is `{_row_value(best_llm, 'feasible_utility')}`.",
        "- H3, the best useful system is likely hybrid: partially supported. Guarded/tool-summary LLM rows can improve over bare LLM rows, but this implementation is not yet the broader agent design where QSAR, RDKit, similarity retrieval, and other tools are actively available as callable tools.",
        "- H4, compliance and utility are imperfectly correlated: supported. Near-perfect compliance appears in rows with materially different feasible utility, so compliance alone is not the target outcome.",
        "",
        *_optional_paired_bootstrap_section(comparison_csv.parent),
        *_optional_failure_taxonomy_section(comparison_csv.parent),
        "## Card-Level Diagnostics",
        "",
        f"Per-card diagnostic tables are written next to the comparison CSV in `{comparison_csv.parent}`. The matching figure directory contains card-level utility distributions, utility-delta distributions, and a QSAR-versus-LLM per-card scatter plot when `make-figures` is run.",
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
