from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from ..artifacts import canonical_sha256, system_input_payload
from ..io import ensure_parent, read_json, write_json
from ..schemas import DecisionCard, SelectionItem, SystemOutput
from .providers import LLMModelConfig, default_openai_config

LLM_SYSTEMS = {
    "bare_llm",
    "llm_validator",
    "llm_tools",
    "llm_tools_validator",
}


def _candidate_summary(card: DecisionCard, *, include_tool_fields: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in card.candidate_pool:
        row: dict[str, Any] = {
            "id": candidate.id,
            "smiles": candidate.smiles,
            "mw": candidate.descriptors.get("mw"),
            "clogp": candidate.descriptors.get("clogp"),
        }
        if include_tool_fields:
            row.update(
                {
                    "tpsa": candidate.descriptors.get("tpsa"),
                    "hbd": candidate.descriptors.get("hbd"),
                    "hba": candidate.descriptors.get("hba"),
                    "rotatable_bonds": candidate.descriptors.get("rotatable_bonds"),
                }
            )
        rows.append(row)
    return rows


def _request_hash(request: dict[str, Any]) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def request_hash(request: dict[str, Any]) -> str:
    return _request_hash(request)


def _generation_settings(model_config: LLMModelConfig) -> dict[str, Any]:
    return {
        "max_tokens": model_config.max_tokens,
        "temperature": model_config.temperature,
        "reasoning_effort": model_config.reasoning_effort,
        "thinking": model_config.thinking,
        "thinking_budget_tokens": model_config.thinking_budget_tokens,
        "prompt_profile": model_config.prompt_profile,
        "request_timeout_seconds": model_config.request_timeout_seconds,
    }


def build_llm_request(
    card: DecisionCard,
    system_name: str,
    *,
    model_config: LLMModelConfig | None = None,
) -> dict[str, Any]:
    model_config = model_config or default_openai_config("gpt-4.1-mini")
    include_tool_fields = system_name in {"llm_tools", "llm_tools_validator"}
    activity_scale = card.assay_context.activity_scale
    if activity_scale is None:
        support_activity_types = {
            compound.activity_type for compound in card.support_set if compound.activity_type
        }
        activity_scale = (
            next(iter(support_activity_types)) if len(support_activity_types) == 1 else "activity"
        )
    higher_is_better = card.assay_context.activity_direction != "lower_is_better"
    request = {
        "task_id": card.task_id,
        "system_name": system_name,
        "model_config_id": model_config.id,
        "provider": model_config.provider,
        "model": model_config.model,
        "reasoning_effort": model_config.reasoning_effort,
        "thinking": model_config.thinking,
        "prompt_profile": model_config.prompt_profile,
        "generation": _generation_settings(model_config),
        "condition": {
            "uses_tools": system_name in {"llm_tools", "llm_tools_validator"},
            "uses_validator": system_name in {"llm_validator", "llm_tools_validator"},
            "live_provider_optional": True,
        },
        "budget_k": card.budget_k,
        "assay_context": card.assay_context.model_dump(mode="json"),
        "activity_semantics": {
            "support_activity_field": "activity_value",
            "scale": activity_scale,
            "higher_is_better": higher_is_better,
            "objective": (
                f"rank candidates to maximize predicted {activity_scale}"
                if higher_is_better
                else f"rank candidates to minimize predicted {activity_scale}"
            ),
        },
        "support_set": [
            {
                "id": compound.id,
                "smiles": compound.smiles,
                "activity_value": compound.activity_value,
                "activity_type": compound.activity_type,
            }
            for compound in card.support_set
        ],
        "candidate_pool": _candidate_summary(card, include_tool_fields=include_tool_fields),
        "hard_constraints": [
            constraint.model_dump(mode="json") for constraint in card.hard_constraints
        ],
        "response_contract": {
            "task_id": card.task_id,
            "system_name": system_name,
            "selections": [
                {"rank": 1, "candidate_id": "candidate ID from candidate_pool", "confidence": 0.0}
            ],
        },
    }
    if card.provenance is not None:
        request["artifact_provenance"] = card.provenance.model_dump(mode="json")
        request["system_input_sha256"] = canonical_sha256(system_input_payload(card))
    return request


def build_llm_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    system_name = str(request["system_name"])
    uses_tools = bool(request.get("condition", {}).get("uses_tools"))
    uses_validator = bool(request.get("condition", {}).get("uses_validator"))
    generation = request.get("generation") or {}
    prompt_profile = generation.get("prompt_profile") or request.get("prompt_profile") or "default"
    system_prompt = (
        "You are selecting candidate IDs for a retrospective medicinal-chemistry "
        "prioritisation audit. Return only valid JSON. Do not invent molecules or "
        "candidate IDs. Do not make synthesis, safety, selectivity, or clinical claims."
    )
    activity_semantics = request.get("activity_semantics") or {}
    activity_scale = str(activity_semantics.get("scale") or "activity_value")
    if activity_semantics.get("higher_is_better", True):
        system_prompt += (
            f" Support activity_value is on the {activity_scale} scale; higher values are "
            f"better. Rank candidates to maximize predicted {activity_scale}."
        )
    else:
        system_prompt += (
            f" Support activity_value is on the {activity_scale} scale; lower values are "
            f"better. Rank candidates to minimize predicted {activity_scale}."
        )
    if prompt_profile == "json_first":
        system_prompt += (
            " Your entire response must be one JSON object. Do not include markdown, "
            "prose, analysis, explanation, or chain-of-thought. Start with { and end with }."
        )
    if uses_tools:
        system_prompt += (
            " Use the supplied descriptor/tool-summary fields as computed evidence. "
            "Prefer candidates that balance predicted utility signals with hard constraints."
        )
    if uses_validator:
        system_prompt += (
            " Your output will be checked by a deterministic validator; malformed or "
            "invalid selections will be repaired or penalized."
        )
    profile_instruction = ""
    if prompt_profile == "json_first":
        profile_instruction = (
            "Return the final JSON object immediately. Do not describe your method. "
            "Do not emit hidden reasoning or a preamble.\n"
        )
    user_prompt = (
        f"Condition: {system_name}\n"
        f"{profile_instruction}"
        "Return JSON matching response_contract exactly. Select exactly budget_k "
        "candidate IDs from candidate_pool, ranked from best to worst.\n\n"
        f"{json.dumps(request, sort_keys=True)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    digest = _request_hash(request)
    return cache_dir / f"{request['system_name']}__{digest}.json"


def _legacy_hash_cache_path(cache_dir: Path, request: dict[str, Any]) -> Path | None:
    generation = dict(request.get("generation") or {})
    if (
        generation.get("max_tokens") != 4096
        or generation.get("temperature") is not None
        or generation.get("prompt_profile", "default") != "default"
        or generation.get("thinking_budget_tokens") is not None
        or generation.get("request_timeout_seconds") is not None
    ):
        return None
    legacy_request = copy.deepcopy(request)
    legacy_request.pop("generation", None)
    digest = _request_hash(legacy_request)
    return cache_dir / f"{request['system_name']}__{digest}.json"


def _stable_task_cache_paths(cache_dir: Path, request: dict[str, Any]) -> list[Path]:
    generation = dict(request.get("generation") or {})
    if (
        generation.get("max_tokens") != 4096
        or generation.get("temperature") is not None
        or generation.get("prompt_profile", "default") != "default"
        or generation.get("thinking_budget_tokens") is not None
        or generation.get("request_timeout_seconds") is not None
    ):
        return []
    model_config_id = request.get("model_config_id")
    paths = []
    if model_config_id:
        paths.append(
            cache_dir / f"{request['system_name']}__{model_config_id}__{request['task_id']}.json"
        )
    # Backwards-compatible fixture path used before provider/model matrix support.
    paths.append(cache_dir / f"{request['system_name']}__{request['task_id']}.json")
    return paths


def _cache_candidate_paths(cache_dir: Path, request: dict[str, Any]) -> list[Path]:
    paths: list[Path] = [_cache_path(cache_dir, request)]
    legacy_hash = _legacy_hash_cache_path(cache_dir, request)
    if legacy_hash is not None:
        paths.append(legacy_hash)
    paths.extend(_stable_task_cache_paths(cache_dir, request))
    return paths


def cache_candidate_paths(cache_dir: Path, request: dict[str, Any]) -> list[Path]:
    return _cache_candidate_paths(cache_dir, request)


def find_cached_response(cache_dir: Path, request: dict[str, Any]) -> Path | None:
    for candidate_path in _cache_candidate_paths(cache_dir, request):
        if candidate_path.exists():
            return candidate_path
    return None


def _contract_issue(
    code: str,
    message: str,
    *,
    rank: int | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code, "message": message}
    if rank is not None:
        issue["rank"] = rank
    if candidate_id is not None:
        issue["candidate_id"] = candidate_id
    return issue


def _first_decodable_json_object(text: str) -> tuple[dict[str, Any], int, int] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            payload, relative_end = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload, match.start(), match.start() + relative_end
    return None


def _extract_json_object(text: str) -> dict[str, Any]:
    """Legacy permissive extractor retained for non-live compatibility tests.

    Live provider responses use ``_parse_llm_response`` so surrounding prose or
    multiple objects are always retained as raw contract issues.
    """

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        decoded = _first_decodable_json_object(text)
        if decoded is not None:
            return decoded[0]
        raise ValueError("LLM response did not contain a valid JSON object") from None
    if not isinstance(payload, dict):
        raise ValueError("LLM response did not contain a valid JSON object")
    return payload


def _decode_response_object(
    raw_text: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    issues: list[dict[str, Any]] = []
    try:
        strict_payload = json.loads(raw_text)
    except json.JSONDecodeError as strict_error:
        decoded = _first_decodable_json_object(raw_text)
        if decoded is None:
            message = "Response did not contain a JSON object"
            issues.append(_contract_issue("schema_response_envelope", message))
            return {}, issues, f"{message}: {strict_error}"
        payload, start, end = decoded
        issues.append(
            _contract_issue(
                "schema_response_envelope",
                "Response was not exactly one JSON object with no surrounding content",
            )
        )
        trailing = raw_text[end:]
        if _first_decodable_json_object(trailing) is not None:
            issues.append(
                _contract_issue(
                    "schema_multiple_json_objects",
                    "Response contained more than one JSON object",
                )
            )
        if raw_text[:start].strip() or trailing.strip():
            return payload, issues, None
        return payload, issues, str(strict_error)
    if not isinstance(strict_payload, dict):
        message = "Response JSON must be one object"
        issues.append(_contract_issue("schema_response_object", message))
        return {}, issues, message
    return strict_payload, issues, None


def _parse_llm_response(
    request: dict[str, Any],
    raw_text: str,
    *,
    provider: str | None = None,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    """Strictly audit one provider response while retaining salvageable selections."""

    payload, issues, parse_error = _decode_response_object(raw_text)
    expected_task_id = str(request["task_id"])
    expected_system_name = str(request["system_name"])
    allowed_output_fields = {"task_id", "system_name", "selections"}
    for field in sorted(set(payload) - allowed_output_fields):
        issues.append(
            _contract_issue(
                "schema_unexpected_output_field",
                f"Unexpected top-level response field: {field}",
            )
        )

    raw_task_id = payload.get("task_id")
    if "task_id" not in payload:
        issues.append(_contract_issue("schema_missing_task_id", "Response omitted task_id"))
        normalized_task_id = expected_task_id
    elif not isinstance(raw_task_id, str) or not raw_task_id.strip():
        issues.append(
            _contract_issue(
                "schema_task_id_type",
                "Response task_id must be a non-empty string",
            )
        )
        normalized_task_id = expected_task_id
    else:
        normalized_task_id = raw_task_id

    raw_system_name = payload.get("system_name")
    if "system_name" not in payload:
        issues.append(_contract_issue("schema_missing_system_name", "Response omitted system_name"))
    elif not isinstance(raw_system_name, str) or not raw_system_name.strip():
        issues.append(
            _contract_issue(
                "schema_system_name_type",
                "Response system_name must be a non-empty string",
            )
        )
    elif raw_system_name != expected_system_name:
        issues.append(
            _contract_issue(
                "schema_system_name_mismatch",
                f"Response system_name {raw_system_name!r} does not match {expected_system_name!r}",
            )
        )

    raw_selections = payload.get("selections")
    if "selections" not in payload:
        issues.append(_contract_issue("schema_missing_selections", "Response omitted selections"))
        raw_selections = []
    elif not isinstance(raw_selections, list):
        issues.append(
            _contract_issue("schema_selections_type", "Response selections must be an array")
        )
        raw_selections = []

    normalized_selections: list[dict[str, Any]] = []
    raw_ranks: list[Any] = []
    allowed_selection_fields = {"rank", "candidate_id", "confidence", "rationale"}
    for position, item in enumerate(raw_selections, start=1):
        if not isinstance(item, dict):
            raw_ranks.append(None)
            issues.append(
                _contract_issue(
                    "schema_selection_item_type",
                    f"Selection item {position} must be an object",
                    rank=position,
                )
            )
            continue

        for field in sorted(set(item) - allowed_selection_fields):
            issues.append(
                _contract_issue(
                    "schema_selection_unexpected_field",
                    f"Selection item {position} has unexpected field: {field}",
                    rank=position,
                )
            )

        raw_rank = item.get("rank")
        raw_ranks.append(raw_rank)
        if "rank" not in item:
            issues.append(
                _contract_issue(
                    "schema_selection_missing_rank",
                    f"Selection item {position} omitted rank",
                    rank=position,
                )
            )
        elif isinstance(raw_rank, bool) or not isinstance(raw_rank, int):
            issues.append(
                _contract_issue(
                    "schema_selection_rank_type",
                    f"Selection item {position} rank must be an integer",
                    rank=position,
                )
            )
        elif raw_rank < 1:
            issues.append(
                _contract_issue(
                    "schema_selection_rank_value",
                    f"Selection item {position} rank must be at least 1",
                    rank=position,
                )
            )

        raw_candidate_id = item.get("candidate_id")
        if "candidate_id" not in item:
            issues.append(
                _contract_issue(
                    "schema_selection_missing_candidate_id",
                    f"Selection item {position} omitted candidate_id",
                    rank=position,
                )
            )
            continue
        if not isinstance(raw_candidate_id, str):
            issues.append(
                _contract_issue(
                    "schema_selection_candidate_id_type",
                    f"Selection item {position} candidate_id must be a string",
                    rank=position,
                )
            )
            continue
        if not raw_candidate_id.strip():
            issues.append(
                _contract_issue(
                    "schema_selection_candidate_id_empty",
                    f"Selection item {position} candidate_id must be non-empty",
                    rank=position,
                )
            )
            continue

        confidence = item.get("confidence")
        normalized_confidence: float | int | None = confidence
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                issues.append(
                    _contract_issue(
                        "schema_selection_confidence_type",
                        f"Selection item {position} confidence must be numeric",
                        rank=position,
                        candidate_id=raw_candidate_id,
                    )
                )
                normalized_confidence = None
            elif not 0.0 <= float(confidence) <= 1.0:
                issues.append(
                    _contract_issue(
                        "schema_selection_confidence_range",
                        f"Selection item {position} confidence must be between 0 and 1",
                        rank=position,
                        candidate_id=raw_candidate_id,
                    )
                )
                normalized_confidence = None

        rationale = item.get("rationale")
        if rationale is not None and not isinstance(rationale, str):
            issues.append(
                _contract_issue(
                    "schema_selection_rationale_type",
                    f"Selection item {position} rationale must be a string",
                    rank=position,
                    candidate_id=raw_candidate_id,
                )
            )
            rationale = None

        normalized_selections.append(
            {
                "rank": len(normalized_selections) + 1,
                "candidate_id": raw_candidate_id,
                "confidence": normalized_confidence,
                "rationale": rationale,
            }
        )

    expected_ranks = list(range(1, len(raw_selections) + 1))
    if raw_ranks != expected_ranks:
        issues.append(
            _contract_issue(
                "schema_rank_order",
                "Selection ranks must be consecutive and match array order starting at 1",
            )
        )

    if finish_reason in {"length", "max_tokens"}:
        issues.append(
            _contract_issue(
                "schema_provider_truncation",
                f"{provider or 'Provider'} response ended because of {finish_reason!r}",
            )
        )
    elif finish_reason is not None and finish_reason not in {
        "stop",
        "end_turn",
        "stop_sequence",
    }:
        issues.append(
            _contract_issue(
                "schema_provider_finish_reason",
                f"{provider or 'Provider'} response had nonterminal finish reason "
                f"{finish_reason!r}",
            )
        )

    metadata: dict[str, Any] = {
        "response_contract_issues": issues,
        "raw_response_task_id": raw_task_id,
        "raw_response_system_name": raw_system_name,
        "raw_response_selection_ranks": raw_ranks,
        "raw_response_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
    }
    if parse_error is not None:
        metadata["response_parse_error"] = parse_error
    return {
        "task_id": normalized_task_id,
        "system_name": expected_system_name,
        "selections": normalized_selections,
        "metadata": metadata,
    }


def _metadata_for_request(request: dict[str, Any], model_config: LLMModelConfig) -> dict[str, Any]:
    generation = _generation_settings(model_config)
    return {
        "llm_provider": model_config.provider,
        "llm_model": model_config.model,
        "configured_model": model_config.model,
        "llm_model_config_id": model_config.id,
        "request_sha256": _request_hash(request),
        **generation,
    }


def _empty_offline_output(
    card: DecisionCard,
    system_name: str,
    cache_path: Path | None,
    *,
    request: dict[str, Any],
    model_config: LLMModelConfig,
    run_label: str | None = None,
) -> SystemOutput:
    metadata = {
        "external_skipped": True,
        "reason": "No replay cache was available and live external calls were not allowed.",
        **_metadata_for_request(request, model_config),
    }
    if cache_path is not None:
        metadata["cache_path"] = str(cache_path)
    if run_label is not None:
        metadata["base_system_name"] = system_name
    return SystemOutput(
        task_id=card.task_id,
        system_name=run_label or system_name,
        selections=[],
        metadata=metadata,
    )


def _usage_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return None


def _jsonable_provider_content(value: Any) -> Any:
    """Preserve provider-returned content in a JSON-serializable form."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable_provider_content(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_provider_content(item) for item in value]
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return {
            str(key): _jsonable_provider_content(item)
            for key, item in attributes.items()
            if not str(key).startswith("_")
        }
    return str(value)


def _provider_response_metadata(
    *,
    provider: str,
    model_config: LLMModelConfig,
    response: Any,
    latency_ms: int,
    usage: dict[str, Any] | None,
    raw_response_text: str,
    raw_response_content: Any,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    returned_model_value = getattr(response, "model", None)
    provider_returned_model = (
        str(returned_model_value) if returned_model_value is not None else None
    )
    effective_model = provider_returned_model or model_config.model
    return {
        "provider": provider,
        "model": effective_model,
        "configured_model": model_config.model,
        "provider_returned_model": provider_returned_model,
        "model_config_id": model_config.id,
        "llm_model": effective_model,
        "response_id": getattr(response, "id", None),
        "latency_ms": latency_ms,
        "usage": usage,
        "provider_attempt_count": 1,
        "raw_response_text": raw_response_text,
        "raw_response_content": raw_response_content,
        "provider_finish_reason": finish_reason,
    }


def _call_openai(request: dict[str, Any], *, model_config: LLMModelConfig) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional provider path
        raise RuntimeError("Install specguard-chem-v2[providers] to use live OpenAI calls") from exc
    api_key_env = model_config.api_key_env or "OPENAI_API_KEY"
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is required for live OpenAI calls")
    client_kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
    if model_config.request_timeout_seconds is not None:
        client_kwargs["timeout"] = model_config.request_timeout_seconds
    client = OpenAI(**client_kwargs)
    kwargs: dict[str, Any] = {
        "model": model_config.model,
        "messages": build_llm_messages(request),
        "response_format": {"type": "json_object"},
        "max_completion_tokens": model_config.max_tokens,
    }
    if model_config.reasoning_effort is not None:
        kwargs["reasoning_effort"] = model_config.reasoning_effort
    if model_config.temperature is not None:
        kwargs["temperature"] = model_config.temperature
    started = time.perf_counter()
    response = client.chat.completions.create(**kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)
    choice = response.choices[0]
    message = choice.message
    raw_content = getattr(message, "content", None)
    content = raw_content if isinstance(raw_content, str) else ""
    usage = _usage_payload(getattr(response, "usage", None))
    payload = _parse_llm_response(
        request,
        content,
        provider="openai",
        finish_reason=getattr(choice, "finish_reason", None),
    )
    payload.setdefault("metadata", {})
    payload["metadata"].update(
        _provider_response_metadata(
            provider="openai",
            model_config=model_config,
            response=response,
            latency_ms=latency_ms,
            usage=usage,
            raw_response_text=content,
            raw_response_content=_jsonable_provider_content(message),
            finish_reason=getattr(choice, "finish_reason", None),
        )
    )
    return payload


def _call_anthropic(request: dict[str, Any], *, model_config: LLMModelConfig) -> dict[str, Any]:
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - optional provider path
        raise RuntimeError(
            "Install specguard-chem-v2[providers] to use live Anthropic calls"
        ) from exc
    api_key_env = model_config.api_key_env or "ANTHROPIC_API_KEY"
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is required for live Anthropic calls")
    messages = build_llm_messages(request)
    system_prompt = messages[0]["content"]
    user_messages = messages[1:]
    kwargs: dict[str, Any] = {
        "model": model_config.model,
        "max_tokens": model_config.max_tokens,
        "system": system_prompt,
        "messages": user_messages,
    }
    if model_config.temperature is not None:
        kwargs["temperature"] = model_config.temperature
    if model_config.thinking_budget_tokens is not None:
        kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": model_config.thinking_budget_tokens,
        }
    client_kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
    if model_config.request_timeout_seconds is not None:
        client_kwargs["timeout"] = model_config.request_timeout_seconds
    client = Anthropic(**client_kwargs)
    started = time.perf_counter()
    response = client.messages.create(**kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)
    content_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            content_parts.append(str(getattr(block, "text", "")))
    raw_text = "\n".join(content_parts)
    usage = _usage_payload(getattr(response, "usage", None))
    payload = _parse_llm_response(
        request,
        raw_text,
        provider="anthropic",
        finish_reason=getattr(response, "stop_reason", None),
    )
    payload.setdefault("metadata", {})
    payload["metadata"].update(
        _provider_response_metadata(
            provider="anthropic",
            model_config=model_config,
            response=response,
            latency_ms=latency_ms,
            usage=usage,
            raw_response_text=raw_text,
            raw_response_content=_jsonable_provider_content(response.content),
            finish_reason=getattr(response, "stop_reason", None),
        )
    )
    payload["metadata"]["thinking_budget_tokens"] = model_config.thinking_budget_tokens
    return payload


def _call_deepseek(request: dict[str, Any], *, model_config: LLMModelConfig) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional provider path
        raise RuntimeError(
            "Install specguard-chem-v2[providers] to use live DeepSeek calls"
        ) from exc
    api_key_env = model_config.api_key_env or "DEEPSEEK_API_KEY"
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is required for live DeepSeek calls")
    client_kwargs: dict[str, Any] = {
        "api_key": api_key,
        "base_url": model_config.base_url or "https://api.deepseek.com",
        "max_retries": 0,
    }
    if model_config.request_timeout_seconds is not None:
        client_kwargs["timeout"] = model_config.request_timeout_seconds
    client = OpenAI(**client_kwargs)
    kwargs: dict[str, Any] = {
        "model": model_config.model,
        "messages": build_llm_messages(request),
        "response_format": {"type": "json_object"},
        "max_tokens": model_config.max_tokens,
    }
    if model_config.reasoning_effort is not None:
        kwargs["reasoning_effort"] = model_config.reasoning_effort
    extra_body: dict[str, Any] = {}
    if model_config.thinking is not None:
        extra_body["thinking"] = {"type": "enabled" if model_config.thinking else "disabled"}
    if extra_body:
        kwargs["extra_body"] = extra_body
    started = time.perf_counter()
    response = client.chat.completions.create(**kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)
    choice = response.choices[0]
    message = choice.message
    raw_content = getattr(message, "content", None)
    content = raw_content if isinstance(raw_content, str) else ""
    usage = _usage_payload(getattr(response, "usage", None))
    payload = _parse_llm_response(
        request,
        content,
        provider="deepseek",
        finish_reason=getattr(choice, "finish_reason", None),
    )
    payload.setdefault("metadata", {})
    payload["metadata"].update(
        _provider_response_metadata(
            provider="deepseek",
            model_config=model_config,
            response=response,
            latency_ms=latency_ms,
            usage=usage,
            raw_response_text=content,
            raw_response_content=_jsonable_provider_content(message),
            finish_reason=getattr(choice, "finish_reason", None),
        )
    )
    payload["metadata"]["thinking_enabled"] = model_config.thinking
    payload["metadata"]["reasoning_content_present"] = bool(
        getattr(message, "reasoning_content", None)
    )
    return payload


def _call_provider(request: dict[str, Any], *, model_config: LLMModelConfig) -> dict[str, Any]:
    if model_config.provider == "openai":
        return _call_openai(request, model_config=model_config)
    if model_config.provider == "anthropic":
        return _call_anthropic(request, model_config=model_config)
    if model_config.provider == "deepseek":
        return _call_deepseek(request, model_config=model_config)
    raise ValueError(f"Unsupported provider: {model_config.provider}")


def _selection_items_from_payload(payload: dict[str, Any]) -> list[SelectionItem]:
    raw_items = payload.get("selections", [])
    if not isinstance(raw_items, list):
        return []
    return [SelectionItem.model_validate(item) for item in raw_items]


def run_llm_system(
    card: DecisionCard,
    system_name: str,
    *,
    cache_dir: Path | None = None,
    allow_external: bool = False,
    model: str = "gpt-4.1-mini",
    model_config: LLMModelConfig | None = None,
    run_label: str | None = None,
) -> SystemOutput:
    if system_name not in LLM_SYSTEMS:
        raise ValueError(f"Unknown LLM system: {system_name}")
    model_config = model_config or default_openai_config(model)
    request = build_llm_request(card, system_name, model_config=model_config)
    path = _cache_path(cache_dir, request) if cache_dir is not None else None
    candidate_paths = _cache_candidate_paths(cache_dir, request) if cache_dir is not None else []
    for candidate_path in candidate_paths:
        if candidate_path is not None and candidate_path.exists():
            payload = read_json(candidate_path)
            response = payload.get("response", payload)
            output = SystemOutput.model_validate(response)
            metadata = {
                **_metadata_for_request(request, model_config),
                **output.metadata,
            }
            if run_label is not None:
                metadata["base_system_name"] = system_name
                output = output.model_copy(update={"system_name": run_label, "metadata": metadata})
            else:
                output = output.model_copy(update={"metadata": metadata})
            return output
    if not allow_external:
        return _empty_offline_output(
            card,
            system_name,
            path,
            request=request,
            model_config=model_config,
            run_label=run_label,
        )

    response_payload = _call_provider(request, model_config=model_config)
    response_metadata = {
        **_metadata_for_request(request, model_config),
        **dict(response_payload.get("metadata") or {}),
    }
    if run_label is not None:
        response_metadata["base_system_name"] = system_name
    response_task_id = response_payload.get("task_id")
    output = SystemOutput(
        task_id=response_task_id if isinstance(response_task_id, str) else card.task_id,
        system_name=run_label or system_name,
        selections=_selection_items_from_payload(response_payload),
        metadata=response_metadata,
    )
    if path is not None:
        ensure_parent(path)
        write_json(path, {"request": request, "response": output.model_dump(mode="json")})
    return output


def export_llm_requests(
    cards: list[DecisionCard],
    system_names: list[str],
    *,
    model_configs: list[LLMModelConfig] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    configs = model_configs or [default_openai_config("gpt-4.1-mini")]
    for card in cards:
        for system_name in system_names:
            if system_name not in LLM_SYSTEMS:
                raise ValueError(f"Unknown LLM system: {system_name}")
            for model_config in configs:
                request = build_llm_request(card, system_name, model_config=model_config)
                rows.append(
                    {
                        "task_id": card.task_id,
                        "system_name": system_name,
                        "model_config_id": model_config.id,
                        "provider": model_config.provider,
                        "model": model_config.model,
                        "request_sha256": _request_hash(request),
                        "request": request,
                        "messages": build_llm_messages(request),
                    }
                )
    return rows
