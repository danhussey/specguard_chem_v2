from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from specguard_chem_v2.artifacts import load_evaluation_cards
from specguard_chem_v2.io import read_json, read_jsonl
from specguard_chem_v2.runner import repair_output, run_system_file, validate_output
from specguard_chem_v2.schemas import SystemOutput
from specguard_chem_v2.systems import llm
from specguard_chem_v2.systems.providers import LLMModelConfig

FIXTURES = Path(__file__).parent / "fixtures"


class _Dumpable:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self.payload


class _TextBlock(_Dumpable):
    def __init__(self, text: str) -> None:
        super().__init__({"type": "text", "text": text})
        self.type = "text"
        self.text = text


def _request() -> dict[str, Any]:
    return {
        "task_id": "task-1",
        "system_name": "bare_llm",
        "condition": {},
        "generation": {"prompt_profile": "json_first"},
    }


def _valid_text(task_id: str = "task-1") -> str:
    return json.dumps(
        {
            "task_id": task_id,
            "system_name": "bare_llm",
            "selections": [],
        },
        separators=(",", ":"),
    )


def _openai_style_response(
    text: str | None,
    *,
    provider_model: str,
    response_id: str,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    message = SimpleNamespace(content=text, reasoning_content=None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = _Dumpable({"prompt_tokens": 101, "completion_tokens": 17})
    return SimpleNamespace(
        id=response_id,
        model=provider_model,
        choices=[choice],
        usage=usage,
    )


def _install_fake_openai(
    monkeypatch: Any,
    response: SimpleNamespace,
) -> dict[str, Any]:
    state: dict[str, Any] = {"constructor_kwargs": None, "create_calls": []}

    class _Completions:
        def create(self, **kwargs: Any) -> SimpleNamespace:
            state["create_calls"].append(kwargs)
            return response

    class _OpenAI:
        def __init__(self, **kwargs: Any) -> None:
            state["constructor_kwargs"] = kwargs
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_OpenAI))
    return state


def _install_fake_anthropic(
    monkeypatch: Any,
    response: SimpleNamespace,
) -> dict[str, Any]:
    state: dict[str, Any] = {"constructor_kwargs": None, "create_calls": []}

    class _Messages:
        def create(self, **kwargs: Any) -> SimpleNamespace:
            state["create_calls"].append(kwargs)
            return response

    class _Anthropic:
        def __init__(self, **kwargs: Any) -> None:
            state["constructor_kwargs"] = kwargs
            self.messages = _Messages()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=_Anthropic))
    return state


def _assert_preserved_metadata(
    metadata: dict[str, Any],
    *,
    configured_model: str,
    provider_model: str,
    response_id: str,
    raw_text: str,
) -> None:
    assert metadata["configured_model"] == configured_model
    assert metadata["provider_returned_model"] == provider_model
    assert metadata["llm_model"] == provider_model
    assert metadata["response_id"] == response_id
    assert metadata["usage"] == {"prompt_tokens": 101, "completion_tokens": 17}
    assert isinstance(metadata["latency_ms"], int)
    assert metadata["provider_attempt_count"] == 1
    assert metadata["raw_response_text"] == raw_text
    assert metadata["provider_finish_reason"] == "stop"


def test_openai_adapter_uses_one_attempt_and_preserves_response(monkeypatch: Any) -> None:
    raw_text = _valid_text()
    response = _openai_style_response(
        raw_text,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-test",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
        reasoning_effort="low",
    )

    payload = llm._call_openai(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert state["constructor_kwargs"]["max_retries"] == 0
    _assert_preserved_metadata(
        payload["metadata"],
        configured_model=config.model,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-test",
        raw_text=raw_text,
    )
    assert payload["metadata"]["raw_response_content"]["content"] == raw_text


def test_anthropic_adapter_uses_one_attempt_and_preserves_response(monkeypatch: Any) -> None:
    raw_text = _valid_text()
    response = SimpleNamespace(
        id="msg-test",
        model="claude-returned-snapshot",
        content=[_TextBlock(raw_text)],
        usage=_Dumpable({"prompt_tokens": 101, "completion_tokens": 17}),
        stop_reason="stop",
    )
    state = _install_fake_anthropic(monkeypatch, response)
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "test-key")
    config = LLMModelConfig(
        id="anthropic_test",
        provider="anthropic",
        model="claude-configured-snapshot",
        api_key_env="TEST_ANTHROPIC_KEY",
    )

    payload = llm._call_anthropic(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert state["constructor_kwargs"]["max_retries"] == 0
    _assert_preserved_metadata(
        payload["metadata"],
        configured_model=config.model,
        provider_model="claude-returned-snapshot",
        response_id="msg-test",
        raw_text=raw_text,
    )
    assert payload["metadata"]["raw_response_content"] == [{"type": "text", "text": raw_text}]


def test_deepseek_adapter_uses_one_attempt_and_preserves_response(monkeypatch: Any) -> None:
    raw_text = _valid_text()
    response = _openai_style_response(
        raw_text,
        provider_model="deepseek-returned-snapshot",
        response_id="deepseek-test",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_DEEPSEEK_KEY", "test-key")
    config = LLMModelConfig(
        id="deepseek_test",
        provider="deepseek",
        model="deepseek-configured-alias",
        api_key_env="TEST_DEEPSEEK_KEY",
        base_url="https://example.invalid",
        thinking=False,
    )

    payload = llm._call_deepseek(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert state["constructor_kwargs"]["max_retries"] == 0
    assert state["constructor_kwargs"]["base_url"] == "https://example.invalid"
    _assert_preserved_metadata(
        payload["metadata"],
        configured_model=config.model,
        provider_model="deepseek-returned-snapshot",
        response_id="deepseek-test",
        raw_text=raw_text,
    )
    assert payload["metadata"]["raw_response_content"]["content"] == raw_text


def test_malformed_json_is_recorded_without_a_paid_retry(monkeypatch: Any) -> None:
    raw_text = "not valid JSON"
    response = _openai_style_response(
        raw_text,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-malformed",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
    )

    payload = llm._call_openai(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert payload["selections"] == []
    assert payload["metadata"]["provider_attempt_count"] == 1
    assert payload["metadata"]["raw_response_text"] == raw_text
    assert "response_parse_error" in payload["metadata"]
    assert {issue["code"] for issue in payload["metadata"]["response_contract_issues"]} >= {
        "schema_response_envelope",
        "schema_missing_system_name",
    }


def test_none_content_is_preserved_without_fabricating_json(monkeypatch: Any) -> None:
    response = _openai_style_response(
        None,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-empty",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
    )

    payload = llm._call_openai(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert payload["metadata"]["raw_response_text"] == ""
    assert payload["metadata"]["raw_response_content"]["content"] is None
    assert "response_parse_error" in payload["metadata"]


def test_prose_envelope_is_salvaged_but_remains_a_raw_issue(monkeypatch: Any) -> None:
    json_text = json.dumps(
        {
            "task_id": "task-1",
            "system_name": "bare_llm",
            "selections": [{"rank": 1, "candidate_id": "candidate-1"}],
        }
    )
    raw_text = f"Here is the result:\n{json_text}\nDone."
    response = _openai_style_response(
        raw_text,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-prose",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
    )

    payload = llm._call_openai(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert [item["candidate_id"] for item in payload["selections"]] == ["candidate-1"]
    issue_codes = {issue["code"] for issue in payload["metadata"]["response_contract_issues"]}
    assert "schema_response_envelope" in issue_codes


def test_provider_truncation_remains_a_raw_issue_without_retry(monkeypatch: Any) -> None:
    raw_text = _valid_text()
    response = _openai_style_response(
        raw_text,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-truncated",
        finish_reason="length",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
    )

    payload = llm._call_openai(_request(), model_config=config)

    assert len(state["create_calls"]) == 1
    assert payload["metadata"]["provider_finish_reason"] == "length"
    assert "schema_provider_truncation" in {
        issue["code"] for issue in payload["metadata"]["response_contract_issues"]
    }


def test_strict_payload_audit_preserves_salvageable_items_and_raw_issues() -> None:
    raw_text = json.dumps(
        {
            "task_id": "task-1",
            "system_name": "wrong-system",
            "unexpected": "field",
            "selections": [
                {
                    "rank": 2,
                    "candidate_id": "candidate-1",
                    "confidence": "high",
                    "extra": True,
                },
                "not-an-object",
                {"rank": 1, "candidate_id": 42},
                {"candidate_id": "candidate-2", "rationale": 123},
            ],
        }
    )

    payload = llm._parse_llm_response(_request(), raw_text)

    assert [item["candidate_id"] for item in payload["selections"]] == [
        "candidate-1",
        "candidate-2",
    ]
    assert [item["rank"] for item in payload["selections"]] == [1, 2]
    assert payload["selections"][0]["confidence"] is None
    assert payload["selections"][1]["rationale"] is None
    issue_codes = {issue["code"] for issue in payload["metadata"]["response_contract_issues"]}
    assert {
        "schema_system_name_mismatch",
        "schema_unexpected_output_field",
        "schema_selection_unexpected_field",
        "schema_selection_confidence_type",
        "schema_selection_item_type",
        "schema_selection_candidate_id_type",
        "schema_selection_missing_rank",
        "schema_selection_rationale_type",
        "schema_rank_order",
    } <= issue_codes


def test_repair_resolves_contract_issues_without_erasing_raw_evidence() -> None:
    card = load_evaluation_cards(FIXTURES / "cards.jsonl")[0]
    raw_text = json.dumps(
        {
            "task_id": card.task_id,
            "system_name": "wrong-system",
            "selections": [
                {"rank": 3, "candidate_id": "A1_C1"},
                {"rank": 2, "candidate_id": "A1_C2"},
                {"rank": 1, "candidate_id": "A1_C3"},
            ],
        }
    )
    payload = llm._parse_llm_response(
        {"task_id": card.task_id, "system_name": "bare_llm"},
        raw_text,
    )
    raw_output = SystemOutput.model_validate(payload)

    raw_issues = validate_output(card, raw_output)
    repaired_output = repair_output(card, raw_output)
    repaired_issues = validate_output(card, repaired_output)

    assert {"schema_system_name_mismatch", "schema_rank_order"} <= {
        issue.code for issue in raw_issues
    }
    assert not {
        "schema_system_name_mismatch",
        "schema_rank_order",
    } & {issue.code for issue in repaired_issues}
    assert repaired_output.metadata["response_contract_issues"]
    assert repaired_output.metadata["response_contract_issues_resolved"] is True


def test_provider_evidence_is_preserved_in_trace_and_cache(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    raw_text = json.dumps(
        {
            "task_id": "fixture_A1",
            "system_name": "wrong-system",
            "selections": [
                {"rank": 2, "candidate_id": "A1_C1", "confidence": "high"},
                {"candidate_id": "A1_C2", "confidence": 0.5},
                {"rank": 3, "candidate_id": 123},
                {"rank": 4, "candidate_id": "A1_C3", "extra": True},
            ],
        },
        separators=(",", ":"),
    )
    response = _openai_style_response(
        raw_text,
        provider_model="gpt-returned-snapshot",
        response_id="chatcmpl-trace",
    )
    state = _install_fake_openai(monkeypatch, response)
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-key")
    config = LLMModelConfig(
        id="openai_test",
        provider="openai",
        model="gpt-configured-snapshot",
        api_key_env="TEST_OPENAI_KEY",
        prompt_profile="json_first",
    )
    trace_path = tmp_path / "trace.jsonl"
    cache_dir = tmp_path / "cache"

    run_system_file(
        FIXTURES / "cards.jsonl",
        "bare_llm",
        trace_path,
        cache_dir=cache_dir,
        allow_external=True,
        model_config=config,
        run_label="bare_llm__openai_test",
        task_id="fixture_A1",
    )

    assert len(state["create_calls"]) == 1
    trace = read_jsonl(trace_path)
    assert len(trace) == 1
    trace_metadata = trace[0]["metadata"]
    output_metadata = trace[0]["output"]["metadata"]
    for metadata in (trace_metadata, output_metadata):
        assert metadata["configured_model"] == "gpt-configured-snapshot"
        assert metadata["provider_returned_model"] == "gpt-returned-snapshot"
        assert metadata["provider_attempt_count"] == 1
        assert metadata["raw_response_text"] == raw_text
        assert metadata["response_id"] == "chatcmpl-trace"
        assert metadata["usage"] == {"prompt_tokens": 101, "completion_tokens": 17}

    assert [item["candidate_id"] for item in trace[0]["output"]["selections"]] == [
        "A1_C1",
        "A1_C2",
        "A1_C3",
    ]
    raw_issue_codes = {issue["code"] for issue in trace[0]["raw_issues"]}
    assert {
        "schema_system_name_mismatch",
        "schema_selection_confidence_type",
        "schema_selection_missing_rank",
        "schema_selection_candidate_id_type",
        "schema_selection_unexpected_field",
        "schema_rank_order",
    } <= raw_issue_codes
    assert raw_issue_codes <= {issue["code"] for issue in trace[0]["issues"]}

    cache_paths = list(cache_dir.glob("*.json"))
    assert len(cache_paths) == 1
    cached_metadata = read_json(cache_paths[0])["response"]["metadata"]
    assert cached_metadata["provider_returned_model"] == "gpt-returned-snapshot"
    assert cached_metadata["configured_model"] == "gpt-configured-snapshot"
    assert cached_metadata["provider_attempt_count"] == 1
    assert cached_metadata["raw_response_text"] == raw_text
    assert cached_metadata["response_contract_issues"]

    provider_trace_bytes = trace_path.read_bytes()
    replay_trace_path = tmp_path / "replay.trace.jsonl"
    run_system_file(
        FIXTURES / "cards.jsonl",
        "bare_llm",
        replay_trace_path,
        cache_dir=cache_dir,
        allow_external=False,
        model_config=config,
        run_label="bare_llm__openai_test",
        task_id="fixture_A1",
    )

    assert len(state["create_calls"]) == 1
    assert replay_trace_path.read_bytes() == provider_trace_bytes
    assert "cache_path" not in read_jsonl(replay_trace_path)[0]["output"]["metadata"]
