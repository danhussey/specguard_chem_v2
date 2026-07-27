"""Corrected v0.1.0 figures for the eight-figure manuscript review series.

This module deliberately has no CLI or report integration.  Its public builder
accepts the canonical comparison directory and writes corrected Figures 3--8.
The input gates reject the retired 50-card comparison and require the complete
raw/repaired six-condition LLM matrix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

POSTHOC_REPAIR_SUFFIX = "__posthoc_repair"
EXPECTED_COMPARISON_ROWS = 19
EXPECTED_NUM_CARDS = 91

INK = "#1d252c"
MUTED = "#65727d"
GRID = "#d7dde2"
ORACLE = "#6f42c1"
QSAR = "#1f4e79"
BASELINE = "#66717e"
RAW = "#b75d0a"
REPAIRED = "#007f83"
PROVIDER_COLORS = {
    "openai": "#1565c0",
    "anthropic": "#c2410c",
    "deepseek": "#15803d",
}
PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
}

FIGURE_STEMS = (
    "figure_3_main_system_comparison",
    "figure_4_ndcg_system_comparison",
    "figure_5_raw_vs_final_llm",
    "figure_6_raw_vs_final_action_validity",
    "figure_7_leaderboard_summary",
    "figure_8_failure_taxonomy",
)


def _text(*values: object) -> str:
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _provider(row: pd.Series) -> str:
    return _text(row.get("llm_provider"), row.get("provider")).lower()


def _model(row: pd.Series) -> str:
    return _text(row.get("llm_model"), row.get("model"))


def _interface(row: pd.Series) -> str:
    base = _text(row.get("base_system_name"))
    if base:
        return base
    return str(row["system_name"]).split("__", maxsplit=1)[0]


def _interface_label(row: pd.Series) -> str:
    return {
        "bare_llm": "bare",
        "llm_tools": "descriptors",
    }.get(_interface(row), _interface(row).replace("_", " "))


def _is_repaired(system_name: object) -> bool:
    return str(system_name).endswith(POSTHOC_REPAIR_SUFFIX)


def _is_raw_llm_row(row: pd.Series) -> bool:
    return str(row.get("system_group")) == "LLM" and not _is_repaired(row["system_name"])


def _llm_label(row: pd.Series, *, include_state: bool, multiline: bool = False) -> str:
    provider = PROVIDER_LABELS.get(_provider(row), _provider(row).title() or "LLM")
    model = _model(row)
    interface = _interface_label(row)
    separator = "\n" if multiline else " "
    label = f"{provider} {model}{separator}{interface}"
    if include_state:
        state = "post-hoc repair" if _is_repaired(row["system_name"]) else "raw"
        label = f"{label} — {state}"
    return label


def _system_label(row: pd.Series, *, multiline: bool = False) -> str:
    system_name = str(row["system_name"])
    known = {
        "oracle_valid_topk": "Oracle upper bound",
        "qsar_svm": "QSAR linear SVR",
        "qsar_rf": "QSAR random forest",
        "qsar_gbt": "QSAR gradient boosting",
        "similarity_to_best_active": "Similarity to best active",
        "random_valid": "Random valid",
        "rules_only": "Rules only",
    }
    if system_name in known:
        return known[system_name]
    if str(row.get("system_group")) == "LLM":
        return _llm_label(row, include_state=True, multiline=multiline)
    return _text(row.get("display_label"), system_name)


def _system_color(row: pd.Series) -> str:
    group = str(row.get("system_group"))
    if group == "Oracle":
        return ORACLE
    if group == "QSAR":
        return QSAR
    if group == "Baseline":
        return BASELINE
    if group == "LLM":
        return PROVIDER_COLORS.get(_provider(row), REPAIRED)
    return BASELINE


def _required_columns(frame: pd.DataFrame, columns: Iterable[str], *, source: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def _load_corrected_inputs(comparison_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    comparison_path = comparison_dir / "system_comparison.csv"
    taxonomy_path = comparison_dir / "failure_taxonomy_summary.csv"
    if not comparison_path.exists():
        raise FileNotFoundError(comparison_path)
    if not taxonomy_path.exists():
        raise FileNotFoundError(taxonomy_path)

    comparison = pd.read_csv(comparison_path)
    _required_columns(
        comparison,
        {
            "system_name",
            "system_group",
            "num_cards",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            "action_validity",
            "repaired_rate",
        },
        source=str(comparison_path),
    )
    if len(comparison) != EXPECTED_COMPARISON_ROWS:
        raise ValueError(
            "figure review series requires the corrected 19-row comparison; "
            f"found {len(comparison)} rows"
        )
    card_counts = {
        int(value)
        for value in pd.to_numeric(comparison["num_cards"], errors="coerce").dropna().unique()
    }
    if card_counts != {EXPECTED_NUM_CARDS}:
        raise ValueError(
            "figure review series requires the corrected 91-card comparison; "
            f"found card counts {sorted(card_counts)}"
        )

    raw_llm = comparison.loc[comparison.apply(_is_raw_llm_row, axis=1)].copy()
    repaired_llm = comparison.loc[
        comparison["system_group"].eq("LLM")
        & comparison["system_name"].astype(str).str.endswith(POSTHOC_REPAIR_SUFFIX)
    ].copy()
    if len(raw_llm) != 6 or len(repaired_llm) != 6:
        raise ValueError("figure review series requires six raw and six post-hoc-repaired LLM rows")
    comparison_names = set(comparison["system_name"].astype(str))
    missing_pairs = [
        str(name)
        for name in raw_llm["system_name"]
        if f"{name}{POSTHOC_REPAIR_SUFFIX}" not in comparison_names
    ]
    if missing_pairs:
        raise ValueError(f"missing repaired partners for raw systems: {missing_pairs}")
    providers = {_provider(row) for _, row in raw_llm.iterrows()}
    if providers != set(PROVIDER_COLORS):
        raise ValueError(
            "figure review series requires OpenAI, Anthropic, and DeepSeek rows; "
            f"found {sorted(providers)}"
        )

    taxonomy = pd.read_csv(taxonomy_path)
    _required_columns(
        taxonomy,
        {
            "system_name",
            "system_group",
            "failure_type",
            "num_cards",
            "cards_with_type",
            "card_rate",
        },
        source=str(taxonomy_path),
    )
    taxonomy_cards = {
        int(value)
        for value in pd.to_numeric(taxonomy["num_cards"], errors="coerce").dropna().unique()
    }
    if not taxonomy_cards or not taxonomy_cards.issubset({EXPECTED_NUM_CARDS}):
        raise ValueError(
            "failure taxonomy must come from the corrected 91-card analysis; "
            f"found card counts {sorted(taxonomy_cards)}"
        )
    return comparison, taxonomy


def _save_all(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{stem}.{suffix}" for suffix in ("png", "pdf", "svg")]
    with plt.rc_context(
        {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "specguard-chem-v2",
        }
    ):
        fig.savefig(
            outputs[0],
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.12,
            metadata={"Software": "SpecGuard-Chem v2"},
        )
        fig.savefig(
            outputs[1],
            bbox_inches="tight",
            pad_inches=0.12,
            metadata={
                "Creator": "SpecGuard-Chem v2",
                "CreationDate": None,
                "ModDate": None,
            },
        )
        fig.savefig(
            outputs[2],
            bbox_inches="tight",
            pad_inches=0.12,
            metadata={"Creator": "SpecGuard-Chem v2", "Date": None},
        )
    plt.close(fig)
    return outputs


def _main_comparison_rows(frame: pd.DataFrame) -> pd.DataFrame:
    keep = ~frame["system_group"].eq("LLM") | frame["system_name"].map(_is_repaired)
    return frame.loc[keep].copy()


def _comparison_legend(rows: pd.DataFrame) -> list[Line2D]:
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            color=ORACLE,
            markersize=6,
            label="Oracle control",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            color=QSAR,
            markersize=6,
            label="QSAR",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="none",
            color=BASELINE,
            markersize=6,
            label="Simple baseline",
        ),
    ]
    for provider in sorted({_provider(row) for _, row in rows.iterrows() if _provider(row)}):
        handles.append(
            Line2D(
                [0],
                [0],
                marker="^",
                linestyle="none",
                color=PROVIDER_COLORS.get(provider, REPAIRED),
                markersize=6,
                label=f"{PROVIDER_LABELS.get(provider, provider.title())} + repair",
            )
        )
    return handles


def _make_interval_comparison(
    rows: pd.DataFrame,
    output_dir: Path,
    *,
    stem: str,
    metric: str,
    low_column: str,
    high_column: str,
    title: str,
    xlabel: str,
    digits: int,
) -> list[Path]:
    data = rows.dropna(subset=[metric, low_column, high_column]).sort_values(metric)
    if data.empty:
        raise ValueError(f"no rows available for {stem}")

    fig_height = max(5.8, 0.42 * len(data) + 1.6)
    fig, ax = plt.subplots(figsize=(10.2, fig_height), constrained_layout=True)
    y_positions = np.arange(len(data))
    for y_position, (_, row) in zip(y_positions, data.iterrows(), strict=True):
        value = float(row[metric])
        low = float(row[low_column])
        high = float(row[high_column])
        color = _system_color(row)
        marker = (
            "D"
            if str(row["system_group"]) == "Oracle"
            else "^"
            if str(row["system_group"]) == "LLM"
            else "o"
            if str(row["system_group"]) == "QSAR"
            else "s"
        )
        ax.errorbar(
            value,
            y_position,
            xerr=[[max(0.0, value - low)], [max(0.0, high - value)]],
            color=color,
            marker=marker,
            markersize=6.5,
            markeredgewidth=0.9,
            capsize=2.8,
            linewidth=1.4,
            zorder=3,
        )
        ax.annotate(
            f"{value:.{digits}f}",
            (value, y_position),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK,
            bbox={
                "boxstyle": "round,pad=0.08",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.94,
            },
        )

    low_bound = float(data[low_column].min())
    high_bound = float(data[high_column].max())
    span = max(high_bound - low_bound, 0.1)
    ax.set_xlim(low_bound - 0.08 * span, high_bound + 0.14 * span)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([_system_label(row) for _, row in data.iterrows()])
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        handles=_comparison_legend(data),
        loc="lower right",
        frameon=False,
        fontsize=8,
        ncol=2,
    )
    ax.text(
        0,
        -0.09,
        "Intervals are marginal task-bootstrap intervals; paired claims use paired deltas.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=8,
    )
    return _save_all(fig, output_dir, stem)


def _make_figure_3(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    return _make_interval_comparison(
        _main_comparison_rows(frame),
        output_dir,
        stem="figure_3_main_system_comparison",
        metric="feasible_utility",
        low_column="feasible_utility_ci_low",
        high_column="feasible_utility_ci_high",
        title="Main system comparison",
        xlabel=f"Mean feasible utility across {EXPECTED_NUM_CARDS} cards (95% bootstrap CI)",
        digits=1,
    )


def _make_figure_4(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    return _make_interval_comparison(
        _main_comparison_rows(frame),
        output_dir,
        stem="figure_4_ndcg_system_comparison",
        metric="ndcg_at_k",
        low_column="ndcg_at_k_ci_low",
        high_column="ndcg_at_k_ci_high",
        title="Ranking quality by system",
        xlabel=f"NDCG@10 across {EXPECTED_NUM_CARDS} cards (95% bootstrap CI)",
        digits=3,
    )


def _llm_pairs(frame: pd.DataFrame) -> list[tuple[pd.Series, pd.Series]]:
    lookup = frame.set_index("system_name", drop=False)
    raw_rows = frame.loc[frame.apply(_is_raw_llm_row, axis=1)].copy()
    pairs: list[tuple[pd.Series, pd.Series]] = []
    for _, raw_row in raw_rows.iterrows():
        repaired_name = f"{raw_row['system_name']}{POSTHOC_REPAIR_SUFFIX}"
        repaired_row = lookup.loc[repaired_name]
        if isinstance(repaired_row, pd.DataFrame):
            raise ValueError(f"duplicate repaired row: {repaired_name}")
        pairs.append((raw_row, repaired_row))
    return pairs


def _state_legend() -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            marker="X",
            linestyle="none",
            color=RAW,
            markersize=7,
            label="Raw output",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            linestyle="none",
            markerfacecolor="white",
            markeredgecolor=REPAIRED,
            markeredgewidth=1.5,
            color=REPAIRED,
            markersize=7,
            label="Post-hoc repaired",
        ),
    ]


def _make_figure_5(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    pairs = sorted(
        _llm_pairs(frame),
        key=lambda pair: float(pair[1]["feasible_utility"]),
        reverse=True,
    )
    value_max = max(float(row["feasible_utility"]) for pair in pairs for row in pair)
    fig, ax = plt.subplots(figsize=(10.4, 5.8), constrained_layout=True)
    y_positions = np.arange(len(pairs))
    values: list[float] = []
    for y_position, (raw_row, repaired_row) in zip(y_positions, pairs, strict=True):
        raw_value = float(raw_row["feasible_utility"])
        repaired_value = float(repaired_row["feasible_utility"])
        values.extend([raw_value, repaired_value])
        provider_color = PROVIDER_COLORS.get(_provider(raw_row), BASELINE)
        ax.plot(
            [raw_value, repaired_value],
            [y_position, y_position],
            color=provider_color,
            linewidth=2.2,
            alpha=0.55,
            zorder=1,
        )
        ax.scatter(
            raw_value,
            y_position,
            marker="X",
            s=72,
            color=RAW,
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        ax.scatter(
            repaired_value,
            y_position,
            marker="^",
            s=78,
            facecolor="white",
            edgecolor=REPAIRED,
            linewidth=1.8,
            zorder=4,
        )
        ax.annotate(
            f"{raw_value:.1f}",
            (raw_value, y_position),
            xytext=(0, -11),
            textcoords="offset points",
            ha="center",
            va="top",
            color=RAW,
            fontsize=8,
        )
        ax.annotate(
            f"{repaired_value:.1f}",
            (repaired_value, y_position),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=REPAIRED,
            fontsize=8,
        )
        repaired_rate = float(repaired_row["repaired_rate"])
        repaired_count = int(round(repaired_rate * EXPECTED_NUM_CARDS))
        ax.annotate(
            f"{repaired_count}/{EXPECTED_NUM_CARDS} actions repaired",
            (value_max, y_position),
            xytext=(13, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8,
            color=MUTED,
        )

    value_min = min(values)
    span = max(1.0, value_max - value_min)
    ax.set_xlim(value_min - 0.05 * span, value_max + 0.23 * span)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([_llm_label(raw_row, include_state=False) for raw_row, _ in pairs])
    ax.set_ylim(len(pairs) - 0.25, -0.75)
    ax.set_xlabel("Mean feasible utility")
    ax.set_title(
        "Raw versus post-hoc-repaired LLM utility",
        loc="left",
        fontweight="bold",
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        handles=_state_legend(),
        loc="lower right",
        bbox_to_anchor=(1.0, 1.01),
        frameon=False,
        ncol=2,
    )
    ax.text(
        0,
        -0.10,
        "Each line joins the same provider response before and after zero-call deterministic repair.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=8,
    )
    return _save_all(fig, output_dir, "figure_5_raw_vs_final_llm")


def _make_figure_6(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    pairs = sorted(
        _llm_pairs(frame),
        key=lambda pair: float(pair[0]["action_validity"]),
        reverse=True,
    )
    fig, ax = plt.subplots(figsize=(10.4, 5.8), constrained_layout=True)
    y_positions = np.arange(len(pairs))
    for y_position, (raw_row, repaired_row) in zip(y_positions, pairs, strict=True):
        raw_value = float(raw_row["action_validity"])
        repaired_value = float(repaired_row["action_validity"])
        provider_color = PROVIDER_COLORS.get(_provider(raw_row), BASELINE)
        ax.plot(
            [raw_value, repaired_value],
            [y_position, y_position],
            color=provider_color,
            linewidth=2.2,
            alpha=0.55,
            zorder=1,
        )
        ax.scatter(
            raw_value,
            y_position,
            marker="X",
            s=72,
            color=RAW,
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        ax.scatter(
            repaired_value,
            y_position,
            marker="^",
            s=78,
            facecolor="white",
            edgecolor=REPAIRED,
            linewidth=1.8,
            zorder=4,
        )
        ax.annotate(
            f"{raw_value:.3f}",
            (raw_value, y_position),
            xytext=(0, -11),
            textcoords="offset points",
            ha="center",
            va="top",
            color=RAW,
            fontsize=8,
        )
        ax.annotate(
            f"{repaired_value:.3f}",
            (repaired_value, y_position),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=REPAIRED,
            fontsize=8,
        )
        repaired_rate = float(repaired_row["repaired_rate"])
        repaired_count = int(round(repaired_rate * EXPECTED_NUM_CARDS))
        ax.annotate(
            f"{repaired_count}/{EXPECTED_NUM_CARDS} repairs",
            (repaired_value, y_position),
            xytext=(52, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            color=MUTED,
            fontsize=8,
        )

    ax.set_xlim(0, 1.18)
    ax.set_xticks([0, 0.25, 0.50, 0.75, 1.00])
    ax.set_yticks(y_positions)
    ax.set_yticklabels([_llm_label(raw_row, include_state=False) for raw_row, _ in pairs])
    ax.set_ylim(len(pairs) - 0.25, -0.75)
    ax.set_xlabel("Whole-action validity rate")
    ax.set_title(
        "Whole-action validity before and after repair",
        loc="left",
        fontweight="bold",
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        handles=_state_legend(),
        loc="lower right",
        bbox_to_anchor=(1.0, 1.01),
        frameon=False,
        ncol=2,
    )
    ax.text(
        0,
        -0.10,
        "Validity equals one only when the complete action has zero contract issues.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=8,
    )
    return _save_all(fig, output_dir, "figure_6_raw_vs_final_action_validity")


def _lollipop_panel(
    ax: plt.Axes,
    rows: pd.DataFrame,
    *,
    metric: str,
    title: str,
    digits: int,
    labels: list[str],
) -> None:
    data = rows.copy().sort_values(metric)
    values = data[metric].astype(float).to_numpy()
    low = float(values.min())
    high = float(values.max())
    span = max(high - low, 0.05)
    axis_low = max(0.0, low - 0.18 * span)
    y_positions = np.arange(len(data))
    for y_position, (_, row) in zip(y_positions, data.iterrows(), strict=True):
        value = float(row[metric])
        color = _system_color(row)
        ax.hlines(y_position, axis_low, value, color=color, linewidth=2, alpha=0.55)
        ax.scatter(value, y_position, color=color, s=44, zorder=3)
        ax.annotate(
            f"{value:.{digits}f}",
            (value, y_position),
            xytext=(5, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.5,
            color=INK,
        )
    ax.set_xlim(axis_low, high + 0.25 * span)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_title(title, fontweight="bold", fontsize=10)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.tick_params(axis="y", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)


def _make_figure_7(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    utility = frame.nlargest(6, "feasible_utility").copy()
    ndcg = frame.nlargest(6, "ndcg_at_k").copy()
    raw_llm = frame.loc[frame.apply(_is_raw_llm_row, axis=1)].copy()

    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.8), constrained_layout=True)
    _lollipop_panel(
        axes[0],
        utility,
        metric="feasible_utility",
        title="A. Leading feasible utility",
        digits=1,
        labels=[
            _system_label(row, multiline=True)
            for _, row in utility.sort_values("feasible_utility").iterrows()
        ],
    )
    _lollipop_panel(
        axes[1],
        ndcg,
        metric="ndcg_at_k",
        title="B. Leading NDCG@10",
        digits=3,
        labels=[
            _system_label(row, multiline=True)
            for _, row in ndcg.sort_values("ndcg_at_k").iterrows()
        ],
    )
    _lollipop_panel(
        axes[2],
        raw_llm,
        metric="action_validity",
        title="C. Raw LLM action validity",
        digits=3,
        labels=[
            _llm_label(row, include_state=False, multiline=True)
            for _, row in raw_llm.sort_values("action_validity").iterrows()
        ],
    )
    axes[0].set_xlabel("Mean feasible utility")
    axes[1].set_xlabel("Mean NDCG@10")
    axes[2].set_xlabel("Whole-action validity rate")
    fig.suptitle("Corrected v0.1.0 leaderboard snapshot", fontweight="bold", fontsize=15)
    fig.text(
        0.5,
        -0.015,
        "Panels A and B include the hidden-outcome oracle; Panel C uses raw LLM outputs.",
        ha="center",
        va="top",
        fontsize=8,
        color=MUTED,
    )
    return _save_all(fig, output_dir, "figure_7_leaderboard_summary")


def _taxonomy_color(failure_type: str, rate: float) -> tuple[float, float, float, float]:
    base = "#2f7251" if failure_type == "none" else "#c2410c"
    alpha = 0.10 + 0.82 * min(max(rate, 0.0), 1.0)
    rgba = to_rgba(base)
    return (
        1 - (1 - rgba[0]) * alpha,
        1 - (1 - rgba[1]) * alpha,
        1 - (1 - rgba[2]) * alpha,
        1.0,
    )


def _make_figure_8(
    frame: pd.DataFrame,
    taxonomy: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    raw_rows = frame.loc[frame.apply(_is_raw_llm_row, axis=1)].copy()
    raw_rows = raw_rows.sort_values(["llm_provider", "base_system_name"])
    raw_names = set(raw_rows["system_name"].astype(str))
    raw_taxonomy = taxonomy.loc[taxonomy["system_name"].astype(str).isin(raw_names)].copy()

    failure_types = (
        ("none", "No detected\nissue"),
        ("schema_failure", "JSON/schema\nfailure"),
        ("selection_contract_failure", "Selection-contract\nfailure"),
        ("constraint_failure", "Candidate-constraint\nfailure"),
    )
    lookup = {
        (str(row["system_name"]), str(row["failure_type"])): (
            int(row["cards_with_type"]),
            float(row["card_rate"]),
        )
        for _, row in raw_taxonomy.iterrows()
    }
    fig, ax = plt.subplots(figsize=(10.4, 5.4), constrained_layout=True)
    for row_index, (_, system_row) in enumerate(raw_rows.iterrows()):
        system_name = str(system_row["system_name"])
        for column_index, (failure_type, _) in enumerate(failure_types):
            count, rate = lookup.get((system_name, failure_type), (0, 0.0))
            ax.add_patch(
                Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1,
                    1,
                    facecolor=_taxonomy_color(failure_type, rate),
                    edgecolor="white",
                    linewidth=2,
                )
            )
            ax.text(
                column_index,
                row_index,
                f"{count}\n({rate:.1%})",
                ha="center",
                va="center",
                fontsize=8.5,
                fontweight="bold",
                color=INK,
            )

    ax.set_xlim(-0.5, len(failure_types) - 0.5)
    ax.set_ylim(-0.5, len(raw_rows) - 0.5)
    ax.set_xticks(range(len(failure_types)))
    ax.set_xticklabels([label for _, label in failure_types])
    ax.set_yticks(range(len(raw_rows)))
    ax.set_yticklabels([_llm_label(row, include_state=False) for _, row in raw_rows.iterrows()])
    ax.invert_yaxis()
    ax.tick_params(axis="both", length=0)
    ax.spines[:].set_visible(False)
    ax.set_title(
        f"Raw LLM failure taxonomy ({EXPECTED_NUM_CARDS} cards per condition)",
        loc="left",
        fontweight="bold",
    )
    ax.text(
        0,
        -0.09,
        "Green denotes zero-issue actions. Failure categories can overlap, so row counts "
        "must not be summed.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=8,
    )
    return _save_all(fig, output_dir, "figure_8_failure_taxonomy")


def build_figure_review_series(
    comparison_dir: Path | str,
    output_dir: Path | str,
) -> list[Path]:
    """Build corrected review Figures 3--8 from canonical v0.1.0 tables.

    The returned paths contain PNG, PDF, and SVG output for each of the six
    figure stems, ordered by figure number and then by format.
    """

    comparison_path = Path(comparison_dir)
    output_path = Path(output_dir)
    frame, taxonomy = _load_corrected_inputs(comparison_path)
    outputs: list[Path] = []
    outputs.extend(_make_figure_3(frame, output_path))
    outputs.extend(_make_figure_4(frame, output_path))
    outputs.extend(_make_figure_5(frame, output_path))
    outputs.extend(_make_figure_6(frame, output_path))
    outputs.extend(_make_figure_7(frame, output_path))
    outputs.extend(_make_figure_8(frame, taxonomy, output_path))
    return outputs


__all__ = ["FIGURE_STEMS", "build_figure_review_series"]
