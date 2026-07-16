import json
from pathlib import Path

from typer.testing import CliRunner

from specguard_chem_v2.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
PILOT_TASK_ID = "CARA_LO_CHEMBL1006579_IC50_0001"
RELEASE_MODEL_CONDITIONS = (
    "openai_gpt_5_5_2026_04_23_selector,"
    "anthropic_opus_4_8_selector,"
    "deepseek_v4_pro_2026_07_16_selector"
)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


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
            "--manifest-started-at",
            "2026-07-16T00:00:00+00:00",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (suite_dir / "random_valid" / "trace.jsonl").exists()
    assert (suite_dir / "rules_only" / "scores" / "summary.json").exists()
    manifest = json.loads((suite_dir / "manifest.json").read_text())
    assert manifest["started_at"] == "2026-07-16T00:00:00+00:00"
    assert "cards_sha256" in manifest
    assert "model" not in manifest

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

    result = runner.invoke(app, ["list-model-matrix", "configs/model_matrix.toml"])
    assert result.exit_code == 0, result.output
    assert "openai_fast" in result.output
    assert "openai_frontier_selector" in result.output

    result = runner.invoke(
        app,
        [
            "estimate-llm-cost",
            str(cards),
            "--systems",
            "llm_tools_validator",
            "--model-conditions",
            "openai_fast,deepseek_fast",
            "--out-run-dir",
            str(tmp_path / "cost_matrix"),
            "--out",
            str(tmp_path / "cost_estimate.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cost_estimate.json").exists()
    assert '"missing_live_calls": 4' in result.output

    result = runner.invoke(
        app,
        [
            "run-llm-matrix",
            str(cards),
            "--systems",
            "llm_tools_validator",
            "--model-conditions",
            "openai_fast",
            "--out",
            str(tmp_path / "gated_matrix"),
            "--allow-external",
            "--max-live-calls",
            "0",
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Cost gate failed" in result.output
    assert (tmp_path / "gated_matrix" / "cost_estimate.json").exists()

    matrix_dir = tmp_path / "llm_matrix"
    result = runner.invoke(
        app,
        [
            "run-llm-matrix",
            str(cards),
            "--systems",
            "llm_tools_validator",
            "--model-conditions",
            "openai_fast,deepseek_fast",
            "--out",
            str(matrix_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (matrix_dir / "openai_fast" / "llm_tools_validator" / "trace.jsonl").exists()
    assert (
        matrix_dir / "deepseek_fast" / "llm_tools_validator" / "scores" / "summary.json"
    ).exists()

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

    result = runner.invoke(
        app,
        [
            "make-dashboard",
            str(tmp_path / "compare" / "system_comparison.csv"),
            "--out",
            str(tmp_path / "paper"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "paper" / "RESULTS_DASHBOARD.html").exists()


def test_llm_matrix_task_id_selector_is_consistent_and_offline(tmp_path: Path) -> None:
    runner = CliRunner()
    cards = FIXTURES / "cards.jsonl"
    selected_task = "fixture_A1"
    model_conditions = "openai_fast,deepseek_fast"

    default_requests = tmp_path / "default_requests.jsonl"
    result = runner.invoke(
        app,
        ["export-llm-requests", str(cards), "--out", str(default_requests)],
    )
    assert result.exit_code == 0, result.output
    default_rows = _read_jsonl(default_requests)
    assert len(default_rows) == 4
    assert {row["system_name"] for row in default_rows} == {"bare_llm", "llm_tools"}

    requests_path = tmp_path / "selected_requests.jsonl"
    result = runner.invoke(
        app,
        [
            "export-llm-requests",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--model-matrix",
            "configs/model_matrix.toml",
            "--model-conditions",
            model_conditions,
            "--task-id",
            selected_task,
            "--out",
            str(requests_path),
        ],
    )
    assert result.exit_code == 0, result.output
    request_rows = _read_jsonl(requests_path)
    assert len(request_rows) == 4
    assert {row["task_id"] for row in request_rows} == {selected_task}

    estimate_path = tmp_path / "selected_estimate.json"
    result = runner.invoke(
        app,
        [
            "estimate-llm-cost",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--model-conditions",
            model_conditions,
            "--task-id",
            selected_task,
            "--out-run-dir",
            str(tmp_path / "selected_matrix"),
            "--out",
            str(estimate_path),
        ],
    )
    assert result.exit_code == 0, result.output
    estimate = json.loads(estimate_path.read_text())
    assert estimate["total_requests"] == 4
    assert estimate["missing_live_calls"] == 4
    assert {row["task_id"] for row in estimate["rows"]} == {selected_task}

    matrix_dir = tmp_path / "offline_matrix"
    result = runner.invoke(
        app,
        [
            "run-llm-matrix",
            str(cards),
            "--systems",
            "llm_tools",
            "--model-conditions",
            "openai_fast",
            "--task-id",
            selected_task,
            "--out",
            str(matrix_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    trace = _read_jsonl(matrix_dir / "openai_fast" / "llm_tools" / "trace.jsonl")
    assert len(trace) == 1
    assert trace[0]["task_id"] == selected_task
    manifest = json.loads((matrix_dir / "manifest.json").read_text())
    assert manifest["task_id"] == selected_task
    assert manifest["cache_dir"] == str(matrix_dir / "cache")

    result = runner.invoke(
        app,
        [
            "run-llm-matrix",
            str(cards),
            "--systems",
            "llm_tools",
            "--model-conditions",
            "openai_fast",
            "--task-id",
            "fixture_A2",
            "--out",
            str(matrix_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    replacement_trace = _read_jsonl(matrix_dir / "openai_fast" / "llm_tools" / "trace.jsonl")
    assert [row["task_id"] for row in replacement_trace] == ["fixture_A2"]

    missing_path = tmp_path / "missing.jsonl"
    result = runner.invoke(
        app,
        [
            "export-llm-requests",
            str(cards),
            "--task-id",
            "not-a-task",
            "--out",
            str(missing_path),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "not-a-task" in result.output
    assert "decision cards" in result.output
    assert not missing_path.exists()

    result = runner.invoke(
        app,
        [
            "export-llm-requests",
            str(cards),
            "--model-conditions",
            "openai_fast",
            "--out",
            str(tmp_path / "ambiguous_model_requests.jsonl"),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "requires" in result.output
    assert "--model-matrix" in result.output


def test_release_pilot_no_call_commands_match_canonical_rows(tmp_path: Path) -> None:
    runner = CliRunner()
    cards = Path("data/releases/v0.1.0/system_input_cards.jsonl")
    canonical_requests = _read_jsonl(Path("release/v0.1.0/experiments/llm/exact_requests.jsonl"))
    assert len(canonical_requests) == 546
    expected_requests = [row for row in canonical_requests if row["task_id"] == PILOT_TASK_ID]
    assert len(expected_requests) == 6

    pilot_requests = tmp_path / "pilot_requests.jsonl"
    result = runner.invoke(
        app,
        [
            "export-llm-requests",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--model-matrix",
            "configs/model_matrix.toml",
            "--model-conditions",
            RELEASE_MODEL_CONDITIONS,
            "--task-id",
            PILOT_TASK_ID,
            "--out",
            str(pilot_requests),
        ],
    )
    assert result.exit_code == 0, result.output
    assert _read_jsonl(pilot_requests) == expected_requests

    canonical_estimate = json.loads(
        Path("release/v0.1.0/experiments/llm/pre_run_cost_estimate.json").read_text()
    )
    expected_cost_rows = [
        row for row in canonical_estimate["rows"] if row["task_id"] == PILOT_TASK_ID
    ]
    assert len(expected_cost_rows) == 6

    pilot_estimate = tmp_path / "pilot_estimate.json"
    result = runner.invoke(
        app,
        [
            "estimate-llm-cost",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--model-matrix",
            "configs/model_matrix.toml",
            "--model-conditions",
            RELEASE_MODEL_CONDITIONS,
            "--pricing",
            "configs/provider_pricing.toml",
            "--task-id",
            PILOT_TASK_ID,
            "--out-run-dir",
            "release/v0.1.0/experiments/llm/matrix",
            "--out",
            str(pilot_estimate),
        ],
    )
    assert result.exit_code == 0, result.output
    estimated = json.loads(pilot_estimate.read_text())
    assert estimated["total_requests"] == 6
    assert estimated["missing_live_calls"] == 6
    assert estimated["rows"] == expected_cost_rows

    shared_cache = tmp_path / "shared_matrix_cache"
    for row in expected_requests:
        cache_file = (
            shared_cache
            / row["model_config_id"]
            / row["system_name"]
            / f"{row['system_name']}__{row['request_sha256']}.json"
        )
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"response": {"metadata": {}}}))

    residual_estimate = tmp_path / "residual_estimate.json"
    result = runner.invoke(
        app,
        [
            "estimate-llm-cost",
            str(cards),
            "--systems",
            "bare_llm,llm_tools",
            "--model-matrix",
            "configs/model_matrix.toml",
            "--model-conditions",
            RELEASE_MODEL_CONDITIONS,
            "--pricing",
            "configs/provider_pricing.toml",
            "--cache-dir",
            str(shared_cache),
            "--out-run-dir",
            str(tmp_path / "full_matrix"),
            "--out",
            str(residual_estimate),
        ],
    )
    assert result.exit_code == 0, result.output
    residual = json.loads(residual_estimate.read_text())
    assert residual["total_requests"] == 546
    assert residual["cached_or_completed_calls"] == 6
    assert residual["missing_live_calls"] == 540
    assert abs(residual["estimated_incremental_cost_usd"] - 105.122676615) < 1e-9
