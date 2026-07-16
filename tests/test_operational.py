from __future__ import annotations

import json
from pathlib import Path

import pytest

from specguard_chem_v2.costing import PricingConfig, PricingEntry
from specguard_chem_v2.io import load_models, write_json, write_jsonl
from specguard_chem_v2.operational import (
    normalize_provider_usage,
    operational_row,
    summarize_operational_rows,
    usage_cost_usd,
)
from specguard_chem_v2.runner import run_system_on_card
from specguard_chem_v2.schemas import DecisionCard, RunRecord
from specguard_chem_v2.scoring import score_run

FIXTURES = Path(__file__).parent / "fixtures"


def _pricing() -> PricingConfig:
    return PricingConfig.model_validate(
        {
            "models": {
                "test_model": {
                    "input_per_1m_usd": 2.0,
                    "cached_input_per_1m_usd": 0.5,
                    "output_per_1m_usd": 4.0,
                    "source_url": "https://pricing.invalid/test-model",
                }
            }
        }
    )


def _record(
    task_id: str,
    *,
    metadata: dict[str, object],
    system_name: str = "bare_llm__test_model",
) -> RunRecord:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    baseline = run_system_on_card(card, "rules_only")
    output = baseline.output.model_copy(
        update={"task_id": task_id, "system_name": system_name, "metadata": metadata},
        deep=True,
    )
    return baseline.model_copy(
        update={
            "task_id": task_id,
            "system_name": system_name,
            "output": output,
            "raw_output": output,
            "metadata": {"base_system_name": "bare_llm"},
        },
        deep=True,
    )


def test_usage_normalization_avoids_alias_double_counting() -> None:
    openai_usage = {
        "prompt_tokens": 100,
        "input_tokens": 999,
        "completion_tokens": 10,
        "output_tokens": 888,
        "prompt_tokens_details": {"cached_tokens": 20},
        "completion_tokens_details": {"reasoning_tokens": 3},
    }
    normalized = normalize_provider_usage("openai", openai_usage)

    assert normalized == {
        "input_tokens": 100,
        "uncached_input_tokens": 80,
        "cached_input_tokens": 20,
        "cache_creation_input_tokens": 0,
        "output_tokens": 10,
        "reasoning_output_tokens": 3,
        "total_tokens": 110,
    }
    assert usage_cost_usd(
        normalized,
        PricingEntry(
            input_per_1m_usd=2.0,
            cached_input_per_1m_usd=0.5,
            output_per_1m_usd=4.0,
        ),
    ) == pytest.approx(0.00021)


def test_anthropic_usage_adds_separate_cache_counters() -> None:
    normalized = normalize_provider_usage(
        "anthropic",
        {
            "input_tokens": 100,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 20,
            "output_tokens": 5,
        },
    )

    assert normalized == {
        "input_tokens": 130,
        "uncached_input_tokens": 110,
        "cached_input_tokens": 20,
        "cache_creation_input_tokens": 10,
        "output_tokens": 5,
        "reasoning_output_tokens": 0,
        "total_tokens": 135,
    }


def test_operational_row_can_recover_usage_from_replay_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cached-response.json"
    cached_usage = {"prompt_tokens": 50, "completion_tokens": 7}
    write_json(
        cache,
        {
            "response": {
                "metadata": {
                    "llm_provider": "openai",
                    "llm_model": "test-model",
                    "llm_model_config_id": "test_model",
                    "request_sha256": "a" * 64,
                    "latency_ms": 125,
                    "provider_attempt_count": 1,
                    "usage": cached_usage,
                }
            }
        },
    )
    record = _record(
        "fixture_A1",
        metadata={
            "base_system_name": "bare_llm",
            "llm_provider": "openai",
            "llm_model_config_id": "test_model",
            "cache_path": str(cache),
        },
    )

    row = operational_row(record, pricing=_pricing())

    assert row is not None
    assert row["usage_source"] == "cache"
    assert row["usage"] == cached_usage
    assert row["input_tokens"] == 50
    assert row["output_tokens"] == 7
    assert row["latency_ms"] == 125
    assert row["provider_attempts"] == 1
    assert row["actual_cost_usd"] == pytest.approx(0.000128)


def test_partial_usage_never_becomes_a_false_total_cost() -> None:
    complete = operational_row(
        _record(
            "fixture_A1",
            metadata={
                "llm_provider": "openai",
                "llm_model": "test-model",
                "llm_model_config_id": "test_model",
                "latency_ms": 100,
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
        ),
        pricing=_pricing(),
    )
    missing = operational_row(
        _record(
            "fixture_A2",
            metadata={
                "llm_provider": "openai",
                "llm_model": "test-model",
                "llm_model_config_id": "test_model",
                "latency_ms": 300,
                "usage": {},
            },
        ),
        pricing=_pricing(),
    )
    assert complete is not None and missing is not None

    summary = summarize_operational_rows([complete, missing])

    assert summary["usage_coverage"] == 0.5
    assert summary["latency_coverage"] == 1.0
    assert summary["cost_coverage"] == 0.5
    assert summary["observed_cost_usd"] == pytest.approx(0.00024)
    assert summary["actual_cost_usd"] is None
    assert summary["latency_ms_mean"] == 200
    assert summary["latency_ms_median"] == 200
    assert summary["latency_ms_p95"] == pytest.approx(290)


def test_score_run_emits_paper_facing_operational_artifacts(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    scores_dir = tmp_path / "scores"
    record = _record(
        "fixture_A1",
        metadata={
            "base_system_name": "bare_llm",
            "llm_provider": "openai",
            "llm_model": "test-model",
            "llm_model_config_id": "test_model",
            "request_sha256": "b" * 64,
            "latency_ms": 250,
            "provider_attempt_count": 1,
            "usage": {"prompt_tokens": 100, "completion_tokens": 10},
        },
    )
    write_jsonl(trace_path, [record])

    score_run(FIXTURES / "cards.jsonl", trace_path, scores_dir, pricing=_pricing())

    rows = [
        json.loads(line)
        for line in (scores_dir / "operational_metrics.jsonl").read_text().splitlines()
    ]
    operational_summary = json.loads((scores_dir / "operational_summary.json").read_text())
    score_summary = json.loads((scores_dir / "summary.json").read_text())
    assert len(rows) == 1
    assert rows[0]["usage"]["prompt_tokens"] == 100
    assert operational_summary["usage_coverage"] == 1.0
    assert operational_summary["latency_ms_mean"] == 250
    assert operational_summary["provider_attempts"] == 1
    assert operational_summary["actual_cost_usd"] == pytest.approx(0.00024)
    assert score_summary["actual_cost_usd"] == pytest.approx(0.00024)
    assert score_summary["actual_total_tokens"] == 110
