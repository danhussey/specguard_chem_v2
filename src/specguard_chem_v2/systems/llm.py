from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from ..io import ensure_parent, read_json, write_json
from ..schemas import DecisionCard, SelectionItem, SystemOutput

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


def build_llm_request(card: DecisionCard, system_name: str) -> dict[str, Any]:
    include_tool_fields = system_name in {"llm_tools", "llm_tools_validator"}
    return {
        "task_id": card.task_id,
        "system_name": system_name,
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
        "hard_constraints": [constraint.model_dump(mode="json") for constraint in card.hard_constraints],
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
    system_prompt = (
        "You are selecting candidate IDs for a retrospective medicinal-chemistry "
        "prioritisation audit. Return only valid JSON. Do not invent molecules or "
        "candidate IDs. Do not make synthesis, safety, selectivity, or clinical claims."
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
    user_prompt = (
        f"Condition: {system_name}\n"
        "Return JSON matching response_contract exactly. Select exactly budget_k "
        "candidate IDs from candidate_pool, ranked from best to worst.\n\n"
        f"{json.dumps(request, sort_keys=True)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return cache_dir / f"{request['system_name']}__{digest}.json"


def _stable_task_cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    return cache_dir / f"{request['system_name']}__{request['task_id']}.json"


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(match.group(0))


def _empty_offline_output(card: DecisionCard, system_name: str, cache_path: Path | None) -> SystemOutput:
    metadata = {
        "external_skipped": True,
        "reason": "No replay cache was available and live external calls were not allowed.",
    }
    if cache_path is not None:
        metadata["cache_path"] = str(cache_path)
    return SystemOutput(task_id=card.task_id, system_name=system_name, selections=[], metadata=metadata)


def _call_openai(request: dict[str, Any], *, model: str) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional provider path
        raise RuntimeError("Install specguard-chem-v2[providers] to use live OpenAI calls") from exc
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for live OpenAI calls")
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=build_llm_messages(request),
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    payload = _extract_json_object(content)
    payload.setdefault("metadata", {})
    payload["metadata"]["provider"] = "openai"
    payload["metadata"]["model"] = model
    return payload


def run_llm_system(
    card: DecisionCard,
    system_name: str,
    *,
    cache_dir: Path | None = None,
    allow_external: bool = False,
    model: str = "gpt-4.1-mini",
) -> SystemOutput:
    if system_name not in LLM_SYSTEMS:
        raise ValueError(f"Unknown LLM system: {system_name}")
    request = build_llm_request(card, system_name)
    path = _cache_path(cache_dir, request) if cache_dir is not None else None
    stable_path = _stable_task_cache_path(cache_dir, request) if cache_dir is not None else None
    for candidate_path in [stable_path, path]:
        if candidate_path is not None and candidate_path.exists():
            payload = read_json(candidate_path)
            response = payload.get("response", payload)
            return SystemOutput.model_validate(response)
    if not allow_external:
        return _empty_offline_output(card, system_name, path)

    response_payload = _call_openai(request, model=model)
    output = SystemOutput(
        task_id=str(response_payload.get("task_id", card.task_id)),
        system_name=system_name,
        selections=[
            SelectionItem.model_validate(item)
            for item in response_payload.get("selections", [])
            if isinstance(item, dict)
        ],
        metadata=dict(response_payload.get("metadata") or {}),
    )
    if path is not None:
        ensure_parent(path)
        write_json(path, {"request": request, "response": output.model_dump(mode="json")})
    return output


def export_llm_requests(
    cards: list[DecisionCard],
    system_names: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in cards:
        for system_name in system_names:
            if system_name not in LLM_SYSTEMS:
                raise ValueError(f"Unknown LLM system: {system_name}")
            request = build_llm_request(card, system_name)
            rows.append(
                {
                    "task_id": card.task_id,
                    "system_name": system_name,
                    "request": request,
                    "messages": build_llm_messages(request),
                }
            )
    return rows
