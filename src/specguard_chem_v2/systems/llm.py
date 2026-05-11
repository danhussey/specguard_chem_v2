from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

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
    return {
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
        "support_set": [
            {
                "id": compound.id,
                "smiles": compound.smiles,
                "activity_value": compound.activity_value,
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


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(match.group(0))


def _metadata_for_request(request: dict[str, Any], model_config: LLMModelConfig) -> dict[str, Any]:
    generation = _generation_settings(model_config)
    return {
        "llm_provider": model_config.provider,
        "llm_model": model_config.model,
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


def _call_openai(request: dict[str, Any], *, model_config: LLMModelConfig) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional provider path
        raise RuntimeError("Install specguard-chem-v2[providers] to use live OpenAI calls") from exc
    api_key_env = model_config.api_key_env or "OPENAI_API_KEY"
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is required for live OpenAI calls")
    client_kwargs: dict[str, Any] = {"api_key": api_key}
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
    content = response.choices[0].message.content or "{}"
    payload = _extract_json_object(content)
    payload.setdefault("metadata", {})
    payload["metadata"]["provider"] = "openai"
    payload["metadata"]["model"] = model_config.model
    payload["metadata"]["model_config_id"] = model_config.id
    payload["metadata"]["response_id"] = getattr(response, "id", None)
    payload["metadata"]["latency_ms"] = latency_ms
    payload["metadata"]["usage"] = _usage_payload(getattr(response, "usage", None))
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
    client_kwargs: dict[str, Any] = {"api_key": api_key}
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
    payload = _extract_json_object("\n".join(content_parts))
    payload.setdefault("metadata", {})
    payload["metadata"]["provider"] = "anthropic"
    payload["metadata"]["model"] = model_config.model
    payload["metadata"]["model_config_id"] = model_config.id
    payload["metadata"]["thinking_budget_tokens"] = model_config.thinking_budget_tokens
    payload["metadata"]["response_id"] = getattr(response, "id", None)
    payload["metadata"]["latency_ms"] = latency_ms
    payload["metadata"]["usage"] = _usage_payload(getattr(response, "usage", None))
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
    message = response.choices[0].message
    payload = _extract_json_object(message.content or "{}")
    payload.setdefault("metadata", {})
    payload["metadata"]["provider"] = "deepseek"
    payload["metadata"]["model"] = model_config.model
    payload["metadata"]["model_config_id"] = model_config.id
    payload["metadata"]["thinking_enabled"] = model_config.thinking
    payload["metadata"]["response_id"] = getattr(response, "id", None)
    payload["metadata"]["latency_ms"] = latency_ms
    payload["metadata"]["usage"] = _usage_payload(getattr(response, "usage", None))
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
    selections: list[SelectionItem] = []
    raw_items = payload.get("selections", [])
    if not isinstance(raw_items, list):
        return selections
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        candidate_id = item.get("candidate_id")
        if candidate_id is None:
            continue
        try:
            rank = int(item.get("rank", index))
        except (TypeError, ValueError):
            rank = index
        confidence = item.get("confidence")
        try:
            normalized_confidence = None if confidence is None else float(confidence)
        except (TypeError, ValueError):
            normalized_confidence = None
        if normalized_confidence is not None:
            normalized_confidence = max(0.0, min(1.0, normalized_confidence))
        rationale = item.get("rationale")
        selections.append(
            SelectionItem(
                rank=max(1, rank),
                candidate_id=str(candidate_id),
                confidence=normalized_confidence,
                rationale=str(rationale) if rationale is not None else None,
            )
        )
    return selections


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
                **output.metadata,
                **_metadata_for_request(request, model_config),
                "cache_path": str(candidate_path),
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
        **dict(response_payload.get("metadata") or {}),
        **_metadata_for_request(request, model_config),
    }
    if run_label is not None:
        response_metadata["base_system_name"] = system_name
    output = SystemOutput(
        task_id=str(response_payload.get("task_id", card.task_id)),
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
