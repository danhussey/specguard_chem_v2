import json
from pathlib import Path

import pandas as pd

from specguard_chem_v2.io import load_models
from specguard_chem_v2.reports import (
    CONDITION_METADATA,
    _system_display_label_from_row,
    compare_run_summaries,
    make_frontier_plot,
    write_results_dashboard,
    write_results_summary,
)
from specguard_chem_v2.runner import run_system_file, run_system_on_card, validate_output
from specguard_chem_v2.schemas import DecisionCard, RunRecord
from specguard_chem_v2.scoring import score_record, score_run, summarize_scores
from specguard_chem_v2.systems.llm import (
    _cache_path,
    _parse_llm_response,
    _request_hash,
    _selection_items_from_payload,
    build_llm_request,
    export_llm_requests,
)
from specguard_chem_v2.systems.providers import (
    LLMModelConfig,
    load_model_matrix,
    select_model_configs,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_baseline_runner_and_scoring(tmp_path: Path) -> None:
    cards_path = FIXTURES / "cards.jsonl"
    trace_path = tmp_path / "runs" / "rules_only" / "trace.jsonl"
    records = run_system_file(cards_path, "rules_only", trace_path, workers=2)
    assert len(records) == 2
    assert all(not record.issues for record in records)

    scores = score_run(cards_path, trace_path, tmp_path / "scores")
    assert len(scores) == 2
    assert (tmp_path / "scores" / "summary.json").exists()
    assert (tmp_path / "scores" / "metric_denominators.json").exists()
    assert (tmp_path / "scores" / "failure_taxonomy.csv").exists()
    assert all(score.compliance_rate == 1.0 for score in scores)
    assert all(score.oracle_utility >= score.feasible_utility for score in scores)


def test_qsar_and_llm_validator_paths(tmp_path: Path) -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    for system_name in ["qsar_rf", "qsar_gbt", "qsar_svm", "oracle_valid_topk"]:
        qsar_record = run_system_on_card(card, system_name)
        assert qsar_record.output.system_name == system_name
        assert len(qsar_record.output.selections) == card.budget_k

    llm_record = run_system_on_card(card, "llm_tools_validator", cache_dir=tmp_path / "cache")
    assert llm_record.repaired is True
    assert llm_record.raw_output is not None
    assert llm_record.raw_output.selections == []
    assert llm_record.raw_issues
    assert llm_record.metadata["repaired_from_empty"] is True
    assert not llm_record.issues
    score = score_record(card, llm_record)
    assert score.action_validity == 1.0
    assert score.compliance_rate == 1.0
    assert score.raw_action_validity == 0.0
    assert score.raw_feasible_utility == 0.0
    assert score.repaired_rate == 1.0
    assert score.repaired_from_empty_rate == 1.0
    assert score.repair_delta_feasible_utility == score.feasible_utility


def test_whole_action_validity_is_distinct_from_valid_selection_fraction() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    valid_record = run_system_on_card(card, "rules_only")
    mismatched_output = valid_record.output.model_copy(update={"task_id": "wrong-task"})
    record = RunRecord(
        task_id=card.task_id,
        system_name="wrong_task_id",
        output=mismatched_output,
        issues=validate_output(card, mismatched_output),
    )

    score = score_record(card, record)

    assert len(mismatched_output.selections) == card.budget_k
    assert score.valid_selected_count == card.budget_k
    assert score.compliance_rate == 1.0
    assert score.action_validity == 0.0
    summary = summarize_scores([score], bootstrap_samples=10)
    assert summary["action_validity"] == 0.0
    assert summary["action_validity_ci_low"] == 0.0
    assert summary["action_validity_ci_high"] == 0.0


def test_cached_llm_replay_variants() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    for system_name in ["bare_llm", "llm_validator", "llm_tools", "llm_tools_validator"]:
        record = run_system_on_card(card, system_name, cache_dir=FIXTURES / "llm_cache")
        assert record.output.system_name == system_name
        assert len(record.output.selections) == card.budget_k
    validator_record = run_system_on_card(card, "llm_validator", cache_dir=FIXTURES / "llm_cache")
    assert validator_record.repaired is True
    assert not validator_record.issues


def test_llm_request_export_distinguishes_tool_condition() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    bare = build_llm_request(card, "bare_llm")
    tools = build_llm_request(card, "llm_tools")
    assert bare["condition"]["uses_tools"] is False
    assert tools["condition"]["uses_tools"] is True
    assert bare["activity_semantics"] == {
        "support_activity_field": "activity_value",
        "scale": "pIC50",
        "higher_is_better": True,
        "objective": "rank candidates to maximize predicted pIC50",
    }
    assert bare["support_set"][0]["activity_type"] == "pIC50"
    assert bare["generation"]["max_tokens"] == 4096
    assert "tpsa" not in bare["candidate_pool"][0]
    assert "tpsa" in tools["candidate_pool"][0]
    rows = export_llm_requests([card], ["bare_llm", "llm_tools"])
    assert len(rows) == 2
    assert rows[0]["messages"][0]["role"] == "system"
    assert "higher values are better" in rows[0]["messages"][0]["content"]


def test_model_matrix_requests_and_offline_run(tmp_path: Path) -> None:
    cards_path = FIXTURES / "cards.jsonl"
    cards = load_models(cards_path, DecisionCard)
    configs = select_model_configs(
        load_model_matrix(Path("configs/model_matrix.toml")),
        "openai_fast,deepseek_fast",
    )
    rows = export_llm_requests(cards[:1], ["llm_tools"], model_configs=configs)
    assert len(rows) == 2
    assert {row["model_config_id"] for row in rows} == {"openai_fast", "deepseek_fast"}
    assert all("activity_value" not in row["request"]["candidate_pool"][0] for row in rows)

    records = run_system_file(
        cards_path,
        "llm_tools_validator",
        tmp_path / "trace.jsonl",
        cache_dir=tmp_path / "cache",
        model_config=configs[0],
        run_label="llm_tools_validator__openai_fast",
    )
    assert records[0].system_name == "llm_tools_validator__openai_fast"
    assert records[0].metadata["llm_model_config_id"] == "openai_fast"
    assert records[0].metadata["max_tokens"] == 4096
    assert records[0].metadata["prompt_profile"] == "default"
    assert records[0].raw_output is not None
    assert records[0].repaired is True
    summary_scores = score_run(cards_path, tmp_path / "trace.jsonl", tmp_path / "scores")
    assert summary_scores[0].system_name == "llm_tools_validator__openai_fast"
    assert summary_scores[0].raw_feasible_utility is not None


def test_llm_request_cache_identity_includes_generation_settings(tmp_path: Path) -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    short_config = LLMModelConfig(
        id="deepseek_frontier",
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        reasoning_effort="high",
        thinking=True,
        max_tokens=4096,
    )
    long_config = short_config.model_copy(update={"max_tokens": 32768})
    selector_config = short_config.model_copy(
        update={
            "id": "deepseek_frontier_selector",
            "thinking": False,
            "prompt_profile": "json_first",
        }
    )

    short_request = build_llm_request(card, "bare_llm", model_config=short_config)
    long_request = build_llm_request(card, "bare_llm", model_config=long_config)
    selector_request = build_llm_request(card, "bare_llm", model_config=selector_config)

    assert short_request["generation"]["max_tokens"] == 4096
    assert long_request["generation"]["max_tokens"] == 32768
    assert selector_request["generation"]["prompt_profile"] == "json_first"
    assert _request_hash(short_request) != _request_hash(long_request)
    assert _request_hash(short_request) != _request_hash(selector_request)
    assert _cache_path(tmp_path, short_request) != _cache_path(tmp_path, long_request)
    assert _cache_path(tmp_path, short_request) != _cache_path(tmp_path, selector_request)


def test_thinking_budget_changes_cache_identity_and_validates() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    base_config = LLMModelConfig(
        id="anthropic_frontier_selector",
        provider="anthropic",
        model="claude-opus-4-7",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        prompt_profile="json_first",
    )
    thinking_config = base_config.model_copy(
        update={
            "id": "anthropic_frontier_thinking_8k",
            "thinking_budget_tokens": 8192,
            "max_tokens": 16384,
        }
    )
    base_request = build_llm_request(card, "llm_tools", model_config=base_config)
    thinking_request = build_llm_request(card, "llm_tools", model_config=thinking_config)

    assert thinking_request["generation"]["thinking_budget_tokens"] == 8192
    assert _request_hash(base_request) != _request_hash(thinking_request)

    try:
        LLMModelConfig(
            id="bad_anthropic",
            provider="anthropic",
            model="claude-opus-4-7",
            thinking_budget_tokens=4096,
            max_tokens=4096,
        )
    except ValueError as exc:
        assert "thinking_budget_tokens must be less than max_tokens" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected invalid Anthropic thinking budget")

    try:
        LLMModelConfig(
            id="bad_openai",
            provider="openai",
            model="gpt-5.5",
            thinking_budget_tokens=1024,
            max_tokens=4096,
        )
    except ValueError as exc:
        assert "supported only for Anthropic" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected provider-specific thinking budget validation")


def test_live_payload_selection_normalization_records_invalid_types() -> None:
    payload = _parse_llm_response(
        {"task_id": "T1", "system_name": "bare_llm"},
        json.dumps(
            {
                "task_id": "T1",
                "system_name": "bare_llm",
                "selections": [
                    {"rank": "1", "candidate_id": "C001", "confidence": 7.0},
                    {"rank": "bad", "candidate_id": "C002", "confidence": "not-a-number"},
                ],
            }
        ),
    )
    selections = _selection_items_from_payload(payload)
    assert selections[0].confidence is None
    assert selections[1].rank == 2
    assert selections[1].confidence is None
    issue_codes = {issue["code"] for issue in payload["metadata"]["response_contract_issues"]}
    assert {"schema_selection_rank_type", "schema_selection_confidence_range"} <= issue_codes
    assert "schema_selection_confidence_type" in issue_codes


def test_json_extraction_salvages_prefix_and_extra_json_as_raw_issues() -> None:
    payload = _parse_llm_response(
        {"task_id": "T1", "system_name": "bare_llm"},
        'prefix {"task_id": "T1", "system_name": "bare_llm", "selections": []} '
        'trailing {"ignored": true}',
    )
    assert payload["task_id"] == "T1"
    assert payload["selections"] == []
    issue_codes = {issue["code"] for issue in payload["metadata"]["response_contract_issues"]}
    assert {"schema_response_envelope", "schema_multiple_json_objects"} <= issue_codes


def test_compare_and_frontier_plot(tmp_path: Path) -> None:
    cards_path = FIXTURES / "cards.jsonl"
    summary_paths = []
    for system_name in ["random_valid", "rules_only"]:
        trace_path = tmp_path / system_name / "trace.jsonl"
        run_system_file(cards_path, system_name, trace_path)
        score_run(cards_path, trace_path, tmp_path / system_name / "scores")
        summary_paths.append(tmp_path / system_name / "scores" / "summary.json")

    frame = compare_run_summaries(summary_paths, tmp_path / "compare")
    assert set(frame["system_name"]) == {"random_valid", "rules_only"}
    assert "raw_feasible_utility" in frame.columns
    assert "action_validity" in frame.columns
    assert "action_validity_ci_low" in frame.columns
    assert "action_validity_ci_high" in frame.columns
    assert (tmp_path / "compare" / "metric_winners.csv").exists()
    assert (tmp_path / "compare" / "metric_winners_primary.csv").exists()
    assert (tmp_path / "compare" / "primary_leaderboard.csv").exists()
    assert (tmp_path / "compare" / "oracle_controls.csv").exists()
    assert (tmp_path / "compare" / "ablation_deltas.csv").exists()
    assert (tmp_path / "compare" / "paired_bootstrap_deltas.csv").exists()
    assert (tmp_path / "compare" / "paired_bootstrap_key_deltas.csv").exists()
    assert (tmp_path / "compare" / "card_level_key_systems.csv").exists()
    assert (tmp_path / "compare" / "card_level_diagnostics.csv").exists()
    assert (tmp_path / "compare" / "failure_taxonomy_summary.csv").exists()
    assert (tmp_path / "compare" / "failure_taxonomy_by_group.csv").exists()
    plot = make_frontier_plot(tmp_path / "compare" / "system_comparison.csv", tmp_path / "figures")
    assert plot.exists()
    assert plot.with_suffix(".pdf").exists()
    assert (tmp_path / "figures" / "primary_utility_leaderboard.png").exists()
    assert (tmp_path / "figures" / "card_level_utility_distribution.png").exists()
    summary = write_results_summary(
        tmp_path / "compare" / "system_comparison.csv",
        tmp_path / "paper",
        generated_at="2026-07-16T00:00:00+00:00",
        source_path="release/tables/system_comparison.csv",
    )
    summary_text = summary.read_text(encoding="utf-8")
    assert summary.exists()
    assert "Primary Systems" in summary_text
    assert "raw_feasible_utility" in summary_text
    assert "Failure Taxonomy Summary" in summary_text
    assert "Card-Level Diagnostics" in summary_text
    assert "2026-07-16T00:00:00+00:00" in summary_text
    assert "release/tables/system_comparison.csv" in summary_text
    assert str(tmp_path) not in summary_text
    assert "paper-50" not in summary_text
    dashboard = write_results_dashboard(
        tmp_path / "compare" / "system_comparison.csv",
        tmp_path / "paper",
        generated_at="2026-07-16T00:00:00+00:00",
        source_path="release/tables/system_comparison.csv",
    )
    dashboard_text = dashboard.read_text(encoding="utf-8")
    assert dashboard.exists()
    assert "SpecGuard-Chem Action-Quality Results Dashboard" in dashboard_text
    assert "Action-Quality Profile" in dashboard_text
    assert "Final whole-action validity" in dashboard_text
    assert "Final valid-selection fraction" in dashboard_text
    assert "QSAR models" in dashboard_text
    assert "xScale" in dashboard_text
    assert "Plotly.react" in dashboard_text
    assert "data-tooltip" in dashboard_text
    assert "Research Questions and Observed Evidence" in dashboard_text
    assert "Action utility is the primary scientific outcome" in dashboard_text
    assert "wrapPlotLabel" in dashboard_text
    assert "wrapHoverText" in dashboard_text
    assert "wrapIdentifier" in dashboard_text
    assert "escapeHtml" in dashboard_text
    assert "richTooltip" in dashboard_text
    assert "data-example" in dashboard_text
    assert "metricExamples" in dashboard_text
    assert "selectedMetricDefinitions" in dashboard_text
    assert "fallback_ranking(card)" in dashboard_text
    assert "repairPointView" in dashboard_text
    assert "Raw LLM points" in dashboard_text
    assert "Raw + final repair links" in dashboard_text
    assert "raw output" in dashboard_text
    assert "circle-open" in dashboard_text
    assert "Paired Card-Level Bootstrap" in dashboard_text
    assert "Card-Level Utility Distribution" in dashboard_text
    assert "Percent of oracle utility" in dashboard_text
    assert "dividing by budget k gives the mean selected activity" in dashboard_text
    assert "Raw output:" in dashboard_text
    assert "Failure Taxonomy" in dashboard_text
    assert "pairedRows" in dashboard_text
    assert "cardKeyRows" in dashboard_text
    assert "failureRows" in dashboard_text
    assert "Primary Systems" in dashboard_text
    assert "term" in dashboard_text
    assert "2026-07-16T00:00:00+00:00" in dashboard_text
    assert "release/tables/system_comparison.csv" in dashboard_text
    assert str(tmp_path) not in dashboard_text
    assert "paper-50" not in dashboard_text


def test_report_summary_figures_cover_repair_and_paired_effects(tmp_path: Path) -> None:
    comparison_dir = tmp_path / "compare"
    comparison_dir.mkdir()
    condition = "openai_gpt_5_5_2026_04_23_selector"
    bare = f"bare_llm__{condition}"
    tools = f"llm_tools__{condition}"
    repair_suffix = "__posthoc_repair"
    pd.DataFrame(
        [
            {
                "system_name": bare,
                "feasible_utility": 60.0,
                "feasible_utility_ci_low": 58.0,
                "feasible_utility_ci_high": 62.0,
                "action_validity": 0.5,
                "raw_action_validity": 0.5,
                "repaired_rate": 0.0,
            },
            {
                "system_name": tools,
                "feasible_utility": 62.0,
                "feasible_utility_ci_low": 60.0,
                "feasible_utility_ci_high": 64.0,
                "action_validity": 0.6,
                "raw_action_validity": 0.6,
                "repaired_rate": 0.0,
            },
            {
                "system_name": f"{bare}{repair_suffix}",
                "feasible_utility": 70.0,
                "feasible_utility_ci_low": 68.0,
                "feasible_utility_ci_high": 72.0,
                "action_validity": 1.0,
                "raw_action_validity": 0.5,
                "repaired_rate": 0.5,
            },
            {
                "system_name": f"{tools}{repair_suffix}",
                "feasible_utility": 72.0,
                "feasible_utility_ci_low": 70.0,
                "feasible_utility_ci_high": 74.0,
                "action_validity": 1.0,
                "raw_action_validity": 0.6,
                "repaired_rate": 0.4,
            },
        ]
    ).to_csv(comparison_dir / "system_comparison.csv", index=False)

    paired_columns = [
        "comparison",
        "metric",
        "system_a",
        "system_b",
        "mean_delta",
        "ci_low",
        "ci_high",
    ]
    pd.DataFrame(
        [
            ["all_primary_pairs", "feasible_utility", tools, bare, 2.0, 0.5, 3.5],
            [
                "all_primary_pairs",
                "feasible_utility",
                f"{tools}{repair_suffix}",
                f"{bare}{repair_suffix}",
                2.0,
                0.4,
                3.6,
            ],
        ],
        columns=paired_columns,
    ).to_csv(comparison_dir / "paired_bootstrap_deltas.csv", index=False)
    headline_systems = {
        "best_qsar_minus_best_final_llm": ("qsar_svm", f"{tools}{repair_suffix}"),
        "best_final_llm_minus_similarity": (
            f"{tools}{repair_suffix}",
            "similarity_to_best_active",
        ),
        "best_qsar_minus_similarity": ("qsar_svm", "similarity_to_best_active"),
        "oracle_minus_best_qsar": ("oracle_valid_topk", "qsar_svm"),
    }
    pd.DataFrame(
        [
            [comparison, "feasible_utility", systems[0], systems[1], 1.0, 0.2, 1.8]
            for comparison, systems in headline_systems.items()
        ],
        columns=paired_columns,
    ).to_csv(comparison_dir / "paired_bootstrap_key_deltas.csv", index=False)

    card_rows = []
    diagnostic_rows = []
    card_values = [
        (80.0, 75.0, 74.0, 73.0, 72.0, 68.0),
        (78.0, 74.0, 75.0, 72.0, 71.0, 67.0),
        (82.0, 77.0, 76.0, 74.0, 73.0, 69.0),
    ]
    series = [
        "Oracle upper-bound",
        "Best QSAR",
        "Best final LLM",
        "Best raw LLM",
        "Similarity baseline",
        "Rules-only baseline",
    ]
    for index, values in enumerate(card_values, start=1):
        task_id = f"T{index}"
        oracle, qsar, final_llm, raw_llm, similarity, rules = values
        for series_name, utility in zip(series, values, strict=True):
            card_rows.append(
                {
                    "task_id": task_id,
                    "series": series_name,
                    "feasible_utility": utility,
                    "oracle_utility": oracle,
                }
            )
        diagnostic_rows.append(
            {
                "task_id": task_id,
                "best_qsar_utility": qsar,
                "best_final_llm_utility": final_llm,
                "oracle_minus_best_qsar": oracle - qsar,
                "best_qsar_minus_best_final_llm": qsar - final_llm,
                "best_qsar_minus_best_raw_llm": qsar - raw_llm,
                "best_final_llm_minus_similarity": final_llm - similarity,
                "best_qsar_minus_similarity": qsar - similarity,
                "rules_utility": rules,
            }
        )
    pd.DataFrame(card_rows).to_csv(comparison_dir / "card_level_key_systems.csv", index=False)
    pd.DataFrame(diagnostic_rows).to_csv(
        comparison_dir / "card_level_diagnostics.csv",
        index=False,
    )

    make_frontier_plot(comparison_dir / "system_comparison.csv", tmp_path / "figures")
    for filename in [
        "primary_utility_leaderboard",
        "llm_repair_effect",
        "descriptor_ablation",
        "paired_utility_effects",
        "card_level_utility_distribution",
        "card_level_delta_distribution",
        "card_level_qsar_vs_llm_scatter",
    ]:
        assert (tmp_path / "figures" / f"{filename}.png").exists()
        assert (tmp_path / "figures" / f"{filename}.pdf").exists()


def test_report_condition_metadata_uses_release_ids_and_keeps_historical_labels() -> None:
    expected_models = {
        "openai_gpt_5_5_2026_04_23_selector": "gpt-5.5-2026-04-23",
        "anthropic_opus_4_8_selector": "claude-opus-4-8",
        "deepseek_v4_pro_2026_07_16_selector": "deepseek-v4-pro",
    }
    for condition_id, model in expected_models.items():
        assert CONDITION_METADATA[condition_id]["model"] == model
        assert "Release-candidate" in CONDITION_METADATA[condition_id]["description"]

    assert "Historical condition" in CONDITION_METADATA["openai_frontier_selector"]["description"]

    repaired_label = _system_display_label_from_row(
        {
            "system_name": ("bare_llm__openai_gpt_5_5_2026_04_23_selector__posthoc_repair"),
            "llm_provider": "openai",
            "llm_model": "gpt-5.5-2026-04-23",
        }
    )
    assert repaired_label == (
        "Bare LLM + post-hoc repair - OpenAI gpt-5.5-2026-04-23, low reasoning, direct JSON"
    )


def test_compare_variant_ablation_rows(tmp_path: Path) -> None:
    cards_path = FIXTURES / "cards.jsonl"
    summary_paths = []
    config = load_model_matrix(Path("configs/model_matrix.toml"))["openai_fast"]
    for system_name in ["bare_llm", "llm_validator"]:
        run_label = f"{system_name}__openai_fast"
        trace_path = tmp_path / system_name / "trace.jsonl"
        run_system_file(
            cards_path,
            system_name,
            trace_path,
            cache_dir=FIXTURES / "llm_cache",
            model_config=config,
            run_label=run_label,
        )
        score_run(cards_path, trace_path, tmp_path / system_name / "scores")
        summary_paths.append(tmp_path / system_name / "scores" / "summary.json")

    compare_run_summaries(summary_paths, tmp_path / "compare")
    ablations = (tmp_path / "compare" / "ablation_deltas.csv").read_text(encoding="utf-8")
    assert "validator_delta__openai_fast" in ablations
