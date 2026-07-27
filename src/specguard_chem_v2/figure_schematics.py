from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import (
    DECISION_CARD_INPUT_SCHEMA_VERSION,
    SCORER_OUTCOMES_SCHEMA_VERSION,
    canonical_sha256,
)
from .io import read_jsonl

EXPECTED_RELEASE_CARDS = 91
DETERMINISTIC_SYSTEMS = 7
RAW_LLM_CONDITIONS = 6
REPAIRED_LLM_VIEWS = 6

_INK = "#17212b"
_MUTED = "#5f6f7a"
_LINE = "#aab5bd"
_BLUE = "#1f5f8b"
_BLUE_LIGHT = "#e7f0f7"
_GREEN = "#28734f"
_GREEN_LIGHT = "#e8f3ec"
_ORANGE = "#a85f13"
_ORANGE_LIGHT = "#fff1dd"
_PURPLE = "#684a8f"
_PURPLE_LIGHT = "#f2ebf8"
_RED = "#963f48"
_RED_LIGHT = "#f7e9eb"
_GOLD = "#806021"
_GOLD_LIGHT = "#f6f0df"
_GRAY_LIGHT = "#f5f7f8"


@dataclass(frozen=True)
class FigureFiles:
    """Paths emitted for one schematic figure."""

    png: Path
    pdf: Path
    svg: Path


@dataclass(frozen=True)
class _ReleaseArtifacts:
    system_inputs: list[dict[str, Any]]
    scorer_outcomes: list[dict[str, Any]]


def _load_corrected_release(
    system_input_cards_path: Path | str,
    scorer_outcomes_path: Path | str,
) -> _ReleaseArtifacts:
    input_path = Path(system_input_cards_path)
    scorer_path = Path(scorer_outcomes_path)
    system_inputs = read_jsonl(input_path)
    scorer_outcomes = read_jsonl(scorer_path)

    if len(system_inputs) != EXPECTED_RELEASE_CARDS:
        raise ValueError(
            f"corrected v0.1.0 schematics require {EXPECTED_RELEASE_CARDS} system-input "
            f"cards; found {len(system_inputs)} in {input_path}"
        )
    if len(scorer_outcomes) != EXPECTED_RELEASE_CARDS:
        raise ValueError(
            f"corrected v0.1.0 schematics require {EXPECTED_RELEASE_CARDS} scorer rows; "
            f"found {len(scorer_outcomes)} in {scorer_path}"
        )

    for index, (card, scorer) in enumerate(
        zip(system_inputs, scorer_outcomes, strict=True),
        start=1,
    ):
        if card.get("schema_version") != DECISION_CARD_INPUT_SCHEMA_VERSION:
            raise ValueError(f"{input_path}:{index} is not a corrected split system-input card")
        if scorer.get("schema_version") != SCORER_OUTCOMES_SCHEMA_VERSION:
            raise ValueError(f"{scorer_path}:{index} is not a corrected scorer-only row")
        if card.get("provenance", {}).get("benchmark_version") != "0.1.0":
            raise ValueError(f"{input_path}:{index} does not declare benchmark version 0.1.0")
        if card.get("task_id") != scorer.get("task_id"):
            raise ValueError(f"task mismatch at paired row {index}")

        candidates = card.get("candidate_pool")
        if not isinstance(candidates, list):
            raise ValueError(f"{input_path}:{index} has no candidate_pool list")
        if any("activity_value" in candidate for candidate in candidates):
            raise ValueError(
                f"{input_path}:{index} leaks candidate activity into the system-input card"
            )
        if canonical_sha256(card) != scorer.get("system_input_sha256"):
            raise ValueError(f"scorer hash binding mismatch at paired row {index}")

        candidate_ids = [candidate.get("id") for candidate in candidates]
        outcome_ids = [outcome.get("candidate_id") for outcome in scorer.get("outcomes", [])]
        if candidate_ids != outcome_ids:
            raise ValueError(f"candidate/outcome order mismatch at paired row {index}")

    return _ReleaseArtifacts(
        system_inputs=system_inputs,
        scorer_outcomes=scorer_outcomes,
    )


def _matplotlib() -> tuple[Any, Any, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    return plt, FancyBboxPatch, Rectangle


def _panel(
    ax: Any,
    fancy_box: Any,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    facecolor: str,
    edgecolor: str,
    linewidth: float = 1.2,
    radius: float = 0.012,
    zorder: int = 2,
) -> None:
    ax.add_patch(
        fancy_box(
            (x, y),
            width,
            height,
            boxstyle=f"round,pad=0.008,rounding_size={radius}",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth,
            zorder=zorder,
        )
    )


def _arrow(
    ax: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = _MUTED,
    dashed: bool = False,
    connectionstyle: str = "arc3",
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        zorder=1,
        arrowprops={
            "arrowstyle": "-|>",
            "color": color,
            "lw": 1.25,
            "linestyle": (0, (3, 3)) if dashed else "solid",
            "mutation_scale": 11,
            "shrinkA": 3,
            "shrinkB": 3,
            "connectionstyle": connectionstyle,
        },
    )


def _heading(
    ax: Any,
    x: float,
    y: float,
    title: str,
    subtitle: str = "",
    *,
    color: str = _INK,
    align: str = "left",
    title_size: float = 10.0,
    subtitle_size: float = 7.5,
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
        zorder=4,
    )
    if subtitle:
        ax.text(
            x,
            y - 0.032,
            subtitle,
            ha=align,
            va="top",
            fontsize=subtitle_size,
            color=_INK,
            linespacing=1.25,
            zorder=4,
        )


def _short(value: object, width: int) -> str:
    text = str(value)
    if len(text) <= width:
        return text
    return f"{text[: width - 1]}…"


def _number(value: object, digits: int = 1) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return "—"


def _table(
    ax: Any,
    rectangle: Any,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    headers: list[str],
    rows: list[list[str]],
    column_weights: list[float],
    header_color: str,
    body_size: float = 6.0,
    header_size: float = 6.2,
) -> None:
    row_height = height / (len(rows) + 1)
    total_weight = sum(column_weights)
    fractions = [weight / total_weight for weight in column_weights]
    cursor = x
    for header, fraction in zip(headers, fractions, strict=True):
        cell_width = width * fraction
        ax.add_patch(
            rectangle(
                (cursor, y + height - row_height),
                cell_width,
                row_height,
                facecolor=header_color,
                edgecolor="white",
                linewidth=0.8,
                zorder=3,
            )
        )
        ax.text(
            cursor + 0.005,
            y + height - row_height / 2,
            header,
            ha="left",
            va="center",
            fontsize=header_size,
            fontweight="bold",
            color=_INK,
            zorder=4,
        )
        cursor += cell_width

    for row_index, row in enumerate(rows):
        cursor = x
        row_y = y + height - row_height * (row_index + 2)
        fill = "white" if row_index % 2 == 0 else "#f5f7f8"
        for value, fraction in zip(row, fractions, strict=True):
            cell_width = width * fraction
            ax.add_patch(
                rectangle(
                    (cursor, row_y),
                    cell_width,
                    row_height,
                    facecolor=fill,
                    edgecolor="white",
                    linewidth=0.8,
                    zorder=3,
                )
            )
            ax.text(
                cursor + 0.005,
                row_y + row_height / 2,
                value,
                ha="left",
                va="center",
                fontsize=body_size,
                color=_INK,
                zorder=4,
            )
            cursor += cell_width


def _save_figure(fig: Any, output_dir: Path | str, stem: str) -> FigureFiles:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    files = FigureFiles(
        png=directory / f"{stem}.png",
        pdf=directory / f"{stem}.pdf",
        svg=directory / f"{stem}.svg",
    )
    fig.savefig(
        files.png,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.12,
        metadata={"Software": "SpecGuard-Chem v2"},
    )
    fig.savefig(
        files.pdf,
        bbox_inches="tight",
        pad_inches=0.12,
        metadata={
            "Creator": "SpecGuard-Chem v2",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(
        files.svg,
        bbox_inches="tight",
        pad_inches=0.12,
        metadata={"Creator": "SpecGuard-Chem v2", "Date": None},
    )
    return files


def _is_feasible(candidate: dict[str, Any]) -> bool:
    descriptors = candidate.get("descriptors", {})
    mw = descriptors.get("mw")
    clogp = descriptors.get("clogp")
    return (
        descriptors.get("valid_smiles") is True
        and isinstance(mw, (int, float))
        and mw <= 500
        and isinstance(clogp, (int, float))
        and clogp <= 4.5
    )


def make_decision_card_anatomy_figure(
    system_input_cards_path: Path | str,
    scorer_outcomes_path: Path | str,
    output_dir: Path | str,
) -> FigureFiles:
    """Render the corrected split-artifact anatomy using the first frozen card."""

    artifacts = _load_corrected_release(system_input_cards_path, scorer_outcomes_path)
    card = artifacts.system_inputs[0]
    scorer = artifacts.scorer_outcomes[0]
    candidates = card["candidate_pool"]
    feasible = [candidate for candidate in candidates if _is_feasible(candidate)]
    support = card["support_set"]
    outcome_by_id = {outcome["candidate_id"]: outcome for outcome in scorer["outcomes"]}
    example_candidates = feasible[:2]

    plt, fancy_box, rectangle = _matplotlib()
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "specguard-chem-v2",
        }
    ):
        fig = plt.figure(figsize=(14.0, 8.4))
        ax = fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        ax.text(
            0.04,
            0.965,
            "One task, two hash-bound artifacts",
            ha="left",
            va="top",
            fontsize=19,
            fontweight="bold",
            color=_INK,
        )
        ax.text(
            0.04,
            0.925,
            (
                f"{card['task_id']}  •  50 observed supports  •  "
                f"{len(candidates)} candidates  •  {len(feasible)} feasible  •  "
                f"budget k={card['budget_k']}"
            ),
            ha="left",
            va="top",
            fontsize=9.3,
            color=_MUTED,
        )

        _panel(
            ax,
            fancy_box,
            0.035,
            0.105,
            0.625,
            0.775,
            facecolor="#fbfcfd",
            edgecolor="#b9cedd",
            linewidth=1.5,
        )
        _panel(
            ax,
            fancy_box,
            0.705,
            0.18,
            0.26,
            0.63,
            facecolor="#fdfafb",
            edgecolor="#ddbdc2",
            linewidth=1.5,
        )
        ax.axvline(0.682, ymin=0.13, ymax=0.84, color=_RED, linestyle=(0, (3, 3)), lw=1.1)
        ax.text(
            0.682,
            0.855,
            "visibility boundary",
            ha="center",
            va="bottom",
            fontsize=7.2,
            fontweight="bold",
            color=_RED,
        )

        _heading(
            ax,
            0.055,
            0.85,
            "SYSTEM-VISIBLE INPUT CARD",
            "schema: specguard.decision-card-input.v1  •  candidate activity is absent",
            color=_BLUE,
            title_size=11.2,
        )
        _heading(
            ax,
            0.725,
            0.78,
            "SCORER-ONLY OUTCOMES",
            "schema: specguard.scorer-outcomes.v1\nnever supplied to deployable systems",
            color=_RED,
            title_size=10.4,
            subtitle_size=7.2,
        )

        _panel(
            ax,
            fancy_box,
            0.055,
            0.705,
            0.585,
            0.085,
            facecolor=_BLUE_LIGHT,
            edgecolor="#c9dce9",
        )
        context = card["assay_context"]
        _heading(
            ax,
            0.07,
            0.772,
            "Assay context and provenance",
            (
                f"target {context['target']}  •  {context['assay_type']}  •  "
                f"{context['activity_scale']} ({context['activity_direction']})  •  "
                f"source {context['source']}\nbenchmark 0.1.0  •  data cara-lo-all/0.1.0"
            ),
            color=_BLUE,
            title_size=8.8,
            subtitle_size=6.9,
        )

        _heading(
            ax,
            0.055,
            0.685,
            "Observed support evidence",
            "IDs, structures, descriptors, and measured pChEMBL are visible.",
            color=_GREEN,
            title_size=8.9,
            subtitle_size=6.7,
        )
        support_rows = [
            [
                compound["id"],
                _short(compound["smiles"], 36),
                _number(compound["activity_value"], 2),
                _number(compound["descriptors"].get("mw"), 1),
                _number(compound["descriptors"].get("clogp"), 2),
            ]
            for compound in support[:2]
        ]
        _table(
            ax,
            rectangle,
            x=0.055,
            y=0.55,
            width=0.585,
            height=0.085,
            headers=["compound ID", "SMILES", "pChEMBL", "MW", "cLogP"],
            rows=support_rows,
            column_weights=[1.2, 3.2, 0.85, 0.65, 0.7],
            header_color="#d8eadf",
        )

        _heading(
            ax,
            0.055,
            0.525,
            "Candidate action space",
            "IDs, structures, and permitted descriptors are visible; there is no activity field.",
            color=_ORANGE,
            title_size=8.9,
            subtitle_size=6.7,
        )
        candidate_rows = [
            [
                compound["id"],
                _short(compound["smiles"], 36),
                _number(compound["descriptors"].get("mw"), 1),
                _number(compound["descriptors"].get("clogp"), 2),
                _number(compound["descriptors"].get("tpsa"), 1),
            ]
            for compound in example_candidates
        ]
        _table(
            ax,
            rectangle,
            x=0.055,
            y=0.39,
            width=0.585,
            height=0.085,
            headers=["candidate ID", "SMILES", "MW", "cLogP", "TPSA"],
            rows=candidate_rows,
            column_weights=[1.2, 3.2, 0.65, 0.7, 0.65],
            header_color="#f5dfbd",
        )

        _panel(
            ax,
            fancy_box,
            0.055,
            0.215,
            0.37,
            0.135,
            facecolor=_GRAY_LIGHT,
            edgecolor="#d4dce1",
        )
        _heading(
            ax,
            0.07,
            0.33,
            "Hard action and eligibility constraints",
            (
                "OUTPUT  exactly 10 • candidate-pool IDs • unique • exclude support\n"
                "CANDIDATE  parseable SMILES • MW ≤ 500 • cLogP ≤ 4.5\n"
                "forbidden SMARTS list: empty"
            ),
            color=_BLUE,
            title_size=8.3,
            subtitle_size=6.8,
        )
        _panel(
            ax,
            fancy_box,
            0.445,
            0.215,
            0.195,
            0.135,
            facecolor=_GRAY_LIGHT,
            edgecolor="#d4dce1",
        )
        _heading(
            ax,
            0.46,
            0.33,
            "Ordered output schema",
            (
                "rank: integer\n"
                "candidate_id: string\n"
                "confidence: optional number\n"
                "→ ranked top-10 batch"
            ),
            color=_BLUE,
            title_size=8.3,
            subtitle_size=6.8,
        )

        sha = scorer["system_input_sha256"]
        _panel(
            ax,
            fancy_box,
            0.725,
            0.615,
            0.22,
            0.09,
            facecolor=_RED_LIGHT,
            edgecolor="#e2c7cb",
        )
        _heading(
            ax,
            0.74,
            0.687,
            "Cryptographic binding",
            f"same task_id\nsystem_input_sha256:\n{sha[:16]}…{sha[-8:]}",
            color=_RED,
            title_size=8.2,
            subtitle_size=6.3,
        )
        _arrow(
            ax,
            (0.64, 0.66),
            (0.725, 0.66),
            color=_RED,
            dashed=True,
        )

        scorer_rows = [
            [
                candidate["id"],
                _number(outcome_by_id[candidate["id"]]["activity_value"], 2),
            ]
            for candidate in example_candidates
        ]
        _heading(
            ax,
            0.725,
            0.58,
            "Retrospective candidate outcomes",
            "One outcome for every candidate ID.",
            color=_RED,
            title_size=8.5,
            subtitle_size=6.7,
        )
        _table(
            ax,
            rectangle,
            x=0.725,
            y=0.435,
            width=0.22,
            height=0.085,
            headers=["candidate_id", "hidden pChEMBL"],
            rows=scorer_rows,
            column_weights=[1.4, 1.0],
            header_color="#efdadd",
            body_size=6.2,
        )
        _panel(
            ax,
            fancy_box,
            0.725,
            0.245,
            0.22,
            0.14,
            facecolor=_GOLD_LIGHT,
            edgecolor="#e1d4af",
        )
        _heading(
            ax,
            0.74,
            0.365,
            "Evaluator use after selection",
            (
                "Join selected candidate IDs to outcomes.\n"
                "Compute feasible utility, NDCG@10,\n"
                "and constrained regret.\n"
                "Oracle access is upper-bound only."
            ),
            color=_GOLD,
            title_size=8.2,
            subtitle_size=6.6,
        )

        _panel(
            ax,
            fancy_box,
            0.055,
            0.125,
            0.89,
            0.05,
            facecolor="#eef3f6",
            edgecolor="#d4dfe5",
        )
        ax.text(
            0.5,
            0.15,
            (
                "Leakage boundary: candidate activity is prohibited by the input schema; "
                "the evaluator joins the separate, hash-bound scorer row only after an "
                "action is issued."
            ),
            ha="center",
            va="center",
            fontsize=7.5,
            fontweight="bold",
            color=_INK,
        )

        files = _save_figure(fig, output_dir, "figure_1_decision_card_anatomy")
        plt.close(fig)
    return files


def make_benchmark_pipeline_figure(
    system_input_cards_path: Path | str,
    scorer_outcomes_path: Path | str,
    output_dir: Path | str,
) -> FigureFiles:
    """Render the corrected v0.1.0 data, execution, repair, and scoring pipeline."""

    artifacts = _load_corrected_release(system_input_cards_path, scorer_outcomes_path)
    num_cards = len(artifacts.system_inputs)
    num_requests = num_cards * RAW_LLM_CONDITIONS
    comparison_rows = DETERMINISTIC_SYSTEMS + RAW_LLM_CONDITIONS + REPAIRED_LLM_VIEWS
    if num_requests != 546:
        raise ValueError(f"expected 546 corrected LLM requests; derived {num_requests}")

    plt, fancy_box, _ = _matplotlib()
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "specguard-chem-v2",
        }
    ):
        fig = plt.figure(figsize=(14.5, 8.6))
        ax = fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        ax.text(
            0.5,
            0.965,
            "Corrected v0.1.0 benchmark pipeline",
            ha="center",
            va="top",
            fontsize=19,
            fontweight="bold",
            color=_INK,
        )
        ax.text(
            0.5,
            0.928,
            (
                "One fixed action contract • scorer outcomes never enter deployable "
                "system prompts • raw and repaired views share the same responses"
            ),
            ha="center",
            va="top",
            fontsize=8.8,
            color=_MUTED,
        )

        _panel(
            ax,
            fancy_box,
            0.035,
            0.82,
            0.93,
            0.075,
            facecolor=_BLUE_LIGHT,
            edgecolor="#c8dbe8",
        )
        _heading(
            ax,
            0.5,
            0.875,
            "CARA v1.0.1 LO_All → corrected positional import and exhaustive audit",
            "100 official tasks • include every task with at least 10 feasible candidates → 91 included / 9 excluded",
            color=_BLUE,
            align="center",
            title_size=9.3,
            subtitle_size=7.2,
        )

        _panel(
            ax,
            fancy_box,
            0.055,
            0.685,
            0.57,
            0.09,
            facecolor=_GREEN_LIGHT,
            edgecolor="#c7ddcf",
        )
        _heading(
            ax,
            0.34,
            0.752,
            f"{num_cards} SYSTEM-INPUT CARDS",
            (
                "assay context • 50 measured supports • finite candidate pool • "
                "constraints • k=10\ncandidate activity absent"
            ),
            color=_GREEN,
            align="center",
            title_size=9.1,
            subtitle_size=7.0,
        )
        _panel(
            ax,
            fancy_box,
            0.68,
            0.685,
            0.265,
            0.09,
            facecolor=_RED_LIGHT,
            edgecolor="#dfc1c6",
        )
        _heading(
            ax,
            0.8125,
            0.752,
            f"{num_cards} SCORER-ONLY ROWS",
            "candidate pChEMBL outcomes\nsame task_id + system-input SHA256",
            color=_RED,
            align="center",
            title_size=9.1,
            subtitle_size=7.0,
        )
        _arrow(ax, (0.5, 0.82), (0.34, 0.775), color=_BLUE)
        _arrow(ax, (0.5, 0.82), (0.8125, 0.775), color=_RED, dashed=True)

        _panel(
            ax,
            fancy_box,
            0.035,
            0.48,
            0.29,
            0.15,
            facecolor=_GRAY_LIGHT,
            edgecolor="#d3dade",
        )
        _heading(
            ax,
            0.18,
            0.605,
            f"{DETERMINISTIC_SYSTEMS} DETERMINISTIC SYSTEMS",
            (
                "6 deployable: random-valid, rules, similarity,\n"
                "QSAR RF / GBT / linear SVR\n"
                "1 scorer-only oracle upper bound"
            ),
            color=_INK,
            align="center",
            title_size=9.1,
            subtitle_size=7.1,
        )
        _panel(
            ax,
            fancy_box,
            0.355,
            0.48,
            0.355,
            0.15,
            facecolor=_PURPLE_LIGHT,
            edgecolor="#d7c8e5",
        )
        _heading(
            ax,
            0.5325,
            0.605,
            f"{RAW_LLM_CONDITIONS} RAW LLM CONDITIONS",
            (
                "3 frozen provider/model conditions × 2 interfaces\n"
                f"{num_cards} cards per condition = {num_requests} provider requests\n"
                "exact requests • one successful attempt • cached traces"
            ),
            color=_PURPLE,
            align="center",
            title_size=9.1,
            subtitle_size=7.1,
        )
        _panel(
            ax,
            fancy_box,
            0.74,
            0.48,
            0.225,
            0.15,
            facecolor=_ORANGE_LIGHT,
            edgecolor="#e4cda9",
        )
        _heading(
            ax,
            0.8525,
            0.605,
            f"{REPAIRED_LLM_VIEWS} ZERO-CALL REPAIRED VIEWS",
            (
                f"{num_cards} actions per view\nretain valid IDs • remove violations\n"
                "fill from deterministic rules ranking"
            ),
            color=_ORANGE,
            align="center",
            title_size=8.8,
            subtitle_size=6.9,
        )

        _arrow(ax, (0.27, 0.685), (0.18, 0.63), color=_GREEN)
        _arrow(ax, (0.45, 0.685), (0.5325, 0.63), color=_GREEN)
        _arrow(ax, (0.8125, 0.685), (0.255, 0.63), color=_RED, dashed=True)
        ax.text(
            0.68,
            0.655,
            "evaluator/oracle only",
            ha="center",
            va="center",
            fontsize=6.7,
            color=_RED,
            fontweight="bold",
        )
        _arrow(ax, (0.71, 0.555), (0.74, 0.555), color=_ORANGE)
        ax.text(
            0.725,
            0.575,
            "same response",
            ha="center",
            va="bottom",
            fontsize=6.6,
            color=_ORANGE,
            fontweight="bold",
        )

        _panel(
            ax,
            fancy_box,
            0.07,
            0.35,
            0.86,
            0.075,
            facecolor="#eef3f6",
            edgecolor="#d2dde3",
        )
        _heading(
            ax,
            0.5,
            0.402,
            "ORDERED TOP-10 ACTION RECORDS",
            (
                "7 deterministic/oracle traces  •  6 raw LLM traces × 91  •  "
                "6 post-hoc-repaired traces × 91  •  repair adds zero provider calls"
            ),
            color=_BLUE,
            align="center",
            title_size=9.0,
            subtitle_size=7.0,
        )
        _arrow(ax, (0.18, 0.48), (0.3, 0.425), color=_MUTED)
        _arrow(ax, (0.5325, 0.48), (0.5, 0.425), color=_PURPLE)
        _arrow(ax, (0.8525, 0.48), (0.7, 0.425), color=_ORANGE)

        _panel(
            ax,
            fancy_box,
            0.035,
            0.185,
            0.275,
            0.115,
            facecolor=_GOLD_LIGHT,
            edgecolor="#dfd0a8",
        )
        _heading(
            ax,
            0.1725,
            0.275,
            "SCIENTIFIC UTILITY / RANKING",
            "feasible utility • NDCG@10\nconstrained regret • oracle headroom\nselected IDs joined to scorer outcomes",
            color=_GOLD,
            align="center",
            title_size=8.5,
            subtitle_size=6.9,
        )
        _panel(
            ax,
            fancy_box,
            0.355,
            0.185,
            0.275,
            0.115,
            facecolor=_BLUE_LIGHT,
            edgecolor="#c8dbe8",
        )
        _heading(
            ax,
            0.4925,
            0.275,
            "ACTION VALIDITY / FAILURES",
            (
                "zero-issue whole-action validity\nvalid-selection compliance • "
                "schema / contract /\nconstraint failure taxonomy"
            ),
            color=_BLUE,
            align="center",
            title_size=8.5,
            subtitle_size=6.9,
        )
        _panel(
            ax,
            fancy_box,
            0.675,
            0.185,
            0.29,
            0.115,
            facecolor=_PURPLE_LIGHT,
            edgecolor="#d7c8e5",
        )
        _heading(
            ax,
            0.82,
            0.275,
            "PAIRED 91-CARD ANALYSIS",
            (
                "task-level 95% bootstrap intervals\nQSAR vs repaired/raw LLM • "
                "bare vs descriptors\nraw vs repaired attribution"
            ),
            color=_PURPLE,
            align="center",
            title_size=8.5,
            subtitle_size=6.9,
        )
        _arrow(ax, (0.36, 0.35), (0.1725, 0.3), color=_GOLD)
        _arrow(ax, (0.5, 0.35), (0.4925, 0.3), color=_BLUE)
        _arrow(ax, (0.64, 0.35), (0.82, 0.3), color=_PURPLE)
        _arrow(
            ax,
            (0.8125, 0.685),
            (0.1725, 0.3),
            color=_RED,
            dashed=True,
            connectionstyle="arc3,rad=0.23",
        )

        _panel(
            ax,
            fancy_box,
            0.19,
            0.055,
            0.62,
            0.075,
            facecolor="#f4f0e6",
            edgecolor="#ddd0b6",
            linewidth=1.4,
        )
        _heading(
            ax,
            0.5,
            0.107,
            f"CANONICAL {comparison_rows}-SYSTEM COMPARISON",
            (
                "primary leaderboard • paired deltas • card diagnostics • "
                "raw/final ablations • latency, tokens, usage-derived cost"
            ),
            color=_GOLD,
            align="center",
            title_size=9.2,
            subtitle_size=7.0,
        )
        _arrow(ax, (0.1725, 0.185), (0.38, 0.13), color=_GOLD)
        _arrow(ax, (0.4925, 0.185), (0.5, 0.13), color=_BLUE)
        _arrow(ax, (0.82, 0.185), (0.62, 0.13), color=_PURPLE)

        files = _save_figure(fig, output_dir, "figure_2_benchmark_pipeline")
        plt.close(fig)
    return files


__all__ = [
    "FigureFiles",
    "make_benchmark_pipeline_figure",
    "make_decision_card_anatomy_figure",
]
