from pathlib import Path

import pandas as pd
import pytest

from specguard_chem_v2.figure_review_series import (
    FIGURE_STEMS,
    build_figure_review_series,
)

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_DIR = ROOT / "release/v0.1.0/experiments/llm/comparison"


def test_build_corrected_figure_review_series(tmp_path: Path) -> None:
    outputs = build_figure_review_series(COMPARISON_DIR, tmp_path)

    expected = [
        tmp_path / f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in ("png", "pdf", "svg")
    ]
    assert outputs == expected
    assert all(path.exists() and path.stat().st_size > 0 for path in expected)
    assert not (tmp_path / "figure_6_raw_vs_final_compliance.png").exists()


def test_builder_rejects_non_corrected_comparison(tmp_path: Path) -> None:
    comparison_dir = tmp_path / "comparison"
    comparison_dir.mkdir()
    frame = pd.read_csv(COMPARISON_DIR / "system_comparison.csv").iloc[:-1]
    frame.to_csv(comparison_dir / "system_comparison.csv", index=False)
    pd.read_csv(COMPARISON_DIR / "failure_taxonomy_summary.csv").to_csv(
        comparison_dir / "failure_taxonomy_summary.csv",
        index=False,
    )

    with pytest.raises(ValueError, match="corrected 19-row comparison"):
        build_figure_review_series(comparison_dir, tmp_path / "figures")
