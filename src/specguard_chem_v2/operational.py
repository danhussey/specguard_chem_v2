from __future__ import annotations

import math
from pathlib import Path
from statistics import mean, median
from typing import Any

from .costing import PricingConfig, PricingEntry
from .io import read_json, write_json, write_jsonl
from .schemas import RunRecord

OPERATIONAL_METRICS_SCHEMA_VERSION = "1.0.0"
LLM_BASE_SYSTEMS = frozenset({"bare_llm", "llm_tools", "llm_validator", "llm_tools_validator"})


def _nested_value(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)) or value < 0:
        return None
    return int(value)


def _nonnegative_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        return None
    return normalized


def _first_int(payload: dict[str, Any], *paths: str) -> int | None:
    for path in paths:
        value = _nonnegative_int(_nested_value(payload, path))
        if value is not None:
            return value
    return None


def normalize_provider_usage(provider: str | None, usage: dict[str, Any]) -> dict[str, int]:
    """Normalize provider usage without double-counting alias fields.

    OpenAI-compatible usage reports cached prompt tokens as a subset of
    ``prompt_tokens``. Anthropic reports ordinary, cache-write, and cache-read
    input tokens as separate counters. The normalized total therefore uses the
    provider's accounting convention instead of summing every known alias.
    """

    base_input = _first_int(usage, "prompt_tokens", "input_tokens") or 0
    output_tokens = _first_int(usage, "completion_tokens", "output_tokens") or 0
    cached_input = (
        _first_int(
            usage,
            "prompt_tokens_details.cached_tokens",
            "input_tokens_details.cached_tokens",
            "cache_read_input_tokens",
            "prompt_cache_hit_tokens",
        )
        or 0
    )
    cache_creation_input = (
        _first_int(
            usage,
            "cache_creation_input_tokens",
            "prompt_cache_creation_tokens",
        )
        or 0
    )
    reasoning_output = (
        _first_int(
            usage,
            "completion_tokens_details.reasoning_tokens",
            "output_tokens_details.reasoning_tokens",
            "reasoning_tokens",
        )
        or 0
    )

    anthropic_style = provider == "anthropic" or (
        "prompt_tokens" not in usage
        and ("cache_creation_input_tokens" in usage or "cache_read_input_tokens" in usage)
    )
    if anthropic_style:
        uncached_input = base_input + cache_creation_input
        total_input = uncached_input + cached_input
    else:
        total_input = base_input
        cached_input = min(cached_input, total_input)
        uncached_input = max(0, total_input - cached_input)

    return {
        "input_tokens": total_input,
        "uncached_input_tokens": uncached_input,
        "cached_input_tokens": cached_input,
        "cache_creation_input_tokens": cache_creation_input,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_output,
        "total_tokens": total_input + output_tokens,
    }


def _has_complete_usage(usage: dict[str, Any]) -> bool:
    return (
        _first_int(usage, "prompt_tokens", "input_tokens") is not None
        and _first_int(usage, "completion_tokens", "output_tokens") is not None
    )


def usage_cost_usd(usage: dict[str, int], pricing: PricingEntry) -> float:
    """Calculate usage-derived cost under a frozen pricing entry.

    Cache-creation tokens are included in ``uncached_input_tokens`` and use the
    ordinary input rate. This is exact for the release matrix, which does not
    enable Anthropic prompt caching, and remains explicit in the emitted cost
    basis should a later run introduce cache-write usage.
    """

    return (
        (usage["uncached_input_tokens"] / 1_000_000) * pricing.input_per_1m_usd
        + (usage["cached_input_tokens"] / 1_000_000) * pricing.cached_input_per_1m_usd
        + (usage["output_tokens"] / 1_000_000) * pricing.output_per_1m_usd
    )


def _cache_metadata(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    payload = read_json(path)
    response = payload.get("response", payload)
    if not isinstance(response, dict):
        raise ValueError(f"{path}: cached response must be an object")
    metadata = response.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError(f"{path}: cached response metadata must be an object")
    return metadata


def _record_metadata(record: RunRecord) -> tuple[dict[str, Any], str]:
    raw_output = record.raw_output or record.output
    metadata = {**record.metadata, **raw_output.metadata}
    if isinstance(metadata.get("usage"), dict):
        return metadata, "trace"

    cached = _cache_metadata(metadata.get("cache_path"))
    if cached is not None and isinstance(cached.get("usage"), dict):
        return {**metadata, **cached}, "cache"
    return metadata, "trace"


def _base_system_name(record: RunRecord, metadata: dict[str, Any]) -> str:
    value = record.metadata.get("base_system_name") or metadata.get("base_system_name")
    if value:
        return str(value)
    return record.system_name.split("__", 1)[0]


def _is_llm_record(record: RunRecord, metadata: dict[str, Any]) -> bool:
    return bool(
        _base_system_name(record, metadata) in LLM_BASE_SYSTEMS
        or metadata.get("llm_model_config_id")
        or metadata.get("model_config_id")
        or metadata.get("usage")
    )


def operational_row(
    record: RunRecord,
    *,
    pricing: PricingConfig | None = None,
) -> dict[str, Any] | None:
    metadata, usage_source = _record_metadata(record)
    if not _is_llm_record(record, metadata):
        return None

    provider_value = metadata.get("llm_provider") or metadata.get("provider")
    provider = str(provider_value) if provider_value is not None else None
    model_value = metadata.get("llm_model") or metadata.get("model")
    model = str(model_value) if model_value is not None else None
    config_value = metadata.get("llm_model_config_id") or metadata.get("model_config_id")
    model_config_id = str(config_value) if config_value is not None else None
    usage_payload = metadata.get("usage")
    normalized_usage = (
        normalize_provider_usage(provider, usage_payload)
        if isinstance(usage_payload, dict) and _has_complete_usage(usage_payload)
        else None
    )

    entry = None
    actual_cost = None
    if normalized_usage is not None and pricing is not None and model_config_id is not None:
        entry = pricing.entry_for(model_config_id)
        actual_cost = usage_cost_usd(normalized_usage, entry)

    attempts = _first_int(
        metadata,
        "provider_attempts",
        "provider_attempt_count",
        "attempt_count",
    )
    row: dict[str, Any] = {
        "schema_version": OPERATIONAL_METRICS_SCHEMA_VERSION,
        "task_id": record.task_id,
        "system_name": record.system_name,
        "base_system_name": _base_system_name(record, metadata),
        "provider": provider,
        "model": model,
        "model_config_id": model_config_id,
        "request_sha256": metadata.get("request_sha256"),
        "usage_source": usage_source if isinstance(usage_payload, dict) else None,
        "usage": usage_payload if isinstance(usage_payload, dict) else None,
        "latency_ms": _nonnegative_float(metadata.get("latency_ms")),
        "provider_attempts": attempts,
        "actual_cost_usd": actual_cost,
        "pricing_source_url": entry.source_url if entry is not None else None,
        "cost_basis": (
            "provider-reported token usage multiplied by frozen per-token pricing"
            if actual_cost is not None
            else None
        ),
    }
    if normalized_usage is not None:
        row.update(normalized_usage)
    else:
        row.update(
            {
                "input_tokens": None,
                "uncached_input_tokens": None,
                "cached_input_tokens": None,
                "cache_creation_input_tokens": None,
                "output_tokens": None,
                "reasoning_output_tokens": None,
                "total_tokens": None,
            }
        )
    return row


def operational_rows(
    records: list[RunRecord],
    *,
    pricing: PricingConfig | None = None,
) -> list[dict[str, Any]]:
    rows = [operational_row(record, pricing=pricing) for record in records]
    return [row for row in rows if row is not None]


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize_operational_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}

    num_records = len(rows)
    usage_payload_rows = [row for row in rows if isinstance(row.get("usage"), dict)]
    usage_rows = [row for row in rows if row.get("input_tokens") is not None]
    latency_values = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    cost_values = [
        float(row["actual_cost_usd"]) for row in rows if row.get("actual_cost_usd") is not None
    ]
    attempt_values = [
        int(row["provider_attempts"]) for row in rows if row.get("provider_attempts") is not None
    ]

    summary: dict[str, Any] = {
        "operational_metrics_schema_version": OPERATIONAL_METRICS_SCHEMA_VERSION,
        "operational_num_records": num_records,
        "usage_payload_records": len(usage_payload_rows),
        "usage_records": len(usage_rows),
        "usage_coverage": len(usage_rows) / num_records,
        "latency_records": len(latency_values),
        "latency_coverage": len(latency_values) / num_records,
        "cost_records": len(cost_values),
        "cost_coverage": len(cost_values) / num_records,
        "actual_input_tokens": sum(int(row["input_tokens"]) for row in usage_rows),
        "actual_uncached_input_tokens": sum(
            int(row["uncached_input_tokens"]) for row in usage_rows
        ),
        "actual_cached_input_tokens": sum(int(row["cached_input_tokens"]) for row in usage_rows),
        "actual_cache_creation_input_tokens": sum(
            int(row["cache_creation_input_tokens"]) for row in usage_rows
        ),
        "actual_output_tokens": sum(int(row["output_tokens"]) for row in usage_rows),
        "actual_reasoning_output_tokens": sum(
            int(row["reasoning_output_tokens"]) for row in usage_rows
        ),
        "actual_total_tokens": sum(int(row["total_tokens"]) for row in usage_rows),
        "observed_cost_usd": sum(cost_values),
        "actual_cost_usd": sum(cost_values) if len(cost_values) == num_records else None,
        "actual_cost_basis": (
            "provider-reported token usage multiplied by frozen per-token pricing"
            if len(cost_values) == num_records
            else None
        ),
        "provider_attempt_records": len(attempt_values),
        "provider_attempts": sum(attempt_values) if len(attempt_values) == num_records else None,
    }

    if latency_values:
        summary.update(
            {
                "latency_ms_total": sum(latency_values),
                "latency_ms_mean": mean(latency_values),
                "latency_ms_median": median(latency_values),
                "latency_ms_p95": _percentile(latency_values, 0.95),
                "latency_ms_min": min(latency_values),
                "latency_ms_max": max(latency_values),
            }
        )
    else:
        summary.update(
            {
                "latency_ms_total": None,
                "latency_ms_mean": None,
                "latency_ms_median": None,
                "latency_ms_p95": None,
                "latency_ms_min": None,
                "latency_ms_max": None,
            }
        )

    for field in ("system_name", "base_system_name", "provider", "model", "model_config_id"):
        values = {str(row[field]) for row in rows if row.get(field) is not None}
        if len(values) == 1:
            summary[field] = values.pop()
    source_urls = {str(row["pricing_source_url"]) for row in rows if row.get("pricing_source_url")}
    if len(source_urls) == 1:
        summary["pricing_source_url"] = source_urls.pop()
    return summary


def write_operational_artifacts(
    records: list[RunRecord],
    out_dir: Path,
    *,
    pricing: PricingConfig | None = None,
) -> dict[str, Any]:
    rows = operational_rows(records, pricing=pricing)
    if not rows:
        return {}
    summary = summarize_operational_rows(rows)
    write_jsonl(out_dir / "operational_metrics.jsonl", rows)
    write_json(out_dir / "operational_summary.json", summary)
    return summary
