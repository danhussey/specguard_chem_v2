from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "paper/figures/cara_lo_paper_50_direct_json_completed"
OUT_STEM = "figure_2_benchmark_pipeline"

INK = "#1d252c"
MUTED = "#66727d"
LINE = "#7a858e"
LIGHT_LINE = "#d9dee3"
PAPER = "#ffffff"
PANEL = "#f7f9fa"
SOURCE = "#e8eef5"
CARD = "#ecf4ef"
METHOD = "#f8f8f5"
LLM = "#f3edf7"
ORACLE = "#f8ecec"
SCORE = "#eef2f5"
RESULT = "#f5f1e8"
BLUE = "#2d5f86"
GREEN = "#2f7251"
PURPLE = "#69538f"
RED = "#9a3f45"
BROWN = "#8a6428"


def _box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    facecolor: str = PAPER,
    edgecolor: str = LIGHT_LINE,
    linewidth: float = 1.1,
    radius: float = 0.012,
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle=f"round,pad=0.008,rounding_size={radius}",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth,
        )
    )


def _label(
    ax: plt.Axes,
    x: float,
    y: float,
    title: str,
    body: str,
    *,
    color: str = INK,
    body_size: float = 8.2,
    title_size: float = 9.0,
    align: str = "center",
) -> None:
    ax.text(
        x,
        y,
        title,
        ha=align,
        va="top",
        fontsize=title_size,
        fontweight="bold",
        color=color,
    )
    ax.text(
        x,
        y - 0.028,
        body,
        ha=align,
        va="top",
        fontsize=body_size,
        color=INK,
        linespacing=1.25,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = LINE,
    dashed: bool = False,
    lw: float = 1.15,
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "-|>",
            "color": color,
            "lw": lw,
            "mutation_scale": 9.5,
            "shrinkA": 5,
            "shrinkB": 5,
            "linestyle": (0, (3, 3)) if dashed else "solid",
        },
    )


def _center(x: float, y: float, w: float, h: float) -> tuple[float, float]:
    return x + w / 2, y + h / 2


def _labeled_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    *,
    facecolor: str,
    edgecolor: str,
    title_color: str,
    body_size: float = 8.2,
    title_size: float = 9.0,
) -> None:
    _box(ax, x, y, w, h, facecolor=facecolor, edgecolor=edgecolor)
    _label(
        ax,
        x + w / 2,
        y + h - 0.020,
        title,
        body,
        color=title_color,
        body_size=body_size,
        title_size=title_size,
    )


def make_figure() -> None:
    fig = plt.figure(figsize=(12.0, 8.0), dpi=220)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Benchmark pipeline",
        ha="center",
        va="top",
        fontsize=17,
        fontweight="bold",
        color=INK,
    )

    source = (0.335, 0.842, 0.330, 0.082)
    cards = (0.315, 0.720, 0.370, 0.090)
    methods_panel = (0.045, 0.455, 0.910, 0.210)
    shortlist = (0.355, 0.330, 0.290, 0.075)
    score_left = (0.165, 0.185, 0.310, 0.095)
    score_right = (0.525, 0.185, 0.310, 0.095)
    results = (0.315, 0.060, 0.370, 0.080)

    _labeled_box(
        ax,
        *source,
        "SOURCE DATA",
        "CARA/ChEMBL\nlead-optimisation records",
        facecolor=SOURCE,
        edgecolor="#cbd8e5",
        title_color=BLUE,
    )
    _labeled_box(
        ax,
        *cards,
        "DECISION CARDS",
        "50 fixed test cases\nknown compounds, candidate pool, rules, budget",
        facecolor=CARD,
        edgecolor="#cbded2",
        title_color=GREEN,
        body_size=8.0,
    )

    _box(
        ax,
        *methods_panel,
        facecolor=PANEL,
        edgecolor="#cfd6dc",
        linewidth=1.2,
        radius=0.015,
    )
    ax.text(
        methods_panel[0] + 0.020,
        methods_panel[1] + methods_panel[3] - 0.025,
        "METHODS COMPARED",
        ha="left",
        va="top",
        fontsize=9.4,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        methods_panel[0] + 0.190,
        methods_panel[1] + methods_panel[3] - 0.025,
        "same decision cards given to each method",
        ha="left",
        va="top",
        fontsize=8.1,
        color=MUTED,
    )

    method_y = 0.485
    method_h = 0.125
    method_w = 0.158
    method_xs = [0.070, 0.245, 0.420, 0.595, 0.770]
    method_specs = [
        ("SIMPLE RULES", "random\nproperty rules\nsimilarity", METHOD, "#d8d8cf", INK),
        ("QSAR", "standard chemistry\nprediction models", METHOD, "#d8d8cf", INK),
        ("LANGUAGE MODEL", "model chooses\nIDs directly", LLM, "#d8cfe3", PURPLE),
        ("GUARDED\nLANGUAGE MODEL", "output checked\nand repaired", LLM, "#d8cfe3", PURPLE),
        ("ORACLE", "upper bound;\nsees hidden activity", ORACLE, "#e3caca", RED),
    ]
    for x, (title, body, fill, edge, color) in zip(method_xs, method_specs, strict=True):
        _labeled_box(
            ax,
            x,
            method_y,
            method_w,
            method_h,
            title,
            body,
            facecolor=fill,
            edgecolor=edge,
            title_color=color,
            title_size=8.1,
            body_size=7.5,
        )

    _labeled_box(
        ax,
        *shortlist,
        "TOP-10 SHORTLIST",
        "ranked candidate IDs",
        facecolor="#f2f5f7",
        edgecolor="#cbd3d9",
        title_color=INK,
        body_size=8.2,
    )
    _labeled_box(
        ax,
        *score_left,
        "COMPLIANCE CHECK",
        "did the shortlist\nfollow the rules?",
        facecolor=SCORE,
        edgecolor="#cad4dc",
        title_color=BLUE,
        body_size=8.0,
    )
    _labeled_box(
        ax,
        *score_right,
        "HIDDEN-ACTIVITY SCORE",
        "were the chosen\ncompounds active?",
        facecolor=SCORE,
        edgecolor="#cad4dc",
        title_color=GREEN,
        body_size=8.0,
    )
    _labeled_box(
        ax,
        *results,
        "RESULTS",
        "leaderboard, raw/final language-model comparison,\npaired differences",
        facecolor=RESULT,
        edgecolor="#dfd4bd",
        title_color=BROWN,
        body_size=7.8,
    )

    source_center = _center(*source)
    cards_center = _center(*cards)
    panel_center = _center(*methods_panel)
    shortlist_center = _center(*shortlist)
    left_center = _center(*score_left)
    right_center = _center(*score_right)
    results_center = _center(*results)

    _arrow(ax, (source_center[0], source[1]), (cards_center[0], cards[1] + cards[3]))
    _arrow(ax, (cards_center[0], cards[1]), (panel_center[0], methods_panel[1] + methods_panel[3]))
    _arrow(ax, (panel_center[0], methods_panel[1]), (shortlist_center[0], shortlist[1] + shortlist[3]))
    _arrow(ax, (shortlist_center[0] - 0.025, shortlist[1]), (left_center[0], score_left[1] + score_left[3]))
    _arrow(ax, (shortlist_center[0] + 0.025, shortlist[1]), (right_center[0], score_right[1] + score_right[3]))
    _arrow(ax, (left_center[0], score_left[1]), (results_center[0] - 0.065, results[1] + results[3]))
    _arrow(ax, (right_center[0], score_right[1]), (results_center[0] + 0.065, results[1] + results[3]))

    ax.text(
        0.5,
        0.022,
        "Candidate activity values are hidden from tested methods. The oracle is kept separate as a non-deployable upper bound.",
        ha="center",
        va="bottom",
        fontsize=7.4,
        color=MUTED,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT_DIR / f"{OUT_STEM}.{suffix}", bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


if __name__ == "__main__":
    make_figure()
