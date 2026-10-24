from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_VERSION = "1.0"
Role = Literal[
    "orchestrator",
    "engineering_plan",
    "schedule",
    "solution_architect",
    "poc_planner",
    "tech_stack",
    "critic",
]
UncertaintyType = Literal["ambiguity", "contradiction", "assumption", "question"]
UncertaintyStatus = Literal["open", "reviewed", "resolved"]
Badge = Literal["Green", "Amber", "Red"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    contract_version: Literal["1.0"] = CONTRACT_VERSION


class SourceRequirement(Contract):
    requirement_id: str
    text: str
    section_id: str
    source_locator: str
    source_hash: str


class NormalizedBRD(Contract):
    source_name: str
    source_hash: str
    title: str
    section_ids: list[str]
    requirements: list[SourceRequirement]

    @field_validator("requirements")
    @classmethod
    def must_have_requirements(cls, value: list[SourceRequirement]) -> list[SourceRequirement]:
        if not value:
            raise ValueError("BRD must contain at least one requirement")
        return value


class Citation(Contract):
    source_id: str
    chunk_id: str
    source_locator: str


class Uncertainty(Contract):
    uncertainty_id: str
    type: UncertaintyType
    description: str
    source_requirement_ids: list[str] = Field(default_factory=list)
    owner: str
    status: UncertaintyStatus = "open"


class Claim(Contract):
    text: str
    requirement_refs: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    non_trivial: bool = True


class AgentArtifact(Contract):
    run_id: str
    artifact_id: str
    role: Literal[
        "engineering_plan",
        "schedule",
        "solution_architect",
        "poc_planner",
        "tech_stack",
    ]
    revision: int = Field(default=0, ge=0, le=2)
    source_requirement_ids: list[str]
    upstream_artifact_ids: list[str] = Field(default_factory=list)
    upstream_artifact_revisions: dict[str, int] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[Uncertainty] = Field(default_factory=list)
    claims: list[Claim]
    covered_sections: list[str]
    actionability: float = Field(ge=1, le=5)
    badge: Badge = "Amber"
    retrieval_disclaimer: str | None = None

    @field_validator("claims")
    @classmethod
    def needs_claims(cls, value: list[Claim]) -> list[Claim]:
        if not value:
            raise ValueError("Artifacts must contain at least one claim")
        return value


class PlanArtifact(AgentArtifact):
    role: Literal["engineering_plan"] = "engineering_plan"
    phases: list[str]
    milestones: list[str]
    risks: list[str]
    team_composition: list[str]
    reflection: str


class ScheduleArtifact(AgentArtifact):
    role: Literal["schedule"] = "schedule"
    estimates: list[str]
    dependencies: list[str]
    timeline: list[str]
    resource_allocation: list[str]


class ArchitectureArtifact(AgentArtifact):
    role: Literal["solution_architect"] = "solution_architect"
    components: list[str]
    data_flows: list[str]
    nfr_mapping: list[str]


class PocArtifact(AgentArtifact):
    role: Literal["poc_planner"] = "poc_planner"
    scope: list[str]
    modular_boundaries: list[str]
    success_criteria: list[str]


class TechOption(Contract):
    name: str
    scalability: str
    team_familiarity: str
    integration_risk: str
    cost: str
    rationale: str


class TechStackArtifact(AgentArtifact):
    role: Literal["tech_stack"] = "tech_stack"
    options: list[TechOption]

    @field_validator("options")
    @classmethod
    def compare_two_or_three_options(cls, value: list[TechOption]) -> list[TechOption]:
        if len(value) not in (2, 3):
            raise ValueError("Tech-stack recommendations require two or three options")
        return value


class ArtifactScore(Contract):
    artifact_id: str
    revision: int = Field(default=0, ge=0, le=2)
    groundedness: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    consistency: float = Field(ge=0, le=1)
    actionability: float = Field(ge=1, le=5)
    overall: float = Field(ge=0, le=5)
    badge: Badge
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    cross_artifact_issues: list[str] = Field(default_factory=list)
    retrieval_empty: bool = False


class JudgeAssessment(Contract):
    artifact_id: str
    groundedness: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    consistency: float = Field(ge=0, le=1)
    actionability: float = Field(ge=1, le=5)
    note: str


class CriticFinding(Contract):
    originating_artifact_id: str
    dimension: Literal["groundedness", "completeness", "consistency", "actionability"]
    issue: str
    correction: str


class CriticResult(Contract):
    run_id: str
    artifact_id: str
    rubric_version: str = "1.0"
    scores: dict[str, ArtifactScore]
    findings: list[CriticFinding]
    revision_cycles: dict[str, int]
    badge: Badge


class OrchestratorResult(Contract):
    run_id: str
    artifact_id: str
    completed_roles: list[Role]
    transition_order: list[str]
    status: Literal["completed", "blocked", "rejected"]
    errors: list[str] = Field(default_factory=list)
    guardrail_events: list[str] = Field(default_factory=list)


class OperationalRecord(Contract):
    run_id: str
    agent_id: str
    input_hash: str
    output_id: str
    provider: str
    model: str
    duration_ms: int = Field(ge=0)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    score: float | None = None
    guardrail_events: list[str] = Field(default_factory=list)
    revision_count: int = Field(default=0, ge=0)


Artifact = Annotated[
    Union[PlanArtifact, ScheduleArtifact, ArchitectureArtifact, PocArtifact, TechStackArtifact],
    Field(discriminator="role"),
]


class RunResult(Contract):
    run_id: str
    input_hash: str
    normalized_brd: NormalizedBRD
    artifacts: dict[str, Artifact]
    critic: CriticResult
    orchestrator: OrchestratorResult
    operational_records: list[OperationalRecord]
    revision_history: dict[str, list[ArtifactScore]]
    evaluation: dict[str, object]
    retrieval_metadata: dict[str, object]
    aggregate_badge: Badge
    evidence_disclaimer: str | None = None
