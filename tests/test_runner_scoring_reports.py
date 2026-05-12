from pathlib import Path

from specguard_chem_v2.io import load_models
from specguard_chem_v2.reports import (
    compare_run_summaries,
    make_frontier_plot,
    write_results_dashboard,
    write_results_summary,
)
from specguard_chem_v2.runner import run_system_file, run_system_on_card
from specguard_chem_v2.schemas import DecisionCard
from specguard_chem_v2.scoring import score_record, score_run
from specguard_chem_v2.systems.llm import (
    _cache_path,
    _extract_json_object,
    _request_hash,
    _selection_items_from_payload,
    build_llm_request,
    export_llm_requests,
)
from specguard_chem_v2.systems.providers import LLMModelConfig
from specguard_chem_v2.systems.providers import load_model_matrix, select_model_configs

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
    assert score.compliance_rate == 1.0
    assert score.raw_feasible_utility == 0.0
    assert score.repaired_rate == 1.0
    assert score.repaired_from_empty_rate == 1.0
    assert score.repair_delta_feasible_utility == score.feasible_utility


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
    assert bare["generation"]["max_tokens"] == 4096
    assert "tpsa" not in bare["candidate_pool"][0]
    assert "tpsa" in tools["candidate_pool"][0]
    rows = export_llm_requests([card], ["bare_llm", "llm_tools"])
    assert len(rows) == 2
    assert rows[0]["messages"][0]["role"] == "system"


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
        update={"id": "deepseek_frontier_selector", "thinking": False, "prompt_profile": "json_first"}
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


def test_live_payload_selection_normalization_clamps_confidence() -> None:
    selections = _selection_items_from_payload(
        {
            "selections": [
                {"rank": "1", "candidate_id": "C001", "confidence": 7.0},
                {"rank": "bad", "candidate_id": "C002", "confidence": "not-a-number"},
            ]
        }
    )
    assert selections[0].confidence == 1.0
    assert selections[1].rank == 2
    assert selections[1].confidence is None


def test_json_extraction_ignores_prefix_and_extra_json() -> None:
    payload = _extract_json_object(
        'prefix {"task_id": "T1", "selections": []} trailing {"ignored": true}'
    )
    assert payload == {"task_id": "T1", "selections": []}


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
    assert (tmp_path / "compare" / "metric_winners.csv").exists()
    assert (tmp_path / "compare" / "metric_winners_primary.csv").exists()
    assert (tmp_path / "compare" / "primary_leaderboard.csv").exists()
    assert (tmp_path / "compare" / "oracle_controls.csv").exists()
    assert (tmp_path / "compare" / "ablation_deltas.csv").exists()
    plot = make_frontier_plot(tmp_path / "compare" / "system_comparison.csv", tmp_path / "figures")
    assert plot.exists()
    summary = write_results_summary(
        tmp_path / "compare" / "system_comparison.csv",
        tmp_path / "paper",
    )
    assert summary.exists()
    assert "Primary Systems" in summary.read_text(encoding="utf-8")
    assert "raw_feasible_utility" in summary.read_text(encoding="utf-8")
    dashboard = write_results_dashboard(
        tmp_path / "compare" / "system_comparison.csv",
        tmp_path / "paper",
    )
    dashboard_text = dashboard.read_text(encoding="utf-8")
    assert dashboard.exists()
    assert "SpecGuard-Chem v2 Results Dashboard" in dashboard_text
    assert "Compliance-Utility Frontier" in dashboard_text
    assert "QSAR models" in dashboard_text
    assert "xScale" in dashboard_text
    assert "Plotly.react" in dashboard_text
    assert "data-tooltip" in dashboard_text
    assert "Original Hypotheses and Evidence" in dashboard_text
    assert "Compliance is not utility" in dashboard_text
    assert "wrapPlotLabel" in dashboard_text
    assert "wrapHoverText" in dashboard_text
    assert "wrapIdentifier" in dashboard_text
    assert "escapeHtml" in dashboard_text
    assert "repairPointView" in dashboard_text
    assert "Raw LLM points" in dashboard_text
    assert "Raw + final repair links" in dashboard_text
    assert "raw output" in dashboard_text
    assert "circle-open" in dashboard_text
    assert "Primary Systems" in dashboard_text
    assert "term" in dashboard_text


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
