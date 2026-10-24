from __future__ import annotations

import hashlib

from src.contracts.schemas import AgentArtifact, RunResult
from src.storage.approval import ApprovalError, ApprovalRecord
from src.tools.contracts import ExportRequest, ExportResponse


def export_markdown(
    result: RunResult,
    approval: ApprovalRecord,
    selected_artifact_ids: list[str] | None = None,
) -> ExportResponse:
    if not isinstance(approval, ApprovalRecord):
        raise ApprovalError("An explicit Engineering Manager approval is required before export.")
    if approval.run_id != result.run_id:
        raise ApprovalError("Approval belongs to a different run.")
    by_id = {artifact.artifact_id: artifact for artifact in result.artifacts.values()}
    approved_revisions = dict(approval.artifact_revisions)
    approved_hashes = dict(approval.artifact_hashes)
    if set(approved_revisions) != set(approved_hashes):
        raise ApprovalError("Approval is incomplete: artifact integrity hashes are missing.")
    selected = (
        list(approved_revisions)
        if selected_artifact_ids is None
        else selected_artifact_ids
    )
    if not selected:
        raise ApprovalError("Export must include one or more explicitly approved artifacts.")
    if not set(selected).issubset(approved_revisions):
        raise ApprovalError("Export includes an artifact that was not explicitly approved.")
    request = ExportRequest(
        run_id=result.run_id,
        selected_artifact_ids=selected,
        approved_revisions=approved_revisions,
    )
    for artifact_id in request.selected_artifact_ids:
        artifact = by_id.get(artifact_id)
        approved_revision = request.approved_revisions.get(artifact_id)
        current_hash = (
            hashlib.sha256(artifact.model_dump_json().encode("utf-8")).hexdigest()
            if artifact is not None
            else None
        )
        if (
            artifact is None
            or approved_revision != artifact.revision
            or approved_hashes.get(artifact_id) != current_hash
        ):
            raise ApprovalError("Approval is stale: artifact revisions changed after approval.")

    body = [
        f"# Approved engineering artifacts — {result.run_id}",
        "",
        f"**Approver:** {approval.approver}",
        f"**Run badge:** {result.aggregate_badge}",
        f"**Approval time:** {approval.approved_at}",
        "",
        "> This export contains only the selected, revision-bound artifacts. It does not include the original BRD.",
    ]
    if result.evidence_disclaimer:
        body.extend(["", f"> **Evidence warning:** {result.evidence_disclaimer}"])
    for artifact_id in request.selected_artifact_ids:
        body.extend(["", _render_artifact(by_id[artifact_id])])
    if result.critic.findings:
        body.extend(["", "## Unresolved critic findings", ""])
        for finding in result.critic.findings:
            if finding.originating_artifact_id in request.selected_artifact_ids:
                body.append(
                    f"- **{finding.dimension}** ({finding.originating_artifact_id}): "
                    f"{finding.issue} Suggested correction: {finding.correction}"
                )
    status = "approved" if all(by_id[item].badge == "Green" for item in request.selected_artifact_ids) else "approved_with_findings"
    body.extend(["", f"**Export disposition:** {status}"])
    return ExportResponse(
        run_id=result.run_id,
        artifact_ids=request.selected_artifact_ids,
        markdown="\n".join(body),
    )


def _render_artifact(artifact: AgentArtifact) -> str:
    lines = [
        f"## {artifact.role.replace('_', ' ').title()}",
        "",
        f"- **Artifact ID:** `{artifact.artifact_id}`",
        f"- **Contract version:** `{artifact.contract_version}`",
        f"- **Revision:** {artifact.revision}",
        f"- **Quality badge:** {artifact.badge}",
        f"- **Actionability:** {artifact.actionability}/5",
        f"- **Source requirement IDs:** {', '.join(artifact.source_requirement_ids)}",
        f"- **Upstream artifacts:** {artifact.upstream_artifact_revisions}",
    ]
    lines.extend(["", "### Claims"])
    for claim in artifact.claims:
        lines.append(f"- {claim.text}")
        for citation in claim.citations:
            lines.append(
                f"  - Citation: `{citation.source_id}` / `{citation.chunk_id}` "
                f"({citation.source_locator})"
            )
    lines.extend(["", "### Assumptions"])
    lines.extend(f"- {item}" for item in artifact.assumptions)
    if artifact.uncertainties:
        lines.extend(["", "### Open uncertainties"])
        lines.extend(f"- [{item.type}] {item.description} (owner: {item.owner})" for item in artifact.uncertainties)
    if artifact.retrieval_disclaimer:
        lines.extend(["", f"> **Evidence disclaimer:** {artifact.retrieval_disclaimer}"])
    return "\n".join(lines)
