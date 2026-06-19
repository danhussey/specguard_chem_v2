from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
CARD_PATH = ROOT / "data/cards/cara_lo_paper_50.jsonl"
OUT_DIR = ROOT / "paper/figures/cara_lo_paper_50_direct_json_completed"
OUT_STEM = "figure_1_decision_card_anatomy"

INK = "#17202a"
MUTED = "#5f6f7a"
GRID = "#d9dee3"
PANEL = "#f8fafb"
SOURCE = "#dfeaf5"
SUPPORT = "#e8f2eb"
CANDIDATE = "#fff2dc"
SCORER = "#f5e7ea"
ACCENT_BLUE = "#2f6f9f"
ACCENT_GREEN = "#2f7d55"
ACCENT_ORANGE = "#b56a1e"
ACCENT_RED = "#9a3c44"


def _load_card() -> dict[str, Any]:
    with CARD_PATH.open() as handle:
        return json.loads(handle.readline())


def _short_smiles(value: str, width: int = 32) -> str:
    if len(value) <= width:
        return value
    return f"{value[: width - 3]}..."


def _short_id(value: str, width: int = 12) -> str:
    if len(value) <= width:
        return value
    return f"{value[: width - 3]}..."


def _round(value: Any, digits: int = 1) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    facecolor: str,
    edgecolor: str = GRID,
    linewidth: float = 1.1,
    radius: float = 0.018,
) -> FancyBboxPatch:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.010,rounding_size={radius}",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    return box


def _title(ax: plt.Axes, x: float, y: float, label: str, color: str = INK) -> None:
    ax.text(x, y, label, ha="left", va="top", fontsize=10.5, fontweight="bold", color=color)


def _small(ax: plt.Axes, x: float, y: float, label: str, color: str = MUTED, size: float = 7.6) -> None:
    ax.text(x, y, label, ha="left", va="top", fontsize=size, color=color, linespacing=1.25)


def _panel_label(ax: plt.Axes, x: float, y: float, label: str, color: str) -> None:
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="white",
        bbox={
            "boxstyle": "circle,pad=0.28",
            "facecolor": color,
            "edgecolor": color,
            "linewidth": 0,
        },
    )


def _arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = MUTED) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "-|>",
            "lw": 1.1,
            "color": color,
            "mutation_scale": 9,
            "shrinkA": 2,
            "shrinkB": 2,
        },
    )


def _draw_table(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    rows: list[list[str]],
    headers: list[str],
    *,
    row_h: float,
    col_widths: list[float],
    header_color: str,
    header_size: float = 6.1,
    body_size: float = 5.8,
) -> None:
    total = sum(col_widths)
    col_fracs = [value / total for value in col_widths]
    cursor = x
    for header, frac in zip(headers, col_fracs, strict=True):
        ax.add_patch(
            Rectangle(
                (cursor, y - row_h),
                width * frac,
                row_h,
                facecolor=header_color,
                edgecolor="white",
                linewidth=0.6,
            )
        )
        ax.text(
            cursor + 0.006,
            y - row_h / 2,
            header,
            ha="left",
            va="center",
            fontsize=header_size,
            fontweight="bold",
            color=INK,
        )
        cursor += width * frac

    for row_index, row in enumerate(rows):
        row_y = y - row_h * (row_index + 2)
        cursor = x
        fill = "white" if row_index % 2 == 0 else "#f5f7f8"
        for value, frac in zip(row, col_fracs, strict=True):
            ax.add_patch(
                Rectangle(
                    (cursor, row_y),
                    width * frac,
                    row_h,
                    facecolor=fill,
                    edgecolor="white",
                    linewidth=0.6,
                )
            )
            ax.text(
                cursor + 0.006,
                row_y + row_h / 2,
                value,
                ha="left",
                va="center",
                fontsize=body_size,
                color=INK,
            )
            cursor += width * frac


def _descriptor_summary(descriptors: dict[str, Any]) -> str:
    return (
        f"mw={_round(descriptors.get('mw'))}; "
        f"cLogP={_round(descriptors.get('clogp'))}; "
        f"TPSA={_round(descriptors.get('tpsa'))}; "
        f"HBD/HBA={descriptors.get('hbd')}/{descriptors.get('hba')}; "
        f"rot={descriptors.get('rotatable_bonds')}"
    )


def _support_rows(card: dict[str, Any]) -> list[list[str]]:
    rows = []
    for compound in card["support_set"][:2]:
        rows.append(
            [
                _short_id(compound["id"]),
                _short_smiles(compound["smiles"], width=34),
                _round(compound.get("activity_value"), digits=2),
                _descriptor_summary(compound["descriptors"]),
            ]
        )
    return rows


def _candidate_rows(card: dict[str, Any]) -> list[list[str]]:
    eligible = []
    for compound in card["candidate_pool"]:
        descriptors = compound["descriptors"]
        valid_smiles = descriptors.get("valid_smiles") is True
        mw = float(descriptors.get("mw", 1e9))
        clogp = float(descriptors.get("clogp", 1e9))
        is_feasible = valid_smiles and mw <= 500 and clogp <= 4.5
        if is_feasible and len(eligible) < 2:
            eligible.append(compound)
        if len(eligible) >= 2:
            break

    rows = []
    for compound in eligible:
        rows.append(
            [
                _short_id(compound["id"]),
                _short_smiles(compound["smiles"], width=34),
                "scorer-only",
                _descriptor_summary(compound["descriptors"]),
            ]
        )
    return rows


def _constraint_rows(card: dict[str, Any]) -> list[list[str]]:
    rows = []
    for constraint in card["hard_constraints"]:
        params = constraint.get("params") or {}
        params_label = "; ".join(f"{key}={value}" for key, value in params.items())
        rows.append(
            [
                constraint["id"],
                constraint["type"],
                constraint["check"],
                _short_smiles(params_label, width=34),
            ]
        )
    return rows


def make_figure() -> None:
    card = _load_card()
    metadata = card["metadata"]

    fig = plt.figure(figsize=(12.8, 8.0), dpi=220)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.045,
        0.965,
        "Example frozen decision card",
        ha="left",
        va="top",
        fontsize=18,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.045,
        0.925,
        f"Frozen card: {card['task_id']}  |  source task: {metadata['assay_id']}",
        ha="left",
        va="top",
        fontsize=9.3,
        color=MUTED,
    )

    _box(ax, (0.055, 0.785), 0.89, 0.10, facecolor=SOURCE, edgecolor="#cad9e6")
    _title(ax, 0.075, 0.860, "card header", ACCENT_BLUE)
    header = (
        f"task_id: {card['task_id']}\n"
        f"assay_context: {{source: CARA, assay_id: {metadata['assay_id']}}}"
    )
    _small(ax, 0.075, 0.832, header, color=INK, size=7.1)
    _title(ax, 0.475, 0.860, "card-level metadata", ACCENT_BLUE)
    metadata_text = (
        f"budget_k: {card['budget_k']}; support_size: {metadata['support_size']}; "
        f"candidate_pool_size: {metadata['candidate_pool_size']}; "
        f"feasible_candidate_count: {metadata['feasible_candidate_count']}"
    )
    _small(ax, 0.475, 0.832, metadata_text, color=INK, size=7.1)

    _box(ax, (0.055, 0.575), 0.89, 0.17, facecolor=SUPPORT, edgecolor="#cbded0")
    _title(ax, 0.075, 0.720, "support_set excerpt", ACCENT_GREEN)
    _small(
        ax,
        0.075,
        0.698,
        "Support activity and descriptors are stored in the card and are visible to deployable systems.",
        size=6.9,
    )
    _draw_table(
        ax,
        0.075,
        0.665,
        0.85,
        _support_rows(card),
        ["id", "smiles", "activity_value", "descriptors"],
        row_h=0.034,
        col_widths=[0.75, 2.0, 0.7, 2.75],
        header_color="#d7e8dc",
        header_size=6.1,
        body_size=5.8,
    )

    _box(ax, (0.055, 0.365), 0.89, 0.17, facecolor=CANDIDATE, edgecolor="#e6d3b3")
    _title(ax, 0.075, 0.510, "candidate_pool excerpt", ACCENT_ORANGE)
    _small(
        ax,
        0.075,
        0.488,
        "Candidate descriptors are stored in the card. Candidate activity is retained only for offline scoring.",
        size=6.9,
    )
    _draw_table(
        ax,
        0.075,
        0.455,
        0.85,
        _candidate_rows(card),
        ["id", "smiles", "activity_value", "descriptors"],
        row_h=0.034,
        col_widths=[0.75, 2.0, 0.7, 2.75],
        header_color="#f1dfbf",
        header_size=6.1,
        body_size=5.8,
    )

    _box(ax, (0.055, 0.165), 0.55, 0.16, facecolor=PANEL, edgecolor="#d4d9dd")
    _title(ax, 0.075, 0.300, "hard_constraints", ACCENT_BLUE)
    _draw_table(
        ax,
        0.075,
        0.270,
        0.51,
        _constraint_rows(card),
        ["id", "type", "check", "params"],
        row_h=0.012,
        col_widths=[1.4, 0.75, 1.25, 1.25],
        header_color="#e8ecef",
        header_size=4.4,
        body_size=4.2,
    )

    _box(ax, (0.635, 0.165), 0.31, 0.16, facecolor=PANEL, edgecolor="#d4d9dd")
    _title(ax, 0.655, 0.300, "output_schema", ACCENT_BLUE)
    output_rows = [[key, value] for key, value in card["output_schema"].items()]
    _draw_table(
        ax,
        0.655,
        0.270,
        0.27,
        output_rows,
        ["field", "expected value"],
        row_h=0.025,
        col_widths=[1.0, 1.2],
        header_color="#e8ecef",
        header_size=5.5,
        body_size=5.3,
    )
    _box(ax, (0.055, 0.075), 0.89, 0.055, facecolor=SCORER, edgecolor="#e0c9ce")
    _title(ax, 0.075, 0.112, "leakage boundary", ACCENT_RED)
    _small(
        ax,
        0.235,
        0.112,
        "Support activity is visible input. Candidate activity is stored in the frozen card but hidden from evaluated systems and used only by the scorer.",
        color=INK,
        size=7.0,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT_DIR / f"{OUT_STEM}.{suffix}", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


if __name__ == "__main__":
    make_figure()
