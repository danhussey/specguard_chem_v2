from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs

from .io import read_json, read_jsonl

ABLATION_PAIRS = [
    ("bare_llm", "llm_validator", "validator_delta"),
    ("llm_tools", "llm_tools_validator", "tools_validator_delta"),
    ("bare_llm", "llm_tools", "tools_delta"),
]

POSTHOC_REPAIR_SUFFIX = "__posthoc_repair"


def _save_report_plot(fig: object, output: Path) -> None:
    import matplotlib.pyplot as plt

    with plt.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        fig.savefig(
            output,
            dpi=300,
            bbox_inches="tight",
            metadata={"Software": "SpecGuard-Chem v2"},
        )
        fig.savefig(
            output.with_suffix(".pdf"),
            bbox_inches="tight",
            metadata={
                "Creator": "SpecGuard-Chem v2",
                "CreationDate": None,
                "ModDate": None,
            },
        )


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
        ("action_validity", False),
        ("raw_action_validity", False),
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
        "action_validity",
        "raw_action_validity",
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
    system_a_metric: str | None = None,
    system_b_metric: str | None = None,
) -> dict[str, object] | None:
    left_metric = system_a_metric or metric
    right_metric = system_b_metric or metric
    if left_metric not in scores.columns or right_metric not in scores.columns:
        return None
    left = (
        scores.loc[scores["system_name"] == system_a, ["task_id", left_metric]]
        .dropna()
        .rename(columns={left_metric: "metric_a"})
    )
    right = (
        scores.loc[scores["system_name"] == system_b, ["task_id", right_metric]]
        .dropna()
        .rename(columns={right_metric: "metric_b"})
    )
    merged = left.merge(right, on="task_id")
    if merged.empty:
        return None
    stats = _paired_bootstrap_delta(merged["metric_a"], merged["metric_b"], seed=seed)
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


def _is_primary_raw_llm_system(system_name: object) -> bool:
    """Return whether a row is one of the release's directly recorded LLM systems."""

    name = str(system_name)
    return _base_system_name(name) in {"bare_llm", "llm_tools"} and not name.endswith(
        POSTHOC_REPAIR_SUFFIX
    )


def _primary_raw_llm_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "system_name" not in frame.columns:
        return frame.iloc[0:0]
    return frame.loc[frame["system_name"].map(_is_primary_raw_llm_system)].copy()


def _write_paired_bootstrap_tables(
    scores: pd.DataFrame, frame: pd.DataFrame, out_dir: Path
) -> None:
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
        pd.DataFrame(columns=columns).to_csv(
            out_dir / "paired_bootstrap_key_deltas.csv", index=False
        )
        return

    enriched_frame = _add_display_columns(frame)
    primary = enriched_frame.loc[~enriched_frame["system_name"].map(_is_oracle_system)].copy()
    labels = _system_label_maps(enriched_frame)
    metrics = [
        "feasible_utility",
        "ndcg_at_k",
        "action_validity",
        "compliance_rate",
        "raw_feasible_utility",
        "raw_ndcg_at_k",
        "raw_action_validity",
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
    best_raw_llm = _best_system(
        _primary_raw_llm_rows(enriched_frame), "LLM", "raw_feasible_utility"
    )
    similarity = (
        "similarity_to_best_active" if "similarity_to_best_active" in ordered_systems else None
    )
    rules = "rules_only" if "rules_only" in ordered_systems else None
    key_specs = [
        ("oracle_minus_best_qsar", oracle, best_qsar, False),
        ("best_qsar_minus_best_final_llm", best_qsar, best_llm, False),
        ("best_qsar_minus_similarity", best_qsar, similarity, False),
        ("best_final_llm_minus_similarity", best_llm, similarity, False),
        ("best_final_llm_minus_rules", best_llm, rules, False),
        ("best_raw_llm_minus_similarity", best_raw_llm, similarity, True),
    ]
    key_rows: list[dict[str, object]] = []
    for comparison, system_a, system_b, use_raw_system_a in key_specs:
        if system_a is None or system_b is None or system_a == system_b:
            continue
        for base_metric in ["feasible_utility", "ndcg_at_k", "action_validity"]:
            metric = f"raw_{base_metric}" if use_raw_system_a else base_metric
            row = _paired_metric_row(
                scores,
                labels,
                system_a,
                system_b,
                metric,
                comparison=comparison,
                seed=13,
                system_a_metric=metric,
                system_b_metric=base_metric,
            )
            if row is not None and int(row["n_cards"]) >= 2:
                key_rows.append(row)
    pd.DataFrame(key_rows, columns=columns).to_csv(
        out_dir / "paired_bootstrap_key_deltas.csv",
        index=False,
    )


def _card_series_specs(frame: pd.DataFrame) -> list[tuple[str, str | None, str]]:
    enriched = _add_display_columns(frame)
    raw_llm_rows = _primary_raw_llm_rows(enriched)
    return [
        ("Oracle upper-bound", _best_system(enriched, "Oracle", "feasible_utility"), "final"),
        ("Best QSAR", _best_system(enriched, "QSAR", "feasible_utility"), "final"),
        ("Best final LLM", _best_system(enriched, "LLM", "feasible_utility"), "final"),
        ("Best raw LLM", _best_system(raw_llm_rows, "LLM", "raw_feasible_utility"), "raw"),
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
        "action_validity",
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
        pd.DataFrame(columns=key_columns).to_csv(
            out_dir / "card_level_key_systems.csv", index=False
        )
        pd.DataFrame(columns=diagnostic_columns).to_csv(
            out_dir / "card_level_diagnostics.csv", index=False
        )
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
                    "action_validity": _score_value(row, "action_validity", source),
                    "compliance_rate": _score_value(row, "compliance_rate", source),
                    "constrained_regret": row.get("oracle_utility") - float(feasible_utility),
                    "oracle_utility": row.get("oracle_utility"),
                }
            )
    key_frame = pd.DataFrame(key_rows, columns=key_columns)
    key_frame.to_csv(out_dir / "card_level_key_systems.csv", index=False)

    if key_frame.empty:
        pd.DataFrame(columns=diagnostic_columns).to_csv(
            out_dir / "card_level_diagnostics.csv", index=False
        )
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
        diagnostics[column] = (
            diagnostics["task_id"].map(pivot[series]) if series in pivot else np.nan
        )
    diagnostics["oracle_minus_best_qsar"] = (
        diagnostics["oracle_utility"] - diagnostics["best_qsar_utility"]
    )
    diagnostics["best_qsar_minus_best_final_llm"] = (
        diagnostics["best_qsar_utility"] - diagnostics["best_final_llm_utility"]
    )
    diagnostics["best_qsar_minus_best_raw_llm"] = (
        diagnostics["best_qsar_utility"] - diagnostics["best_raw_llm_utility"]
    )
    diagnostics["best_final_llm_minus_similarity"] = (
        diagnostics["best_final_llm_utility"] - diagnostics["similarity_utility"]
    )
    diagnostics["best_qsar_minus_similarity"] = (
        diagnostics["best_qsar_utility"] - diagnostics["similarity_utility"]
    )
    diagnostics[diagnostic_columns].to_csv(out_dir / "card_level_diagnostics.csv", index=False)


def _write_failure_taxonomy_tables(
    taxonomy: pd.DataFrame, frame: pd.DataFrame, out_dir: Path
) -> None:
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
        pd.DataFrame(columns=summary_columns).to_csv(
            out_dir / "failure_taxonomy_summary.csv", index=False
        )
        pd.DataFrame(columns=group_columns).to_csv(
            out_dir / "failure_taxonomy_by_group.csv", index=False
        )
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
                "system_group": labels.get(str(system_name), {}).get(
                    "system_group", _system_group(str(system_name))
                ),
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
    from matplotlib.lines import Line2D

    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.2, 6.1))
    validity_metric = "action_validity" if "action_validity" in frame.columns else "compliance_rate"
    if not frame.empty:
        frame = _add_display_columns(frame)
        llm_mask = (
            frame["system_group"].eq("LLM")
            if "system_group" in frame.columns
            else frame["system_name"].map(_system_group).eq("LLM")
        )
        non_llm = frame[~llm_mask]
        llm = frame[llm_mask]

        if not non_llm.empty:
            ax.scatter(
                non_llm[validity_metric],
                non_llm["feasible_utility"],
                s=58,
                color="#566573",
                alpha=0.85,
                zorder=3,
            )
            baseline_labels = {
                "oracle_valid_topk": "Oracle",
                "qsar_svm": "QSAR SVM",
                "similarity_to_best_active": "Similarity",
                "random_valid": "Random",
                "rules_only": "Rules",
            }
            for _, row in non_llm[non_llm["system_name"].isin(baseline_labels)].iterrows():
                ax.annotate(
                    baseline_labels[str(row["system_name"])],
                    (float(row[validity_metric]), float(row["feasible_utility"])),
                    xytext=(7, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=8,
                    color="#34495e",
                )

        provider_colors = {
            "openai": "#1565c0",
            "anthropic": "#c2410c",
            "deepseek": "#15803d",
        }
        interface_linestyles = {
            "bare_llm": "-",
            "llm_tools": "--",
        }
        provider_labels = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "deepseek": "DeepSeek",
        }
        interface_labels = {
            "bare_llm": "bare",
            "llm_tools": "descriptors",
        }
        condition_handles: list[Line2D] = []
        raw_llm = llm[~llm["system_name"].astype(str).str.endswith(POSTHOC_REPAIR_SUFFIX)]
        for _, raw_row in raw_llm.sort_values("system_name").iterrows():
            raw_name = str(raw_row["system_name"])
            repaired = llm[llm["system_name"].eq(f"{raw_name}{POSTHOC_REPAIR_SUFFIX}")]
            provider = str(raw_row.get("llm_provider") or raw_row.get("provider") or "").lower()
            interface = str(raw_row.get("base_system_name") or raw_name.split("__", maxsplit=1)[0])
            color = provider_colors.get(provider, "#7f8c8d")
            linestyle = interface_linestyles.get(interface, "-")
            label = (
                f"{provider_labels.get(provider, provider.title() or 'LLM')} "
                f"{interface_labels.get(interface, interface)}"
            )
            raw_x = float(raw_row[validity_metric])
            raw_y = float(raw_row["feasible_utility"])
            ax.scatter(raw_x, raw_y, s=62, marker="x", linewidth=2, color=color, zorder=5)
            if not repaired.empty:
                repaired_row = repaired.iloc[0]
                repaired_x = float(repaired_row[validity_metric])
                repaired_y = float(repaired_row["feasible_utility"])
                ax.plot(
                    [raw_x, repaired_x],
                    [raw_y, repaired_y],
                    color=color,
                    linewidth=1.4,
                    linestyle=linestyle,
                    alpha=0.7,
                    zorder=2,
                )
                ax.scatter(
                    repaired_x,
                    repaired_y,
                    s=62,
                    marker="^",
                    facecolors="white",
                    edgecolors=color,
                    linewidth=1.8,
                    zorder=5,
                )
                repair_rate = _safe_float(repaired_row.get("repaired_rate"))
                if repair_rate is not None and repair_rate > 0:
                    label_offset = 7 if interface == "bare_llm" else -9
                    ax.annotate(
                        f"{repair_rate:.1%} repaired",
                        ((raw_x + repaired_x) / 2, (raw_y + repaired_y) / 2),
                        xytext=(0, label_offset),
                        textcoords="offset points",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color=color,
                        bbox={
                            "boxstyle": "round,pad=0.16",
                            "facecolor": "white",
                            "edgecolor": "none",
                            "alpha": 0.82,
                        },
                    )
            condition_handles.append(
                Line2D([0], [0], color=color, lw=2, linestyle=linestyle, label=label)
            )

        if condition_handles:
            state_handles = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="none",
                    markerfacecolor="#566573",
                    markeredgecolor="#566573",
                    label="Non-language system",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="x",
                    color="#222222",
                    linestyle="none",
                    markeredgewidth=2,
                    label="Raw LLM output",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="^",
                    color="#222222",
                    linestyle="none",
                    markerfacecolor="white",
                    label="Post-hoc repaired output",
                ),
            ]
            ax.legend(
                handles=condition_handles + state_handles,
                loc="upper left",
                bbox_to_anchor=(1.01, 1),
                frameon=False,
                fontsize=8,
            )
        elif llm.empty:
            ax.scatter(
                frame[validity_metric],
                frame["feasible_utility"],
                s=58,
                color="#566573",
                alpha=0.85,
            )
        else:
            label_column = "display_label" if "display_label" in frame.columns else "system_name"
            ax.scatter(frame[validity_metric], frame["feasible_utility"], s=58)
            for _, row in frame.iterrows():
                ax.annotate(
                    str(row.get(label_column, row.get("system_name", ""))),
                    (float(row[validity_metric]), float(row["feasible_utility"])),
                    xytext=(5, 4),
                    textcoords="offset points",
                    fontsize=8,
                )
    ax.set_xlabel(
        "Whole-action validity rate"
        if validity_metric == "action_validity"
        else "Valid-selection fraction (legacy summaries)"
    )
    ax.set_ylabel("Feasible utility")
    ax.set_title(
        "Action Quality: Utility by Whole-Action Validity"
        if validity_metric == "action_validity"
        else "Action Quality: Utility by Valid-Selection Fraction"
    )
    ax.set_xlim(-0.03, 1.12)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output = out_dir / "compliance_utility_frontier.png"
    _save_report_plot(fig, output)
    plt.close(fig)
    _make_report_summary_plots(frame, comparison_csv.parent, out_dir)
    _make_card_level_plots(comparison_csv.parent, out_dir)
    return output


def _concise_system_label(system_name: object) -> str:
    name = str(system_name)
    base_labels = {
        "qsar_svm": "QSAR SVM",
        "qsar_rf": "QSAR RF",
        "qsar_gbt": "QSAR GBT",
        "similarity_to_best_active": "Similarity",
        "random_valid": "Random valid",
        "rules_only": "Rules only",
    }
    if name in base_labels:
        return base_labels[name]
    base = _base_system_name(name)
    provider = _title_provider(_system_provider(name)) or "LLM"
    interface = {
        "bare_llm": "bare",
        "llm_tools": "descriptors",
    }.get(base, base.replace("_", " "))
    state = "repaired" if name.endswith(POSTHOC_REPAIR_SUFFIX) else "raw"
    return f"{provider} {interface} — {state}"


def _report_plot_style(system_name: object) -> tuple[str, str, str]:
    name = str(system_name)
    group = _system_group(name)
    if group == "QSAR":
        return "#1f4e79", "o", "QSAR"
    if group == "Baseline":
        return "#66717e", "s", "Other baseline"
    if group == "LLM" and name.endswith(POSTHOC_REPAIR_SUFFIX):
        return "#007f83", "^", "Repaired LLM"
    if group == "LLM":
        return "#b75d0a", "X", "Raw LLM"
    return "#7a7a7a", "D", group


def _make_primary_utility_leaderboard(frame: pd.DataFrame, out_dir: Path) -> Path | None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    required = {"system_name", "feasible_utility"}
    if frame.empty or not required.issubset(frame.columns):
        return None
    primary = frame.loc[~frame["system_name"].map(_is_oracle_system)].copy()
    primary = primary.dropna(subset=["feasible_utility"]).sort_values("feasible_utility")
    if primary.empty:
        return None

    height = max(5.4, 0.34 * len(primary) + 1.7)
    fig, ax = plt.subplots(figsize=(9.4, height), constrained_layout=True)
    y_positions = np.arange(len(primary))
    legend_styles: dict[str, tuple[str, str]] = {}
    for y_position, (_, row) in zip(y_positions, primary.iterrows(), strict=True):
        value = float(row["feasible_utility"])
        color, marker, legend_label = _report_plot_style(row["system_name"])
        legend_styles.setdefault(legend_label, (color, marker))
        low = _safe_float(row.get("feasible_utility_ci_low"))
        high = _safe_float(row.get("feasible_utility_ci_high"))
        if low is not None and high is not None:
            ax.errorbar(
                value,
                y_position,
                xerr=[[max(0.0, value - low)], [max(0.0, high - value)]],
                color=color,
                marker=marker,
                markersize=6.5,
                markeredgewidth=1,
                capsize=2.5,
                linewidth=1.3,
                zorder=3,
            )
        else:
            ax.scatter(value, y_position, color=color, marker=marker, s=48, zorder=3)
        ax.annotate(
            f"{value:.1f}",
            (value, y_position),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#263238",
            bbox={
                "boxstyle": "round,pad=0.08",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )

    oracle = frame.loc[frame["system_name"].map(_is_oracle_system), "feasible_utility"].dropna()
    if not oracle.empty:
        oracle_value = float(oracle.max())
        ax.axvline(oracle_value, color="#6f42c1", linestyle="--", linewidth=1.2, alpha=0.85)
        ax.annotate(
            f"Oracle {oracle_value:.1f}",
            (oracle_value, len(primary) - 0.25),
            xytext=(-5, 0),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=8,
            color="#5b2c83",
        )

    values = primary["feasible_utility"].astype(float)
    ci_low = (
        primary["feasible_utility_ci_low"].astype(float)
        if "feasible_utility_ci_low" in primary.columns
        else values
    )
    ci_high = (
        primary["feasible_utility_ci_high"].astype(float)
        if "feasible_utility_ci_high" in primary.columns
        else values
    )
    x_min = float(min(values.min(), ci_low.min()))
    x_max = float(max(values.max(), ci_high.max(), oracle.max() if not oracle.empty else -np.inf))
    span = max(1.0, x_max - x_min)
    ax.set_xlim(x_min - span * 0.04, x_max + span * 0.13)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([_concise_system_label(name) for name in primary["system_name"]])
    ax.set_xlabel("Mean feasible utility (95% bootstrap CI)")
    ax.set_title(
        "Primary Utility Leaderboard",
        loc="left",
        fontweight="bold",
        pad=36,
    )
    ax.text(
        0,
        1.012,
        "All non-oracle evaluated systems; the hidden-outcome oracle is shown only as a reference.",
        transform=ax.transAxes,
        fontsize=9,
        color="#52606d",
        va="bottom",
    )
    ax.grid(axis="x", alpha=0.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [
        Line2D(
            [0],
            [0],
            color=color,
            marker=marker,
            linestyle="none",
            markersize=6.5,
            label=label,
        )
        for label, (color, marker) in legend_styles.items()
    ]
    if not oracle.empty:
        handles.append(
            Line2D([0], [0], color="#6f42c1", linestyle="--", linewidth=1.2, label="Oracle")
        )
    ax.legend(
        handles=handles,
        loc="upper left",
        ncol=2,
        frameon=False,
        fontsize=8,
    )
    output = out_dir / "primary_utility_leaderboard.png"
    _save_report_plot(fig, output)
    plt.close(fig)
    return output


def _llm_condition_sort_key(system_name: str) -> tuple[int, int]:
    provider_order = {"openai": 0, "anthropic": 1, "deepseek": 2}
    interface_order = {"bare_llm": 0, "llm_tools": 1}
    return (
        provider_order.get(_system_provider(system_name), 99),
        interface_order.get(_base_system_name(system_name), 99),
    )


def _make_llm_repair_effect(frame: pd.DataFrame, out_dir: Path) -> Path | None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    required = {"system_name", "feasible_utility"}
    if frame.empty or not required.issubset(frame.columns):
        return None
    by_system = {str(row["system_name"]): row for _, row in frame.iterrows()}
    raw_names = sorted(
        (
            name
            for name in by_system
            if _is_primary_raw_llm_system(name) and f"{name}{POSTHOC_REPAIR_SUFFIX}" in by_system
        ),
        key=_llm_condition_sort_key,
    )
    if not raw_names:
        return None

    rows: list[dict[str, object]] = []
    for raw_name in raw_names:
        raw = by_system[raw_name]
        repaired = by_system[f"{raw_name}{POSTHOC_REPAIR_SUFFIX}"]
        as_issued = _safe_float(raw.get("action_validity"))
        if as_issued is None:
            as_issued = _safe_float(raw.get("raw_action_validity")) or 0.0
        repair_triggered = _safe_float(repaired.get("repaired_rate")) or 0.0
        unresolved = max(0.0, 1.0 - as_issued - repair_triggered)
        if unresolved < 1e-9:
            unresolved = 0.0
        rows.append(
            {
                "label": _concise_system_label(raw_name).removesuffix(" — raw"),
                "raw_utility": float(raw["feasible_utility"]),
                "repaired_utility": float(repaired["feasible_utility"]),
                "as_issued": as_issued,
                "repair_triggered": repair_triggered,
                "unresolved": unresolved,
            }
        )

    plot = pd.DataFrame(rows)
    y_positions = np.arange(len(plot))
    fig, (utility_ax, validity_ax) = plt.subplots(
        1,
        2,
        figsize=(11.2, max(4.8, 0.58 * len(plot) + 1.7)),
        sharey=True,
        gridspec_kw={"width_ratios": [1.15, 1]},
        constrained_layout=True,
    )
    raw_color = "#b75d0a"
    repaired_color = "#007f83"
    for y_position, row in plot.iterrows():
        raw_value = float(row["raw_utility"])
        repaired_value = float(row["repaired_utility"])
        utility_ax.plot(
            [raw_value, repaired_value],
            [y_position, y_position],
            color="#9aa5b1",
            linewidth=1.7,
            zorder=1,
        )
        utility_ax.scatter(
            raw_value,
            y_position,
            color=raw_color,
            marker="X",
            s=62,
            zorder=3,
            label="Raw output" if y_position == 0 else None,
        )
        utility_ax.scatter(
            repaired_value,
            y_position,
            facecolor="white",
            edgecolor=repaired_color,
            marker="^",
            linewidth=1.8,
            s=72,
            zorder=3,
            label="Post-hoc repaired" if y_position == 0 else None,
        )
        utility_ax.annotate(
            f"{raw_value:.1f}",
            (raw_value, y_position),
            xytext=(-7, -12),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=raw_color,
        )
        utility_ax.annotate(
            f"{repaired_value:.1f}",
            (repaired_value, y_position),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=repaired_color,
        )

    as_issued = plot["as_issued"].astype(float).to_numpy()
    repair_triggered = plot["repair_triggered"].astype(float).to_numpy()
    unresolved = plot["unresolved"].astype(float).to_numpy()
    validity_ax.barh(y_positions, as_issued, color="#5b8ff9", height=0.56)
    validity_ax.barh(
        y_positions,
        repair_triggered,
        left=as_issued,
        color="#f6bd16",
        height=0.56,
    )
    if np.any(unresolved > 0):
        validity_ax.barh(
            y_positions,
            unresolved,
            left=as_issued + repair_triggered,
            color="#d9dde3",
            height=0.56,
        )
    for y_position, issued, repaired in zip(y_positions, as_issued, repair_triggered, strict=True):
        if issued >= 0.08:
            validity_ax.text(
                issued / 2,
                y_position,
                f"{issued:.0%}",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                fontweight="bold",
            )
        if repaired >= 0.08:
            validity_ax.text(
                issued + repaired / 2,
                y_position,
                f"{repaired:.0%}",
                ha="center",
                va="center",
                fontsize=8,
                color="#3c4043",
                fontweight="bold",
            )

    utility_ax.set_yticks(y_positions)
    utility_ax.set_yticklabels(plot["label"])
    utility_ax.invert_yaxis()
    utility_ax.set_xlabel("Mean feasible utility")
    utility_ax.set_title("Utility before and after repair", loc="left", fontweight="bold")
    utility_ax.grid(axis="x", alpha=0.22)
    utility_ax.spines[["top", "right", "left"]].set_visible(False)
    utility_ax.tick_params(axis="y", length=0)
    utility_ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.2),
        ncol=2,
        frameon=False,
        fontsize=8,
    )

    validity_ax.set_xlim(0, 1)
    validity_ax.set_xlabel("Share of actions")
    validity_ax.set_title("How final actions became valid", loc="left", fontweight="bold")
    validity_ax.grid(axis="x", alpha=0.18)
    validity_ax.spines[["top", "right", "left"]].set_visible(False)
    validity_ax.tick_params(axis="y", length=0)
    validity_handles = [
        Patch(facecolor="#5b8ff9", label="Valid as issued"),
        Patch(facecolor="#f6bd16", label="Repair triggered"),
    ]
    if np.any(unresolved > 0):
        validity_handles.append(Patch(facecolor="#d9dde3", label="Unresolved"))
    validity_ax.legend(
        handles=validity_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.2),
        ncol=len(validity_handles),
        frameon=False,
        fontsize=8,
    )

    fig.suptitle(
        "Raw and Post-Hoc-Repaired LLM Outcomes",
        x=0.01,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    output = out_dir / "llm_repair_effect.png"
    _save_report_plot(fig, output)
    plt.close(fig)
    return output


def _paired_delta_for_systems(
    frame: pd.DataFrame,
    system_a: str,
    system_b: str,
) -> tuple[float, float, float] | None:
    if frame.empty:
        return None
    subset = frame.loc[
        frame["metric"].eq("feasible_utility")
        & (
            (frame["system_a"].eq(system_a) & frame["system_b"].eq(system_b))
            | (frame["system_a"].eq(system_b) & frame["system_b"].eq(system_a))
        )
    ]
    if subset.empty:
        return None
    row = subset.iloc[0]
    mean = float(row["mean_delta"])
    low = float(row["ci_low"])
    high = float(row["ci_high"])
    if str(row["system_a"]) != system_a:
        return -mean, -high, -low
    return mean, low, high


def _make_descriptor_ablation(table_dir: Path, out_dir: Path) -> Path | None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    paired_path = table_dir / "paired_bootstrap_deltas.csv"
    if not paired_path.exists():
        return None
    paired = pd.read_csv(paired_path)
    required = {"metric", "system_a", "system_b", "mean_delta", "ci_low", "ci_high"}
    if paired.empty or not required.issubset(paired.columns):
        return None

    rows: list[dict[str, object]] = []
    providers = ["openai", "anthropic", "deepseek"]
    system_names = set(paired["system_a"].astype(str)) | set(paired["system_b"].astype(str))
    for provider in providers:
        bare_candidates = sorted(
            name
            for name in system_names
            if _base_system_name(name) == "bare_llm"
            and _system_provider(name) == provider
            and not name.endswith(POSTHOC_REPAIR_SUFFIX)
        )
        for bare_raw in bare_candidates[:1]:
            condition = _condition_name(bare_raw)
            tools_raw = f"llm_tools__{condition}"
            for state, suffix in [
                ("Raw", ""),
                ("Repaired", POSTHOC_REPAIR_SUFFIX),
            ]:
                bare = f"{bare_raw}{suffix}"
                tools = f"{tools_raw}{suffix}"
                delta = _paired_delta_for_systems(paired, tools, bare)
                if delta is None:
                    continue
                mean, low, high = delta
                rows.append(
                    {
                        "label": f"{_title_provider(provider)} — {state.lower()}",
                        "state": state,
                        "mean": mean,
                        "low": low,
                        "high": high,
                    }
                )
    if not rows:
        return None

    plot = pd.DataFrame(rows)
    y_positions = np.arange(len(plot))
    fig, ax = plt.subplots(
        figsize=(8.8, max(4.8, 0.58 * len(plot) + 1.8)),
        constrained_layout=True,
    )
    state_styles = {
        "Raw": ("#b75d0a", "X"),
        "Repaired": ("#007f83", "^"),
    }
    for y_position, row in plot.iterrows():
        color, marker = state_styles[str(row["state"])]
        mean = float(row["mean"])
        low = float(row["low"])
        high = float(row["high"])
        ax.errorbar(
            mean,
            y_position,
            xerr=[[mean - low], [high - mean]],
            color=color,
            marker=marker,
            markersize=7,
            markeredgewidth=1,
            capsize=3,
            linewidth=1.5,
            zorder=3,
        )
        ax.annotate(
            f"{mean:+.1f}",
            (mean, y_position),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=color,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.08",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )

    bounds = np.concatenate([plot["low"].astype(float), plot["high"].astype(float), [0.0]])
    span = max(1.0, float(bounds.max() - bounds.min()))
    ax.set_xlim(float(bounds.min() - span * 0.12), float(bounds.max() + span * 0.16))
    ax.axvline(0, color="#52606d", linewidth=1.1)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(plot["label"])
    ax.invert_yaxis()
    ax.set_xlabel("Descriptor-minus-bare feasible utility delta (paired 95% CI)")
    ax.set_title(
        "Descriptor Ablation",
        loc="left",
        fontweight="bold",
        pad=36,
    )
    ax.text(
        0,
        1.012,
        "Positive values favor candidate descriptor summaries; intervals crossing zero are inconclusive.",
        transform=ax.transAxes,
        fontsize=9,
        color="#52606d",
        va="bottom",
    )
    ax.grid(axis="x", alpha=0.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [
        Line2D(
            [0],
            [0],
            color=color,
            marker=marker,
            linestyle="none",
            markersize=7,
            label=state,
        )
        for state, (color, marker) in state_styles.items()
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8)
    output = out_dir / "descriptor_ablation.png"
    _save_report_plot(fig, output)
    plt.close(fig)
    return output


def _make_paired_utility_effects(table_dir: Path, out_dir: Path) -> Path | None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    key_path = table_dir / "paired_bootstrap_key_deltas.csv"
    paired_path = table_dir / "paired_bootstrap_deltas.csv"
    if not key_path.exists() or not paired_path.exists():
        return None
    key = pd.read_csv(key_path)
    paired = pd.read_csv(paired_path)
    required = {"metric", "mean_delta", "ci_low", "ci_high"}
    if (
        key.empty
        or paired.empty
        or not required.issubset(key.columns)
        or not required.issubset(paired.columns)
    ):
        return None

    headline_labels = {
        "best_qsar_minus_best_final_llm": "Best QSAR − best repaired LLM",
        "best_final_llm_minus_similarity": "Best repaired LLM − similarity",
        "best_qsar_minus_similarity": "Best QSAR − similarity",
        "oracle_minus_best_qsar": "Oracle − best QSAR",
    }
    headline = key.loc[
        key["metric"].eq("feasible_utility") & key["comparison"].isin(headline_labels),
        ["comparison", "mean_delta", "ci_low", "ci_high"],
    ].copy()
    if headline.empty:
        return None
    headline["label"] = headline["comparison"].map(headline_labels)
    order = {comparison: index for index, comparison in enumerate(headline_labels)}
    headline["order"] = headline["comparison"].map(order)
    headline = headline.sort_values("order")

    descriptor_rows: list[dict[str, object]] = []
    system_names = set(paired["system_a"].astype(str)) | set(paired["system_b"].astype(str))
    for provider in ["openai", "anthropic", "deepseek"]:
        bare_candidates = sorted(
            name
            for name in system_names
            if _base_system_name(name) == "bare_llm"
            and _system_provider(name) == provider
            and not name.endswith(POSTHOC_REPAIR_SUFFIX)
        )
        for bare_raw in bare_candidates[:1]:
            condition = _condition_name(bare_raw)
            tools_raw = f"llm_tools__{condition}"
            for state, suffix in [
                ("Raw", ""),
                ("Repaired", POSTHOC_REPAIR_SUFFIX),
            ]:
                delta = _paired_delta_for_systems(
                    paired,
                    f"{tools_raw}{suffix}",
                    f"{bare_raw}{suffix}",
                )
                if delta is None:
                    continue
                mean, low, high = delta
                descriptor_rows.append(
                    {
                        "label": f"{_title_provider(provider)} — {state.lower()}",
                        "state": state,
                        "mean_delta": mean,
                        "ci_low": low,
                        "ci_high": high,
                    }
                )
    descriptor = pd.DataFrame(descriptor_rows)
    if descriptor.empty:
        return None

    fig, (headline_ax, descriptor_ax) = plt.subplots(
        1,
        2,
        figsize=(12.6, 6.0),
        gridspec_kw={"width_ratios": [1, 1.1]},
        constrained_layout=True,
    )

    headline_positions = np.arange(len(headline))
    for y_position, (_, row) in zip(headline_positions, headline.iterrows(), strict=True):
        mean = float(row["mean_delta"])
        low = float(row["ci_low"])
        high = float(row["ci_high"])
        is_oracle = str(row["comparison"]) == "oracle_minus_best_qsar"
        color = "#6f42c1" if is_oracle else "#1f4e79"
        headline_ax.errorbar(
            mean,
            y_position,
            xerr=[[mean - low], [high - mean]],
            color=color,
            marker="D" if is_oracle else "o",
            markersize=7,
            capsize=3,
            linewidth=1.5,
            zorder=3,
        )
        headline_ax.annotate(
            f"{mean:+.2f}",
            (mean, y_position),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=color,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.08",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )
    headline_bounds = np.concatenate(
        [
            headline["ci_low"].astype(float),
            headline["ci_high"].astype(float),
            [0.0],
        ]
    )
    headline_span = max(1.0, float(headline_bounds.max() - headline_bounds.min()))
    headline_ax.set_xlim(
        float(headline_bounds.min() - headline_span * 0.12),
        float(headline_bounds.max() + headline_span * 0.2),
    )
    headline_ax.axvline(0, color="#52606d", linewidth=1.1)
    headline_ax.set_yticks(headline_positions)
    headline_ax.set_yticklabels(headline["label"])
    headline_ax.invert_yaxis()
    headline_ax.set_xlabel("First system − second system")
    headline_ax.set_title("A. Headline paired effects", loc="left", fontweight="bold")
    headline_ax.grid(axis="x", alpha=0.22)
    headline_ax.spines[["top", "right", "left"]].set_visible(False)
    headline_ax.tick_params(axis="y", length=0)

    descriptor_positions = np.arange(len(descriptor))
    state_styles = {
        "Raw": ("#b75d0a", "X"),
        "Repaired": ("#007f83", "^"),
    }
    for y_position, row in descriptor.iterrows():
        color, marker = state_styles[str(row["state"])]
        mean = float(row["mean_delta"])
        low = float(row["ci_low"])
        high = float(row["ci_high"])
        descriptor_ax.errorbar(
            mean,
            y_position,
            xerr=[[mean - low], [high - mean]],
            color=color,
            marker=marker,
            markersize=7,
            capsize=3,
            linewidth=1.5,
            zorder=3,
        )
        descriptor_ax.annotate(
            f"{mean:+.2f}",
            (mean, y_position),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=color,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.08",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )
    descriptor_bounds = np.concatenate(
        [
            descriptor["ci_low"].astype(float),
            descriptor["ci_high"].astype(float),
            [0.0],
        ]
    )
    descriptor_span = max(1.0, float(descriptor_bounds.max() - descriptor_bounds.min()))
    descriptor_ax.set_xlim(
        float(descriptor_bounds.min() - descriptor_span * 0.12),
        float(descriptor_bounds.max() + descriptor_span * 0.17),
    )
    descriptor_ax.axvline(0, color="#52606d", linewidth=1.1)
    descriptor_ax.set_yticks(descriptor_positions)
    descriptor_ax.set_yticklabels(descriptor["label"])
    descriptor_ax.invert_yaxis()
    descriptor_ax.set_xlabel("Descriptors − bare")
    descriptor_ax.set_title("B. Descriptor ablation", loc="left", fontweight="bold")
    descriptor_ax.grid(axis="x", alpha=0.22)
    descriptor_ax.spines[["top", "right", "left"]].set_visible(False)
    descriptor_ax.tick_params(axis="y", length=0)
    descriptor_ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color=color,
                marker=marker,
                linestyle="none",
                markersize=7,
                label=state,
            )
            for state, (color, marker) in state_styles.items()
        ],
        loc="lower right",
        frameon=False,
        fontsize=8,
    )

    fig.suptitle(
        "Paired Feasible-Utility Effects (95% Bootstrap CI)",
        x=0.01,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    output = out_dir / "paired_utility_effects.png"
    _save_report_plot(fig, output)
    plt.close(fig)
    return output


def _make_report_summary_plots(
    frame: pd.DataFrame,
    table_dir: Path,
    out_dir: Path,
) -> list[Path]:
    outputs = [
        _make_primary_utility_leaderboard(frame, out_dir),
        _make_llm_repair_effect(frame, out_dir),
        _make_descriptor_ablation(table_dir, out_dir),
        _make_paired_utility_effects(table_dir, out_dir),
    ]
    return [output for output in outputs if output is not None]


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
    series_labels = {
        "Oracle upper-bound": "Oracle upper bound",
        "Best QSAR": "Best observed QSAR",
        "Best final LLM": "Best repaired LLM",
        "Best raw LLM": "Best raw LLM",
        "Similarity baseline": "Similarity baseline",
        "Rules-only baseline": "Rules-only baseline",
    }
    series_colors = {
        "Oracle upper-bound": "#6f42c1",
        "Best QSAR": "#1f4e79",
        "Best final LLM": "#007f83",
        "Best raw LLM": "#b75d0a",
        "Similarity baseline": "#66717e",
        "Rules-only baseline": "#8a949e",
    }
    available_series = [series for series in series_order if series in set(key["series"])]
    if available_series:
        plot_data = [
            key.loc[key["series"] == series, "feasible_utility"].astype(float).dropna().to_numpy()
            for series in available_series
        ]
        positions = np.arange(len(available_series))
        fig, ax = plt.subplots(figsize=(9.2, 5.8), constrained_layout=True)
        boxplot = ax.boxplot(
            plot_data,
            positions=positions,
            orientation="horizontal",
            widths=0.55,
            showfliers=False,
            patch_artist=True,
            boxprops={"linewidth": 1.3},
            whiskerprops={"linewidth": 1.2},
            capprops={"linewidth": 1.2},
            medianprops={"linewidth": 1.6},
        )
        means = np.asarray([float(np.mean(values)) for values in plot_data])
        rng = np.random.default_rng(7)
        for index, (series, color) in enumerate(
            (series, series_colors[series]) for series in available_series
        ):
            boxplot["boxes"][index].set_facecolor(color)
            boxplot["boxes"][index].set_edgecolor(color)
            boxplot["boxes"][index].set_alpha(0.16)
            boxplot["medians"][index].set_color(color)
            for artist in (
                boxplot["whiskers"][2 * index : 2 * index + 2]
                + boxplot["caps"][2 * index : 2 * index + 2]
            ):
                artist.set_color(color)
            jitter = rng.uniform(-0.16, 0.16, size=len(plot_data[index]))
            ax.scatter(
                plot_data[index],
                positions[index] + jitter,
                color=color,
                marker="o",
                s=13,
                alpha=0.28,
                edgecolor="none",
                zorder=2,
            )
            ax.scatter(
                means[index],
                positions[index],
                color=color,
                marker="D",
                s=38,
                edgecolor="white",
                linewidth=0.7,
                zorder=3,
            )

        all_values = np.concatenate(plot_data)
        x_min = float(np.min(all_values))
        x_max = float(np.max(all_values))
        span = max(1.0, x_max - x_min)
        value_column_x = x_max + span * 0.055
        for y_position, mean in zip(positions, means, strict=True):
            ax.text(
                value_column_x,
                y_position,
                f"mean {mean:.1f}",
                va="center",
                fontsize=8,
                color="#263238",
            )
        ax.set_xlim(x_min - span * 0.04, x_max + span * 0.18)
        ax.set_yticks(positions)
        ax.set_yticklabels([series_labels[series] for series in available_series])
        ax.invert_yaxis()
        ax.set_xlabel("Per-card feasible utility")
        ax.set_title(
            "Across-Card Feasible-Utility Distributions",
            loc="left",
            fontweight="bold",
            pad=36,
        )
        ax.text(
            0,
            1.012,
            "Dots show all cards; boxes show IQR with 1.5×IQR whiskers; diamonds mark means.",
            transform=ax.transAxes,
            fontsize=9,
            color="#52606d",
            va="bottom",
        )
        ax.grid(axis="x", alpha=0.22)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        output = out_dir / "card_level_utility_distribution.png"
        _save_report_plot(fig, output)
        plt.close(fig)
        outputs.append(output)

    delta_labels = {
        "oracle_minus_best_qsar": "Oracle − best observed QSAR",
        "best_qsar_minus_best_final_llm": "Best QSAR − best repaired LLM",
        "best_qsar_minus_best_raw_llm": "Best QSAR − best raw LLM",
        "best_final_llm_minus_similarity": "Best repaired LLM − similarity",
        "best_qsar_minus_similarity": "Best QSAR − similarity",
    }
    delta_columns = list(delta_labels)
    available_deltas = [
        column
        for column in delta_columns
        if column in diagnostics.columns and diagnostics[column].notna().any()
    ]
    if available_deltas:
        plot_data = [
            diagnostics[column].dropna().astype(float).to_numpy() for column in available_deltas
        ]
        positions = np.arange(len(available_deltas))
        fig, ax = plt.subplots(figsize=(9.2, 5.5), constrained_layout=True)
        boxplot = ax.boxplot(
            plot_data,
            positions=positions,
            orientation="horizontal",
            widths=0.55,
            showfliers=False,
            patch_artist=True,
            boxprops={"linewidth": 1.3},
            whiskerprops={"linewidth": 1.2},
            capprops={"linewidth": 1.2},
            medianprops={"linewidth": 1.6},
        )
        means = np.asarray([float(np.mean(values)) for values in plot_data])
        colors = [
            "#6f42c1" if column == "oracle_minus_best_qsar" else "#1f4e79"
            for column in available_deltas
        ]
        rng = np.random.default_rng(11)
        for index, color in enumerate(colors):
            boxplot["boxes"][index].set_facecolor(color)
            boxplot["boxes"][index].set_edgecolor(color)
            boxplot["boxes"][index].set_alpha(0.16)
            boxplot["medians"][index].set_color(color)
            for artist in (
                boxplot["whiskers"][2 * index : 2 * index + 2]
                + boxplot["caps"][2 * index : 2 * index + 2]
            ):
                artist.set_color(color)
            jitter = rng.uniform(-0.16, 0.16, size=len(plot_data[index]))
            ax.scatter(
                plot_data[index],
                positions[index] + jitter,
                color=color,
                marker="o",
                s=13,
                alpha=0.28,
                edgecolor="none",
                zorder=2,
            )
            ax.scatter(
                means[index],
                positions[index],
                color=color,
                marker="D",
                s=38,
                edgecolor="white",
                linewidth=0.7,
                zorder=3,
            )

        all_values = np.concatenate(plot_data)
        x_min = float(np.min(all_values))
        x_max = float(np.max(all_values))
        span = max(1.0, x_max - x_min)
        value_column_x = x_max + span * 0.055
        for y_position, mean in zip(positions, means, strict=True):
            ax.text(
                value_column_x,
                y_position,
                f"mean {mean:+.2f}",
                va="center",
                fontsize=8,
                color="#263238",
            )
        ax.set_xlim(x_min - span * 0.04, x_max + span * 0.2)
        ax.axvline(0, color="#52606d", linewidth=1.1)
        ax.set_yticks(positions)
        ax.set_yticklabels([delta_labels[column] for column in available_deltas])
        ax.invert_yaxis()
        ax.set_xlabel("Per-card feasible-utility difference")
        ax.set_title(
            "Across-Card Utility-Difference Distributions",
            loc="left",
            fontweight="bold",
            pad=36,
        )
        ax.text(
            0,
            1.012,
            "Positive favors the first system; dots show all cards; diamonds mark means.",
            transform=ax.transAxes,
            fontsize=9,
            color="#52606d",
            va="bottom",
        )
        ax.grid(axis="x", alpha=0.22)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        output = out_dir / "card_level_delta_distribution.png"
        _save_report_plot(fig, output)
        plt.close(fig)
        outputs.append(output)

    if {
        "best_qsar_utility",
        "best_final_llm_utility",
    }.issubset(diagnostics.columns):
        scatter = diagnostics[["best_qsar_utility", "best_final_llm_utility"]].dropna()
        if not scatter.empty:
            qsar_values = scatter["best_qsar_utility"].astype(float)
            llm_values = scatter["best_final_llm_utility"].astype(float)
            differences = qsar_values - llm_values
            tie_mask = np.isclose(differences, 0.0, atol=1e-9)
            qsar_mask = differences > 1e-9
            llm_mask = differences < -1e-9
            winner_styles = [
                ("QSAR higher", qsar_mask, "#1f4e79", "o"),
                ("Repaired LLM higher", llm_mask, "#007f83", "^"),
                ("Tie", tie_mask, "#66717e", "s"),
            ]

            fig, ax = plt.subplots(figsize=(8.6, 6.8), constrained_layout=True)
            for label, mask, color, marker in winner_styles:
                if not bool(mask.any()):
                    continue
                ax.scatter(
                    qsar_values[mask],
                    llm_values[mask],
                    alpha=0.78,
                    color=color,
                    marker=marker,
                    s=48,
                    edgecolor="white",
                    linewidth=0.6,
                    label=f"{label} ({int(mask.sum())})",
                    zorder=3,
                )
            axis_min = float(min(qsar_values.min(), llm_values.min()))
            axis_max = float(max(qsar_values.max(), llm_values.max()))
            padding = max(1.0, (axis_max - axis_min) * 0.035)
            axis_min -= padding
            axis_max += padding
            ax.plot(
                [axis_min, axis_max],
                [axis_min, axis_max],
                color="#64717f",
                linestyle="--",
                linewidth=1.1,
                zorder=1,
            )
            ax.set_xlim(axis_min, axis_max)
            ax.set_ylim(axis_min, axis_max)
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlabel("Best observed QSAR feasible utility")
            ax.set_ylabel("Best repaired LLM feasible utility")
            ax.set_title(
                "Per-Card Utility: QSAR vs Repaired LLM",
                loc="left",
                fontweight="bold",
                pad=36,
            )
            ax.text(
                0,
                1.012,
                f"Mean paired difference (QSAR − repaired LLM): {differences.mean():+.2f}.",
                transform=ax.transAxes,
                fontsize=9,
                color="#52606d",
                va="bottom",
            )
            ax.grid(alpha=0.22)
            ax.spines[["top", "right"]].set_visible(False)
            ax.legend(
                loc="upper left",
                frameon=False,
                fontsize=8,
            )
            output = out_dir / "card_level_qsar_vs_llm_scatter.png"
            _save_report_plot(fig, output)
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
    "openai_gpt_5_5_2026_04_23_selector": {
        "provider": "openai",
        "model": "gpt-5.5-2026-04-23",
        "profile": "low reasoning, direct JSON",
        "description": "Release-candidate direct-JSON condition pinned to the GPT-5.5 snapshot dated 2026-04-23.",
    },
    "anthropic_opus_4_8_selector": {
        "provider": "anthropic",
        "model": "claude-opus-4-8",
        "profile": "no extended thinking, direct JSON",
        "description": "Release-candidate Claude Opus 4.8 direct-JSON condition without an extended-thinking budget.",
    },
    "deepseek_v4_pro_2026_07_16_selector": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "thinking off, direct JSON",
        "description": "Release-candidate direct-JSON condition using the DeepSeek V4 Pro alias as checked on 2026-07-16; traces preserve the provider-returned model identifier.",
    },
    "openai_frontier_selector": {
        "provider": "openai",
        "model": "gpt-5.5",
        "profile": "historical low-reasoning direct-JSON condition",
        "description": "Historical condition retained so earlier result artifacts remain readable; it used the unpinned GPT-5.5 alias.",
    },
    "anthropic_frontier_selector": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "profile": "historical direct-JSON condition",
        "description": "Historical condition retained so earlier result artifacts remain readable; it used Claude Opus 4.7 without extended thinking.",
    },
    "deepseek_frontier_selector": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "historical direct-JSON condition",
        "description": "Historical condition retained so earlier result artifacts remain readable; it used the DeepSeek V4 Pro alias with thinking disabled.",
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
        "description": "Historical pilot-only reasoning-budget condition retained for earlier artifacts.",
    },
    "anthropic_frontier_thinking_8k": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "profile": "8k extended thinking budget pilot, Direct JSON",
        "description": "Historical pilot-only extended-thinking condition retained for earlier artifacts.",
    },
    "deepseek_frontier_thinking_32k": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "profile": "thinking on, long output budget pilot, Direct JSON",
        "description": "Historical pilot-only thinking-budget condition retained for earlier artifacts.",
    },
}


METRIC_DESCRIPTIONS = {
    "feasible_utility": "Final action utility after any deterministic repair. It sums hidden activity for selected candidates that satisfy the action contract and hard constraints. Higher is better.",
    "raw_feasible_utility": "Action utility before deterministic repair. This is the closer measure of raw LLM behavior. Higher is better.",
    "ndcg_at_k": "Final ranking quality using hidden activity as graded relevance. 1.0 is ideal.",
    "raw_ndcg_at_k": "NDCG before validator repair.",
    "constrained_regret": "Oracle valid top-k utility minus observed feasible utility. Lower is better.",
    "action_validity": "Whole-action validity after final repair, if repair applies: 1 only when the complete output has zero validation issues, otherwise 0. Run summaries report the fraction of cards with fully valid actions.",
    "raw_action_validity": "Whole-action validity before validator repair: 1 only when the complete raw output has zero validation issues, otherwise 0.",
    "compliance_rate": "Valid-selection fraction after final repair, if repair applies: the number of valid selected entries divided by requested budget k. This can be 1.0 even when the whole action is invalid for another reason, such as a task-ID mismatch.",
    "raw_compliance_rate": "Valid-selection fraction before validator repair. This is not whole-action validity.",
    "schema_error_rate": "Fraction of cards with final output schema or contract errors.",
    "raw_schema_error_rate": "Fraction of cards with raw output schema or contract errors.",
    "repaired_rate": "Fraction of cards where the final validator changed the raw model output.",
    "repaired_from_empty_rate": "Fraction of cards where an empty raw model selection was repaired. Near zero is expected for a usable LLM interface.",
}


METRIC_EXAMPLES = {
    "feasible_utility": "For valid selected activities a_i, feasible_utility = sum(a_i). Invalid or missing slots contribute 0; when all k slots are valid, feasible_utility / k is the mean selected activity.",
    "raw_feasible_utility": "Same calculation as feasible_utility, but applied to the model's raw output before deterministic validator repair.",
    "ndcg_at_k": "Example: the best possible valid ranking has DCG=18.0 and the system ranking has DCG=14.4. NDCG@k = 14.4 / 18.0 = 0.80.",
    "raw_ndcg_at_k": "Same NDCG@k calculation, but on the raw model output before validator repair.",
    "constrained_regret": "Example: the hidden-activity oracle can reach 90.0 feasible utility and a system reaches 76.0. constrained_regret = 90.0 - 76.0 = 14.0.",
    "action_validity": "action_validity = 1 when the final output has zero validation issues; otherwise 0. The run summary is the mean over cards.",
    "raw_action_validity": "Same zero-issue whole-action check, but on the raw model output before validator repair.",
    "compliance_rate": "compliance_rate = valid selected candidate IDs satisfying all hard constraints / budget k. It measures slot-level selection compliance, not whether the complete action is valid.",
    "raw_compliance_rate": "Same valid-selection fraction, but on the raw model output before validator repair.",
    "schema_error_rate": "Example: if a card has a malformed final output, wrong k, or missing candidate IDs, schema_error_rate=1 for that card; otherwise 0. Run summaries average this over cards.",
    "raw_schema_error_rate": "Same schema/contract error calculation, but before validator repair.",
    "repaired_rate": "If repair changes r of n raw card outputs, repaired_rate = r / n.",
    "repaired_from_empty_rate": "If repair fills an empty raw selection on e of n cards, repaired_from_empty_rate = e / n.",
}


def _report_generated_at(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


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
    condition = system_name.split("__", 1)[1]
    return condition.removesuffix(POSTHOC_REPAIR_SUFFIX)


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
    if system_name.endswith(POSTHOC_REPAIR_SUFFIX):
        base_label = f"{base_label} + post-hoc repair"
    condition_label = _condition_label_from_row(row)
    if condition_label:
        return f"{base_label} - {condition_label}"
    return base_label


def _system_description_from_row(row: pd.Series | dict[str, object]) -> str:
    system_name = str(row.get("system_name", ""))
    base = _base_system_name(system_name)
    description = SYSTEM_DESCRIPTIONS.get(base, "System row from the comparison table.")
    if system_name.endswith(POSTHOC_REPAIR_SUFFIX):
        description += (
            " This row applies the deterministic post-hoc repair policy to the "
            "recorded raw response without another provider call."
        )
    condition = _condition_description(_condition_name(system_name))
    if condition:
        return f"{description} Model condition: {_condition_label_from_row(row)}. {condition} Raw run ID: {system_name}."
    return description


def _add_display_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "system_name" not in frame.columns:
        return frame
    enriched = frame.copy()
    enriched["system_group"] = [
        str(_system_group(str(row.get("system_name", "")))) for _, row in enriched.iterrows()
    ]
    enriched["display_label"] = [
        _system_display_label_from_row(row) for _, row in enriched.iterrows()
    ]
    enriched["condition_label"] = [_condition_label_from_row(row) for _, row in enriched.iterrows()]
    enriched["condition_description"] = [
        _condition_description(_condition_name(str(row.get("system_name", ""))))
        for _, row in enriched.iterrows()
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
        "action_validity",
        "raw_action_validity",
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
            "is_primary_raw_llm": _is_primary_raw_llm_system(system_name),
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
    title: str = "SpecGuard-Chem Action-Quality Results Dashboard",
    generated_at: datetime | str | None = None,
    source_path: str | Path | None = None,
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
    generated_at_text = _report_generated_at(generated_at)
    source_display_path = str(source_path if source_path is not None else comparison_csv)
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
        "One system-visible benchmark instance: assay semantics, support evidence, candidate pool, hard constraints, and budget k. Hidden candidate outcomes live in a separate scorer artifact.",
        example='{\n  "task_id": "CARA_LO_assay_0001",\n  "assay_context": {"activity_scale": "pChEMBL", "activity_direction": "higher_is_better"},\n  "budget_k": 10,\n  "support_set": [{"id": "S001", "smiles": "...", "activity_value": 6.4, "activity_type": "pChEMBL"}],\n  "candidate_pool": [{"id": "C017", "mw": 412.2, "clogp": 3.1}],\n  "hard_constraints": ["MW <= 500", "cLogP <= 4.5", "no support compounds"]\n}',
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
        "Computes utility, ranking quality, whole-action validity, valid-selection fraction, regret, repair rates, and comparison tables from the final output and raw output where available.",
        example="feasible_utility = sum(hidden activity for valid selected IDs)\naction_validity = 1 if validation issues are empty else 0\ncompliance_rate = valid_selected_count / budget_k",
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
        "action_validity": _term(
            "Action validity",
            METRIC_DESCRIPTIONS["action_validity"],
            example=METRIC_EXAMPLES["action_validity"],
            title="action_validity",
        ),
        "raw_action_validity": _term(
            "Raw action validity",
            METRIC_DESCRIPTIONS["raw_action_validity"],
            example=METRIC_EXAMPLES["raw_action_validity"],
            title="raw_action_validity",
        ),
        "compliance_rate": _term(
            "Valid-selection fraction",
            METRIC_DESCRIPTIONS["compliance_rate"],
            example=METRIC_EXAMPLES["compliance_rate"],
            title="compliance_rate",
        ),
        "raw_compliance_rate": _term(
            "Raw valid-selection fraction",
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
    .question-grid {{ display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 12px; }}
    .question {{
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fbfcfa;
      padding: 12px;
    }}
    .question-title {{ display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }}
    .question-title strong {{ font-size: 14px; }}
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
    .definition-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
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
      .summary-grid, .plot-grid, .flow, .question-grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 16px; }}
      header {{ padding: 22px 18px 14px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="subtle">Generated at <code>{escape(generated_at_text)}</code> from <code>{escape(source_display_path)}</code></div>
  </header>
  <main>
    <section class="grid summary-grid" id="summaryCards"></section>
    <section class="definition-strip" aria-label="Key metric definitions">
      {table_terms["feasible_utility"]}
      {table_terms["ndcg_at_k"]}
      {table_terms["action_validity"]}
      {table_terms["raw_feasible_utility"]}
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>{run_pipeline_term}</h2>
      <div class="flow">
        <div class="flow-step"><strong>{decision_cards_term}</strong><small>Support set, candidate pool, hard constraints, and budget k.</small></div>
        <div class="flow-step"><strong>{system_output_term}</strong><small>Baselines or LLMs return ranked candidate IDs.</small></div>
        <div class="flow-step"><strong>{raw_audit_term}</strong><small>Raw LLM selections are scored before repair where available.</small></div>
        <div class="flow-step"><strong>{validator_term}</strong><small>Deterministic schema, ID, duplicate, support-exclusion, and RDKit/property checks.</small></div>
        <div class="flow-step"><strong>{scoring_term}</strong><small>Utility, whole-action validity, valid-selection fraction, regret, and repair.</small></div>
      </div>
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>Research Questions and Observed Evidence</h2>
      <p class="subtle">Action utility is the primary scientific outcome. Validity and repair are reported separately so a well-formed but weak shortlist is not mistaken for a useful one. This panel is descriptive, not a replacement for statistical analysis.</p>
      <div id="researchQuestions" class="question-grid"></div>
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
        <h2><span class="term" tabindex="0" data-tooltip="Per-card utility distribution for key systems. The default normalizes each card by its own oracle valid top-k utility, because absolute utility ranges differ by assay/card.">Card-Level Utility Distribution</span></h2>
        <div class="controls compact-controls">
          <label><span class="term" tabindex="0" data-tooltip="Controls how per-card utility is plotted. Oracle-normalized utility is the clearest cross-card view; absolute utility is available for auditing the raw scale.">Card metric</span>
            <select id="cardUtilityMode">
              <option value="normalized">Percent of oracle utility</option>
              <option value="regret">Constrained regret</option>
              <option value="absolute">Absolute feasible utility</option>
            </select>
          </label>
        </div>
        <p class="subtle" id="cardUtilityNote"></p>
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
        <h2><span class="term" tabindex="0" data-tooltip="Action utility is the primary outcome on the y-axis; contract validity is a separately visible diagnostic on the x-axis.">Action-Quality Profile</span></h2>
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
              <option value="action_validity">Final whole-action validity</option>
              <option value="raw_action_validity">Raw whole-action validity</option>
              <option value="compliance_rate">Final valid-selection fraction</option>
              <option value="raw_compliance_rate">Raw valid-selection fraction</option>
              <option value="schema_error_rate">Final schema error</option>
              <option value="raw_schema_error_rate">Raw schema error</option>
            </select>
          </label>
          <label>{_term("X scale", "How the x-axis is transformed. Log gap to 1.0 expands rate values clustered near 1.0; log value expands small error rates.")}
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
              <th>{table_terms["action_validity"]}</th>
              <th>{table_terms["raw_action_validity"]}</th>
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
      const rawLlm = bestBy("raw_feasible_utility", row => row.is_primary_raw_llm);
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

    function renderResearchQuestions() {{
      const oracle = bestRow("feasible_utility", row => row.group === "Oracle");
      const bestPrimary = bestRow("feasible_utility", row => row.group !== "Oracle");
      const bestQsar = bestRow("feasible_utility", row => row.group === "QSAR");
      const bestLlmFinal = bestRow("feasible_utility", row => row.group === "LLM");
      const bestRawLlm = bestRow("raw_feasible_utility", row => row.is_primary_raw_llm);
      const similarity = rowByName("similarity_to_best_active");
      const representationPairs = rows
        .filter(row => row.base_system === "bare_llm" && row.condition && row.feasible_utility !== null)
        .map(bare => {{
          const tools = rows.find(row => row.base_system === "llm_tools" && row.condition === bare.condition);
          if (!tools || tools.feasible_utility === null) return null;
          return {{
            condition: bare.condition_label || bare.condition,
            bare,
            tools,
            delta: tools.feasible_utility - bare.feasible_utility
          }};
        }})
        .filter(Boolean)
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
      const largestRepresentationShift = representationPairs[0];
      const repairRows = rows
        .filter(row => row.raw_feasible_utility !== null && row.feasible_utility !== null)
        .map(row => ({{...row, delta: row.feasible_utility - row.raw_feasible_utility}}))
        .sort((a, b) => b.delta - a.delta);
      const biggestRepair = repairRows[0];
      const perfectValidityRange = metricRange("feasible_utility", row => row.group !== "Oracle" && row.action_validity !== null && row.action_validity >= 0.999);
      const questions = [
        {{
          label: "RQ1",
          status: "Observed",
          statusClass: "status-supported",
          title: "How much useful next-assay action quality is attainable?",
          evidence: `Best primary action is ${{escapeHtml(labelFor(bestPrimary))}} at ${{fmt(bestPrimary?.feasible_utility)}} ${{metricTerm("feasible_utility", "feasible utility")}}; the hidden-outcome oracle reaches ${{fmt(oracle?.feasible_utility)}}. Their separation measures remaining prioritisation headroom.`
        }},
        {{
          label: "RQ2",
          status: "Observed",
          statusClass: "status-supported",
          title: "How do LLM selectors compare with conventional prioritisation methods?",
          evidence: `Best LLM final is ${{escapeHtml(labelFor(bestLlmFinal))}} at ${{fmt(bestLlmFinal?.feasible_utility)}} ${{metricTerm("feasible_utility", "feasible utility")}}; best QSAR is ${{escapeHtml(labelFor(bestQsar))}} at ${{fmt(bestQsar?.feasible_utility)}}; similarity-to-best-active is ${{fmt(similarity?.feasible_utility)}}.`
        }},
        {{
          label: "RQ3",
          status: "Observed",
          statusClass: "status-partial",
          title: "Does the candidate representation change LLM action quality?",
          evidence: largestRepresentationShift
            ? `The largest matched bare-versus-tool-summary shift is ${{escapeHtml(largestRepresentationShift.condition)}}: ${{fmt(largestRepresentationShift.delta)}} ${{metricTerm("feasible_utility", "feasible utility")}} (tools minus bare). All matched conditions should be inspected before drawing a representation-level conclusion.`
            : "No matched bare-versus-tool-summary LLM conditions were available in this table."
        }},
        {{
          label: "RQ4",
          status: "Diagnostic",
          statusClass: "status-supported",
          title: "Can contract-valid actions still have weak scientific utility?",
          evidence: perfectValidityRange
            ? `Among non-oracle rows with final ${{metricTerm("action_validity", "whole-action validity")}} near 1.0, ${{metricTerm("feasible_utility", "feasible utility")}} ranges from ${{fmt(perfectValidityRange.min)}} to ${{fmt(perfectValidityRange.max)}}. Perfect validity alone does not imply strong prioritisation utility.`
            : "No near-perfect whole-action-validity rows were available."
        }},
        {{
          label: "Audit",
          status: "Diagnostic",
          statusClass: "status-caveat",
          title: "How much does deterministic repair change the recorded action?",
          evidence: biggestRepair
            ? `Largest observed raw-to-final ${{metricTerm("feasible_utility", "utility")}} shift is ${{escapeHtml(labelFor(biggestRepair))}}: ${{fmt(biggestRepair.delta)}}. Best raw LLM utility is ${{fmt(bestRawLlm?.raw_feasible_utility)}}. Final repaired scores describe the guarded system, not the unaided model.`
            : "Raw-to-final repair data were not available for this table."
        }}
      ];
      document.getElementById("researchQuestions").innerHTML = questions.map(item => `
        <article class="question">
          <div class="question-title">
            <strong>${{item.label}}: ${{item.title}}</strong>
            <span class="status ${{item.statusClass}}">${{item.status}}</span>
          </div>
          <p class="evidence">${{item.evidence}}</p>
        </article>`).join("");
    }}

    function effectiveXScale(metric, requested) {{
      if (requested !== "auto") return requested;
      if (metric.includes("validity") || metric.includes("compliance")) return "log_gap";
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
        action_validity: "raw_action_validity",
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
        `<span class="metric-chip">${{termHtml("scale: " + xMode, "The selected x-axis transform. log_gap plots -log10(1 - value), which spreads rate values clustered close to 1.0. log_value plots log10(value), which spreads small error rates.", "linear: value is unchanged\\nlog_gap: a rate of 0.99 becomes 2.0 because -log10(0.01)=2\\nlog_value: schema error 0.01 becomes -2.0 because log10(0.01)=-2")}}</span>`,
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
      const layout = plotlyLayout("Action quality: validity and utility", xAxisLabel(xMetric, xMode), yMetric, 500);
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
        note.textContent = "Raw-to-final repair links require a final metric with a matching raw metric. Use final utility or NDCG with whole-action validity or valid-selection fraction to inspect repair movement.";
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
        customdata: plotRows.map(row => [wrapHoverText(row.description), row.ndcg_at_k, row.action_validity, row.compliance_rate, wrapHoverText(labelFor(row), 44), wrapIdentifier(row.system_name)]),
        hovertemplate: "<b>%{{customdata[4]}}</b><br>%{{customdata[0]}}<br>utility: %{{x:.3f}}<br>NDCG@k: %{{customdata[1]:.3f}}<br>whole-action validity: %{{customdata[2]:.3f}}<br>valid-selection fraction: %{{customdata[3]:.3f}}<br>raw run ID: %{{customdata[5]}}<extra></extra>"
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
        .filter(row => ["feasible_utility", "ndcg_at_k", "action_validity"].includes(row.metric))
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
      const cardMode = document.getElementById("cardUtilityMode")?.value || "normalized";
      const cardModeMeta = {{
        normalized: {{
          title: "Per-card utility as percent of oracle",
          yTitle: "utility (% of oracle valid top-k)",
          note: "Default view. Each card is normalized to its own oracle valid top-k utility, so the boxplots compare relative performance rather than mixing assay-specific activity scales. QSAR/LLM boxes use the strongest aggregate system from the summary table, then show that same system card by card."
        }},
        regret: {{
          title: "Per-card constrained regret",
          yTitle: "oracle utility - system utility",
          note: "Lower is better. Regret measures how far each system is from the best possible valid top-k selection on the same card."
        }},
        absolute: {{
          title: "Per-card absolute feasible utility",
          yTitle: "sum of selected valid hidden activity",
          note: "Audit view. Absolute utility is the sum of selected valid hidden activity values; dividing by budget k gives the mean selected activity when every slot is valid. Different cards have different oracle ceilings, so cross-system boxplots can look misleading."
        }}
      }}[cardMode];
      const cardValue = row => {{
        if (cardMode === "regret") return row.constrained_regret;
        if (cardMode === "absolute") return row.feasible_utility;
        const oracle = Number(row.oracle_utility);
        return oracle > 0 ? Number(row.feasible_utility) / oracle * 100 : null;
      }};
      const note = document.getElementById("cardUtilityNote");
      if (note) note.textContent = cardModeMeta.note;
      const order = ["Oracle upper-bound", "Best QSAR", "Best final LLM", "Best raw LLM", "Similarity baseline", "Rules-only baseline"];
      const cardModeHover = {{
        normalized: {{label: "percent of oracle", suffix: "%"}},
        regret: {{label: "constrained regret", suffix: ""}},
        absolute: {{label: "absolute feasible utility", suffix: ""}}
      }}[cardMode];
      const seriesLabel = (series, rows) => {{
        const display = String(rows[0]?.row?.display_label || series);
        return series === "Best raw LLM" ? "Raw output: " + display : display;
      }};
      const cardSeries = order
        .map(series => {{
          const rows = cardKeyRows
            .filter(row => row.series === series)
            .map(row => ({{row, value: cardValue(row)}}))
            .filter(item => item.value !== null && item.value !== undefined && Number.isFinite(Number(item.value)));
          if (!rows.length) return null;
          const label = seriesLabel(series, rows);
          const color = series.includes("QSAR") ? colors.QSAR : series.includes("LLM") ? colors.LLM : series.includes("Oracle") ? colors.Oracle : colors.Baseline;
          return {{series, label, rows, color}};
        }})
        .filter(Boolean);
      const boxTraces = cardSeries.map(item => {{
          return {{
            type: "box",
            orientation: "h",
            name: item.label,
            x: item.rows.map(entry => entry.value),
            y: item.rows.map(() => item.label),
            boxpoints: false,
            hoverinfo: "skip",
            marker: {{color: item.color}},
            line: {{color: item.color}},
            fillcolor: item.color
          }};
        }});
      const pointTraces = cardSeries.map(item => ({{
        type: "scatter",
        mode: "markers",
        name: item.label + " cards",
        x: item.rows.map(entry => entry.value),
        y: item.rows.map(() => item.label),
        customdata: item.rows.map(entry => [
          wrapIdentifier(entry.row.task_id),
          entry.value,
          entry.row.feasible_utility,
          entry.row.oracle_utility,
          entry.row.constrained_regret,
          wrapHoverText(item.label, 52)
        ]),
        hovertemplate: "<b>%{{customdata[5]}}</b><br>%{{customdata[0]}}<br>" + cardModeHover.label + ": %{{customdata[1]:.2f}}" + cardModeHover.suffix + "<br>absolute feasible utility: %{{customdata[2]:.2f}}<br>oracle utility: %{{customdata[3]:.2f}}<br>constrained regret: %{{customdata[4]:.2f}}<extra></extra>",
        marker: {{size: 5, color: item.color, opacity: 0.34, line: {{color: "#ffffff", width: 0.5}}}},
        showlegend: false
      }}));
      if (boxTraces.length) {{
        const layout = plotlyLayout(cardModeMeta.title, cardModeMeta.yTitle, "", 520);
        layout.margin = {{l: 220, r: 24, t: 52, b: 64}};
        layout.showlegend = false;
        layout.yaxis.categoryorder = "array";
        layout.yaxis.categoryarray = cardSeries.map(item => item.label).reverse();
        layout.yaxis.tickvals = cardSeries.map(item => item.label);
        layout.yaxis.ticktext = cardSeries.map(item => wrapHoverText(item.label, 28));
        if (cardMode === "normalized") {{
          layout.xaxis.range = [Math.max(0, Math.min(...boxTraces.flatMap(trace => trace.x)) - 5), 102];
          layout.shapes = [{{
            type: "line",
            yref: "paper",
            x0: 100,
            x1: 100,
            y0: 0,
            y1: 1,
            line: {{color: "#64717f", width: 1, dash: "dash"}}
          }}];
        }}
        Plotly.react("cardUtilityBoxes", [...boxTraces, ...pointTraces], layout, plotlyConfig);
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
          <td class="num">${{fmt(row.action_validity)}}</td>
          <td class="num">${{fmt(row.raw_action_validity)}}</td>
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
    renderResearchQuestions();
    renderScatter();
    renderLeaderboard();
    renderRepairBars();
    renderPairedBootstrap();
    renderCardDiagnostics();
    renderFailureTaxonomy();
    renderTable();
    renderMetricDefinitions();
    document.getElementById("cardUtilityMode")?.addEventListener("change", renderCardDiagnostics);
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
        "- `action_validity`: whole-action validity after final repair, if repair applies; `1` only when the complete output has zero validation issues, otherwise `0`. The run summary is the fraction of fully valid actions.",
        "- `raw_action_validity`: the same zero-issue whole-action check before deterministic validator repair.",
        "- `compliance_rate`: valid-selection fraction after final repair: valid selected entries divided by requested `k`. It is not whole-action validity.",
        "- `raw_compliance_rate`: valid-selection fraction before deterministic validator repair.",
        "- `schema_error_rate`: fraction of cards with final schema/contract errors.",
        "- `raw_schema_error_rate`: schema/contract error rate before deterministic validator repair.",
        "- `repaired_from_empty_rate`: fraction of cards where the validator repaired an empty raw selection list. This should be near zero for a usable LLM interface.",
        "",
        "### Interpretation rules",
        "",
        "- Raw metrics describe model behavior; final metrics for `*_validator` rows describe model plus deterministic guardrail behavior.",
        "- Oracle controls are sanity checks, not systems that could be used prospectively.",
        "- Action utility is the primary scientific outcome. A row can have a high valid-selection fraction yet still be invalid as a whole or scientifically weak, so these diagnostics remain separate.",
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
    metrics = {"feasible_utility", "ndcg_at_k", "action_validity"}
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


def _optional_report_figure_section(source_path: Path, out_dir: Path) -> list[str]:
    parts = source_path.parts
    version = ""
    for index, part in enumerate(parts[:-1]):
        candidate = parts[index + 1]
        if part == "release" and candidate.startswith("v") and candidate.count(".") == 2:
            version = candidate
            break
    if not version:
        return []

    relative_dir = Path("figures") / version
    figure_dir = out_dir / relative_dir
    review_figures = [
        ("Decision-card anatomy and leakage boundary", "figure_1_decision_card_anatomy.png"),
        ("Corrected benchmark pipeline", "figure_2_benchmark_pipeline.png"),
        ("Main feasible-utility comparison", "figure_3_main_system_comparison.png"),
        ("System NDCG@10 comparison", "figure_4_ndcg_system_comparison.png"),
        ("Raw versus post-hoc-repaired LLM utility", "figure_5_raw_vs_final_llm.png"),
        (
            "Raw versus post-hoc-repaired whole-action validity",
            "figure_6_raw_vs_final_action_validity.png",
        ),
        ("Corrected leaderboard summary", "figure_7_leaderboard_summary.png"),
        ("Raw LLM failure taxonomy", "figure_8_failure_taxonomy.png"),
    ]
    core_figures = [
        (
            "Utility–validity repair frontier",
            "compliance_utility_frontier.png",
        ),
        (
            "Paired feasible-utility effects",
            "paired_utility_effects.png",
        ),
    ]
    review_available = all((figure_dir / filename).exists() for _, filename in review_figures)
    core_available = all((figure_dir / filename).exists() for _, filename in core_figures)
    if not review_available and not core_available:
        return []

    lines = [
        "## Report Figures",
        "",
    ]
    if review_available:
        lines.extend(
            [
                "### Corrected Figure 1–8 series",
                "",
                "This complete replacement for the retired paper-50 figure package uses the corrected 91-card benchmark, all 546 recorded raw LLM requests, and six zero-call post-hoc-repaired views.",
                "",
            ]
        )
        for number, (label, filename) in enumerate(review_figures, start=1):
            path = relative_dir / filename
            lines.extend(
                [
                    f"**Figure {number}. {label}.**",
                    "",
                    f"![Figure {number}: {label}]({path.as_posix()})",
                    "",
                ]
            )
    if core_available:
        lines.extend(
            [
                "### Additional inferential views",
                "",
                "These views are generated from the same comparison and paired card-level tables. Repaired rows are deterministic views of recorded raw responses, not additional provider calls.",
                "",
            ]
        )
        for label, filename in core_figures:
            path = relative_dir / filename
            lines.extend([f"![{label}]({path.as_posix()})", ""])
    supporting = [
        ("complete primary leaderboard", "primary_utility_leaderboard.png"),
        ("repair decomposition", "llm_repair_effect.png"),
        ("standalone descriptor ablation", "descriptor_ablation.png"),
        ("across-card utility distributions", "card_level_utility_distribution.png"),
        ("across-card utility-difference distributions", "card_level_delta_distribution.png"),
        ("per-card QSAR-versus-LLM scatter", "card_level_qsar_vs_llm_scatter.png"),
    ]
    links = [
        f"[{label}]({(relative_dir / filename).as_posix()})"
        for label, filename in supporting
        if (figure_dir / filename).exists()
    ]
    if links:
        lines.extend(
            [
                "Additional diagnostic figures: " + ", ".join(links) + ".",
                "",
            ]
        )
    return lines


def write_results_summary(
    comparison_csv: Path,
    out_dir: Path,
    *,
    title: str = "SpecGuard-Chem Action-Quality Results Summary",
    generated_at: datetime | str | None = None,
    source_path: str | Path | None = None,
) -> Path:
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
    best_raw_llm = _best_row(_primary_raw_llm_rows(primary), "raw_feasible_utility", group="LLM")
    best_primary = _best_row(primary, "feasible_utility")
    best_similarity = (
        primary[primary["system_name"] == "similarity_to_best_active"].iloc[0]
        if not primary.empty and (primary["system_name"] == "similarity_to_best_active").any()
        else None
    )
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
        "action_validity",
        "action_validity_ci_low",
        "action_validity_ci_high",
        "raw_action_validity",
        "compliance_rate",
        "raw_compliance_rate",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_from_empty_rate",
    ]
    generated_at_text = _report_generated_at(generated_at)
    source_display_path = Path(source_path) if source_path is not None else comparison_csv
    display_table_dir = source_display_path.parent
    content = [
        f"# {title}",
        "",
        f"Generated at: `{generated_at_text}`",
        "",
        f"Source comparison CSV: `{source_display_path}`",
        "",
        "This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.",
        "",
        "## Benchmark Question",
        "",
        "SpecGuard-Chem is an action-level unit test for constrained compound selection: can a system turn sparse project-local assay evidence into a useful, budget-constrained next-assay shortlist? Action utility is the primary scientific outcome. Contract validity is reported separately because a malformed action and a well-formed but scientifically weak action are different failures.",
        "",
        "The comparison includes LLM selectors, deterministic baselines, conventional per-card QSAR models, and a hidden-outcome oracle control. The best primary system is "
        f"**{_row_label(best_primary)}** with feasible utility `{_row_value(best_primary, 'feasible_utility')}`. "
        f"The oracle upper bound is `{_row_value(best_oracle, 'feasible_utility')}`; the best final LLM row is "
        f"**{_row_label(best_llm)}** at `{_row_value(best_llm, 'feasible_utility')}`, and the best raw LLM row is "
        f"**{_row_label(best_raw_llm)}** at raw feasible utility `{_row_value(best_raw_llm, 'raw_feasible_utility')}`.",
        "",
        "## QSAR Baseline Interpretation",
        "",
        "QSAR means quantitative structure-activity relationship modelling. Here, each QSAR row is trained separately for each decision card using only the support compounds' Morgan fingerprints and measured support activity. The trained model predicts candidate activity, then ranks feasible candidate IDs. It does not use hidden candidate activity and is therefore a deployable non-language comparator, unlike the oracle control.",
        "",
        "QSAR is included as a serious non-language comparator, not as ground truth, a universal activity model, or a substitute for prospective medicinal-chemistry judgement. Its observed performance should be read directly from the table and paired card-level comparisons.",
        "",
        "## Research Questions",
        "",
        f"- RQ1, how much action quality is attainable? Best primary feasible utility is `{_row_value(best_primary, 'feasible_utility')}` versus the oracle `{_row_value(best_oracle, 'feasible_utility')}`.",
        f"- RQ2, how do LLM selectors compare with conventional prioritisation methods? Best final LLM utility is `{_row_value(best_llm, 'feasible_utility')}`; best QSAR is `{_row_value(best_qsar, 'feasible_utility')}`; similarity-to-best-active is `{_row_value(best_similarity, 'feasible_utility')}`.",
        "- RQ3, does adding computed tool-summary fields change LLM action quality? Use matched bare-versus-tool-summary conditions and paired card-level deltas; do not infer a representation effect from unmatched rows.",
        "- RQ4, are action validity and action utility distinct? Report zero-issue whole-action validity alongside utility; use compliance only for the valid-selection fraction and do not treat either validity measure as the primary scientific outcome.",
        "- Audit question, how much does deterministic repair change the action? Raw metrics describe model behavior; final repaired metrics describe the guarded system.",
        "",
        *_optional_paired_bootstrap_section(comparison_csv.parent),
        *_optional_failure_taxonomy_section(comparison_csv.parent),
        *_optional_report_figure_section(source_display_path, out_dir),
        "## Card-Level Diagnostics",
        "",
        f"Per-card diagnostic tables are written next to the comparison CSV in `{display_table_dir}`. `make-figures` also writes the report-level leaderboard, repair analysis, paired-effect forest plots, card-level utility distributions, utility-delta distributions, and a QSAR-versus-LLM per-card scatter plot.",
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
        "- `action_validity` is the zero-issue whole-action rate; `compliance_rate` is only the valid-selection fraction and can remain 1.0 when another contract error invalidates the action.",
        "- Lower constrained regret and schema error rate are better.",
        "- Oracle controls are sanity checks and must not be mixed into primary system claims.",
        "",
        *_results_glossary(),
    ]
    output = out_dir / "RESULTS_SUMMARY.md"
    output.write_text("\n".join(content) + "\n", encoding="utf-8")
    return output
