from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ArtifactProvenance(BaseModel):
    """Version and content identity shared by paired benchmark artifacts."""

    model_config = ConfigDict(extra="forbid")

    benchmark_version: str
    data_version: str
    source_sha256: str = Field(pattern=SHA256_PATTERN)
    config_sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("benchmark_version", "data_version")
    @classmethod
    def _non_empty_version(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class AssayContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    target: str | None = None
    assay_type: str | None = None
    assay_id: str | None = None
    source: str | None = None
    activity_scale: str | None = None
    activity_direction: Literal["higher_is_better", "lower_is_better"] | None = None


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

    schema_version: str | None = None
    provenance: ArtifactProvenance | None = None
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

    @field_validator("schema_version")
    @classmethod
    def _schema_version_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("schema_version must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_ids(self) -> "DecisionCard":
        if (self.schema_version is None) != (self.provenance is None):
            raise ValueError(
                "schema_version and provenance must either both be present or both be absent"
            )
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


class CandidateOutcome(BaseModel):
    """One scorer-only candidate outcome, keyed to a system-input candidate ID."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    candidate_id: str
    activity_value: float
    activity_type: str = "pIC50"

    @field_validator("candidate_id", "activity_type")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class ScorerOutcomes(BaseModel):
    """Scorer-only outcomes cryptographically bound to one system-input card."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    provenance: ArtifactProvenance
    task_id: str
    system_input_sha256: str = Field(pattern=SHA256_PATTERN)
    outcomes: list[CandidateOutcome]

    @field_validator("schema_version", "task_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def _unique_candidate_ids(self) -> "ScorerOutcomes":
        candidate_ids = [outcome.candidate_id for outcome in self.outcomes]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("scorer outcome candidate IDs must be unique")
        return self


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
    raw_output: SystemOutput | None = None
    raw_issues: list[ValidationIssue] = Field(default_factory=list)
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
    action_validity: float = Field(ge=0.0, le=1.0)
    compliance_rate: float
    schema_error_rate: float
    wrong_k: bool
    pool_violation_count: int
    duplicate_count: int
    support_violation_count: int
    constraint_violation_count: int
    valid_selected_count: int
    raw_ndcg_at_k: float | None = None
    raw_feasible_utility: float | None = None
    raw_action_validity: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_compliance_rate: float | None = None
    raw_schema_error_rate: float | None = None
    raw_valid_selected_count: int | None = None
    raw_selection_count: int | None = None
    repaired_rate: float = 0.0
    repaired_from_empty_rate: float = 0.0
    repair_delta_feasible_utility: float | None = None
    hit_threshold: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
