from __future__ import annotations

import json
import math
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .io import read_json, read_jsonl
from .schemas import DecisionCard
from .systems.llm import (
    build_llm_messages,
    build_llm_request,
    find_cached_response,
    request_hash,
)
from .systems.providers import LLMModelConfig


class PricingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_per_1m_usd: float = Field(ge=0)
    cached_input_per_1m_usd: float = Field(default=0.0, ge=0)
    output_per_1m_usd: float = Field(ge=0)
    chars_per_token: float | None = Field(default=None, gt=0)
    safety_multiplier: float | None = Field(default=None, gt=0)
    source_url: str | None = None
    notes: str | None = None


class PricingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_chars_per_token: float = Field(default=3.5, gt=0)
    default_safety_multiplier: float = Field(default=1.35, gt=0)
    models: dict[str, PricingEntry]

    @field_validator("models")
    @classmethod
    def _non_empty(cls, value: dict[str, PricingEntry]) -> dict[str, PricingEntry]:
        if not value:
            raise ValueError("pricing config must define at least one model")
        return value

    def entry_for(self, model_config_id: str) -> PricingEntry:
        try:
            return self.models[model_config_id]
        except KeyError as exc:
            available = ", ".join(sorted(self.models))
            raise KeyError(
                f"No pricing entry for {model_config_id}. Available pricing entries: {available}"
            ) from exc


class CostEstimateRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    system_name: str
    model_config_id: str
    provider: str
    model: str
    request_sha256: str
    status: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    actual_input_tokens: int | None = None
    actual_cached_input_tokens: int | None = None
    actual_output_tokens: int | None = None
    actual_cost_usd: float | None = None
    cache_path: str | None = None
    trace_path: str | None = None


def load_pricing_config(path: Path) -> PricingConfig:
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    defaults = payload.get("defaults") or {}
    raw_models = payload.get("models")
    if not isinstance(raw_models, dict):
        raise ValueError(f"{path} must contain [models.<model_config_id>] pricing tables")
    return PricingConfig.model_validate(
        {
            "default_chars_per_token": defaults.get("chars_per_token", 3.5),
            "default_safety_multiplier": defaults.get("safety_multiplier", 1.35),
            "models": raw_models,
        }
    )


def trace_is_complete(trace_path: Path, expected_rows: int) -> bool:
    if not trace_path.exists():
        return False
    try:
        rows = read_jsonl(trace_path)
    except ValueError:
        return False
    return len(rows) == expected_rows


def estimate_message_tokens(
    messages: list[dict[str, str]],
    *,
    chars_per_token: float,
    safety_multiplier: float,
) -> int:
    serialized = json.dumps(messages, sort_keys=True, separators=(",", ":"))
    return int(math.ceil((len(serialized) / chars_per_token) * safety_multiplier))


def _usage_value(usage: dict[str, Any], *keys: str) -> int:
    total = 0
    for key in keys:
        value: Any = usage
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, (int, float)):
            total += int(value)
    return total


def _actual_usage_from_cache(cache_path: Path, entry: PricingEntry) -> dict[str, int | float] | None:
    payload = read_json(cache_path)
    response = payload.get("response", payload)
    metadata = response.get("metadata") if isinstance(response, dict) else None
    usage = metadata.get("usage") if isinstance(metadata, dict) else None
    if not isinstance(usage, dict):
        return None

    input_tokens = _usage_value(
        usage,
        "prompt_tokens",
        "input_tokens",
        "cache_creation_input_tokens",
    )
    output_tokens = _usage_value(usage, "completion_tokens", "output_tokens")
    cached_input_tokens = _usage_value(
        usage,
        "prompt_tokens_details.cached_tokens",
        "prompt_cache_hit_tokens",
        "cache_read_input_tokens",
    )
    uncached_input_tokens = max(0, input_tokens - cached_input_tokens)
    cost = (
        (uncached_input_tokens / 1_000_000) * entry.input_per_1m_usd
        + (cached_input_tokens / 1_000_000) * entry.cached_input_per_1m_usd
        + (output_tokens / 1_000_000) * entry.output_per_1m_usd
    )
    return {
        "actual_input_tokens": input_tokens,
        "actual_cached_input_tokens": cached_input_tokens,
        "actual_output_tokens": output_tokens,
        "actual_cost_usd": cost,
    }


def estimate_llm_matrix_cost(
    cards: list[DecisionCard],
    system_names: list[str],
    model_configs: list[LLMModelConfig],
    *,
    pricing: PricingConfig,
    cache_dir: Path,
    run_out: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    rows: list[CostEstimateRow] = []
    expected_rows = len(cards)
    for model_config in model_configs:
        entry = pricing.entry_for(model_config.id)
        chars_per_token = entry.chars_per_token or pricing.default_chars_per_token
        safety_multiplier = entry.safety_multiplier or pricing.default_safety_multiplier
        for system_name in system_names:
            run_label = f"{system_name}__{model_config.id}"
            trace_path = (
                run_out / model_config.id / system_name / "trace.jsonl"
                if run_out is not None
                else None
            )
            completed_trace = (
                False if force or trace_path is None else trace_is_complete(trace_path, expected_rows)
            )
            for card in cards:
                request = build_llm_request(card, system_name, model_config=model_config)
                messages = build_llm_messages(request)
                request_sha256 = request_hash(request)
                # The request hash is not embedded in the request itself; use the cache path basename as
                # the stable external identifier when present.
                cached_path = find_cached_response(cache_dir / model_config.id / system_name, request)
                estimated_input_tokens = estimate_message_tokens(
                    messages,
                    chars_per_token=chars_per_token,
                    safety_multiplier=safety_multiplier,
                )
                estimated_output_tokens = model_config.max_tokens
                estimated_cost = (
                    (estimated_input_tokens / 1_000_000) * entry.input_per_1m_usd
                    + (estimated_output_tokens / 1_000_000) * entry.output_per_1m_usd
                )
                status = "missing_live_call"
                incremental_cost = estimated_cost
                actual: dict[str, int | float] | None = None
                if completed_trace:
                    status = "completed_trace"
                    incremental_cost = 0.0
                elif cached_path is not None:
                    status = "response_cache"
                    incremental_cost = 0.0
                    actual = _actual_usage_from_cache(cached_path, entry)
                row_payload: dict[str, Any] = {
                    "task_id": card.task_id,
                    "system_name": run_label,
                    "model_config_id": model_config.id,
                    "provider": model_config.provider,
                    "model": model_config.model,
                    "request_sha256": request_sha256,
                    "status": status,
                    "estimated_input_tokens": estimated_input_tokens,
                    "estimated_output_tokens": estimated_output_tokens,
                    "estimated_cost_usd": incremental_cost,
                    "cache_path": str(cached_path) if cached_path is not None else None,
                    "trace_path": str(trace_path) if trace_path is not None else None,
                }
                if actual is not None:
                    row_payload.update(actual)
                rows.append(CostEstimateRow.model_validate(row_payload))
    return summarize_cost_rows(rows)


def summarize_cost_rows(rows: list[CostEstimateRow]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    max_input = 0
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        if row.status == "missing_live_call":
            max_input = max(max_input, row.estimated_input_tokens)
    total_estimated = sum(row.estimated_cost_usd for row in rows)
    actual_cached_cost = sum(row.actual_cost_usd or 0.0 for row in rows)
    return {
        "total_requests": len(rows),
        "missing_live_calls": by_status.get("missing_live_call", 0),
        "cached_or_completed_calls": by_status.get("response_cache", 0)
        + by_status.get("completed_trace", 0),
        "status_counts": by_status,
        "max_missing_input_tokens": max_input,
        "estimated_incremental_cost_usd": total_estimated,
        "actual_cached_cost_usd": actual_cached_cost,
        "rows": [row.model_dump(mode="json") for row in rows],
    }


def enforce_cost_limits(
    estimate: dict[str, Any],
    *,
    max_estimated_cost_usd: float | None = None,
    max_live_calls: int | None = None,
    max_input_tokens_per_call: int | None = None,
) -> list[str]:
    failures: list[str] = []
    if (
        max_estimated_cost_usd is not None
        and float(estimate["estimated_incremental_cost_usd"]) > max_estimated_cost_usd
    ):
        failures.append(
            "estimated incremental cost "
            f"${float(estimate['estimated_incremental_cost_usd']):.2f} exceeds "
            f"${max_estimated_cost_usd:.2f}"
        )
    if max_live_calls is not None and int(estimate["missing_live_calls"]) > max_live_calls:
        failures.append(
            f"missing live calls {int(estimate['missing_live_calls'])} exceeds {max_live_calls}"
        )
    if (
        max_input_tokens_per_call is not None
        and int(estimate["max_missing_input_tokens"]) > max_input_tokens_per_call
    ):
        failures.append(
            "max estimated input tokens per missing call "
            f"{int(estimate['max_missing_input_tokens'])} exceeds "
            f"{max_input_tokens_per_call}"
        )
    return failures
