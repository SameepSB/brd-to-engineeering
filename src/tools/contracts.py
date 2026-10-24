from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.contracts.schemas import AgentArtifact, NormalizedBRD, Uncertainty


class ToolContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParseRequest(ToolContract):
    filename: str
    content: str


class ParseResponse(ToolContract):
    brd: NormalizedBRD
    uncertainties: list[Uncertainty]


class RetrievedChunkOutput(ToolContract):
    source_id: str
    chunk_id: str
    source_locator: str
    text: str
    score: float = Field(ge=0, le=1)


class RetrievalRequest(ToolContract):
    query: str
    top_k: int = Field(default=4, ge=1, le=20)


class RetrievalResponse(ToolContract):
    chunks: list[RetrievedChunkOutput]
    error: str | None = None


class ExportRequest(ToolContract):
    run_id: str
    selected_artifact_ids: list[str]
    approved_revisions: dict[str, int]


class ExportResponse(ToolContract):
    run_id: str
    artifact_ids: list[str]
    markdown: str


class MockIntegrationRequest(ToolContract):
    run_id: str
    artifact: AgentArtifact

    @model_validator(mode="after")
    def artifact_must_belong_to_run(self):
        if self.artifact.run_id != self.run_id:
            raise ValueError("Integration request and artifact run IDs must match.")
        return self


class MockIntegrationResponse(ToolContract):
    external_id: str
    destination: str
    status: str
