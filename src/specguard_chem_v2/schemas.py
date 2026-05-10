from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class AssayContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    target: str | None = None
    assay_type: str | None = None
    assay_id: str | None = None
    source: str | None = None


class ConstraintSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["candidate", "output"]
    check: str
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "check")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class CompoundRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    smiles: str
    activity_value: float | None = Field(
        default=None,
        validation_alias=AliasChoices("activity_value", "pIC50", "pic50", "pchembl_value"),
        serialization_alias="activity_value",
    )
    activity_type: str = "pIC50"
    descriptors: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "smiles")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class DecisionCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    assay_context: AssayContext = Field(default_factory=AssayContext)
    support_set: list[CompoundRecord]
    candidate_pool: list[CompoundRecord]
    budget_k: int = Field(gt=0)
    hard_constraints: list[ConstraintSpec]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("task_id")
    @classmethod
    def _task_id_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("task_id must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_ids(self) -> "DecisionCard":
        support_ids = [compound.id for compound in self.support_set]
        candidate_ids = [compound.id for compound in self.candidate_pool]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_pool IDs must be unique")
        if len(set(support_ids)) != len(support_ids):
            raise ValueError("support_set IDs must be unique")
        return self

    @property
    def candidate_by_id(self) -> dict[str, CompoundRecord]:
        return {compound.id: compound for compound in self.candidate_pool}

    @property
    def support_ids(self) -> set[str]:
        return {compound.id for compound in self.support_set}


class SelectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    candidate_id: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = None

    @field_validator("candidate_id")
    @classmethod
    def _candidate_id_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("candidate_id must be non-empty")
        return value


class SystemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    system_name: str
    selections: list[SelectionItem]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    candidate_id: str | None = None
    constraint_id: str | None = None
    rank: int | None = None


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    system_name: str
    output: SystemOutput
    issues: list[ValidationIssue] = Field(default_factory=list)
    repaired: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CardScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    system_name: str
    ndcg_at_k: float
    mean_selected_activity: float | None
    hit_recovery_at_k: float | None
    enrichment_at_k: float | None
    feasible_utility: float
    oracle_utility: float
    constrained_regret: float
    compliance_rate: float
    schema_error_rate: float
    wrong_k: bool
    pool_violation_count: int
    duplicate_count: int
    support_violation_count: int
    constraint_violation_count: int
    valid_selected_count: int
    hit_threshold: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
