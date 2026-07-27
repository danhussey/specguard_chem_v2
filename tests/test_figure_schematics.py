from __future__ import annotations

from pathlib import Path

import pytest

from specguard_chem_v2.figure_schematics import (
    make_benchmark_pipeline_figure,
    make_decision_card_anatomy_figure,
)
from specguard_chem_v2.io import read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
INPUT_CARDS = ROOT / "data/releases/v0.1.0/system_input_cards.jsonl"
SCORER_OUTCOMES = ROOT / "data/releases/v0.1.0/scorer_outcomes.jsonl"


def test_corrected_schematics_emit_png_pdf_and_searchable_svg(tmp_path: Path) -> None:
    anatomy = make_decision_card_anatomy_figure(
        INPUT_CARDS,
        SCORER_OUTCOMES,
        tmp_path,
    )
    pipeline = make_benchmark_pipeline_figure(
        INPUT_CARDS,
        SCORER_OUTCOMES,
        tmp_path,
    )

    for files, stem in [
        (anatomy, "figure_1_decision_card_anatomy"),
        (pipeline, "figure_2_benchmark_pipeline"),
    ]:
        assert files.png == tmp_path / f"{stem}.png"
        assert files.pdf == tmp_path / f"{stem}.pdf"
        assert files.svg == tmp_path / f"{stem}.svg"
        assert files.png.read_bytes().startswith(b"\x89PNG")
        assert files.pdf.read_bytes().startswith(b"%PDF")
        assert files.svg.stat().st_size > 5_000

    anatomy_svg = anatomy.svg.read_text(encoding="utf-8")
    assert "SYSTEM-VISIBLE INPUT CARD" in anatomy_svg
    assert "SCORER-ONLY OUTCOMES" in anatomy_svg
    assert "candidate activity is absent" in anatomy_svg

    pipeline_svg = pipeline.svg.read_text(encoding="utf-8")
    assert "91 SYSTEM-INPUT CARDS" in pipeline_svg
    assert "7 DETERMINISTIC SYSTEMS" in pipeline_svg
    assert "6 RAW LLM CONDITIONS" in pipeline_svg
    assert "546 provider requests" in pipeline_svg
    assert "6 ZERO-CALL REPAIRED VIEWS" in pipeline_svg
    assert "PAIRED 91-CARD ANALYSIS" in pipeline_svg


def test_schematic_rejects_candidate_activity_in_system_input(tmp_path: Path) -> None:
    cards = read_jsonl(INPUT_CARDS)
    cards[0]["candidate_pool"][0]["activity_value"] = 7.0
    leaked_cards = tmp_path / "leaked_cards.jsonl"
    write_jsonl(leaked_cards, cards)

    with pytest.raises(ValueError, match="leaks candidate activity"):
        make_decision_card_anatomy_figure(
            leaked_cards,
            SCORER_OUTCOMES,
            tmp_path / "figures",
        )
