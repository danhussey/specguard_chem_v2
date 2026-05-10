from pathlib import Path

from typer.testing import CliRunner

from specguard_chem_v2.cli import app


FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_fixture_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    cards = FIXTURES / "cards.jsonl"
    result = runner.invoke(app, ["validate-cards", str(cards)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["list-systems"])
    assert result.exit_code == 0, result.output
    assert "qsar_rf" in result.output

    result = runner.invoke(
        app,
        ["summarize-cards", str(cards), "--out", str(tmp_path / "card_summary.json")],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "card_summary.json").exists()

    suite_dir = tmp_path / "suite"
    result = runner.invoke(
        app,
        [
            "run-suite",
            str(cards),
            "--systems",
            "random_valid,rules_only",
            "--out",
            str(suite_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (suite_dir / "random_valid" / "trace.jsonl").exists()
    assert (suite_dir / "rules_only" / "scores" / "summary.json").exists()

    result = runner.invoke(
        app,
        [
            "export-llm-requests",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--out",
            str(tmp_path / "llm_requests.jsonl"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "llm_requests.jsonl").exists()

    result = runner.invoke(
        app,
        [
            "compare-runs",
            str(suite_dir / "random_valid" / "scores" / "summary.json"),
            str(suite_dir / "rules_only" / "scores" / "summary.json"),
            "--out",
            str(tmp_path / "compare"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "compare" / "system_comparison.csv").exists()

    result = runner.invoke(
        app,
        [
            "make-report",
            str(tmp_path / "compare" / "system_comparison.csv"),
            "--out",
            str(tmp_path / "paper"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "paper" / "RESULTS_SUMMARY.md").exists()
