from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "paper/figures/cara_lo_paper_50_direct_json_completed"
TABLE_DIR = ROOT / "paper/tables/cara_lo_paper_50_direct_json_completed"
OUT_HTML = ROOT / "paper/FIGURE_REVIEW.html"

SUMMARY_PATH = ROOT / "data/cards/cara_lo_paper_50.summary.json"
SYSTEM_COMPARISON_PATH = TABLE_DIR / "system_comparison.csv"
PAIRED_DELTAS_PATH = TABLE_DIR / "paired_bootstrap_key_deltas.csv"
FAILURE_TAXONOMY_PATH = TABLE_DIR / "failure_taxonomy_summary.csv"

INK = "#1d252c"
MUTED = "#65727d"
GRID = "#d7dde2"
ORACLE = "#9a3f45"
QSAR = "#2f7251"
OPENAI = "#69538f"
ANTHROPIC = "#2d5f86"
DEEPSEEK = "#b56a1e"
BASELINE = "#6d7378"
RAW = "#9aa2aa"
FINAL = "#533f80"


def _system_legend() -> list[Line2D]:
    return [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORACLE, markeredgecolor="white", markersize=7, label="Oracle"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=QSAR, markeredgecolor="white", markersize=7, label="QSAR"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=OPENAI, markeredgecolor="white", markersize=7, label="OpenAI LLM"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ANTHROPIC, markeredgecolor="white", markersize=7, label="Anthropic LLM"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=DEEPSEEK, markeredgecolor="white", markersize=7, label="DeepSeek LLM"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BASELINE, markeredgecolor="white", markersize=7, label="Simple baseline"),
    ]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        return float("nan")
    return float(value)


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _find(rows: Iterable[dict[str, str]], system_name: str) -> dict[str, str]:
    for row in rows:
        if row["system_name"] == system_name:
            return row
    raise KeyError(system_name)


def _save_all(fig: plt.Figure, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(FIG_DIR / f"{stem}.{suffix}", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def make_main_utility_plot(rows: list[dict[str, str]]) -> None:
    selected = [
        ("Oracle upper bound", "oracle_valid_topk", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", ORACLE),
        ("QSAR linear SVR", "qsar_svm", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", QSAR),
        ("QSAR gradient boosting", "qsar_gbt", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", QSAR),
        ("QSAR random forest", "qsar_rf", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", QSAR),
        (
            "GPT-5.5",
            "llm_validator__openai_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            OPENAI,
        ),
        (
            "GPT-5.5 + descriptors",
            "llm_tools_validator__openai_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            OPENAI,
        ),
        (
            "Opus 4.7",
            "llm_validator__anthropic_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            ANTHROPIC,
        ),
        (
            "Opus 4.7 + descriptors",
            "llm_tools_validator__anthropic_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            ANTHROPIC,
        ),
        (
            "DeepSeek V4 Pro",
            "llm_validator__deepseek_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            DEEPSEEK,
        ),
        (
            "DeepSeek V4 Pro + descriptors",
            "llm_tools_validator__deepseek_frontier_selector",
            "feasible_utility",
            "feasible_utility_ci_low",
            "feasible_utility_ci_high",
            DEEPSEEK,
        ),
        ("Similarity baseline", "similarity_to_best_active", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", BASELINE),
        ("Random valid baseline", "random_valid", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", BASELINE),
        ("Rules baseline", "rules_only", "feasible_utility", "feasible_utility_ci_low", "feasible_utility_ci_high", BASELINE),
    ]
    data = []
    for label, system_name, value_key, lo_key, hi_key, color in selected:
        row = _find(rows, system_name)
        value = _float(row, value_key)
        data.append(
            {
                "label": label,
                "value": value,
                "lo": _float(row, lo_key),
                "hi": _float(row, hi_key),
                "color": color,
            }
        )
    data.sort(key=lambda item: item["value"])

    fig, ax = plt.subplots(figsize=(9.6, 7.4), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_positions = range(len(data))
    for y, item in zip(y_positions, data, strict=True):
        lo_err = item["value"] - item["lo"]
        hi_err = item["hi"] - item["value"]
        ax.errorbar(
            item["value"],
            y,
            xerr=[[lo_err], [hi_err]],
            fmt="o",
            color=item["color"],
            ecolor=item["color"],
            elinewidth=1.7,
            capsize=3.0,
            markersize=7.0,
            markeredgecolor="white",
            markeredgewidth=0.9,
            zorder=3,
        )
        label_x = item["hi"] + 0.35
        ax.text(
            label_x,
            y,
            _fmt(item["value"]),
            va="center",
            ha="left",
            fontsize=11.3,
            color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.86},
        )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([item["label"] for item in data], fontsize=12.2)
    ax.set_xlabel("Mean feasible utility across 50 decision cards (higher is better)", fontsize=12.0, color=INK)
    ax.set_xlim(63, 92)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="x", labelsize=11.0, colors=INK)
    ax.tick_params(axis="y", length=0, colors=INK)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_title("Main system comparison", fontsize=18.0, fontweight="bold", color=INK, pad=15)
    ax.legend(
        handles=_system_legend(),
        loc="lower right",
        frameon=False,
        fontsize=10.0,
        ncol=2,
        handletextpad=0.3,
        columnspacing=0.8,
    )
    ax.text(
        63,
        len(data) - 0.35,
        "Dots show mean feasible utility; bars show 95% bootstrap intervals over cards. LLM rows show final output after validation/repair.",
        fontsize=10.6,
        color=MUTED,
        ha="left",
        va="top",
    )
    _save_all(fig, "figure_3_main_system_comparison")


def make_ndcg_plot(rows: list[dict[str, str]]) -> None:
    selected = [
        ("Oracle upper bound", "oracle_valid_topk", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", ORACLE),
        ("QSAR linear SVR", "qsar_svm", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", QSAR),
        ("QSAR gradient boosting", "qsar_gbt", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", QSAR),
        ("QSAR random forest", "qsar_rf", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", QSAR),
        (
            "GPT-5.5",
            "llm_validator__openai_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            OPENAI,
        ),
        (
            "GPT-5.5 + descriptors",
            "llm_tools_validator__openai_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            OPENAI,
        ),
        (
            "Opus 4.7",
            "llm_validator__anthropic_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            ANTHROPIC,
        ),
        (
            "Opus 4.7 + descriptors",
            "llm_tools_validator__anthropic_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            ANTHROPIC,
        ),
        (
            "DeepSeek V4 Pro",
            "llm_validator__deepseek_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            DEEPSEEK,
        ),
        (
            "DeepSeek V4 Pro + descriptors",
            "llm_tools_validator__deepseek_frontier_selector",
            "ndcg_at_k",
            "ndcg_at_k_ci_low",
            "ndcg_at_k_ci_high",
            DEEPSEEK,
        ),
        ("Similarity baseline", "similarity_to_best_active", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", BASELINE),
        ("Random valid baseline", "random_valid", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", BASELINE),
        ("Rules baseline", "rules_only", "ndcg_at_k", "ndcg_at_k_ci_low", "ndcg_at_k_ci_high", BASELINE),
    ]
    data = []
    for label, system_name, value_key, lo_key, hi_key, color in selected:
        row = _find(rows, system_name)
        value = _float(row, value_key)
        data.append(
            {
                "label": label,
                "value": value,
                "lo": _float(row, lo_key),
                "hi": _float(row, hi_key),
                "color": color,
            }
        )
    data.sort(key=lambda item: item["value"])

    fig, ax = plt.subplots(figsize=(9.6, 7.4), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_positions = range(len(data))
    for y, item in zip(y_positions, data, strict=True):
        lo_err = item["value"] - item["lo"]
        hi_err = item["hi"] - item["value"]
        ax.errorbar(
            item["value"],
            y,
            xerr=[[lo_err], [hi_err]],
            fmt="o",
            color=item["color"],
            ecolor=item["color"],
            elinewidth=1.7,
            capsize=3.0,
            markersize=7.0,
            markeredgecolor="white",
            markeredgewidth=0.9,
            zorder=3,
        )
        label_x = min(item["hi"] + 0.010, 1.025)
        ax.text(
            label_x,
            y,
            _fmt(item["value"]),
            va="center",
            ha="left",
            fontsize=11.3,
            color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.86},
        )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([item["label"] for item in data], fontsize=12.2)
    ax.set_xlabel("NDCG@10 ranking quality across 50 decision cards (higher is better)", fontsize=12.0, color=INK)
    ax.set_xlim(0.70, 1.03)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="x", labelsize=11.0, colors=INK)
    ax.tick_params(axis="y", length=0, colors=INK)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_title("Ranking quality by system", fontsize=18.0, fontweight="bold", color=INK, pad=15)
    ax.legend(
        handles=_system_legend(),
        loc="lower right",
        frameon=False,
        fontsize=10.0,
        ncol=2,
        handletextpad=0.3,
        columnspacing=0.8,
    )
    ax.text(
        0.69,
        len(data) - 0.35,
        "NDCG@10 asks whether higher-activity candidates were placed nearer the top. LLM rows show final output after validation/repair.",
        fontsize=10.6,
        color=MUTED,
        ha="left",
        va="top",
    )
    _save_all(fig, "figure_4_ndcg_system_comparison")


def make_raw_final_plot(rows: list[dict[str, str]]) -> None:
    selected = [
        ("GPT-5.5", "llm_validator__openai_frontier_selector"),
        ("GPT-5.5\n+ descriptors", "llm_tools_validator__openai_frontier_selector"),
        ("Opus 4.7", "llm_validator__anthropic_frontier_selector"),
        ("Opus 4.7\n+ descriptors", "llm_tools_validator__anthropic_frontier_selector"),
        ("DeepSeek V4 Pro", "llm_validator__deepseek_frontier_selector"),
        ("DeepSeek V4 Pro\n+ descriptors", "llm_tools_validator__deepseek_frontier_selector"),
    ]
    data = []
    for label, system_name in selected:
        row = _find(rows, system_name)
        data.append(
            {
                "label": label,
                "raw": _float(row, "raw_feasible_utility"),
                "final": _float(row, "feasible_utility"),
                "raw_compliance": _float(row, "raw_compliance_rate"),
                "final_compliance": _float(row, "compliance_rate"),
                "repair": _float(row, "repaired_rate"),
            }
        )
    data.sort(key=lambda item: item["final"])

    fig, ax = plt.subplots(figsize=(10.6, 6.3), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_positions = range(len(data))
    for y, item in zip(y_positions, data, strict=True):
        ax.plot([item["raw"], item["final"]], [y, y], color="#c5ccd2", linewidth=4, solid_capstyle="round", zorder=1)
        ax.scatter(item["raw"], y, s=78, color=RAW, edgecolor="white", linewidth=0.9, zorder=3, label="Raw output" if y == 0 else "")
        ax.scatter(item["final"], y, s=90, color=FINAL, edgecolor="white", linewidth=0.9, zorder=4, label="After validation/repair" if y == 0 else "")
        ax.text(item["raw"] - 0.65, y, _fmt(item["raw"]), ha="right", va="center", fontsize=9.5, color=MUTED)
        ax.text(item["final"] + 0.65, y, _fmt(item["final"]), ha="left", va="center", fontsize=9.5, color=INK)
        ax.text(
            83.0,
            y,
            f"repair on {item['repair']:.0%} of tasks",
            ha="left",
            va="center",
            fontsize=9.2,
            color=MUTED,
        )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([item["label"] for item in data], fontsize=10.3)
    ax.set_xlabel("Mean feasible utility", fontsize=10.6, color=INK)
    ax.set_xlim(46, 87)
    ax.set_ylim(-0.35, len(data) - 0.35)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="x", labelsize=9.6, colors=INK)
    ax.tick_params(axis="y", length=0, colors=INK)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(loc="upper left", bbox_to_anchor=(0.72, 1.02), frameon=False, fontsize=9.2)
    ax.set_title("Raw versus final utility for selected language models", fontsize=15.0, fontweight="bold", color=INK, pad=13)
    _save_all(fig, "figure_5_raw_vs_final_llm")


def make_raw_final_compliance_plot(rows: list[dict[str, str]]) -> None:
    selected = [
        ("GPT-5.5", "llm_validator__openai_frontier_selector"),
        ("GPT-5.5\n+ descriptors", "llm_tools_validator__openai_frontier_selector"),
        ("Opus 4.7", "llm_validator__anthropic_frontier_selector"),
        ("Opus 4.7\n+ descriptors", "llm_tools_validator__anthropic_frontier_selector"),
        ("DeepSeek V4 Pro", "llm_validator__deepseek_frontier_selector"),
        ("DeepSeek V4 Pro\n+ descriptors", "llm_tools_validator__deepseek_frontier_selector"),
    ]
    data = []
    for label, system_name in selected:
        row = _find(rows, system_name)
        data.append(
            {
                "label": label,
                "raw": _float(row, "raw_compliance_rate"),
                "final": _float(row, "compliance_rate"),
                "repair": _float(row, "repaired_rate"),
            }
        )
    data.sort(key=lambda item: item["raw"])

    fig, ax = plt.subplots(figsize=(10.6, 6.1), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_positions = range(len(data))
    for y, item in zip(y_positions, data, strict=True):
        ax.plot([item["raw"], item["final"]], [y, y], color="#c5ccd2", linewidth=4, solid_capstyle="round", zorder=1)
        ax.scatter(item["raw"], y, s=78, color=RAW, edgecolor="white", linewidth=0.9, zorder=3, label="Raw output" if y == 0 else "")
        ax.scatter(item["final"], y, s=90, color=FINAL, edgecolor="white", linewidth=0.9, zorder=4, label="Final guarded output" if y == 0 else "")
        ax.text(item["raw"] - 0.012, y, _fmt(item["raw"]), ha="right", va="center", fontsize=9.5, color=MUTED)
        ax.text(item["final"] + 0.010, y, _fmt(item["final"]), ha="left", va="center", fontsize=9.5, color=INK)
        ax.text(
            1.070,
            y,
            f"repair on {item['repair']:.0%} of tasks",
            ha="left",
            va="center",
            fontsize=9.2,
            color=MUTED,
        )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([item["label"] for item in data], fontsize=10.3)
    ax.set_xlabel("Compliance: valid selected entries divided by requested top-10 list", fontsize=10.5, color=INK)
    ax.set_xlim(0.66, 1.13)
    ax.set_ylim(-0.35, len(data) - 0.35)
    ax.set_xticks([0.70, 0.80, 0.90, 1.00])
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="x", labelsize=9.6, colors=INK)
    ax.tick_params(axis="y", length=0, colors=INK)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(loc="upper left", bbox_to_anchor=(0.70, 1.03), frameon=False, fontsize=9.2)
    ax.set_title("Raw versus final compliance for selected language models", fontsize=15.0, fontweight="bold", color=INK, pad=13)
    _save_all(fig, "figure_6_raw_vs_final_compliance")


def make_leaderboard_summary(rows: list[dict[str, str]]) -> None:
    utility_specs = [
        ("Oracle", "oracle_valid_topk", "feasible_utility", ORACLE),
        ("QSAR linear\nSVR", "qsar_svm", "feasible_utility", QSAR),
        ("QSAR gradient\nboosting", "qsar_gbt", "feasible_utility", QSAR),
        ("QSAR random\nforest", "qsar_rf", "feasible_utility", QSAR),
        ("GPT-5.5", "llm_validator__openai_frontier_selector", "feasible_utility", OPENAI),
        ("GPT-5.5\n+ descriptors", "llm_tools_validator__openai_frontier_selector", "feasible_utility", OPENAI),
    ]
    ndcg_specs = [
        ("Oracle", "oracle_valid_topk", "ndcg_at_k", ORACLE),
        ("QSAR linear\nSVR", "qsar_svm", "ndcg_at_k", QSAR),
        ("QSAR random\nforest", "qsar_rf", "ndcg_at_k", QSAR),
        ("QSAR gradient\nboosting", "qsar_gbt", "ndcg_at_k", QSAR),
        ("GPT-5.5", "llm_validator__openai_frontier_selector", "ndcg_at_k", OPENAI),
        ("GPT-5.5\n+ descriptors", "llm_tools_validator__openai_frontier_selector", "ndcg_at_k", OPENAI),
    ]
    compliance_specs = [
        ("GPT-5.5\n+ descriptors", "llm_tools_validator__openai_frontier_selector", "raw_compliance_rate", OPENAI),
        ("GPT-5.5", "llm_validator__openai_frontier_selector", "raw_compliance_rate", OPENAI),
        ("DeepSeek V4 Pro\n+ descriptors", "llm_tools_validator__deepseek_frontier_selector", "raw_compliance_rate", DEEPSEEK),
        ("Anthropic Opus 4.7\n+ descriptors", "llm_tools_validator__anthropic_frontier_selector", "raw_compliance_rate", ANTHROPIC),
        ("DeepSeek V4 Pro", "llm_validator__deepseek_frontier_selector", "raw_compliance_rate", DEEPSEEK),
        ("Anthropic Opus 4.7", "llm_validator__anthropic_frontier_selector", "raw_compliance_rate", ANTHROPIC),
    ]

    panels = [
        ("Feasible utility", "Higher selected activity", utility_specs, (72, 91), "{:.1f}"),
        ("Ranking quality", "NDCG@10", ndcg_specs, (0.80, 1.02), "{:.3f}"),
        ("Raw LLM compliance", "Before validation/repair", compliance_specs, (0.66, 1.02), "{:.3f}"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(10.6, 9.8), dpi=220)
    fig.patch.set_facecolor("white")
    for ax, (title, subtitle, specs, xlim, fmt) in zip(axes, panels, strict=True):
        data = []
        for label, system_name, metric, color in specs:
            row = _find(rows, system_name)
            data.append({"label": label, "value": _float(row, metric), "color": color})
        data.sort(key=lambda item: item["value"])

        y_positions = range(len(data))
        left = xlim[0]
        widths = [item["value"] - left for item in data]
        ax.barh(
            list(y_positions),
            widths,
            left=left,
            color=[item["color"] for item in data],
            height=0.56,
            alpha=0.90,
        )
        for y, item in zip(y_positions, data, strict=True):
            ax.text(
                item["value"] + (xlim[1] - xlim[0]) * 0.015,
                y,
                fmt.format(item["value"]),
                ha="left",
                va="center",
                fontsize=9.5,
                color=INK,
            )
        ax.set_yticks(list(y_positions))
        ax.set_yticklabels([item["label"] for item in data], fontsize=10.0)
        ax.set_xlim(*xlim)
        ax.set_title(title, fontsize=12.8, fontweight="bold", color=INK, pad=16)
        ax.text(
            0.5,
            1.01,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=9.0,
            color=MUTED,
        )
        ax.grid(axis="x", color=GRID, linewidth=0.7)
        ax.tick_params(axis="x", labelsize=9.0, colors=INK)
        ax.tick_params(axis="y", length=0, colors=INK)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(GRID)

    fig.suptitle("Leaderboard snapshot", fontsize=16.4, fontweight="bold", color=INK, y=0.995)
    fig.text(
        0.5,
        0.015,
        "Compliance panel uses raw language-model outputs. Final guarded compliance is 1.000 after validation/repair for these rows.",
        ha="center",
        va="bottom",
        fontsize=9.0,
        color=MUTED,
    )
    fig.tight_layout(rect=(0.04, 0.055, 0.995, 0.955), h_pad=2.25)
    _save_all(fig, "figure_7_leaderboard_summary")


def make_failure_taxonomy_figure(rows: list[dict[str, str]]) -> None:
    systems = [
        ("OpenAI gpt-5.5", "bare_llm__openai_frontier_selector"),
        ("OpenAI gpt-5.5\n+ descriptors", "llm_tools__openai_frontier_selector"),
        ("Anthropic Opus 4.7", "bare_llm__anthropic_frontier_selector"),
        ("Anthropic Opus 4.7\n+ descriptors", "llm_tools__anthropic_frontier_selector"),
        ("DeepSeek V4 Pro", "bare_llm__deepseek_frontier_selector"),
        ("DeepSeek V4 Pro\n+ descriptors", "llm_tools__deepseek_frontier_selector"),
    ]
    failure_types = [
        ("none", "No detected\nissue"),
        ("constraint_failure", "Molecular-rule\nfailure"),
        ("selection_contract_failure", "Shortlist-format\nfailure"),
        ("schema_failure", "JSON/schema\nfailure"),
    ]
    lookup = {
        (row["system_name"], row["failure_type"]): int(float(row["cards_with_type"]))
        for row in rows
    }
    matrix = [
        [lookup.get((system_name, failure_type), 0) for failure_type, _ in failure_types]
        for _, system_name in systems
    ]

    fig, ax = plt.subplots(figsize=(8.8, 4.8), dpi=220)
    fig.patch.set_facecolor("white")
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=50, aspect="auto")

    ax.set_xticks(range(len(failure_types)))
    ax.set_xticklabels([label for _, label in failure_types], fontsize=8.5)
    ax.set_yticks(range(len(systems)))
    ax.set_yticklabels([label for label, _ in systems], fontsize=8.7)
    ax.tick_params(axis="both", length=0, colors=INK)

    for row_idx, row_values in enumerate(matrix):
        for col_idx, value in enumerate(row_values):
            color = "white" if value >= 28 else INK
            ax.text(
                col_idx,
                row_idx,
                str(value),
                ha="center",
                va="center",
                fontsize=9.0,
                fontweight="bold",
                color=color,
            )

    ax.set_title("Raw language-model failure taxonomy", fontsize=13.5, fontweight="bold", color=INK, pad=22)
    ax.text(
        0.5,
        1.035,
        "Number of tasks out of 50 before validation/repair",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.4,
        color=MUTED,
    )
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.025)
    cbar.set_label("Tasks", fontsize=8.0, color=INK)
    cbar.ax.tick_params(labelsize=7.5, colors=INK)

    fig.text(
        0.5,
        0.015,
        "Failure categories can overlap on the same task, so row counts should not be summed.",
        ha="center",
        va="bottom",
        fontsize=8.0,
        color=MUTED,
    )
    fig.tight_layout(rect=(0.04, 0.055, 0.98, 0.93))
    _save_all(fig, "figure_8_failure_taxonomy")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _main_table(rows: list[dict[str, str]]) -> str:
    specs = [
        ("Oracle upper bound", "oracle_valid_topk", "feasible_utility", "ndcg_at_k", "Uses hidden activity; not deployable"),
        ("QSAR linear SVR", "qsar_svm", "feasible_utility", "ndcg_at_k", "Ranks prefiltered feasible candidates"),
        ("QSAR gradient boosting", "qsar_gbt", "feasible_utility", "ndcg_at_k", "Ranks prefiltered feasible candidates"),
        ("QSAR random forest", "qsar_rf", "feasible_utility", "ndcg_at_k", "Ranks prefiltered feasible candidates"),
        ("OpenAI gpt-5.5 + validation/repair", "llm_validator__openai_frontier_selector", "feasible_utility", "ndcg_at_k", "Best final LLM row"),
        ("OpenAI gpt-5.5 + descriptors + validation/repair", "llm_tools_validator__openai_frontier_selector", "feasible_utility", "ndcg_at_k", "Descriptor-enriched LLM row"),
        ("OpenAI gpt-5.5 + descriptors, raw output", "llm_tools_validator__openai_frontier_selector", "raw_feasible_utility", "raw_ndcg_at_k", "Best raw LLM row"),
        ("Similarity baseline", "similarity_to_best_active", "feasible_utility", "ndcg_at_k", "Ranks prefiltered feasible candidates"),
        ("Random valid baseline", "random_valid", "feasible_utility", "ndcg_at_k", "Selects only feasible candidates"),
        ("Rules baseline", "rules_only", "feasible_utility", "ndcg_at_k", "Ranks prefiltered feasible candidates"),
    ]
    table_rows = []
    for label, system_name, utility_key, ndcg_key, note in specs:
        row = _find(rows, system_name)
        table_rows.append(
            [
                label,
                _fmt(_float(row, utility_key)),
                _fmt(_float(row, ndcg_key)),
                note,
            ]
        )
    return _table(["System", "Feasible utility", "NDCG@10", "Output handling"], table_rows)


def _raw_final_table(rows: list[dict[str, str]]) -> str:
    specs = [
        ("OpenAI gpt-5.5 + validation/repair", "llm_validator__openai_frontier_selector"),
        ("Anthropic Opus 4.7 + validation/repair", "llm_validator__anthropic_frontier_selector"),
        ("DeepSeek V4 Pro + validation/repair", "llm_validator__deepseek_frontier_selector"),
        ("OpenAI gpt-5.5 + descriptors + validation/repair", "llm_tools_validator__openai_frontier_selector"),
        ("Anthropic Opus 4.7 + descriptors + validation/repair", "llm_tools_validator__anthropic_frontier_selector"),
        ("DeepSeek V4 Pro + descriptors + validation/repair", "llm_tools_validator__deepseek_frontier_selector"),
    ]
    table_rows = []
    for label, system_name in specs:
        row = _find(rows, system_name)
        table_rows.append(
            [
                label,
                _fmt(_float(row, "raw_feasible_utility")),
                _fmt(_float(row, "feasible_utility")),
                _fmt(_float(row, "raw_compliance_rate")),
                _fmt(_float(row, "compliance_rate")),
                f"{_float(row, 'repaired_rate'):.0%}",
            ]
        )
    return _table(["System", "Raw utility", "Final utility", "Raw compliance", "Final compliance", "Tasks where repair was used"], table_rows)


def _dataset_table(summary: dict[str, object], rows: list[dict[str, str]]) -> str:
    oracle = _find(rows, "oracle_valid_topk")
    table_rows = [
        ["Decision cards", str(summary["num_cards"])],
        ["Selection budget per card", "10"],
        ["Mean support compounds", _fmt(float(summary["support_size"]["mean"]), 2)],
        ["Support compounds range", f"{summary['support_size']['min']}-{summary['support_size']['max']}"],
        ["Mean candidate pool", _fmt(float(summary["candidate_pool_size"]["mean"]), 2)],
        ["Candidate pool range", f"{summary['candidate_pool_size']['min']}-{summary['candidate_pool_size']['max']}"],
        ["Mean feasible candidates", _fmt(float(summary["feasible_candidate_count"]["mean"]), 1)],
        ["Feasible candidates range", f"{summary['feasible_candidate_count']['min']}-{summary['feasible_candidate_count']['max']}"],
        ["Oracle feasible utility", _fmt(_float(oracle, "feasible_utility"))],
    ]
    return _table(["Measure", "Value"], table_rows)


def _paired_delta_table(rows: list[dict[str, str]]) -> str:
    wanted = {
        ("best_qsar_minus_best_final_llm", "feasible_utility"): "QSAR SVM minus best guarded language model",
        ("best_qsar_minus_best_final_llm", "ndcg_at_k"): "QSAR SVM minus best guarded language model",
        ("best_final_llm_minus_similarity", "feasible_utility"): "Best guarded language model minus similarity baseline",
        ("best_final_llm_minus_rules", "feasible_utility"): "Best guarded language model minus rules baseline",
    }
    table_rows = []
    for row in rows:
        key = (row["comparison"], row["metric"])
        if key not in wanted:
            continue
        metric = "Feasible utility" if row["metric"] == "feasible_utility" else "NDCG@10"
        table_rows.append(
            [
                wanted[key],
                metric,
                _fmt(float(row["mean_delta"])),
                f"{_fmt(float(row['ci_low']))} to {_fmt(float(row['ci_high']))}",
            ]
        )
    return _table(["Comparison", "Metric", "Mean delta", "95% interval"], table_rows)


def write_review_page() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    system_rows = _read_csv(SYSTEM_COMPARISON_PATH)
    paired_rows = _read_csv(PAIRED_DELTAS_PATH)
    failure_rows = _read_csv(FAILURE_TAXONOMY_PATH)

    make_main_utility_plot(system_rows)
    make_ndcg_plot(system_rows)
    make_raw_final_plot(system_rows)
    make_raw_final_compliance_plot(system_rows)
    make_leaderboard_summary(system_rows)
    make_failure_taxonomy_figure(failure_rows)

    dataset_table = _dataset_table(summary, system_rows)
    main_table = _main_table(system_rows)
    raw_final_table = _raw_final_table(system_rows)
    paired_table = _paired_delta_table(paired_rows)

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SpecGuard Chem Figure Review</title>
  <style>
    :root {{
      --ink: #1d252c;
      --muted: #65727d;
      --line: #d8dee4;
      --panel: #f7f9fa;
      --paper: #ffffff;
      --accent: #2f7251;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #edf1f4;
      line-height: 1.45;
    }}
    main {{
      width: min(1180px, calc(100vw - 48px));
      margin: 0 auto;
      padding: 42px 0 64px;
    }}
    header {{
      margin-bottom: 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 21px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 28px 0 10px;
      font-size: 17px;
    }}
    p {{
      margin: 0 0 14px;
      color: var(--muted);
      max-width: 900px;
    }}
    .section {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 24px;
      margin: 18px 0;
      box-shadow: 0 1px 2px rgba(20, 30, 40, 0.04);
    }}
    .figure {{
      margin: 14px 0 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 12px;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      border-radius: 4px;
    }}
    .caption {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 6px;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel);
      color: var(--ink);
      font-weight: 650;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .note {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 8px;
    }}
    .todo {{
      border-left: 4px solid var(--accent);
      padding-left: 12px;
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      main {{ width: min(100vw - 24px, 1180px); padding-top: 24px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .section {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Figure and Table Review</h1>
    <p>Draft review page for the constrained lead-optimisation manuscript. Figures are working versions; captions and labels are intentionally plain-language where possible.</p>
  </header>

  <section class="section">
    <h2>Figure 1. Example Frozen Decision Card</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_1_decision_card_anatomy.png" alt="Example frozen decision card">
    </div>
    <p class="caption">Shows what one decision card contains: known support compounds, candidate compounds, rules, budget, output schema, and scorer-only hidden activity values.</p>
  </section>

  <section class="section">
    <h2>Figure 2. Benchmark Pipeline</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_2_benchmark_pipeline.png" alt="Benchmark pipeline">
    </div>
    <p class="caption">Public CARA/ChEMBL lead-optimisation records were converted into fixed decision cards. Each method returned a top-10 shortlist, then the shortlist was checked for rule-following and hidden-activity score.</p>
  </section>

  <section class="section">
    <h2>Figure 3. Main System Comparison</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_3_main_system_comparison.png" alt="Main system comparison">
    </div>
    <p class="caption">Mean feasible utility across the 50 cards. The oracle is an upper bound; colours separate QSAR, simple baselines, and the selected OpenAI, Anthropic, and DeepSeek language-model variants. Descriptor-enriched LLM conditions are included.</p>
  </section>

  <section class="section">
    <h2>Figure 4. Ranking Quality</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_4_ndcg_system_comparison.png" alt="Ranking quality by system">
    </div>
    <p class="caption">NDCG@10 measures whether stronger candidates were placed nearer the top of the ranked shortlist. This complements feasible utility, which scores the selected top-10 set without caring as much about the exact order within the list. Descriptor-enriched LLM conditions are included.</p>
  </section>

  <section class="section">
    <h2>Figure 5. Raw Versus Final Utility</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_5_raw_vs_final_llm.png" alt="Raw versus final guarded language-model outputs">
    </div>
    <p class="caption">This figure shows selected conditions for each frontier language model, including versions with and without extra molecular descriptors. Raw output means the language-model response before deterministic repair. Final output means the guarded pipeline after validation and repair. "Repair used" is the percentage of the 50 tasks where repair was applied before final scoring.</p>
  </section>

  <section class="section">
    <h2>Figure 6. Raw Versus Final Compliance</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_6_raw_vs_final_compliance.png" alt="Raw versus final guarded compliance">
    </div>
    <p class="caption">Final compliance reaches 1.000 because the validator/repair layer enforces the output contract. The raw compliance values show how often the model/interface already followed the rules. "Repair used" is the percentage of the 50 tasks where repair was applied before final scoring.</p>
  </section>

  <section class="section">
    <h2>Figure 7. Leaderboard Snapshot</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_7_leaderboard_summary.png" alt="Leaderboard snapshot for utility, ranking quality, and raw compliance">
    </div>
    <p class="caption">Compact summary of the leading rows for feasible utility, NDCG@10 ranking quality, and raw language-model compliance. The compliance panel uses raw language-model outputs because final guarded compliance is enforced by validation/repair.</p>
  </section>

  <section class="section">
    <h2>Figure 8. Failure Taxonomy</h2>
    <div class="figure">
      <img src="figures/cara_lo_paper_50_direct_json_completed/figure_8_failure_taxonomy.png" alt="Raw language-model failure taxonomy">
    </div>
    <p class="caption">Counts of raw language-model tasks with no detected issue, molecular-rule failures, shortlist-format failures, or JSON/schema failures before validation/repair. Categories can overlap on the same task, so counts should not be summed across a row.</p>
  </section>

  <section class="section">
    <h2>Draft Tables</h2>
    <div class="grid">
      <div>
        <h3>Table 1. Dataset Summary</h3>
        {dataset_table}
      </div>
      <div>
        <h3>Key Paired Differences</h3>
        {paired_table}
      </div>
    </div>
    <h3>Table 2. Main System Comparison</h3>
    {main_table}
    <p class="note">Compliance is not shown as a single generic column in this table because it has different meanings across rows. Deterministic baselines and QSAR rank prefiltered feasible candidates, while guarded language-model rows are final outputs after validation/repair. Raw language-model compliance is shown in Figure 6 and Table 3.</p>
    <h3>Table 3. Raw Versus Final Language-Model Accounting</h3>
    {raw_final_table}
    <p class="note">All values are read from the frozen result artifacts under <code>paper/tables/cara_lo_paper_50_direct_json_completed/</code>.</p>
  </section>

  <section class="section">
    <h2>Open Design Questions</h2>
    <p class="todo">Decide whether Figures 3 and 4 should stay separate or become a two-panel figure: feasible utility on the left, ranking quality on the right.</p>
    <p class="todo">Decide whether Figures 5 and 6 should stay as separate panels or become a single two-panel raw/final figure: utility on the left, compliance on the right.</p>
  </section>
</main>
</body>
</html>
"""
    OUT_HTML.write_text(html_text, encoding="utf-8")


if __name__ == "__main__":
    write_review_page()
