from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from src.contracts.schemas import RunResult


class ApprovalError(ValueError):
    """Raised when approval does not cover the exact artifacts being exported."""


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    approver: str
    artifact_revisions: tuple[tuple[str, int], ...]
    artifact_hashes: tuple[tuple[str, str], ...]
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def approve_run(
    result: RunResult,
    approver: str,
    selected_artifact_ids: list[str] | None = None,
) -> ApprovalRecord:
    if result.orchestrator.status != "completed":
        raise ApprovalError("Only a completed run can be approved.")
    if not approver.strip():
        raise ApprovalError("An identified Engineering Manager is required for approval.")
    current = {
        artifact.artifact_id: artifact.revision
        for artifact in result.artifacts.values()
    }
    artifacts_by_id = {
        artifact.artifact_id: artifact for artifact in result.artifacts.values()
    }
    selected = sorted(current) if selected_artifact_ids is None else selected_artifact_ids
    if not selected or not set(selected).issubset(current):
        raise ApprovalError("Approval must select one or more artifacts from this run.")
    for artifact_id in selected:
        artifact = artifacts_by_id[artifact_id]
        for upstream_role, upstream_revision in artifact.upstream_artifact_revisions.items():
            upstream = result.artifacts.get(upstream_role)
            if (
                upstream is None
                or upstream.artifact_id not in artifact.upstream_artifact_ids
                or upstream.revision != upstream_revision
            ):
                raise ApprovalError(
                    f"Cannot approve {artifact_id}: its {upstream_role} dependency is stale."
                )
    selected_ids = sorted(set(selected))
    return ApprovalRecord(
        run_id=result.run_id,
        approver=approver.strip(),
        artifact_revisions=tuple((artifact_id, current[artifact_id]) for artifact_id in selected_ids),
        artifact_hashes=tuple(
            (
                artifact_id,
                hashlib.sha256(
                    artifacts_by_id[artifact_id].model_dump_json().encode("utf-8")
                ).hexdigest(),
            )
            for artifact_id in selected_ids
        ),
    )
