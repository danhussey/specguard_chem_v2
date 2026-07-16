from pathlib import Path

import pytest
from typer.testing import CliRunner

from specguard_chem_v2.artifacts import sha256_file
from specguard_chem_v2.cli import app
from specguard_chem_v2.io import load_models, read_json
from specguard_chem_v2.posthoc import (
    POSTHOC_REPAIR_POLICY,
    apply_posthoc_repair,
)
from specguard_chem_v2.runner import run_system_file, run_system_on_card
from specguard_chem_v2.schemas import DecisionCard, RunRecord
from specguard_chem_v2.scoring import score_record

FIXTURES = Path(__file__).parent / "fixtures"


def test_posthoc_repair_preserves_raw_evidence_and_is_deterministic(tmp_path: Path) -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    source = run_system_on_card(card, "bare_llm", cache_dir=tmp_path / "empty-cache")
    source_payload = source.model_dump(mode="json")

    first = apply_posthoc_repair(card, source, source_trace_sha256="a" * 64)
    second = apply_posthoc_repair(card, source, source_trace_sha256="a" * 64)

    assert source.model_dump(mode="json") == source_payload
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.raw_output is not None
    assert first.raw_output.model_dump(mode="json") == source.raw_output.model_dump(mode="json")
    assert [issue.model_dump(mode="json") for issue in first.raw_issues] == [
        issue.model_dump(mode="json") for issue in source.raw_issues
    ]
    assert first.system_name == "bare_llm__posthoc_repair"
    assert first.output.system_name == first.system_name
    assert first.repaired is True
    assert not first.issues
    assert first.metadata["repair_mode"] == "posthoc"
    assert first.metadata["repair_policy"] == POSTHOC_REPAIR_POLICY
    assert first.metadata["repair_source_trace_sha256"] == "a" * 64
    assert first.metadata["provider_calls_added"] == 0
    assert first.output.metadata["provider_calls_added"] == 0

    score = score_record(card, first)
    assert score.action_validity == 1.0
    assert score.raw_action_validity == 0.0
    assert score.raw_feasible_utility == 0.0
    assert score.feasible_utility > score.raw_feasible_utility
    assert score.repaired_rate == 1.0


def test_posthoc_valid_response_is_a_noop_on_selections() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    source = run_system_on_card(card, "llm_tools", cache_dir=FIXTURES / "llm_cache")
    assert not source.raw_issues

    transformed = apply_posthoc_repair(card, source, source_trace_sha256="b" * 64)

    assert transformed.repaired is False
    assert transformed.output.selections == source.raw_output.selections
    assert transformed.raw_output == source.raw_output
    assert transformed.raw_issues == source.raw_issues
    assert transformed.metadata["repair_applied"] is False


def test_repair_llm_trace_cli_scores_both_views_without_changing_source(
    tmp_path: Path,
) -> None:
    cards = FIXTURES / "cards.jsonl"
    source_trace = tmp_path / "source" / "trace.jsonl"
    run_system_file(
        cards,
        "llm_tools",
        source_trace,
        cache_dir=tmp_path / "empty-cache",
        run_label="llm_tools__test_condition",
    )
    source_bytes = source_trace.read_bytes()
    source_hash = sha256_file(source_trace)
    repaired_trace = tmp_path / "repaired" / "trace.jsonl"
    repeated_trace = tmp_path / "repeated" / "trace.jsonl"
    scores_dir = tmp_path / "scores"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "repair-llm-trace",
            str(cards),
            str(source_trace),
            "--out",
            str(repaired_trace),
            "--scores-out",
            str(scores_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "post-hoc repaired view" in result.output
    assert source_trace.read_bytes() == source_bytes

    repeated = runner.invoke(
        app,
        [
            "repair-llm-trace",
            str(cards),
            str(source_trace),
            "--out",
            str(repeated_trace),
        ],
    )
    assert repeated.exit_code == 0, repeated.output
    assert repaired_trace.read_bytes() == repeated_trace.read_bytes()

    records = load_models(repaired_trace, RunRecord)
    assert all(record.raw_output is not None for record in records)
    assert all(record.metadata["repair_source_trace_sha256"] == source_hash for record in records)
    assert all(record.metadata["provider_calls_added"] == 0 for record in records)
    summary = read_json(scores_dir / "summary.json")
    assert summary["repair_mode"] == "posthoc"
    assert summary["repair_policy"] == POSTHOC_REPAIR_POLICY
    assert summary["repair_source_trace_sha256"] == source_hash
    assert summary["action_validity"] == 1.0
    assert summary["raw_action_validity"] == 0.0
    assert summary["raw_action_validity_ci_low"] == 0.0
    assert summary["raw_action_validity_ci_high"] == 0.0
    assert summary["raw_feasible_utility"] == 0.0
    assert summary["feasible_utility"] > summary["raw_feasible_utility"]


def test_posthoc_repair_rejects_changed_raw_issues_and_repaired_sources(
    tmp_path: Path,
) -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    source = run_system_on_card(card, "bare_llm", cache_dir=tmp_path / "empty-cache")
    changed = source.model_copy(update={"raw_issues": []}, deep=True)

    with pytest.raises(ValueError, match="raw issues do not match"):
        apply_posthoc_repair(card, changed, source_trace_sha256="c" * 64)

    transformed = apply_posthoc_repair(card, source, source_trace_sha256="c" * 64)
    with pytest.raises(ValueError, match="already been repaired"):
        apply_posthoc_repair(card, transformed, source_trace_sha256="c" * 64)
