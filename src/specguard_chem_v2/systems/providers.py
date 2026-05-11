from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProviderName = Literal["openai", "anthropic", "deepseek"]
ModelTier = Literal["frontier", "fast", "other"]
PromptProfile = Literal["default", "json_first"]


class LLMModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    provider: ProviderName
    model: str
    tier: ModelTier = "other"
    api_key_env: str | None = None
    base_url: str | None = None
    reasoning_effort: str | None = None
    thinking: bool | None = None
    thinking_budget_tokens: int | None = Field(default=None, gt=0)
    max_tokens: int = Field(default=4096, gt=0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    prompt_profile: PromptProfile = "default"
    request_timeout_seconds: int | None = Field(default=None, gt=0)
    notes: str | None = None

    @field_validator("id", "model")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_thinking_budget(self) -> "LLMModelConfig":
        if self.thinking_budget_tokens is not None:
            if self.provider != "anthropic":
                raise ValueError("thinking_budget_tokens is currently supported only for Anthropic")
            if self.thinking_budget_tokens >= self.max_tokens:
                raise ValueError("thinking_budget_tokens must be less than max_tokens")
        return self


def default_openai_config(model: str) -> LLMModelConfig:
    return LLMModelConfig(
        id="openai_default",
        provider="openai",
        model=model,
        api_key_env="OPENAI_API_KEY",
    )


def load_model_matrix(path: Path) -> dict[str, LLMModelConfig]:
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    raw_models = payload.get("models")
    if not isinstance(raw_models, dict):
        raise ValueError(f"{path} must contain a [models.<id>] table")
    configs: dict[str, LLMModelConfig] = {}
    for model_id, values in raw_models.items():
        if not isinstance(values, dict):
            raise ValueError(f"{path}: models.{model_id} must be a table")
        config = LLMModelConfig.model_validate({"id": model_id, **values})
        configs[model_id] = config
    return configs


def select_model_configs(
    configs: dict[str, LLMModelConfig],
    selection: str,
) -> list[LLMModelConfig]:
    if selection.strip().lower() == "all":
        return [configs[key] for key in sorted(configs)]
    requested = [item.strip() for item in selection.split(",") if item.strip()]
    missing = [item for item in requested if item not in configs]
    if missing:
        available = ", ".join(sorted(configs))
        raise ValueError(
            f"Unknown model condition(s): {', '.join(missing)}. Available: {available}"
        )
    return [configs[item] for item in requested]
