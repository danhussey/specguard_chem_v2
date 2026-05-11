from pathlib import Path

from specguard_chem_v2.io import load_models
from specguard_chem_v2.reports import (
    compare_run_summaries,
    make_frontier_plot,
    write_results_summary,
)
from specguard_chem_v2.runner import run_system_file, run_system_on_card
from specguard_chem_v2.schemas import DecisionCard
from specguard_chem_v2.scoring import score_record, score_run
from specguard_chem_v2.systems.llm import (
    _cache_path,
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
    records = run_system_file(cards_path, "rules_only", trace_path)
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
    assert not llm_record.issues
    score = score_record(card, llm_record)
    assert score.compliance_rate == 1.0


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
    assert records[0].repaired is True
    summary_scores = score_run(cards_path, tmp_path / "trace.jsonl", tmp_path / "scores")
    assert summary_scores[0].system_name == "llm_tools_validator__openai_fast"


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

    short_request = build_llm_request(card, "bare_llm", model_config=short_config)
    long_request = build_llm_request(card, "bare_llm", model_config=long_config)

    assert short_request["generation"]["max_tokens"] == 4096
    assert long_request["generation"]["max_tokens"] == 32768
    assert _request_hash(short_request) != _request_hash(long_request)
    assert _cache_path(tmp_path, short_request) != _cache_path(tmp_path, long_request)


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
